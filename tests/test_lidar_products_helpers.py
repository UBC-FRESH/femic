from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from pathlib import Path

import pytest

from femic.lidar import products
from femic.lidar.products import (
    LidarProductBuildResult,
    LidarProductError,
    LidarProductValidation,
    build_lidar_product_bundle,
    validate_lidar_product_bundle,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "lidar"
SELECTION_MANIFEST = FIXTURE_ROOT / "selection_manifest.json"
PRODUCT_PLAN = FIXTURE_ROOT / "product_plan.json"
GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _as_dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def _as_list(value: object) -> list[object]:
    assert isinstance(value, list)
    return value


def _read(path: Path) -> dict[str, object]:
    return _as_dict(json.loads(path.read_text(encoding="utf-8")))


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _build(
    base: Path,
    *,
    name: str = "bundle",
    overwrite: bool = False,
) -> LidarProductBuildResult:
    return build_lidar_product_bundle(
        selection_manifest_path=SELECTION_MANIFEST,
        product_plan_path=PRODUCT_PLAN,
        output_dir=base / name,
        generated_utc=GENERATED_UTC,
        overwrite=overwrite,
    )


def _plan(tmp_path: Path, mutate: Callable[[dict[str, object]], None]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    payload = _read(PRODUCT_PLAN)
    for item in _as_list(payload["products"]):
        product = _as_dict(item)
        product["path"] = str(FIXTURE_ROOT / str(product["path"]))
    mutate(payload)
    return _write(tmp_path / "product_plan.json", payload)


def _selection(tmp_path: Path, mutate: Callable[[dict[str, object]], None]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    payload = _read(SELECTION_MANIFEST)
    mutate(payload)
    return _write(tmp_path / "selection.json", payload)


def _mutate_manifest(
    tmp_path: Path,
    mutate: Callable[[dict[str, object], LidarProductBuildResult], None],
) -> LidarProductValidation:
    result = _build(tmp_path)
    manifest = _read(result.manifest_path)
    mutate(manifest, result)
    _write(result.manifest_path, manifest)
    return validate_lidar_product_bundle(result.bundle_dir)


def _build_with_plan(tmp_path: Path, plan: Path) -> LidarProductBuildResult:
    return build_lidar_product_bundle(
        selection_manifest_path=SELECTION_MANIFEST,
        product_plan_path=plan,
        output_dir=tmp_path / "bundle",
        generated_utc=GENERATED_UTC,
    )


def _build_with_selection(tmp_path: Path, selection: Path) -> LidarProductBuildResult:
    return build_lidar_product_bundle(
        selection_manifest_path=selection,
        product_plan_path=PRODUCT_PLAN,
        output_dir=tmp_path / "bundle",
        generated_utc=GENERATED_UTC,
    )


def test_build_result_to_dict_and_empty_output_directory(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir()

    result = _build(tmp_path)

    payload = result.to_dict()
    assert payload["bundle_dir"] == str(result.bundle_dir)
    assert payload["manifest"]["summary"]["product_count"] == 4
    assert result.bundle_dir == output


def test_build_cleans_temp_directory_after_copy_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_copy(source: Path, destination: Path) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr(products.shutil, "copyfile", fail_copy)

    with pytest.raises(OSError, match="copy failed"):
        _build(tmp_path)

    assert not (tmp_path / "bundle").exists()
    assert not any(path.name.startswith(".bundle.") for path in tmp_path.iterdir())


def test_build_rejects_output_path_that_is_a_file(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.write_text("not a directory")

    with pytest.raises(LidarProductError, match="not a directory"):
        _build(tmp_path)


def test_build_rejects_unreadable_or_foreign_bundle_on_overwrite(
    tmp_path: Path,
) -> None:
    output = tmp_path / "bundle"
    output.mkdir()
    (output / "manifest.json").write_text("not-json")

    with pytest.raises(LidarProductError, match="unreadable bundle"):
        _build(tmp_path, name="bundle", overwrite=True)

    (output / "manifest.json").write_text('{"schema_version": "other"}')
    with pytest.raises(LidarProductError, match="non-FEMIC-LiDAR bundle"):
        _build(tmp_path, name="bundle", overwrite=True)


def test_validate_manifest_schema_and_identity_errors(tmp_path: Path) -> None:
    def mutate(manifest: dict[str, object], result: LidarProductBuildResult) -> None:
        manifest["schema_version"] = "bad"
        del manifest["bundle_id"]
        del manifest["bundle_version"]

    report = _mutate_manifest(tmp_path, mutate)

    assert not report.is_valid
    assert any(
        "Unsupported product manifest schema" in error for error in report.errors
    )
    assert any("bundle_id" in error for error in report.errors)
    assert any("bundle_version" in error for error in report.errors)


def test_validate_missing_selection_provenance(tmp_path: Path) -> None:
    result = _build(tmp_path)
    result.selection_path.unlink()

    report = validate_lidar_product_bundle(result.bundle_dir)

    assert not report.is_valid
    assert any("Missing selection provenance" in error for error in report.errors)


def test_validate_invalid_selection_provenance(tmp_path: Path) -> None:
    result = _build(tmp_path)
    provenance = _read(result.selection_path)
    source = _as_dict(provenance["source"])
    source["licence_id"] = "Access Only"
    _write(result.selection_path, provenance)

    manifest = _read(result.manifest_path)
    selection = _as_dict(manifest["selection"])
    selection["sha256"] = hashlib.sha256(
        products._canonical_json_bytes(provenance)
    ).hexdigest()
    _write(result.manifest_path, manifest)

    report = validate_lidar_product_bundle(result.bundle_dir)

    assert not report.is_valid
    assert any("Invalid selection provenance" in error for error in report.errors)


def test_validate_manifest_source_processing_and_contract_errors(
    tmp_path: Path,
) -> None:
    def mutate(manifest: dict[str, object], result: LidarProductBuildResult) -> None:
        source = _as_dict(manifest["source"])
        source["source_id"] = "other"
        source["native_crs"] = "EPSG:4326"
        processing = _as_dict(manifest["processing"])
        del processing["version"]
        contract = _as_dict(manifest["consumer_contract"])
        del contract["products_dir"]

    report = _mutate_manifest(tmp_path, mutate)

    assert not report.is_valid
    assert any("source_id does not match" in error for error in report.errors)
    assert any("native_crs does not match" in error for error in report.errors)
    assert any("processing.version" in error for error in report.errors)
    assert any("products_dir" in error for error in report.errors)


def test_validate_product_list_edge_cases(tmp_path: Path) -> None:
    def empty_products(
        manifest: dict[str, object], result: LidarProductBuildResult
    ) -> None:
        manifest["products"] = []

    report = _mutate_manifest(tmp_path / "empty", empty_products)
    assert not report.is_valid
    assert any("non-empty `products`" in error for error in report.errors)

    def non_object_and_missing_fields(
        manifest: dict[str, object], result: LidarProductBuildResult
    ) -> None:
        entries = _as_list(manifest["products"])
        entries.append("bad")
        _as_dict(entries[0]).pop("sha256")

    report = _mutate_manifest(tmp_path / "bad-entry", non_object_and_missing_fields)
    assert not report.is_valid
    assert any("is not an object" in error for error in report.errors)
    assert any("sha256" in error for error in report.errors)


def test_validate_duplicate_product_identity(tmp_path: Path) -> None:
    def mutate(manifest: dict[str, object], result: LidarProductBuildResult) -> None:
        entries = _as_list(manifest["products"])
        first = _as_dict(entries[0])
        second = _as_dict(entries[1])
        second["product_id"] = first["product_id"]
        second["relative_path"] = first["relative_path"]

    report = _mutate_manifest(tmp_path, mutate)

    assert not report.is_valid
    assert any("Duplicate product_id" in error for error in report.errors)
    assert any("Duplicate product path" in error for error in report.errors)


def test_validate_product_metadata_errors(tmp_path: Path) -> None:
    def mutate(manifest: dict[str, object], result: LidarProductBuildResult) -> None:
        entries = _as_list(manifest["products"])
        first = _as_dict(entries[0])
        first["product"] = "radar"
        first["derived"] = True
        first["licence_id"] = "Access Only"
        _as_dict(entries[1])["resolution_m"] = None
        _as_dict(entries[2])["resolution_m"] = 0.0

    report = _mutate_manifest(tmp_path, mutate)

    assert not report.is_valid
    assert any("Unsupported product kind" in error for error in report.errors)
    assert any("missing resolution_m" in error for error in report.errors)
    assert any("non-positive resolution_m" in error for error in report.errors)
    assert any("inconsistent derived" in error for error in report.errors)
    assert any("licence" in error for error in report.errors)


def test_validate_path_escape_and_summary_bytes(tmp_path: Path) -> None:
    def mutate(manifest: dict[str, object], result: LidarProductBuildResult) -> None:
        first = _as_dict(_as_list(manifest["products"])[0])
        first["relative_path"] = "../outside.tif"
        summary = _as_dict(manifest["summary"])
        summary["total_bytes"] = 0

    report = _mutate_manifest(tmp_path, mutate)

    assert not report.is_valid
    assert any("escapes the bundle" in error for error in report.errors)
    assert any("total_bytes" in error for error in report.errors)


def test_validate_derived_without_lineage_warns(tmp_path: Path) -> None:
    def mutate(manifest: dict[str, object], result: LidarProductBuildResult) -> None:
        for item in _as_list(manifest["products"]):
            product = _as_dict(item)
            if product["product"] == "chm":
                product["lineage"] = []

    report = _mutate_manifest(tmp_path, mutate)

    assert report.is_valid
    assert any("no lineage notes" in warning for warning in report.warnings)


def test_validate_malformed_summary_is_reported(tmp_path: Path) -> None:
    def mutate(manifest: dict[str, object], result: LidarProductBuildResult) -> None:
        manifest["summary"] = "bad"

    report = _mutate_manifest(tmp_path, mutate)

    assert not report.is_valid
    assert any("summary must be an object" in error for error in report.errors)


def test_validate_non_object_manifest(tmp_path: Path) -> None:
    result = _build(tmp_path)
    result.manifest_path.write_text("[]")

    report = validate_lidar_product_bundle(result.bundle_dir)

    assert not report.is_valid
    assert any("must be a JSON object" in error for error in report.errors)


def test_plan_validation_errors(tmp_path: Path) -> None:
    def no_products(payload: dict[str, object]) -> None:
        payload["products"] = []

    with pytest.raises(LidarProductError, match="at least one"):
        _build_with_plan(tmp_path / "empty", _plan(tmp_path / "empty", no_products))

    def unsupported(payload: dict[str, object]) -> None:
        _as_dict(_as_list(payload["products"])[0])["product"] = "radar"

    with pytest.raises(LidarProductError, match="Unsupported product kind"):
        _build_with_plan(
            tmp_path / "unsupported",
            _plan(tmp_path / "unsupported", unsupported),
        )

    def missing_source(payload: dict[str, object]) -> None:
        _as_dict(_as_list(payload["products"])[0])["path"] = "missing.tif"

    with pytest.raises(LidarProductError, match="does not exist"):
        _build_with_plan(
            tmp_path / "missing", _plan(tmp_path / "missing", missing_source)
        )

    def reused_source(payload: dict[str, object]) -> None:
        entries = _as_list(payload["products"])
        _as_dict(entries[1])["path"] = _as_dict(entries[0])["path"]

    with pytest.raises(LidarProductError, match="reused"):
        _build_with_plan(tmp_path / "reused", _plan(tmp_path / "reused", reused_source))

    def missing_resolution(payload: dict[str, object]) -> None:
        _as_dict(_as_list(payload["products"])[0])["resolution_m"] = None

    with pytest.raises(LidarProductError, match="must declare resolution_m"):
        _build_with_plan(
            tmp_path / "resolution",
            _plan(tmp_path / "resolution", missing_resolution),
        )

    def bad_resolution(payload: dict[str, object]) -> None:
        _as_dict(_as_list(payload["products"])[0])["resolution_m"] = 0

    with pytest.raises(LidarProductError, match="positive resolution_m"):
        _build_with_plan(
            tmp_path / "bad-resolution",
            _plan(tmp_path / "bad-resolution", bad_resolution),
        )

    def empty_tiles(payload: dict[str, object]) -> None:
        _as_dict(_as_list(payload["products"])[0])["source_tile_ids"] = []

    with pytest.raises(LidarProductError, match="must not be empty"):
        _build_with_plan(
            tmp_path / "empty-tiles",
            _plan(tmp_path / "empty-tiles", empty_tiles),
        )

    def empty_layers(payload: dict[str, object]) -> None:
        _as_dict(_as_list(payload["products"])[0])["source_layer_ids"] = []

    with pytest.raises(LidarProductError, match="must not be empty"):
        _build_with_plan(
            tmp_path / "empty-layers",
            _plan(tmp_path / "empty-layers", empty_layers),
        )


def test_selection_contract_errors(tmp_path: Path) -> None:
    def bad_schema(payload: dict[str, object]) -> None:
        payload["schema_version"] = "bad"

    with pytest.raises(LidarProductError, match="Unsupported selection"):
        _build_with_selection(
            tmp_path / "schema",
            _selection(tmp_path / "schema", bad_schema),
        )

    def bad_source(payload: dict[str, object]) -> None:
        _as_dict(payload["source"])["source_id"] = "other"

    with pytest.raises(LidarProductError, match="only 'lidarbc'"):
        _build_with_selection(
            tmp_path / "source",
            _selection(tmp_path / "source", bad_source),
        )

    def bad_crs(payload: dict[str, object]) -> None:
        _as_dict(payload["source"])["native_crs"] = "EPSG:4326"

    with pytest.raises(LidarProductError, match="native CRS"):
        _build_with_selection(
            tmp_path / "crs",
            _selection(tmp_path / "crs", bad_crs),
        )

    def bad_bbox(payload: dict[str, object]) -> None:
        _as_dict(payload["aoi"])["bbox_epsg3005"] = [0, 0, 0, 1]

    with pytest.raises(LidarProductError, match="Invalid selection AOI"):
        _build_with_selection(
            tmp_path / "bbox",
            _selection(tmp_path / "bbox", bad_bbox),
        )

    def duplicate_tiles(payload: dict[str, object]) -> None:
        tiles = _as_list(payload["tiles"])
        _as_dict(tiles[1])["tile_id"] = _as_dict(tiles[0])["tile_id"]

    with pytest.raises(LidarProductError, match="duplicate tile IDs"):
        _build_with_selection(
            tmp_path / "duplicates",
            _selection(tmp_path / "duplicates", duplicate_tiles),
        )


def test_optional_str_behaviour() -> None:
    assert products._optional_str(None) is None
    assert products._optional_str("  ") is None
    assert products._optional_str(1) is None
    assert products._optional_str(" value ") == "value"


def test_required_int_behaviour() -> None:
    assert products._required_int({"value": 2}, "value", context="test") == 2
    assert products._required_int({"value": "2"}, "value", context="test") == 2
    with pytest.raises(LidarProductError, match="integer"):
        products._required_int({"value": True}, "value", context="test")
    with pytest.raises(LidarProductError, match="integer"):
        products._required_int({"value": "x"}, "value", context="test")
    with pytest.raises(LidarProductError, match="integer"):
        products._required_int({"value": 1.5}, "value", context="test")


def test_required_string_list_behaviour() -> None:
    assert products._required_str_list([" a ", "b"], context="test") == ("a", "b")
    with pytest.raises(LidarProductError, match="must be a list"):
        products._required_str_list("a", context="test")
    with pytest.raises(LidarProductError, match="non-empty strings"):
        products._required_str_list([""], context="test")
    with pytest.raises(LidarProductError, match="must not be empty"):
        products._required_str_list([], context="test")


def test_required_int_list_behaviour() -> None:
    assert products._required_int_list([1, "2"], context="test") == (1, 2)
    with pytest.raises(LidarProductError, match="must be a list"):
        products._required_int_list("1", context="test")
    with pytest.raises(LidarProductError, match="must be integers"):
        products._required_int_list([True], context="test")
    with pytest.raises(LidarProductError, match="must be integers"):
        products._required_int_list(["x"], context="test")
    with pytest.raises(LidarProductError, match="must be integers"):
        products._required_int_list([1.5], context="test")
    with pytest.raises(LidarProductError, match="must not be empty"):
        products._required_int_list([], context="test")


def test_optional_string_list_behaviour() -> None:
    assert products._optional_str_list(None, context="test") == ()
    assert products._optional_str_list([" a ", ""], context="test") == ("a",)
    with pytest.raises(LidarProductError, match="must be a list"):
        products._optional_str_list("a", context="test")
    with pytest.raises(LidarProductError, match="must be strings"):
        products._optional_str_list([1], context="test")


def test_optional_numeric_and_boolean_behaviour() -> None:
    assert products._optional_float(None) is None
    assert products._optional_float(1) == 1.0
    assert products._optional_float("1.5") == 1.5
    assert products._optional_bool(None) is False
    assert products._optional_bool(True) is True
    with pytest.raises(LidarProductError, match="boolean"):
        products._optional_float(True)
    with pytest.raises(LidarProductError, match="Invalid numeric"):
        products._optional_float("x")
    with pytest.raises(LidarProductError, match="Invalid numeric"):
        products._optional_float(object())
    with pytest.raises(LidarProductError, match="finite"):
        products._optional_float(math.inf)
    with pytest.raises(LidarProductError, match="true or false"):
        products._optional_bool("true")


def test_mapping_and_list_helpers() -> None:
    assert products._required_mapping({"value": {"a": 1}}, "value", context="test") == {
        "a": 1
    }
    assert products._optional_mapping(None, context="test") == {}
    assert products._required_list({"value": [1]}, "value", context="test") == [1]
    assert products._required_str({"value": " x "}, "value", context="test") == "x"
    with pytest.raises(LidarProductError, match="must be an object"):
        products._required_mapping({"value": "x"}, "value", context="test")
    with pytest.raises(LidarProductError, match="must be an object"):
        products._optional_mapping("x", context="test")
    with pytest.raises(LidarProductError, match="must be a list"):
        products._required_list({"value": "x"}, "value", context="test")
    with pytest.raises(LidarProductError, match="non-empty string"):
        products._required_str({"value": " "}, "value", context="test")


def test_json_reader_and_path_helpers(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(LidarProductError, match="Unable to read"):
        products._read_json_object(missing, context="test")

    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json")
    with pytest.raises(LidarProductError, match="Invalid JSON"):
        products._read_json_object(invalid, context="test")

    array = tmp_path / "array.json"
    array.write_text("[]")
    with pytest.raises(LidarProductError, match="JSON object"):
        products._read_json_object(array, context="test")

    assert products._artifact_relative_path("dem", Path("###"), 1).endswith(
        "dem__01__artifact"
    )
    root = tmp_path / "bundle"
    root.mkdir()
    assert products._resolve_bundle_member(root, "../escape") is None
