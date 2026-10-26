from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
from pyproj import CRS


def _metadata_module() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "audit_chapman_dem_metadata.py"
    )
    spec = importlib.util.spec_from_file_location("audit_chapman_dem_metadata", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the DEM metadata script.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


metadata = _metadata_module()


def test_compound_crs_metadata() -> None:
    result = metadata._crs_metadata(CRS.from_epsg(6653))
    assert result["crs_epsg"] == 6653
    assert result["horizontal_epsg"] == "3157"
    assert result["vertical_epsg"] == "6647"
    assert "CGVD2013" in str(result["vertical_datum"])


def _selection(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "tiles": [
                    {
                        "product": "dem",
                        "tile_id": "t1",
                        "filename": "a.tif",
                        "download_url": "https://example/a.tif",
                        "acquisition_year": 2024,
                    },
                    {
                        "product": "dem",
                        "tile_id": "t2",
                        "filename": "b.tif",
                        "download_url": "https://example/b.tif",
                        "acquisition_year": 2020,
                    },
                    {
                        "product": "dsm",
                        "tile_id": "t3",
                        "filename": "c.tif",
                        "download_url": "https://example/c.tif",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def test_audit_reads_metadata_and_records_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selection = _selection(tmp_path / "selection.json")

    def fake_probe(url: str) -> dict[str, object]:
        if url.endswith("b.tif"):
            raise RuntimeError("unreadable tile")
        return {
            "crs_epsg": 6653,
            "horizontal_epsg": "3157",
            "vertical_datum": "CGVD2013(CGG2013) height",
            "vertical_epsg": "6647",
            "resolution_m": [1.0, 1.0],
            "nodata": -32767.0,
        }

    monkeypatch.setattr(metadata, "_probe_tile", fake_probe)
    result = metadata.audit_dem_metadata(
        selection,
        generated_utc="2026-10-26T00:00:00+00:00",
    )
    assert result["tile_count"] == 2
    assert result["probed_count"] == 1
    assert result["failure_count"] == 1
    assert result["horizontal_epsg"] == ["3157"]
    assert result["vertical_datum"] == ["CGVD2013(CGG2013) height"]
    assert result["vertical_epsg"] == ["6647"]
    receptor = result["receptor"]
    assert isinstance(receptor, dict)
    assert receptor["status"] == "unreviewed"
    assert receptor["geometry"] is None


def test_audit_limit_and_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selection = _selection(tmp_path / "selection.json")
    calls: list[str] = []

    def fake_probe(url: str) -> dict[str, object]:
        calls.append(url)
        return {
            "crs_epsg": 6653,
            "horizontal_epsg": "3157",
            "vertical_datum": "CGVD2013(CGG2013) height",
            "vertical_epsg": "6647",
            "resolution_m": [1.0, 1.0],
            "nodata": None,
        }

    monkeypatch.setattr(metadata, "_probe_tile", fake_probe)
    output = tmp_path / "audit.json"
    code = metadata.main(
        [
            "--selection",
            str(selection),
            "--output",
            str(output),
            "--limit",
            "1",
            "--generated-utc",
            "2026-10-26T00:00:00+00:00",
        ]
    )
    assert code == 0
    assert len(calls) == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == metadata.SCHEMA_VERSION
    assert payload["tile_count"] == 1
    assert payload["probed_count"] == 1
