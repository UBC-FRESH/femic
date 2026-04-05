from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from femic import tsr_catalog
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
    artifact_path.write_text("placeholder", encoding="utf-8")
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
    assert netdown_step["normalized_action"] == "exclude"
    assert netdown_step["linked_source_entry_ids"] == ["mdwr"]


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
    assert "Input:AFLB =" in status_text
    assert "AFLB:THLB =" in status_text
    assert "AFLB lock state: `unlocked`" in status_text
    assert "## Sequential THLB Steps" in status_text
    assert "Linked source layers:" in status_text
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
