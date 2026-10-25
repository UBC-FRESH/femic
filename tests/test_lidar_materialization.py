from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar, Self

import pytest
from typer.testing import CliRunner

from femic.cli.main import app
from femic.lidar import materialization
from femic.lidar.materialization import (
    LidarMaterializationError,
    LidarMaterializationManifest,
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


def _selection_with_files(
    tmp_path: Path,
    *,
    tile_count: int = 2,
) -> Path:
    payload = _read(SELECTION_MANIFEST)
    source_root = tmp_path / "source"
    source_root.mkdir(parents=True)
    tiles = payload["tiles"]
    assert isinstance(tiles, list)
    selected = tiles[:tile_count]
    for index, item in enumerate(selected):
        assert isinstance(item, dict)
        source_path = source_root / f"source_{index}.bin"
        source_path.write_bytes(f"tile-{index}-payload".encode())
        item["filename"] = f"tile_{index}.bin"
        item["download_url"] = source_path.as_uri()
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


def test_plan_materialization_is_pending_and_portable(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path)

    manifest = plan_lidar_materialization(selection, generated_utc=GENERATED_UTC)

    assert manifest.tile_count == 2
    assert manifest.verified_count == 0
    assert manifest.pending_count == 2
    assert not manifest.is_complete
    assert manifest.storage["partial_suffix"] == ".part"
    assert manifest.tiles[0].relative_path.startswith("lidarbc/")
    assert "layer_" in manifest.tiles[0].relative_path
    assert "2023" in manifest.tiles[0].relative_path
    payload = manifest.to_dict()
    assert payload["summary"]["pending_count"] == 2
    assert payload["selection"]["sha256"]

    path = write_lidar_materialization_manifest(
        manifest,
        tmp_path / "data" / "materialization.json",
    )
    assert path.is_file()
    report = validate_lidar_materialization(path)
    assert report.is_valid
    assert not report.is_complete
    assert len(report.warnings) == 2


def test_materialize_downloads_and_verifies_files(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path)

    result = _materialize(tmp_path, selection)

    assert result.downloaded_count == 2
    assert result.failed_count == 0
    assert result.manifest.is_complete
    assert result.manifest.verified_count == 2
    assert result.manifest_path.is_file()
    for tile in result.manifest.tiles:
        path = result.output_root / tile.relative_path
        assert path.is_file()
        assert tile.status == "verified"
        assert tile.sha256 == materialization._sha256_file(path)
        assert tile.size_bytes == path.stat().st_size
    report = validate_lidar_materialization(result.output_root)
    assert report.is_valid
    assert report.is_complete
    assert report.errors == ()


def test_materialize_skips_verified_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _selection_with_files(tmp_path)
    _materialize(tmp_path, selection)

    def fail_download(url: str, partial_path: Path, *, timeout_sec: float) -> object:
        raise AssertionError("verified files must not be downloaded again")

    monkeypatch.setattr(materialization, "_download_to_partial", fail_download)
    result = _materialize(tmp_path, selection)

    assert result.downloaded_count == 0
    assert result.skipped_count == 2
    assert result.manifest.is_complete


def test_materialize_redownloads_corrupted_file(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path)
    first = _materialize(tmp_path, selection)
    tile = next(tile for tile in first.manifest.tiles if tile.filename == "tile_0.bin")
    corrupted = first.output_root / tile.relative_path
    corrupted.write_text("tampered")

    second = _materialize(tmp_path, selection)

    assert second.downloaded_count == 1
    assert second.skipped_count == 1
    assert second.manifest.is_complete
    assert corrupted.read_text() == "tile-0-payload"


def test_materialize_resumes_partial_file(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path, tile_count=1)
    plan = plan_lidar_materialization(selection, generated_utc=GENERATED_UTC)
    relative = plan.tiles[0].relative_path
    partial = tmp_path / "data" / relative
    partial = partial.with_name(f"{partial.name}.part")
    partial.parent.mkdir(parents=True)
    partial.write_bytes(b"tile-0-")
    write_lidar_materialization_manifest(
        plan,
        tmp_path / "data" / "materialization.json",
    )

    result = _materialize(tmp_path, selection)

    assert result.manifest.is_complete
    assert result.manifest.tiles[0].resumed_from_bytes == 0
    assert not partial.exists()


def test_materialize_preserves_partial_on_failure_then_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _selection_with_files(tmp_path, tile_count=1)

    def fail_download(url: str, partial_path: Path, *, timeout_sec: float) -> object:
        partial_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path.write_bytes(b"tile-0-")
        raise LidarMaterializationError("network interrupted")

    monkeypatch.setattr(materialization, "_download_to_partial", fail_download)
    failed = _materialize(tmp_path, selection)

    assert failed.failed_count == 1
    assert failed.manifest.tiles[0].status == "partial"
    assert "network interrupted" in (failed.manifest.tiles[0].last_error or "")
    assert failed.manifest.tiles[0].last_attempt_utc

    monkeypatch.undo()
    completed = _materialize(tmp_path, selection)
    assert completed.manifest.is_complete
    assert completed.downloaded_count == 1


def test_materialize_marks_failure_without_partial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _selection_with_files(tmp_path, tile_count=1)

    def fail_download(url: str, partial_path: Path, *, timeout_sec: float) -> object:
        raise LidarMaterializationError("connection refused")

    monkeypatch.setattr(materialization, "_download_to_partial", fail_download)
    result = _materialize(tmp_path, selection, fail_fast=True)

    assert result.failed_count == 1
    assert result.manifest.tiles[0].status == "failed"
    assert result.manifest.pending_count == 0


def test_materialize_max_tiles_leaves_remaining_pending(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path)

    result = _materialize(tmp_path, selection, max_tiles=1)

    assert result.downloaded_count == 1
    assert result.manifest.verified_count == 1
    assert result.manifest.pending_count == 1
    assert not result.manifest.is_complete


def test_materialize_plan_only_writes_manifest_without_bytes(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path)

    result = _materialize(tmp_path, selection, plan_only=True)

    assert result.downloaded_count == 0
    assert result.manifest.pending_count == 2
    assert result.manifest_path.is_file()
    assert not (tmp_path / "data" / "lidarbc").exists()
    assert result.manifest_path.read_text().count('"status": "pending"') == 2


def test_materialize_rejects_changed_selection(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path)
    _materialize(tmp_path, selection)
    payload = _read(selection)
    payload["generated_utc"] = "2026-10-26T00:00:00+00:00"
    _write(selection, payload)

    with pytest.raises(LidarMaterializationError, match="does not match"):
        _materialize(tmp_path, selection)


def test_materialize_rejects_bad_selection_values(tmp_path: Path) -> None:
    def missing_url(payload: dict[str, object]) -> None:
        tiles = payload["tiles"]
        assert isinstance(tiles, list)
        tile = tiles[0]
        assert isinstance(tile, dict)
        del tile["download_url"]

    selection = _selection_with_files(tmp_path)
    payload = _read(selection)
    missing_url(payload)
    _write(selection, payload)
    with pytest.raises(LidarMaterializationError, match="download_url"):
        plan_lidar_materialization(selection)

    payload = _read(SELECTION_MANIFEST)
    payload["schema_version"] = "bad"
    _write(selection, payload)
    with pytest.raises(LidarMaterializationError, match="Unsupported selection"):
        plan_lidar_materialization(selection)

    payload = _read(SELECTION_MANIFEST)
    source = payload["source"]
    assert isinstance(source, dict)
    source["licence_id"] = "Access Only"
    _write(selection, payload)
    with pytest.raises(LidarMaterializationError, match="OGL-BC"):
        plan_lidar_materialization(selection)

    payload = _read(SELECTION_MANIFEST)
    tiles = payload["tiles"]
    assert isinstance(tiles, list)
    first = tiles[0]
    assert isinstance(first, dict)
    second = tiles[1]
    assert isinstance(second, dict)
    second["tile_id"] = first["tile_id"]
    _write(selection, payload)
    with pytest.raises(LidarMaterializationError, match="duplicate tile ID"):
        plan_lidar_materialization(selection)


def test_validate_detects_missing_and_tampered_files(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path)
    result = _materialize(tmp_path, selection)
    first_tile = next(
        tile for tile in result.manifest.tiles if tile.filename == "tile_0.bin"
    )
    second_tile = next(
        tile for tile in result.manifest.tiles if tile.filename == "tile_1.bin"
    )
    first = result.output_root / first_tile.relative_path
    second = result.output_root / second_tile.relative_path
    first.unlink()
    second.write_text("tampered")

    report = validate_lidar_materialization(result.manifest_path)

    assert not report.is_valid
    assert not report.is_complete
    assert any("missing" in error.lower() for error in report.errors)
    assert any("checksum mismatch" in error for error in report.errors)


def test_validate_missing_manifest(tmp_path: Path) -> None:
    report = validate_lidar_materialization(tmp_path / "missing.json")

    assert not report.is_valid
    assert "Unable to read" in report.errors[0]


def test_validate_can_skip_checksums(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path)
    result = _materialize(tmp_path, selection)

    report = validate_lidar_materialization(
        result.manifest_path,
        verify_checksums=False,
    )

    assert report.is_valid


def test_materialization_manifest_and_result_helpers(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path, tile_count=1)
    result = _materialize(tmp_path, selection)
    payload = result.to_dict()
    manifest_payload = result.manifest.to_dict()

    assert payload["downloaded_count"] == 1
    assert manifest_payload["summary"]["is_complete"] is True
    assert result.manifest.tile_count == 1
    assert result.manifest.total_bytes == result.manifest.tiles[0].size_bytes
    report_payload = validate_lidar_materialization(result.manifest_path).to_dict()
    assert report_payload["is_complete"] is True


def test_download_to_partial_handles_range_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    partial = tmp_path / "tile.bin.part"
    partial.write_bytes(b"ab")

    class FakeResponse:
        status = 206
        headers: ClassVar[dict[str, str]] = {
            "Content-Range": "bytes 2-5/6",
            "ETag": '"etag"',
        }

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            if self._done:
                return b""
            self._done = True
            return b"cdef"

        _done = False

    monkeypatch.setattr(
        materialization,
        "urlopen",
        lambda request, timeout: FakeResponse(),
    )

    outcome = materialization._download_to_partial(
        "https://example.test/tile.bin",
        partial,
        timeout_sec=1.0,
    )

    assert partial.read_bytes() == b"abcdef"
    assert outcome.resumed_from_bytes == 2
    assert outcome.expected_size_bytes == 6
    assert outcome.remote_etag == '"etag"'


def test_download_to_partial_restarts_when_server_ignores_range(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    partial = tmp_path / "tile.bin.part"
    partial.write_bytes(b"old")

    class FakeResponse:
        status = 200
        headers: ClassVar[dict[str, str]] = {"Content-Length": "3"}

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            if self._done:
                return b""
            self._done = True
            return b"new"

        _done = False

    monkeypatch.setattr(
        materialization,
        "urlopen",
        lambda request, timeout: FakeResponse(),
    )

    outcome = materialization._download_to_partial(
        "https://example.test/tile.bin",
        partial,
        timeout_sec=1.0,
    )

    assert partial.read_bytes() == b"new"
    assert outcome.resumed_from_bytes == 0
    assert outcome.expected_size_bytes == 3


def test_download_to_partial_rejects_empty_url_and_network_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(LidarMaterializationError, match="empty"):
        materialization._download_to_partial(
            " ",
            tmp_path / "tile.bin.part",
            timeout_sec=1.0,
        )

    def fail(request: object, timeout: float) -> object:
        raise OSError("offline")

    monkeypatch.setattr(materialization, "urlopen", fail)
    with pytest.raises(LidarMaterializationError, match="Unable to download"):
        materialization._download_to_partial(
            "https://example.test/tile.bin",
            tmp_path / "tile.bin.part",
            timeout_sec=1.0,
        )


def test_expected_size_parsing() -> None:
    assert materialization._expected_size({}, offset=0, status=200) is None
    assert (
        materialization._expected_size(
            {"Content-Length": "4"},
            offset=0,
            status=200,
        )
        == 4
    )
    assert (
        materialization._expected_size(
            {"Content-Length": "4"},
            offset=2,
            status=206,
        )
        == 6
    )
    assert (
        materialization._expected_size(
            {"Content-Range": "bytes 2-5/6"},
            offset=2,
            status=206,
        )
        == 6
    )
    assert (
        materialization._expected_size(
            {"Content-Range": "bytes 2-5/*"},
            offset=2,
            status=206,
        )
        is None
    )


def test_manifest_tile_record_requires_all_fields() -> None:
    with pytest.raises(LidarMaterializationError, match="status"):
        materialization._required_str(
            {"tile_id": "t"},
            "status",
            context="tile",
        )


def test_resolve_manifest_path_accepts_file_or_directory(tmp_path: Path) -> None:
    manifest = tmp_path / "data" / "materialization.json"
    manifest.parent.mkdir()
    manifest.write_text("{}")

    assert (
        materialization.resolve_lidar_materialization_manifest_path(manifest)
        == manifest.resolve()
    )
    assert (
        materialization.resolve_lidar_materialization_manifest_path(manifest.parent)
        == manifest.resolve()
    )


def test_materialization_tile_round_trip() -> None:
    tile = LidarMaterializationTile(
        tile_id="lidarbc:1:1",
        product="dem",
        layer_id=5,
        filename="tile.tif",
        download_url="https://example.test/tile.tif",
        relative_path="lidarbc/dem/layer_5/2023/tile.tif",
        status="verified",
        attempts=1,
        expected_size_bytes=10,
        size_bytes=10,
        sha256="a" * 64,
        remote_etag='"etag"',
        last_attempt_utc=GENERATED_UTC,
        resumed_from_bytes=2,
    )
    manifest = LidarMaterializationManifest(
        generated_utc=GENERATED_UTC,
        updated_utc=GENERATED_UTC,
        source={"source_id": "lidarbc"},
        selection={"sha256": "b" * 64},
        storage={"manifest_name": "materialization.json"},
        tiles=(tile,),
    )

    assert manifest.is_complete
    assert manifest.to_dict()["tiles"][0]["tile_id"] == "lidarbc:1:1"


def test_cli_materialize_and_status(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path)
    output_root = tmp_path / "data"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "lidar",
            "materialize",
            "--selection-manifest",
            str(selection),
            "--output-root",
            str(output_root),
            "--generated-utc",
            GENERATED_UTC,
        ],
    )

    assert result.exit_code == 0, result.output
    assert "verified: 2" in result.output

    status = runner.invoke(
        app,
        ["lidar", "materialization-status", str(output_root), "--require-complete"],
    )
    assert status.exit_code == 0, status.output
    assert "complete: True" in status.output

    status_json = runner.invoke(
        app,
        ["lidar", "materialization-status", str(output_root), "--json"],
    )
    assert status_json.exit_code == 0, status_json.output
    assert json.loads(status_json.stdout)["is_complete"] is True


def test_cli_plan_only_and_incomplete_status(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path)
    output_root = tmp_path / "data"
    runner = CliRunner()

    plan = runner.invoke(
        app,
        [
            "lidar",
            "materialize",
            "--selection-manifest",
            str(selection),
            "--output-root",
            str(output_root),
            "--plan-only",
            "--generated-utc",
            GENERATED_UTC,
        ],
    )
    assert plan.exit_code == 0, plan.output
    assert "pending: 2" in plan.output

    status = runner.invoke(
        app,
        [
            "lidar",
            "materialization-status",
            str(output_root),
            "--require-complete",
        ],
    )
    assert status.exit_code == 1
    assert "complete: False" in status.output


def test_cli_materialize_reports_errors(tmp_path: Path) -> None:
    selection = _selection_with_files(tmp_path, tile_count=1)
    payload = _read(selection)
    payload["schema_version"] = "bad"
    _write(selection, payload)

    result = CliRunner().invoke(
        app,
        [
            "lidar",
            "materialize",
            "--selection-manifest",
            str(selection),
            "--output-root",
            str(tmp_path / "data"),
        ],
    )

    assert result.exit_code == 1
    assert "LiDAR materialization error" in result.output
