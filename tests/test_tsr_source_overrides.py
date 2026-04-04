from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from femic.tsr_catalog import source_overrides
from femic.tsr_catalog.source_overrides import (
    TsrSourceLayerOverridesError,
    build_tsr_source_layer_override_report,
    init_tsr_source_layer_overrides,
    load_tsr_source_layer_overrides,
)


def _write_overlay(path: Path) -> None:
    payload = {
        "schema_version": 1,
        "tsa": {
            "tsa_id": "tsa_29",
            "tsa_code": "29",
            "tsa_name": "Williams Lake",
        },
        "canonical_summary": {
            "candidate_fact_count": 1,
            "document_count": 1,
            "fact_family_counts": {"source_layer_candidate": 1},
            "candidate_facts_path": "metadata/tsr/tsa_candidate_facts.json",
            "documents_path": "metadata/tsr/tsa_documents.json",
            "registry_path": "metadata/tsr/tsa_registry.json",
        },
        "adopted": {
            "source_layers": [],
            "au_definitions": [],
            "thlb_references": [],
            "tipsy_inputs": [],
            "notes": [],
        },
        "bcdc_acquisition_review": {
            "attempts": [
                {
                    "query": "REG_LAND_AND_NATURAL_RESOURCE.L_MULE_DEER",
                    "acquisition_outcome": "no_catalog_match",
                    "matched_by": "",
                    "top_match_title": "",
                    "dataset_page_url": "",
                    "suggested_fetch_strategy": "",
                    "notes": "No catalogue matches found for the supplied query.",
                },
                {
                    "query": "WHSE_HUMAN_CULTURAL_ECONOMIC.FNIRS",
                    "acquisition_outcome": "failed",
                    "matched_by": "object_name_suffix:WHSE_HUMAN_CULTURAL_ECONOMIC.FNIRS",
                    "top_match_title": "Profiles of Indigenous Peoples (PIP): Consultation Areas - Public Map Service",
                    "dataset_page_url": "https://catalogue.data.gov.bc.ca/dataset/pip-consultation-areas-public-map-service",
                    "suggested_fetch_strategy": "wfs_getfeature_bbox",
                    "notes": "Resolver guessed a public lead but later automation failed. | Needs human review.",
                },
            ]
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_init_tsr_source_layer_overrides_writes_template(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "instance"
    overlay_path = instance_root / "config" / "tsr" / "overlay.yaml"
    overrides_path = instance_root / "config" / "tsr" / "source_layer_overrides.yaml"
    _write_overlay(overlay_path)
    monkeypatch.setattr(
        source_overrides,
        "suggest_bcdc_replacement_family",
        lambda query, limit=3: (
            (
                source_overrides.BcdcReplacementFamilyCandidate(
                    title="Mule Deer Winter Range Topographic Buffers - Cariboo Region",
                    dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/mule-deer-winter-range-topographic-buffers-cariboo-region",
                    object_names=(
                        "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP",
                    ),
                    matched_query="MULE_DEER",
                    rationale="Broad mule-deer search surfaced a small public wildlife family that may replace a stale TSR token.",
                ),
            )
            if "MULE_DEER" in query
            else ()
        ),
    )

    result = init_tsr_source_layer_overrides(
        instance_root=instance_root,
        overlay_path=overlay_path,
        overrides_path=overrides_path,
    )

    assert result.entry_count == 2
    payload = yaml.safe_load(overrides_path.read_text(encoding="utf-8"))
    assert payload["tsa"]["tsa_id"] == "tsa_29"
    assert payload["source_overlay_path"] == "config/tsr/overlay.yaml"
    assert payload["entries"][0]["query"] == "REG_LAND_AND_NATURAL_RESOURCE.L_MULE_DEER"
    assert payload["entries"][0]["override_kind"] == ""
    assert payload["entries"][0]["replacement_family_candidates"]
    assert (
        payload["entries"][0]["replacement_family_candidates"][0]["matched_query"]
        == "MULE_DEER"
    )
    assert payload["entries"][1]["current_public_notes"] == [
        "Resolver guessed a public lead but later automation failed.",
        "Needs human review.",
    ]


def test_load_tsr_source_layer_overrides_rejects_unknown_kind(tmp_path: Path) -> None:
    path = tmp_path / "source_layer_overrides.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "tsa": {
                    "tsa_id": "tsa_29",
                    "tsa_code": "29",
                    "tsa_name": "Williams Lake",
                },
                "source_overlay_path": "config/tsr/overlay.yaml",
                "entries": [
                    {
                        "query": "REG_LAND_AND_NATURAL_RESOURCE.L_MULE_DEER",
                        "current_public_status": "no_catalog_match",
                        "override_kind": "magic_portal",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(TsrSourceLayerOverridesError):
        load_tsr_source_layer_overrides(path)


def test_build_tsr_source_layer_override_report_summarizes_resolved_and_pending(
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "instance"
    overlay_path = instance_root / "config" / "tsr" / "overlay.yaml"
    overrides_path = instance_root / "config" / "tsr" / "source_layer_overrides.yaml"
    _write_overlay(overlay_path)
    overrides_path.parent.mkdir(parents=True, exist_ok=True)
    overrides_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "tsa": {
                    "tsa_id": "tsa_29",
                    "tsa_code": "29",
                    "tsa_name": "Williams Lake",
                },
                "source_overlay_path": "config/tsr/overlay.yaml",
                "entries": [
                    {
                        "query": "REG_LAND_AND_NATURAL_RESOURCE.L_MULE_DEER",
                        "current_public_status": "no_catalog_match",
                        "replacement_family_candidates": [
                            {
                                "title": "Mule Deer Winter Range Topographic Buffers - Cariboo Region",
                                "dataset_page_url": "https://catalogue.data.gov.bc.ca/dataset/mule-deer-winter-range-topographic-buffers-cariboo-region",
                                "object_names": [
                                    "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP"
                                ],
                                "matched_query": "MULE_DEER",
                                "rationale": "Broad mule-deer search surfaced a small public wildlife family that may replace a stale TSR token.",
                            }
                        ],
                        "override_kind": "replacement_layer",
                        "override_value": "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP",
                        "notes": "Use reviewed replacement family candidate for now.",
                    },
                    {
                        "query": "WHSE_HUMAN_CULTURAL_ECONOMIC.FNIRS",
                        "current_public_status": "failed",
                        "override_kind": "",
                        "override_value": "",
                        "notes": "",
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    report = build_tsr_source_layer_override_report(
        overlay_path=overlay_path,
        overrides_path=overrides_path,
    )

    assert report.total_entries == 2
    assert report.resolved_entries == 1
    assert report.pending_entries == 1
    assert report.entries_with_suggestions == 1
    assert report.total_suggestion_candidates == 1
    assert report.override_kind_counts == {"replacement_layer": 1}
    assert report.unresolved_overlay_queries == ("WHSE_HUMAN_CULTURAL_ECONOMIC.FNIRS",)


def test_load_tsr_source_layer_overrides_preserves_replacement_family_candidates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "source_layer_overrides.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "tsa": {
                    "tsa_id": "tsa_29",
                    "tsa_code": "29",
                    "tsa_name": "Williams Lake",
                },
                "source_overlay_path": "config/tsr/overlay.yaml",
                "entries": [
                    {
                        "query": "REG_LAND_AND_NATURAL_RESOURCE.L_MULE_DEER_WR_CAR_POLY",
                        "current_public_status": "no_catalog_match",
                        "matched_by": "",
                        "top_match_title": "",
                        "dataset_page_url": "",
                        "suggested_fetch_strategy": "",
                        "current_public_notes": [],
                        "replacement_family_candidates": [
                            {
                                "title": "Mule Deer Winter Range Topographic Buffers - Cariboo Region",
                                "dataset_page_url": "https://catalogue.data.gov.bc.ca/dataset/mule-deer-winter-range-topographic-buffers-cariboo-region",
                                "object_names": [
                                    "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP"
                                ],
                                "matched_query": "MULE_DEER",
                                "rationale": "Broad mule-deer search surfaced a small public wildlife family that may replace a stale TSR token.",
                            }
                        ],
                        "override_kind": "",
                        "override_value": "",
                        "notes": "",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    record = load_tsr_source_layer_overrides(path)

    assert len(record.entries) == 1
    assert len(record.entries[0].replacement_family_candidates) == 1
    candidate = record.entries[0].replacement_family_candidates[0]
    assert candidate.matched_query == "MULE_DEER"
    assert candidate.object_names == (
        "REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP",
    )
