from __future__ import annotations

import json
from pathlib import Path

import pytest

from femic import tsr_catalog


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
