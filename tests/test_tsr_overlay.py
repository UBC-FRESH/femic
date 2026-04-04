from __future__ import annotations

import json
from pathlib import Path

from femic import tsr_catalog
import yaml


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
            {"tsa_id": "tsa_29"},
            {"tsa_id": "tsa_29"},
        ],
    }
    path = tmp_path / "metadata" / "tsr" / "tsa_documents.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_candidate_facts(tmp_path: Path) -> Path:
    payload = {
        "generated_utc": "2026-04-04T00:00:00+00:00",
        "fact_count": 4,
        "facts": [
            {"tsa_id": "tsa_29", "fact_family": "source_layer_candidate"},
            {"tsa_id": "tsa_29", "fact_family": "source_layer_candidate"},
            {"tsa_id": "tsa_29", "fact_family": "thlb_reference"},
            {"tsa_id": "tsa_29", "fact_family": "tipsy_input_candidate"},
        ],
    }
    path = tmp_path / "metadata" / "tsr" / "tsa_candidate_facts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_init_tsr_overlay_writes_reviewed_overlay_yaml(tmp_path: Path) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    overlay_path = instance_root / "config" / "tsr" / "overlay.yaml"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)

    result = tsr_catalog.init_tsr_overlay(
        instance_root=instance_root,
        overlay_path=overlay_path,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
    )

    assert result.overlay_path == overlay_path.resolve()
    assert result.tsa.tsa_id == "tsa_29"
    assert result.canonical_summary.candidate_fact_count == 4
    overlay = tsr_catalog.load_tsr_overlay(overlay_path)
    assert overlay.tsa.tsa_name == "Williams Lake"
    assert overlay.adopted["source_layers"] == []
    assert overlay.canonical_summary.registry_path == "metadata/tsr/tsa_registry.json"


def test_build_tsr_overlay_report_counts_adopted_sections(tmp_path: Path) -> None:
    source_root = tmp_path
    instance_root = tmp_path / "external" / "femic-tsa29-instance"
    overlay_path = instance_root / "config" / "tsr" / "overlay.yaml"
    registry_path = _write_registry(tmp_path)
    documents_path = _write_documents(tmp_path)
    candidate_facts_path = _write_candidate_facts(tmp_path)

    tsr_catalog.init_tsr_overlay(
        instance_root=instance_root,
        overlay_path=overlay_path,
        tsa="29",
        registry_path=registry_path,
        documents_path=documents_path,
        candidate_facts_path=candidate_facts_path,
        source_root=source_root,
    )
    payload = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
    payload["adopted"]["source_layers"] = [
        {
            "value": "WHSE_FOREST_VEGETATION.F_OWN",
            "provenance_id": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf#page=12",
        }
    ]
    overlay_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )

    report = tsr_catalog.build_tsr_overlay_report(overlay_path=overlay_path)

    assert report.tsa.tsa_code == "29"
    assert report.canonical_summary.candidate_fact_count == 4
    assert report.adopted_counts["source_layers"] == 1
    assert report.adopted_counts["thlb_references"] == 0
