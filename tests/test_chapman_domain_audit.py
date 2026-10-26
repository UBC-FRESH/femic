from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def _audit_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "audit_chapman_domain.py"
    spec = importlib.util.spec_from_file_location("audit_chapman_domain", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the domain-audit script.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = _audit_module()


def _polygon(x0: float, y0: float, x1: float, y1: float) -> dict[str, object]:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]],
        },
        "properties": {},
    }


def _point(x: float, y: float, **properties: object) -> dict[str, object]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [x, y]},
        "properties": properties,
    }


def _write(path: Path, features: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8",
    )


def _fixture(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    _write(
        root / "watersheds.geojson",
        [_polygon(0, 0, 100, 100), _polygon(100, 0, 200, 100)],
    )
    _write(root / "streams.geojson", [_point(50, 50)])
    _write(root / "roads.geojson", [_point(60, 40), _point(80, 30)])
    _write(root / "gauges.geojson", [_point(90, 90, drainage_area_km2=0.015)])
    selection = root / "selection.json"
    selection.write_text(
        json.dumps(
            {
                "tiles": [
                    {
                        "product": "dem",
                        "bbox_epsg3005": [0, 0, 100, 100],
                        "acquisition_year": 2024,
                        "projection": "utm10",
                        "vertical_datum": None,
                    },
                    {
                        "product": "dsm",
                        "bbox_epsg3005": [0, 0, 200, 100],
                        "acquisition_year": 2024,
                        "projection": "utm10",
                        "vertical_datum": "CGVD2013",
                    },
                    {
                        "product": "point_cloud",
                        "bbox_epsg3005": [0, 0, 200, 100],
                        "acquisition_year": 2024,
                        "projection": "utm10",
                        "vertical_datum": "CGVD2013",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return root, selection


def test_domain_audit_reports_union_and_lidar_gaps(tmp_path: Path) -> None:
    root, selection = _fixture(tmp_path / "runtime")
    result = audit.audit_domain(
        root,
        lidar_selection=selection,
        generated_utc="2026-10-26T00:00:00+00:00",
    )
    watershed = result["watershed"]
    assert isinstance(watershed, dict)
    assert watershed["part_count"] == 2
    assert watershed["area_ha"] == pytest.approx(2.0)
    assert watershed["gauge_drainage_area_ha"] == pytest.approx(1.5)
    assert watershed["area_ratio_to_gauge"] == pytest.approx(2.0 / 1.5)
    assert watershed["gauge_records"][0]["drainage_area_km2"] == pytest.approx(0.015)
    layers = result["layers"]
    assert layers["streams"]["feature_count"] == 1
    assert layers["roads"]["feature_count"] == 2
    lidar = result["lidar"]
    assert lidar["available"] is True
    assert lidar["products"]["dem"]["intersecting_tile_count"] == 1
    assert lidar["products"]["dem"]["covered_area_ha"] == pytest.approx(1.0)
    assert lidar["products"]["dem"]["uncovered_area_ha"] == pytest.approx(1.0)
    assert lidar["products"]["dem"]["vertical_datum_missing"] == 1
    assert lidar["products"]["dsm"]["covered_area_ha"] == pytest.approx(2.0)
    assert result["gaps"]


def test_domain_audit_without_lidar_selection(tmp_path: Path) -> None:
    root, _selection = _fixture(tmp_path / "runtime")
    result = audit.audit_domain(root, lidar_selection=tmp_path / "missing.json")
    assert result["lidar"] == {
        "available": False,
        "reason": "selection manifest missing",
    }


def test_domain_audit_requires_watersheds(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    _write(root / "watersheds.geojson", [])
    _write(root / "streams.geojson", [])
    _write(root / "roads.geojson", [])
    _write(root / "gauges.geojson", [])
    with pytest.raises(RuntimeError, match="No watershed"):
        audit.audit_domain(root)


def test_cli_writes_domain_audit(tmp_path: Path) -> None:
    root, selection = _fixture(tmp_path / "runtime")
    output = root / "domain_audit.json"
    code = audit.main(
        [
            "--runtime-root",
            str(root),
            "--lidar-selection",
            str(selection),
            "--output",
            str(output),
            "--generated-utc",
            "2026-10-26T00:00:00+00:00",
        ]
    )
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == audit.SCHEMA_VERSION
    assert payload["watershed"]["area_ha"] == pytest.approx(2.0)
