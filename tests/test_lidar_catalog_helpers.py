from __future__ import annotations

import json
from pathlib import Path
from typing import Self

import pytest

from femic.lidar import catalog


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_layer_to_dict_is_json_ready() -> None:
    payload = catalog.LIDARBC_LAYERS[0].to_dict()

    assert payload == {
        "product": "dsm",
        "layer_id": 1,
        "layer_name": "LiDAR DSM Index 1:2,500",
        "grid_scale": "1:2500",
    }


def test_tile_rejects_missing_object_id() -> None:
    feature: dict[str, object] = {
        "attributes": {"filename": "tile.tif"},
        "geometry": {"xmin": 0, "ymin": 0, "xmax": 1, "ymax": 1},
    }

    with pytest.raises(catalog.LidarCatalogError, match="OBJECTID"):
        catalog.tile_from_arcgis_feature(feature, product="dem", layer_id=5)


def test_tile_rejects_non_mapping_attributes() -> None:
    feature: dict[str, object] = {
        "attributes": "bad",
        "geometry": {"xmin": 0, "ymin": 0, "xmax": 1, "ymax": 1},
    }

    with pytest.raises(catalog.LidarCatalogError, match="tile attributes"):
        catalog.tile_from_arcgis_feature(feature, product="dem", layer_id=5)


def test_discover_rejects_blank_product_name() -> None:
    with pytest.raises(catalog.LidarCatalogError, match="cannot be empty"):
        catalog.discover_lidarbc_tiles((0, 0, 1, 1), (" ",))


def test_discover_rejects_non_positive_page_limit() -> None:
    with pytest.raises(catalog.LidarCatalogError, match="page limit"):
        catalog.discover_lidarbc_tiles(
            (0, 0, 1, 1),
            ("point_cloud",),
            max_pages_per_layer=0,
        )


def test_load_json_parses_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        catalog,
        "urlopen",
        lambda url, timeout: _FakeResponse(b'{"features": []}'),
    )

    assert catalog._load_json("https://example.test", timeout_sec=1.0) == {
        "features": []
    }


def test_load_json_rejects_non_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        catalog,
        "urlopen",
        lambda url, timeout: _FakeResponse(b"[]"),
    )

    with pytest.raises(catalog.LidarCatalogError, match="non-object"):
        catalog._load_json("https://example.test", timeout_sec=1.0)


def test_load_json_rejects_error_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        catalog,
        "urlopen",
        lambda url, timeout: _FakeResponse(b'{"error": {"code": 400}}'),
    )

    with pytest.raises(catalog.LidarCatalogError, match="error payload"):
        catalog._load_json("https://example.test", timeout_sec=1.0)


def test_load_json_wraps_network_and_decode_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(url: str, timeout: float) -> _FakeResponse:
        raise OSError("offline")

    monkeypatch.setattr(catalog, "urlopen", fail)
    with pytest.raises(catalog.LidarCatalogError, match="Unable to read"):
        catalog._load_json("https://example.test", timeout_sec=1.0)

    monkeypatch.setattr(
        catalog,
        "urlopen",
        lambda url, timeout: _FakeResponse(b"not-json"),
    )
    with pytest.raises(catalog.LidarCatalogError, match="Unable to read"):
        catalog._load_json("https://example.test", timeout_sec=1.0)


def test_feature_mappings_handles_absent_and_invalid_features() -> None:
    assert catalog._feature_mappings({}) == ()
    with pytest.raises(catalog.LidarCatalogError, match="must be a list"):
        catalog._feature_mappings({"features": "bad"})


def test_optional_scalar_helpers_are_defensive() -> None:
    assert catalog._as_optional_int(None) is None
    assert catalog._as_optional_int("not-a-number") is None
    assert catalog._as_optional_float(None) is None
    assert catalog._as_optional_float("not-a-number") is None
    assert catalog._as_optional_float("inf") is None
    assert catalog._first_optional_int(None, "2") == 2
    assert catalog._first_optional_int(None, "bad") is None
    assert catalog._as_optional_str(" ") is None
    assert catalog._as_optional_str(" null ") is None
    assert catalog._as_optional_str("value") == "value"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ([1, 2, "7", "bad"], (1, 2, 7)),
        ((1, 2), (1, 2)),
        ("", ()),
        ("1, 2, 7", (1, 2, 7)),
        ("not-json", ()),
    ],
)
def test_parse_point_classes(value: object, expected: tuple[int, ...]) -> None:
    assert catalog._parse_point_classes(value) == expected


def test_bbox_from_geometry_skips_unusable_rings_and_points() -> None:
    geometry: dict[str, object] = {
        "rings": [
            "bad-ring",
            [None, [1], ["a", "b"], ["1", "2"]],
        ]
    }

    assert catalog._bbox_from_arcgis_geometry(geometry) == (1.0, 2.0, 1.0, 2.0)


def test_bbox_from_geometry_requires_rings_or_envelope() -> None:
    with pytest.raises(catalog.LidarCatalogError, match="no usable"):
        catalog._bbox_from_arcgis_geometry({})
    with pytest.raises(catalog.LidarCatalogError, match="no usable"):
        catalog._bbox_from_arcgis_geometry({"xmin": 0})


def test_selection_manifest_tolerates_missing_area(tmp_path: Path) -> None:
    tile = catalog.tile_from_arcgis_feature(
        {
            "attributes": {"OBJECTID": 1, "filename": "tile.tif"},
            "geometry": {"xmin": 0, "ymin": 0, "xmax": 1, "ymax": 1},
        },
        product="dem",
        layer_id=5,
    )
    selection = catalog.LidarTileSelection(
        source=catalog.LIDARBC_SOURCE,
        generated_utc="2026-10-25T00:00:00+00:00",
        aoi_bbox_epsg3005=(0.0, 0.0, 1.0, 1.0),
        products=("dem",),
        tiles=(tile,),
    )

    assert selection.total_area_m2 == 0.0
    path = catalog.write_lidar_selection_manifest(selection, tmp_path / "manifest.json")
    assert json.loads(path.read_text(encoding="utf-8"))["summary"]["tile_count"] == 1
