from __future__ import annotations

from pathlib import Path

import pytest

from femic import bcdc_catalog
from femic import bcdc_fetch


def _wfs_resolve_result() -> bcdc_catalog.BcdcResolveResult:
    return bcdc_catalog.BcdcResolveResult(
        query="WHSE_FOREST_VEGETATION.F_OWN",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        api_urls=("https://example.invalid/package_search",),
        matches=(
            bcdc_catalog.BcdcPackageMatch(
                package_id="pkg-f-own",
                package_name="generalized-forest-cover-ownership",
                title="Generalized Forest Cover Ownership",
                dataset_page_url=(
                    "https://catalogue.data.gov.bc.ca/dataset/"
                    "generalized-forest-cover-ownership"
                ),
                organization_name="forest-analysis-and-inventory",
                organization_title="Forest Analysis and Inventory Branch",
                license_title="Access Only",
                download_audience="Public",
                matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
                match_score=400,
                suggested_fetch_strategy="wfs_getfeature_bbox",
                resources=(
                    bcdc_catalog.BcdcResourceMatch(
                        resource_id="wms-id",
                        name="WMS getCapabilities request",
                        classification="service",
                        url=(
                            "https://openmaps.gov.bc.ca/geo/pub/"
                            "WHSE_FOREST_VEGETATION.F_OWN/ows"
                        ),
                        format="wms",
                        bcdc_type="webservice",
                        object_name="WHSE_FOREST_VEGETATION.F_OWN",
                        object_short_name="F_OWN",
                        resource_access_method="service",
                        resource_type="data",
                        resource_storage_location="bc geographic warehouse",
                        service_type="openmaps_ows",
                        wfs_queryable=True,
                        wfs_capabilities_url=(
                            "https://openmaps.gov.bc.ca/geo/pub/"
                            "WHSE_FOREST_VEGETATION.F_OWN/ows"
                            "?service=WFS&request=GetCapabilities&version=2.0.0"
                        ),
                        wfs_typename="pub:WHSE_FOREST_VEGETATION.F_OWN",
                        suggested_fetch_strategy="wfs_getfeature_bbox",
                        matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
                        match_score=400,
                        notes=("WFS-capable OpenMaps service.",),
                    ),
                ),
                manual_follow_up=(),
            ),
        ),
        notes=(),
    )


def _geojson_feature_collection() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "numberReturned": 1,
        "features": [
            {
                "type": "Feature",
                "properties": {"OWN": 60, "SCHEDULE": "A"},
                "geometry": {"type": "Point", "coordinates": [1175000.0, 455000.0]},
            }
        ],
    }


def test_build_bbox_3005_parses_and_validates() -> None:
    bbox = bcdc_fetch.build_bbox_3005("1170000,450000,1180000,460000")

    assert bbox == (1170000.0, 450000.0, 1180000.0, 460000.0)


def test_build_bbox_3005_rejects_invalid_order() -> None:
    with pytest.raises(bcdc_fetch.BcdcFetchError):
        bcdc_fetch.build_bbox_3005("1180000,450000,1170000,460000")


def test_resolve_geomark_bbox_3005_accepts_full_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bcdc_fetch,
        "_fetch_json_payload",
        lambda _url: {
            "id": "gm-abcdefghijklmnopqrstuvwxyz0000bc",
            "url": "https://apps.gov.bc.ca/pub/geomark/geomarks/gm-abcdefghijklmnopqrstuvwxyz0000bc",
            "geometry": (
                "SRID=4326;POLYGON((-144.664931 47.527035,-112.989186 47.527035,"
                "-112.989186 60.724742,-144.664931 60.724742,-144.664931 47.527035))"
            ),
        },
    )

    result = bcdc_fetch.resolve_geomark_bbox_3005(
        "https://apps.gov.bc.ca/pub/geomark/geomarks/gm-abcdefghijklmnopqrstuvwxyz0000bc"
    )

    assert result.geomark_id == "gm-abcdefghijklmnopqrstuvwxyz0000bc"
    minx, miny, maxx, maxy = result.bbox_epsg3005
    assert minx < maxx
    assert miny < maxy


def test_build_wfs_getfeature_url_uses_bbox_and_typename() -> None:
    url = bcdc_fetch._build_wfs_getfeature_url(
        "https://openmaps.gov.bc.ca/geo/pub/WHSE_FOREST_VEGETATION.F_OWN/ows?service=WMS&request=GetCapabilities",
        typename="pub:WHSE_FOREST_VEGETATION.F_OWN",
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
    )

    assert "service=WFS" in url
    assert "request=GetFeature" in url
    assert "typeNames=pub%3AWHSE_FOREST_VEGETATION.F_OWN" in url
    assert "bbox=1170000.0%2C450000.0%2C1180000.0%2C460000.0%2CEPSG%3A3005" in url


def test_fetch_bcdc_wfs_data_writes_geojson(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        bcdc_fetch,
        "resolve_bcdc_candidates",
        lambda query, limit: _wfs_resolve_result(),
    )
    monkeypatch.setattr(
        bcdc_fetch,
        "_fetch_json_payload",
        lambda _url: _geojson_feature_collection(),
    )

    result = bcdc_fetch.fetch_bcdc_wfs_data(
        "WHSE_FOREST_VEGETATION.F_OWN",
        destination_root=tmp_path,
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        output_format="geojson",
    )

    assert result.feature_count == 1
    assert result.saved_path.suffix == ".geojson"
    assert result.saved_path.is_file()
    assert "GetFeature" in result.request_url


def test_fetch_bcdc_wfs_data_writes_gpkg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        bcdc_fetch,
        "resolve_bcdc_candidates",
        lambda query, limit: _wfs_resolve_result(),
    )
    monkeypatch.setattr(
        bcdc_fetch,
        "_fetch_json_payload",
        lambda _url: _geojson_feature_collection(),
    )

    result = bcdc_fetch.fetch_bcdc_wfs_data(
        "WHSE_FOREST_VEGETATION.F_OWN",
        destination_root=tmp_path,
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        output_format="gpkg",
    )

    assert result.feature_count == 1
    assert result.saved_path.suffix == ".gpkg"
    assert result.saved_path.is_file()


def test_fetch_bcdc_wfs_data_pages_large_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        bcdc_fetch,
        "resolve_bcdc_candidates",
        lambda query, limit: _wfs_resolve_result(),
    )

    calls: list[str] = []

    def _fake_fetch(url: str):
        calls.append(url)
        if "startIndex=10000" in url:
            return {
                "type": "FeatureCollection",
                "numberMatched": 10005,
                "numberReturned": 5,
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"OWNERSHIP_DESCRIPTION": "Private"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [0.0, 0.0],
                                    [0.0, 1.0],
                                    [1.0, 1.0],
                                    [1.0, 0.0],
                                    [0.0, 0.0],
                                ]
                            ],
                        },
                    }
                    for _ in range(5)
                ],
            }
        return {
            "type": "FeatureCollection",
            "numberMatched": 10005,
            "numberReturned": 10000,
            "features": [
                {
                    "type": "Feature",
                    "properties": {"OWNERSHIP_DESCRIPTION": "Private"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [0.0, 0.0],
                                [0.0, 1.0],
                                [1.0, 1.0],
                                [1.0, 0.0],
                                [0.0, 0.0],
                            ]
                        ],
                    },
                }
                for _ in range(10000)
            ],
        }

    monkeypatch.setattr(bcdc_fetch, "_fetch_json_payload", _fake_fetch)

    result = bcdc_fetch.fetch_bcdc_wfs_data(
        "WHSE_FOREST_VEGETATION.F_OWN",
        destination_root=tmp_path,
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        output_format="geojson",
    )

    assert result.feature_count == 10005
    assert len(calls) == 2
    assert "count=10000" in calls[0]
    assert "startIndex" not in calls[0]
    assert "startIndex=10000" in calls[1]
    assert any(
        "Paged WFS fetch assembled `10005` features" in warning
        for warning in result.warnings
    )


def test_fetch_bcdc_wfs_data_tiles_when_service_rejects_pagination(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        bcdc_fetch,
        "resolve_bcdc_candidates",
        lambda query, limit: _wfs_resolve_result(),
    )

    calls: list[str] = []

    def _feature(feature_id: str) -> dict[str, object]:
        return {
            "type": "Feature",
            "id": feature_id,
            "properties": {"OWNERSHIP_DESCRIPTION": "Private"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [0.0, 0.0],
                        [0.0, 1.0],
                        [1.0, 1.0],
                        [1.0, 0.0],
                        [0.0, 0.0],
                    ]
                ],
            },
        }

    def _fake_fetch(url: str):
        calls.append(url)
        if "startIndex=10000" in url:
            raise bcdc_fetch.BcdcFetchError(
                f"Unable to fetch JSON from {url}: HTTP Error 400: Bad Request"
            )
        if "bbox=1170000.0%2C450000.0%2C1180000.0%2C460000.0" in url:
            return {
                "type": "FeatureCollection",
                "numberMatched": 10005,
                "numberReturned": 10000,
                "features": [_feature("root-1") for _ in range(10000)],
            }
        return {
            "type": "FeatureCollection",
            "numberMatched": 1,
            "numberReturned": 1,
            "features": [_feature(url.split("bbox=")[1].split("&")[0])],
        }

    monkeypatch.setattr(bcdc_fetch, "_fetch_json_payload", _fake_fetch)

    result = bcdc_fetch.fetch_bcdc_wfs_data(
        "WHSE_FOREST_VEGETATION.F_OWN",
        destination_root=tmp_path,
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        output_format="geojson",
    )

    assert result.feature_count == 4
    assert any("fell back to recursive bbox tiling" in warning for warning in result.warnings)
    assert any("Tiled WFS fetch assembled `4` unique features" in warning for warning in result.warnings)


def test_fetch_bcdc_wfs_data_rejects_direct_download_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    resolve_result = bcdc_catalog.BcdcResolveResult(
        query="SITE_PROD_BC",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        api_urls=("https://example.invalid/package_search",),
        matches=(
            bcdc_catalog.BcdcPackageMatch(
                package_id="pkg-site-prod",
                package_name="provincial-site-productivity-layer",
                title="Provincial Site Productivity Layer",
                dataset_page_url=(
                    "https://catalogue.data.gov.bc.ca/dataset/"
                    "provincial-site-productivity-layer"
                ),
                organization_name="forest-analysis-and-inventory",
                organization_title="Forest Analysis and Inventory Branch",
                license_title="Open Government Licence",
                download_audience="Public",
                matched_by="text_contains:SITE_PROD_BC",
                match_score=100,
                resources=(
                    bcdc_catalog.BcdcResourceMatch(
                        resource_id="zip-id",
                        name="Site Productivity zip",
                        classification="direct_data_download",
                        url="https://example.invalid/site_prod.zip",
                        format="zip",
                        bcdc_type="geographic",
                        object_name=None,
                        object_short_name=None,
                        resource_access_method="direct access",
                        resource_type="data",
                        resource_storage_location="web or ftp site",
                        matched_by="text_contains:SITE_PROD_BC",
                        match_score=100,
                        notes=(),
                    ),
                ),
                manual_follow_up=(),
            ),
        ),
    )
    monkeypatch.setattr(
        bcdc_fetch,
        "resolve_bcdc_candidates",
        lambda query, limit: resolve_result,
    )

    with pytest.raises(bcdc_fetch.BcdcFetchError) as exc_info:
        bcdc_fetch.fetch_bcdc_wfs_data(
            "SITE_PROD_BC",
            destination_root=tmp_path,
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        )

    assert "download-direct" in str(exc_info.value)
