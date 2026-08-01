"""Typed request and workspace records for Coordinator-driven model builds."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MODEL_BUILD_SCHEMA_VERSION = "1.0"
WORKSPACE_MANIFEST_SCHEMA_VERSION = "1.0"
APPROVAL_MODES = frozenset({"propose", "dry_run", "apply", "run"})
MANIFEST_STATUSES = frozenset({"planned", "running", "succeeded", "failed"})
_MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _non_empty_strings(values: tuple[str, ...], field_name: str) -> list[str]:
    errors: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field_name}[{index}] must be a non-empty string.")
    if len(values) != len(set(values)):
        errors.append(f"{field_name} must not contain duplicates.")
    return errors


@dataclass(frozen=True)
class ModelBuildSpec:
    """Serializable request for constructing one model instance."""

    model_id: str
    source_root: Path
    output_root: Path
    target_engine: str = "ws3"
    requested_sections: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    approval_mode: str = "propose"
    horizon_years: int | None = None
    period_length_years: int | None = None
    schema_version: str = MODEL_BUILD_SCHEMA_VERSION

    def validate(self) -> tuple[str, ...]:
        """Return validation diagnostics without touching the filesystem."""
        errors: list[str] = []
        if self.schema_version != MODEL_BUILD_SCHEMA_VERSION:
            errors.append(
                "schema_version must be "
                f"{MODEL_BUILD_SCHEMA_VERSION!r} (got {self.schema_version!r})."
            )
        if not _MODEL_ID_PATTERN.fullmatch(self.model_id):
            errors.append(
                "model_id must start with a letter or number and contain only "
                "letters, numbers, '.', '_' or '-'."
            )
        if not str(self.source_root).strip():
            errors.append("source_root must be non-empty.")
        if not str(self.output_root).strip():
            errors.append("output_root must be non-empty.")
        if not isinstance(self.target_engine, str) or not self.target_engine.strip():
            errors.append("target_engine must be a non-empty string.")
        if self.approval_mode not in APPROVAL_MODES:
            errors.append(
                f"approval_mode must be one of {sorted(APPROVAL_MODES)} "
                f"(got {self.approval_mode!r})."
            )
        errors.extend(_non_empty_strings(self.requested_sections, "requested_sections"))
        errors.extend(_non_empty_strings(self.outputs, "outputs"))
        if self.horizon_years is not None and self.horizon_years <= 0:
            errors.append("horizon_years must be positive when provided.")
        if self.period_length_years is not None and self.period_length_years <= 0:
            errors.append("period_length_years must be positive when provided.")
        if (
            self.horizon_years is not None
            and self.period_length_years is not None
            and self.period_length_years > self.horizon_years
        ):
            errors.append("period_length_years must not exceed horizon_years.")
        return tuple(errors)

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-compatible request representation."""
        return {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "source_root": str(self.source_root),
            "output_root": str(self.output_root),
            "target_engine": self.target_engine,
            "requested_sections": list(self.requested_sections),
            "outputs": list(self.outputs),
            "approval_mode": self.approval_mode,
            "horizon_years": self.horizon_years,
            "period_length_years": self.period_length_years,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ModelBuildSpec:
        """Construct a request from a decoded JSON/YAML mapping."""
        if not isinstance(payload, Mapping):
            raise TypeError("ModelBuildSpec payload must be a mapping.")
        sections = payload.get("requested_sections", ())
        outputs = payload.get("outputs", ())
        if not isinstance(sections, (list, tuple)):
            raise TypeError("requested_sections must be a list.")
        if not isinstance(outputs, (list, tuple)):
            raise TypeError("outputs must be a list.")
        return cls(
            schema_version=str(
                payload.get("schema_version", MODEL_BUILD_SCHEMA_VERSION)
            ),
            model_id=str(payload.get("model_id", "")),
            source_root=Path(str(payload.get("source_root", ""))),
            output_root=Path(str(payload.get("output_root", ""))),
            target_engine=str(payload.get("target_engine", "ws3")),
            requested_sections=tuple(str(value) for value in sections),
            outputs=tuple(str(value) for value in outputs),
            approval_mode=str(payload.get("approval_mode", "propose")),
            horizon_years=_optional_int(payload.get("horizon_years"), "horizon_years"),
            period_length_years=_optional_int(
                payload.get("period_length_years"), "period_length_years"
            ),
        )

    def canonical_json(self) -> str:
        """Return stable JSON used for reproducibility hashes."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        """Return the canonical SHA-256 digest for this request."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WorkspaceManifest:
    """Evidence index for one model-build workspace."""

    workflow_id: str
    workspace_root: Path
    spec_sha256: str
    input_hashes: Mapping[str, str] = field(default_factory=dict)
    artifacts: Mapping[str, str] = field(default_factory=dict)
    verification_tier: int = 0
    status: str = "planned"
    tool_versions: Mapping[str, str] = field(default_factory=dict)
    schema_version: str = WORKSPACE_MANIFEST_SCHEMA_VERSION

    def validate(self) -> tuple[str, ...]:
        """Return manifest diagnostics without reading artifact paths."""
        errors: list[str] = []
        if self.schema_version != WORKSPACE_MANIFEST_SCHEMA_VERSION:
            errors.append(
                "schema_version must be "
                f"{WORKSPACE_MANIFEST_SCHEMA_VERSION!r} (got {self.schema_version!r})."
            )
        if not self.workflow_id.strip():
            errors.append("workflow_id must be non-empty.")
        if not str(self.workspace_root).strip():
            errors.append("workspace_root must be non-empty.")
        if not re.fullmatch(r"[0-9a-f]{64}", self.spec_sha256):
            errors.append("spec_sha256 must be a lowercase SHA-256 digest.")
        if self.verification_tier not in range(6):
            errors.append("verification_tier must be between 0 and 5.")
        if self.status not in MANIFEST_STATUSES:
            errors.append(
                f"status must be one of {sorted(MANIFEST_STATUSES)} "
                f"(got {self.status!r})."
            )
        errors.extend(_mapping_key_errors(self.input_hashes, "input_hashes"))
        errors.extend(_mapping_key_errors(self.artifacts, "artifacts"))
        errors.extend(_mapping_key_errors(self.tool_versions, "tool_versions"))
        return tuple(errors)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible manifest representation."""
        return {
            "schema_version": self.schema_version,
            "workflow_id": self.workflow_id,
            "workspace_root": str(self.workspace_root),
            "spec_sha256": self.spec_sha256,
            "input_hashes": dict(sorted(self.input_hashes.items())),
            "artifacts": dict(sorted(self.artifacts.items())),
            "verification_tier": self.verification_tier,
            "status": self.status,
            "tool_versions": dict(sorted(self.tool_versions.items())),
        }

    def write(self, path: Path) -> None:
        """Write the manifest as stable, human-readable JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")


def _optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer or null.")
    return value


def _mapping_key_errors(values: Mapping[str, str], field_name: str) -> list[str]:
    errors: list[str] = []
    for key, value in values.items():
        if not isinstance(key, str) or not key.strip():
            errors.append(f"{field_name} keys must be non-empty strings.")
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field_name}[{key!r}] must be a non-empty string.")
    return errors
