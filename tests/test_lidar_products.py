from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from femic.cli.main import app
from femic.lidar.products import (
    LidarProductError,
    build_lidar_product_bundle,
    load_lidar_product_plan,
    validate_lidar_product_bundle,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "lidar"
SELECTION_MANIFEST = FIXTURE_ROOT / "selection_manifest.json"
PRODUCT_PLAN = FIXTURE_ROOT / "product_plan.json"
GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _selection_copy(
    tmp_path: Path,
    *,
    mutate: object | None = None,
) -> Path:
    payload = _read_json(SELECTION_MANIFEST)
    if callable(mutate):
        mutate(payload)
    return _write_json(tmp_path / "selection.json", payload)


def _plan_copy(
    tmp_path: Path,
    *,
    mutate: object | None = None,
) -> Path:
    payload = _read_json(PRODUCT_PLAN)
    for product in payload["products"]:  # type: ignore[index]
        product["path"] = str(FIXTURE_ROOT / product["path"])
    if callable(mutate):
        mutate(payload)
    return _write_json(tmp_path / "product_plan.json", payload)


def _build(tmp_path: Path, **kwargs: object) -> object:
    return build_lidar_product_bundle(
        selection_manifest_path=SELECTION_MANIFEST,
        product_plan_path=PRODUCT_PLAN,
        output_dir=tmp_path / "bundle",
        generated_utc=GENERATED_UTC,
        **kwargs,
    )


def test_load_plan_resolves_product_paths() -> None:
    plan = load_lidar_product_plan(PRODUCT_PLAN)

    assert plan.bundle_version == "2026.10.0-fixture"
    assert plan.processing_version == "femic-p79.8-fixture-v1"
    assert len(plan.products) == 4
    assert plan.products[0].product == "dem"
    assert plan.products[0].source_path == (FIXTURE_ROOT / "products/dem.asc").resolve()
    assert plan.products[2].derived is True
    assert plan.products[2].source_layer_ids == (1, 5)
    assert plan.to_dict()["products"][0]["product"] == "dem"


def test_build_bundle_writes_manifest_and_products(tmp_path: Path) -> None:
    result = _build(tmp_path)

    assert result.bundle_dir == (tmp_path / "bundle").resolve()
    assert result.manifest_path.is_file()
    assert result.selection_path.is_file()
    assert result.manifest.bundle_id.startswith("lidarbc-")
    assert result.manifest.bundle_version == "2026.10.0-fixture"
    assert result.manifest.product_count == 4
    assert result.manifest.total_bytes == sum(
        path.stat().st_size for path in (result.bundle_dir / "products").iterdir()
    )
    assert (result.bundle_dir / "products/dem__01__dem.asc").is_file()
    assert (result.bundle_dir / "products/canopy__04__canopy.csv").is_file()

    manifest = _read_json(result.manifest_path)
    assert manifest["schema_version"] == "femic.lidar.product.v1"
    assert manifest["layout_version"] == "femic.lidar.bundle.v1"
    assert manifest["source"]["licence_id"] == "OGL-BC"
    assert manifest["selection"]["tile_count"] == 2
    assert manifest["selection"]["tile_ids"] == ["lidarbc:1:1", "lidarbc:5:1"]
    assert manifest["consumer_contract"]["consumer_phases"] == {
        "fhops": "P13",
        "ws4": "P43",
    }
    assert all("sha256" in product for product in manifest["products"])
    assert str(tmp_path) not in result.manifest_path.read_text(encoding="utf-8")


def test_build_is_reproducible_with_fixed_timestamp(tmp_path: Path) -> None:
    first = _build(tmp_path / "first")
    second = _build(tmp_path / "second")

    assert first.manifest.bundle_id == second.manifest.bundle_id
    assert first.manifest_path.read_text() == second.manifest_path.read_text()
    assert first.selection_path.read_text() == second.selection_path.read_text()


def test_build_refuses_nonempty_output_without_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir()
    (output / "existing.txt").write_text("keep me")

    with pytest.raises(LidarProductError, match="not empty"):
        _build(tmp_path)


def test_build_refuses_overwriting_non_bundle(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir()
    (output / "existing.txt").write_text("keep me")

    with pytest.raises(LidarProductError, match="Refusing to overwrite"):
        _build(tmp_path, overwrite=True)


def test_build_overwrites_existing_bundle(tmp_path: Path) -> None:
    first = _build(tmp_path)
    first_manifest = first.manifest_path.read_text()
    (first.bundle_dir / "products/dem__01__dem.asc").write_text("tampered")

    second = _build(tmp_path, overwrite=True)

    assert second.manifest.bundle_id == first.manifest.bundle_id
    assert second.manifest_path.read_text() == first_manifest
    assert (second.bundle_dir / "products/dem__01__dem.asc").read_text() != "tampered"


def test_build_rejects_tile_outside_selection(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        products = payload["products"]
        assert isinstance(products, list)
        first = products[0]
        assert isinstance(first, dict)
        first["source_tile_ids"] = ["lidarbc:5:999"]

    plan = _plan_copy(tmp_path, mutate=mutate)
    with pytest.raises(LidarProductError, match="outside the selection"):
        build_lidar_product_bundle(
            selection_manifest_path=SELECTION_MANIFEST,
            product_plan_path=plan,
            output_dir=tmp_path / "bundle",
        )


def test_build_rejects_reprojected_product(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        products = payload["products"]
        assert isinstance(products, list)
        first = products[0]
        assert isinstance(first, dict)
        first["crs"] = "EPSG:4326"

    plan = _plan_copy(tmp_path, mutate=mutate)
    with pytest.raises(LidarProductError, match="silent reprojection"):
        build_lidar_product_bundle(
            selection_manifest_path=SELECTION_MANIFEST,
            product_plan_path=plan,
            output_dir=tmp_path / "bundle",
        )


def test_build_rejects_inconsistent_derived_flag(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        products = payload["products"]
        assert isinstance(products, list)
        first = products[0]
        assert isinstance(first, dict)
        first["derived"] = True

    plan = _plan_copy(tmp_path, mutate=mutate)
    with pytest.raises(LidarProductError, match="inconsistent"):
        build_lidar_product_bundle(
            selection_manifest_path=SELECTION_MANIFEST,
            product_plan_path=plan,
            output_dir=tmp_path / "bundle",
        )


def test_build_rejects_selection_wrong_licence(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        source = payload["source"]
        assert isinstance(source, dict)
        source["licence_id"] = "Access Only"

    selection = _selection_copy(tmp_path, mutate=mutate)
    with pytest.raises(LidarProductError, match="OGL-BC"):
        build_lidar_product_bundle(
            selection_manifest_path=selection,
            product_plan_path=_plan_copy(tmp_path),
            output_dir=tmp_path / "bundle",
        )


def test_build_rejects_selection_without_tiles(tmp_path: Path) -> None:
    def mutate(payload: dict[str, object]) -> None:
        payload["tiles"] = []

    selection = _selection_copy(tmp_path, mutate=mutate)
    with pytest.raises(LidarProductError, match="no tiles"):
        build_lidar_product_bundle(
            selection_manifest_path=selection,
            product_plan_path=_plan_copy(tmp_path),
            output_dir=tmp_path / "bundle",
        )


def test_validate_bundle_is_valid(tmp_path: Path) -> None:
    result = _build(tmp_path)

    report = validate_lidar_product_bundle(
        result.bundle_dir,
        checked_utc=GENERATED_UTC,
    )

    assert report.is_valid
    assert report.errors == ()
    assert report.warnings == ()
    assert report.bundle_id == result.manifest.bundle_id
    assert report.product_count == 4
    assert report.to_dict()["is_valid"] is True


def test_validate_reports_missing_manifest(tmp_path: Path) -> None:
    report = validate_lidar_product_bundle(tmp_path / "missing")

    assert not report.is_valid
    assert "manifest.json" in report.errors[0]


def test_validate_detects_product_tampering(tmp_path: Path) -> None:
    result = _build(tmp_path)
    artifact = result.bundle_dir / "products/dem__01__dem.asc"
    artifact.write_text("tampered")

    report = validate_lidar_product_bundle(result.bundle_dir)

    assert not report.is_valid
    assert any("size mismatch" in error for error in report.errors)
    assert any("checksum mismatch" in error for error in report.errors)


def test_validate_detects_missing_product(tmp_path: Path) -> None:
    result = _build(tmp_path)
    (result.bundle_dir / "products/dsm__02__dsm.asc").unlink()

    report = validate_lidar_product_bundle(result.bundle_dir)

    assert not report.is_valid
    assert any("Missing product artifact" in error for error in report.errors)


def test_validate_detects_selection_provenance_tampering(tmp_path: Path) -> None:
    result = _build(tmp_path)
    provenance = _read_json(result.selection_path)
    provenance["generated_utc"] = "2026-10-26T00:00:00+00:00"
    _write_json(result.selection_path, provenance)

    report = validate_lidar_product_bundle(result.bundle_dir)

    assert not report.is_valid
    assert any("digest does not match" in error for error in report.errors)


def test_validate_detects_manifest_source_mismatch(tmp_path: Path) -> None:
    result = _build(tmp_path)
    manifest = _read_json(result.manifest_path)
    source = manifest["source"]
    assert isinstance(source, dict)
    source["licence_id"] = "Access Only"
    _write_json(result.manifest_path, manifest)

    report = validate_lidar_product_bundle(result.bundle_dir)

    assert not report.is_valid
    assert any("licence_id does not match" in error for error in report.errors)


def test_validate_detects_summary_and_consumer_contract_errors(tmp_path: Path) -> None:
    result = _build(tmp_path)
    manifest = _read_json(result.manifest_path)
    summary = manifest["summary"]
    assert isinstance(summary, dict)
    summary["product_count"] = 99
    contract = manifest["consumer_contract"]
    assert isinstance(contract, dict)
    del contract["pin_rule"]
    _write_json(result.manifest_path, manifest)

    report = validate_lidar_product_bundle(result.bundle_dir)

    assert not report.is_valid
    assert any("summary product_count" in error for error in report.errors)
    assert any("pin_rule" in error for error in report.errors)


def test_validate_detects_bad_product_metadata(tmp_path: Path) -> None:
    result = _build(tmp_path)
    manifest = _read_json(result.manifest_path)
    products = manifest["products"]
    assert isinstance(products, list)
    first = products[0]
    assert isinstance(first, dict)
    first["source_tile_ids"] = ["lidarbc:5:999"]
    first["crs"] = "EPSG:4326"
    first["resolution_m"] = None
    first["derived"] = True
    _write_json(result.manifest_path, manifest)

    report = validate_lidar_product_bundle(result.bundle_dir)

    assert not report.is_valid
    assert any("unknown source" in error for error in report.errors)
    assert any("CRS" in error for error in report.errors)
    assert any("missing resolution_m" in error for error in report.errors)
    assert any("inconsistent derived" in error for error in report.errors)


def test_load_plan_rejects_bad_schema(tmp_path: Path) -> None:
    payload = _read_json(PRODUCT_PLAN)
    payload["schema_version"] = "bad"
    path = _write_json(tmp_path / "plan.json", payload)

    with pytest.raises(LidarProductError, match="Unsupported"):
        load_lidar_product_plan(path)


def test_cli_bundle_and_inspect(tmp_path: Path) -> None:
    runner = CliRunner()
    bundle_dir = tmp_path / "bundle"

    result = runner.invoke(
        app,
        [
            "lidar",
            "bundle",
            "--selection-manifest",
            str(SELECTION_MANIFEST),
            "--product-plan",
            str(PRODUCT_PLAN),
            "--output-dir",
            str(bundle_dir),
            "--generated-utc",
            GENERATED_UTC,
        ],
    )

    assert result.exit_code == 0, result.output
    assert "LiDAR product bundle built" in result.output
    assert "bundle_id: lidarbc-" in result.output

    inspect = runner.invoke(app, ["lidar", "inspect", str(bundle_dir)])
    assert inspect.exit_code == 0, inspect.output
    assert "LiDAR product bundle is valid" in inspect.output

    inspect_json = runner.invoke(
        app,
        ["lidar", "inspect", str(bundle_dir), "--json"],
    )
    assert inspect_json.exit_code == 0, inspect_json.output
    assert json.loads(inspect_json.stdout)["is_valid"] is True


def test_cli_inspect_fails_for_invalid_bundle(tmp_path: Path) -> None:
    result = _build(tmp_path)
    (result.bundle_dir / "products/dem__01__dem.asc").write_text("tampered")

    inspect = CliRunner().invoke(app, ["lidar", "inspect", str(result.bundle_dir)])

    assert inspect.exit_code == 1
    assert "LiDAR product bundle is invalid" in inspect.output


def test_cli_bundle_reports_plan_errors(tmp_path: Path) -> None:
    plan = _plan_copy(tmp_path)
    payload = _read_json(plan)
    payload["schema_version"] = "bad"
    _write_json(plan, payload)

    result = CliRunner().invoke(
        app,
        [
            "lidar",
            "bundle",
            "--selection-manifest",
            str(SELECTION_MANIFEST),
            "--product-plan",
            str(plan),
            "--output-dir",
            str(tmp_path / "bundle"),
        ],
    )

    assert result.exit_code == 1
    assert "LiDAR bundle error" in result.output


def test_lidar_help_renders() -> None:
    result = CliRunner().invoke(app, ["lidar", "--help"])

    assert result.exit_code == 0
    assert "bundle" in result.stdout
    assert "inspect" in result.stdout
