from __future__ import annotations

import json
from pathlib import Path

import pytest

from femic.lidar import materialization
from femic.lidar.materialization import (
    LidarMaterializationError,
    LidarMaterializationTile,
    materialize_lidar_selection,
    plan_lidar_materialization,
    validate_lidar_materialization,
    write_lidar_materialization_manifest,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "lidar"
SELECTION_MANIFEST = FIXTURE_ROOT / "selection_manifest.json"
GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def _selection(tmp_path: Path, *, tile_count: int = 1) -> Path:
    payload = _read(SELECTION_MANIFEST)
    source_root = tmp_path / "source"
    source_root.mkdir(parents=True, exist_ok=True)
    tiles = payload["tiles"]
    assert isinstance(tiles, list)
    selected = tiles[:tile_count]
    for index, item in enumerate(selected):
        assert isinstance(item, dict)
        source = source_root / f"source_{index}.bin"
        source.write_bytes(f"tile-{index}-payload".encode())
        item["filename"] = f"tile_{index}.bin"
        item["download_url"] = source.as_uri()
        item["acquisition_year"] = 2023
    payload["tiles"] = selected
    summary = payload["summary"]
    assert isinstance(summary, dict)
    summary["tile_count"] = len(selected)
    return _write(tmp_path / "selection.json", payload)


def _materialize(tmp_path: Path, selection: Path, **kwargs: object) -> object:
    return materialize_lidar_selection(
        selection_manifest_path=selection,
        output_root=tmp_path / "data",
        generated_utc=GENERATED_UTC,
        **kwargs,
    )


def test_materialize_rejects_invalid_limits(tmp_path: Path) -> None:
    with pytest.raises(LidarMaterializationError, match="max_tiles"):
        materialize_lidar_selection(
            selection_manifest_path=tmp_path / "missing.json",
            output_root=tmp_path / "data",
            max_tiles=0,
        )
    with pytest.raises(LidarMaterializationError, match="timeout_sec"):
        materialize_lidar_selection(
            selection_manifest_path=tmp_path / "missing.json",
            output_root=tmp_path / "data",
            timeout_sec=0,
        )


def test_materialize_rejects_manifest_path_escape(tmp_path: Path) -> None:
    selection = _selection(tmp_path)
    manifest = plan_lidar_materialization(selection, generated_utc=GENERATED_UTC)
    path = write_lidar_materialization_manifest(
        manifest,
        tmp_path / "data" / "materialization.json",
    )
    payload = _read(path)
    tiles = payload["tiles"]
    assert isinstance(tiles, list)
    first = tiles[0]
    assert isinstance(first, dict)
    first["relative_path"] = "../escape.bin"
    _write(path, payload)

    with pytest.raises(LidarMaterializationError, match="escapes"):
        _materialize(tmp_path, selection)


def test_materialize_reports_size_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _selection(tmp_path)

    def fake_download(
        url: str,
        partial_path: Path,
        *,
        timeout_sec: float,
    ) -> materialization._DownloadOutcome:
        partial_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path.write_bytes(b"short")
        return materialization._DownloadOutcome(
            resumed_from_bytes=0,
            expected_size_bytes=999,
            remote_etag='"etag"',
        )

    monkeypatch.setattr(materialization, "_download_to_partial", fake_download)
    result = _materialize(tmp_path, selection)

    assert result.failed_count == 1
    assert result.manifest.tiles[0].status == "failed"
    assert "size mismatch" in (result.manifest.tiles[0].last_error or "")


def test_materialize_counts_resumed_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _selection(tmp_path)

    def fake_download(
        url: str,
        partial_path: Path,
        *,
        timeout_sec: float,
    ) -> materialization._DownloadOutcome:
        partial_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path.write_bytes(b"tile-0-payload")
        return materialization._DownloadOutcome(
            resumed_from_bytes=2,
            expected_size_bytes=len(b"tile-0-payload"),
            remote_etag='"etag"',
        )

    monkeypatch.setattr(materialization, "_download_to_partial", fake_download)
    result = _materialize(tmp_path, selection)

    assert result.downloaded_count == 1
    assert result.resumed_count == 1
    assert result.manifest.tiles[0].remote_etag == '"etag"'


def test_validate_manifest_path_escape_missing_sha_and_size(tmp_path: Path) -> None:
    selection = _selection(tmp_path, tile_count=2)
    result = _materialize(tmp_path, selection)
    payload = _read(result.manifest_path)
    tiles = payload["tiles"]
    assert isinstance(tiles, list)
    first = tiles[0]
    second = tiles[1]
    assert isinstance(first, dict)
    assert isinstance(second, dict)
    first["relative_path"] = "../escape.bin"
    second["sha256"] = None
    second["size_bytes"] = 1
    _write(result.manifest_path, payload)

    report = validate_lidar_materialization(result.manifest_path)

    assert not report.is_valid
    assert any("escapes" in error for error in report.errors)
    assert any("no SHA-256" in error for error in report.errors)
    assert any("size mismatch" in error for error in report.errors)


def test_validate_empty_tiles(tmp_path: Path) -> None:
    selection = _selection(tmp_path)
    manifest = plan_lidar_materialization(selection, generated_utc=GENERATED_UTC)
    path = write_lidar_materialization_manifest(
        manifest,
        tmp_path / "data" / "materialization.json",
    )
    payload = _read(path)
    payload["tiles"] = []
    _write(path, payload)

    report = validate_lidar_materialization(path)

    assert not report.is_valid
    assert any("no tiles" in error for error in report.errors)


def test_selection_rejects_bad_source_crs_bbox_and_empty_tiles(
    tmp_path: Path,
) -> None:
    selection = _selection(tmp_path)

    def mutate(key: str, value: object) -> None:
        payload = _read(selection)
        source = payload["source"]
        assert isinstance(source, dict)
        source[key] = value
        _write(selection, payload)

    mutate("source_id", "other")
    with pytest.raises(LidarMaterializationError, match="only 'lidarbc'"):
        plan_lidar_materialization(selection)

    _write(selection, _read(SELECTION_MANIFEST))
    mutate("native_crs", "EPSG:4326")
    with pytest.raises(LidarMaterializationError, match="native CRS"):
        plan_lidar_materialization(selection)

    payload = _read(SELECTION_MANIFEST)
    aoi = payload["aoi"]
    assert isinstance(aoi, dict)
    aoi["bbox_epsg3005"] = [0, 0, 0, 1]
    _write(selection, payload)
    with pytest.raises(LidarMaterializationError, match="Invalid selection AOI"):
        plan_lidar_materialization(selection)

    payload = _read(SELECTION_MANIFEST)
    payload["tiles"] = []
    _write(selection, payload)
    with pytest.raises(LidarMaterializationError, match="no tiles"):
        plan_lidar_materialization(selection)


def test_manifest_loader_rejects_bad_schema_and_status(tmp_path: Path) -> None:
    path = tmp_path / "materialization.json"
    _write(
        path,
        {
            "schema_version": "bad",
            "tiles": [],
        },
    )
    with pytest.raises(LidarMaterializationError, match="Unsupported"):
        materialization._load_manifest(path)

    _write(
        path,
        {
            "schema_version": materialization.LIDAR_MATERIALIZATION_SCHEMA_VERSION,
            "tiles": [{"status": "weird"}],
        },
    )
    with pytest.raises(LidarMaterializationError, match="unsupported status"):
        materialization._load_manifest(path)


def test_manifest_tile_set_mismatch(tmp_path: Path) -> None:
    selection = _selection(tmp_path, tile_count=2)
    result = _materialize(tmp_path, selection)
    payload = _read(result.manifest_path)
    tiles = payload["tiles"]
    assert isinstance(tiles, list)
    payload["tiles"] = tiles[:1]
    _write(result.manifest_path, payload)

    with pytest.raises(LidarMaterializationError, match="tile set"):
        _materialize(tmp_path, selection)


def test_private_file_and_path_helpers(tmp_path: Path) -> None:
    tile = LidarMaterializationTile(
        tile_id="t",
        product="dem",
        layer_id=5,
        filename="tile.bin",
        download_url="https://example.test/tile.bin",
        relative_path="tile.bin",
        status="verified",
        size_bytes=1,
        sha256=None,
    )
    path = tmp_path / "tile.bin"
    path.write_bytes(b"x")

    assert not materialization._file_matches(path, tile)
    assert materialization._resolve_member(tmp_path, "../escape") is None
    assert materialization._safe_component("###") == "unknown"
    assert materialization._safe_filename("###") == "artifact"


def test_json_and_scalar_helpers(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(LidarMaterializationError, match="Unable to read"):
        materialization._read_json_object(missing, context="test")

    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json")
    with pytest.raises(LidarMaterializationError, match="Invalid JSON"):
        materialization._read_json_object(invalid, context="test")

    array = tmp_path / "array.json"
    array.write_text("[]")
    with pytest.raises(LidarMaterializationError, match="JSON object"):
        materialization._read_json_object(array, context="test")

    with pytest.raises(LidarMaterializationError, match="must be an object"):
        materialization._required_mapping({"value": "x"}, "value", context="test")
    assert materialization._optional_mapping(None, context="test") == {}
    with pytest.raises(LidarMaterializationError, match="must be an object"):
        materialization._optional_mapping("x", context="test")
    with pytest.raises(LidarMaterializationError, match="must be a list"):
        materialization._required_list({"value": "x"}, "value", context="test")
    with pytest.raises(LidarMaterializationError, match="must be an integer"):
        materialization._required_int({"value": "x"}, "value", context="test")
    assert materialization._optional_int(True) is None
    assert materialization._optional_int("3") == 3
    assert materialization._optional_int("x") is None
    assert materialization._optional_int(object()) is None
    with pytest.raises(LidarMaterializationError, match="must be a list"):
        materialization._required_str_list("x", context="test")
    with pytest.raises(LidarMaterializationError, match="non-empty strings"):
        materialization._required_str_list([""], context="test")
    with pytest.raises(LidarMaterializationError, match="must not be empty"):
        materialization._required_str_list([], context="test")
