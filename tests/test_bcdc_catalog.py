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


def _managed_licence_payload() -> dict[str, object]:
    return {
        "success": True,
        "result": {
            "results": [
                {
                    "id": "pkg-managed-lic",
                    "name": "forest-tenure-managed-licence",
                    "title": "Forest Tenure Managed Licence",
                    "license_title": "Access Only",
                    "download_audience": "Public",
                    "organization": {
                        "name": "forest-tenure",
                        "title": "Forest Tenure Branch",
                    },
                    "resources": [
                        {
                            "id": "managed-lic-wms",
                            "name": "WMS getCapabilities request",
                            "format": "wms",
                            "bcdc_type": "webservice",
                            "object_name": "WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE_POLY_SVW",
                            "object_short_name": "FTEN_MGD_LIC",
                            "resource_access_method": "service",
                            "resource_type": "data",
                            "resource_storage_location": "bc geographic warehouse",
                            "url": "https://openmaps.gov.bc.ca/geo/pub/WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE_POLY_SVW/ows?service=WMS&request=GetCapabilities",
                        }
                    ],
                }
            ]
        },
    }


def _single_resource_payload(
    *,
    package_id: str,
    package_name: str,
    title: str,
    object_name: str,
    object_short_name: str = "",
) -> dict[str, object]:
    return {
        "success": True,
        "result": {
            "results": [
                {
                    "id": package_id,
                    "name": package_name,
                    "title": title,
                    "license_title": "Access Only",
                    "download_audience": "Public",
                    "organization": {
                        "name": "data-systems-and-services",
                        "title": "Data Systems and Services",
                    },
                    "resources": [
                        {
                            "id": f"{package_id}-wms",
                            "name": "WMS getCapabilities request",
                            "format": "wms",
                            "bcdc_type": "webservice",
                            "object_name": object_name,
                            "object_short_name": object_short_name,
                            "resource_access_method": "service",
                            "resource_type": "data",
                            "resource_storage_location": "bc geographic warehouse",
                            "url": f"https://openmaps.gov.bc.ca/geo/pub/{object_name}/ows",
                        }
                    ],
                }
            ]
        },
    }


def _mule_deer_payload() -> dict[str, object]:
    return {
        "success": True,
        "result": {
            "results": [
                {
                    "id": "pkg-mule-deer-suit2",
                    "name": "mule-deer-suitability-lillooet-tsa-version-2",
                    "title": "Mule Deer Suitability Lillooet TSA Version 2",
                    "resources": [
                        {
                            "object_name": "REG_LAND_AND_NATURAL_RESOURCE.MULE_DEER_SUIT2_TLI_POLY"
                        }
                    ],
                },
                {
                    "id": "pkg-mule-deer-topo",
                    "name": "mule-deer-winter-range-topographic-buffers-cariboo-region",
                    "title": "Mule Deer Winter Range Topographic Buffers - Cariboo Region",
                    "resources": [
                        {
                            "object_name": "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP"
                        }
                    ],
                },
                {
                    "id": "pkg-mule-deer-vernon",
                    "name": "mule-deer-winter-range-shelter-vernon-forest-district",
                    "title": "Mule Deer Winter Range Shelter Vernon Forest District",
                    "resources": [
                        {
                            "object_name": "REG_LAND_AND_NATURAL_RESOURCE.MULE_DEER_WR_SHELTER_DVE_POLY"
                        }
                    ],
                },
                {
                    "id": "pkg-mule-deer-hab",
                    "name": "mule-deer-habitat-management-zones-cariboo-region",
                    "title": "Mule Deer Habitat Management Zones - Cariboo Region",
                    "resources": [
                        {
                            "object_name": "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_HAB_MG_ZN_CAR_SP"
                        }
                    ],
                },
                {
                    "id": "pkg-mule-deer-stand",
                    "name": "stand-structure-habitat-classes-in-mule-deer-winter-range-cariboo-region",
                    "title": "Stand Structure Habitat Classes in Mule Deer Winter Range - Cariboo Region",
                    "resources": [
                        {
                            "object_name": "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_STND_STRC_CAR_SP"
                        }
                    ],
                },
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


def test_resolve_bcdc_candidates_only_advertises_wfs_when_top_match_is_fetchable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "success": True,
        "result": {
            "results": [
                {
                    "id": "pkg-burn",
                    "name": "burn-severity-mixed-package",
                    "title": "Burn Severity Mixed Package",
                    "license_title": "Open Government Licence",
                    "download_audience": "Public",
                    "organization": {
                        "name": "forest-analysis-and-inventory",
                        "title": "Forest Analysis and Inventory Branch",
                    },
                    "resources": [
                        {
                            "id": "svc-burn",
                            "name": "View WMS getCapabilities request details",
                            "format": "wms",
                            "bcdc_type": "webservice",
                            "object_name": "WHSE_FOREST_VEGETATION.VEG_BURN_SEVERITY_SP",
                            "object_short_name": "VEG_BURN",
                            "resource_access_method": "indirect access",
                            "resource_type": "data",
                            "resource_storage_location": "bc geographic warehouse",
                            "url": (
                                "https://openmaps.gov.bc.ca/geo/pub/"
                                "WHSE_FOREST_VEGETATION.VEG_BURN_SEVERITY_SP/ows"
                                "?service=WMS&request=GetCapabilities"
                            ),
                        },
                        {
                            "id": "dict-burn",
                            "name": "Burn Severity Legend",
                            "format": "pdf",
                            "bcdc_type": "document",
                            "resource_access_method": "direct access",
                            "resource_type": "abstraction",
                            "resource_storage_location": "web or ftp site",
                            "url": "https://example.invalid/burn_severity_legend.pdf",
                        },
                    ],
                }
            ]
        },
    }

    monkeypatch.setattr(bcdc_catalog, "_fetch_json", lambda _url: payload)
    monkeypatch.setattr(
        bcdc_catalog,
        "_fetch_text",
        lambda _url: (
            """<?xml version="1.0" encoding="UTF-8"?>
<WFS_Capabilities xmlns="http://www.opengis.net/wfs/2.0">
  <FeatureTypeList>
    <FeatureType>
      <Name>pub:WHSE_FOREST_VEGETATION.VEG_BURN_SEVERITY_SP</Name>
    </FeatureType>
  </FeatureTypeList>
</WFS_Capabilities>
"""
        ),
    )

    result = bcdc_catalog.resolve_bcdc_candidates(
        "WHSE_FOREST_VEGETATION.VEG_BURN_SEVERITY"
    )

    assert result.top_match is not None
    assert result.top_match.matched_by.startswith("object_name_stem:")
    assert result.top_match.suggested_fetch_strategy is None
    assert not any(
        "WFS-queryable OpenMaps service resources" in note
        for note in result.top_match.manual_follow_up
    )
    service_resource = next(
        resource
        for resource in result.top_match.resources
        if resource.resource_id == "svc-burn"
    )
    assert service_resource.classification == bcdc_catalog.INDIRECT_CUSTOM_DOWNLOAD
    assert service_resource.wfs_queryable is True
    assert service_resource.suggested_fetch_strategy == "wfs_getfeature_bbox"


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


def test_query_variants_expand_tsa_shorthand_namespace_and_suffix() -> None:
    variants = bcdc_catalog._query_variants("FTEN_MANAGED_LIC")

    assert "WHSE_FOREST_TENURE.FTEN_MANAGED_LIC" in variants
    assert "WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE_POLY_SVW" in variants


def test_query_variants_include_cross_namespace_curated_aliases() -> None:
    cadastre_variants = bcdc_catalog._query_variants(
        "WHSE_CADASTRE.CBM_CADASTRAL_FABRIC"
    )
    proposed_wha_variants = bcdc_catalog._query_variants(
        "REG_LAND_AND_NATURAL_RESOURCE.WLD_WHA_PROPOSED_SP"
    )

    assert "WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW" in cadastre_variants
    assert "WHSE_WILDLIFE_MANAGEMENT.WCP_WHA_PROPOSED_SP" in proposed_wha_variants


@pytest.mark.parametrize(
    ("query", "alias", "title", "object_name"),
    [
        (
            "coastline",
            "WHSE_BASEMAPPING.FWA_COASTLINES_SP",
            "Freshwater Atlas Coastlines",
            "WHSE_BASEMAPPING.FWA_COASTLINES_SP",
        ),
        (
            "FWA streams",
            "WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP",
            "Freshwater Atlas Stream Network",
            "WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP",
        ),
        (
            "FWA lakes",
            "WHSE_BASEMAPPING.FWA_LAKES_POLY",
            "Freshwater Atlas Lakes",
            "WHSE_BASEMAPPING.FWA_LAKES_POLY",
        ),
        (
            "FWA wetlands",
            "WHSE_BASEMAPPING.FWA_WETLANDS_POLY",
            "Freshwater Atlas Wetlands",
            "WHSE_BASEMAPPING.FWA_WETLANDS_POLY",
        ),
        (
            "landscape unit",
            "WHSE_LAND_USE_PLANNING.RMP_LANDSCAPE_UNIT_SVW",
            "Landscape Units of British Columbia - Current",
            "WHSE_LAND_USE_PLANNING.RMP_LANDSCAPE_UNIT_SVW",
        ),
        (
            "wildlife habitat area",
            "WHSE_WILDLIFE_MANAGEMENT.WCP_WILDLIFE_HABITAT_AREA_POLY",
            "Wildlife Habitat Areas - Approved",
            "WHSE_WILDLIFE_MANAGEMENT.WCP_WILDLIFE_HABITAT_AREA_POLY",
        ),
        (
            "ungulate winter range",
            "WHSE_WILDLIFE_MANAGEMENT.WCP_UNGULATE_WINTER_RANGE_SP",
            "Ungulate Winter Range - Approved",
            "WHSE_WILDLIFE_MANAGEMENT.WCP_UNGULATE_WINTER_RANGE_SP",
        ),
    ],
)
def test_resolve_bcdc_candidates_uses_phase75_free_text_aliases(
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    alias: str,
    title: str,
    object_name: str,
) -> None:
    calls: list[str] = []

    def _fake_fetch(url: str) -> dict[str, object]:
        calls.append(url)
        if alias in url:
            return _single_resource_payload(
                package_id=f"pkg-{object_name.rsplit('.', maxsplit=1)[-1].casefold()}",
                package_name=title.casefold().replace(" ", "-"),
                title=title,
                object_name=object_name,
            )
        return {"success": True, "result": {"results": []}}

    monkeypatch.setattr(bcdc_catalog, "_fetch_json", _fake_fetch)
    monkeypatch.setattr(
        bcdc_catalog,
        "_fetch_text",
        lambda _url: (
            f"""<?xml version="1.0" encoding="UTF-8"?>
<WFS_Capabilities xmlns="http://www.opengis.net/wfs/2.0">
  <FeatureTypeList>
    <FeatureType>
      <Name>pub:{object_name}</Name>
    </FeatureType>
  </FeatureTypeList>
</WFS_Capabilities>
"""
        ),
    )

    result = bcdc_catalog.resolve_bcdc_candidates(query)

    assert result.top_match is not None
    assert result.top_match.title == title
    assert result.top_match.matched_by == f"object_name:{object_name}"
    assert result.top_match.suggested_fetch_strategy == "wfs_getfeature_bbox"
    assert any(alias in note for note in result.notes)
    assert any(alias in url for url in calls)


def test_resolve_bcdc_candidates_prefers_cded_for_dem_free_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    cded_title = "Digital Elevation Model for British Columbia - CDED - 1:250,000"

    def _fake_fetch(url: str) -> dict[str, object]:
        calls.append(url)
        if "Digital+Elevation+Model" in url or "Digital%20Elevation%20Model" in url:
            return {
                "success": True,
                "result": {
                    "results": [
                        {
                            "id": "pkg-cded",
                            "name": "digital-elevation-model-cded",
                            "title": cded_title,
                            "license_title": "Open Government Licence",
                            "download_audience": "Public",
                            "organization": {
                                "name": "base-mapping-and-geomatic-services",
                                "title": "Base Mapping and Geomatic Services",
                            },
                            "resources": [],
                        }
                    ]
                },
            }
        return {"success": True, "result": {"results": []}}

    monkeypatch.setattr(bcdc_catalog, "_fetch_json", _fake_fetch)
    monkeypatch.setattr(bcdc_catalog, "_fetch_text", lambda _url: "")

    result = bcdc_catalog.resolve_bcdc_candidates("DEM")

    assert result.top_match is not None
    assert result.top_match.title == cded_title
    assert result.top_match.matched_by == f"exact_text:{cded_title}"
    assert any("Digital+Elevation+Model" in url for url in calls)


def test_resolve_bcdc_candidates_uses_generated_alias_for_managed_licence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _fake_fetch(url: str) -> dict[str, object]:
        calls.append(url)
        if "FTEN_MANAGED_LICENCE_POLY_SVW" in url:
            return _managed_licence_payload()
        return {"success": True, "result": {"results": []}}

    monkeypatch.setattr(bcdc_catalog, "_fetch_json", _fake_fetch)
    monkeypatch.setattr(
        bcdc_catalog,
        "_fetch_text",
        lambda _url: (
            """<?xml version="1.0" encoding="UTF-8"?>
<WFS_Capabilities xmlns="http://www.opengis.net/wfs/2.0">
  <FeatureTypeList>
    <FeatureType>
      <Name>pub:WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE_POLY_SVW</Name>
    </FeatureType>
  </FeatureTypeList>
</WFS_Capabilities>
"""
        ),
    )

    result = bcdc_catalog.resolve_bcdc_candidates("FTEN_MANAGED_LIC")

    assert result.top_match is not None
    assert result.top_match.title == "Forest Tenure Managed Licence"
    assert any("FTEN_MANAGED_LICENCE_POLY_SVW" in note for note in result.notes)
    assert any("FTEN_MANAGED_LICENCE_POLY_SVW" in url for url in result.api_urls)


def test_suggest_bcdc_replacement_family_returns_review_only_candidates() -> None:
    suggestions = bcdc_catalog.suggest_bcdc_replacement_family(
        "REG_LAND_AND_NATURAL_RESOURCE.L_MULE_DEER_WR_CAR_POLY",
        fetch_json_fn=lambda _url: _mule_deer_payload(),
        limit=3,
    )

    assert len(suggestions) == 3
    assert suggestions[0].matched_query == "MULE_DEER"
    assert suggestions[0].dataset_page_url.endswith(
        "/mule-deer-winter-range-topographic-buffers-cariboo-region"
    )
    assert (
        "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP"
        in suggestions[0].object_names
    )


def test_score_resource_promotes_object_name_stem_matches() -> None:
    resource = {
        "object_name": "WHSE_FOREST_VEGETATION.BEC_BIOGEOCLIMATIC_POLY",
        "object_short_name": "BEC",
        "name": "BEC Map",
        "object_table_comments": "",
    }

    score, matched_by = bcdc_catalog._score_resource(
        "WHSE_FOREST_VEGETATION.BEC",
        resource,
    )

    assert score == bcdc_catalog.OBJECT_NAME_STEM_MATCH_SCORE
    assert (
        matched_by == "object_name_stem:WHSE_FOREST_VEGETATION.BEC_BIOGEOCLIMATIC_POLY"
    )


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
