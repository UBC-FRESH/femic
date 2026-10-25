from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from femic.hydrology import domain as hydrology
from femic.hydrology.domain import (
    HydrologyDomainError,
    HydrologyGauge,
    HydrologyLayerSpec,
    HydrologyReceptor,
    HydrologyWatershed,
    audit_hydrology_domain,
    build_hydrology_domain,
    find_hydrology_source,
    hydrology_source_registry,
    load_hydrology_domain_manifest,
    validate_hydrology_domain,
    write_hydrology_domain_manifest,
)

GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _file(path: Path, content: bytes = b"fixture") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _layer(
    layer_id: str,
    role: str,
    path: str,
    **kwargs: object,
) -> HydrologyLayerSpec:
    return HydrologyLayerSpec(
        layer_id=layer_id,
        role=role,
        path=path,
        format=str(kwargs.pop("format", "geojson")),
        crs=str(kwargs.pop("crs", "EPSG:3005")),
        geometry_type=str(kwargs.pop("geometry_type", "vector")),
        source_id=str(kwargs.pop("source_id", "")) or None,
        **kwargs,
    )


def _valid_domain(tmp_path: Path) -> tuple[hydrology.HydrologyDomainManifest, Path]:
    files = {
        "watersheds.geojson": b"watershed",
        "streams.geojson": b"stream",
        "roads.geojson": b"road",
        "dem.tif": b"dem",
        "receptors.geojson": b"receptor",
        "gauges.csv": b"gauge",
    }
    data_root = tmp_path / "data"
    for name, content in files.items():
        _file(data_root / name, content)
    layers = (
        _layer(
            "watersheds",
            "watershed",
            "data/watersheds.geojson",
            source_id="fwa_watersheds",
        ),
        _layer(
            "streams",
            "stream",
            "data/streams.geojson",
            source_id="fwa_streams",
        ),
        _layer(
            "roads",
            "road",
            "data/roads.geojson",
            source_id="road_atlas",
        ),
        _layer(
            "dem",
            "dem",
            "data/dem.tif",
            format="tif",
            geometry_type="raster",
            source_id="lidarbc_dem",
            resolution_m=1.0,
        ),
        _layer(
            "receptors",
            "receptor",
            "data/receptors.geojson",
            source_id="receptor_inventory",
        ),
        _layer(
            "gauges",
            "gauge",
            "data/gauges.csv",
            format="csv",
            geometry_type="table",
            source_id="wsc_gauges",
        ),
    )
    manifest = build_hydrology_domain(
        domain_id="test-domain",
        name="Test watershed domain",
        layers=layers,
        watersheds=(
            HydrologyWatershed(
                watershed_id="ws1",
                name="Test Creek",
                area_km2=12.5,
                layer_id="watersheds",
                feature_id="1",
            ),
        ),
        receptors=(
            HydrologyReceptor(
                receptor_id="r1",
                name="Downstream community",
                receptor_type="community",
                watershed_id="ws1",
                layer_id="receptors",
                feature_id="1",
                capacity_m3s=50.0,
            ),
        ),
        gauges=(
            HydrologyGauge(
                gauge_id="g1",
                station_name="Test Creek above town",
                watershed_id="ws1",
                layer_id="gauges",
                drainage_area_km2=12.5,
                period_start="1990-01-01",
                period_end="2020-12-31",
            ),
        ),
        caveats=("Screening only.",),
        provenance={"source": "unit-test"},
        created_utc=GENERATED_UTC,
    )
    return manifest, tmp_path


def test_source_registry_is_public_and_role_based() -> None:
    registry = hydrology_source_registry()

    assert len(registry) >= 8
    assert find_hydrology_source("fwa_watersheds") is not None
    assert find_hydrology_source("road_atlas") is not None
    assert find_hydrology_source("lidarbc_dem") is not None
    assert find_hydrology_source("missing") is None
    assert {source.role for source in registry} >= {
        "watershed",
        "stream",
        "road",
        "dem",
        "gauge",
        "receptor",
    }
    assert all(source.licence_id for source in registry)
    assert all(source.to_dict()["source_id"] == source.source_id for source in registry)


def test_build_write_load_and_audit_domain(tmp_path: Path) -> None:
    manifest, root = _valid_domain(tmp_path)
    validation = validate_hydrology_domain(manifest)
    assert validation.is_valid
    assert validation.warnings == ()

    path = write_hydrology_domain_manifest(
        manifest,
        tmp_path / "metadata" / "domain.json",
    )
    loaded = load_hydrology_domain_manifest(path)
    assert loaded.to_dict() == manifest.to_dict()

    audit = audit_hydrology_domain(path, data_root=root, checked_utc=GENERATED_UTC)
    assert audit.is_valid
    assert audit.domain_id == "test-domain"
    assert len(audit.layers) == 6
    assert all(layer.exists for layer in audit.layers)
    assert all(layer.checksum_ok is None for layer in audit.layers)
    assert audit.to_dict()["is_valid"] is True


def test_audit_checks_size_and_checksum(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    payload = b"good"
    _file(data_root / "watersheds.geojson", payload)
    _file(data_root / "streams.geojson", payload)
    _file(data_root / "roads.geojson", payload)
    _file(data_root / "dem.tif", payload)
    _file(data_root / "receptors.geojson", payload)
    digest = hashlib.sha256(payload).hexdigest()
    layers = tuple(
        _layer(
            name,
            role,
            f"data/{filename}",
            size_bytes=len(payload),
            checksum_sha256=digest,
        )
        for name, role, filename in (
            ("watersheds", "watershed", "watersheds.geojson"),
            ("streams", "stream", "streams.geojson"),
            ("roads", "road", "roads.geojson"),
            ("dem", "dem", "dem.tif"),
            ("receptors", "receptor", "receptors.geojson"),
        )
    )
    manifest = build_hydrology_domain(
        domain_id="checks",
        name="Checks",
        layers=layers,
        watersheds=(HydrologyWatershed("ws", "WS", 1.0, "watersheds"),),
        receptors=(
            HydrologyReceptor(
                "r",
                "Receptor",
                "channel_capacity",
                "ws",
                "receptors",
                capacity_m3s=1.0,
            ),
        ),
        gauges=(),
        created_utc=GENERATED_UTC,
    )
    path = write_hydrology_domain_manifest(manifest, tmp_path / "domain.json")
    audit = audit_hydrology_domain(path, data_root=tmp_path)
    assert audit.is_valid
    assert all(layer.checksum_ok is True for layer in audit.layers)

    (data_root / "roads.geojson").write_bytes(b"bad")
    audit = audit_hydrology_domain(path, data_root=tmp_path)
    assert not audit.is_valid
    assert any("size mismatch" in error for error in audit.errors)
    assert any(layer.checksum_ok is False for layer in audit.layers)


def test_audit_reports_missing_file(tmp_path: Path) -> None:
    manifest, root = _valid_domain(tmp_path)
    (root / "data" / "streams.geojson").unlink()

    audit = audit_hydrology_domain(manifest, data_root=root)

    assert not audit.is_valid
    assert any("missing" in error for error in audit.errors)
    assert any(not layer.exists for layer in audit.layers)


def test_validation_rejects_duplicate_ids_and_bad_roles(tmp_path: Path) -> None:
    manifest, _ = _valid_domain(tmp_path)
    duplicate = hydrology.HydrologyDomainManifest(
        **{
            **manifest.__dict__,
            "layers": manifest.layers + (manifest.layers[0],),
        }
    )
    validation = validate_hydrology_domain(duplicate)
    assert not validation.is_valid
    assert any("Duplicate layer ID" in error for error in validation.errors)

    bad_role = hydrology.HydrologyDomainManifest(
        **{
            **manifest.__dict__,
            "layers": (
                _layer("watersheds", "bad-role", "data/watersheds.geojson"),
                *manifest.layers[1:],
            ),
        }
    )
    validation = validate_hydrology_domain(bad_role)
    assert any("unsupported role" in error for error in validation.errors)


def test_validation_rejects_missing_roles_crs_and_checksum(tmp_path: Path) -> None:
    manifest, _ = _valid_domain(tmp_path)
    no_stream = hydrology.HydrologyDomainManifest(
        **{
            **manifest.__dict__,
            "layers": tuple(
                layer for layer in manifest.layers if layer.role != "stream"
            ),
        }
    )
    validation = validate_hydrology_domain(no_stream)
    assert any("missing required layer roles" in error for error in validation.errors)

    bad_crs_layer = _layer(
        "dem",
        "dem",
        "data/dem.tif",
        crs="EPSG:4326",
    )
    bad_crs = hydrology.HydrologyDomainManifest(
        **{
            **manifest.__dict__,
            "layers": tuple(
                bad_crs_layer if layer.layer_id == "dem" else layer
                for layer in manifest.layers
            ),
        }
    )
    validation = validate_hydrology_domain(bad_crs)
    assert any("does not match domain CRS" in error for error in validation.errors)

    bad_checksum_layer = _layer(
        "dem",
        "dem",
        "data/dem.tif",
        checksum_sha256="not-a-checksum",
    )
    bad_checksum = hydrology.HydrologyDomainManifest(
        **{
            **manifest.__dict__,
            "layers": tuple(
                bad_checksum_layer if layer.layer_id == "dem" else layer
                for layer in manifest.layers
            ),
        }
    )
    validation = validate_hydrology_domain(bad_checksum)
    assert any("invalid SHA-256" in error for error in validation.errors)


def test_validation_rejects_unknown_source_and_negative_resolution(
    tmp_path: Path,
) -> None:
    manifest, _ = _valid_domain(tmp_path)
    bad_source = hydrology.HydrologyDomainManifest(
        **{
            **manifest.__dict__,
            "layers": (
                _layer(
                    "watersheds",
                    "watershed",
                    "data/watersheds.geojson",
                    source_id="unknown-source",
                ),
                *manifest.layers[1:],
            ),
            "resolution_m": 0.0,
        }
    )
    validation = validate_hydrology_domain(bad_source)
    assert any("unknown source" in error for error in validation.errors)
    assert any("resolution_m" in error for error in validation.errors)


def test_validation_rejects_bad_receptor_and_gauge_links(tmp_path: Path) -> None:
    manifest, _ = _valid_domain(tmp_path)
    bad_receptor = HydrologyReceptor(
        receptor_id="r1",
        name="Bad receptor",
        receptor_type="unknown",
        watershed_id="missing",
        layer_id="missing",
        capacity_m3s=-1.0,
    )
    bad_gauge = HydrologyGauge(
        gauge_id="g1",
        station_name="Bad gauge",
        watershed_id="missing",
        layer_id="missing",
        drainage_area_km2=-1.0,
        period_start="2020-01-01",
        period_end="1990-01-01",
    )
    bad = hydrology.HydrologyDomainManifest(
        **{
            **manifest.__dict__,
            "receptors": (bad_receptor,),
            "gauges": (bad_gauge,),
        }
    )
    validation = validate_hydrology_domain(bad)
    assert any("unsupported type" in error for error in validation.errors)
    assert any("unknown watershed" in error for error in validation.errors)
    assert any("unknown layer" in error for error in validation.errors)
    assert any("positive capacity" in error for error in validation.errors)
    assert any("positive drainage area" in error for error in validation.errors)
    assert any("period start" in error for error in validation.errors)


def test_validation_warns_when_no_gauge(tmp_path: Path) -> None:
    manifest, _ = _valid_domain(tmp_path)
    no_gauge = hydrology.HydrologyDomainManifest(**{**manifest.__dict__, "gauges": ()})

    validation = validate_hydrology_domain(no_gauge)

    assert validation.is_valid
    assert any(
        "no linked hydrometric gauge" in warning for warning in validation.warnings
    )


def test_load_rejects_bad_schema_and_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "domain.json"
    path.write_text('{"schema_version": "bad"}')
    with pytest.raises(HydrologyDomainError, match="Unsupported"):
        load_hydrology_domain_manifest(path)

    path.write_text("not-json")
    with pytest.raises(HydrologyDomainError, match="Invalid JSON"):
        load_hydrology_domain_manifest(path)

    path.write_text("[]")
    with pytest.raises(HydrologyDomainError, match="JSON object"):
        load_hydrology_domain_manifest(path)


def test_build_rejects_invalid_domain(tmp_path: Path) -> None:
    with pytest.raises(HydrologyDomainError):
        build_hydrology_domain(
            domain_id="bad",
            name="Bad",
            layers=(),
            watersheds=(),
            receptors=(),
            gauges=(),
        )


def test_layer_payload_helpers_and_audit_payload(tmp_path: Path) -> None:
    manifest, root = _valid_domain(tmp_path)
    audit = audit_hydrology_domain(manifest, data_root=root)
    payload = audit.to_dict()
    assert payload["domain_id"] == "test-domain"
    assert len(payload["layers"]) == 6
    assert validate_hydrology_domain(manifest).to_dict()["is_valid"] is True
    assert (
        find_hydrology_source("fwa_streams").title == "Freshwater Atlas stream networks"
    )
    assert (
        json.loads(json.dumps(hydrology_source_registry()[0].to_dict()))["source_id"]
        == "fwa_watersheds"
    )


def test_validation_covers_missing_identity_and_negative_values(
    tmp_path: Path,
) -> None:
    bad_layer = HydrologyLayerSpec(
        layer_id=" ",
        role="watershed",
        path=" ",
        format=" ",
        crs=" ",
        licence_id=" ",
        size_bytes=-1,
        resolution_m=0.0,
    )
    manifest = hydrology.HydrologyDomainManifest(
        domain_id=" ",
        name=" ",
        created_utc=" ",
        crs=" ",
        resolution_m=-1.0,
        layers=(bad_layer,),
        watersheds=(HydrologyWatershed(" ", " ", 0.0, "missing"),),
        receptors=(HydrologyReceptor(" ", " ", "community", "missing", "missing"),),
        gauges=(HydrologyGauge(" ", " ", "missing", layer_id="missing"),),
    )

    validation = validate_hydrology_domain(manifest)

    assert not validation.is_valid
    assert any("Domain ID" in error for error in validation.errors)
    assert any("Domain name" in error for error in validation.errors)
    assert any("created_utc" in error for error in validation.errors)
    assert any("Domain CRS" in error for error in validation.errors)
    assert any("resolution_m" in error for error in validation.errors)
    assert any("Layer ID" in error for error in validation.errors)
    assert any("has no path" in error for error in validation.errors)
    assert any("has no format" in error for error in validation.errors)
    assert any("has no licence" in error for error in validation.errors)
    assert any("has no CRS" in error for error in validation.errors)
    assert any("negative size" in error for error in validation.errors)
    assert any("non-positive resolution" in error for error in validation.errors)
    assert any("Watershed ID" in error for error in validation.errors)
    assert any("positive area" in error for error in validation.errors)
    assert any("Receptor ID" in error for error in validation.errors)
    assert any("Gauge ID" in error for error in validation.errors)


def test_validation_covers_duplicates_and_unknown_references(
    tmp_path: Path,
) -> None:
    manifest, _ = _valid_domain(tmp_path)
    duplicate_watershed = HydrologyWatershed("ws1", "Dup", 1.0, "missing")
    duplicate_receptor = HydrologyReceptor(
        "r1",
        "Dup",
        "community",
        "ws1",
        "missing",
    )
    duplicate_gauge = HydrologyGauge(
        "g1",
        "Dup",
        "ws1",
        layer_id="missing",
    )
    bad = hydrology.HydrologyDomainManifest(
        **{
            **manifest.__dict__,
            "watersheds": (manifest.watersheds[0], duplicate_watershed),
            "receptors": (manifest.receptors[0], duplicate_receptor),
            "gauges": (manifest.gauges[0], duplicate_gauge),
        }
    )

    validation = validate_hydrology_domain(bad)

    assert any("Duplicate watershed ID" in error for error in validation.errors)
    assert any("Duplicate receptor ID" in error for error in validation.errors)
    assert any("Duplicate gauge ID" in error for error in validation.errors)
    assert any("references unknown layer" in error for error in validation.errors)


def test_validation_covers_missing_receptor_and_layers(tmp_path: Path) -> None:
    manifest, _ = _valid_domain(tmp_path)
    no_receptor = hydrology.HydrologyDomainManifest(
        **{**manifest.__dict__, "receptors": ()}
    )
    no_layers = hydrology.HydrologyDomainManifest(
        **{
            **manifest.__dict__,
            "layers": (),
            "watersheds": (),
            "receptors": (),
            "gauges": (),
        }
    )

    assert any(
        "at least one flood-risk receptor" in error
        for error in validate_hydrology_domain(no_receptor).errors
    )
    assert any(
        "at least one layer" in error
        for error in validate_hydrology_domain(no_layers).errors
    )


def test_private_parsing_and_path_helpers(tmp_path: Path) -> None:
    absolute = tmp_path / "absolute.geojson"
    absolute.write_bytes(b"x")
    assert hydrology._resolve_layer_path(str(absolute), tmp_path) == absolute.resolve()

    with pytest.raises(HydrologyDomainError, match="Unable to read"):
        hydrology._read_json_object(tmp_path / "missing.json", context="test")
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json")
    with pytest.raises(HydrologyDomainError, match="Invalid JSON"):
        hydrology._read_json_object(invalid, context="test")
    array = tmp_path / "array.json"
    array.write_text("[]")
    with pytest.raises(HydrologyDomainError, match="JSON object"):
        hydrology._read_json_object(array, context="test")

    with pytest.raises(HydrologyDomainError, match="must be an object"):
        hydrology._mapping_from_object("x", context="test")
    with pytest.raises(HydrologyDomainError, match="must be a list"):
        hydrology._required_list({"v": "x"}, "v", context="test")
    with pytest.raises(HydrologyDomainError, match="non-empty string"):
        hydrology._required_str({"v": " "}, "v", context="test")
    with pytest.raises(HydrologyDomainError, match="must be numeric"):
        hydrology._required_float({"v": "x"}, "v", context="test")
    assert hydrology._optional_int(True) is None
    assert hydrology._optional_int("2") == 2
    assert hydrology._optional_int("x") is None
    assert hydrology._optional_int(object()) is None
    assert hydrology._optional_float(True) is None
    assert hydrology._optional_float("2.5") == 2.5
    assert hydrology._optional_float("x") is None
    assert hydrology._optional_float(object()) is None
    assert hydrology._optional_float(float("inf")) is None
    assert hydrology._optional_str_list(None, context="test") == ()
    assert hydrology._optional_str_list([" a ", ""], context="test") == ("a",)
    with pytest.raises(HydrologyDomainError, match="must be a list"):
        hydrology._optional_str_list("x", context="test")
    with pytest.raises(HydrologyDomainError, match="must be strings"):
        hydrology._optional_str_list([1], context="test")
    assert hydrology._optional_mapping(None, context="test") == {}
    with pytest.raises(HydrologyDomainError, match="must be an object"):
        hydrology._optional_mapping("x", context="test")


def test_record_payloads_round_trip(tmp_path: Path) -> None:
    manifest, _ = _valid_domain(tmp_path)
    assert manifest.layers[0].to_dict()["layer_id"] == "watersheds"
    assert manifest.watersheds[0].to_dict()["watershed_id"] == "ws1"
    assert manifest.receptors[0].to_dict()["receptor_id"] == "r1"
    assert manifest.gauges[0].to_dict()["gauge_id"] == "g1"
    assert (
        manifest.to_dict()["schema_version"]
        == hydrology.HYDROLOGY_DOMAIN_SCHEMA_VERSION
    )


def test_validation_rejects_unsupported_schema(tmp_path: Path) -> None:
    manifest, _ = _valid_domain(tmp_path)
    bad = hydrology.HydrologyDomainManifest(
        **{**manifest.__dict__, "schema_version": "bad"}
    )

    validation = validate_hydrology_domain(bad)

    assert not validation.is_valid
    assert any(
        "Unsupported hydrology domain schema" in error for error in validation.errors
    )
