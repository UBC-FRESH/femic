"""Versioned hydrologic response and flood-risk bundles.

P114.8 packages response surfaces, surrogate state, frequency fits, flood-risk
rows, and provenance into a pinned consumer bundle for WS4/FHOPS.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from femic.hydrology.flood import (
    HYDROLOGY_FLOOD_FREQUENCY_SCHEMA_VERSION,
    HYDROLOGY_FLOOD_RESPONSE_SCHEMA_VERSION,
)
from femic.hydrology.screening import HYDROLOGY_SCREENING_SCHEMA_VERSION
from femic.hydrology.surrogate import HYDROLOGY_SURROGATE_MODEL_SCHEMA_VERSION

HYDROLOGY_RESPONSE_SCHEMA_VERSION = "femic.hydrology.response.v1"
HYDROLOGY_FLOOD_RISK_SCHEMA_VERSION = "femic.hydrology.flood_risk.v1"
HYDROLOGY_RESPONSE_PLAN_SCHEMA_VERSION = "femic.hydrology.response_plan.v1"
HYDROLOGY_RESPONSE_MANIFEST_NAME = "manifest.json"
HYDROLOGY_RESPONSE_ARTIFACTS_DIR = "artifacts"
HYDROLOGY_RESPONSE_PROVENANCE_DIR = "provenance"
HYDROLOGY_RESPONSE_REQUIRED_ROLES: tuple[str, ...] = (
    "response_surface",
    "flood_risk",
    "domain",
    "disturbance_ledger",
)
HYDROLOGY_RESPONSE_ARTIFACT_ROLES: tuple[str, ...] = (
    "response_surface",
    "surrogate_model",
    "surrogate_validation",
    "frequency_fit",
    "frequency_pairing",
    "flood_risk",
    "tier0_screening",
    "domain",
    "disturbance_ledger",
    "benchmark_check",
)
ROLE_SCHEMAS: dict[str, str] = {
    "response_surface": HYDROLOGY_FLOOD_RESPONSE_SCHEMA_VERSION,
    "surrogate_model": HYDROLOGY_SURROGATE_MODEL_SCHEMA_VERSION,
    "frequency_fit": HYDROLOGY_FLOOD_FREQUENCY_SCHEMA_VERSION,
    "flood_risk": HYDROLOGY_FLOOD_RISK_SCHEMA_VERSION,
    "tier0_screening": HYDROLOGY_SCREENING_SCHEMA_VERSION,
    "domain": "femic.hydrology.domain.v1",
    "disturbance_ledger": "femic.hydrology.disturbance.v1",
}


class HydrologyResponseError(RuntimeError):
    """Raised when a response plan, flood-risk table, or bundle is invalid."""


@dataclass(frozen=True)
class FloodRiskRow:
    """One receptor/return-period flood-risk record."""

    receptor_id: str
    watershed_id: str
    return_period: float
    baseline_peak_flow_m3s: float
    scenario_peak_flow_m3s: float
    ratio: float
    exceedance_probability: float | None = None
    expected_annual_damage: float | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the row as a JSON-serializable mapping."""

        return {
            "receptor_id": self.receptor_id,
            "watershed_id": self.watershed_id,
            "return_period": self.return_period,
            "baseline_peak_flow_m3s": self.baseline_peak_flow_m3s,
            "scenario_peak_flow_m3s": self.scenario_peak_flow_m3s,
            "ratio": self.ratio,
            "exceedance_probability": self.exceedance_probability,
            "expected_annual_damage": self.expected_annual_damage,
        }


@dataclass(frozen=True)
class FloodRiskTable:
    """Versioned receptor-level flood-risk table."""

    table_id: str
    generated_utc: str
    source_surface_id: str
    baseline_name: str
    rows: tuple[FloodRiskRow, ...]
    caveats: tuple[str, ...] = ()
    schema_version: str = HYDROLOGY_FLOOD_RISK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.table_id.strip():
            raise HydrologyResponseError("Flood-risk table ID must be non-empty.")
        if not self.source_surface_id.strip():
            raise HydrologyResponseError("Flood-risk source surface ID is required.")
        if not self.rows:
            raise HydrologyResponseError("Flood-risk table must contain rows.")
        seen: set[tuple[str, float]] = set()
        for row in self.rows:
            if not row.receptor_id.strip() or not row.watershed_id.strip():
                raise HydrologyResponseError(
                    "Flood-risk receptor/watershed IDs are required."
                )
            if row.return_period <= 1 or not math.isfinite(row.return_period):
                raise HydrologyResponseError("Flood-risk return periods must be > 1.")
            if (
                row.baseline_peak_flow_m3s <= 0
                or row.scenario_peak_flow_m3s <= 0
                or not math.isfinite(row.baseline_peak_flow_m3s)
                or not math.isfinite(row.scenario_peak_flow_m3s)
            ):
                raise HydrologyResponseError(
                    "Flood-risk flows must be positive and finite."
                )
            expected_ratio = row.scenario_peak_flow_m3s / row.baseline_peak_flow_m3s
            if not math.isclose(row.ratio, expected_ratio, rel_tol=1e-6, abs_tol=1e-9):
                raise HydrologyResponseError(
                    "Flood-risk ratio must equal scenario/baseline flow."
                )
            if row.exceedance_probability is not None and not (
                0 <= row.exceedance_probability <= 1
            ):
                raise HydrologyResponseError(
                    "Exceedance probability must be in [0, 1]."
                )
            if (
                row.expected_annual_damage is not None
                and row.expected_annual_damage < 0
            ):
                raise HydrologyResponseError(
                    "Expected annual damage cannot be negative."
                )
            key = (row.receptor_id, row.return_period)
            if key in seen:
                raise HydrologyResponseError(
                    f"Duplicate flood-risk row for {key[0]}/{key[1]}."
                )
            seen.add(key)

    def to_dict(self) -> dict[str, object]:
        """Return the table as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "table_id": self.table_id,
            "generated_utc": self.generated_utc,
            "source_surface_id": self.source_surface_id,
            "baseline_name": self.baseline_name,
            "summary": {"row_count": len(self.rows)},
            "rows": [row.to_dict() for row in self.rows],
            "caveats": list(self.caveats),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> FloodRiskTable:
        """Load a flood-risk table from a mapping."""

        rows = tuple(
            _risk_row_from_payload(item, index=index)
            for index, item in enumerate(
                _required_list(payload, "rows", context="flood-risk table"),
                start=1,
            )
        )
        table = cls(
            table_id=_required_str(payload, "table_id", context="flood-risk table"),
            generated_utc=_optional_str(payload.get("generated_utc")) or "",
            source_surface_id=_required_str(
                payload,
                "source_surface_id",
                context="flood-risk table",
            ),
            baseline_name=_required_str(
                payload,
                "baseline_name",
                context="flood-risk table",
            ),
            rows=rows,
            caveats=_optional_str_list(payload.get("caveats"), context="caveats"),
            schema_version=_optional_str(payload.get("schema_version"))
            or HYDROLOGY_FLOOD_RISK_SCHEMA_VERSION,
        )
        summary = payload.get("summary")
        if isinstance(summary, Mapping):
            row_count = summary.get("row_count")
            if row_count is not None:
                try:
                    parsed_count = _coerce_int(row_count)
                except (TypeError, ValueError) as exc:
                    raise HydrologyResponseError(
                        "Flood-risk summary row count must be an integer."
                    ) from exc
                if parsed_count != len(table.rows):
                    raise HydrologyResponseError(
                        "Flood-risk summary row count does not match the rows."
                    )
        return table


@dataclass(frozen=True)
class ResponseArtifactSpec:
    """One planned bundle artifact."""

    role: str
    path: str
    schema_version: str | None = None
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return the artifact spec as a JSON-serializable mapping."""

        return {
            "role": self.role,
            "path": self.path,
            "schema_version": self.schema_version,
            "description": self.description,
        }


@dataclass(frozen=True)
class HydrologyResponsePlan:
    """Reproducible plan for one response bundle."""

    bundle_version: str
    domain_id: str
    ledger_id: str
    response_surface_id: str
    artifacts: tuple[ResponseArtifactSpec, ...]
    applicability_domain: dict[str, object] = field(default_factory=dict)
    uncertainty: dict[str, object] = field(default_factory=dict)
    caveats: tuple[str, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)
    schema_version: str = HYDROLOGY_RESPONSE_PLAN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the plan as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "bundle_version": self.bundle_version,
            "domain_id": self.domain_id,
            "ledger_id": self.ledger_id,
            "response_surface_id": self.response_surface_id,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "applicability_domain": self.applicability_domain,
            "uncertainty": self.uncertainty,
            "caveats": list(self.caveats),
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class HydrologyResponseArtifact:
    """One materialized response bundle artifact."""

    artifact_id: str
    role: str
    relative_path: str
    schema_version: str | None
    media_type: str
    size_bytes: int
    sha256: str
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return the artifact as a JSON-serializable mapping."""

        return {
            "artifact_id": self.artifact_id,
            "role": self.role,
            "relative_path": self.relative_path,
            "schema_version": self.schema_version,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "description": self.description,
        }


@dataclass(frozen=True)
class HydrologyResponseManifest:
    """Consumer-facing hydrologic response bundle manifest."""

    bundle_id: str
    bundle_name: str
    bundle_version: str
    generated_utc: str
    domain_id: str
    ledger_id: str
    response_surface_id: str
    artifacts: tuple[HydrologyResponseArtifact, ...]
    applicability_domain: dict[str, object] = field(default_factory=dict)
    uncertainty: dict[str, object] = field(default_factory=dict)
    response_surface: dict[str, object] = field(default_factory=dict)
    flood_risk: dict[str, object] = field(default_factory=dict)
    consumer_contract: dict[str, object] = field(default_factory=dict)
    caveats: tuple[str, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)
    schema_version: str = HYDROLOGY_RESPONSE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the manifest as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "bundle_name": self.bundle_name,
            "bundle_version": self.bundle_version,
            "generated_utc": self.generated_utc,
            "domain_id": self.domain_id,
            "ledger_id": self.ledger_id,
            "response_surface_id": self.response_surface_id,
            "summary": {"artifact_count": len(self.artifacts)},
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "applicability_domain": self.applicability_domain,
            "uncertainty": self.uncertainty,
            "response_surface": self.response_surface,
            "flood_risk": self.flood_risk,
            "consumer_contract": self.consumer_contract,
            "caveats": list(self.caveats),
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class HydrologyResponseBuildResult:
    """Result of a successful response bundle build."""

    bundle_dir: Path
    manifest_path: Path
    manifest: HydrologyResponseManifest

    def to_dict(self) -> dict[str, object]:
        """Return the build result as a JSON-serializable mapping."""

        return {
            "bundle_dir": str(self.bundle_dir),
            "manifest_path": str(self.manifest_path),
            "manifest": self.manifest.to_dict(),
        }


@dataclass(frozen=True)
class HydrologyResponseArtifactAudit:
    """Local file audit for one response artifact."""

    artifact_id: str
    role: str
    relative_path: str
    exists: bool
    size_bytes: int | None
    expected_size_bytes: int
    checksum_ok: bool | None
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the artifact audit as a JSON-serializable mapping."""

        return {
            "artifact_id": self.artifact_id,
            "role": self.role,
            "relative_path": self.relative_path,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "expected_size_bytes": self.expected_size_bytes,
            "checksum_ok": self.checksum_ok,
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class HydrologyResponseAudit:
    """Validation and local-file audit for a response bundle."""

    bundle_id: str
    bundle_dir: Path
    manifest_path: Path
    is_valid: bool
    is_complete: bool
    checked_utc: str
    artifacts: tuple[HydrologyResponseArtifactAudit, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the audit as a JSON-serializable mapping."""

        return {
            "bundle_id": self.bundle_id,
            "bundle_dir": str(self.bundle_dir),
            "manifest_path": str(self.manifest_path),
            "is_valid": self.is_valid,
            "is_complete": self.is_complete,
            "checked_utc": self.checked_utc,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def build_flood_risk_table(
    rows: Sequence[FloodRiskRow],
    *,
    source_surface_id: str,
    baseline_name: str,
    generated_utc: str | None = None,
) -> FloodRiskTable:
    """Build a deterministic flood-risk table."""

    material = {
        "source_surface_id": source_surface_id,
        "baseline_name": baseline_name,
        "rows": [row.to_dict() for row in rows],
    }
    digest = hashlib.sha256(_canonical_json_bytes(material)).hexdigest()
    return FloodRiskTable(
        table_id=f"hydro-risk-{digest[:16]}",
        generated_utc=generated_utc or _now(),
        source_surface_id=source_surface_id,
        baseline_name=baseline_name,
        rows=tuple(rows),
    )


def write_flood_risk_table(table: FloodRiskTable, path: Path) -> Path:
    """Write a flood-risk table as JSON."""

    return _write_json(table.to_dict(), path)


def read_flood_risk_table(path: Path) -> FloodRiskTable:
    """Read and validate a flood-risk table."""

    payload = _read_json_object(path, context="flood-risk table")
    schema = _optional_str(payload.get("schema_version"))
    if schema != HYDROLOGY_FLOOD_RISK_SCHEMA_VERSION:
        raise HydrologyResponseError(
            f"Unsupported flood-risk schema {schema!r}; expected "
            f"{HYDROLOGY_FLOOD_RISK_SCHEMA_VERSION!r}."
        )
    return FloodRiskTable.from_dict(payload)


def validate_hydrology_response_plan(
    plan: HydrologyResponsePlan,
) -> tuple[str, ...]:
    """Validate a response-bundle plan."""

    errors: list[str] = []
    if plan.schema_version != HYDROLOGY_RESPONSE_PLAN_SCHEMA_VERSION:
        errors.append(f"Unsupported response plan schema {plan.schema_version!r}.")
    for name, value in (
        ("bundle_version", plan.bundle_version),
        ("domain_id", plan.domain_id),
        ("ledger_id", plan.ledger_id),
        ("response_surface_id", plan.response_surface_id),
    ):
        if not value.strip():
            errors.append(f"{name} must be non-empty.")
    if not plan.artifacts:
        errors.append("Plan must contain at least one artifact.")
    roles: set[str] = set()
    for artifact in plan.artifacts:
        if artifact.role not in HYDROLOGY_RESPONSE_ARTIFACT_ROLES:
            errors.append(f"Unsupported artifact role {artifact.role!r}.")
        if artifact.role in roles:
            errors.append(f"Duplicate artifact role {artifact.role!r}.")
        roles.add(artifact.role)
        if not artifact.path.strip():
            errors.append(f"Artifact {artifact.role!r} has no path.")
        else:
            artifact_path = Path(artifact.path)
            if artifact_path.is_absolute():
                errors.append(
                    f"Artifact {artifact.role!r} path must be relative to the plan."
                )
            if ".." in artifact_path.parts:
                errors.append(
                    f"Artifact {artifact.role!r} path must not traverse parent directories."
                )
        expected_schema = ROLE_SCHEMAS.get(artifact.role)
        if expected_schema is not None:
            if artifact.schema_version is None:
                errors.append(f"Artifact {artifact.role!r} must declare its schema.")
            elif artifact.schema_version != expected_schema:
                errors.append(
                    f"Artifact {artifact.role!r} schema {artifact.schema_version!r} "
                    f"does not match {expected_schema!r}."
                )
    missing = [role for role in HYDROLOGY_RESPONSE_REQUIRED_ROLES if role not in roles]
    if missing:
        errors.append(
            "Plan is missing required artifact roles: " + ", ".join(missing) + "."
        )
    if not plan.artifacts:
        errors.append("Plan must include a response surface.")
    return tuple(errors)


def write_hydrology_response_plan(
    plan: HydrologyResponsePlan,
    path: Path,
) -> Path:
    """Write a response plan as JSON."""

    return _write_json(plan.to_dict(), path)


def load_hydrology_response_plan(path: Path) -> HydrologyResponsePlan:
    """Load a response plan from JSON."""

    resolved = path.expanduser().resolve()
    payload = _read_json_object(resolved, context="response plan")
    schema = _required_str(payload, "schema_version", context="response plan")
    if schema != HYDROLOGY_RESPONSE_PLAN_SCHEMA_VERSION:
        raise HydrologyResponseError(
            f"Unsupported response plan schema {schema!r}; expected "
            f"{HYDROLOGY_RESPONSE_PLAN_SCHEMA_VERSION!r}."
        )
    artifacts = tuple(
        _artifact_spec_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "artifacts", context="response plan"),
            start=1,
        )
    )
    plan = HydrologyResponsePlan(
        bundle_version=_required_str(
            payload,
            "bundle_version",
            context="response plan",
        ),
        domain_id=_required_str(payload, "domain_id", context="response plan"),
        ledger_id=_required_str(payload, "ledger_id", context="response plan"),
        response_surface_id=_required_str(
            payload,
            "response_surface_id",
            context="response plan",
        ),
        artifacts=artifacts,
        applicability_domain=_optional_mapping(
            payload.get("applicability_domain"),
            context="applicability_domain",
        ),
        uncertainty=_optional_mapping(
            payload.get("uncertainty"), context="uncertainty"
        ),
        caveats=_optional_str_list(payload.get("caveats"), context="caveats"),
        provenance=_optional_mapping(payload.get("provenance"), context="provenance"),
        schema_version=schema,
    )
    errors = validate_hydrology_response_plan(plan)
    if errors:
        raise HydrologyResponseError("; ".join(errors))
    return plan


def build_hydrology_response_bundle(
    plan_path: Path,
    output_dir: Path,
    *,
    overwrite: bool = False,
    generated_utc: str | None = None,
) -> HydrologyResponseBuildResult:
    """Build a versioned response bundle from a plan and local artifacts."""

    resolved_plan_path = plan_path.expanduser().resolve()
    plan = load_hydrology_response_plan(resolved_plan_path)
    plan_root = resolved_plan_path.parent
    output = output_dir.expanduser().resolve()
    _prepare_output(output, overwrite=overwrite)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        (temp_dir / HYDROLOGY_RESPONSE_PROVENANCE_DIR).mkdir(parents=True)
        plan_text = _pretty_json(plan.to_dict())
        (
            temp_dir / HYDROLOGY_RESPONSE_PROVENANCE_DIR / "response_plan.json"
        ).write_text(
            plan_text,
            encoding="utf-8",
        )
        artifacts: list[HydrologyResponseArtifact] = []
        response_payload: dict[str, object] | None = None
        risk_payload: dict[str, object] | None = None
        extracted_applicability: dict[str, object] = {}
        extracted_uncertainty: dict[str, object] = {}
        for spec in sorted(plan.artifacts, key=lambda item: item.role):
            source = Path(spec.path).expanduser()
            if not source.is_absolute():
                source = plan_root / source
            source = source.resolve()
            if not source.is_file():
                raise HydrologyResponseError(
                    f"Artifact {spec.role!r} is missing: {source}"
                )
            payload = _read_json_object(source, context=f"artifact {spec.role}")
            actual_schema = _optional_str(payload.get("schema_version"))
            expected_schema = ROLE_SCHEMAS.get(spec.role)
            if expected_schema is not None and actual_schema != expected_schema:
                raise HydrologyResponseError(
                    f"Artifact {spec.role!r} has schema {actual_schema!r}; "
                    f"expected {expected_schema!r}."
                )
            if spec.role == "response_surface":
                response_payload = payload
                if _required_str(payload, "surface_id", context="response surface") != (
                    plan.response_surface_id
                ):
                    raise HydrologyResponseError(
                        "Response surface ID does not match the plan."
                    )
            elif spec.role == "flood_risk":
                risk_table = FloodRiskTable.from_dict(payload)
                if risk_table.source_surface_id != plan.response_surface_id:
                    raise HydrologyResponseError(
                        "Flood-risk table source surface does not match the plan."
                    )
                risk_payload = payload
            elif spec.role == "domain":
                if _required_str(payload, "domain_id", context="domain artifact") != (
                    plan.domain_id
                ):
                    raise HydrologyResponseError(
                        "Domain artifact ID does not match the plan."
                    )
            elif spec.role == "disturbance_ledger":
                if (
                    _required_str(
                        payload,
                        "ledger_id",
                        context="disturbance ledger",
                    )
                    != plan.ledger_id
                ):
                    raise HydrologyResponseError(
                        "Disturbance ledger ID does not match the plan."
                    )
                if (
                    _required_str(
                        payload,
                        "domain_id",
                        context="disturbance ledger",
                    )
                    != plan.domain_id
                ):
                    raise HydrologyResponseError(
                        "Disturbance ledger domain ID does not match the plan."
                    )
            elif spec.role == "surrogate_model":
                domain_payload = _optional_mapping(
                    payload.get("applicability_domain"),
                    context="applicability_domain",
                )
                if domain_payload:
                    extracted_applicability = domain_payload
            elif spec.role == "surrogate_validation":
                extracted_uncertainty = {
                    key: payload[key]
                    for key in ("rmse", "mae", "r2", "coverage_95")
                    if key in payload
                }
            relative_path = (
                f"{HYDROLOGY_RESPONSE_ARTIFACTS_DIR}/{spec.role}/"
                f"{_safe_filename(source.name)}"
            )
            destination = temp_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            digest = _sha256_file(destination)
            artifacts.append(
                HydrologyResponseArtifact(
                    artifact_id=f"{spec.role}:{digest[:12]}",
                    role=spec.role,
                    relative_path=relative_path,
                    schema_version=actual_schema,
                    media_type="application/json",
                    size_bytes=destination.stat().st_size,
                    sha256=digest,
                    description=spec.description,
                )
            )
        if response_payload is None:
            raise HydrologyResponseError("Response surface artifact is required.")
        if risk_payload is None:
            flood_risk: dict[str, object] = {}
        else:
            risk_table = FloodRiskTable.from_dict(risk_payload)
            flood_risk = {
                "table_id": risk_table.table_id,
                "row_count": len(risk_table.rows),
                "baseline_name": risk_table.baseline_name,
            }
        applicability = plan.applicability_domain or extracted_applicability
        uncertainty = {
            **plan.uncertainty,
            **extracted_uncertainty,
        }
        timestamp = generated_utc or _now()
        material = {
            "plan": plan.to_dict(),
            "artifacts": [artifact.to_dict() for artifact in artifacts],
        }
        digest = hashlib.sha256(_canonical_json_bytes(material)).hexdigest()
        bundle_id = f"hydro-response-{digest[:16]}"
        manifest = HydrologyResponseManifest(
            bundle_id=bundle_id,
            bundle_name=f"{bundle_id}-{plan.bundle_version}",
            bundle_version=plan.bundle_version,
            generated_utc=timestamp,
            domain_id=plan.domain_id,
            ledger_id=plan.ledger_id,
            response_surface_id=plan.response_surface_id,
            artifacts=tuple(artifacts),
            applicability_domain=applicability,
            uncertainty=uncertainty,
            response_surface={
                "surface_id": plan.response_surface_id,
                "baseline_name": _optional_str(response_payload.get("baseline_name")),
                "return_periods": response_payload.get("return_periods", []),
            },
            flood_risk=flood_risk,
            consumer_contract=_consumer_contract(),
            caveats=plan.caveats,
            provenance={
                "producer": "femic.hydrology.response_bundle",
                **plan.provenance,
                "materialized_utc": timestamp,
            },
        )
        manifest_path = temp_dir / HYDROLOGY_RESPONSE_MANIFEST_NAME
        manifest_path.write_text(_pretty_json(manifest.to_dict()), encoding="utf-8")
        if output.exists():
            if any(output.iterdir()):
                _assert_replaceable_bundle(output)
                shutil.rmtree(output)
            else:
                output.rmdir()
        temp_dir.replace(output)
        return HydrologyResponseBuildResult(
            bundle_dir=output,
            manifest_path=output / HYDROLOGY_RESPONSE_MANIFEST_NAME,
            manifest=manifest,
        )
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def load_hydrology_response_manifest(path: Path) -> HydrologyResponseManifest:
    """Load a response bundle manifest from JSON."""

    resolved = _resolve_manifest_path(path)
    payload = _read_json_object(resolved, context="response bundle manifest")
    schema = _required_str(payload, "schema_version", context="response manifest")
    if schema != HYDROLOGY_RESPONSE_SCHEMA_VERSION:
        raise HydrologyResponseError(
            f"Unsupported response manifest schema {schema!r}; expected "
            f"{HYDROLOGY_RESPONSE_SCHEMA_VERSION!r}."
        )
    artifacts = tuple(
        _artifact_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "artifacts", context="response manifest"),
            start=1,
        )
    )
    return HydrologyResponseManifest(
        bundle_id=_required_str(payload, "bundle_id", context="response manifest"),
        bundle_name=_required_str(payload, "bundle_name", context="response manifest"),
        bundle_version=_required_str(
            payload,
            "bundle_version",
            context="response manifest",
        ),
        generated_utc=_optional_str(payload.get("generated_utc")) or "",
        domain_id=_required_str(payload, "domain_id", context="response manifest"),
        ledger_id=_required_str(payload, "ledger_id", context="response manifest"),
        response_surface_id=_required_str(
            payload,
            "response_surface_id",
            context="response manifest",
        ),
        artifacts=artifacts,
        applicability_domain=_optional_mapping(
            payload.get("applicability_domain"),
            context="applicability_domain",
        ),
        uncertainty=_optional_mapping(
            payload.get("uncertainty"), context="uncertainty"
        ),
        response_surface=_optional_mapping(
            payload.get("response_surface"),
            context="response_surface",
        ),
        flood_risk=_optional_mapping(payload.get("flood_risk"), context="flood_risk"),
        consumer_contract=_optional_mapping(
            payload.get("consumer_contract"),
            context="consumer_contract",
        ),
        caveats=_optional_str_list(payload.get("caveats"), context="caveats"),
        provenance=_optional_mapping(payload.get("provenance"), context="provenance"),
        schema_version=schema,
    )


def validate_hydrology_response_bundle(
    manifest: HydrologyResponseManifest,
) -> tuple[str, ...]:
    """Validate response-bundle manifest structure and consumer contract."""

    errors: list[str] = []
    if manifest.schema_version != HYDROLOGY_RESPONSE_SCHEMA_VERSION:
        errors.append(f"Unsupported response schema {manifest.schema_version!r}.")
    for name, value in (
        ("bundle_id", manifest.bundle_id),
        ("bundle_name", manifest.bundle_name),
        ("bundle_version", manifest.bundle_version),
        ("domain_id", manifest.domain_id),
        ("ledger_id", manifest.ledger_id),
        ("response_surface_id", manifest.response_surface_id),
    ):
        if not value.strip():
            errors.append(f"{name} must be non-empty.")
    if not manifest.artifacts:
        errors.append("Bundle must contain artifacts.")
    if not manifest.bundle_name.startswith(manifest.bundle_id):
        errors.append("Bundle name must start with the bundle ID.")
    roles = {artifact.role for artifact in manifest.artifacts}
    missing = [role for role in HYDROLOGY_RESPONSE_REQUIRED_ROLES if role not in roles]
    if missing:
        errors.append(
            "Bundle is missing required artifact roles: " + ", ".join(missing) + "."
        )
    for artifact in manifest.artifacts:
        if artifact.role not in HYDROLOGY_RESPONSE_ARTIFACT_ROLES:
            errors.append(f"Unsupported artifact role {artifact.role!r}.")
        expected_schema = ROLE_SCHEMAS.get(artifact.role)
        if expected_schema is not None and artifact.schema_version != expected_schema:
            errors.append(
                f"Artifact {artifact.role!r} schema {artifact.schema_version!r} "
                f"does not match {expected_schema!r}."
            )
        if not artifact.relative_path.strip():
            errors.append(f"Artifact {artifact.role!r} has no relative path.")
        if not SHA256_PATTERN.match(artifact.sha256):
            errors.append(f"Artifact {artifact.role!r} has an invalid SHA-256.")
        if artifact.size_bytes < 0:
            errors.append(f"Artifact {artifact.role!r} has a negative size.")
    for key in (
        "manifest_path",
        "read_order",
        "pin_rule",
        "applicability_rule",
        "native_units_rule",
        "consumer_phases",
    ):
        if key not in manifest.consumer_contract:
            errors.append(f"Consumer contract is missing {key!r}.")
    phases = manifest.consumer_contract.get("consumer_phases")
    if not isinstance(phases, Mapping):
        errors.append("Consumer contract phases must be an object.")
    else:
        for consumer, phase in (("ws4", "P49"), ("fhops", "P14")):
            if phases.get(consumer) != phase:
                errors.append(f"Consumer contract must map {consumer!r} to {phase!r}.")
    if not manifest.response_surface:
        errors.append("Bundle is missing a response-surface summary.")
    else:
        for key in ("surface_id", "baseline_name", "return_periods"):
            if key not in manifest.response_surface:
                errors.append(f"Response-surface summary is missing {key!r}.")
    if not manifest.flood_risk:
        errors.append("Bundle is missing a flood-risk summary.")
    else:
        for key in ("table_id", "row_count", "baseline_name"):
            if key not in manifest.flood_risk:
                errors.append(f"Flood-risk summary is missing {key!r}.")
    return tuple(errors)


def audit_hydrology_response_bundle(
    path: Path,
    *,
    checked_utc: str | None = None,
) -> HydrologyResponseAudit:
    """Validate a response manifest and audit local artifacts."""

    manifest_path = _resolve_manifest_path(path)
    bundle_dir = manifest_path.parent
    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest = load_hydrology_response_manifest(manifest_path)
    except HydrologyResponseError as exc:
        return HydrologyResponseAudit(
            bundle_id="",
            bundle_dir=bundle_dir,
            manifest_path=manifest_path,
            is_valid=False,
            is_complete=False,
            checked_utc=checked_utc or _now(),
            artifacts=(),
            errors=(str(exc),),
            warnings=(),
        )
    errors.extend(validate_hydrology_response_bundle(manifest))
    artifact_audits: list[HydrologyResponseArtifactAudit] = []
    for artifact in manifest.artifacts:
        member = _resolve_member(bundle_dir, artifact.relative_path)
        issues: list[str] = []
        if member is None:
            errors.append(f"Artifact {artifact.role!r} path escapes the bundle.")
            artifact_audits.append(
                HydrologyResponseArtifactAudit(
                    artifact_id=artifact.artifact_id,
                    role=artifact.role,
                    relative_path=artifact.relative_path,
                    exists=False,
                    size_bytes=None,
                    expected_size_bytes=artifact.size_bytes,
                    checksum_ok=None,
                    issues=("path escape",),
                )
            )
            continue
        exists = member.is_file()
        size_bytes = member.stat().st_size if exists else None
        checksum_ok: bool | None = None
        if not exists:
            issues.append("missing file")
            errors.append(f"Artifact is missing: {artifact.relative_path}")
        else:
            if size_bytes != artifact.size_bytes:
                issues.append("size mismatch")
                errors.append(
                    f"Artifact {artifact.role!r} size mismatch: {size_bytes} != "
                    f"{artifact.size_bytes}."
                )
            checksum_ok = _sha256_file(member) == artifact.sha256.lower()
            if not checksum_ok:
                issues.append("checksum mismatch")
                errors.append(f"Artifact {artifact.role!r} checksum mismatch.")
        artifact_audits.append(
            HydrologyResponseArtifactAudit(
                artifact_id=artifact.artifact_id,
                role=artifact.role,
                relative_path=artifact.relative_path,
                exists=exists,
                size_bytes=size_bytes,
                expected_size_bytes=artifact.size_bytes,
                checksum_ok=checksum_ok,
                issues=tuple(issues),
            )
        )
    by_role = {artifact.role: artifact for artifact in manifest.artifacts}
    surface_artifact = by_role.get("response_surface")
    if surface_artifact is not None:
        surface_member = _resolve_member(bundle_dir, surface_artifact.relative_path)
        if surface_member is not None and surface_member.is_file():
            try:
                payload = _read_json_object(surface_member, context="response surface")
                if payload.get("schema_version") != ROLE_SCHEMAS["response_surface"]:
                    errors.append("Response surface artifact schema is unsupported.")
                if payload.get("surface_id") != manifest.response_surface_id:
                    errors.append(
                        "Response surface artifact ID does not match the manifest."
                    )
                periods = payload.get("return_periods")
                if not isinstance(periods, list) or not periods:
                    errors.append("Response surface artifact has no return periods.")
                elif periods != manifest.response_surface.get("return_periods"):
                    errors.append(
                        "Response surface return periods do not match the manifest."
                    )
            except HydrologyResponseError as exc:
                errors.append(str(exc))
    risk_artifact = by_role.get("flood_risk")
    if risk_artifact is not None:
        risk_member = _resolve_member(bundle_dir, risk_artifact.relative_path)
        if risk_member is not None and risk_member.is_file():
            try:
                table = read_flood_risk_table(risk_member)
                if table.source_surface_id != manifest.response_surface_id:
                    errors.append(
                        "Flood-risk table source surface does not match the manifest."
                    )
                if table.table_id != manifest.flood_risk.get("table_id"):
                    errors.append("Flood-risk table ID does not match the manifest.")
                if len(table.rows) != manifest.flood_risk.get("row_count"):
                    errors.append("Flood-risk row count does not match the manifest.")
            except HydrologyResponseError as exc:
                errors.append(str(exc))
    domain_artifact = by_role.get("domain")
    if domain_artifact is not None:
        domain_member = _resolve_member(bundle_dir, domain_artifact.relative_path)
        if domain_member is not None and domain_member.is_file():
            try:
                payload = _read_json_object(domain_member, context="domain artifact")
                if payload.get("domain_id") != manifest.domain_id:
                    errors.append("Domain artifact ID does not match the manifest.")
            except HydrologyResponseError as exc:
                errors.append(str(exc))
    ledger_artifact = by_role.get("disturbance_ledger")
    if ledger_artifact is not None:
        ledger_member = _resolve_member(bundle_dir, ledger_artifact.relative_path)
        if ledger_member is not None and ledger_member.is_file():
            try:
                payload = _read_json_object(
                    ledger_member,
                    context="disturbance ledger artifact",
                )
                if payload.get("ledger_id") != manifest.ledger_id:
                    errors.append("Disturbance ledger ID does not match the manifest.")
                if payload.get("domain_id") != manifest.domain_id:
                    errors.append(
                        "Disturbance ledger domain ID does not match the manifest."
                    )
            except HydrologyResponseError as exc:
                errors.append(str(exc))
    return HydrologyResponseAudit(
        bundle_id=manifest.bundle_id,
        bundle_dir=bundle_dir,
        manifest_path=manifest_path,
        is_valid=not errors,
        is_complete=not errors and bool(manifest.artifacts),
        checked_utc=checked_utc or _now(),
        artifacts=tuple(artifact_audits),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _consumer_contract() -> dict[str, object]:
    return {
        "manifest_path": HYDROLOGY_RESPONSE_MANIFEST_NAME,
        "read_order": [
            "manifest.json",
            "artifacts/response_surface/*.json",
            "artifacts/flood_risk/*.json",
            "artifacts/surrogate_model/*.json",
            "artifacts/domain/*.json",
            "artifacts/disturbance_ledger/*.json",
        ],
        "pin_rule": (
            "Pin bundle_id and bundle_version, then verify every artifact sha256 "
            "before use."
        ),
        "applicability_rule": (
            "Refuse queries outside the recorded applicability domain unless an "
            "explicit reviewed extrapolation is approved."
        ),
        "native_units_rule": (
            "Use the recorded CRS, time step, flow units, area units, and return "
            "periods; do not silently reproject, resample, or convert units."
        ),
        "consumer_phases": {"ws4": "P49", "fhops": "P14"},
    }


def _artifact_spec_from_payload(item: object, *, index: int) -> ResponseArtifactSpec:
    payload = _mapping_from_object(item, context=f"artifact {index}")
    return ResponseArtifactSpec(
        role=_required_str(payload, "role", context=f"artifact {index}"),
        path=_required_str(payload, "path", context=f"artifact {index}"),
        schema_version=_optional_str(payload.get("schema_version")),
        description=_optional_str(payload.get("description")) or "",
    )


def _artifact_from_payload(item: object, *, index: int) -> HydrologyResponseArtifact:
    payload = _mapping_from_object(item, context=f"artifact {index}")
    return HydrologyResponseArtifact(
        artifact_id=_required_str(
            payload,
            "artifact_id",
            context=f"artifact {index}",
        ),
        role=_required_str(payload, "role", context=f"artifact {index}"),
        relative_path=_required_str(
            payload,
            "relative_path",
            context=f"artifact {index}",
        ),
        schema_version=_optional_str(payload.get("schema_version")),
        media_type=_required_str(
            payload,
            "media_type",
            context=f"artifact {index}",
        ),
        size_bytes=_required_int(payload, "size_bytes", context=f"artifact {index}"),
        sha256=_required_str(payload, "sha256", context=f"artifact {index}"),
        description=_optional_str(payload.get("description")) or "",
    )


def _risk_row_from_payload(item: object, *, index: int) -> FloodRiskRow:
    payload = _mapping_from_object(item, context=f"risk row {index}")
    return FloodRiskRow(
        receptor_id=_required_str(
            payload,
            "receptor_id",
            context=f"risk row {index}",
        ),
        watershed_id=_required_str(
            payload,
            "watershed_id",
            context=f"risk row {index}",
        ),
        return_period=_required_float(
            payload,
            "return_period",
            context=f"risk row {index}",
        ),
        baseline_peak_flow_m3s=_required_float(
            payload,
            "baseline_peak_flow_m3s",
            context=f"risk row {index}",
        ),
        scenario_peak_flow_m3s=_required_float(
            payload,
            "scenario_peak_flow_m3s",
            context=f"risk row {index}",
        ),
        ratio=_required_float(payload, "ratio", context=f"risk row {index}"),
        exceedance_probability=_optional_float(payload.get("exceedance_probability")),
        expected_annual_damage=_optional_float(payload.get("expected_annual_damage")),
    )


def _prepare_output(output: Path, *, overwrite: bool) -> None:
    if not output.exists():
        return
    if not output.is_dir():
        raise HydrologyResponseError(f"Output path is not a directory: {output}")
    if not any(output.iterdir()):
        return
    if not overwrite:
        raise HydrologyResponseError(
            f"Output directory is not empty: {output}. Use `overwrite=True`."
        )
    _assert_replaceable_bundle(output)


def _assert_replaceable_bundle(output: Path) -> None:
    manifest_path = output / HYDROLOGY_RESPONSE_MANIFEST_NAME
    if not manifest_path.is_file():
        raise HydrologyResponseError(
            f"Refusing to overwrite non-bundle directory: {output}"
        )
    load_hydrology_response_manifest(manifest_path)


def _resolve_manifest_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    return (
        resolved / HYDROLOGY_RESPONSE_MANIFEST_NAME if resolved.is_dir() else resolved
    )


def _resolve_member(root: Path, relative_path: str) -> Path | None:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _safe_filename(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return text or "artifact.json"


def _read_json_object(path: Path, *, context: str) -> dict[str, object]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise HydrologyResponseError(
            f"Unable to read {context}: {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise HydrologyResponseError(
            f"Invalid JSON in {context}: {path}: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise HydrologyResponseError(f"{context} must be a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _mapping_from_object(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise HydrologyResponseError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _required_list(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise HydrologyResponseError(f"{context} field {key!r} must be a list.")
    return value


def _required_str(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HydrologyResponseError(
            f"{context} field {key!r} must be a non-empty string."
        )
    return value.strip()


def _required_float(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> float:
    value = mapping.get(key)
    if isinstance(value, bool):
        raise HydrologyResponseError(f"{context} field {key!r} must be numeric.")
    try:
        parsed = float(str(value))
    except (TypeError, ValueError) as exc:
        raise HydrologyResponseError(
            f"{context} field {key!r} must be numeric."
        ) from exc
    if not math.isfinite(parsed):
        raise HydrologyResponseError(f"{context} field {key!r} must be finite.")
    return parsed


def _required_int(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> int:
    value = mapping.get(key)
    if isinstance(value, bool):
        raise HydrologyResponseError(f"{context} field {key!r} must be an integer.")
    try:
        return _coerce_int(value)
    except (TypeError, ValueError) as exc:
        raise HydrologyResponseError(
            f"{context} field {key!r} must be an integer."
        ) from exc


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError("Boolean values are not integers.")
    return int(str(value))


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _optional_str_list(value: object, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise HydrologyResponseError(f"{context} must be a list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise HydrologyResponseError(f"{context} entries must be strings.")
        text = item.strip()
        if text:
            items.append(text)
    return tuple(items)


def _optional_mapping(value: object, *, context: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise HydrologyResponseError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _pretty_json(payload: object) -> str:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def _write_json(payload: object, path: Path) -> Path:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(_pretty_json(payload), encoding="utf-8")
    return resolved


def _now() -> str:
    return datetime.now(UTC).isoformat()


SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
