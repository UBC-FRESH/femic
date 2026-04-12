from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, box

from femic import bcdc_dwds
from femic import tsr_catalog
from femic.fmg.patchworks import build_fragments_geodataframe
from femic.tsr_catalog import recipes as tsr_recipes


def _write_registry(tmp_path: Path) -> Path:
    payload = {
        "generated_utc": "2026-04-04T00:00:00+00:00",
        "tsa_count": 1,
        "document_count": 2,
        "tsas": [
            {
                "tsa_id": "tsa_29",
                "tsa_code": "29",
                "tsa_name": "Williams Lake",
            }
        ],
    }
    path = tmp_path / "metadata" / "tsr" / "tsa_registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_documents(tmp_path: Path) -> Path:
    payload = {
        "generated_utc": "2026-04-04T00:00:00+00:00",
        "document_count": 2,
        "documents": [
            {
                "tsa_id": "tsa_29",
                "relative_path": "TSR_2013/Data_Package_2013/29ts_dpkg_2013.pdf",
                "title": "Williams Lake TSA data package 2013",
                "document_type": "data_package",
                "cycle_year": 2013,
            },
            {
                "tsa_id": "tsa_29",
                "relative_path": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf",
                "title": "Williams Lake TSA data package 2024",
                "document_type": "data_package",
                "cycle_year": 2024,
            },
        ],
    }
    path = tmp_path / "metadata" / "tsr" / "tsa_documents.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_candidate_facts(tmp_path: Path) -> Path:
    payload = {
        "generated_utc": "2026-04-04T00:00:00+00:00",
        "fact_count": 2,
        "facts": [
            {"tsa_id": "tsa_29", "fact_family": "source_layer_candidate"},
            {"tsa_id": "tsa_29", "fact_family": "thlb_reference"},
        ],
    }
    path = tmp_path / "metadata" / "tsr" / "tsa_candidate_facts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_landscape_unit_layer(
    instance_root: Path,
    *,
    geometries: list,
    names: list[str] | None = None,
    numbers: list[str] | None = None,
) -> Path:
    resolved_names = names or [
        f"LU_{index + 1:02d}" for index in range(len(geometries))
    ]
    resolved_numbers = numbers or [str(index + 1) for index in range(len(geometries))]
    lu_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_LAND_USE_PLANNING_RMP_LANDSCAPE_UNIT_SVW"
        / "WHSE_LAND_USE_PLANNING_RMP_LANDSCAPE_UNIT_SVW.gpkg"
    )
    lu_path.parent.mkdir(parents=True, exist_ok=True)
    lu_layer = gpd.GeoDataFrame(
        {
            "LANDSCAPE_UNIT_NAME": resolved_names,
            "LANDSCAPE_UNIT_NUMBER": resolved_numbers,
        },
        geometry=geometries,
        crs="EPSG:3005",
    )
    lu_layer.to_file(lu_path, driver="GPKG")
    return lu_path


def _sample_dwds_order_result() -> bcdc_dwds.BcdcDwdsOrderResult:
    return bcdc_dwds.BcdcDwdsOrderResult(
        query="WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
        limit=5,
        generated_utc="2026-04-10T00:00:00+00:00",
        package_id="pkg-psp",
        package_name="growth-and-yield-samples-all-status",
        package_title="Growth and Yield Samples - All Status",
        dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/example",
        resource_id="dwds-id",
        resource_name="BC Geographic Warehouse Custom Download",
        resource_url=None,
        feature_type="WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
        matched_by="object_name:WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
        aoi_source="bbox",
        bbox_epsg3005=(1.0, 2.0, 3.0, 4.0),
        geomark_id=None,
        geomark_url=None,
        output_format="gpkg",
        email_address="user@example.com",
        clipping_method="clip_to_aoi",
        ordering_application="FEMIC-BCDC-DWDS",
        request_url="https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
        request_payload={"featureItems": []},
        order_id="2551000",
        order_guid="guid-123",
        submission_status="SUCCESS",
        submission_description="submitted",
        submission_value="2551000",
        status_probe=None,
    )


def test_init_tsr_recipe_scaffolds_writes_both_instance_local_yaml_files(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)

    result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    assert result.tsa.tsa_id == "tsa_29"
    source_layers_recipe = tsr_catalog.load_tsr_source_layers_recipe(
        result.source_layers_recipe_path
    )
    assert source_layers_recipe.recipe_kind == "source_layers"
    assert source_layers_recipe.tsa.tsa_name == "Williams Lake"
    assert (
        source_layers_recipe.canonical_inputs.candidate_facts_path
        == "metadata/tsr/tsa_candidate_facts.json"
    )
    assert (
        source_layers_recipe.instance_inputs.overlay_path == "config/tsr/overlay.yaml"
    )
    assert source_layers_recipe.entries == ()

    thlb_recipe = tsr_catalog.load_tsr_thlb_netdown_recipe(
        result.thlb_netdown_recipe_path
    )
    assert thlb_recipe.recipe_kind == "thlb_netdown"
    assert (
        thlb_recipe.instance_inputs.source_layer_recipe_path
        == "config/tsr/source_layers.recipe.yaml"
    )
    assert thlb_recipe.steps == ()
    assert source_layers_recipe.instance_inputs.download_root == "data/downloads/bcdc"


def test_init_tsr_recipe_scaffolds_rejects_existing_files_without_overwrite(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    source_layers_recipe_path = (
        instance_root / "config" / "tsr" / "source_layers.recipe.yaml"
    )
    thlb_netdown_recipe_path = (
        instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml"
    )

    tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=source_layers_recipe_path,
        thlb_netdown_recipe_path=thlb_netdown_recipe_path,
    )

    with pytest.raises(tsr_catalog.TsrRecipeError):
        tsr_catalog.init_tsr_recipe_scaffolds(
            instance_root=instance_root,
            tsa="29",
            registry_path=registry_path,
            documents_path=documents_path,
            candidate_facts_path=candidate_facts_path,
            source_root=source_root,
            overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
            overrides_path=instance_root
            / "config"
            / "tsr"
            / "source_layer_overrides.yaml",
            source_layers_recipe_path=source_layers_recipe_path,
            thlb_netdown_recipe_path=thlb_netdown_recipe_path,
        )


def test_preferred_thlb_primary_text_prefers_rich_snippet_over_numeric_heading() -> (
    None
):
    assert (
        tsr_recipes._preferred_thlb_primary_text(
            value="6.4",
            snippet="6.4. Identification of the Timber Harvesting Land Base ........ 25",
        )
        == "6.4. Identification of the Timber Harvesting Land Base ........ 25"
    )


def test_infer_land_base_stage_prefers_thlb_over_lhlb_for_thlb_definition() -> None:
    assert (
        tsr_recipes._infer_land_base_stage(
            action="definition",
            snippet="The THLB is the portion of the LHLB where timber harvesting is expected to occur.",
            value="The THLB is the portion of the LHLB where timber harvesting is expected to occur.",
        )
        == "lhlb_to_thlb"
    )


def test_low_signal_thlb_subject_uses_full_primary_text_for_label() -> None:
    assert tsr_recipes._is_low_signal_thlb_subject("stands")
    primary_text = "stands are removed from the THLB."
    label = (
        primary_text[:120]
        if tsr_recipes._is_low_signal_thlb_subject("stands")
        else "stands"
    )
    assert label == "stands are removed from the THLB."


def test_extract_land_base_summary_rows_and_subsections_build_parent_steps() -> None:
    pages = (
        {
            "page_number": 24,
            "relative_path": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf",
            "text": """
Table 3. Preliminary land base classification summary for the Williams Lake TSA
Area net of overlaps with prior items
Land classification Total area (ha) Forested area (ha) Net area removed (ha) Percent (%) of total TSA Percent (%) of AFLB
Total TSA area 4,933,635
Land not administered by the Province 697,033 697,033 14.13
Non-forest 1,284,855 1,105,908 1,105,908 22.42
Roads and landings 50,434 32,526 0.66
Analysis forest land base 3,098,168 0.00 100
Parks, protected areas, area-base tenures 935,744 504,260 306,327 6.23 9.93
Old growth management areas 292,759 211,183 210,719 4.27 6.80
Timber harvesting land base 1,682,843 34.11 54.32
Long-term THLB 1,660,053 53.66
6.2 Identification of the analysis forest land base
""",
        },
        {
            "page_number": 25,
            "relative_path": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf",
            "text": """
6.2.1 Land not administered by the Province for TSA timber supply
Certain types of lands do not contribute to timber supply for the purpose of this timber supply analysis.
This includes privately held lands, First Nations reserves, some lands under the jurisdiction of the federal government and area-based forest tenures.

6.2.2 Land classified as non-forest
All land classified as non-forest, non-productive forest, or not typed are excluded from the AFLB unless they were harvested in the past.
The VRI attribute Forest Management Land Base will be used to identify areas of non-forest.

6.2.3 Roads and landings
The existing permanent RTL area will be removed from the AFLB and will not contribute to timber supply.

6.3.1 Parks, protected areas, and small area-based tenures
The parks, protected areas, and woodlots that were included in the AFLB will be removed at this stage.

6.3.2 Old growth management areas
Permanent and Permanent-Rotating Old Growth Management Areas are removed from the LHLB as no harvest areas.

6.4.8 Wildlife tree retention areas
The land base that will continually be required for WTRA will be modelled as an aspatial THLB reduction factor.

7. Current Forest Management Assumptions
""",
        },
    )
    source_index = (
        {
            "entry_id": "whse_f_own",
            "tokens": {"ownership", "province", "administered", "land", "f", "own"},
        },
        {
            "entry_id": "rmp_ogma_legal",
            "tokens": {"old", "growth", "management", "ogma", "areas"},
        },
    )

    summary_rows = tsr_recipes._extract_land_base_summary_rows(pages)
    assert [row["parent_label"] for row in summary_rows][:4] == [
        "Total TSA area",
        "Land not administered by the Province",
        "Non-forest",
        "Roads and landings",
    ]

    subsections = tsr_recipes._extract_land_base_subsections(pages)
    assert [subsection["section_number"] for subsection in subsections][:3] == [
        "6.2.1",
        "6.2.2",
        "6.2.3",
    ]

    parent_steps, compiled_steps = (
        tsr_recipes._build_parent_steps_from_land_base_summary(
            summary_rows=summary_rows,
            subsections=subsections,
            source_index=source_index,
            tsa_code="29",
        )
    )

    glb_parent = next(
        step
        for step in parent_steps
        if step["parent_label"] == "Land not administered by the Province"
    )
    assert glb_parent["land_base_stage"] == "glb_to_aflb"
    assert glb_parent["benchmark_marginal_area_ha"] == pytest.approx(697033.0)
    assert glb_parent["subsection_number"] == "6.2.1"
    assert glb_parent["draft_subrules"]

    non_forest_parent = next(
        step for step in parent_steps if step["parent_label"] == "Non-forest"
    )
    assert non_forest_parent["land_base_stage"] == "glb_to_aflb"
    assert non_forest_parent["subsection_number"] == "6.2.2"

    parks_parent = next(
        step
        for step in parent_steps
        if step["parent_label"] == "Parks, protected areas, area-base tenures"
    )
    assert parks_parent["land_base_stage"] == "aflb_to_lhlb"
    assert parks_parent["subsection_number"] == "6.3.1"

    ogma_parent = next(
        step
        for step in parent_steps
        if step["parent_label"] == "Old growth management areas"
    )
    assert ogma_parent["land_base_stage"] == "aflb_to_lhlb"
    assert ogma_parent["execution_class"] == "legal_harvest_exclusion"
    assert ogma_parent["subsection_number"] == "6.3.2"

    ogma_compiled = next(
        step
        for step in compiled_steps
        if step["parent_label"] == "Old growth management areas"
    )
    assert ogma_compiled["parent_step_id"] == ogma_parent["parent_step_id"]
    assert ogma_compiled["land_base_stage"] == "aflb_to_lhlb"
    assert ogma_compiled["linked_source_entry_ids"] == ["rmp_ogma_legal"]
    assert ogma_compiled["source_attribute_filters"] == [
        {
            "field": "OGMA_TYPE",
            "operator": "in",
            "value": ["PERM", "ROT"],
        }
    ]


def test_split_subsection_and_explicit_data_source_hints_clean_tableish_noise() -> None:
    text = """
The VRI attribute Forest Management Land Base (FMLB) will be used to identify areas of non-forest.
Table 5. Land classified as non-forest Attributes Description Logging history Total area 9,374 50,191 4,455 741 4,413 976,656.
Data source and comments: WHSE_FOREST_VEGETATION.F_OWN WHSE_BASEMAPPING.FWA_LAKES_POLY
WHSE_BASEMAPPING.FWA_RIVERS_POLY
WHSE_BASEMAPPING.FWA_WETLANDS_POLY
"""
    source_index = (
        {
            "entry_id": "whse_forest_vegetation_f_own",
            "label": "WHSE_FOREST_VEGETATION.F_OWN",
            "recommended_query": "WHSE_FOREST_VEGETATION.F_OWN",
            "exact_query_keys": {
                tsr_recipes._normalize_source_query_key("WHSE_FOREST_VEGETATION.F_OWN")
            },
            "tokens": {"ownership", "forest", "vegetation", "f", "own"},
        },
        {
            "entry_id": "whse_basemapping_fwa_lakes_poly",
            "label": "WHSE_BASEMAPPING.FWA_LAKES_POLY",
            "recommended_query": "WHSE_BASEMAPPING.FWA_LAKES_POLY",
            "exact_query_keys": {
                tsr_recipes._normalize_source_query_key(
                    "WHSE_BASEMAPPING.FWA_LAKES_POLY"
                )
            },
            "tokens": {"fwa", "lakes", "poly"},
        },
        {
            "entry_id": "whse_basemapping_fwa_rivers_poly",
            "label": "WHSE_BASEMAPPING.FWA_RIVERS_POLY",
            "recommended_query": "WHSE_BASEMAPPING.FWA_RIVERS_POLY",
            "exact_query_keys": {
                tsr_recipes._normalize_source_query_key(
                    "WHSE_BASEMAPPING.FWA_RIVERS_POLY"
                )
            },
            "tokens": {"fwa", "rivers", "poly"},
        },
        {
            "entry_id": "whse_basemapping_fwa_wetlands_poly",
            "label": "WHSE_BASEMAPPING.FWA_WETLANDS_POLY",
            "recommended_query": "WHSE_BASEMAPPING.FWA_WETLANDS_POLY",
            "exact_query_keys": {
                tsr_recipes._normalize_source_query_key(
                    "WHSE_BASEMAPPING.FWA_WETLANDS_POLY"
                )
            },
            "tokens": {"fwa", "wetlands", "poly"},
        },
    )

    assert tsr_recipes._split_subsection_into_draft_subrules(text) == (
        "The VRI attribute Forest Management Land Base (FMLB) will be used to identify areas of non-forest.",
    )
    assert tsr_recipes._extract_data_source_comment_tokens(text) == (
        "WHSE_FOREST_VEGETATION.F_OWN",
        "WHSE_BASEMAPPING.FWA_LAKES_POLY",
        "WHSE_BASEMAPPING.FWA_RIVERS_POLY",
        "WHSE_BASEMAPPING.FWA_WETLANDS_POLY",
    )
    assert tsr_recipes._link_thlb_step_to_sources(
        "non-forest",
        source_index=source_index,
        explicit_query_tokens=tsr_recipes._extract_data_source_comment_tokens(text),
    ) == (
        "whse_forest_vegetation_f_own",
        "whse_basemapping_fwa_lakes_poly",
        "whse_basemapping_fwa_rivers_poly",
        "whse_basemapping_fwa_wetlands_poly",
    )


def test_build_draft_subrules_prefers_semantic_layer_hints_for_non_forest_logic() -> (
    None
):
    linked_subsection = {
        "title": "Land classified as non-forest",
        "body": """
All land classified as non-forest, non-productive forest, or not typed are excluded from the AFLB unless they were harvested in the past.
These areas do not contribute to forest management objectives such as seral objectives for landscape-level biodiversity.
The VRI attribute Forest Management Land Base (FMLB) will be used to identify areas of non-forest.
In addition to the FMLB criteria, areas with a crown closure less than 10% also be considered non-forest and will be excluded.
Areas with low crown closure resulting from past harvest are exceptions that will remain in the AFLB.
A final check will use data from the Freshwater Atlas (FWA) data to ensure lakes, rivers and wetlands are appropriately excluded.
Data source and comments:
WHSE_BASEMAPPING.FWA_LAKES_POLY
""",
        "provenance_id": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=26",
    }
    subrules = tsr_recipes._build_draft_subrules_for_parent_step(
        parent_step_id="thlb_parent_003_non_forest",
        linked_subsection=linked_subsection,
        source_index=(),
        execution_class="drop_from_universe",
    )

    summaries = [subrule["human_summary"] for subrule in subrules]
    assert not any(
        "do not contribute to forest management objectives" in summary
        for summary in summaries
    )
    fmlb_rule = next(
        subrule for subrule in subrules if "FMLB" in subrule["human_summary"]
    )
    assert "vri" in fmlb_rule["candidate_layers"]
    assert "FOR_MGMT_LAND_BASE_IND" in fmlb_rule["candidate_fields"]
    crown_rule = next(
        subrule
        for subrule in subrules
        if "crown closure less than 10%" in subrule["human_summary"]
    )
    assert "CROWN_CLOSURE" in crown_rule["candidate_fields"]
    assert "< 10" in crown_rule["candidate_values"]
    harvest_exception = next(
        subrule for subrule in subrules if "past harvest" in subrule["human_summary"]
    )
    assert "consolidated_harvest_depletion" in harvest_exception["candidate_layers"]
    assert harvest_exception["candidate_operation_type"] == "no_deduction"
    fwa_rule = next(
        subrule
        for subrule in subrules
        if "Freshwater Atlas" in subrule["human_summary"]
    )
    assert "freshwater_atlas" in fwa_rule["candidate_layers"]


def test_build_draft_subrules_filters_rationale_dates_and_adds_ownership_hints() -> (
    None
):
    linked_subsection = {
        "title": "Land not administered by the Province for TSA timber supply",
        "body": """
Certain types of lands do not contribute to timber supply for the purpose of this timber supply analysis.
This includes privately held lands, First Nations reserves, some lands under the jurisdiction of the federal government and area-based forest tenures.
Woodlots are not required to manage for landscape-level biodiversity objectives, so they are left in the AFLB and removed when defining the LHLB.
The Northern Secwepemc te Qelmucw (NStQ) Treaty Negotiations Agreement in Principle was signed on July 22, 2018, and the Parties are in Stage 5 negotiations to conclude treaty.
On June 26, 2014, the Supreme Court of Canada (SCC) released its decision on Tsilhqot’in Nation v. British Columbia.
Areas classified in this data set with ownership codes 62 (Forest Management Unit) or 69 (Community Watershed) are generally administered by the Province for TSA timber supply.
Areas classified with ownership code 99 (crown leases) are not generally managed for TSA timber supply.
Data source and comments:
WHSE_FOREST_VEGETATION.F_OWN
""",
        "provenance_id": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=25",
    }
    subrules = tsr_recipes._build_draft_subrules_for_parent_step(
        parent_step_id="thlb_parent_002_land_not_administered_by_the_province",
        linked_subsection=linked_subsection,
        source_index=(),
        execution_class="drop_from_universe",
    )

    summaries = [subrule["human_summary"] for subrule in subrules]
    assert not any("was signed on July 22, 2018" in summary for summary in summaries)
    assert not any("On June 26, 2014" in summary for summary in summaries)
    ownership_rule = next(
        subrule
        for subrule in subrules
        if "privately held lands" in subrule["human_summary"]
    )
    assert "whse_forest_vegetation_f_own" in ownership_rule["candidate_layers"]
    assert "OWNERSHIP_CLASS" in ownership_rule["candidate_fields"]
    assert "private" in ownership_rule["candidate_values"]
    assert "federal" in ownership_rule["candidate_values"]
    defer_rule = next(
        subrule
        for subrule in subrules
        if "removed when defining the LHLB" in subrule["human_summary"]
    )
    assert defer_rule["candidate_operation_type"] == "defer_to_lhlb"
    code_99_rule = next(
        subrule
        for subrule in subrules
        if "ownership code 99" in subrule["human_summary"]
    )
    assert "OWNERSHIP_CODE" in code_99_rule["candidate_fields"]
    assert "99" in code_99_rule["candidate_values"]
    code_62_69_rule = next(
        subrule
        for subrule in subrules
        if "ownership codes 62" in subrule["human_summary"]
    )
    assert "OWNERSHIP_CODE" in code_62_69_rule["candidate_fields"]
    assert "62" in code_62_69_rule["candidate_values"]
    assert "69" in code_62_69_rule["candidate_values"]


def test_build_draft_subrules_for_cultural_heritage_avoids_fake_spatial_layers() -> (
    None
):
    linked_subsection = {
        "title": "Cultural heritage and archaeological resources.",
        "body": """
The Heritage Conservation Act (HCA) recognizes the historical, cultural, scientific, spiritual, and educational value of archaeological sites.
Cultural heritage resources are identified by the licensees through information sharing prior to the submission of cutting permit and road permit applications to the ministry.
The incremental excluded area required to protect these sites was estimated from discussions with licensees and the Tsilhqot'in National Government.
This will be modelled as an aspatial reduction to the THLB.
Data source and comments:
Tsilhqot'in National Government; Tolko Industries Ltd. - FSP #780; West Fraser Mills Ltd. - FSP #755; and BCTS - FSP #828.
""",
        "provenance_id": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=37",
    }
    subrules = tsr_recipes._build_draft_subrules_for_parent_step(
        parent_step_id="thlb_parent_021_cultural_heritage_and_archaeological_resources",
        linked_subsection=linked_subsection,
        source_index=(),
        execution_class="projected_harvest_exclusion",
    )

    assert len(subrules) == 2
    assert all(not subrule["candidate_layers"] for subrule in subrules)
    assert subrules[0]["candidate_operation_type"] == "review"
    assert subrules[1]["candidate_operation_type"] == "aspatial_reduction"
    assert "2% of cutblock area" in subrules[1]["candidate_values"]


def test_build_draft_subrules_for_future_roads_prefers_aspatial_factor() -> None:
    linked_subsection = {
        "title": "Roads and landings",
        "body": """
Future roads, trails and landings
The AFLB area removed to account for future RTL was estimated based on current performance and RESULTS data.
The future RTL reduction will be applied to future harvested areas in the timber supply model after stands are harvested for the first time.
The average factor is 2.28% for all three Cariboo TSAs.
In total, 22 754 hectares will be excluded from the forested land base at the time of first harvest to represent the area lost due to future road development.
""",
        "provenance_id": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=27",
    }
    subrules = tsr_recipes._build_draft_subrules_for_parent_step(
        parent_step_id="thlb_parent_023_future_roads",
        linked_subsection=linked_subsection,
        source_index=(),
        execution_class="projected_harvest_exclusion",
    )

    assert len(subrules) == 1
    assert subrules[0]["candidate_operation_type"] == "aspatial_area_reduction"
    assert subrules[0]["candidate_layers"] == []
    assert "2.28% future RTL factor" in subrules[0]["candidate_values"]


def test_infer_parent_row_stage_places_future_roads_in_lhlb_to_thlb_for_tsa29() -> None:
    stage, execution_class = tsr_recipes._infer_parent_row_stage(
        label="Future roads",
        linked_subsection={
            "section_number": "6.2.3",
            "land_base_stage": "glb_to_aflb",
            "title": "Roads and landings",
        },
        seen_aflb_row=True,
        seen_thlb_row=False,
        tsa_code="29",
    )

    assert stage == "lhlb_to_thlb"
    assert execution_class == "projected_harvest_exclusion"


def test_infer_parent_row_stage_places_proven_aboriginal_rights_in_aflb_to_lhlb() -> (
    None
):
    stage, execution_class = tsr_recipes._infer_parent_row_stage(
        label="Proven Aboriginal Rights areas",
        linked_subsection={
            "section_number": "6.4.1",
            "land_base_stage": "lhlb_to_thlb",
            "title": "Proven Aboriginal Rights area",
        },
        seen_aflb_row=True,
        seen_thlb_row=False,
        tsa_code="29",
    )

    assert stage == "aflb_to_lhlb"
    assert execution_class == "legal_harvest_exclusion"


def test_infer_parent_row_stage_places_buffered_trails_in_lhlb_to_thlb() -> None:
    stage, execution_class = tsr_recipes._infer_parent_row_stage(
        label="Buffered trails",
        linked_subsection={
            "section_number": "6.3.6",
            "land_base_stage": "aflb_to_lhlb",
            "title": "Buffered trails",
        },
        seen_aflb_row=True,
        seen_thlb_row=False,
        tsa_code="29",
    )

    assert stage == "lhlb_to_thlb"
    assert execution_class == "projected_harvest_exclusion"


def test_extract_land_base_subsections_ignores_duplicate_heading_echoes() -> None:
    pages = (
        {
            "page_number": 25,
            "relative_path": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf",
            "text": """
6.2.1 Land not administered by the Province for TSA timber supply
Certain types of lands do not contribute to timber supply.
6.2.1 Land not administered by the Province for TSA timber supply
This includes privately held lands and reserves.
6.2.2 Land classified as non-forest
Exclude non-forest areas from the AFLB.
7. Current Forest Management Assumptions
""",
        },
    )

    subsections = tsr_recipes._extract_land_base_subsections(pages)

    assert [subsection["section_number"] for subsection in subsections] == [
        "6.2.1",
        "6.2.2",
    ]
    assert (
        "6.2.1 Land not administered by the Province for TSA timber supply"
        not in (subsections[0]["body"])
    )


def test_build_parent_steps_from_land_base_summary_prefers_tsa29_table_stage_over_subsection_stage() -> (
    None
):
    summary_rows = (
        {
            "parent_label": "Total TSA area",
            "numeric_tokens": (4793635.0,),
            "table_provenance": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=24",
        },
        {
            "parent_label": "Analysis forest land base",
            "numeric_tokens": (3098168.0, 0.0, 100.0),
            "table_provenance": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=24",
        },
        {
            "parent_label": "Future roads",
            "numeric_tokens": (22754.0, 2.28, 0.73),
            "table_provenance": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=24",
        },
    )
    subsections = (
        {
            "section_number": "6.2.3",
            "title": "Roads and landings",
            "provenance_id": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=27",
            "land_base_stage": "glb_to_aflb",
            "body": "Future roads, trails and landings are described here.",
        },
    )

    parent_steps, _compiled_steps = (
        tsr_recipes._build_parent_steps_from_land_base_summary(
            summary_rows=summary_rows,
            subsections=subsections,
            source_index=(),
            tsa_code="29",
        )
    )

    future_roads = next(
        step for step in parent_steps if step["parent_label"] == "Future roads"
    )
    assert future_roads["land_base_stage"] == "lhlb_to_thlb"
    assert future_roads["execution_class"] == "projected_harvest_exclusion"
    assert future_roads["subsection_number"] == "6.2.3"


def test_infer_semantic_candidate_layers_prefers_terrain_stability_for_inoperable_slopes() -> (
    None
):
    layers = tsr_recipes._infer_semantic_candidate_layers(
        "Inoperable areas will be identified as follows: Slopes that exceed 70% east of Highway 97.",
        subsection_source_hints=(),
    )

    assert "terrain_stability" in layers
    assert "consolidated_harvest_depletion" not in layers


def test_link_thlb_step_to_sources_demotes_stale_year_stamped_entries() -> None:
    source_index = (
        {
            "entry_id": "consolidated_cutblocks_2011",
            "label": "CONSOLIDATED_CUTBLOCKS_2011",
            "recommended_query": "CONSOLIDATED_CUTBLOCKS_2011",
            "exact_query_keys": {
                "consolidated_cutblocks_2011",
            },
            "tokens": {"consolidated", "cutblocks"},
            "cycle_year": 2013,
            "query_years": (2011,),
            "is_stale_year_stamped": True,
        },
        {
            "entry_id": "consolidated_cutblocks_2020",
            "label": "CONSOLIDATED_CUTBLOCKS_2020",
            "recommended_query": "CONSOLIDATED_CUTBLOCKS_2020",
            "exact_query_keys": {
                "consolidated_cutblocks_2020",
            },
            "tokens": {"consolidated", "cutblocks"},
            "cycle_year": 2024,
            "query_years": (2020,),
            "is_stale_year_stamped": False,
        },
    )

    linked = tsr_recipes._link_thlb_step_to_sources(
        "Use consolidated cutblocks to identify recent harvest history.",
        source_index=source_index,
    )

    assert linked == ("consolidated_cutblocks_2020",)


def test_describe_exact_thlb_step_logic_reports_operation_details() -> None:
    description = tsr_recipes._describe_exact_thlb_step_logic(
        {
            "compiled_operation_type": "curve_volume_threshold_exclusion",
            "curve_volume_metric": "volume_at_age",
            "curve_volume_age_years": 160.0,
            "curve_volume_threshold_m3_per_ha": 67.1,
            "checkpoint_attribute_mode": "all",
            "checkpoint_attribute_filters": [
                {
                    "field": "femic_step13_steep_slope_flag",
                    "operator": "eq",
                    "value": False,
                }
            ],
        }
    )

    assert "age 160" in description
    assert "67.100 m3/ha" in description
    assert "femic_step13_steep_slope_flag" in description


def test_thlb_status_report_prefers_parent_steps_when_present() -> None:
    recipe = tsr_recipes.TsrThlbNetdownRecipeRecord(
        schema_version=1,
        recipe_kind="thlb_netdown",
        tsa=tsr_catalog.TsrOverlayTsaRecord(
            tsa_id="tsa_29",
            tsa_code="29",
            tsa_name="Williams Lake",
        ),
        canonical_inputs=tsr_catalog.TsrRecipeCanonicalInputs(
            registry_path="metadata/tsr/tsa_registry.json",
            documents_path="metadata/tsr/tsa_documents.json",
            candidate_facts_path="metadata/tsr/tsa_candidate_facts.json",
        ),
        instance_inputs=tsr_catalog.TsrThlbNetdownRecipeInstanceInputs(
            overlay_path="config/tsr/overlay.yaml",
            source_layer_recipe_path="config/tsr/source_layers.recipe.yaml",
            source_layer_overrides_path="config/tsr/source_layer_overrides.yaml",
        ),
        recipe_contract={
            "lock_state": {
                "aflb": {
                    "locked": True,
                    "locked_utc": "2026-04-10T01:02:03+00:00",
                    "locked_script_path": "workbench/tsr/thlb_netdown.locked.py",
                    "frozen_status_report_path": "workbench/tsr/frozen/aflb.md",
                    "note": "AFLB universe definition locked",
                },
                "thlb": {
                    "locked": False,
                    "note": "THLB lock remains inactive until explicitly locked after AFLB",
                },
            }
        },
        parent_steps=(
            {
                "parent_step_id": "thlb_parent_001_land_not_administered",
                "parent_label": "Land not administered by the Province",
                "parent_kind": "transformation",
                "row_order": 1,
                "land_base_stage": "glb_to_aflb",
                "stage_label": "GLB -> AFLB",
                "execution_class": "drop_from_universe",
                "benchmark_marginal_area_ha": 697033.0,
                "benchmark_cumulative_area_ha": 4236602.0,
                "table_provenance": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=24",
                "subsection_number": "6.2.1",
                "subsection_title": "Land not administered by the Province for TSA timber supply",
                "supporting_provenance_ids": [
                    "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=25"
                ],
                "draft_subrules": [
                    {
                        "subrule_id": "draft_01",
                        "human_summary": "Exclude privately held lands and federal lands from AFLB.",
                        "candidate_operation_type": "exclude",
                        "review_status": "draft",
                        "candidate_layers": ["whse_f_own"],
                        "candidate_fields": ["OWNERSHIP_CODE"],
                        "candidate_values": ["private", "federal"],
                        "field_mapping_notes": [
                            "Validate the reviewed ownership-code mapping against the current layer."
                        ],
                    }
                ],
                "compiled_logic": [
                    {
                        "step_id": "thlb_parent_001_land_not_administered_compiled_01",
                        "label": "Exclude private and federal lands",
                    }
                ],
            },
        ),
        steps=(
            {
                "step_id": "thlb_parent_001_land_not_administered_compiled_01",
                "parent_step_id": "thlb_parent_001_land_not_administered",
                "label": "Land not administered by the Province",
                "order_index": 1,
                "step_kind": "netdown_rule",
                "land_base_stage": "glb_to_aflb",
                "stage_label": "GLB -> AFLB",
                "execution_class": "drop_from_universe",
                "run_status": "blocked_missing_source",
                "step_status": "blocked_missing_source",
                "normalized_action": "exclude",
                "compiled_operation_type": "select_spatial_intersect",
                "normalized_subject": "Land not administered by the Province",
                "normalized_predicate": "",
                "linked_source_entry_ids": ["whse_f_own"],
                "source_attribute_mode": "all",
                "source_attribute_filters": [
                    {
                        "field": "OWNERSHIP_CODE",
                        "operator": "in",
                        "value": ["private", "federal"],
                    }
                ],
                "notes": [],
                "run_notes": ["No fetched polygon artifact was available."],
            },
        ),
    )

    markdown = tsr_recipes._build_tsr_thlb_status_report_markdown(
        recipe=recipe,
        recipe_relative_path="config/tsr/thlb_netdown.recipe.yaml",
        checkpoint_relative_path="data/ria_vri_vclr1p_checkpoint1.feather",
        output_relative_path="data/tsr/thlb_reconstructed_checkpoint.feather",
        audit_relative_path="config/tsr/thlb_reconstructed.audit.json",
        execution_mode="reconstructed",
        allow_stand_binary_fallback=False,
        baseline_signal="checkpoint1_aflb_initialization",
        selected_map_ids=("092O071",),
        input_area_ha=27072.529,
        baseline_managed_area_ha=26350.175,
        final_managed_area_ha=25690.668,
        legacy_reference_managed_area_ha=1513233.574,
        tsr_reported_aflb_area_ha=3098168.0,
        tsr_reported_thlb_area_ha=1660053.0,
        outcome_counts={"blocked_missing_source": 1},
        step_count=1,
        generated_utc="2026-04-05T20:34:26Z",
        runtime_report_relative_path="runtime/logs/tsr/example.md",
        reconstruction_comparison_markdown_relative_path=(
            "config/tsr/thlb_reconstruction_comparison.md"
        ),
        applied_steps=recipe.steps,
        diagnostic_steps=[
            {
                "step_id": "thlb_parent_001_land_not_administered_compiled_01",
                "label": "Land not administered by the Province",
                "normalized_action": "exclude",
                "spatial_application_mode": "blocked_exact_overlay",
                "run_status": "blocked_missing_source",
                "total_seconds": 12.5,
                "source_load_seconds": 0.5,
                "candidate_query_seconds": 2.0,
                "overlay_seconds": 0.0,
                "write_seconds": 0.0,
                "merge_seconds": 0.0,
                "lu_chunk_count": 0,
                "intersecting_exclusion_feature_count": 0,
            }
        ],
        source_entry_map={
            "whse_f_own": {
                "entry_id": "whse_f_own",
                "recommended_query": "WHSE_FOREST_VEGETATION.F_OWN",
                "current_public_status": "exact_hit",
                "acquisition_strategy": "wfs_fetch",
                "artifact_path": "data/downloads/bcdc/F_OWN/F_OWN.gpkg",
                "matched_by": "object_name:WHSE_FOREST_VEGETATION.F_OWN",
                "top_match_title": "Generalized Forest Cover Ownership",
            }
        },
        override_entries={
            "whse_forest_vegetation.f_own": tsr_recipes.TsrSourceLayerOverrideEntry(
                query="WHSE_FOREST_VEGETATION.F_OWN",
                current_public_status="exact_hit",
                matched_by="object_name",
                top_match_title="Generalized Forest Cover Ownership",
                dataset_page_url="https://example.invalid/f_own",
                suggested_fetch_strategy="wfs_fetch",
                current_public_notes=(),
                override_kind="replacement_layer",
                override_value="local reviewed ownership layer",
                notes="Use reviewed ownership mapping for TSA29.",
            )
        },
    )

    assert "## Review Dashboard" in markdown
    assert "## Locking / Convergence" in markdown
    assert "Benchmark marginal deduction" in markdown
    assert "Draft subrules:" in markdown
    assert "Supporting prose section" in markdown
    assert "Land not administered by the Province" in markdown
    assert "Review logic mode: `user_overlay`" in markdown
    assert "Exact FEMIC logic:" in markdown
    assert "Intersect the working land base" in markdown
    assert "AFLB lock state: `locked`" in markdown
    assert "frozen status report" in markdown
    assert (
        "Reconstruction comparison: `config/tsr/thlb_reconstruction_comparison.md`"
        in markdown
    )
    assert "Active user overrides:" in markdown
    assert "`None`" not in markdown
    assert "candidate fields" in markdown
    assert "candidate values" in markdown
    assert "field/value mapping notes" in markdown
    assert "Current compiled status summary" in markdown


def test_thlb_recipe_build_report_uses_parent_steps_and_stage_counts() -> None:
    record = tsr_recipes.TsrThlbNetdownRecipeRecord(
        schema_version=1,
        recipe_kind="thlb_netdown",
        tsa=tsr_catalog.TsrOverlayTsaRecord(
            tsa_id="tsa_29",
            tsa_code="29",
            tsa_name="Williams Lake",
        ),
        canonical_inputs=tsr_catalog.TsrRecipeCanonicalInputs(
            registry_path="metadata/tsr/tsa_registry.json",
            documents_path="metadata/tsr/tsa_documents.json",
            candidate_facts_path="metadata/tsr/tsa_candidate_facts.json",
        ),
        instance_inputs=tsr_catalog.TsrThlbNetdownRecipeInstanceInputs(
            overlay_path="config/tsr/overlay.yaml",
            source_layer_recipe_path="config/tsr/source_layers.recipe.yaml",
            source_layer_overrides_path="config/tsr/source_layer_overrides.yaml",
        ),
        recipe_contract={
            "selected_document_paths": [
                "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf",
            ]
        },
        parent_steps=(
            {
                "parent_step_id": "thlb_parent_001_total_tsa_area",
                "parent_label": "Total TSA area",
                "parent_kind": "milestone",
                "row_order": 1,
                "land_base_stage": "reference_target",
                "stage_label": "Reference targets",
                "execution_class": "reference_only",
                "benchmark_marginal_area_ha": None,
                "benchmark_cumulative_area_ha": 4933635.0,
                "table_provenance": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=24",
                "subsection_number": "",
                "subsection_title": "",
                "supporting_provenance_ids": [],
                "draft_subrules": [],
                "compiled_logic": [
                    {
                        "step_id": "thlb_parent_001_total_tsa_area_compiled_01",
                    }
                ],
            },
            {
                "parent_step_id": "thlb_parent_003_non_forest",
                "parent_label": "Non-forest",
                "parent_kind": "transformation",
                "row_order": 3,
                "land_base_stage": "glb_to_aflb",
                "stage_label": "GLB -> AFLB",
                "execution_class": "drop_from_universe",
                "benchmark_marginal_area_ha": 1105908.0,
                "benchmark_cumulative_area_ha": 3130694.0,
                "table_provenance": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=24",
                "subsection_number": "6.2.2",
                "subsection_title": "Land classified as non-forest",
                "supporting_provenance_ids": [],
                "draft_subrules": [
                    {
                        "subrule_id": "draft_non_forest_01",
                        "human_summary": "The VRI attribute FMLB will be used to identify areas of non-forest.",
                        "candidate_operation_type": "exclude",
                        "review_status": "draft",
                        "candidate_layers": ["vri"],
                        "candidate_fields": ["FOR_MGMT_LAND_BASE_IND"],
                        "candidate_values": [],
                        "field_mapping_notes": ["Validate FMLB mapping."],
                    }
                ],
                "compiled_logic": [
                    {
                        "step_id": "thlb_parent_003_non_forest_compiled_01",
                    }
                ],
            },
        ),
        steps=(
            {
                "step_id": "thlb_parent_003_non_forest_compiled_01",
                "parent_step_id": "thlb_parent_003_non_forest",
                "label": "Non-forest",
                "order_index": 3,
                "step_kind": "netdown_rule",
                "land_base_stage": "glb_to_aflb",
                "stage_label": "GLB -> AFLB",
                "execution_class": "drop_from_universe",
                "run_status": "ready",
                "step_status": "ready",
                "normalized_action": "exclude",
                "normalized_subject": "Non-forest",
                "normalized_predicate": "",
                "linked_source_entry_ids": [],
                "notes": [],
                "run_notes": [],
            },
        ),
    )
    markdown = tsr_recipes._build_tsr_thlb_recipe_build_report_markdown(
        recipe=record,
        recipe_relative_path="config/tsr/thlb_netdown.recipe.yaml",
        source_layer_recipe_relative_path="config/tsr/source_layers.recipe.yaml",
        generated_utc="2026-04-05T22:30:00Z",
        runtime_report_relative_path="runtime/logs/tsr/example-build.md",
        source_entry_map={},
        override_entries={},
    )
    assert "THLB Recipe Build Report" in markdown
    assert "Report mode: `recipe_build`" in markdown
    assert "## Review Dashboard" in markdown
    assert "## Stage Counts" in markdown
    assert "## Locking / Convergence" in markdown
    assert "Selected TSR documents" in markdown
    assert "Backbone Milestones" in markdown
    assert "Total TSA area" in markdown
    assert "`GLB -> AFLB`: `1`" in markdown
    assert "candidate fields" in markdown
    assert "Current compiled status summary" in markdown


def test_tsr_thlb_reconstruction_comparison_payload_buckets_parent_steps() -> None:
    recipe = tsr_recipes.TsrThlbNetdownRecipeRecord(
        schema_version=1,
        recipe_kind="thlb_netdown",
        tsa=tsr_catalog.TsrOverlayTsaRecord(
            tsa_id="tsa_29",
            tsa_code="29",
            tsa_name="Williams Lake",
        ),
        canonical_inputs=tsr_catalog.TsrRecipeCanonicalInputs(
            registry_path="metadata/tsr/tsa_registry.json",
            documents_path="metadata/tsr/tsa_documents.json",
            candidate_facts_path="metadata/tsr/tsa_candidate_facts.json",
        ),
        instance_inputs=tsr_catalog.TsrThlbNetdownRecipeInstanceInputs(
            overlay_path="config/tsr/overlay.yaml",
            source_layer_recipe_path="config/tsr/source_layers.recipe.yaml",
            source_layer_overrides_path="config/tsr/source_layer_overrides.yaml",
        ),
        recipe_contract={},
        parent_steps=(
            {
                "parent_step_id": "thlb_parent_001_total_tsa_area",
                "parent_label": "Total TSA area",
                "parent_kind": "milestone",
                "row_order": 1,
                "land_base_stage": "reference_target",
                "stage_label": "Reference targets",
                "benchmark_cumulative_area_ha": 1000.0,
            },
            {
                "parent_step_id": "thlb_parent_002_land_not_administered",
                "parent_label": "Land not administered",
                "parent_kind": "transformation",
                "row_order": 2,
                "land_base_stage": "glb_to_aflb",
                "stage_label": "GLB -> AFLB",
                "benchmark_marginal_area_ha": 200.0,
                "benchmark_cumulative_area_ha": 800.0,
                "last_notebook_run_status": "applied",
                "last_removed_area_ha": 210.0,
                "last_remaining_area_ha": 790.0,
            },
            {
                "parent_step_id": "thlb_parent_003_reviewed_bridge",
                "parent_label": "Reviewed bridge",
                "parent_kind": "transformation",
                "row_order": 3,
                "land_base_stage": "aflb_to_lhlb",
                "stage_label": "AFLB -> LHLB",
                "benchmark_marginal_area_ha": 120.0,
                "benchmark_cumulative_area_ha": 680.0,
                "last_notebook_run_status": "applied",
                "last_removed_area_ha": 125.0,
                "last_remaining_area_ha": 665.0,
            },
            {
                "parent_step_id": "thlb_parent_004_strict_overcut",
                "parent_label": "Strict overcut",
                "parent_kind": "transformation",
                "row_order": 4,
                "land_base_stage": "aflb_to_lhlb",
                "stage_label": "AFLB -> LHLB",
                "benchmark_marginal_area_ha": 75.0,
                "benchmark_cumulative_area_ha": 605.0,
                "last_notebook_run_status": "applied",
                "last_removed_area_ha": 70.0,
                "last_remaining_area_ha": 595.0,
            },
            {
                "parent_step_id": "thlb_parent_005_strict_undercut",
                "parent_label": "Strict undercut",
                "parent_kind": "transformation",
                "row_order": 5,
                "land_base_stage": "lhlb_to_thlb",
                "stage_label": "LHLB -> THLB",
                "benchmark_marginal_area_ha": 300.0,
                "benchmark_cumulative_area_ha": 305.0,
                "last_notebook_run_status": "applied",
                "last_removed_area_ha": 300.0,
                "last_remaining_area_ha": 295.0,
            },
            {
                "parent_step_id": "thlb_parent_006_manual_override",
                "parent_label": "Manual override",
                "parent_kind": "transformation",
                "row_order": 6,
                "land_base_stage": "lhlb_to_thlb",
                "stage_label": "LHLB -> THLB",
                "benchmark_marginal_area_ha": 90.0,
                "benchmark_cumulative_area_ha": 215.0,
                "last_notebook_run_status": "applied_noop",
                "last_removed_area_ha": 0.0,
                "last_remaining_area_ha": 295.0,
                "approval_scope": "user-directed calibrated skip",
                "compiled_logic": [
                    {
                        "step_id": "compiled_override_01",
                        "compiled_operation_type": "no_deduction",
                    }
                ],
            },
            {
                "parent_step_id": "thlb_parent_007_aspatial_bridge",
                "parent_label": "Aspatial bridge",
                "parent_kind": "transformation",
                "row_order": 7,
                "land_base_stage": "lhlb_to_thlb",
                "stage_label": "LHLB -> THLB",
                "benchmark_marginal_area_ha": 50.0,
                "benchmark_cumulative_area_ha": 165.0,
                "last_notebook_run_status": "applied",
                "last_removed_area_ha": 45.0,
                "last_remaining_area_ha": 250.0,
            },
            {
                "parent_step_id": "thlb_parent_008_blocked_source",
                "parent_label": "Blocked source",
                "parent_kind": "transformation",
                "row_order": 8,
                "land_base_stage": "lhlb_to_thlb",
                "stage_label": "LHLB -> THLB",
                "benchmark_marginal_area_ha": 40.0,
                "benchmark_cumulative_area_ha": 125.0,
                "last_notebook_run_status": "blocked_missing_source",
                "last_removed_area_ha": None,
                "last_remaining_area_ha": None,
            },
        ),
        steps=(),
    )
    reconstructed_audit_payload = {
        "final_managed_area_ha": 100.0,
        "tsr_reported_thlb_area_ha": 1000.0,
        "steps": [
            {
                "step_id": "compiled_002",
                "parent_step_id": "thlb_parent_002_land_not_administered",
                "affected_area_ha": 205.0,
                "run_status": "applied",
                "spatial_application_mode": "fragment_overlay",
            },
            {
                "step_id": "compiled_004",
                "parent_step_id": "thlb_parent_004_strict_overcut",
                "affected_area_ha": 200.0,
                "run_status": "applied",
                "spatial_application_mode": "fragment_overlay",
            },
            {
                "step_id": "compiled_005",
                "parent_step_id": "thlb_parent_005_strict_undercut",
                "affected_area_ha": 101.0,
                "run_status": "applied",
                "spatial_application_mode": "fragment_overlay",
            },
            {
                "step_id": "compiled_007",
                "parent_step_id": "thlb_parent_007_aspatial_bridge",
                "affected_area_ha": 48.0,
                "run_status": "applied",
                "spatial_application_mode": "aspatial_fallback",
            },
            {
                "step_id": "compiled_008",
                "parent_step_id": "thlb_parent_008_blocked_source",
                "affected_area_ha": 0.0,
                "run_status": "blocked_missing_source",
                "spatial_application_mode": "blocked_exact_overlay",
            },
        ],
    }

    payload = tsr_recipes._build_tsr_thlb_reconstruction_comparison_payload(
        recipe=recipe,
        reconstructed_audit_payload=reconstructed_audit_payload,
        recipe_relative_path="config/tsr/thlb_netdown.recipe.yaml",
        reviewed_status_relative_path="config/tsr/thlb_netdown.status.md",
        reconstructed_audit_relative_path="config/tsr/thlb_reconstructed.audit.json",
        comparison_markdown_relative_path="config/tsr/thlb_reconstruction_comparison.md",
        comparison_json_relative_path="config/tsr/thlb_reconstruction_comparison.json",
    )
    entries_by_id = {
        str(item["parent_step_id"]): item
        for item in payload["entries"]
        if isinstance(item, dict)
    }

    assert payload["strict_vs_tsr_delta_ha"] == pytest.approx(-900.0)
    assert payload["reviewed_vs_tsr_delta_ha"] == pytest.approx(-750.0)
    assert (
        entries_by_id["thlb_parent_001_total_tsa_area"]["comparison_bucket"]
        == "not_comparable"
    )
    assert (
        entries_by_id["thlb_parent_002_land_not_administered"]["comparison_bucket"]
        == "close_match"
    )
    assert (
        entries_by_id["thlb_parent_003_reviewed_bridge"]["comparison_bucket"]
        == "reviewed_bridge_only"
    )
    assert (
        entries_by_id["thlb_parent_004_strict_overcut"]["comparison_bucket"]
        == "strict_overcut_candidate"
    )
    assert (
        entries_by_id["thlb_parent_005_strict_undercut"]["comparison_bucket"]
        == "strict_undercut_candidate"
    )
    assert (
        entries_by_id["thlb_parent_006_manual_override"]["comparison_bucket"]
        == "manual_or_reviewed_override"
    )
    assert (
        entries_by_id["thlb_parent_007_aspatial_bridge"]["comparison_bucket"]
        == "aspatial_bridge_difference"
    )
    assert (
        entries_by_id["thlb_parent_008_blocked_source"]["comparison_bucket"]
        == "blocked_or_missing_source"
    )

    markdown = tsr_recipes._build_tsr_thlb_reconstruction_comparison_markdown(
        recipe=recipe,
        comparison_payload=payload,
    )

    assert "THLB Reconstruction Comparison" in markdown
    assert "Top 5 Parent-Step Contributors" in markdown
    assert "Strict vs TSR delta" in markdown
    assert "strict_overcut_candidate" in markdown
    assert "reviewed bridge" in markdown.casefold()


def test_resolve_reviewed_thlb_remaining_area_ignores_tail_no_deduction_steps() -> (
    None
):
    recipe = tsr_recipes.TsrThlbNetdownRecipeRecord(
        schema_version=1,
        recipe_kind="thlb_netdown",
        tsa=tsr_catalog.TsrOverlayTsaRecord(
            tsa_id="tsa_29",
            tsa_code="29",
            tsa_name="Williams Lake",
        ),
        canonical_inputs=tsr_catalog.TsrRecipeCanonicalInputs(
            registry_path="metadata/tsr/tsa_registry.json",
            documents_path="metadata/tsr/tsa_documents.json",
            candidate_facts_path="metadata/tsr/tsa_candidate_facts.json",
        ),
        instance_inputs=tsr_catalog.TsrThlbNetdownRecipeInstanceInputs(
            overlay_path="config/tsr/overlay.yaml",
            source_layer_recipe_path="config/tsr/source_layers.recipe.yaml",
            source_layer_overrides_path="config/tsr/source_layer_overrides.yaml",
        ),
        recipe_contract={},
        parent_steps=(
            {
                "parent_step_id": "thlb_parent_021_cultural_heritage",
                "parent_label": "Cultural heritage",
                "parent_kind": "transformation",
                "row_order": 21,
                "land_base_stage": "lhlb_to_thlb",
                "stage_label": "LHLB -> THLB",
                "last_remaining_area_ha": 1649049.232214973,
            },
            {
                "parent_step_id": "thlb_parent_023_future_roads",
                "parent_label": "Future roads",
                "parent_kind": "transformation",
                "row_order": 23,
                "land_base_stage": "lhlb_to_thlb",
                "stage_label": "LHLB -> THLB",
                "normalized_action": "no_deduction",
                "last_remaining_area_ha": 1592878.9364607423,
                "compiled_logic": [
                    {
                        "step_id": "thlb_parent_023_future_roads_compiled_01",
                        "compiled_operation_type": "no_deduction",
                    }
                ],
            },
        ),
        steps=(),
    )

    assert tsr_recipes._resolve_reviewed_thlb_remaining_area_ha(recipe) == pytest.approx(
        1649049.232214973
    )


def test_merge_preserved_thlb_parent_step_metadata_keeps_approved_review_logic() -> (
    None
):
    merged = tsr_recipes._merge_preserved_thlb_parent_step_metadata(
        existing_parent_steps=(
            {
                "parent_step_id": "thlb_parent_023_future_roads",
                "ratchet_state": "approved",
                "draft_subrules": [
                    {
                        "subrule_id": "draft_01",
                        "candidate_operation_type": "no_deduction",
                    }
                ],
                "compiled_logic": [
                    {
                        "step_id": "compiled_01",
                        "compiled_operation_type": "no_deduction",
                    }
                ],
            },
        ),
        built_parent_steps=(
            {
                "parent_step_id": "thlb_parent_023_future_roads",
                "draft_subrules": [
                    {
                        "subrule_id": "draft_01",
                        "candidate_operation_type": "aspatial_area_reduction",
                    }
                ],
                "compiled_logic": [
                    {
                        "step_id": "compiled_01",
                        "compiled_operation_type": "aspatial_area_reduction",
                    }
                ],
            },
        ),
    )

    assert merged[0]["draft_subrules"][0]["candidate_operation_type"] == "no_deduction"
    assert merged[0]["compiled_logic"][0]["compiled_operation_type"] == "no_deduction"


def test_merge_preserved_thlb_compiled_steps_keeps_approved_review_logic() -> None:
    merged = tsr_recipes._merge_preserved_thlb_compiled_steps(
        existing_steps=(
            {
                "step_id": "compiled_01",
                "parent_step_id": "thlb_parent_023_future_roads",
                "compiled_operation_type": "no_deduction",
                "normalized_action": "no_deduction",
            },
        ),
        built_steps=(
            {
                "step_id": "compiled_01",
                "parent_step_id": "thlb_parent_023_future_roads",
                "compiled_operation_type": "aspatial_area_reduction",
                "normalized_action": "aspatial_area_reduction",
                "stage_label": "LHLB -> THLB",
            },
        ),
        parent_steps=(
            {
                "parent_step_id": "thlb_parent_023_future_roads",
                "ratchet_state": "approved",
                "compiled_logic": [
                    {
                        "step_id": "compiled_01",
                        "compiled_operation_type": "no_deduction",
                        "normalized_action": "no_deduction",
                    }
                ],
            },
        ),
    )

    assert merged[0]["compiled_operation_type"] == "no_deduction"
    assert merged[0]["normalized_action"] == "no_deduction"
    assert merged[0]["stage_label"] == "LHLB -> THLB"


def test_format_thlb_lock_state_markdown_skips_placeholder_none_strings() -> None:
    markdown_lines = tsr_recipes._format_thlb_lock_state_markdown(
        {
            "aflb": {
                "locked": False,
                "locked_utc": "None",
                "locked_script_path": "null",
                "frozen_status_report_path": "",
                "frozen_audit_path": None,
                "note": "None",
            },
            "thlb": {
                "locked": True,
                "locked_utc": "2026-04-10T00:00:00Z",
                "locked_script_path": "scripts/example.py",
                "frozen_status_report_path": "workbench/status.md",
                "frozen_audit_path": "runtime/audit.json",
                "note": "Pinned for review.",
            },
        }
    )

    markdown = "\n".join(markdown_lines)
    assert "AFLB lock state: `unlocked`" in markdown
    assert "THLB lock state: `locked`" in markdown
    assert "`None`" not in markdown
    assert "null" not in markdown
    assert "Pinned for review." in markdown


def test_build_tsr_source_layers_recipe_populates_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    monkeypatch.setattr(
        tsr_recipes,
        "report_tsr_candidate_facts",
        lambda **_kwargs: type(
            "Result",
            (),
            {
                "rows": (
                    tsr_recipes.TsrFactReviewRow(
                        tsa_id="tsa_29",
                        tsa_code="29",
                        tsa_name="Williams Lake",
                        fact_family="source_layer_candidate",
                        extracted_value="WHSE_FOREST_VEGETATION.F_OWN",
                        recommended_query="WHSE_FOREST_VEGETATION.F_OWN",
                        quality="likely_useful",
                        quality_reason="BCGW object-name style token",
                        snippet="F_OWN source",
                        page_number=12,
                        title="TSA29 data package",
                        cycle_label="Current",
                        cycle_year=2024,
                        provenance_id="doc:12",
                        source_url="https://example.invalid/doc.pdf",
                    ),
                )
            },
        )(),
    )
    monkeypatch.setattr(
        tsr_recipes,
        "resolve_bcdc_candidates",
        lambda query, *, limit=5: type(
            "ResolveResult",
            (),
            {
                "query": query,
                "notes": (),
                "top_match": type(
                    "TopMatch",
                    (),
                    {
                        "title": "Generalized Forest Cover Ownership",
                        "dataset_page_url": "https://example.invalid/fown",
                        "matched_by": "object_name:WHSE_FOREST_VEGETATION.F_OWN",
                        "suggested_fetch_strategy": "wfs_getfeature_bbox",
                        "manual_follow_up": (),
                        "resources": (
                            type(
                                "Resource",
                                (),
                                {
                                    "classification": "service",
                                    "wfs_queryable": True,
                                },
                            )(),
                        ),
                        "direct_download_resources": (),
                    },
                )(),
            },
        )(),
    )

    result = tsr_catalog.build_tsr_source_layers_recipe(
        recipe_path=init_result.source_layers_recipe_path,
        source_root=source_root,
    )

    assert result.entry_count == 1
    recipe = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    )
    entry = recipe.entries[0]
    assert entry["recommended_query"] == "WHSE_FOREST_VEGETATION.F_OWN"
    assert entry["current_public_status"] == "exact_hit"
    assert entry["acquisition_strategy"] == "wfs_fetch"
    assert entry["suggested_fetch_strategy"] == "wfs_getfeature_bbox"


def test_run_tsr_source_layers_recipe_reuses_existing_artifact(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    artifact_path = (
        instance_root / "data" / "downloads" / "bcdc" / "F_OWN" / "F_OWN.gpkg"
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {"OWNERSHIP_DESCRIPTION": ["Private"]},
        geometry=[box(1, 2, 3, 4)],
        crs="EPSG:3005",
    ).to_file(artifact_path, driver="GPKG")
    overlay_path = instance_root / "config" / "tsr" / "overlay.yaml"
    overlay_path.write_text(
        tsr_recipes.yaml.safe_dump(
            {"bcdc_acquisition_review": {"bbox_epsg3005": [1.0, 2.0, 3.0, 4.0]}},
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["entries"] = [
        {
            "entry_id": "whse_f_own",
            "label": "WHSE_FOREST_VEGETATION.F_OWN",
            "recommended_query": "WHSE_FOREST_VEGETATION.F_OWN",
            "current_public_status": "exact_hit",
            "acquisition_strategy": "wfs_fetch",
            "artifact_path": "data/downloads/bcdc/F_OWN/F_OWN.gpkg",
            "override_kind": "",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_catalog.run_tsr_source_layers_recipe(
        recipe_path=init_result.source_layers_recipe_path,
        bbox_epsg3005=(1.0, 2.0, 3.0, 4.0),
    )

    assert result.outcome_counts["reused"] == 1
    recipe = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    )
    assert recipe.entries[0]["run_status"] == "reused"
    assert recipe.entries[0]["artifact_scope"] == "production_full_tsa"
    assert recipe.entries[0]["requested_bbox_epsg3005"] == [1.0, 2.0, 3.0, 4.0]
    assert recipe.entries[0]["artifact_extent_bbox_epsg3005"] == [1.0, 2.0, 3.0, 4.0]


def test_run_tsr_source_layers_recipe_dwds_order_persists_manifest_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    monkeypatch.setattr(
        tsr_recipes,
        "submit_bcdc_dwds_order",
        lambda *args, **kwargs: _sample_dwds_order_result(),
    )
    recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["entries"] = [
        {
            "entry_id": "whse_forest_vegetation_gry_psp_status_active",
            "label": "Growth and Yield Samples - All Status",
            "recommended_query": "WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
            "acquisition_query": "WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
            "current_public_status": "exact_hit",
            "acquisition_strategy": "dwds_order",
            "artifact_path": "",
            "override_kind": "",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_catalog.run_tsr_source_layers_recipe(
        recipe_path=init_result.source_layers_recipe_path,
        bbox_epsg3005=(1.0, 2.0, 3.0, 4.0),
        allow_order=True,
    )

    assert result.outcome_counts["ordered"] == 1
    recipe = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    )
    entry = recipe.entries[0]
    assert entry["run_status"] == "ordered"
    assert entry["order_id"] == "2551000"
    assert entry["submission_status"] == "SUCCESS"
    assert entry["order_manifest_path"] == (
        "runtime/logs/tsr/dwds_orders/"
        "whse_forest_vegetation_gry_psp_status_active_order_manifest.json"
    )
    manifest_path = instance_root / entry["order_manifest_path"]
    assert manifest_path.exists()
    manifest_orders = bcdc_dwds.load_bcdc_dwds_manifest(manifest_path)
    assert manifest_orders[0].order_id == "2551000"


def test_run_tsr_source_layers_recipe_dwds_followup_materializes_without_resubmitting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    artifact_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_FOREST_VEGETATION_GRY_PSP_STATUS_ACTIVE"
        / "GRY_PSP_STATUS_ACTIVE.gpkg"
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {"STATUS": ["ACTIVE"]},
        geometry=[box(1, 2, 3, 4)],
        crs="EPSG:3005",
    ).to_file(artifact_path, driver="GPKG")
    manifest_path = (
        instance_root
        / "runtime"
        / "logs"
        / "tsr"
        / "dwds_orders"
        / "whse_forest_vegetation_gry_psp_status_active_order_manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    bcdc_dwds.write_bcdc_dwds_manifest([_sample_dwds_order_result()], manifest_path)
    monkeypatch.setattr(
        tsr_recipes,
        "submit_bcdc_dwds_order",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("submit_bcdc_dwds_order should not be called")
        ),
    )
    monkeypatch.setattr(
        tsr_recipes,
        "follow_up_bcdc_dwds_order",
        lambda order_result, **kwargs: replace(
            order_result,
            materialized_artifact_path=str(artifact_path),
            materialized_download_url="https://distribution.data.gov.bc.ca/example.gpkg",
        ),
    )
    recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "run"
    recipe_payload["entries"] = [
        {
            "entry_id": "whse_forest_vegetation_gry_psp_status_active",
            "label": "Growth and Yield Samples - All Status",
            "recommended_query": "WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
            "acquisition_query": "WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
            "current_public_status": "exact_hit",
            "acquisition_strategy": "dwds_order",
            "artifact_path": "",
            "order_manifest_path": "runtime/logs/tsr/dwds_orders/whse_forest_vegetation_gry_psp_status_active_order_manifest.json",
            "override_kind": "",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_catalog.run_tsr_source_layers_recipe(
        recipe_path=init_result.source_layers_recipe_path,
        bbox_epsg3005=(1.0, 2.0, 3.0, 4.0),
        allow_order=False,
    )

    assert result.outcome_counts["materialized"] == 1
    recipe = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    )
    entry = recipe.entries[0]
    assert entry["run_status"] == "materialized"
    assert entry["artifact_path"] == (
        "data/downloads/bcdc/WHSE_FOREST_VEGETATION_GRY_PSP_STATUS_ACTIVE/"
        "GRY_PSP_STATUS_ACTIVE.gpkg"
    )
    assert entry["artifact_extent_bbox_epsg3005"] == [1.0, 2.0, 3.0, 4.0]
    manifest_orders = bcdc_dwds.load_bcdc_dwds_manifest(manifest_path)
    assert manifest_orders[0].materialized_artifact_path == str(artifact_path)


def test_run_tsr_source_layers_recipe_reuses_materialized_dwds_manifest_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    artifact_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_FOREST_VEGETATION_GRY_PSP_STATUS_ACTIVE"
        / "GRY_PSP_STATUS_ACTIVE.gpkg"
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {"STATUS": ["ACTIVE"]},
        geometry=[box(1, 2, 3, 4)],
        crs="EPSG:3005",
    ).to_file(artifact_path, driver="GPKG")
    manifest_path = (
        instance_root
        / "runtime"
        / "logs"
        / "tsr"
        / "dwds_orders"
        / "whse_forest_vegetation_gry_psp_status_active_order_manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    bcdc_dwds.write_bcdc_dwds_manifest(
        [
            replace(
                _sample_dwds_order_result(),
                materialized_artifact_path=str(artifact_path),
            )
        ],
        manifest_path,
    )
    monkeypatch.setattr(
        tsr_recipes,
        "follow_up_bcdc_dwds_order",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("follow_up_bcdc_dwds_order should not be called")
        ),
    )
    recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "run"
    recipe_payload["entries"] = [
        {
            "entry_id": "whse_forest_vegetation_gry_psp_status_active",
            "label": "Growth and Yield Samples - All Status",
            "recommended_query": "WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
            "acquisition_query": "WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
            "current_public_status": "exact_hit",
            "acquisition_strategy": "dwds_order",
            "artifact_path": "",
            "order_manifest_path": "runtime/logs/tsr/dwds_orders/whse_forest_vegetation_gry_psp_status_active_order_manifest.json",
            "override_kind": "",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_catalog.run_tsr_source_layers_recipe(
        recipe_path=init_result.source_layers_recipe_path,
        bbox_epsg3005=(1.0, 2.0, 3.0, 4.0),
        allow_order=False,
    )

    assert result.outcome_counts["materialized"] == 1
    recipe = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    )
    assert recipe.entries[0]["run_status"] == "materialized"
    assert recipe.entries[0]["artifact_path"] == (
        "data/downloads/bcdc/WHSE_FOREST_VEGETATION_GRY_PSP_STATUS_ACTIVE/"
        "GRY_PSP_STATUS_ACTIVE.gpkg"
    )


def test_run_tsr_source_layers_recipe_dwds_followup_pending_does_not_resubmit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    manifest_path = (
        instance_root
        / "runtime"
        / "logs"
        / "tsr"
        / "dwds_orders"
        / "whse_forest_vegetation_gry_psp_status_active_order_manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    bcdc_dwds.write_bcdc_dwds_manifest([_sample_dwds_order_result()], manifest_path)
    monkeypatch.setattr(
        tsr_recipes,
        "submit_bcdc_dwds_order",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("submit_bcdc_dwds_order should not be called")
        ),
    )
    monkeypatch.setattr(
        tsr_recipes,
        "follow_up_bcdc_dwds_order",
        lambda order_result, **kwargs: order_result,
    )
    recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "run"
    recipe_payload["entries"] = [
        {
            "entry_id": "whse_forest_vegetation_gry_psp_status_active",
            "label": "Growth and Yield Samples - All Status",
            "recommended_query": "WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
            "acquisition_query": "WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE",
            "current_public_status": "exact_hit",
            "acquisition_strategy": "dwds_order",
            "artifact_path": "",
            "order_manifest_path": "runtime/logs/tsr/dwds_orders/whse_forest_vegetation_gry_psp_status_active_order_manifest.json",
            "override_kind": "",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_catalog.run_tsr_source_layers_recipe(
        recipe_path=init_result.source_layers_recipe_path,
        bbox_epsg3005=(1.0, 2.0, 3.0, 4.0),
        allow_order=False,
    )

    assert result.outcome_counts["followup_pending"] == 1
    recipe = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    )
    entry = recipe.entries[0]
    assert entry["run_status"] == "followup_pending"
    assert entry["artifact_path"] == ""
    assert entry["order_manifest_path"] == (
        "runtime/logs/tsr/dwds_orders/"
        "whse_forest_vegetation_gry_psp_status_active_order_manifest.json"
    )


def test_run_tsr_thlb_parent_step_blocks_obvious_smoke_extent_mismatch(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    smoke_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "smoke"
        / "F_OWN"
        / "F_OWN_smoke.gpkg"
    )
    smoke_path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {"OWNERSHIP_DESCRIPTION": ["Private"]},
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    ).to_file(smoke_path, driver="GPKG")

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "run"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "whse_f_own",
            "label": "Generalized Forest Cover Ownership",
            "recommended_query": "WHSE_FOREST_VEGETATION.F_OWN",
            "acquisition_strategy": "wfs_fetch",
            "artifact_scope": "smoke_subset",
            "artifact_path": "data/downloads/bcdc/smoke/F_OWN/F_OWN_smoke.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["recipe_contract"]["recipe_build_status_report_path"] = (
        "config/tsr/thlb_netdown.status.md"
    )
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 100.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "thlb_parent_002_land_not_administered_by_the_province",
            "parent_label": "Land not administered by the Province",
            "parent_kind": "transformation",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "drop_from_universe",
            "benchmark_marginal_area_ha": 10.0,
            "benchmark_cumulative_area_ha": 90.0,
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_002_compiled_01",
                    "parent_step_id": "thlb_parent_002_land_not_administered_by_the_province",
                    "label": "Exclude private ownership polygons",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "land_base_stage": "glb_to_aflb",
                    "operation_type": "select_spatial_intersect",
                    "linked_source_entry_ids": ["whse_f_own"],
                }
            ],
            "row_order": 2,
        },
    ]
    recipe_payload["steps"] = [
        {
            "step_id": "thlb_parent_002_compiled_01",
            "parent_step_id": "thlb_parent_002_land_not_administered_by_the_province",
            "label": "Exclude private ownership polygons",
            "step_status": "ready",
            "execution_status": "ready",
            "step_kind": "netdown_rule",
            "land_base_stage": "glb_to_aflb",
        }
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    checkpoint_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1],
            "MAP_ID": ["092O071"],
        },
        geometry=[box(0, 0, 1000, 1000)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)

    result = tsr_recipes.run_tsr_thlb_parent_step(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_id="thlb_parent_002_land_not_administered_by_the_province",
        checkpoint_path=checkpoint_path,
        map_ids=("092O071",),
        auto_map_id_smoke_subset=False,
    )

    assert result.status == "blocked_extent_mismatch"
    assert result.removed_area_ha == pytest.approx(0.0)
    payload = json.loads(result.result_json_path.read_text(encoding="utf-8"))
    item = next(
        entry
        for entry in payload["executed_items"]
        if entry["parent_step_id"]
        == "thlb_parent_002_land_not_administered_by_the_province"
    )
    assert item["execution_status"] == "blocked_extent_mismatch"
    assert "smoke/aoi-scoped overlays" in " ".join(item["runtime_notes"]).lower()


def test_build_tsr_thlb_netdown_recipe_populates_steps_from_latest_data_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "built"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "whse_f_own",
            "label": "Generalized Forest Cover Ownership",
            "recommended_query": "WHSE_FOREST_VEGETATION.F_OWN",
            "top_match_title": "Generalized Forest Cover Ownership",
            "snippet": "F_OWN ownership layer",
        },
        {
            "entry_id": "mdwr",
            "label": "Mule Deer winter range",
            "recommended_query": "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP",
            "top_match_title": "Mule Deer winter range topographic buffers",
            "snippet": "Mule Deer winter range layer",
        },
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        tsr_recipes,
        "report_tsr_candidate_facts",
        lambda **_kwargs: type(
            "Result",
            (),
            {
                "rows": (
                    tsr_recipes.TsrFactReviewRow(
                        tsa_id="tsa_29",
                        tsa_code="29",
                        tsa_name="Williams Lake",
                        fact_family="thlb_reference",
                        extracted_value="6. Timber Harvesting Land Base Definition ........ 44",
                        recommended_query=(
                            "6. Timber Harvesting Land Base Definition ........ 44"
                        ),
                        quality="likely_noise",
                        quality_reason="TOC row",
                        snippet="6. Timber Harvesting Land Base Definition ........ 44",
                        page_number=4,
                        title="Williams Lake TSA data package 2024",
                        cycle_label="TSR 2024",
                        cycle_year=2024,
                        provenance_id="TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=4",
                        source_url="https://example.invalid/29ts_dpkg_2024.pdf",
                    ),
                    tsr_recipes.TsrFactReviewRow(
                        tsa_id="tsa_29",
                        tsa_code="29",
                        tsa_name="Williams Lake",
                        fact_family="thlb_reference",
                        extracted_value="Long-term THLB 1,660,053 53.66",
                        recommended_query="Long-term THLB 1,660,053 53.66",
                        quality="needs_review",
                        quality_reason="Contains THLB reference context",
                        snippet="Long-term THLB 1,660,053 53.66",
                        page_number=44,
                        title="Williams Lake TSA data package 2024",
                        cycle_label="TSR 2024",
                        cycle_year=2024,
                        provenance_id="TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=44",
                        source_url="https://example.invalid/29ts_dpkg_2024.pdf",
                    ),
                    tsr_recipes.TsrFactReviewRow(
                        tsa_id="tsa_29",
                        tsa_code="29",
                        tsa_name="Williams Lake",
                        fact_family="thlb_reference",
                        extracted_value="Mule Deer winter range Remove moderate to shallow MDWRs from the THLB",
                        recommended_query=(
                            "Mule Deer winter range Remove moderate to shallow MDWRs "
                            "from the THLB"
                        ),
                        quality="needs_review",
                        quality_reason="Contains THLB rule context",
                        snippet=(
                            "Mule Deer winter range Remove moderate to shallow MDWRs "
                            "from the THLB"
                        ),
                        page_number=47,
                        title="Williams Lake TSA data package 2024",
                        cycle_label="TSR 2024",
                        cycle_year=2024,
                        provenance_id="TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=47",
                        source_url="https://example.invalid/29ts_dpkg_2024.pdf",
                    ),
                    tsr_recipes.TsrFactReviewRow(
                        tsa_id="tsa_29",
                        tsa_code="29",
                        tsa_name="Williams Lake",
                        fact_family="thlb_reference",
                        extracted_value="Long-term THLB 1,500,000 49.00",
                        recommended_query="Long-term THLB 1,500,000 49.00",
                        quality="needs_review",
                        quality_reason="Older cycle reference",
                        snippet="Long-term THLB 1,500,000 49.00",
                        page_number=30,
                        title="Williams Lake TSA data package 2013",
                        cycle_label="TSR 2013",
                        cycle_year=2013,
                        provenance_id="TSR_2013/Data_Package_2013/29ts_dpkg_2013.pdf#page=30",
                        source_url="https://example.invalid/29ts_dpkg_2013.pdf",
                    ),
                )
            },
        )(),
    )
    monkeypatch.setattr(
        tsr_recipes,
        "_load_selected_tsr_pdf_pages",
        lambda **_kwargs: ((), None),
    )

    result = tsr_catalog.build_tsr_thlb_netdown_recipe(
        recipe_path=init_result.thlb_netdown_recipe_path,
        source_root=source_root,
    )

    assert result.step_count == 2
    assert result.step_kind_counts == {"netdown_rule": 1, "reference_target": 1}
    assert result.status_counts == {"ready": 2}
    assert result.selected_document_paths == (
        "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf",
    )

    recipe = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    )
    assert recipe.recipe_contract["status"] == "built"
    assert recipe.recipe_contract["selected_document_paths"] == list(
        result.selected_document_paths
    )
    assert len(recipe.steps) == 2
    reference_step = next(
        step for step in recipe.steps if step["step_kind"] == "reference_target"
    )
    netdown_step = next(
        step for step in recipe.steps if step["step_kind"] == "netdown_rule"
    )
    assert reference_step["normalized_action"] == "reference_target"
    assert reference_step["label"] == "Long-term THLB reference"
    assert reference_step["land_base_stage"] == "reference_target"
    assert reference_step["execution_class"] == "reference_only"
    assert netdown_step["normalized_action"] == "exclude"
    assert netdown_step["linked_source_entry_ids"] == ["mdwr"]
    assert netdown_step["land_base_stage"] == "lhlb_to_thlb"
    assert netdown_step["execution_class"] == "projected_harvest_exclusion"


def test_build_tsr_thlb_workbench_writes_generated_notebook_and_updates_recipe_contract(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "built"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "whse_f_own",
            "label": "Generalized Forest Cover Ownership",
            "recommended_query": "WHSE_FOREST_VEGETATION.F_OWN",
            "current_public_status": "exact_hit",
            "artifact_path": "data/downloads/bcdc/F_OWN/F_OWN.gpkg",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )
    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["recipe_contract"]["recipe_build_status_report_path"] = (
        "config/tsr/thlb_netdown.status.md"
    )
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "milestone_aflb",
            "parent_label": "Analysis forest land base",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 3098168.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "step_001_land_not_administered",
            "parent_label": "Land not administered by the Province",
            "parent_kind": "transformation",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "drop_from_universe",
            "table_provenance": "TSR_2024/...#table=3,row=2",
            "benchmark_marginal_area_ha": 697033.0,
            "benchmark_cumulative_area_ha": 4236602.0,
            "subsection_number": "6.2.1",
            "subsection_title": "Land not administered by the Province for TSA timber supply",
            "supporting_provenance_ids": [
                "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=19"
            ],
            "draft_subrules": [
                {
                    "subrule_id": "exclude_private_federal",
                    "human_summary": "Exclude private and federal lands from AFLB",
                    "candidate_layers": ["whse_forest_vegetation_f_own"],
                    "candidate_fields": ["OWNERSHIP_CLASS"],
                    "candidate_values": ["private", "federal"],
                    "candidate_operation_type": "attribute_select",
                    "review_status": "needs_review",
                }
            ],
            "compiled_logic": [
                {
                    "step_id": "compiled_001",
                    "parent_step_id": "step_001_land_not_administered",
                    "label": "Exclude private and federal lands",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "linked_source_entry_ids": ["whse_f_own"],
                }
            ],
            "row_order": 2,
        },
    ]
    recipe_payload["steps"] = [
        {
            "step_id": "compiled_001",
            "parent_step_id": "step_001_land_not_administered",
            "label": "Exclude private and federal lands",
            "step_status": "ready",
            "execution_status": "ready",
            "step_kind": "netdown_rule",
            "land_base_stage": "glb_to_aflb",
        }
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )
    status_report_path = instance_root / "config" / "tsr" / "thlb_netdown.status.md"
    status_report_path.parent.mkdir(parents=True, exist_ok=True)
    status_report_path.write_text("# THLB status\n", encoding="utf-8")

    result = tsr_recipes.build_tsr_thlb_workbench(
        recipe_path=init_result.thlb_netdown_recipe_path
    )

    assert result.parent_step_count == 2
    assert result.compiled_logic_count == 1
    notebook_payload = json.loads(result.notebook_path.read_text(encoding="utf-8"))
    notebook_text = json.dumps(notebook_payload)
    assert "THLB Netdown Workbench: TSA 29 (Williams Lake)" in notebook_text
    assert "Review Dashboard" in notebook_text
    assert (
        "Treat the exact FEMIC logic summaries as the executable contract."
        in notebook_text
    )
    assert "Locking / Convergence" in notebook_text
    assert "Land not administered by the Province" in notebook_text
    assert "run_tsr_thlb_parent_step(" in notebook_text
    assert "Review prompts" in notebook_text
    assert "Lock impact if this step is accepted or revised:" in notebook_text
    assert "LANDSCAPE_UNIT_SCOPE" in notebook_text
    assert "Williams Lake" in notebook_text
    assert "Chimney" not in notebook_text
    assert "Alkali" not in notebook_text
    assert "PROGRESS_ROOT" in notebook_text
    assert "LU_BUNDLE_COUNT = 8" in notebook_text
    assert "FloatProgress" in notebook_text
    recipe = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    )
    assert recipe.recipe_contract["workbench_notebook_path"] == (
        "workbench/tsr/thlb_netdown.workbench.ipynb"
    )


def test_build_tsr_thlb_warmstart_writes_noncanonical_markdown_and_yaml(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "built"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "whse_f_own",
            "recommended_query": "WHSE_FOREST_VEGETATION.F_OWN",
            "current_public_status": "exact_hit",
            "artifact_path": "data/downloads/bcdc/F_OWN/F_OWN.gpkg",
        },
        {
            "entry_id": "missing_streams",
            "recommended_query": "REG_LAND_AND_NATURAL_RESOURCE.STREAM_CLASSIFICATION_CAR_LINE",
            "current_public_status": "no_hit",
        },
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )
    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "milestone_aflb",
            "parent_label": "Analysis forest land base",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 3098168.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "compiled_step",
            "parent_label": "Land not administered by the Province",
            "parent_kind": "transformation",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "drop_from_universe",
            "benchmark_marginal_area_ha": 10.0,
            "benchmark_cumulative_area_ha": 90.0,
            "table_provenance": "TSR_2024/...#table=3,row=2",
            "supporting_provenance_ids": ["TSR_2024/...#page=19"],
            "draft_subrules": [
                {
                    "candidate_operation_type": "attribute_select",
                    "candidate_layers": ["whse_forest_vegetation_f_own"],
                    "candidate_fields": ["OWN"],
                    "candidate_values": ["40", "50"],
                }
            ],
            "compiled_logic": [
                {
                    "step_id": "compiled_001",
                    "parent_step_id": "compiled_step",
                    "label": "Exclude private land",
                    "step_status": "ready",
                    "run_status": "ready",
                    "compiled_operation_type": "attribute_select",
                    "linked_source_entry_ids": ["whse_f_own"],
                }
            ],
            "row_order": 2,
        },
        {
            "parent_step_id": "blocked_step",
            "parent_label": "Riparian areas",
            "parent_kind": "transformation",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "projected_harvest_exclusion",
            "benchmark_marginal_area_ha": 5.0,
            "benchmark_cumulative_area_ha": 85.0,
            "draft_subrules": [
                {
                    "candidate_operation_type": "buffer_intersect",
                    "candidate_layers": ["stream_classification_car_line"],
                    "candidate_fields": ["STREAM_CLASS"],
                    "candidate_values": ["1", "2"],
                }
            ],
            "compiled_logic": [
                {
                    "step_id": "compiled_002",
                    "parent_step_id": "blocked_step",
                    "label": "Buffer stream classes",
                    "step_status": "needs_review",
                    "compiled_operation_type": "buffer_intersect",
                    "linked_source_entry_ids": ["missing_streams"],
                }
            ],
            "row_order": 3,
        },
        {
            "parent_step_id": "manual_step",
            "parent_label": "Future roads",
            "parent_kind": "transformation",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "projected_harvest_exclusion",
            "benchmark_marginal_area_ha": 3.0,
            "benchmark_cumulative_area_ha": 82.0,
            "compiled_logic": [
                {
                    "step_id": "compiled_003",
                    "parent_step_id": "manual_step",
                    "label": "Apply reviewed no-op tail step",
                    "step_status": "ready",
                    "compiled_operation_type": "no_deduction",
                }
            ],
            "row_order": 4,
        },
        {
            "parent_step_id": "unknown_step",
            "parent_label": "Odd custom clause",
            "parent_kind": "transformation",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "projected_harvest_exclusion",
            "benchmark_marginal_area_ha": 1.0,
            "benchmark_cumulative_area_ha": 81.0,
            "compiled_logic": [],
            "draft_subrules": [],
            "row_order": 5,
        },
    ]
    recipe_payload["steps"] = [
        {
            "step_id": "compiled_001",
            "parent_step_id": "compiled_step",
            "label": "Exclude private land",
            "step_status": "ready",
            "run_status": "ready",
            "compiled_operation_type": "attribute_select",
        },
        {
            "step_id": "compiled_002",
            "parent_step_id": "blocked_step",
            "label": "Buffer stream classes",
            "step_status": "needs_review",
            "compiled_operation_type": "buffer_intersect",
            "linked_source_entry_ids": ["missing_streams"],
        },
        {
            "step_id": "compiled_003",
            "parent_step_id": "manual_step",
            "label": "Apply reviewed no-op tail step",
            "step_status": "ready",
            "compiled_operation_type": "no_deduction",
        },
    ]
    original_recipe_text = tsr_recipes.yaml.safe_dump(
        recipe_payload, sort_keys=False, allow_unicode=False
    )
    init_result.thlb_netdown_recipe_path.write_text(
        original_recipe_text,
        encoding="utf-8",
    )

    result = tsr_recipes.build_tsr_thlb_warmstart(
        recipe_path=init_result.thlb_netdown_recipe_path
    )

    assert result.markdown_path.name == "thlb_netdown.warmstart.md"
    assert result.yaml_path.name == "thlb_warmstart.yaml"
    assert result.milestone_count == 1
    assert result.parent_step_count == 4
    assert result.warmstart_status_counts["compiled_ready"] == 1
    assert result.warmstart_status_counts["blocked_missing_source"] == 1
    assert result.warmstart_status_counts["manual_or_aspatial"] == 1
    assert result.warmstart_status_counts["no_pattern_match"] == 1
    payload = tsr_recipes.yaml.safe_load(result.yaml_path.read_text(encoding="utf-8"))
    assert payload["artifact_kind"] == "thlb_warmstart"
    assert "Review aid only" in payload["non_canonical_warning"]
    assert payload["milestones"][0]["parent_label"] == "Analysis forest land base"
    entries = {item["parent_step_id"]: item for item in payload["entries"]}
    assert entries["compiled_step"]["warmstart_status"] == "compiled_ready"
    assert entries["compiled_step"]["motif_id"] == "ownership_admin_exclusion"
    assert entries["blocked_step"]["warmstart_status"] == "blocked_missing_source"
    assert entries["manual_step"]["warmstart_status"] == "manual_or_aspatial"
    assert entries["unknown_step"]["warmstart_status"] == "no_pattern_match"
    markdown_text = result.markdown_path.read_text(encoding="utf-8")
    assert "THLB Warm-Start Checklist: TSA 29 (Williams Lake)" in markdown_text
    assert "Backbone Milestones" in markdown_text
    assert "Warm-start status: `compiled_ready`" in markdown_text
    assert "Warm-start status: `blocked_missing_source`" in markdown_text
    assert "Warm-start status: `manual_or_aspatial`" in markdown_text
    assert "Warm-start status: `no_pattern_match`" in markdown_text
    assert (
        init_result.thlb_netdown_recipe_path.read_text(encoding="utf-8")
        == original_recipe_text
    )


def test_lock_tsr_thlb_workbench_requires_aflb_lock_before_thlb_only_lock(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "built"
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )
    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["recipe_contract"]["recipe_build_status_report_path"] = (
        "config/tsr/thlb_netdown.status.md"
    )
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )
    status_report_path = instance_root / "config" / "tsr" / "thlb_netdown.status.md"
    status_report_path.parent.mkdir(parents=True, exist_ok=True)
    status_report_path.write_text("# THLB status\n", encoding="utf-8")
    workbench_path = tsr_recipes.default_tsr_thlb_workbench_notebook_path(
        instance_root=instance_root
    )
    workbench_path.parent.mkdir(parents=True, exist_ok=True)
    workbench_path.write_text("{}", encoding="utf-8")

    with pytest.raises(tsr_recipes.TsrRecipeError):
        tsr_recipes.lock_tsr_thlb_workbench(
            recipe_path=init_result.thlb_netdown_recipe_path,
            lock_scope="thlb",
        )


def test_lock_tsr_thlb_workbench_writes_script_and_frozen_report_bundle(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "built"
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )
    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["recipe_contract"]["recipe_build_status_report_path"] = (
        "config/tsr/thlb_netdown.status.md"
    )
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "step_001_land_not_administered",
            "parent_label": "Land not administered by the Province",
            "parent_kind": "transformation",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "drop_from_universe",
            "compiled_logic": [],
            "row_order": 1,
        }
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )
    status_report_path = instance_root / "config" / "tsr" / "thlb_netdown.status.md"
    status_report_path.parent.mkdir(parents=True, exist_ok=True)
    status_report_path.write_text("# THLB status\n", encoding="utf-8")
    audit_path = instance_root / "config" / "tsr" / "thlb_reconstructed.audit.json"
    audit_path.write_text('{"ok": true}\n', encoding="utf-8")
    workbench_path = tsr_recipes.default_tsr_thlb_workbench_notebook_path(
        instance_root=instance_root
    )
    workbench_path.parent.mkdir(parents=True, exist_ok=True)
    workbench_path.write_text("{}", encoding="utf-8")

    result = tsr_recipes.lock_tsr_thlb_workbench(
        recipe_path=init_result.thlb_netdown_recipe_path,
        lock_scope="all",
    )

    assert result.locked_script_path.exists()
    assert result.locked_recipe_path.exists()
    assert result.frozen_status_report_path.exists()
    assert result.frozen_audit_path is not None
    assert result.frozen_audit_path.exists()
    recipe = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    )
    lock_state = recipe.recipe_contract["lock_state"]
    assert lock_state["aflb"]["locked"] is True
    assert lock_state["thlb"]["locked"] is True
    assert recipe.recipe_contract["locked_script_path"] == (
        "workbench/tsr/thlb_netdown.locked.py"
    )


def test_run_tsr_thlb_parent_step_executes_first_tranche_parent_and_writes_runtime_artifacts(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    f_own_path = instance_root / "data" / "downloads" / "bcdc" / "F_OWN" / "F_OWN.gpkg"
    f_own_path.parent.mkdir(parents=True, exist_ok=True)
    f_own = gpd.GeoDataFrame(
        {
            "OWN": [40, 62],
            "OWNERSHIP_DESCRIPTION": [
                "Private",
                "Crown - Forest Management Unit",
            ],
        },
        geometry=[box(0, 0, 100, 100), box(110, 0, 210, 100)],
        crs="EPSG:3005",
    )
    f_own.to_file(f_own_path, driver="GPKG")

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "built"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "whse_f_own",
            "label": "Generalized Forest Cover Ownership",
            "recommended_query": "WHSE_FOREST_VEGETATION.F_OWN",
            "artifact_path": "data/downloads/bcdc/F_OWN/F_OWN.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["recipe_contract"]["recipe_build_status_report_path"] = (
        "config/tsr/thlb_netdown.status.md"
    )
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 2.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "thlb_parent_002_land_not_administered_by_the_province",
            "parent_label": "Land not administered by the Province",
            "parent_kind": "transformation",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "drop_from_universe",
            "benchmark_marginal_area_ha": 1.0,
            "benchmark_cumulative_area_ha": 1.0,
            "table_provenance": "TSR_2024/...#table=3,row=2",
            "subsection_number": "6.2.1",
            "subsection_title": "Land not administered by the Province for TSA timber supply",
            "supporting_provenance_ids": [
                "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=19"
            ],
            "draft_subrules": [
                {
                    "subrule_id": "exclude_non_tsa_supply_ownership",
                    "human_summary": "Exclude ownership classes not administered for TSA supply",
                    "candidate_layers": ["whse_f_own"],
                    "candidate_fields": ["OWNERSHIP_DESCRIPTION"],
                    "candidate_values": [
                        "Private",
                        "Federal - Dominion government Block/Federal Parcels",
                    ],
                    "candidate_operation_type": "attribute_select",
                    "review_status": "draft",
                }
            ],
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_002_land_not_administered_by_the_province_compiled_01",
                    "parent_step_id": "thlb_parent_002_land_not_administered_by_the_province",
                    "label": "Exclude ownership classes not administered for TSA timber supply",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "operation_type": "select_spatial_intersect",
                    "linked_source_entry_ids": ["whse_f_own"],
                    "source_attribute_filters": [
                        {
                            "field": "OWNERSHIP_DESCRIPTION",
                            "operator": "in",
                            "value": [
                                "Private",
                                "Federal - Dominion government Block/Federal Parcels",
                            ],
                        }
                    ],
                }
            ],
            "row_order": 2,
        },
    ]
    recipe_payload["steps"] = [
        {
            "step_id": "thlb_parent_002_land_not_administered_by_the_province_compiled_01",
            "parent_step_id": "thlb_parent_002_land_not_administered_by_the_province",
            "label": "Exclude ownership classes not administered for TSA timber supply",
            "step_status": "ready",
            "execution_status": "ready",
            "step_kind": "netdown_rule",
            "land_base_stage": "glb_to_aflb",
        }
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    checkpoint_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1, 2],
            "MAP_ID": ["092O071", "092O071"],
        },
        geometry=[box(0, 0, 100, 100), box(110, 0, 210, 100)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)

    result = tsr_recipes.run_tsr_thlb_parent_step(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_id="thlb_parent_002_land_not_administered_by_the_province",
        checkpoint_path=checkpoint_path,
        map_ids=("092O071",),
        auto_map_id_smoke_subset=False,
    )

    assert result.status == "applied"
    assert result.input_area_ha == pytest.approx(2.0)
    assert result.removed_area_ha == pytest.approx(1.0)
    assert result.remaining_area_ha == pytest.approx(1.0)
    assert result.benchmark_marginal_delta_ha == pytest.approx(0.0)
    assert result.benchmark_cumulative_delta_ha == pytest.approx(0.0)
    assert result.smoke_benchmark_scale_factor == pytest.approx(1.0)
    assert result.scaled_benchmark_marginal_area_ha == pytest.approx(1.0)
    assert result.scaled_benchmark_cumulative_area_ha == pytest.approx(1.0)
    assert result.scaled_benchmark_marginal_delta_ha == pytest.approx(0.0)
    assert result.scaled_benchmark_cumulative_delta_ha == pytest.approx(0.0)
    assert result.output_path.exists()
    assert result.result_json_path.exists()
    result_payload = json.loads(result.result_json_path.read_text(encoding="utf-8"))
    assert result_payload["parent_step_id"] == (
        "thlb_parent_002_land_not_administered_by_the_province"
    )
    assert result_payload["executed_items"][0]["execution_status"] == "applied"
    updated_recipe = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    )
    updated_parent = next(
        parent
        for parent in updated_recipe.parent_steps
        if parent["parent_step_id"]
        == "thlb_parent_002_land_not_administered_by_the_province"
    )
    assert updated_parent["ratchet_state"] == "benchmarked"
    assert updated_parent["last_notebook_run_status"] == "applied"


def test_run_tsr_thlb_parent_step_buffers_line_sources_for_roads_step(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    road_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_FOREST_TENURE_FTEN_ROAD_SECTION_LINES_SVW"
        / "WHSE_FOREST_TENURE_FTEN_ROAD_SECTION_LINES_SVW.gpkg"
    )
    road_path.parent.mkdir(parents=True, exist_ok=True)
    roads = gpd.GeoDataFrame(
        {"FILE_TYPE_DESCRIPTION": ["Road Permit"]},
        geometry=[LineString([(45, -10), (45, 110)])],
        crs="EPSG:3005",
    )
    roads.to_file(road_path, driver="GPKG")

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "built"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "whse_forest_tenure_ften_road_section_lines_svw",
            "label": "WHSE_FOREST_TENURE.FTEN_ROAD_SECTION_LINES_SVW",
            "recommended_query": "WHSE_FOREST_TENURE.FTEN_ROAD_SECTION_LINES_SVW",
            "artifact_path": (
                "data/downloads/bcdc/WHSE_FOREST_TENURE_FTEN_ROAD_SECTION_LINES_SVW/"
                "WHSE_FOREST_TENURE_FTEN_ROAD_SECTION_LINES_SVW.gpkg"
            ),
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 2.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "thlb_parent_004_roads_and_landings",
            "parent_label": "Roads and landings",
            "parent_kind": "transformation",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "drop_from_universe",
            "benchmark_marginal_area_ha": 0.3,
            "benchmark_cumulative_area_ha": 1.7,
            "table_provenance": "TSR_2024/...#table=3,row=4",
            "subsection_number": "6.2.3",
            "subsection_title": "Roads and landings",
            "supporting_provenance_ids": [
                "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=27"
            ],
            "draft_subrules": [
                {
                    "subrule_id": "buffer_road_permits",
                    "human_summary": "Buffer road permit centerlines and exclude overlap",
                    "candidate_layers": [
                        "whse_forest_tenure_ften_road_section_lines_svw"
                    ],
                    "candidate_operation_type": "buffer_intersect",
                    "review_status": "draft",
                }
            ],
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_004_roads_and_landings_compiled_01",
                    "parent_step_id": "thlb_parent_004_roads_and_landings",
                    "label": "Buffer active or retired road permit roads",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "operation_type": "buffer_then_intersect",
                    "linked_source_entry_ids": [
                        "whse_forest_tenure_ften_road_section_lines_svw"
                    ],
                    "source_attribute_filters": [
                        {
                            "field": "FILE_TYPE_DESCRIPTION",
                            "operator": "in",
                            "value": ["Road Permit"],
                        }
                    ],
                    "buffer_distance_m": 5.0,
                }
            ],
            "row_order": 4,
        },
    ]
    recipe_payload["steps"] = [
        {
            "step_id": "thlb_parent_004_roads_and_landings_compiled_01",
            "parent_step_id": "thlb_parent_004_roads_and_landings",
            "label": "Buffer active or retired road permit roads",
            "step_status": "ready",
            "execution_status": "ready",
            "step_kind": "netdown_rule",
            "land_base_stage": "glb_to_aflb",
        }
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    checkpoint_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1, 2],
            "MAP_ID": ["092O071", "092O071"],
        },
        geometry=[box(0, 0, 100, 100), box(110, 0, 210, 100)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)

    result = tsr_recipes.run_tsr_thlb_parent_step(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_id="thlb_parent_004_roads_and_landings",
        checkpoint_path=checkpoint_path,
        map_ids=("092O071",),
        auto_map_id_smoke_subset=False,
    )

    assert result.status == "applied"
    assert result.removed_area_ha > 0
    assert result.remaining_area_ha < result.input_area_ha
    payload = json.loads(result.result_json_path.read_text(encoding="utf-8"))
    assert payload["executed_items"][0]["execution_status"] == "applied"
    updated_recipe = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    )
    updated_parent = next(
        parent
        for parent in updated_recipe.parent_steps
        if parent["parent_step_id"] == "thlb_parent_004_roads_and_landings"
    )
    assert updated_parent["ratchet_state"] == "benchmarked"
    assert updated_parent["last_notebook_run_status"] == "applied"


def test_run_tsr_thlb_parent_step_reports_applied_with_blockers_for_partial_success(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "built"
    source_recipe_payload["entries"] = []
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["recipe_contract"]["recipe_build_status_report_path"] = (
        "config/tsr/thlb_netdown.status.md"
    )
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 2.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "thlb_parent_003_non_forest",
            "parent_label": "Non-forest",
            "parent_kind": "transformation",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "drop_from_universe",
            "benchmark_marginal_area_ha": 1.0,
            "benchmark_cumulative_area_ha": 1.0,
            "table_provenance": "TSR_2024/...#table=3,row=3",
            "subsection_number": "6.2.2",
            "subsection_title": "Land classified as non-forest",
            "supporting_provenance_ids": [
                "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=20"
            ],
            "draft_subrules": [],
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_003_non_forest_compiled_01",
                    "parent_step_id": "thlb_parent_003_non_forest",
                    "label": "Exclude non-forest checkpoint polygons",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "operation_type": "select_attribute",
                    "checkpoint_attribute_mode": "any",
                    "checkpoint_attribute_filters": [
                        {
                            "field": "FOR_MGMT_LAND_BASE_IND",
                            "operator": "ne",
                            "value": "Y",
                        }
                    ],
                },
                {
                    "step_id": "thlb_parent_003_non_forest_compiled_02",
                    "parent_step_id": "thlb_parent_003_non_forest",
                    "label": "Freshwater Atlas final water check",
                    "step_status": "manual_review_required",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "operation_type": "select_spatial_intersect",
                    "linked_source_entry_ids": ["missing_fwa_layer"],
                },
            ],
            "row_order": 3,
        },
    ]
    recipe_payload["steps"] = []
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    checkpoint_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1, 2],
            "MAP_ID": ["092O071", "092O071"],
            "FOR_MGMT_LAND_BASE_IND": ["N", "Y"],
        },
        geometry=[box(0, 0, 100, 100), box(110, 0, 210, 100)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)

    result = tsr_recipes.run_tsr_thlb_parent_step(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_id="thlb_parent_003_non_forest",
        checkpoint_path=checkpoint_path,
        map_ids=("092O071",),
        auto_map_id_smoke_subset=False,
    )

    assert result.status == "applied_with_blockers"
    assert result.removed_area_ha == pytest.approx(1.0)
    assert result.remaining_area_ha == pytest.approx(1.0)


def test_load_compiled_logic_geometries_treats_empty_bbox_hit_as_no_matching(
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "instance"
    artifact_dir = instance_root / "data" / "downloads" / "bcdc" / "TEST"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "TEST.gpkg"
    layer = gpd.GeoDataFrame(
        {"CLASS": ["U"]},
        geometry=[box(1000, 1000, 1100, 1100)],
        crs="EPSG:3005",
    )
    layer.to_file(artifact_path, driver="GPKG")

    geometries, missing_sources, no_matching, extent_mismatch_notes = (
        tsr_recipes._load_compiled_logic_geometries(
            instance_root=instance_root,
            compiled_item={
                "compiled_operation_type": "select_spatial_intersect",
                "linked_source_entry_ids": ["terrain"],
                "source_attribute_filters": [
                    {"field": "CLASS", "operator": "eq", "value": "U"}
                ],
            },
            source_entry_map={
                "terrain": {
                    "artifact_path": "data/downloads/bcdc/TEST/TEST.gpkg",
                }
            },
            bbox=(0.0, 0.0, 10.0, 10.0),
        )
    )

    assert geometries is not None
    assert geometries.empty
    assert missing_sources == []
    assert no_matching is True
    assert extent_mismatch_notes == []


def test_apply_checkpoint_attribute_filters_preserves_geometry_for_later_stage() -> (
    None
):
    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1, 2],
            "ZONE": ["exclude", "keep"],
            "thlb_fact": [1.0, 1.0],
            "thlb": [1, 1],
        },
        geometry=[box(0, 0, 100, 100), box(110, 0, 210, 100)],
        crs="EPSG:3005",
    )
    checkpoint = tsr_recipes._assign_fragment_feature_ids(checkpoint)

    updated, removed_area_ha = tsr_recipes._apply_checkpoint_attribute_filters(
        checkpoint,
        filters=[{"field": "ZONE", "operator": "eq", "value": "exclude"}],
        mode="any",
        preserve_geometry=True,
    )

    assert len(updated) == 2
    assert removed_area_ha == pytest.approx(1.0)
    assert updated["thlb_fact"].tolist() == pytest.approx([0.0, 1.0])
    assert updated["thlb"].tolist() == [0, 1]


def test_run_tsr_thlb_parent_step_preserves_geometry_for_later_stage_spatial_exclusion(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "OGMA" / "OGMA.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    exclusion = gpd.GeoDataFrame(
        {
            "name": ["ogma_perm", "ogma_trans"],
            "OGMA_TYPE": ["PERM", "TRANS"],
        },
        geometry=[box(0, 0, 50, 100), box(50, 0, 100, 100)],
        crs="EPSG:3005",
    )
    exclusion.to_file(exclusion_path, driver="GPKG")

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["entries"] = [
        {
            "entry_id": "rmp_ogma_legal",
            "label": "OGMA",
            "artifact_path": "data/downloads/bcdc/OGMA/OGMA.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 2.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "thlb_parent_007_old_growth_management_areas",
            "parent_label": "Old growth management areas",
            "parent_kind": "transformation",
            "land_base_stage": "aflb_to_lhlb",
            "stage_label": "AFLB -> LHLB",
            "execution_class": "legal_harvest_exclusion",
            "benchmark_marginal_area_ha": 0.5,
            "benchmark_cumulative_area_ha": 1.5,
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_007_old_growth_management_areas_compiled_01",
                    "parent_step_id": "thlb_parent_007_old_growth_management_areas",
                    "label": "Old growth management areas",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "land_base_stage": "aflb_to_lhlb",
                    "operation_type": "select_spatial_intersect",
                    "linked_source_entry_ids": ["rmp_ogma_legal"],
                    "source_attribute_filters": [
                        {
                            "field": "OGMA_TYPE",
                            "operator": "in",
                            "value": ["PERM", "ROT"],
                        }
                    ],
                }
            ],
            "row_order": 7,
        },
    ]
    recipe_payload["steps"] = []
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    checkpoint_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1],
            "MAP_ID": ["092O071"],
        },
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)

    result = tsr_recipes.run_tsr_thlb_parent_step(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_id="thlb_parent_007_old_growth_management_areas",
        checkpoint_path=checkpoint_path,
        map_ids=("092O071",),
        auto_map_id_smoke_subset=False,
    )

    assert result.status == "applied"
    output = gpd.read_feather(result.output_path)
    assert set(output["thlb"].tolist()) == {0, 1}
    assert set(output["thlb_fact"].tolist()) == {0.0, 1.0}
    assert len(output) == 2


def test_run_tsr_thlb_parent_step_step13_combines_attribute_and_spatial_exclusion(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    terrain_path = (
        instance_root / "data" / "downloads" / "bcdc" / "TERRAIN" / "TERRAIN.gpkg"
    )
    terrain_path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {"SLOPE_STABILITY_CLASS_W_ROADS": ["U"]},
        geometry=[box(120, 0, 160, 100)],
        crs="EPSG:3005",
    ).to_file(terrain_path, driver="GPKG")

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["entries"] = [
        {
            "entry_id": "reg_land_and_natural_resource_terrain_stability",
            "label": "Terrain stability",
            "artifact_path": "data/downloads/bcdc/TERRAIN/TERRAIN.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 2.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "thlb_parent_013_areas_considered_inoperable",
            "parent_label": "Areas considered inoperable",
            "parent_kind": "transformation",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "projected_harvest_exclusion",
            "benchmark_marginal_area_ha": 1.5,
            "benchmark_cumulative_area_ha": 0.5,
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_013_compiled_01",
                    "parent_step_id": "thlb_parent_013_areas_considered_inoperable",
                    "label": "Unstable terrain and terrain class 5",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "land_base_stage": "lhlb_to_thlb",
                    "compiled_operation_type": "select_spatial_intersect",
                    "linked_source_entry_ids": [
                        "reg_land_and_natural_resource_terrain_stability"
                    ],
                    "source_attribute_filters": [
                        {
                            "field": "SLOPE_STABILITY_CLASS_W_ROADS",
                            "operator": "in",
                            "value": ["U", "V"],
                        }
                    ],
                },
                {
                    "step_id": "thlb_parent_013_compiled_02",
                    "parent_step_id": "thlb_parent_013_areas_considered_inoperable",
                    "label": "Steep slope thresholds east and west of Highway 97",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "land_base_stage": "lhlb_to_thlb",
                    "compiled_operation_type": "select_attribute",
                    "checkpoint_attribute_mode": "any",
                    "checkpoint_attribute_filters": [
                        {
                            "field": "femic_step13_steep_slope_flag",
                            "operator": "eq",
                            "value": True,
                        }
                    ],
                },
            ],
            "row_order": 13,
        },
    ]
    recipe_payload["steps"] = []
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    checkpoint_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint7.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1, 2],
            "MAP_ID": ["092O071", "092O071"],
            "femic_step13_steep_slope_flag": [True, False],
        },
        geometry=[box(0, 0, 100, 100), box(100, 0, 200, 100)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)

    result = tsr_recipes.run_tsr_thlb_parent_step(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_id="thlb_parent_013_areas_considered_inoperable",
        checkpoint_path=checkpoint_path,
        map_ids=("092O071",),
        auto_map_id_smoke_subset=False,
    )

    assert result.status == "applied"
    output = gpd.read_feather(result.output_path)
    assert len(output) == 3
    assert sorted(output["thlb"].tolist()) == [0, 0, 1]
    assert sorted(output["thlb_fact"].tolist()) == pytest.approx([0.0, 0.0, 1.0])


def test_run_tsr_thlb_parent_step_lu_parallel_matches_serial_removed_area(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "OGMA" / "OGMA.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    exclusion = gpd.GeoDataFrame(
        {"name": ["ogma"]},
        geometry=[box(0, 0, 50, 100)],
        crs="EPSG:3005",
    )
    exclusion.to_file(exclusion_path, driver="GPKG")

    lu_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_LAND_USE_PLANNING_RMP_LANDSCAPE_UNIT_SVW"
        / "WHSE_LAND_USE_PLANNING_RMP_LANDSCAPE_UNIT_SVW.gpkg"
    )
    lu_path.parent.mkdir(parents=True, exist_ok=True)
    lu_layer = gpd.GeoDataFrame(
        {
            "LANDSCAPE_UNIT_NAME": ["West", "East"],
            "LANDSCAPE_UNIT_NUMBER": ["1", "2"],
        },
        geometry=[box(0, 0, 50, 100), box(50, 0, 100, 100)],
        crs="EPSG:3005",
    )
    lu_layer.to_file(lu_path, driver="GPKG")

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["entries"] = [
        {
            "entry_id": "rmp_ogma_legal",
            "label": "OGMA",
            "artifact_path": "data/downloads/bcdc/OGMA/OGMA.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 1.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "thlb_parent_007_old_growth_management_areas",
            "parent_label": "Old growth management areas",
            "parent_kind": "transformation",
            "land_base_stage": "aflb_to_lhlb",
            "stage_label": "AFLB -> LHLB",
            "execution_class": "legal_harvest_exclusion",
            "benchmark_marginal_area_ha": 0.5,
            "benchmark_cumulative_area_ha": 0.5,
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_007_old_growth_management_areas_compiled_01",
                    "parent_step_id": "thlb_parent_007_old_growth_management_areas",
                    "label": "Old growth management areas",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "land_base_stage": "aflb_to_lhlb",
                    "operation_type": "select_spatial_intersect",
                    "linked_source_entry_ids": ["rmp_ogma_legal"],
                }
            ],
            "row_order": 7,
        },
    ]
    recipe_payload["steps"] = []
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    checkpoint_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1],
            "MAP_ID": ["092O071"],
        },
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)

    serial = tsr_recipes.run_tsr_thlb_parent_step(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_id="thlb_parent_007_old_growth_management_areas",
        checkpoint_path=checkpoint_path,
        landscape_units=("West", "East"),
        auto_map_id_smoke_subset=False,
    )
    parallel = tsr_recipes.run_tsr_thlb_parent_step(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_id="thlb_parent_007_old_growth_management_areas",
        checkpoint_path=checkpoint_path,
        landscape_units=("West", "East"),
        auto_map_id_smoke_subset=False,
        execution_mode=tsr_recipes.TSR_THLB_PARENT_STEP_EXECUTION_MODE_LU_PARALLEL,
        max_workers=2,
        lu_bundle_count=2,
        progress_root=instance_root / "runtime" / "logs" / "tsr" / "progress",
    )

    assert parallel.execution_mode == "lu_parallel"
    assert parallel.worker_count == 2
    assert parallel.lu_chunk_count == 2
    assert parallel.lu_bundle_count == 2
    assert (
        parallel.progress_root
        == (instance_root / "runtime" / "logs" / "tsr" / "progress").resolve()
    )
    assert parallel.removed_area_ha == pytest.approx(serial.removed_area_ha)
    assert parallel.remaining_area_ha == pytest.approx(serial.remaining_area_ha)
    assert len(list(parallel.progress_root.glob("*.json"))) == 2


def test_materialize_checkpoint_landscape_unit_partitions_reuses_cached_chunks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance_root = tmp_path / "instance"
    checkpoint_path = instance_root / "data" / "checkpoint7.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {"FEATURE_ID": [1]},
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)
    lu_frame = gpd.GeoDataFrame(
        {"LANDSCAPE_UNIT_NAME": ["West", "East"]},
        geometry=[box(0, 0, 50, 100), box(50, 0, 100, 100)],
        crs="EPSG:3005",
    )

    records_first = tsr_recipes._materialize_checkpoint_landscape_unit_partitions(
        checkpoint,
        checkpoint_path=checkpoint_path,
        lu_frame=lu_frame,
        selected_landscape_units=("West", "East"),
        instance_root=instance_root,
    )
    assert len(records_first) == 2

    def _fail_if_reclipped(*args, **kwargs):
        raise AssertionError("expected cached LU partitions to be reused")

    monkeypatch.setattr(
        tsr_recipes,
        "_clip_checkpoint_to_landscape_unit_chunks",
        _fail_if_reclipped,
    )

    records_second = tsr_recipes._materialize_checkpoint_landscape_unit_partitions(
        checkpoint,
        checkpoint_path=checkpoint_path,
        lu_frame=lu_frame,
        selected_landscape_units=("West", "East"),
        instance_root=instance_root,
    )

    assert [item["lu_name"] for item in records_second] == ["East", "West"]


def test_load_cached_landscape_unit_partition_selection_returns_cached_names(
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "instance"
    checkpoint_path = (instance_root / "data" / "checkpoint7.feather").resolve()
    partition_root = tsr_recipes.default_tsr_thlb_lu_partition_root(
        instance_root=instance_root
    )
    partition_dir = partition_root / "checkpoint7.cached"
    partition_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = partition_dir / "partition_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "checkpoint_path": str(checkpoint_path),
                "selected_landscape_units": ["West", "East"],
                "chunk_records": [],
            }
        ),
        encoding="utf-8",
    )

    cached = tsr_recipes._load_cached_landscape_unit_partition_selection(
        checkpoint_path=checkpoint_path,
        instance_root=instance_root,
    )

    assert cached is not None
    selected_names, cached_dir = cached
    assert selected_names == ("West", "East")
    assert cached_dir == partition_dir


def test_load_cached_landscape_unit_partition_records_returns_records(
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "instance"
    checkpoint_path = (instance_root / "data" / "checkpoint7.feather").resolve()
    partition_root = tsr_recipes.default_tsr_thlb_lu_partition_root(
        instance_root=instance_root
    )
    partition_dir = partition_root / "checkpoint7.cached"
    partition_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = partition_dir / "001_west.feather"
    gpd.GeoDataFrame(
        {"VALUE": [1]},
        geometry=[box(0, 0, 1, 1)],
        crs="EPSG:3005",
    ).to_feather(chunk_path)
    metadata_path = partition_dir / "partition_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "checkpoint_path": str(checkpoint_path),
                "selected_landscape_units": ["West", "East"],
                "chunk_records": [
                    {
                        "lu_name": "West",
                        "chunk_path": "001_west.feather",
                        "area_ha": 1.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    cached = tsr_recipes._load_cached_landscape_unit_partition_records(
        checkpoint_path=checkpoint_path,
        instance_root=instance_root,
    )

    assert cached is not None
    selected_names, records = cached
    assert selected_names == ("West", "East")
    assert len(records) == 1
    assert records[0]["lu_name"] == "West"
    assert records[0]["chunk_path"] == chunk_path


def test_build_thlb_parent_step_code_cell_defaults_step6_to_full_tsa_parallel() -> None:
    cell_text = tsr_recipes._build_thlb_parent_step_code_cell(
        {
            "parent_step_id": "thlb_parent_006_parks_protected_areas_area_base_tenures",
            "parent_label": "Parks, protected areas, area-base tenures",
            "benchmark_marginal_area_ha": 1.0,
            "benchmark_cumulative_area_ha": 2.0,
            "compiled_logic": [],
        },
        tsa_code="29",
    )

    assert "LANDSCAPE_UNIT_SCOPE: tuple[str, ...] = ()" in cell_text
    assert 'EXECUTION_MODE = "lu_parallel"' in cell_text
    assert "LU_BUNDLE_COUNT = 8" in cell_text
    assert "PERSIST_RECIPE_UPDATE = False" in cell_text
    assert "persist_recipe_update=PERSIST_RECIPE_UPDATE" in cell_text
    assert "PROGRESS_ROOT" in cell_text


def test_run_tsr_thlb_parallel_benchmark_writes_summary(tmp_path: Path) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    lu_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_LAND_USE_PLANNING_RMP_LANDSCAPE_UNIT_SVW"
        / "WHSE_LAND_USE_PLANNING_RMP_LANDSCAPE_UNIT_SVW.gpkg"
    )
    lu_path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {
            "LANDSCAPE_UNIT_NAME": ["West", "East"],
            "LANDSCAPE_UNIT_NUMBER": ["1", "2"],
        },
        geometry=[box(0, 0, 50, 100), box(50, 0, 100, 100)],
        crs="EPSG:3005",
    ).to_file(lu_path, driver="GPKG")
    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "OGMA" / "OGMA.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {"name": ["ogma"]},
        geometry=[box(0, 0, 50, 100)],
        crs="EPSG:3005",
    ).to_file(exclusion_path, driver="GPKG")
    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["entries"] = [
        {
            "entry_id": "rmp_ogma_legal",
            "label": "OGMA",
            "artifact_path": "data/downloads/bcdc/OGMA/OGMA.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )
    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 1.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "thlb_parent_007_old_growth_management_areas",
            "parent_label": "Old growth management areas",
            "parent_kind": "transformation",
            "land_base_stage": "aflb_to_lhlb",
            "stage_label": "AFLB -> LHLB",
            "execution_class": "legal_harvest_exclusion",
            "benchmark_marginal_area_ha": 0.5,
            "benchmark_cumulative_area_ha": 0.5,
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_007_old_growth_management_areas_compiled_01",
                    "parent_step_id": "thlb_parent_007_old_growth_management_areas",
                    "label": "Old growth management areas",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "land_base_stage": "aflb_to_lhlb",
                    "operation_type": "select_spatial_intersect",
                    "linked_source_entry_ids": ["rmp_ogma_legal"],
                }
            ],
            "row_order": 7,
        },
    ]
    recipe_payload["steps"] = []
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )
    checkpoint_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1],
            "MAP_ID": ["092O071"],
        },
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    ).to_feather(checkpoint_path)

    result = tsr_recipes.run_tsr_thlb_parallel_benchmark(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_ids=("thlb_parent_007_old_growth_management_areas",),
        checkpoint_path=checkpoint_path,
        landscape_units=("West", "East"),
        worker_counts=(1,),
    )

    assert result.summary_path.exists()
    assert len(result.run_results) == 2
    parallel = next(
        item for item in result.run_results if item.execution_mode == "lu_parallel"
    )
    assert parallel.parity_with_serial is True


def test_specialized_compiled_logic_for_wildlife_uses_harvest_zone_filters() -> None:
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_008_wildlife_habitat_areas",
        parent_label="Wildlife habitat areas",
        land_base_stage="aflb_to_lhlb",
        stage_label="AFLB -> LHLB",
        execution_class="legal_harvest_exclusion",
        benchmark_marginal_area_ha=10.0,
        benchmark_cumulative_area_ha=90.0,
        table_provenance="TSR_2024/...#table=3,row=8",
        row_order=8,
        linked_subsection={
            "body": "Areas designated through GWMs as no harvest will be excluded from the LHLB. Areas designated as conditional harvest zone will be addressed later.",
            "provenance_id": "TSR_2024/...#page=31",
            "page_number": 31,
        },
    )

    assert items is not None
    no_harvest_items = [
        item
        for item in items
        if item.get("compiled_operation_type") == "select_spatial_intersect"
    ]
    assert len(no_harvest_items) == 2
    for item in no_harvest_items:
        assert item["source_attribute_filters"] == [
            {
                "field": "TIMBER_HARVEST_CODE",
                "operator": "eq",
                "value": "NO HARVEST ZONE",
            }
        ]
    conditional = next(
        item
        for item in items
        if item.get("compiled_operation_type") == "manual_review_required"
    )
    assert conditional["source_attribute_filters"] == [
        {
            "field": "TIMBER_HARVEST_CODE",
            "operator": "eq",
            "value": "CONDITIONAL HARVEST ZONE",
        }
    ]


def test_specialized_compiled_logic_for_step6_uses_fown_tenure_classes() -> None:
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_006_parks_protected_areas_area_base_tenures",
        parent_label="Parks, protected areas, area-base tenures",
        land_base_stage="aflb_to_lhlb",
        stage_label="AFLB -> LHLB",
        execution_class="legal_harvest_exclusion",
        benchmark_marginal_area_ha=306327.0,
        benchmark_cumulative_area_ha=2791841.0,
        table_provenance="TSR_2024/...#table=3,row=6",
        row_order=6,
        linked_subsection={
            "body": (
                "Parks and protected areas are included in the AFLB. "
                "Area-based licences such as community forest agreements and "
                "First Nations woodland licences are removed from the AFLB. "
                "Woodlots are left in the AFLB and removed when defining the LHLB."
            ),
            "provenance_id": "TSR_2024/...#page=25",
            "page_number": 25,
        },
    )

    assert items is not None
    assert len(items) == 2
    tenure_item = next(
        item for item in items if item["label"] == "Area-based tenures and woodlots"
    )
    assert tenure_item["compiled_operation_type"] == "select_spatial_intersect"
    assert tenure_item["linked_source_entry_ids"] == ["whse_forest_vegetation_f_own"]
    assert tenure_item["source_attribute_filters"] == [
        {
            "field": "OWNERSHIP_DESCRIPTION",
            "operator": "in",
            "value": [
                "Crown Lease - Misc. lease",
                "Crown Tenure - Woodlot Licence, Schedule A",
                "Crown Tenure - Woodlot Licence, Schedule B",
            ],
        }
    ]


def test_specialized_compiled_logic_for_casc_uses_cclup_objective_filter() -> None:
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_011_community_areas_of_special_concern",
        parent_label="Community areas of special concern",
        land_base_stage="aflb_to_lhlb",
        stage_label="AFLB -> LHLB",
        execution_class="legal_harvest_exclusion",
        benchmark_marginal_area_ha=62460.0,
        benchmark_cumulative_area_ha=2352758.0,
        table_provenance="TSR_2024/...#table=3,row=11",
        row_order=11,
        linked_subsection={
            "body": "Community areas of special concern are spatially delineated areas that have been designated as no-harvest areas in the LUO to address a mix of CCLUP objectives. Community areas of special concern are excluded from the THLB.",
            "provenance_id": "TSR_2024/...#page=31",
            "page_number": 31,
        },
    )

    assert items is not None
    assert len(items) == 1
    casc_item = items[0]
    assert casc_item["compiled_operation_type"] == "select_spatial_intersect"
    assert casc_item["linked_source_entry_ids"] == [
        "whse_land_use_planning_rmp_plan_legal_poly_svw",
    ]
    assert casc_item["source_attribute_filters"] == [
        {
            "field": "STRGC_LAND_RSRCE_PLAN_NAME",
            "operator": "eq",
            "value": "Cariboo Chilcotin Land Use Plan",
        },
        {
            "field": "LEGAL_FEAT_OBJECTIVE",
            "operator": "eq",
            "value": "Community Areas of Special Concern",
        },
    ]


def test_specialized_compiled_logic_for_pra_is_review_only() -> None:
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_012_proven_aboriginal_rights_areas",
        parent_label="Proven Aboriginal Rights areas",
        land_base_stage="aflb_to_lhlb",
        stage_label="AFLB -> LHLB",
        execution_class="legal_harvest_exclusion",
        benchmark_marginal_area_ha=68401.0,
        benchmark_cumulative_area_ha=2284357.0,
        table_provenance="TSR_2024/...#table=3,row=12",
        row_order=12,
        linked_subsection={
            "body": "The PRA will be excluded from the THLB to reflect the lack of commercial forestry activity in the last nine years.",
            "provenance_id": "TSR_2024/...#page=31",
            "page_number": 31,
        },
    )

    assert items is not None
    assert len(items) == 1
    pra_item = items[0]
    assert pra_item["compiled_operation_type"] == "manual_review_required"
    assert pra_item["step_status"] == "manual_review_required"
    assert pra_item["linked_source_entry_ids"] == [
        "whse_admin_boundaries_pip_consultation",
        "whse_land_use_planning_fadm_designated",
    ]


def test_specialized_compiled_logic_for_inoperable_uses_terrain_plus_step13_flag() -> (
    None
):
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_013_areas_considered_inoperable",
        parent_label="Areas considered inoperable",
        land_base_stage="lhlb_to_thlb",
        stage_label="LHLB -> THLB",
        execution_class="projected_harvest_exclusion",
        benchmark_marginal_area_ha=33533.0,
        benchmark_cumulative_area_ha=2250824.0,
        table_provenance="TSR_2024/...#table=3,row=13",
        row_order=13,
        linked_subsection={
            "body": (
                "Slopes that exceed 70% east of Highway 97, slopes that exceed 40% "
                "west of Highway 97, and slopes classified as Unstable (U) or Terrain "
                "Class 5 are considered inoperable."
            ),
            "provenance_id": "TSR_2024/...#page=32",
            "page_number": 32,
        },
    )

    assert items is not None
    assert len(items) == 2
    terrain_item = next(
        item
        for item in items
        if item["compiled_operation_type"] == "select_spatial_intersect"
    )
    assert terrain_item["linked_source_entry_ids"] == [
        "reg_land_and_natural_resource_terrain_stability"
    ]
    assert terrain_item["source_attribute_filters"] == [
        {
            "field": "SLOPE_STABILITY_CLASS_W_ROADS",
            "operator": "in",
            "value": ["U", "V"],
        }
    ]
    steep_item = next(
        item for item in items if item["compiled_operation_type"] == "select_attribute"
    )
    assert steep_item["linked_source_entry_ids"] == [
        "reg_land_and_natural_resource_terrain_stability",
        "whse_imagery_and_base_maps_mot_highway_profiles_sp",
    ]
    assert steep_item["checkpoint_attribute_filters"] == [
        {
            "field": "femic_step13_steep_slope_flag",
            "operator": "eq",
            "value": True,
        }
    ]


def test_default_workbench_checkpoint_path_prefers_step13_attribute_checkpoint(
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "instance"
    (instance_root / "data" / "tsr").mkdir(parents=True)
    (instance_root / "data" / "ria_vri_vclr1p_checkpoint7.feather").write_text(
        "base", encoding="utf-8"
    )
    enriched_path = (
        instance_root
        / "data"
        / "tsr"
        / "ria_vri_vclr1p_checkpoint7.step13_attrs.feather"
    )
    enriched_path.write_text("enriched", encoding="utf-8")

    selected = tsr_recipes._default_workbench_checkpoint_path(
        instance_root=instance_root,
        target_parent={
            "parent_step_id": "thlb_parent_015_non_merchantable_timber_profiles",
            "land_base_stage": "lhlb_to_thlb",
        },
    )

    assert selected == enriched_path.resolve()


def test_specialized_compiled_logic_for_riparian_uses_classed_buffers() -> None:
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_018_riparian_areas",
        parent_label="Riparian areas",
        land_base_stage="lhlb_to_thlb",
        stage_label="LHLB -> THLB",
        execution_class="projected_harvest_exclusion",
        benchmark_marginal_area_ha=54833.0,
        benchmark_cumulative_area_ha=1812720.0,
        table_provenance="TSR_2024/...#table=3,row=18",
        row_order=18,
        linked_subsection={
            "body": (
                "Each stream, lake, and wetland class were spatially identified, "
                "classified, and then buffered using GIS in accordance with Table 15 "
                "criteria."
            ),
            "provenance_id": "TSR_2024/...#page=31",
            "page_number": 31,
        },
    )

    assert items is not None
    stream_items = [
        item
        for item in items
        if item.get("linked_source_entry_ids")
        == ["reg_land_and_natural_resource_stream_classification_car_line"]
    ]
    assert len(stream_items) == 6
    assert {item["source_attribute_filters"][0]["value"] for item in stream_items} == {
        1,
        2,
        3,
        4,
        5,
        6,
    }
    assert {item["buffer_distance_m"] for item in stream_items} == {
        6.0,
        10.0,
        24.0,
        34.0,
        60.0,
    }

    wetland_items = [
        item
        for item in items
        if item.get("linked_source_entry_ids")
        == ["reg_land_and_natural_resource_wetland_class_car_poly"]
    ]
    assert len(wetland_items) == 5
    assert {item["source_attribute_filters"][0]["value"] for item in wetland_items} == {
        "w1",
        "w2",
        "w3",
        "w4",
        "w5",
    }
    assert {item["buffer_distance_m"] for item in wetland_items} == {6.0, 14.0, 18.0}

    review_items = [
        item
        for item in items
        if item.get("compiled_operation_type") == "manual_review_required"
    ]
    assert len(review_items) == 2


def test_specialized_compiled_logic_for_low_growing_potential_uses_curve_threshold() -> (
    None
):
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_014_sites_with_low_growing_timber_potential",
        parent_label="Sites with low growing timber potential",
        land_base_stage="lhlb_to_thlb",
        stage_label="LHLB -> THLB",
        execution_class="projected_harvest_exclusion",
        benchmark_marginal_area_ha=321044.0,
        benchmark_cumulative_area_ha=1929780.0,
        table_provenance="TSR_2024/...#table=3,row=14",
        row_order=14,
        linked_subsection={
            "body": (
                "Low productivity stands are not capable of achieving the minimum "
                "harvestable criteria by 160 years. The minimum threshold is 80 m3/ha "
                "except for steep slopes where the threshold increases to 250 m3/ha."
            ),
            "provenance_id": "TSR_2024/...#page=33",
            "page_number": 33,
        },
    )

    assert items is not None
    assert len(items) == 2
    curve_items = [
        item
        for item in items
        if item["compiled_operation_type"] == "curve_volume_threshold_exclusion"
    ]
    assert len(curve_items) == 2
    non_steep_item = next(
        item
        for item in curve_items
        if item["minimum_volume_m3_per_ha"] == pytest.approx(67.1)
    )
    steep_item = next(
        item
        for item in curve_items
        if item["minimum_volume_m3_per_ha"] == pytest.approx(250.0)
    )
    assert non_steep_item["curve_id_column"] == "curve1"
    assert non_steep_item["checkpoint_attribute_filters"] == [
        {
            "field": "femic_step13_steep_slope_flag",
            "operator": "eq",
            "value": False,
        }
    ]
    assert steep_item["checkpoint_attribute_filters"] == [
        {
            "field": "femic_step13_steep_slope_flag",
            "operator": "eq",
            "value": True,
        }
    ]
    assert non_steep_item["curve_volume_metric"] == "volume_at_age"
    assert non_steep_item["curve_volume_age_years"] == pytest.approx(160.0)
    assert steep_item["curve_volume_metric"] == "volume_at_age"
    assert steep_item["curve_volume_age_years"] == pytest.approx(160.0)


def test_specialized_compiled_logic_for_non_merchantable_profiles_uses_broadleaf_filter() -> (
    None
):
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_015_non_merchantable_timber_profiles",
        parent_label="Non-merchantable timber profiles",
        land_base_stage="lhlb_to_thlb",
        stage_label="LHLB -> THLB",
        execution_class="projected_harvest_exclusion",
        benchmark_marginal_area_ha=49052.0,
        benchmark_cumulative_area_ha=1880728.0,
        table_provenance="TSR_2024/...#page=24",
        row_order=15,
        linked_subsection={
            "body": (
                "Non-merchantable timber profiles are stands that are physically operable, "
                "meet minimum harvestable criteria for age and volume, yet contain tree species "
                "that are not currently utilized. Therefore, broadleaf-leading stands will be "
                "excluded from the THLB."
            ),
            "provenance_id": "TSR_2024/...#page=35",
            "page_number": 35,
        },
    )

    assert items is not None
    assert len(items) == 1
    item = items[0]
    assert item["compiled_operation_type"] == "select_attribute"
    assert item["checkpoint_attribute_filters"][0]["field"] == "SPECIES_CD_1"
    assert "AT" in item["checkpoint_attribute_filters"][0]["value"]
    assert item["normalized_subject"] == "Broadleaf-leading stands"


def test_curve_volume_threshold_exclusion_respects_checkpoint_filters(
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    bundle_root = instance_root / "data" / "model_input_bundle"
    bundle_root.mkdir(parents=True, exist_ok=True)
    (bundle_root / "curve_table.csv").write_text(
        "curve_id,curve_type\n1001,untreated\n1002,untreated\n",
        encoding="utf-8",
    )
    (bundle_root / "curve_points_table.csv").write_text(
        "curve_id,x,y\n"
        "1001,40,20\n"
        "1001,80,40\n"
        "1001,120,60\n"
        "1001,160,60\n"
        "1002,40,80\n"
        "1002,80,160\n"
        "1002,120,200\n"
        "1002,160,220\n",
        encoding="utf-8",
    )

    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1, 2, 3],
            "curve1": [1001, 1002, 1001],
            "thlb_fact": [1.0, 1.0, 1.0],
            "thlb": [1, 1, 1],
            "_stand_area_sqm": [100.0, 100.0, 100.0],
            "femic_step13_steep_slope_flag": [False, True, True],
        },
        geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10), box(20, 0, 30, 10)],
        crs="EPSG:3005",
    )

    (
        updated,
        removed_area_ha,
        missing_metric_count,
        affected_row_count,
        scoped_row_count,
        scoped_active_row_count,
    ) = tsr_recipes._apply_curve_volume_threshold_exclusion(
        checkpoint,
        instance_root=instance_root,
        compiled_item={
            "curve_id_column": "curve1",
            "minimum_volume_m3_per_ha": 250.0,
            "curve_volume_metric": "volume_at_age",
            "curve_volume_age_years": 160.0,
            "checkpoint_attribute_mode": "any",
            "checkpoint_attribute_filters": [
                {
                    "field": "femic_step13_steep_slope_flag",
                    "operator": "eq",
                    "value": True,
                }
            ],
        },
        preserve_geometry=True,
    )

    assert removed_area_ha == pytest.approx(0.02)
    assert missing_metric_count == 0
    assert affected_row_count == 2
    assert scoped_row_count == 2
    assert scoped_active_row_count == 2
    assert updated["thlb"].tolist() == [1, 0, 0]


def test_specialized_compiled_logic_for_recreation_features_uses_active_recreation_polygons() -> (
    None
):
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_016_recreation_features",
        parent_label="Recreation features",
        land_base_stage="lhlb_to_thlb",
        stage_label="LHLB -> THLB",
        execution_class="projected_harvest_exclusion",
        benchmark_marginal_area_ha=9598.0,
        benchmark_cumulative_area_ha=1871130.0,
        table_provenance="TSR_2024/...#page=24",
        row_order=16,
        linked_subsection={
            "body": (
                "Recreation sites and trails have been legally established within the "
                "Williams Lake TSA under the FRPA. While logging is possible, it is likely "
                "that harvesting of recreation sites will be very limited so identified "
                "recreational areas and features will be excluded from the THLB."
            ),
            "provenance_id": "TSR_2024/...#page=36",
            "page_number": 36,
        },
    )

    assert items is not None
    assert len(items) == 1
    item = items[0]
    assert item["compiled_operation_type"] == "select_spatial_intersect"
    assert item["linked_source_entry_ids"] == ["whse_forest_tenure_ften_recreation"]
    assert item["source_attribute_filters"] == [
        {
            "field": "LIFE_CYCLE_STATUS_CODE",
            "operator": "eq",
            "value": "ACTIVE",
        }
    ]


def test_specialized_compiled_logic_for_buffered_trails_uses_buffered_trail_polygons() -> (
    None
):
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_019_buffered_trails",
        parent_label="Buffered trails",
        land_base_stage="lhlb_to_thlb",
        stage_label="LHLB -> THLB",
        execution_class="projected_harvest_exclusion",
        benchmark_marginal_area_ha=8039.0,
        benchmark_cumulative_area_ha=1804681.0,
        table_provenance="TSR_2024/...#page=24",
        row_order=19,
        linked_subsection={
            "body": (
                "The LAO identifies regionally important trails and defines a 50-metre "
                "management zone on either side of the trail. At least 85% of the area "
                "within the 100-metre corridor along trails will not be available for harvest."
            ),
            "provenance_id": "TSR_2024/...#page=30",
            "page_number": 30,
        },
    )

    assert items is not None
    assert len(items) == 1
    item = items[0]
    assert item["compiled_operation_type"] == "buffer_then_intersect"
    assert item["linked_source_entry_ids"] == [
        "whse_land_use_planning_rmp_plan_legal_poly_svw"
    ]
    assert item["source_attribute_filters"] == [
        {
            "field": "LEGAL_FEAT_OBJECTIVE",
            "operator": "eq",
            "value": "Buffered Trail Areas",
        }
    ]
    assert item["buffer_distance_m"] == pytest.approx(-7.5)
    assert item["normalized_subject"] == "Buffered trail areas"


def test_specialized_compiled_logic_for_wtra_uses_aspatial_reduction() -> None:
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_020_wildlife_tree_retention_areas",
        parent_label="Wildlife tree retention areas",
        land_base_stage="lhlb_to_thlb",
        stage_label="LHLB -> THLB",
        execution_class="projected_harvest_exclusion",
        benchmark_marginal_area_ha=94417.0,
        benchmark_cumulative_area_ha=1710264.0,
        table_provenance="TSR_2024/...#page=24",
        row_order=20,
        linked_subsection={
            "body": (
                "In the base case, the land base that will continually be required for WTRA "
                "will be modelled as an aspatial THLB reduction factor. In total, 94 417 hectares "
                "will be excluded to represent future WTRA."
            ),
            "provenance_id": "TSR_2024/...#page=37",
            "page_number": 37,
        },
    )

    assert items is not None
    assert len(items) == 1
    item = items[0]
    assert item["compiled_operation_type"] == "aspatial_reduction"
    assert item["normalized_action"] == "aspatial_reduction"
    assert item["linked_source_entry_ids"] == []
    assert item["normalized_subject"] == "Future wildlife tree retention area reduction"


def test_specialized_compiled_logic_for_cultural_heritage_uses_aspatial_reduction() -> (
    None
):
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_021_cultural_heritage_and_archaeological_resources",
        parent_label="Cultural heritage and archaeological resources",
        land_base_stage="lhlb_to_thlb",
        stage_label="LHLB -> THLB",
        execution_class="projected_harvest_exclusion",
        benchmark_marginal_area_ha=34205.0,
        benchmark_cumulative_area_ha=1676059.0,
        table_provenance="TSR_2024/...#table=3,row=21",
        row_order=21,
        linked_subsection={
            "body": "This will be modelled as an aspatial reduction to the THLB.",
            "provenance_id": "TSR_2024/...#page=37",
            "page_number": 37,
        },
    )

    assert items is not None
    assert len(items) == 1
    item = items[0]
    assert item["compiled_operation_type"] == "aspatial_reduction"
    assert item["linked_source_entry_ids"] == []
    assert (
        item["normalized_subject"]
        == "Cultural heritage and archaeological resources reduction"
    )


def test_specialized_compiled_logic_for_future_roads_uses_aspatial_area_reduction() -> (
    None
):
    items = tsr_recipes._specialized_compiled_logic_for_parent_step(
        parent_step_id="thlb_parent_023_future_roads",
        parent_label="Future roads",
        land_base_stage="glb_to_aflb",
        stage_label="GLB -> AFLB",
        execution_class="drop_from_universe",
        benchmark_marginal_area_ha=None,
        benchmark_cumulative_area_ha=None,
        table_provenance="TSR_2024/...#table=3,row=23",
        row_order=23,
        linked_subsection={
            "body": "The average factor is 2.28% for all three Cariboo TSAs. In total, 22 754 hectares will be excluded to represent future road development.",
            "provenance_id": "TSR_2024/...#page=27",
            "page_number": 27,
        },
    )

    assert items is not None
    assert len(items) == 1
    item = items[0]
    assert item["compiled_operation_type"] == "aspatial_area_reduction"
    assert item["linked_source_entry_ids"] == []
    assert item["benchmark_marginal_area_ha"] == pytest.approx(22754.0)
    assert (
        item["normalized_subject"]
        == "Future roads, trails, and landings area reduction"
    )


def test_apply_aspatial_area_reduction_sets_effective_area_without_touching_canonical_area_or_thlb() -> (
    None
):
    checkpoint = gpd.GeoDataFrame(
        {
            "_stand_area_sqm": [100.0, 100.0],
            "FEATURE_AREA_SQM": [100.0, 100.0],
            "POLYGON_AREA": [0.01, 0.01],
            "GEOMETRY_AREA": [0.01, 0.01],
            "AREA_HA": [0.01, 0.01],
            "Shape_Area": [100.0, 100.0],
            "thlb_fact": [1.0, 1.0],
            "thlb": [1.0, 1.0],
        },
        geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)],
        crs="EPSG:3005",
    )

    updated, removed_area_ha, affected_row_count = (
        tsr_recipes._apply_aspatial_area_reduction(
            checkpoint,
            target_removed_area_ha=0.01,
        )
    )

    assert removed_area_ha == pytest.approx(0.01)
    assert affected_row_count == 2
    assert updated["_stand_area_sqm"].tolist() == pytest.approx([50.0, 50.0])
    assert updated[tsr_recipes.TSR_EFFECTIVE_AREA_SQM_COLUMN].tolist() == pytest.approx(
        [50.0, 50.0]
    )
    assert updated["FEATURE_AREA_SQM"].tolist() == pytest.approx([100.0, 100.0])
    assert updated["POLYGON_AREA"].tolist() == pytest.approx([0.01, 0.01])
    assert updated["GEOMETRY_AREA"].tolist() == pytest.approx([0.01, 0.01])
    assert updated["AREA_HA"].tolist() == pytest.approx([0.01, 0.01])
    assert updated["Shape_Area"].tolist() == pytest.approx([100.0, 100.0])
    assert updated["thlb_fact"].tolist() == pytest.approx([1.0, 1.0])
    assert updated["thlb"].tolist() == pytest.approx([1.0, 1.0])


def test_apply_aspatial_area_reduction_is_idempotent_against_canonical_area() -> None:
    checkpoint = gpd.GeoDataFrame(
        {
            "_stand_area_sqm": [50.0, 50.0],
            tsr_recipes.TSR_EFFECTIVE_AREA_SQM_COLUMN: [50.0, 50.0],
            "FEATURE_AREA_SQM": [100.0, 100.0],
            "thlb_fact": [1.0, 1.0],
            "thlb": [1.0, 1.0],
        },
        geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)],
        crs="EPSG:3005",
    )

    updated, removed_area_ha, _affected_row_count = (
        tsr_recipes._apply_aspatial_area_reduction(
            checkpoint,
            target_removed_area_ha=0.01,
        )
    )

    assert removed_area_ha == pytest.approx(0.01)
    assert updated[tsr_recipes.TSR_EFFECTIVE_AREA_SQM_COLUMN].tolist() == pytest.approx(
        [50.0, 50.0]
    )
    assert updated["_stand_area_sqm"].tolist() == pytest.approx([50.0, 50.0])


def test_run_tsr_thlb_parent_step_treats_no_matching_filtered_source_as_noop(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    wildlife_path = (
        instance_root / "data" / "downloads" / "bcdc" / "WILDLIFE" / "WILDLIFE.gpkg"
    )
    wildlife_path.parent.mkdir(parents=True, exist_ok=True)
    wildlife = gpd.GeoDataFrame(
        {"TIMBER_HARVEST_CODE": ["CONDITIONAL HARVEST ZONE"]},
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    )
    wildlife.to_file(wildlife_path, driver="GPKG")

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["entries"] = [
        {
            "entry_id": "whse_wildlife_management_wcp_ungulate",
            "label": "WHSE_WILDLIFE_MANAGEMENT.WCP_UNGULATE",
            "artifact_path": "data/downloads/bcdc/WILDLIFE/WILDLIFE.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "reference_only",
            "benchmark_cumulative_area_ha": 1.0,
            "row_order": 1,
        },
        {
            "parent_step_id": "thlb_parent_008_wildlife_habitat_areas",
            "parent_label": "Wildlife habitat areas",
            "parent_kind": "transformation",
            "land_base_stage": "aflb_to_lhlb",
            "stage_label": "AFLB -> LHLB",
            "execution_class": "legal_harvest_exclusion",
            "benchmark_marginal_area_ha": 0.2,
            "benchmark_cumulative_area_ha": 0.8,
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_008_wildlife_habitat_areas_compiled_01",
                    "parent_step_id": "thlb_parent_008_wildlife_habitat_areas",
                    "label": "Wildlife habitat area no-harvest polygons",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "land_base_stage": "aflb_to_lhlb",
                    "operation_type": "select_spatial_intersect",
                    "linked_source_entry_ids": [
                        "whse_wildlife_management_wcp_ungulate"
                    ],
                    "source_attribute_filters": [
                        {
                            "field": "TIMBER_HARVEST_CODE",
                            "operator": "eq",
                            "value": "NO HARVEST ZONE",
                        }
                    ],
                }
            ],
            "row_order": 8,
        },
    ]
    recipe_payload["steps"] = []
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    checkpoint_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1],
            "MAP_ID": ["092O071"],
        },
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)

    result = tsr_recipes.run_tsr_thlb_parent_step(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_id="thlb_parent_008_wildlife_habitat_areas",
        checkpoint_path=checkpoint_path,
        map_ids=("092O071",),
        auto_map_id_smoke_subset=False,
    )

    assert result.status == "applied"
    assert result.removed_area_ha == pytest.approx(0.0)
    payload = json.loads(result.result_json_path.read_text(encoding="utf-8"))
    item = next(
        entry
        for entry in payload["executed_items"]
        if entry["parent_step_id"] == "thlb_parent_008_wildlife_habitat_areas"
    )
    assert item["execution_status"] == "applied_noop"
    assert (
        "no features matched the current attribute filters"
        in " ".join(item["runtime_notes"]).lower()
    )


def test_execute_workbench_compiled_item_handles_no_deduction() -> None:
    checkpoint = gpd.GeoDataFrame(
        {
            "thlb_fact": [1.0],
            "_row_id": [0],
            "_stand_area_sqm": [100.0],
        },
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3005",
    )

    updated, runtime_item = tsr_recipes._execute_workbench_compiled_item(
        checkpoint=checkpoint,
        compiled_item={
            "step_id": "noop_step",
            "normalized_action": "no_deduction",
            "compiled_operation_type": "no_deduction",
            "notes": ["User-directed reconciliation stop-line."],
            "land_base_stage": "lhlb_to_thlb",
        },
        instance_root=Path.cwd(),
        source_entry_map={},
        total_area_benchmark_ha=None,
    )

    assert runtime_item["execution_status"] == "applied_noop"
    assert runtime_item["removed_area_ha"] == pytest.approx(0.0)
    assert runtime_item["remaining_area_ha"] == pytest.approx(0.01)
    assert (
        "no spatial or aspatial deduction applied"
        in " ".join(runtime_item["runtime_notes"]).lower()
    )
    assert updated["thlb_fact"].tolist() == pytest.approx([1.0])


def test_run_tsr_thlb_parent_step_uses_curve_ready_checkpoint_for_step14(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    bundle_root = instance_root / "data" / "model_input_bundle"
    bundle_root.mkdir(parents=True, exist_ok=True)
    (bundle_root / "curve_table.csv").write_text(
        "curve_id,curve_type\n1001,untreated\n1002,untreated\n1003,untreated\n",
        encoding="utf-8",
    )
    (bundle_root / "curve_points_table.csv").write_text(
        "curve_id,x,y\n"
        "1001,40,20\n"
        "1001,80,40\n"
        "1001,120,60\n"
        "1001,160,60\n"
        "1002,40,80\n"
        "1002,80,160\n"
        "1002,120,200\n"
        "1002,160,200\n"
        "1003,40,120\n"
        "1003,80,240\n"
        "1003,120,300\n"
        "1003,160,320\n",
        encoding="utf-8",
    )

    checkpoint1_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint1_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint1 = gpd.GeoDataFrame(
        {"FEATURE_ID": [1], "MAP_ID": ["092O071"]},
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3005",
    )
    checkpoint1.to_feather(checkpoint1_path)
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(-10, -10, 20, 20)],
        names=["Test LU"],
    )
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(-10, -10, 2100, 2100)],
        names=["Test LU"],
    )
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(-10, -10, 2100, 2100)],
        names=["Test LU"],
    )

    checkpoint7_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint7.feather"
    checkpoint7 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1, 2, 3, 4],
            "MAP_ID": ["092O071", "092O071", "092O071", "092O071"],
            "curve1": [1001, 1002, 1003, 1002],
            "femic_step13_steep_slope_flag": [False, True, True, False],
        },
        geometry=[
            box(0, 0, 10, 10),
            box(10, 0, 20, 10),
            box(20, 0, 30, 10),
            box(30, 0, 40, 10),
        ],
        crs="EPSG:3005",
    )
    checkpoint7.to_feather(checkpoint7_path)
    enriched_checkpoint_path = (
        instance_root
        / "data"
        / "tsr"
        / "ria_vri_vclr1p_checkpoint7.step13_attrs.feather"
    )
    enriched_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint7.to_feather(enriched_checkpoint_path)

    recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    recipe_payload["recipe_contract"]["status"] = "built"
    recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_002_land_not_administered_by_the_province",
            "parent_label": "Land not administered by the Province",
            "parent_kind": "transformation",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "drop_from_universe",
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_002_compiled_01",
                    "parent_step_id": "thlb_parent_002_land_not_administered_by_the_province",
                    "label": "Land not administered by the Province",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "land_base_stage": "glb_to_aflb",
                    "compiled_operation_type": "select_attribute",
                    "checkpoint_attribute_mode": "any",
                    "checkpoint_attribute_filters": [
                        {"field": "FEATURE_ID", "operator": "eq", "value": 1}
                    ],
                }
            ],
            "row_order": 2,
        },
        {
            "parent_step_id": "thlb_parent_014_sites_with_low_growing_timber_potential",
            "parent_label": "Sites with low growing timber potential",
            "parent_kind": "transformation",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "projected_harvest_exclusion",
            "benchmark_marginal_area_ha": 1.0,
            "benchmark_cumulative_area_ha": 0.0,
            "compiled_logic": [
                {
                    "step_id": "thlb_parent_014_compiled_01",
                    "parent_step_id": "thlb_parent_014_sites_with_low_growing_timber_potential",
                    "label": "Non-steep 67.1 m3/ha threshold",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "land_base_stage": "lhlb_to_thlb",
                    "compiled_operation_type": "curve_volume_threshold_exclusion",
                    "curve_id_column": "curve1",
                    "minimum_volume_m3_per_ha": 67.1,
                    "curve_volume_metric": "volume_at_age",
                    "curve_volume_age_years": 160.0,
                    "checkpoint_attribute_mode": "any",
                    "checkpoint_attribute_filters": [
                        {
                            "field": "femic_step13_steep_slope_flag",
                            "operator": "eq",
                            "value": False,
                        }
                    ],
                },
                {
                    "step_id": "thlb_parent_014_compiled_02",
                    "parent_step_id": "thlb_parent_014_sites_with_low_growing_timber_potential",
                    "label": "Steep-slope 250 m3/ha threshold",
                    "step_status": "ready",
                    "execution_status": "ready",
                    "step_kind": "netdown_rule",
                    "land_base_stage": "lhlb_to_thlb",
                    "compiled_operation_type": "curve_volume_threshold_exclusion",
                    "curve_id_column": "curve1",
                    "minimum_volume_m3_per_ha": 250.0,
                    "curve_volume_metric": "volume_at_age",
                    "curve_volume_age_years": 160.0,
                    "checkpoint_attribute_mode": "any",
                    "checkpoint_attribute_filters": [
                        {
                            "field": "femic_step13_steep_slope_flag",
                            "operator": "eq",
                            "value": True,
                        }
                    ],
                },
            ],
            "row_order": 14,
        },
    ]
    recipe_payload["steps"] = []
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_recipes.run_tsr_thlb_parent_step(
        recipe_path=init_result.thlb_netdown_recipe_path,
        parent_step_id="thlb_parent_014_sites_with_low_growing_timber_potential",
        map_ids=("092O071",),
        auto_map_id_smoke_subset=False,
    )

    assert result.checkpoint_path == enriched_checkpoint_path.resolve()
    assert result.executed_parent_step_ids == (
        "thlb_parent_014_sites_with_low_growing_timber_potential",
    )
    assert result.status == "applied"
    assert result.removed_area_ha == pytest.approx(0.02)
    output = gpd.read_feather(result.output_path)
    assert output["thlb"].tolist() == [0, 0, 1, 1]
    payload = json.loads(result.result_json_path.read_text(encoding="utf-8"))
    items = [
        entry
        for entry in payload["executed_items"]
        if entry["parent_step_id"]
        == "thlb_parent_014_sites_with_low_growing_timber_potential"
    ]
    assert len(items) == 2
    non_steep_item = next(
        entry
        for entry in items
        if entry["minimum_volume_m3_per_ha"] == pytest.approx(67.1)
    )
    steep_item = next(
        entry
        for entry in items
        if entry["minimum_volume_m3_per_ha"] == pytest.approx(250.0)
    )
    assert non_steep_item["execution_status"] == "applied"
    assert non_steep_item["removed_area_ha"] == pytest.approx(0.01)
    assert non_steep_item["checkpoint_filter_row_count"] == 2
    assert non_steep_item["active_checkpoint_filter_row_count"] == 2
    assert (
        non_steep_item["curve_metric_description"] == "assigned curve volume at age 160"
    )
    assert steep_item["execution_status"] == "applied"
    assert steep_item["removed_area_ha"] == pytest.approx(0.01)
    assert steep_item["checkpoint_filter_row_count"] == 2
    assert steep_item["active_checkpoint_filter_row_count"] == 2
    assert steep_item["curve_metric_description"] == "assigned curve volume at age 160"
    assert "preserved geometry/fragments and set THLB state to 0" in " ".join(
        steep_item["runtime_notes"]
    )


def test_auto_select_smoke_map_ids_for_parent_step_prefers_tile_with_source_hits(
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    road_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_IMAGERY_AND_BASE_MAPS_MOT_HIGHWAY_PROFILES_SP"
        / "WHSE_IMAGERY_AND_BASE_MAPS_MOT_HIGHWAY_PROFILES_SP.gpkg"
    )
    road_path.parent.mkdir(parents=True, exist_ok=True)
    roads = gpd.GeoDataFrame(
        {"name": ["hwy"]},
        geometry=[LineString([(220, 10), (280, 10)])],
        crs="EPSG:3005",
    )
    roads.to_file(road_path, driver="GPKG")

    checkpoint = gpd.GeoDataFrame(
        {
            "MAP_ID": ["092O071", "092O071", "092O065", "092O065"],
        },
        geometry=[
            box(0, 0, 100, 100),
            box(100, 0, 200, 100),
            box(200, 0, 300, 100),
            box(300, 0, 400, 100),
        ],
        crs="EPSG:3005",
    )
    parent_step = {
        "parent_step_id": "thlb_parent_004_roads_and_landings",
        "linked_source_entry_ids": ["mot_highways"],
    }
    compiled_steps = [
        {
            "step_id": "roads_01",
            "linked_source_entry_ids": ["mot_highways"],
        }
    ]
    source_entry_map = {
        "mot_highways": {
            "entry_id": "mot_highways",
            "artifact_path": (
                "data/downloads/bcdc/WHSE_IMAGERY_AND_BASE_MAPS_MOT_HIGHWAY_PROFILES_SP/"
                "WHSE_IMAGERY_AND_BASE_MAPS_MOT_HIGHWAY_PROFILES_SP.gpkg"
            ),
        }
    }

    selected = tsr_recipes._auto_select_smoke_map_ids_for_parent_step(
        checkpoint=checkpoint,
        parent_step=parent_step,
        compiled_steps=compiled_steps,
        instance_root=instance_root,
        source_entry_map=source_entry_map,
    )

    assert selected == ("092O065",)


def test_filter_checkpoint_by_landscape_units_matches_name_and_returns_subset(
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    lu_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_LAND_USE_PLANNING_RMP_LANDSCAPE_UNIT_SVW"
        / "WHSE_LAND_USE_PLANNING_RMP_LANDSCAPE_UNIT_SVW.gpkg"
    )
    lu_path.parent.mkdir(parents=True, exist_ok=True)
    lu = gpd.GeoDataFrame(
        {
            "LANDSCAPE_UNIT_ID": [1372, 1380],
            "LANDSCAPE_UNIT_NUMBER": ["r5_wilk", "r5_chim"],
            "LANDSCAPE_UNIT_NAME": ["Williams Lake", "Chimney"],
        },
        geometry=[box(0, 0, 100, 100), box(200, 0, 300, 100)],
        crs="EPSG:3005",
    )
    lu.to_file(lu_path, driver="GPKG")

    checkpoint = gpd.GeoDataFrame(
        {
            "MAP_ID": ["092O071", "092O065"],
        },
        geometry=[box(10, 10, 20, 20), box(210, 10, 220, 20)],
        crs="EPSG:3005",
    )

    subset, selected_names = tsr_recipes._filter_checkpoint_by_landscape_units(
        checkpoint,
        instance_root=instance_root,
        landscape_units=("Williams Lake", "1380"),
    )

    assert tuple(sorted(selected_names)) == ("Chimney", "Williams Lake")
    assert set(subset["MAP_ID"]) == {"092O071", "092O065"}


def test_resolve_tsr_total_area_benchmark_infers_from_first_glb_to_aflb_row() -> None:
    recipe = tsr_catalog.TsrThlbNetdownRecipeRecord(
        schema_version=1,
        recipe_kind="thlb_netdown",
        tsa=tsr_catalog.TsrOverlayTsaRecord(
            tsa_id="tsa_29",
            tsa_code="29",
            tsa_name="Williams Lake",
        ),
        canonical_inputs=tsr_catalog.TsrRecipeCanonicalInputs(
            registry_path="metadata/tsr/tsa_registry.json",
            documents_path="metadata/tsr/tsa_documents.json",
            candidate_facts_path="metadata/tsr/tsa_candidate_facts.json",
        ),
        instance_inputs=tsr_catalog.TsrThlbNetdownRecipeInstanceInputs(
            overlay_path="config/tsr/overlay.yaml",
            source_layer_recipe_path="config/tsr/source_layers.recipe.yaml",
            source_layer_overrides_path="config/tsr/source_layer_overrides.yaml",
        ),
        recipe_contract={},
        parent_steps=(
            {
                "parent_step_id": "milestone_total",
                "parent_label": "Total TSA area",
                "parent_kind": "milestone",
                "land_base_stage": "reference_target",
                "benchmark_cumulative_area_ha": None,
            },
            {
                "parent_step_id": "step_001",
                "parent_label": "Land not administered by the Province",
                "parent_kind": "transformation",
                "land_base_stage": "glb_to_aflb",
                "benchmark_marginal_area_ha": 697033.0,
                "benchmark_cumulative_area_ha": 4236602.0,
            },
        ),
        steps=(),
    )

    assert tsr_recipes._resolve_tsr_total_area_benchmark(recipe) == pytest.approx(
        4933635.0
    )


def test_run_tsr_thlb_netdown_recipe_writes_thlb_fact_checkpoint_and_audit(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "MDWR" / "MDWR.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    exclusion = gpd.GeoDataFrame(
        {"rule": ["mdwr"]},
        geometry=[box(0, 0, 5, 10)],
        crs="EPSG:3005",
    )
    exclusion.to_file(exclusion_path, driver="GPKG")

    checkpoint_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint8.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1, 2],
            "thlb_raw": [100.0, 100.0],
        },
        geometry=[box(0, 0, 10, 10), box(20, 0, 30, 10)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "run"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "mdwr",
            "label": "Mule Deer winter range",
            "recommended_query": "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP",
            "acquisition_strategy": "wfs_fetch",
            "artifact_path": "data/downloads/bcdc/MDWR/MDWR.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )
    overrides_payload = {
        "schema_version": 1,
        "tsa": {
            "tsa_id": "tsa_29",
            "tsa_code": "29",
            "tsa_name": "Williams Lake",
        },
        "source_overlay_path": "config/tsr/overlay.yaml",
        "entries": [
            {
                "query": "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP",
                "current_public_status": "fetched",
                "matched_by": "object_name",
                "top_match_title": "Mule Deer winter range",
                "dataset_page_url": "https://example.invalid/mdwr",
                "suggested_fetch_strategy": "wfs_getfeature_bbox",
                "current_public_notes": [],
                "replacement_family_candidates": [],
                "override_kind": "local_path",
                "override_value": "data/downloads/bcdc/MDWR/MDWR.gpkg",
                "notes": "Reviewed local override for proving-ground coverage.",
            }
        ],
    }
    (instance_root / "config" / "tsr" / "source_layer_overrides.yaml").write_text(
        tsr_recipes.yaml.safe_dump(
            overrides_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    thlb_recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    thlb_recipe_payload["recipe_contract"]["status"] = "built"
    thlb_recipe_payload["steps"] = [
        {
            "step_id": "thlb_step_001_use_land_base",
            "order_index": 1,
            "step_kind": "reference_target",
            "label": "Long-term THLB reference",
            "land_base_stage": "reference_target",
            "stage_label": "Reference targets",
            "execution_class": "reference_only",
            "normalized_action": "use_land_base",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 25,
        },
        {
            "step_id": "thlb_step_002_mdwr",
            "order_index": 2,
            "step_kind": "netdown_rule",
            "label": "Mule Deer winter range",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "projected_harvest_exclusion",
            "normalized_action": "exclude",
            "linked_source_entry_ids": ["mdwr"],
            "step_status": "ready",
            "page_number": 47,
        },
        {
            "step_id": "thlb_step_003_wtra",
            "order_index": 3,
            "step_kind": "netdown_rule",
            "label": "WTRA",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "aspatial_fallback_candidate",
            "normalized_action": "aspatial_reduction",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 50,
        },
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            thlb_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_recipes.run_tsr_thlb_netdown_recipe(
        recipe_path=init_result.thlb_netdown_recipe_path
    )

    assert result.execution_mode == tsr_recipes.TSR_THLB_EXECUTION_MODE_HYBRID
    assert result.baseline_signal == "thlb_raw"
    assert result.step_count == 3
    assert result.outcome_counts["applied"] == 1
    assert result.outcome_counts["applied_noop"] == 1
    assert result.outcome_counts["unsupported"] == 1
    assert result.input_area_ha == pytest.approx(0.02)
    assert result.baseline_managed_area_ha == pytest.approx(0.02)
    assert result.final_managed_area_ha == pytest.approx(0.015)
    assert result.legacy_reference_managed_area_ha is None
    assert result.tsr_reported_thlb_area_ha is None
    assert result.tsr_reported_aflb_area_ha is None

    output = gpd.read_feather(result.output_path)
    assert output["thlb_fact"].tolist() == pytest.approx([0.5, 1.0])

    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit_payload["execution_mode"] == tsr_recipes.TSR_THLB_EXECUTION_MODE_HYBRID
    assert audit_payload["baseline_signal"] == "thlb_raw"
    assert audit_payload["input_area_ha"] == pytest.approx(0.02)
    assert audit_payload["outcome_counts"]["applied"] == 1
    assert result.status_report_path.exists()
    assert result.runtime_status_report_path.exists()
    status_text = result.status_report_path.read_text(encoding="utf-8")
    assert "# THLB Netdown Status Report: TSA 29 (Williams Lake)" in status_text
    assert "## Backbone Summary" in status_text
    assert "GLB:AFLB current proxy" in status_text
    assert "AFLB:THLB current" in status_text
    assert "AFLB lock state: `unlocked`" in status_text
    assert (
        "Lock dependency: cutting the AFLB lock automatically invalidates the THLB lock"
        in status_text
    )
    assert "## Stage-by-Stage THLB Steps" in status_text
    assert "### LHLB -> THLB" in status_text
    assert "Linked source layers:" in status_text
    assert "Review logic mode: `user_overlay`" in status_text
    assert "user-overlay logic mode: `local_path`" in status_text
    recipe = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    )
    assert recipe.recipe_contract["status"] == "run"
    assert (
        recipe.recipe_contract["status_report_path"]
        == "config/tsr/thlb_netdown.status.md"
    )


def test_run_tsr_thlb_netdown_recipe_reconstructed_mode_fragments_binary_thlb(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "OGMA" / "OGMA.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    exclusion = gpd.GeoDataFrame(
        {"rule": ["ogma"]},
        geometry=[box(0, 0, 5, 10)],
        crs="EPSG:3005",
    )
    exclusion.to_file(exclusion_path, driver="GPKG")

    checkpoint1_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint1_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint1 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [100, 200],
            "FOR_MGMT_LAND_BASE_IND": ["Y", "N"],
            "BCLCS_LEVEL_2": ["T", "T"],
            "NON_PRODUCTIVE_CD": [None, None],
            "BEC_ZONE_CODE": ["SBS", "SBS"],
            "PROJ_AGE_1": [5, 80],
            "BASAL_AREA": [1.0, 20.0],
            "LIVE_STAND_VOLUME_125": [0.0, 50.0],
            "MAP_ID": ["093J034", "093J099"],
            "POLYGON_AREA": [0.01, 0.01],
            "FEATURE_AREA_SQM": [100.0, 100.0],
            "FEATURE_LENGTH_M": [40.0, 40.0],
            "GEOMETRY_AREA": [0.01, 0.01],
            "Shape_Area": [100.0, 100.0],
            "Shape_Length": [40.0, 40.0],
        },
        geometry=[box(0, 0, 10, 10), box(20, 0, 30, 10)],
        crs="EPSG:3005",
    )
    checkpoint1.to_feather(checkpoint1_path)
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(-10, -10, 20, 20)],
        names=["Test LU"],
    )
    _write_landscape_unit_layer(
        instance_root,
        geometries=[
            box(-10, -10, 15, 20),
            box(15, -10, 35, 20),
            box(35, -10, 55, 20),
        ],
        names=["West", "Central", "East"],
    )
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(-10, -10, 40, 20)],
        names=["Test LU"],
    )

    checkpoint8_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint8.feather"
    checkpoint8 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1],
            "thlb_raw": [100.0],
        },
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3005",
    )
    checkpoint8.to_feather(checkpoint8_path)

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "run"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "ogma",
            "label": "OGMA",
            "recommended_query": "WHSE_LAND_USE_PLANNING.RMP_OGMA_LEGAL_CURRENT_SVW",
            "acquisition_strategy": "wfs_fetch",
            "artifact_path": "data/downloads/bcdc/OGMA/OGMA.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    thlb_recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    thlb_recipe_payload["recipe_contract"]["status"] = "built"
    thlb_recipe_payload["steps"] = [
        {
            "step_id": "thlb_step_001_land_base",
            "order_index": 1,
            "step_kind": "netdown_rule",
            "label": "Timber harvesting land base",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "no_deduction",
            "normalized_action": "use_land_base",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 24,
        },
        {
            "step_id": "thlb_step_002_ogma",
            "order_index": 2,
            "step_kind": "netdown_rule",
            "label": "OGMA",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "projected_harvest_exclusion",
            "normalized_action": "exclude",
            "linked_source_entry_ids": ["ogma"],
            "step_status": "ready",
            "page_number": 48,
        },
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            thlb_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_recipes.run_tsr_thlb_netdown_recipe(
        recipe_path=init_result.thlb_netdown_recipe_path,
        execution_mode=tsr_recipes.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
    )

    assert result.execution_mode == tsr_recipes.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
    assert result.checkpoint_path == checkpoint1_path.resolve()
    assert result.baseline_signal == "checkpoint1_aflb_initialization"
    assert result.input_area_ha == pytest.approx(0.02)
    assert result.baseline_managed_area_ha == pytest.approx(0.01)
    assert result.final_managed_area_ha == pytest.approx(0.005)
    assert result.legacy_reference_managed_area_ha == pytest.approx(0.01)
    assert result.selected_map_ids == ()
    assert result.tsr_reported_aflb_area_ha is None

    output = gpd.read_feather(result.output_path)
    assert len(output) == 2
    assert set(output["SOURCE_FEATURE_ID"].tolist()) == {100}
    assert set(output["thlb"].tolist()) == {0, 1}
    assert set(output["thlb_fact"].tolist()) == {0.0, 1.0}
    assert output["FEATURE_ID"].is_unique

    managed = output.loc[output["thlb_fact"] > 0.0]
    unmanaged = output.loc[output["thlb_fact"] == 0.0]
    assert managed.geometry.area.sum() / 10000.0 == pytest.approx(0.005)
    assert unmanaged.geometry.area.sum() / 10000.0 == pytest.approx(0.005)

    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert (
        audit_payload["execution_mode"]
        == tsr_recipes.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
    )
    assert audit_payload["input_area_ha"] == pytest.approx(0.02)
    assert audit_payload["legacy_reference_managed_area_ha"] == pytest.approx(0.01)
    assert audit_payload["outcome_counts"]["applied"] == 1
    reconstructed_status = result.status_report_path.read_text(encoding="utf-8")
    assert "Execution mode: `reconstructed`" in reconstructed_status
    assert "Legacy raster THLB reference: `0.010 ha`" in reconstructed_status
    assert "### GLB -> AFLB" in reconstructed_status
    assert "### LHLB -> THLB" in reconstructed_status

    recipe = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    )
    assert (
        recipe.recipe_contract["reconstructed_output_checkpoint_path"]
        == "data/tsr/thlb_reconstructed_checkpoint.feather"
    )
    assert recipe.recipe_contract["selected_map_ids"] == []
    assert (
        recipe.recipe_contract["status_report_path"]
        == "config/tsr/thlb_reconstructed.status.md"
    )


def test_run_tsr_thlb_netdown_recipe_reconstructed_mode_applies_explicit_aspatial_fallback(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "OGMA" / "OGMA.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    exclusion = gpd.GeoDataFrame(
        {"rule": ["ogma"]},
        geometry=[box(0, 0, 50, 100)],
        crs="EPSG:3005",
    )
    exclusion.to_file(exclusion_path, driver="GPKG")

    checkpoint1_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint1_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint1 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [100],
            "FOR_MGMT_LAND_BASE_IND": ["Y"],
            "BCLCS_LEVEL_2": ["T"],
            "NON_PRODUCTIVE_CD": [None],
            "BEC_ZONE_CODE": ["SBS"],
            "PROJ_AGE_1": [80],
            "BASAL_AREA": [20.0],
            "LIVE_STAND_VOLUME_125": [50.0],
            "MAP_ID": ["093J034"],
            "POLYGON_AREA": [1.0],
            "FEATURE_AREA_SQM": [10000.0],
            "FEATURE_LENGTH_M": [400.0],
            "GEOMETRY_AREA": [1.0],
            "Shape_Area": [10000.0],
            "Shape_Length": [400.0],
        },
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    )
    checkpoint1.to_feather(checkpoint1_path)
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(-10, -10, 110, 110)],
        names=["Test LU"],
    )

    checkpoint8_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint8.feather"
    checkpoint8 = gpd.GeoDataFrame(
        {"FEATURE_ID": [1], "thlb_raw": [100.0]},
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    )
    checkpoint8.to_feather(checkpoint8_path)

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "run"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "ogma",
            "label": "OGMA",
            "recommended_query": "WHSE_LAND_USE_PLANNING.RMP_OGMA_LEGAL_CURRENT_SVW",
            "acquisition_strategy": "wfs_fetch",
            "artifact_path": "data/downloads/bcdc/OGMA/OGMA.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    thlb_recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    thlb_recipe_payload["recipe_contract"]["status"] = "built"
    thlb_recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "reference_target",
            "stage_label": "Reference targets",
            "benchmark_cumulative_area_ha": 1.0,
        }
    ]
    thlb_recipe_payload["steps"] = [
        {
            "step_id": "thlb_step_001_land_base",
            "order_index": 1,
            "step_kind": "netdown_rule",
            "label": "Timber harvesting land base",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "no_deduction",
            "normalized_action": "use_land_base",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 24,
        },
        {
            "step_id": "thlb_step_002_ogma",
            "order_index": 2,
            "step_kind": "netdown_rule",
            "label": "OGMA",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "projected_harvest_exclusion",
            "normalized_action": "exclude",
            "linked_source_entry_ids": ["ogma"],
            "step_status": "ready",
            "page_number": 48,
        },
        {
            "step_id": "thlb_step_003_wtra",
            "order_index": 3,
            "step_kind": "netdown_rule",
            "label": "WTRA",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "aspatial_fallback_candidate",
            "normalized_action": "aspatial_reduction",
            "benchmark_marginal_area_ha": 0.25,
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 50,
        },
        {
            "step_id": "thlb_step_004_manual",
            "order_index": 4,
            "step_kind": "netdown_rule",
            "label": "Manual review seam",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "manual_review_required",
            "normalized_action": "review",
            "linked_source_entry_ids": [],
            "step_status": "manual_review_required",
            "page_number": 55,
        },
        {
            "step_id": "thlb_step_005_noop",
            "order_index": 5,
            "step_kind": "netdown_rule",
            "label": "No-op tail",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "no_deduction",
            "normalized_action": "no_deduction",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 56,
        },
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            thlb_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_recipes.run_tsr_thlb_netdown_recipe(
        recipe_path=init_result.thlb_netdown_recipe_path,
        execution_mode=tsr_recipes.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
    )

    assert result.baseline_managed_area_ha == pytest.approx(1.0)
    assert result.final_managed_area_ha == pytest.approx(0.375)

    output = gpd.read_feather(result.output_path)
    assert sorted(output["thlb_fact"].tolist()) == pytest.approx([0.0, 0.75])

    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit_payload["fragment_overlay_step_count"] == 1
    assert audit_payload["aspatial_fallback_step_count"] == 1
    assert audit_payload["aspatial_fallback_area_ha"] == pytest.approx(0.125)
    assert audit_payload["blocked_exact_overlay_step_count"] == 0
    assert audit_payload["stand_binary_fallback_step_count"] == 0
    assert audit_payload["steps"][2]["spatial_application_mode"] == "aspatial_fallback"
    assert audit_payload["steps"][2]["affected_area_ha"] == pytest.approx(0.125)
    assert audit_payload["steps"][3]["run_status"] == "unsupported"
    assert audit_payload["steps"][4]["run_status"] == "applied_noop"

    reconstructed_status = result.status_report_path.read_text(encoding="utf-8")
    assert "Explicit aspatial fallback steps: `1` / `0.125 ha`" in reconstructed_status
    assert (
        "explicit aspatial fallback means a TSR area target was applied honestly"
        in reconstructed_status
    )


def test_run_tsr_thlb_netdown_recipe_reconstructed_mode_executes_aspatial_area_fallback(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    checkpoint1_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint1_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint1 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [100],
            "FOR_MGMT_LAND_BASE_IND": ["Y"],
            "BCLCS_LEVEL_2": ["T"],
            "NON_PRODUCTIVE_CD": [None],
            "BEC_ZONE_CODE": ["SBS"],
            "PROJ_AGE_1": [80],
            "BASAL_AREA": [20.0],
            "LIVE_STAND_VOLUME_125": [50.0],
            "MAP_ID": ["093J034"],
            "POLYGON_AREA": [1.0],
            "FEATURE_AREA_SQM": [10000.0],
            "FEATURE_LENGTH_M": [400.0],
            "GEOMETRY_AREA": [1.0],
            "Shape_Area": [10000.0],
            "Shape_Length": [400.0],
        },
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    )
    checkpoint1.to_feather(checkpoint1_path)
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(-10, -10, 110, 110)],
        names=["Test LU"],
    )

    checkpoint8_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint8.feather"
    checkpoint8 = gpd.GeoDataFrame(
        {"FEATURE_ID": [1], "thlb_raw": [100.0]},
        geometry=[box(0, 0, 100, 100)],
        crs="EPSG:3005",
    )
    checkpoint8.to_feather(checkpoint8_path)

    thlb_recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    thlb_recipe_payload["recipe_contract"]["status"] = "built"
    thlb_recipe_payload["parent_steps"] = [
        {
            "parent_step_id": "thlb_parent_001_total_tsa_area",
            "parent_label": "Total TSA area",
            "parent_kind": "milestone",
            "land_base_stage": "reference_target",
            "stage_label": "Reference targets",
            "benchmark_cumulative_area_ha": 1.0,
        }
    ]
    thlb_recipe_payload["steps"] = [
        {
            "step_id": "thlb_step_001_land_base",
            "order_index": 1,
            "step_kind": "netdown_rule",
            "label": "Timber harvesting land base",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "no_deduction",
            "normalized_action": "use_land_base",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 24,
        },
        {
            "step_id": "thlb_step_002_future_roads",
            "order_index": 2,
            "step_kind": "netdown_rule",
            "label": "Future roads",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "aspatial_fallback_candidate",
            "normalized_action": "aspatial_area_reduction",
            "benchmark_marginal_area_ha": 0.25,
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 27,
        },
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            thlb_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_recipes.run_tsr_thlb_netdown_recipe(
        recipe_path=init_result.thlb_netdown_recipe_path,
        execution_mode=tsr_recipes.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
    )

    assert result.baseline_managed_area_ha == pytest.approx(1.0)
    assert result.final_managed_area_ha == pytest.approx(0.75)

    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit_payload["aspatial_fallback_step_count"] == 1
    assert audit_payload["aspatial_fallback_area_ha"] == pytest.approx(0.25)
    assert audit_payload["steps"][1]["spatial_application_mode"] == "aspatial_fallback"
    assert audit_payload["steps"][1]["affected_area_ha"] == pytest.approx(0.25)

    reconstructed_status = result.status_report_path.read_text(encoding="utf-8")
    assert "Explicit aspatial fallback steps: `1` / `0.250 ha`" in reconstructed_status


def test_run_tsr_thlb_netdown_recipe_reconstructed_mode_can_auto_select_map_id_subset(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    checkpoint1_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint1_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint1 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [100, 200],
            "FOR_MGMT_LAND_BASE_IND": ["Y", "Y"],
            "BCLCS_LEVEL_2": ["T", "T"],
            "NON_PRODUCTIVE_CD": [None, None],
            "BEC_ZONE_CODE": ["SBS", "SBS"],
            "PROJ_AGE_1": [5, 80],
            "BASAL_AREA": [1.0, 20.0],
            "LIVE_STAND_VOLUME_125": [0.0, 50.0],
            "MAP_ID": ["093J034", "093J099"],
        },
        geometry=[box(0, 0, 1000, 1000), box(0, 0, 2000, 2000)],
        crs="EPSG:3005",
    )
    checkpoint1.to_feather(checkpoint1_path)
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(-10, -10, 2100, 2100)],
        names=["Test LU"],
    )

    checkpoint8_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint8.feather"
    checkpoint8 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [1],
            "thlb_raw": [100.0],
        },
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3005",
    )
    checkpoint8.to_feather(checkpoint8_path)

    thlb_recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    thlb_recipe_payload["recipe_contract"]["status"] = "built"
    thlb_recipe_payload["steps"] = [
        {
            "step_id": "thlb_step_001_land_base",
            "order_index": 1,
            "step_kind": "netdown_rule",
            "label": "Timber harvesting land base",
            "normalized_action": "use_land_base",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 24,
        }
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            thlb_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_recipes.run_tsr_thlb_netdown_recipe(
        recipe_path=init_result.thlb_netdown_recipe_path,
        execution_mode=tsr_recipes.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
        auto_map_id_smoke_subset=True,
    )

    assert result.selected_map_ids == ("093J099",)
    assert result.baseline_managed_area_ha == pytest.approx(400.0)
    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit_payload["selected_map_ids"] == ["093J099"]


def test_run_tsr_thlb_netdown_recipe_reconstructed_mode_chunks_exact_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    monkeypatch.setattr(tsr_recipes, "_RECONSTRUCTED_FRAGMENT_ROW_THRESHOLD", 2)
    monkeypatch.setattr(tsr_recipes, "_RECONSTRUCTED_FRAGMENT_BATCH_SIZE", 1)

    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "OGMA" / "OGMA.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    exclusion = gpd.GeoDataFrame(
        {"rule": ["ogma_a", "ogma_b", "ogma_c"]},
        geometry=[box(0, 0, 5, 10), box(20, 0, 25, 10), box(40, 0, 45, 10)],
        crs="EPSG:3005",
    )
    exclusion.to_file(exclusion_path, driver="GPKG")

    checkpoint1_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint1_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint1 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [100, 200, 300],
            "FOR_MGMT_LAND_BASE_IND": ["Y", "Y", "Y"],
            "BCLCS_LEVEL_2": ["T", "T", "T"],
            "NON_PRODUCTIVE_CD": [None, None, None],
            "BEC_ZONE_CODE": ["SBS", "SBS", "SBS"],
            "PROJ_AGE_1": [80, 80, 80],
            "BASAL_AREA": [20.0, 20.0, 20.0],
            "LIVE_STAND_VOLUME_125": [50.0, 50.0, 50.0],
            "MAP_ID": ["093J034", "093J034", "093J034"],
            "POLYGON_AREA": [0.01, 0.01, 0.01],
            "FEATURE_AREA_SQM": [100.0, 100.0, 100.0],
            "FEATURE_LENGTH_M": [40.0, 40.0, 40.0],
            "GEOMETRY_AREA": [0.01, 0.01, 0.01],
            "Shape_Area": [100.0, 100.0, 100.0],
            "Shape_Length": [40.0, 40.0, 40.0],
            "tsa_code": ["k3z", "k3z", "k3z"],
            "au": [985501000, 985501000, 985501000],
        },
        geometry=[
            box(0, 0, 10, 10),
            box(20, 0, 30, 10),
            box(40, 0, 50, 10),
        ],
        crs="EPSG:3005",
    )
    checkpoint1.to_feather(checkpoint1_path)
    _write_landscape_unit_layer(
        instance_root,
        geometries=[
            box(-10, -10, 15, 20),
            box(15, -10, 35, 20),
            box(35, -10, 55, 20),
        ],
        names=["West", "Central", "East"],
    )

    checkpoint8_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint8.feather"
    checkpoint8 = gpd.GeoDataFrame(
        {"FEATURE_ID": [1], "thlb_raw": [100.0]},
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3005",
    )
    checkpoint8.to_feather(checkpoint8_path)

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "run"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "ogma",
            "label": "OGMA",
            "recommended_query": "WHSE_LAND_USE_PLANNING.RMP_OGMA_LEGAL_CURRENT_SVW",
            "acquisition_strategy": "wfs_fetch",
            "artifact_path": "data/downloads/bcdc/OGMA/OGMA.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    thlb_recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    thlb_recipe_payload["recipe_contract"]["status"] = "built"
    thlb_recipe_payload["steps"] = [
        {
            "step_id": "thlb_step_001_land_base",
            "order_index": 1,
            "step_kind": "netdown_rule",
            "label": "Timber harvesting land base",
            "land_base_stage": "glb_to_aflb",
            "stage_label": "GLB -> AFLB",
            "execution_class": "no_deduction",
            "normalized_action": "use_land_base",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 24,
        },
        {
            "step_id": "thlb_step_002_ogma",
            "order_index": 2,
            "step_kind": "netdown_rule",
            "label": "OGMA",
            "land_base_stage": "lhlb_to_thlb",
            "stage_label": "LHLB -> THLB",
            "execution_class": "projected_harvest_exclusion",
            "normalized_action": "exclude",
            "linked_source_entry_ids": ["ogma"],
            "step_status": "ready",
            "page_number": 48,
        },
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            thlb_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_recipes.run_tsr_thlb_netdown_recipe(
        recipe_path=init_result.thlb_netdown_recipe_path,
        execution_mode=tsr_recipes.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
    )

    assert result.final_managed_area_ha == pytest.approx(0.015)
    output = gpd.read_feather(result.output_path)
    assert set(output["SOURCE_FEATURE_ID"].tolist()) == {100, 200, 300}
    assert output["FEATURE_ID"].is_unique
    assert set(output["thlb"].tolist()) == {0, 1}

    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit_payload["allow_stand_binary_fallback"] is False
    assert audit_payload["fragment_overlay_step_count"] == 1
    assert audit_payload["stand_binary_fallback_step_count"] == 0
    assert audit_payload["lu_fragment_overlay_chunk_count"] == 3
    assert audit_payload["lu_fragment_overlay_feature_count"] == 3
    timing_summary = audit_payload["reconstructed_timing_summary"]
    assert timing_summary["total_runtime_seconds"] > 0.0
    assert timing_summary["overlay_seconds"] >= 0.0
    assert timing_summary["candidate_query_seconds"] >= 0.0
    assert timing_summary["slowest_steps"]
    assert timing_summary["slowest_steps"][0]["step_id"] == "thlb_step_002_ogma"
    run_step = audit_payload["steps"][1]
    assert run_step["spatial_application_mode"] == "fragment_overlay"
    assert run_step["candidate_row_count"] == 3
    assert run_step["fragment_batch_count"] == 3
    assert run_step["lu_chunk_count"] == 3
    assert run_step["intersecting_exclusion_feature_count"] == 3
    status_text = result.status_report_path.read_text(encoding="utf-8")
    assert "## Runtime Timing" in status_text
    assert "### Slowest Steps" in status_text

    fragments = build_fragments_geodataframe(
        checkpoint_path=result.output_path,
        au_table=pd.DataFrame([{"au_id": 985501000}]),
        tsa_list=["k3z"],
    )
    assert not fragments.empty
    assert set(fragments["IFM"].tolist()) == {"managed", "unmanaged"}


def test_run_tsr_thlb_netdown_recipe_reconstructed_mode_respects_lu_boundary_crossing(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "OGMA" / "OGMA.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {"rule": ["ogma"]},
        geometry=[box(5, 0, 15, 10)],
        crs="EPSG:3005",
    ).to_file(exclusion_path, driver="GPKG")

    checkpoint1_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint1_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint1 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [100],
            "FOR_MGMT_LAND_BASE_IND": ["Y"],
            "BCLCS_LEVEL_2": ["T"],
            "NON_PRODUCTIVE_CD": [None],
            "BEC_ZONE_CODE": ["SBS"],
            "PROJ_AGE_1": [80],
            "BASAL_AREA": [20.0],
            "LIVE_STAND_VOLUME_125": [50.0],
            "MAP_ID": ["093J034"],
            "POLYGON_AREA": [0.02],
            "FEATURE_AREA_SQM": [200.0],
            "FEATURE_LENGTH_M": [60.0],
            "GEOMETRY_AREA": [0.02],
            "Shape_Area": [200.0],
            "Shape_Length": [60.0],
        },
        geometry=[box(0, 0, 20, 10)],
        crs="EPSG:3005",
    )
    checkpoint1.to_feather(checkpoint1_path)
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(0, -5, 10, 15), box(10, -5, 20, 15)],
        names=["West", "East"],
    )

    checkpoint8_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint8.feather"
    gpd.GeoDataFrame(
        {"FEATURE_ID": [1], "thlb_raw": [100.0]},
        geometry=[box(0, 0, 20, 10)],
        crs="EPSG:3005",
    ).to_feather(checkpoint8_path)

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "run"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "ogma",
            "label": "OGMA",
            "recommended_query": "WHSE_LAND_USE_PLANNING.RMP_OGMA_LEGAL_CURRENT_SVW",
            "acquisition_strategy": "wfs_fetch",
            "artifact_path": "data/downloads/bcdc/OGMA/OGMA.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    thlb_recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    thlb_recipe_payload["recipe_contract"]["status"] = "built"
    thlb_recipe_payload["steps"] = [
        {
            "step_id": "thlb_step_001_land_base",
            "order_index": 1,
            "step_kind": "netdown_rule",
            "label": "Timber harvesting land base",
            "normalized_action": "use_land_base",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 24,
        },
        {
            "step_id": "thlb_step_002_ogma",
            "order_index": 2,
            "step_kind": "netdown_rule",
            "label": "OGMA",
            "normalized_action": "exclude",
            "linked_source_entry_ids": ["ogma"],
            "step_status": "ready",
            "page_number": 48,
        },
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            thlb_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_recipes.run_tsr_thlb_netdown_recipe(
        recipe_path=init_result.thlb_netdown_recipe_path,
        execution_mode=tsr_recipes.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
    )

    assert result.baseline_managed_area_ha == pytest.approx(0.02)
    assert result.final_managed_area_ha == pytest.approx(0.01)
    output = gpd.read_feather(result.output_path)
    assert output["FEATURE_ID"].is_unique
    assert set(output["SOURCE_FEATURE_ID"].tolist()) == {100}
    assert output.loc[
        output["thlb_fact"] > 0.0
    ].geometry.area.sum() / 10000.0 == pytest.approx(0.01)
    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    run_step = audit_payload["steps"][1]
    assert run_step["spatial_application_mode"] == "fragment_overlay"
    assert run_step["lu_chunk_count"] == 2
    assert run_step["intersecting_exclusion_feature_count"] == 1
    assert (
        audit_payload["reconstructed_timing_summary"]["slowest_steps"][0]["step_id"]
        == "thlb_step_002_ogma"
    )


def test_run_tsr_thlb_netdown_recipe_reconstructed_mode_can_opt_into_stand_binary_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )
    monkeypatch.setattr(tsr_recipes, "_RECONSTRUCTED_FRAGMENT_ROW_THRESHOLD", 2)

    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "OGMA" / "OGMA.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    exclusion = gpd.GeoDataFrame(
        {"rule": ["ogma_a", "ogma_b", "ogma_c"]},
        geometry=[box(0, 0, 6, 10), box(20, 0, 26, 10), box(40, 0, 46, 10)],
        crs="EPSG:3005",
    )
    exclusion.to_file(exclusion_path, driver="GPKG")

    checkpoint1_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint1_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint1 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [100, 200, 300],
            "FOR_MGMT_LAND_BASE_IND": ["Y", "Y", "Y"],
            "BCLCS_LEVEL_2": ["T", "T", "T"],
            "NON_PRODUCTIVE_CD": [None, None, None],
            "BEC_ZONE_CODE": ["SBS", "SBS", "SBS"],
            "PROJ_AGE_1": [80, 80, 80],
            "BASAL_AREA": [20.0, 20.0, 20.0],
            "LIVE_STAND_VOLUME_125": [50.0, 50.0, 50.0],
            "MAP_ID": ["093J034", "093J034", "093J034"],
            "POLYGON_AREA": [0.01, 0.01, 0.01],
            "FEATURE_AREA_SQM": [100.0, 100.0, 100.0],
            "FEATURE_LENGTH_M": [40.0, 40.0, 40.0],
            "GEOMETRY_AREA": [0.01, 0.01, 0.01],
            "Shape_Area": [100.0, 100.0, 100.0],
            "Shape_Length": [40.0, 40.0, 40.0],
        },
        geometry=[
            box(0, 0, 10, 10),
            box(20, 0, 30, 10),
            box(40, 0, 50, 10),
        ],
        crs="EPSG:3005",
    )
    checkpoint1.to_feather(checkpoint1_path)

    checkpoint8_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint8.feather"
    checkpoint8 = gpd.GeoDataFrame(
        {"FEATURE_ID": [1], "thlb_raw": [100.0]},
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3005",
    )
    checkpoint8.to_feather(checkpoint8_path)

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "run"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "ogma",
            "label": "OGMA",
            "recommended_query": "WHSE_LAND_USE_PLANNING.RMP_OGMA_LEGAL_CURRENT_SVW",
            "acquisition_strategy": "wfs_fetch",
            "artifact_path": "data/downloads/bcdc/OGMA/OGMA.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    thlb_recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    thlb_recipe_payload["recipe_contract"]["status"] = "built"
    thlb_recipe_payload["steps"] = [
        {
            "step_id": "thlb_step_001_land_base",
            "order_index": 1,
            "step_kind": "netdown_rule",
            "label": "Timber harvesting land base",
            "normalized_action": "use_land_base",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 24,
        },
        {
            "step_id": "thlb_step_002_ogma",
            "order_index": 2,
            "step_kind": "netdown_rule",
            "label": "OGMA",
            "normalized_action": "exclude",
            "linked_source_entry_ids": ["ogma"],
            "step_status": "ready",
            "page_number": 48,
        },
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            thlb_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    result = tsr_recipes.run_tsr_thlb_netdown_recipe(
        recipe_path=init_result.thlb_netdown_recipe_path,
        execution_mode=tsr_recipes.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
        allow_stand_binary_fallback=True,
    )

    assert result.final_managed_area_ha == pytest.approx(0.0)
    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit_payload["allow_stand_binary_fallback"] is True
    assert audit_payload["stand_binary_fallback_step_count"] == 1
    run_step = audit_payload["steps"][1]
    assert run_step["spatial_application_mode"] == "stand_binary_majority"
    assert run_step["affected_stand_count"] == 3


def test_run_tsr_thlb_netdown_recipe_reconstructed_mode_blocks_failed_exact_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "OGMA" / "OGMA.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    exclusion = gpd.GeoDataFrame(
        {"rule": ["ogma"]},
        geometry=[box(0, 0, 5, 10)],
        crs="EPSG:3005",
    )
    exclusion.to_file(exclusion_path, driver="GPKG")

    checkpoint1_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint1_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint1 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [100],
            "FOR_MGMT_LAND_BASE_IND": ["Y"],
            "BCLCS_LEVEL_2": ["T"],
            "NON_PRODUCTIVE_CD": [None],
            "BEC_ZONE_CODE": ["SBS"],
            "PROJ_AGE_1": [80],
            "BASAL_AREA": [20.0],
            "LIVE_STAND_VOLUME_125": [50.0],
            "MAP_ID": ["093J034"],
            "POLYGON_AREA": [0.01],
            "FEATURE_AREA_SQM": [100.0],
            "FEATURE_LENGTH_M": [40.0],
            "GEOMETRY_AREA": [0.01],
            "Shape_Area": [100.0],
            "Shape_Length": [40.0],
        },
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3005",
    )
    checkpoint1.to_feather(checkpoint1_path)
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(-10, -10, 20, 20)],
        names=["Test LU"],
    )

    checkpoint8_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint8.feather"
    checkpoint8 = gpd.GeoDataFrame(
        {"FEATURE_ID": [1], "thlb_raw": [100.0]},
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3005",
    )
    checkpoint8.to_feather(checkpoint8_path)

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "run"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "ogma",
            "label": "OGMA",
            "recommended_query": "WHSE_LAND_USE_PLANNING.RMP_OGMA_LEGAL_CURRENT_SVW",
            "acquisition_strategy": "wfs_fetch",
            "artifact_path": "data/downloads/bcdc/OGMA/OGMA.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    thlb_recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    thlb_recipe_payload["recipe_contract"]["status"] = "built"
    thlb_recipe_payload["steps"] = [
        {
            "step_id": "thlb_step_001_land_base",
            "order_index": 1,
            "step_kind": "netdown_rule",
            "label": "Timber harvesting land base",
            "normalized_action": "use_land_base",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 24,
        },
        {
            "step_id": "thlb_step_002_ogma",
            "order_index": 2,
            "step_kind": "netdown_rule",
            "label": "OGMA",
            "normalized_action": "exclude",
            "linked_source_entry_ids": ["ogma"],
            "step_status": "ready",
            "page_number": 48,
        },
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            thlb_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    def _raise_overlay(**_kwargs):
        raise RuntimeError("synthetic exact-overlay failure")

    monkeypatch.setattr(
        tsr_recipes, "_fragment_binary_exclusion_step_chunked", _raise_overlay
    )

    result = tsr_recipes.run_tsr_thlb_netdown_recipe(
        recipe_path=init_result.thlb_netdown_recipe_path,
        execution_mode=tsr_recipes.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
    )

    assert result.final_managed_area_ha == pytest.approx(
        result.baseline_managed_area_ha
    )
    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit_payload["blocked_exact_overlay_step_count"] == 1
    assert audit_payload["aspatial_fallback_step_count"] == 0
    run_step = audit_payload["steps"][1]
    assert run_step["run_status"] == "blocked_exact_overlay"
    assert run_step["spatial_application_mode"] == "blocked_exact_overlay"


def test_run_tsr_thlb_reconstructed_diagnostic_slice_can_resume_prefix_output(
    tmp_path: Path,
) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)
    init_result = tsr_catalog.init_tsr_recipe_scaffolds(
        instance_root=instance_root,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
    )

    exclusion_path = (
        instance_root / "data" / "downloads" / "bcdc" / "OGMA" / "OGMA.gpkg"
    )
    exclusion_path.parent.mkdir(parents=True, exist_ok=True)
    exclusion = gpd.GeoDataFrame(
        {"rule": ["ogma"]},
        geometry=[box(0, 0, 5, 10)],
        crs="EPSG:3005",
    )
    exclusion.to_file(exclusion_path, driver="GPKG")

    checkpoint1_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    checkpoint1_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint1 = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [100],
            "FOR_MGMT_LAND_BASE_IND": ["Y"],
            "BCLCS_LEVEL_2": ["T"],
            "NON_PRODUCTIVE_CD": [None],
            "BEC_ZONE_CODE": ["SBS"],
            "PROJ_AGE_1": [80],
            "BASAL_AREA": [20.0],
            "LIVE_STAND_VOLUME_125": [50.0],
            "MAP_ID": ["093J034"],
            "POLYGON_AREA": [0.01],
            "FEATURE_AREA_SQM": [100.0],
            "FEATURE_LENGTH_M": [40.0],
            "GEOMETRY_AREA": [0.01],
            "Shape_Area": [100.0],
            "Shape_Length": [40.0],
        },
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3005",
    )
    checkpoint1.to_feather(checkpoint1_path)
    _write_landscape_unit_layer(
        instance_root,
        geometries=[box(-10, -10, 20, 20)],
        names=["Test LU"],
    )

    checkpoint8_path = instance_root / "data" / "ria_vri_vclr1p_checkpoint8.feather"
    checkpoint8 = gpd.GeoDataFrame(
        {"FEATURE_ID": [1], "thlb_raw": [100.0]},
        geometry=[box(0, 0, 10, 10)],
        crs="EPSG:3005",
    )
    checkpoint8.to_feather(checkpoint8_path)

    source_recipe_payload = tsr_catalog.load_tsr_source_layers_recipe(
        init_result.source_layers_recipe_path
    ).to_dict()
    source_recipe_payload["recipe_contract"]["status"] = "run"
    source_recipe_payload["entries"] = [
        {
            "entry_id": "ogma",
            "label": "OGMA",
            "recommended_query": "WHSE_LAND_USE_PLANNING.RMP_OGMA_LEGAL_CURRENT_SVW",
            "acquisition_strategy": "wfs_fetch",
            "artifact_path": "data/downloads/bcdc/OGMA/OGMA.gpkg",
            "run_status": "fetched",
        }
    ]
    init_result.source_layers_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            source_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    thlb_recipe_payload = tsr_catalog.load_tsr_thlb_netdown_recipe(
        init_result.thlb_netdown_recipe_path
    ).to_dict()
    thlb_recipe_payload["recipe_contract"]["status"] = "built"
    thlb_recipe_payload["steps"] = [
        {
            "step_id": "thlb_step_001_land_base",
            "order_index": 1,
            "step_kind": "netdown_rule",
            "label": "Timber harvesting land base",
            "normalized_action": "use_land_base",
            "linked_source_entry_ids": [],
            "step_status": "ready",
            "page_number": 24,
        },
        {
            "step_id": "thlb_step_002_ogma",
            "order_index": 2,
            "step_kind": "netdown_rule",
            "label": "OGMA",
            "normalized_action": "exclude",
            "linked_source_entry_ids": ["ogma"],
            "step_status": "ready",
            "page_number": 48,
        },
    ]
    init_result.thlb_netdown_recipe_path.write_text(
        tsr_recipes.yaml.safe_dump(
            thlb_recipe_payload, sort_keys=False, allow_unicode=False
        ),
        encoding="utf-8",
    )

    diagnostics_root = instance_root / "runtime" / "logs" / "tsr" / "diagnostics"
    first_result = tsr_recipes.run_tsr_thlb_reconstructed_diagnostic_slice(
        recipe_path=init_result.thlb_netdown_recipe_path,
        output_path=diagnostics_root / "prefix01.feather",
        audit_path=diagnostics_root / "prefix01.audit.json",
        diagnostic_path=diagnostics_root / "prefix01.diag.json",
        start_index=0,
        end_index=1,
    )

    assert first_result.executed_step_ids == ("thlb_step_001_land_base",)
    assert first_result.resumed_from_checkpoint is False

    second_result = tsr_recipes.run_tsr_thlb_reconstructed_diagnostic_slice(
        recipe_path=init_result.thlb_netdown_recipe_path,
        resume_checkpoint_path=first_result.output_path,
        output_path=diagnostics_root / "prefix02.feather",
        audit_path=diagnostics_root / "prefix02.audit.json",
        diagnostic_path=diagnostics_root / "prefix02.diag.json",
        start_index=1,
        end_index=2,
    )

    assert second_result.executed_step_ids == ("thlb_step_002_ogma",)
    assert second_result.resumed_from_checkpoint is True
    assert second_result.final_managed_area_ha == pytest.approx(0.005)
    diagnostic_payload = json.loads(
        second_result.diagnostic_path.read_text(encoding="utf-8")
    )
    assert diagnostic_payload["baseline_signal"] == "resumed_reconstructed_checkpoint"
