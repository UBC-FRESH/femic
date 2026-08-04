"""Tests for the Coordinator-facing model-build records."""

from __future__ import annotations

import json
from pathlib import Path

from femic.model_build import ModelBuildSpec, WorkspaceManifest


def _spec(**overrides: object) -> ModelBuildSpec:
    values: dict[str, object] = {
        "model_id": "teaching-model",
        "source_root": Path("inputs"),
        "output_root": Path("outputs/teaching-model"),
        "requested_sections": ("landscape", "areas", "yields"),
        "outputs": ("woodstock",),
        "horizon_years": 80,
        "period_length_years": 10,
    }
    values.update(overrides)
    return ModelBuildSpec(**values)


def test_model_build_spec_round_trips_and_hashes_canonically() -> None:
    spec = _spec()
    restored = ModelBuildSpec.from_dict(spec.to_dict())

    assert restored == spec
    assert spec.validate() == ()
    assert spec.sha256() == restored.sha256()
    assert len(spec.sha256()) == 64


def test_model_build_spec_rejects_invalid_approval_and_periods() -> None:
    spec = _spec(approval_mode="apply", horizon_years=10, period_length_years=20)
    assert any(
        "period_length_years must not exceed" in error for error in spec.validate()
    )

    invalid = _spec(approval_mode="unsafe")
    assert any("approval_mode must be one of" in error for error in invalid.validate())


def test_model_build_spec_rejects_duplicate_sections() -> None:
    spec = _spec(requested_sections=("landscape", "landscape"))
    assert spec.validate() == ("requested_sections must not contain duplicates.",)


def test_workspace_manifest_serializes_sorted_evidence(tmp_path: Path) -> None:
    spec = _spec()
    manifest = WorkspaceManifest(
        workflow_id="build-teaching-model",
        workspace_root=tmp_path,
        spec_sha256=spec.sha256(),
        input_hashes={"z-input": "z", "a-input": "a"},
        artifacts={"model": "outputs/model"},
        verification_tier=3,
        tool_versions={"ws3": "1.1.0a4", "femic": "0.2.0a1"},
    )
    path = tmp_path / "manifest.json"

    assert manifest.validate() == ()
    manifest.write(path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert list(payload["input_hashes"]) == ["a-input", "z-input"]
    assert list(payload["tool_versions"]) == ["femic", "ws3"]
    assert payload["spec_sha256"] == spec.sha256()


def test_workspace_manifest_rejects_invalid_digest_and_tier(tmp_path: Path) -> None:
    manifest = WorkspaceManifest(
        workflow_id="build-model",
        workspace_root=tmp_path,
        spec_sha256="not-a-digest",
        verification_tier=6,
    )
    errors = manifest.validate()

    assert "spec_sha256 must be a lowercase SHA-256 digest." in errors
    assert "verification_tier must be between 0 and 5." in errors
