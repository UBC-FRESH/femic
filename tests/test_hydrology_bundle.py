from __future__ import annotations

import json
from pathlib import Path

import pytest

from femic.hydrology.bundle import (
    HydrologyBundleBuildResult,
    HydrologyBundleError,
    audit_hydrology_bundle,
    build_hydrology_bundle,
    load_hydrology_bundle_manifest,
    plan_hydrology_bundle,
    validate_hydrology_bundle_manifest,
    write_hydrology_bundle_manifest,
)
from femic.hydrology.domain import (
    HydrologyGauge,
    HydrologyLayerSpec,
    HydrologyReceptor,
    HydrologyWatershed,
    build_hydrology_domain,
    load_hydrology_domain_manifest,
    write_hydrology_domain_manifest,
)

GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _file(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _domain_fixture(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    data_root = tmp_path / "data"
    files = {
        "watersheds": _file(data_root / "watersheds.geojson", b"watershed"),
        "streams": _file(data_root / "streams.geojson", b"stream"),
        "roads": _file(data_root / "roads.geojson", b"road"),
        "dem": _file(data_root / "dem.tif", b"dem"),
        "receptors": _file(data_root / "receptors.geojson", b"receptor"),
        "gauges": _file(data_root / "gauges.csv", b"gauge"),
    }
    layers = (
        HydrologyLayerSpec(
            "watersheds",
            "watershed",
            "data/watersheds.geojson",
            "geojson",
            "EPSG:3005",
            source_id="fwa_watersheds",
        ),
        HydrologyLayerSpec(
            "streams",
            "stream",
            "data/streams.geojson",
            "geojson",
            "EPSG:3005",
            source_id="fwa_streams",
        ),
        HydrologyLayerSpec(
            "roads",
            "road",
            "data/roads.geojson",
            "geojson",
            "EPSG:3005",
            source_id="road_atlas",
        ),
        HydrologyLayerSpec(
            "dem",
            "dem",
            "data/dem.tif",
            "tif",
            "EPSG:3005",
            source_id="lidarbc_dem",
        ),
        HydrologyLayerSpec(
            "receptors",
            "receptor",
            "data/receptors.geojson",
            "geojson",
            "EPSG:3005",
            source_id="receptor_inventory",
        ),
        HydrologyLayerSpec(
            "gauges",
            "gauge",
            "data/gauges.csv",
            "csv",
            "EPSG:3005",
            source_id="wsc_gauges",
        ),
    )
    domain = build_hydrology_domain(
        domain_id="bundle-domain",
        name="Bundle domain",
        layers=layers,
        watersheds=(HydrologyWatershed("ws1", "Creek", 10.0, "watersheds"),),
        receptors=(
            HydrologyReceptor(
                "r1",
                "Town",
                "community",
                "ws1",
                "receptors",
                capacity_m3s=10.0,
            ),
        ),
        gauges=(HydrologyGauge("g1", "Creek gauge", "ws1", "gauges"),),
        created_utc=GENERATED_UTC,
    )
    path = write_hydrology_domain_manifest(domain, tmp_path / "domain.json")
    return path, files


def _build(tmp_path: Path, *, overwrite: bool = False) -> HydrologyBundleBuildResult:
    domain_path, sources = _domain_fixture(tmp_path)
    return build_hydrology_bundle(
        domain_path,
        tmp_path / "bundle",
        aoi_bbox_epsg3005=(0, 0, 10, 10),
        sources=sources,
        generated_utc=GENERATED_UTC,
        overwrite=overwrite,
    )


def test_plan_bundle_records_layers_and_checksums(tmp_path: Path) -> None:
    domain_path, sources = _domain_fixture(tmp_path)

    manifest = plan_hydrology_bundle(
        load_hydrology_domain_manifest(domain_path),
        bundle_dir=tmp_path / "bundle",
        aoi_bbox_epsg3005=(0, 0, 10, 10),
        sources=sources,
        generated_utc=GENERATED_UTC,
    )

    assert manifest.bundle_id.startswith("hydro-")
    assert manifest.layer_count == 6
    assert manifest.materialized_count == 0
    assert manifest.gaps == ()
    assert all(layer.status == "planned" for layer in manifest.layers)
    assert all(layer.checksum_sha256 for layer in manifest.layers)
    assert all(layer.size_bytes and layer.size_bytes > 0 for layer in manifest.layers)
    assert manifest.to_dict()["summary"]["layer_count"] == 6
    assert manifest.caveats


def test_build_bundle_copies_and_audits(tmp_path: Path) -> None:
    domain_path, sources = _domain_fixture(tmp_path)
    result = build_hydrology_bundle(
        domain_path,
        tmp_path / "bundle",
        aoi_bbox_epsg3005=(0, 0, 10, 10),
        sources=sources,
        generated_utc=GENERATED_UTC,
    )

    assert result.bundle_dir == (tmp_path / "bundle").resolve()
    assert result.manifest.is_complete
    assert result.manifest.materialized_count == 6
    assert result.manifest.gaps == ()
    assert result.manifest_path.is_file()
    for layer in result.manifest.layers:
        assert layer.status == "materialized"
        assert (result.bundle_dir / layer.relative_path).is_file()
    audit = audit_hydrology_bundle(result.bundle_dir)
    assert audit.is_valid
    assert audit.is_complete
    assert audit.errors == ()
    assert len(audit.layers) == 6
    assert all(layer.exists for layer in audit.layers)
    assert all(layer.checksum_ok is True for layer in audit.layers)
    assert result.to_dict()["manifest"]["bundle_id"] == result.manifest.bundle_id


def test_build_bundle_id_is_stable(tmp_path: Path) -> None:
    domain_path, sources = _domain_fixture(tmp_path)
    first = build_hydrology_bundle(
        domain_path,
        tmp_path / "first",
        aoi_bbox_epsg3005=(0, 0, 10, 10),
        sources=sources,
        generated_utc=GENERATED_UTC,
    )
    second = build_hydrology_bundle(
        domain_path,
        tmp_path / "second",
        aoi_bbox_epsg3005=(0, 0, 10, 10),
        sources=sources,
        generated_utc=GENERATED_UTC,
    )

    assert first.manifest.bundle_id == second.manifest.bundle_id
    assert first.manifest.layers == second.manifest.layers


def test_plan_reports_gaps_and_audit_is_incomplete(tmp_path: Path) -> None:
    domain_path, _ = _domain_fixture(tmp_path)

    manifest = plan_hydrology_bundle(
        load_hydrology_domain_manifest(domain_path),
        bundle_dir=tmp_path / "bundle",
        aoi_bbox_epsg3005=(0, 0, 10, 10),
        sources=None,
    )
    assert len(manifest.gaps) == 6
    assert all(layer.status == "missing" for layer in manifest.layers)
    path = write_hydrology_bundle_manifest(
        manifest, tmp_path / "bundle" / "bundle.json"
    )
    audit = audit_hydrology_bundle(path)
    assert audit.is_valid
    assert not audit.is_complete
    assert len(audit.warnings) >= 6


def test_build_rejects_missing_sources(tmp_path: Path) -> None:
    domain_path, sources = _domain_fixture(tmp_path)
    sources = dict(sources)
    sources.pop("streams")

    with pytest.raises(HydrologyBundleError, match="incomplete"):
        build_hydrology_bundle(
            domain_path,
            tmp_path / "bundle",
            aoi_bbox_epsg3005=(0, 0, 10, 10),
            sources=sources,
        )


def test_audit_detects_missing_and_tampered_layers(tmp_path: Path) -> None:
    result = _build(tmp_path)
    first = result.bundle_dir / result.manifest.layers[0].relative_path
    first.unlink()
    second = result.bundle_dir / result.manifest.layers[1].relative_path
    second.write_bytes(b"tampered")

    audit = audit_hydrology_bundle(result.bundle_dir)

    assert not audit.is_valid
    assert not audit.is_complete
    assert any("missing" in error for error in audit.errors)
    assert any("checksum mismatch" in error for error in audit.errors)


def test_audit_detects_path_escape(tmp_path: Path) -> None:
    result = _build(tmp_path)
    payload = json.loads(result.manifest_path.read_text())
    payload["layers"][0]["relative_path"] = "../escape.geojson"
    result.manifest_path.write_text(json.dumps(payload))

    audit = audit_hydrology_bundle(result.bundle_dir)

    assert not audit.is_valid
    assert any("escapes" in error for error in audit.errors)


def test_build_overwrite_and_manifest_loading(tmp_path: Path) -> None:
    result = _build(tmp_path)
    rebuilt = _build(tmp_path, overwrite=True)
    assert rebuilt.manifest.bundle_id == result.manifest.bundle_id

    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "bundle.json").write_text("not-json")
    with pytest.raises(HydrologyBundleError, match="non-bundle|unreadable"):
        build_hydrology_bundle(
            tmp_path / "domain.json",
            foreign,
            aoi_bbox_epsg3005=(0, 0, 10, 10),
            sources=_domain_fixture(tmp_path)[1],
            overwrite=True,
        )


def test_load_and_validate_manifest_errors(tmp_path: Path) -> None:
    result = _build(tmp_path)
    payload = json.loads(result.manifest_path.read_text())
    payload["schema_version"] = "bad"
    result.manifest_path.write_text(json.dumps(payload))
    with pytest.raises(HydrologyBundleError, match="Unsupported"):
        load_hydrology_bundle_manifest(result.manifest_path)

    result.manifest_path.write_text("not-json")
    with pytest.raises(HydrologyBundleError, match="Invalid JSON"):
        load_hydrology_bundle_manifest(result.manifest_path)

    result.manifest_path.write_text("[]")
    with pytest.raises(HydrologyBundleError, match="JSON object"):
        load_hydrology_bundle_manifest(result.manifest_path)


def test_validate_bundle_manifest_errors(tmp_path: Path) -> None:
    result = _build(tmp_path)
    manifest = result.manifest
    broken = type(manifest)(
        **{
            **manifest.__dict__,
            "bundle_id": "",
            "bundle_version": "",
            "domain_id": "",
            "domain_sha256": "bad",
            "aoi_bbox_epsg3005": (1.0, 1.0, 1.0, 2.0),
            "layers": (
                type(manifest.layers[0])(
                    **{
                        **manifest.layers[0].__dict__,
                        "licence_id": "",
                        "status": "bad",
                        "checksum_sha256": "bad",
                        "size_bytes": -1,
                        "source_id": "unknown",
                    }
                ),
            ),
        }
    )

    errors = validate_hydrology_bundle_manifest(broken)

    assert any("Bundle ID" in error for error in errors)
    assert any("Bundle version" in error for error in errors)
    assert any("Domain ID" in error for error in errors)
    assert any("Domain SHA-256" in error for error in errors)
    assert any("AOI bbox" in error for error in errors)
    assert any("missing required layer roles" in error for error in errors)
    assert any("unsupported status" in error for error in errors)
    assert any("no licence" in error for error in errors)
    assert any("invalid SHA-256" in error for error in errors)
    assert any("negative size" in error for error in errors)
    assert any("unknown source" in error for error in errors)


def test_plan_rejects_bad_inputs(tmp_path: Path) -> None:
    domain_path, sources = _domain_fixture(tmp_path)
    domain = load_hydrology_domain_manifest(domain_path)
    with pytest.raises(HydrologyBundleError, match="unknown layer IDs"):
        plan_hydrology_bundle(
            domain,
            bundle_dir=tmp_path / "bundle",
            aoi_bbox_epsg3005=(0, 0, 1, 1),
            sources={"missing": sources["streams"]},
        )
    with pytest.raises(HydrologyBundleError, match="AOI bbox"):
        plan_hydrology_bundle(
            domain,
            bundle_dir=tmp_path / "bundle",
            aoi_bbox_epsg3005=(0, 0, 0, 1),
            sources=sources,
        )
    with pytest.raises(HydrologyBundleError, match="Bundle version"):
        plan_hydrology_bundle(
            domain,
            bundle_dir=tmp_path / "bundle",
            aoi_bbox_epsg3005=(0, 0, 1, 1),
            sources=sources,
            bundle_version=" ",
        )


def test_plan_invalid_domain_and_nonfile_source(tmp_path: Path) -> None:
    domain_path, sources = _domain_fixture(tmp_path)
    domain = load_hydrology_domain_manifest(domain_path)
    invalid = type(domain)(**{**domain.__dict__, "domain_id": ""})
    with pytest.raises(HydrologyBundleError, match="Domain ID"):
        plan_hydrology_bundle(
            invalid,
            bundle_dir=tmp_path / "bundle",
            aoi_bbox_epsg3005=(0, 0, 1, 1),
            sources=sources,
        )

    directory_source = tmp_path / "directory-source"
    directory_source.mkdir()
    plan = plan_hydrology_bundle(
        domain,
        bundle_dir=tmp_path / "bundle",
        aoi_bbox_epsg3005=(0, 0, 1, 1),
        sources={"streams": directory_source},
    )
    gap = next(gap for gap in plan.gaps if gap.layer_id == "streams")
    assert "Source file is missing" in gap.reason


def test_plan_rejects_bad_source_mapping(tmp_path: Path) -> None:
    with pytest.raises(HydrologyBundleError, match="non-empty strings"):
        plan_hydrology_bundle(
            load_hydrology_domain_manifest(_domain_fixture(tmp_path)[0]),
            bundle_dir=tmp_path / "bundle",
            aoi_bbox_epsg3005=(0, 0, 1, 1),
            sources={"": tmp_path / "x"},
        )
    with pytest.raises(HydrologyBundleError, match="must be a Path"):
        plan_hydrology_bundle(
            load_hydrology_domain_manifest(_domain_fixture(tmp_path)[0]),
            bundle_dir=tmp_path / "bundle",
            aoi_bbox_epsg3005=(0, 0, 1, 1),
            sources={"streams": "not-a-path"},  # type: ignore[dict-item]
        )


def test_audit_missing_manifest_and_missing_checksum(tmp_path: Path) -> None:
    missing = audit_hydrology_bundle(tmp_path / "missing")
    assert not missing.is_valid
    assert "Unable to read" in missing.errors[0]

    result = _build(tmp_path)
    payload = json.loads(result.manifest_path.read_text())
    payload["layers"][0]["checksum_sha256"] = None
    result.manifest_path.write_text(json.dumps(payload))
    audit = audit_hydrology_bundle(result.bundle_dir)
    assert not audit.is_valid
    assert any("no checksum" in error for error in audit.errors)


def test_audit_warns_when_planned_layer_has_a_file(tmp_path: Path) -> None:
    domain_path, sources = _domain_fixture(tmp_path)
    domain = load_hydrology_domain_manifest(domain_path)
    manifest = plan_hydrology_bundle(
        domain,
        bundle_dir=tmp_path / "bundle",
        aoi_bbox_epsg3005=(0, 0, 10, 10),
        sources=sources,
    )
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    target = bundle / manifest.layers[0].relative_path
    target.parent.mkdir(parents=True)
    target.write_bytes(b"planned")
    write_hydrology_bundle_manifest(manifest, bundle / "bundle.json")

    audit = audit_hydrology_bundle(bundle)

    assert audit.is_valid
    assert any("but a local file exists" in warning for warning in audit.warnings)
    assert audit.to_dict()["is_complete"] is False
    assert audit.layers[0].to_dict()["layer_id"] == manifest.layers[0].layer_id


def test_validate_bundle_manifest_more_errors(tmp_path: Path) -> None:
    result = _build(tmp_path)
    manifest = result.manifest
    from dataclasses import replace

    broken = replace(
        manifest,
        aoi_bbox_epsg3005=(0.0, 0.0, 1.0),
        layers=(
            replace(
                manifest.layers[0],
                relative_path="",
                source_id="unknown",
            ),
            manifest.layers[0],
        ),
    )
    errors = validate_hydrology_bundle_manifest(broken)
    assert any("four numbers" in error for error in errors)
    assert any("Duplicate bundle layer ID" in error for error in errors)
    assert any("no relative path" in error for error in errors)

    nonfinite = replace(manifest, aoi_bbox_epsg3005=(0.0, 0.0, float("nan"), 1.0))
    assert any(
        "AOI bbox must be finite" in error
        for error in validate_hydrology_bundle_manifest(nonfinite)
    )
    empty = replace(manifest, layers=())
    assert any(
        "at least one layer" in error
        for error in validate_hydrology_bundle_manifest(empty)
    )


def test_prepare_output_and_assert_replaceable_paths(tmp_path: Path) -> None:
    from femic.hydrology.bundle import _assert_replaceable_bundle, _prepare_output

    file_output = tmp_path / "file"
    file_output.write_text("x")
    with pytest.raises(HydrologyBundleError, match="not a directory"):
        _prepare_output(file_output, overwrite=False)

    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    (nonempty / "file").write_text("x")
    with pytest.raises(HydrologyBundleError, match="not empty"):
        _prepare_output(nonempty, overwrite=False)
    with pytest.raises(HydrologyBundleError, match="non-bundle"):
        _prepare_output(nonempty, overwrite=True)
    with pytest.raises(HydrologyBundleError, match="non-bundle"):
        _assert_replaceable_bundle(nonempty)

    unreadable = tmp_path / "unreadable"
    unreadable.mkdir()
    (unreadable / "bundle.json").write_text("not-json")
    with pytest.raises(HydrologyBundleError, match="unreadable"):
        _prepare_output(unreadable, overwrite=True)

    foreign = tmp_path / "foreign-schema"
    foreign.mkdir()
    (foreign / "bundle.json").write_text('{"schema_version": "other"}')
    with pytest.raises(HydrologyBundleError, match="unreadable"):
        _prepare_output(foreign, overwrite=True)
    with pytest.raises(HydrologyBundleError, match="Unsupported"):
        _assert_replaceable_bundle(foreign)


def test_build_cleans_temp_directory_on_copy_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domain_path, sources = _domain_fixture(tmp_path)

    def fail_copy(source: Path, destination: Path) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr("femic.hydrology.bundle.shutil.copyfile", fail_copy)
    with pytest.raises(OSError, match="copy failed"):
        build_hydrology_bundle(
            domain_path,
            tmp_path / "bundle",
            aoi_bbox_epsg3005=(0, 0, 10, 10),
            sources=sources,
        )
    assert not (tmp_path / "bundle").exists()
    assert not any(path.name.startswith(".bundle.") for path in tmp_path.iterdir())


def test_build_into_empty_directory_and_private_parsers(tmp_path: Path) -> None:
    from femic.hydrology.bundle import (
        _mapping_from_object,
        _normalize_bbox,
        _optional_int,
        _optional_mapping,
        _optional_str_list,
        _read_json_object,
        _required_bbox,
        _required_list,
        _required_str,
        _safe_filename,
    )

    domain_path, sources = _domain_fixture(tmp_path)
    output = tmp_path / "bundle"
    output.mkdir()
    result = build_hydrology_bundle(
        domain_path,
        output,
        aoi_bbox_epsg3005=(0, 0, 10, 10),
        sources=sources,
    )
    assert result.bundle_dir == output.resolve()

    with pytest.raises(HydrologyBundleError, match="four values"):
        _normalize_bbox((0, 0, 1))
    with pytest.raises(HydrologyBundleError, match="numeric"):
        _normalize_bbox(("x", 0, 1, 1))
    with pytest.raises(HydrologyBundleError, match="finite"):
        _normalize_bbox((0, 0, float("inf"), 1))
    with pytest.raises(HydrologyBundleError, match="minx < maxx"):
        _normalize_bbox((0, 0, 0, 1))

    with pytest.raises(HydrologyBundleError, match="must be an object"):
        _mapping_from_object("x", context="test")
    with pytest.raises(HydrologyBundleError, match="must be a list"):
        _required_list({"v": "x"}, "v", context="test")
    with pytest.raises(HydrologyBundleError, match="non-empty string"):
        _required_str({"v": " "}, "v", context="test")
    with pytest.raises(HydrologyBundleError, match="must be a list"):
        _required_bbox({"aoi_bbox_epsg3005": "x"}, context="test")
    assert _optional_int(True) is None
    assert _optional_int("2") == 2
    assert _optional_int("x") is None
    assert _optional_int(object()) is None
    assert _optional_str_list(None, context="test") == ()
    with pytest.raises(HydrologyBundleError, match="must be a list"):
        _optional_str_list("x", context="test")
    with pytest.raises(HydrologyBundleError, match="must be strings"):
        _optional_str_list([1], context="test")
    assert _optional_mapping(None, context="test") == {}
    with pytest.raises(HydrologyBundleError, match="must be an object"):
        _optional_mapping("x", context="test")
    assert _safe_filename("###") == "artifact"
    with pytest.raises(HydrologyBundleError, match="Unable to read"):
        _read_json_object(tmp_path / "missing.json", context="test")
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json")
    with pytest.raises(HydrologyBundleError, match="Invalid JSON"):
        _read_json_object(invalid, context="test")
    array = tmp_path / "array.json"
    array.write_text("[]")
    with pytest.raises(HydrologyBundleError, match="JSON object"):
        _read_json_object(array, context="test")


def test_validate_rejects_unsupported_schema_and_optional_list_edges(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from femic.hydrology.bundle import _optional_str_list

    result = _build(tmp_path)
    broken = replace(result.manifest, schema_version="bad")
    assert any(
        "Unsupported hydrology bundle schema" in error
        for error in validate_hydrology_bundle_manifest(broken)
    )
    assert _optional_str_list(["a", "b"], context="test") == ("a", "b")
    assert _optional_str_list([""], context="test") == ()
