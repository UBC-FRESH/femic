from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _acquisition_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "acquire_chapman_public.py"
    spec = importlib.util.spec_from_file_location("acquire_chapman_public", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the acquisition script.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


acquire = _acquisition_module()


def _feature(x: float, y: float, **properties: object) -> dict[str, object]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [x, y]},
        "properties": properties,
    }


def _payload(features: list[dict[str, object]]) -> dict[str, object]:
    return {"type": "FeatureCollection", "features": features}


def test_url_builders_include_public_queries() -> None:
    watershed = acquire.wfs_url(
        "WHSE_BASEMAPPING.FWA_WATERSHEDS_POLY",
        cql_filter="FWA_WATERSHED_CODE LIKE '900-127577%'",
        count=5000,
    )
    streams = acquire.wfs_url(
        "WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP",
        bbox=acquire.BBOX,
    )
    station = acquire.station_url("08GA046")

    assert "CQL_FILTER=" in watershed
    assert "900-127577" in watershed
    assert "bbox=" in streams
    assert "1163000" in streams
    assert "STATION_NUMBER=08GA046" in station
    assert "api.weather.gc.ca" in station


def test_acquire_writes_layers_and_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_fetch(url: str, *, timeout: int) -> dict[str, object]:
        _ = timeout
        if "FWA_WATERSHEDS_POLY" in url:
            return _payload(
                [
                    _feature(1.0, 2.0, AREA_HA=100.0),
                    _feature(3.0, 4.0, AREA_HA=200.0),
                ]
            )
        if "FWA_STREAM_NETWORKS_SP" in url:
            return _payload([_feature(1.0, 2.0, GNIS_NAME="Chapman Creek")])
        if "DRA_DGTL_ROAD_ATLAS" in url:
            return _payload([_feature(1.0, 2.0, ROAD_SECTION_ID="1")])
        return _payload(
            [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-123.7, 49.4]},
                    "properties": {
                        "STATION_NUMBER": "08GA046",
                        "STATION_NAME": "Chapman Creek near Wilson Creek",
                        "DRAINAGE_AREA_GROSS": 71.5,
                        "STATUS_EN": "Discontinued",
                    },
                }
            ]
        )

    monkeypatch.setattr(acquire, "_fetch_json", fake_fetch)
    output = tmp_path / "chapman"
    manifest = acquire.acquire(output, timeout=1)

    assert (output / "watersheds.geojson").is_file()
    assert (output / "streams.geojson").is_file()
    assert (output / "roads.geojson").is_file()
    assert (output / "gauges.geojson").is_file()
    assert (output / "provenance.json").is_file()
    assert manifest["schema_version"] == acquire.SCHEMA_VERSION
    assert manifest["watershed_area_ha"] == pytest.approx(300.0)
    assert manifest["watershed_code_prefix"] == acquire.WATERSHED_PREFIX
    gaps = manifest["gaps"]
    assert isinstance(gaps, list)
    assert len(gaps) == len(acquire.GAPS)
    sources = manifest["sources"]
    assert isinstance(sources, list)
    assert len(sources) == 4
    watershed_record = next(item for item in sources if item["id"] == "fwa_watersheds")
    assert watershed_record["feature_count"] == 2
    assert (
        watershed_record["sha256"]
        == hashlib.sha256((output / "watersheds.geojson").read_bytes()).hexdigest()
    )
    assert watershed_record["bbox"] == [1.0, 2.0, 3.0, 4.0]
    station_record = next(item for item in sources if item["id"] == "wsc_gauges")
    assert station_record["feature_count"] == 3
    assert station_record["crs"] == "EPSG:4326"


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    output = tmp_path / "dry"
    manifest = acquire.acquire(output, dry_run=True)
    assert manifest["dry_run"] is True
    assert "queries" in manifest
    assert not output.exists()


def test_acquire_refuses_existing_output_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "chapman"
    output.mkdir()
    (output / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(RuntimeError, match="not empty"):
        acquire.acquire(output)


def test_geojson_bbox_and_area_helpers() -> None:
    payload = _payload(
        [
            _feature(1.0, 2.0, AREA_HA=10.0),
            _feature(3.0, 4.0, AREA_HA=20.0),
        ]
    )
    features = acquire._features(payload)
    assert acquire._bbox_from_geojson(payload) == [1.0, 2.0, 3.0, 4.0]
    assert acquire._area_ha(features[0]) == 10.0
    assert acquire._feature_count(payload) == 2
