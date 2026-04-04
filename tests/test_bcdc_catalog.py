from __future__ import annotations

from pathlib import Path

import pytest

from femic import bcdc_catalog


def _f_own_payload(*, include_direct: bool = False) -> dict[str, object]:
    resources: list[dict[str, object]] = [
        {
            "id": "wms-id",
            "name": "WMS getCapabilities request",
            "format": "wms",
            "bcdc_type": "webservice",
            "object_name": "WHSE_FOREST_VEGETATION.F_OWN",
            "object_short_name": "F_OWN",
            "resource_access_method": "service",
            "resource_type": "data",
            "resource_storage_location": "bc geographic warehouse",
            "url": "https://openmaps.gov.bc.ca/geo/pub/WHSE_FOREST_VEGETATION.F_OWN/ows?service=WMS&request=GetCapabilities",
        },
        {
            "id": "custom-id",
            "name": "BC Geographic Warehouse Custom Download",
            "format": "multiple",
            "bcdc_type": "geographic",
            "object_name": "WHSE_FOREST_VEGETATION.F_OWN",
            "object_short_name": "F_OWN",
            "resource_access_method": "indirect access",
            "resource_type": "data",
            "resource_storage_location": "bc geographic warehouse",
            "url": "",
        },
        {
            "id": "doc-id",
            "name": "Generalized Forest Cover Ownership Layer Documentation",
            "format": "pdf",
            "bcdc_type": "document",
            "object_name": "",
            "object_short_name": "",
            "resource_access_method": "direct access",
            "resource_type": "abstraction",
            "resource_storage_location": "web or ftp site",
            "url": "https://www.for.gov.bc.ca/example/F_OWN_doc.pdf",
        },
    ]
    if include_direct:
        resources.append(
            {
                "id": "zip-id",
                "name": "Download FGDB zip",
                "format": "zip",
                "bcdc_type": "geographic",
                "object_name": "WHSE_FOREST_VEGETATION.F_OWN",
                "object_short_name": "F_OWN",
                "resource_access_method": "direct access",
                "resource_type": "data",
                "resource_storage_location": "web or ftp site",
                "url": "https://pub.data.gov.bc.ca/datasets/F_OWN.gdb.zip",
            }
        )
    return {
        "success": True,
        "result": {
            "results": [
                {
                    "id": "pkg-f-own",
                    "name": "generalized-forest-cover-ownership",
                    "title": "Generalized Forest Cover Ownership",
                    "license_title": "Access Only",
                    "download_audience": "Public",
                    "organization": {
                        "name": "forest-analysis-and-inventory",
                        "title": "Forest Analysis and Inventory Branch",
                    },
                    "resources": resources,
                }
            ]
        },
    }


def test_build_object_name_search_url_uses_res_extras_object_name() -> None:
    url = bcdc_catalog._build_object_name_search_url(
        "WHSE_FOREST_VEGETATION.F_OWN",
        rows=5,
    )

    assert "package_search" in url
    assert "rows=5" in url
    assert "res_extras_object_name%3A%22WHSE_FOREST_VEGETATION.F_OWN%22" in url


def test_resolve_bcdc_candidates_prefers_exact_object_name_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bcdc_catalog, "_fetch_json", lambda _url: _f_own_payload())
    monkeypatch.setattr(
        bcdc_catalog,
        "_fetch_text",
        lambda _url: (
            """<?xml version="1.0" encoding="UTF-8"?>
<WFS_Capabilities xmlns="http://www.opengis.net/wfs/2.0">
  <FeatureTypeList>
    <FeatureType>
      <Name>pub:WHSE_FOREST_VEGETATION.F_OWN</Name>
    </FeatureType>
  </FeatureTypeList>
</WFS_Capabilities>
"""
        ),
    )

    result = bcdc_catalog.resolve_bcdc_candidates("WHSE_FOREST_VEGETATION.F_OWN")

    assert result.top_match is not None
    assert result.top_match.title == "Generalized Forest Cover Ownership"
    assert result.top_match.matched_by.startswith("object_name:")
    assert result.top_match.suggested_fetch_strategy == "wfs_getfeature_bbox"
    classifications = {
        resource.classification for resource in result.top_match.resources
    }
    assert bcdc_catalog.SERVICE in classifications
    assert bcdc_catalog.INDIRECT_CUSTOM_DOWNLOAD in classifications
    assert bcdc_catalog.SUPPORTING_DOCUMENT in classifications
    wms_resource = next(
        resource
        for resource in result.top_match.resources
        if resource.name == "WMS getCapabilities request"
    )
    assert wms_resource.service_type == "openmaps_ows"
    assert wms_resource.wfs_queryable is True
    assert wms_resource.wfs_typename == "pub:WHSE_FOREST_VEGETATION.F_OWN"
    assert wms_resource.suggested_fetch_strategy == "wfs_getfeature_bbox"
    assert any("manual access" in note for note in result.top_match.manual_follow_up)
    assert any(
        "WFS-queryable OpenMaps service resources" in note
        for note in result.top_match.manual_follow_up
    )


def test_resolve_bcdc_candidates_falls_back_to_keyword_search_when_exact_is_weak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _fake_fetch(url: str) -> dict[str, object]:
        calls.append(url)
        if len(calls) == 1:
            return {"success": True, "result": {"results": []}}
        return _f_own_payload()

    monkeypatch.setattr(bcdc_catalog, "_fetch_json", _fake_fetch)
    monkeypatch.setattr(
        bcdc_catalog,
        "_fetch_text",
        lambda _url: (
            """<?xml version="1.0" encoding="UTF-8"?>
<WFS_Capabilities xmlns="http://www.opengis.net/wfs/2.0">
  <FeatureTypeList>
    <FeatureType>
      <Name>pub:WHSE_FOREST_VEGETATION.F_OWN</Name>
    </FeatureType>
  </FeatureTypeList>
</WFS_Capabilities>
"""
        ),
    )

    result = bcdc_catalog.resolve_bcdc_candidates("WHSE_FOREST_VEGETATION.F_OWN")

    assert len(calls) == 2
    assert "res_extras_object_name" in calls[0]
    assert "q=WHSE_FOREST_VEGETATION.F_OWN" in calls[1]
    assert result.top_match is not None


def test_resolve_bcdc_candidates_uses_curated_alias_when_original_query_misses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _fake_fetch(url: str) -> dict[str, object]:
        calls.append(url)
        if "CONSOLIDATED_CUTBLOCKS_2011" in url:
            return {"success": True, "result": {"results": []}}
        if "CONSOLIDATED_CUTBLOCKS" in url:
            return {
                "success": True,
                "result": {
                    "results": [
                        {
                            "id": "pkg-cutblocks",
                            "name": "harvested-areas-of-bc-consolidated-cutblocks",
                            "title": "Harvested Areas of BC (Consolidated Cutblocks)",
                            "license_title": "Open Government Licence",
                            "download_audience": "Public",
                            "organization": {
                                "name": "forest-analysis-and-inventory",
                                "title": "Forest Analysis and Inventory Branch",
                            },
                            "resources": [],
                        }
                    ]
                },
            }
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(bcdc_catalog, "_fetch_json", _fake_fetch)
    monkeypatch.setattr(
        bcdc_catalog,
        "_fetch_text",
        lambda _url: (
            """<?xml version="1.0" encoding="UTF-8"?>
<WFS_Capabilities xmlns="http://www.opengis.net/wfs/2.0">
</WFS_Capabilities>
"""
        ),
    )

    result = bcdc_catalog.resolve_bcdc_candidates("CONSOLIDATED_CUTBLOCKS_2011")

    assert result.top_match is not None
    assert result.top_match.title == "Harvested Areas of BC (Consolidated Cutblocks)"
    assert any("CONSOLIDATED_CUTBLOCKS" in note for note in result.notes)
    assert any("CONSOLIDATED_CUTBLOCKS_2011" in url for url in result.api_urls)
    assert any("CONSOLIDATED_CUTBLOCKS" in url for url in result.api_urls)


def test_probe_service_resource_marks_openmaps_wfs_queryable() -> None:
    resource = _f_own_payload()["result"]["results"][0]["resources"][0]

    probe = bcdc_catalog._probe_service_resource(
        resource,
        fetch_text_fn=lambda _url: (
            """<?xml version="1.0" encoding="UTF-8"?>
<WFS_Capabilities xmlns="http://www.opengis.net/wfs/2.0">
  <FeatureTypeList>
    <FeatureType>
      <Name>pub:WHSE_FOREST_VEGETATION.F_OWN</Name>
    </FeatureType>
  </FeatureTypeList>
</WFS_Capabilities>
"""
        ),
    )

    assert probe[0] == "openmaps_ows"
    assert probe[1] is True
    assert probe[2] is not None
    assert "service=WFS" in probe[2]
    assert probe[3] == "pub:WHSE_FOREST_VEGETATION.F_OWN"
    assert probe[4] == "wfs_getfeature_bbox"


def test_probe_service_resource_keeps_non_ows_service_unprobed() -> None:
    resource = {
        "id": "kml-id",
        "name": "Download KML Ground Overlay file",
        "format": "kml",
        "bcdc_type": "webservice",
        "object_name": "WHSE_FOREST_VEGETATION.F_OWN",
        "object_short_name": "F_OWN",
        "resource_access_method": "service",
        "resource_type": "data",
        "resource_storage_location": "bc geographic warehouse",
        "url": "https://openmaps.gov.bc.ca/kml/geo/layers/WHSE_FOREST_VEGETATION.F_OWN_loader.kml",
    }

    probe = bcdc_catalog._probe_service_resource(
        resource,
        fetch_text_fn=lambda _url: (_ for _ in ()).throw(
            AssertionError("fetch_text_fn should not be called")
        ),
    )

    assert probe == (None, False, None, None, None, ())


def test_download_direct_bcdc_resources_downloads_only_direct_data(
    tmp_path: Path,
) -> None:
    result = bcdc_catalog.BcdcResolveResult(
        query="WHSE_FOREST_VEGETATION.F_OWN",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        api_urls=("https://example.invalid/package_search",),
        matches=(
            bcdc_catalog._build_package_match(
                "WHSE_FOREST_VEGETATION.F_OWN",
                _f_own_payload(include_direct=True)["result"]["results"][0],
            ),
        ),
    )

    def _fake_download(url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(f"downloaded from {url}", encoding="utf-8")

    download_result = bcdc_catalog.download_direct_bcdc_resources(
        result,
        destination_root=tmp_path / "downloads",
        download_url_fn=_fake_download,
    )

    assert len(download_result.downloaded) == 1
    assert download_result.downloaded[0].saved_path.is_file()
    assert "F_OWN.gdb.zip" in download_result.downloaded[0].saved_path.name
    assert any("service" in item for item in download_result.skipped_resources)
    assert any(
        "indirect_custom_download" in item for item in download_result.skipped_resources
    )


def test_bcdc_downloaded_resource_delegates_relative_to(tmp_path: Path) -> None:
    destination_root = tmp_path / "downloads"
    saved_path = destination_root / "SITE_PROD_BC" / "site_prod_bc.gpkg"
    saved_path.parent.mkdir(parents=True, exist_ok=True)
    saved_path.write_text("ok", encoding="utf-8")

    resource = bcdc_catalog.BcdcDownloadedResource(
        resource_name="Site Productivity",
        resource_url="https://example.invalid/site_prod_bc.gpkg",
        saved_path=saved_path,
    )

    assert resource.relative_to(destination_root) == Path(
        "SITE_PROD_BC/site_prod_bc.gpkg"
    )


def test_write_bcdc_manifest_writes_json_payload(tmp_path: Path) -> None:
    result = bcdc_catalog.BcdcResolveResult(
        query="WHSE_FOREST_VEGETATION.F_OWN",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        api_urls=("https://example.invalid/package_search",),
        matches=(),
        notes=("No catalogue matches found for the supplied query.",),
    )

    manifest_path = bcdc_catalog.write_bcdc_manifest(
        result,
        tmp_path / "manifest.json",
    )

    assert manifest_path.is_file()
    text = manifest_path.read_text(encoding="utf-8")
    assert '"query": "WHSE_FOREST_VEGETATION.F_OWN"' in text
    assert '"notes": [' in text
