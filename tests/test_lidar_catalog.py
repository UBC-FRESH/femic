from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from femic.lidar import catalog


def _feature(
    *,
    object_id: int,
    filename: str,
    bbox: tuple[float, float, float, float] = (
        1148001.886,
        391989.265,
        1149851.39,
        393427.352,
    ),
    area_m2: float = 2564813.605,
    classes: object = "[1,2,7,12]",
) -> dict[str, object]:
    minx, miny, maxx, maxy = bbox
    return {
        "attributes": {
            "OBJECTID": object_id,
            "filename": filename,
            "maptile": "092b051_1_3_1",
            "path": f"\\092\\092b\\2023\\{filename}",
            "year": 2023,
            "density": 8,
            "projection": "utm10",
            "contract": "OP24BMRS001",
            "oper_name": "LidarBC Program",
            "op_number": " ",
            "vert_datum": "Canadian Geodetic Vertical Datum of 2013",
            "classes": classes,
            "s3Url": f"https://nrs.objectstore.gov.bc.ca/gdwuts/{filename}",
            "s3RptUrl": (
                "https://nrs.objectstore.gov.bc.ca/gdwuts/metadata/"
                "accuracy_rpts/2024/op24bmrs001_summary.pdf"
            ),
            "Shape__Area": area_m2,
        },
        "geometry": {
            "rings": [
                [[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]
            ]
        },
    }


def _payload(*features: dict[str, object], exceeded: bool = False) -> dict[str, object]:
    return {"features": list(features), "exceededTransferLimit": exceeded}


def test_lidarbc_source_contract_is_explicit() -> None:
    source = catalog.LIDARBC_SOURCE

    assert source.source_id == "lidarbc"
    assert source.licence_id == "OGL-BC"
    assert source.licence_url.endswith("/open-government-licence-bc")
    assert source.native_crs == "EPSG:3005"
    assert source.supported_products == ("point_cloud", "dem", "dsm")
    assert source.derived_products == ("chm",)
    assert "LiDAR_BC_S3_Public" in source.feature_service_url
    assert "Access Only" in source.metadata_caveat
    assert "metadata-only" in source.storage_boundary

    payload = source.to_dict()
    assert payload["supported_products"] == ["point_cloud", "dem", "dsm"]
    assert payload["derived_products"] == ["chm"]
    assert isinstance(payload["notes"], list)


def test_lidarbc_layer_contract_maps_products_to_direct_layers() -> None:
    assert [layer.layer_id for layer in catalog.lidarbc_layers_for_product("dsm")] == [
        1,
        2,
        3,
    ]
    assert [
        layer.layer_id for layer in catalog.lidarbc_layers_for_product("point_cloud")
    ] == [4]
    assert [layer.layer_id for layer in catalog.lidarbc_layers_for_product("dem")] == [
        5,
        6,
    ]

    with pytest.raises(catalog.LidarCatalogError, match="FEMIC-derived"):
        catalog.lidarbc_layers_for_product("chm")
    with pytest.raises(catalog.LidarCatalogError, match="Unsupported"):
        catalog.lidarbc_layers_for_product("radar")


@pytest.mark.parametrize(
    "value",
    [
        (1.0, 2.0, 3.0),
        (0.0, 0.0, 0.0, 1.0),
        (0.0, 1.0, 1.0, 1.0),
        (float("nan"), 0.0, 1.0, 1.0),
        ("a", 0.0, 1.0, 1.0),
    ],
)
def test_normalize_bbox_rejects_invalid_values(value: Sequence[object]) -> None:
    with pytest.raises(catalog.LidarCatalogError):
        catalog.normalize_bbox_epsg3005(value)


def test_normalize_bbox_returns_floats() -> None:
    assert catalog.normalize_bbox_epsg3005([0, 1, 2, 3]) == (0.0, 1.0, 2.0, 3.0)


def test_bbox_intersects_requires_positive_area() -> None:
    assert catalog.bbox_intersects((0, 0, 2, 2), (1, 1, 3, 3))
    assert not catalog.bbox_intersects((0, 0, 1, 1), (1, 0, 2, 1))
    assert not catalog.bbox_intersects((0, 0, 1, 1), (2, 2, 3, 3))


def test_tile_from_arcgis_feature_normalizes_provenance() -> None:
    tile = catalog.tile_from_arcgis_feature(
        _feature(object_id=7, filename="bc_092b051_1_3_1.laz"),
        product="point_cloud",
        layer_id=4,
    )

    assert tile.tile_id == "lidarbc:4:7"
    assert tile.product == "point_cloud"
    assert tile.filename == "bc_092b051_1_3_1.laz"
    assert tile.maptile == "092b051_1_3_1"
    assert tile.acquisition_year == 2023
    assert tile.point_density_ppm2 == 8
    assert tile.operator_number is None
    assert tile.point_classes == (1, 2, 7, 12)
    assert tile.bbox_epsg3005 == (
        1148001.886,
        391989.265,
        1149851.39,
        393427.352,
    )
    assert tile.area_m2 == pytest.approx(2564813.605)
    assert tile.to_dict()["tile_id"] == "lidarbc:4:7"


def test_tile_from_arcgis_feature_rejects_bad_identity() -> None:
    feature = _feature(object_id=1, filename="tile.tif")
    attributes = feature["attributes"]
    assert isinstance(attributes, dict)
    del attributes["filename"]
    with pytest.raises(catalog.LidarCatalogError, match="filename"):
        catalog.tile_from_arcgis_feature(feature, product="dem", layer_id=5)

    feature = _feature(object_id=1, filename="tile.tif")
    feature.pop("geometry", None)
    with pytest.raises(catalog.LidarCatalogError, match="geometry"):
        catalog.tile_from_arcgis_feature(feature, product="dem", layer_id=5)

    with pytest.raises(catalog.LidarCatalogError, match="not 'dem'"):
        catalog.tile_from_arcgis_feature(
            _feature(object_id=1, filename="tile.tif"),
            product="dem",
            layer_id=4,
        )


def test_tile_geometry_falls_back_to_envelope_fields() -> None:
    feature = _feature(object_id=1, filename="tile.tif")
    feature["geometry"] = {"xmin": 1.0, "ymin": 2.0, "xmax": 3.0, "ymax": 4.0}

    tile = catalog.tile_from_arcgis_feature(feature, product="dem", layer_id=5)

    assert tile.bbox_epsg3005 == (1.0, 2.0, 3.0, 4.0)


def test_tile_without_classes_or_area_and_unknown_layer() -> None:
    feature = _feature(object_id=1, filename="tile.tif", classes=None)
    attributes = feature["attributes"]
    assert isinstance(attributes, dict)
    attributes["Shape__Area"] = None

    tile = catalog.tile_from_arcgis_feature(feature, product="dem", layer_id=99)

    assert tile.point_classes == ()
    assert tile.area_m2 is None
    assert tile.grid_scale is None


def test_build_lidarbc_tile_query_url_contains_aoi_and_pagination() -> None:
    url = catalog.build_lidarbc_tile_query_url(
        5,
        aoi_bbox_epsg3005=(1, 2, 3, 4),
        page_size=100,
        result_offset=200,
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.path.endswith("/FeatureServer/5/query")
    assert query["geometry"] == ["1.000,2.000,3.000,4.000"]
    assert query["inSR"] == ["3005"]
    assert query["outSR"] == ["3005"]
    assert query["resultOffset"] == ["200"]
    assert query["resultRecordCount"] == ["100"]
    assert query["orderByFields"] == ["OBJECTID ASC"]
    assert query["f"] == ["json"]


def test_build_lidarbc_tile_query_url_rejects_bad_paging() -> None:
    with pytest.raises(catalog.LidarCatalogError, match="page size"):
        catalog.build_lidarbc_tile_query_url(
            1, aoi_bbox_epsg3005=(0, 0, 1, 1), page_size=0
        )
    with pytest.raises(catalog.LidarCatalogError, match="offset"):
        catalog.build_lidarbc_tile_query_url(
            1,
            aoi_bbox_epsg3005=(0, 0, 1, 1),
            result_offset=-1,
        )


def test_discover_fetches_direct_products_and_warns_for_derived(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_load(url: str, *, timeout_sec: float) -> dict[str, object]:
        assert timeout_sec == 5.0
        calls.append(url)
        layer_id = int(urlparse(url).path.rstrip("/").split("/")[-2])
        assert layer_id == 4
        return _payload(_feature(object_id=1, filename="cloud.laz"))

    monkeypatch.setattr(catalog, "_load_json", fake_load)

    selection = catalog.discover_lidarbc_tiles(
        (1148000, 391900, 1149900, 393500),
        ("point_cloud", "chm"),
        timeout_sec=5.0,
        generated_utc="2026-10-25T00:00:00+00:00",
    )

    assert selection.tile_count == 1
    assert selection.tiles[0].filename == "cloud.laz"
    assert selection.products == ("point_cloud", "chm")
    assert selection.generated_utc == "2026-10-25T00:00:00+00:00"
    assert len(selection.request_urls) == 1
    assert len(calls) == 1
    assert any("FEMIC-derived" in warning for warning in selection.warnings)
    assert selection.to_dict()["summary"] == {
        "tile_count": 1,
        "total_area_m2": pytest.approx(2564813.605),
    }


def test_discover_filters_tiles_outside_aoi_and_deduplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inside = _feature(object_id=1, filename="inside.tif")
    outside = _feature(
        object_id=2,
        filename="outside.tif",
        bbox=(0.0, 0.0, 1.0, 1.0),
    )

    def fake_load(url: str, *, timeout_sec: float) -> dict[str, object]:
        return _payload(inside, outside, inside)

    monkeypatch.setattr(catalog, "_load_json", fake_load)

    selection = catalog.discover_lidarbc_tiles(
        (1148000, 391900, 1149900, 393500),
        ("point_cloud",),
    )

    assert [tile.filename for tile in selection.tiles] == ["inside.tif"]


def test_discover_paginates_until_short_page(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_offsets: list[int] = []

    def fake_load(url: str, *, timeout_sec: float) -> dict[str, object]:
        query = parse_qs(urlparse(url).query)
        offset = int(query["resultOffset"][0])
        requested_offsets.append(offset)
        if offset == 0:
            return _payload(_feature(object_id=1, filename="a.tif"), exceeded=True)
        if offset == 1:
            return _payload(_feature(object_id=2, filename="b.tif"))
        return _payload()

    monkeypatch.setattr(catalog, "_load_json", fake_load)

    selection = catalog.discover_lidarbc_tiles(
        (1148000, 391900, 1149900, 393500),
        ("point_cloud",),
        page_size=1,
    )

    assert requested_offsets == [0, 1, 2]
    assert [tile.filename for tile in selection.tiles] == ["a.tif", "b.tif"]


def test_discover_raises_when_page_limit_is_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load(url: str, *, timeout_sec: float) -> dict[str, object]:
        return _payload(_feature(object_id=1, filename="a.tif"), exceeded=True)

    monkeypatch.setattr(catalog, "_load_json", fake_load)

    with pytest.raises(catalog.LidarCatalogError, match="exceeded 1 pages"):
        catalog.discover_lidarbc_tiles(
            (1148000, 391900, 1149900, 393500),
            ("point_cloud",),
            page_size=1,
            max_pages_per_layer=1,
        )


def test_discover_records_empty_layer_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load(url: str, *, timeout_sec: float) -> dict[str, object]:
        return _payload()

    monkeypatch.setattr(catalog, "_load_json", fake_load)

    selection = catalog.discover_lidarbc_tiles(
        (1148000, 391900, 1149900, 393500),
        ("dem",),
    )

    assert selection.tiles == ()
    assert len(selection.request_urls) == 2
    assert sum("No LidarBC tiles" in item for item in selection.warnings) == 2


def test_discover_rejects_empty_product_list() -> None:
    with pytest.raises(catalog.LidarCatalogError, match="At least one"):
        catalog.discover_lidarbc_tiles((0, 0, 1, 1), ())


def test_discover_rejects_unknown_product() -> None:
    with pytest.raises(catalog.LidarCatalogError, match="Unsupported"):
        catalog.discover_lidarbc_tiles((0, 0, 1, 1), ("radar",))


def test_write_lidar_selection_manifest_round_trip(tmp_path: Path) -> None:
    tile = catalog.tile_from_arcgis_feature(
        _feature(object_id=1, filename="dsm.tif"),
        product="dsm",
        layer_id=1,
    )
    selection = catalog.LidarTileSelection(
        source=catalog.LIDARBC_SOURCE,
        generated_utc="2026-10-25T00:00:00+00:00",
        aoi_bbox_epsg3005=(1148000.0, 391900.0, 1149900.0, 393500.0),
        products=("dsm",),
        tiles=(tile,),
        request_urls=("https://example.test/query",),
        warnings=("note",),
    )

    path = catalog.write_lidar_selection_manifest(
        selection,
        tmp_path / "nested" / "selection.json",
    )

    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert text.endswith("\n")
    assert payload["schema_version"] == catalog.LIDAR_SELECTION_SCHEMA_VERSION
    assert payload["aoi"]["bbox_epsg3005"] == [
        1148000.0,
        391900.0,
        1149900.0,
        393500.0,
    ]
    assert payload["summary"]["tile_count"] == 1
    assert payload["tiles"][0]["tile_id"] == "lidarbc:1:1"
