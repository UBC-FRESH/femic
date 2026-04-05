"""Instance-local TSR recipe scaffold helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources as importlib_resources
import json
from pathlib import Path
import re
from typing import Any

import geopandas as gpd  # type: ignore[import-untyped]
import pandas as pd
import yaml

from femic.bcdc_catalog import (
    INDIRECT_CUSTOM_DOWNLOAD,
    SERVICE,
    SUPPORTING_DOCUMENT,
    download_direct_bcdc_resources,
    resolve_bcdc_candidates,
)
from femic.bcdc_dwds import BcdcDwdsError, submit_bcdc_dwds_order
from femic.bcdc_fetch import (
    BC_ALBERS_EPSG,
    BcdcFetchError,
    GeomarkBBox,
    fetch_bcdc_wfs_data,
)

from .overlay import TsrOverlayTsaRecord
from .report import TsrFactReviewRow, report_tsr_candidate_facts
from .source_overrides import (
    TsrSourceLayerOverrideEntry,
    load_tsr_source_layer_overrides,
)


class TsrRecipeError(RuntimeError):
    """Raised when TSR recipe initialization or loading fails."""


_TSR_RECIPE_RESOURCE_PACKAGE = "femic.resources.tsr_recipes"
_SOURCE_LAYERS_RECIPE_RESOURCE = "source_layers.recipe.yaml"
_THLB_NETDOWN_RECIPE_RESOURCE = "thlb_netdown.recipe.yaml"
TSR_THLB_EXECUTION_MODE_HYBRID = "hybrid"
TSR_THLB_EXECUTION_MODE_RECONSTRUCTED = "reconstructed"
_TSR_THLB_EXECUTION_MODES = {
    TSR_THLB_EXECUTION_MODE_HYBRID,
    TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
}
_RECONSTRUCTED_FRAGMENT_ROW_THRESHOLD = 10000
_RECONSTRUCTED_STAND_BINARY_EXCLUDE_THRESHOLD = 0.5


@dataclass(frozen=True)
class TsrRecipeCanonicalInputs:
    """Canonical shared inputs referenced by TSR recipes."""

    registry_path: str
    documents_path: str
    candidate_facts_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "registry_path": self.registry_path,
            "documents_path": self.documents_path,
            "candidate_facts_path": self.candidate_facts_path,
        }


@dataclass(frozen=True)
class TsrSourceLayersRecipeInstanceInputs:
    """Instance-local inputs referenced by the source-layer recipe."""

    overlay_path: str
    source_layer_overrides_path: str
    download_root: str

    def to_dict(self) -> dict[str, str]:
        return {
            "overlay_path": self.overlay_path,
            "source_layer_overrides_path": self.source_layer_overrides_path,
            "download_root": self.download_root,
        }


@dataclass(frozen=True)
class TsrThlbNetdownRecipeInstanceInputs:
    """Instance-local inputs referenced by the THLB netdown recipe."""

    overlay_path: str
    source_layer_recipe_path: str
    source_layer_overrides_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "overlay_path": self.overlay_path,
            "source_layer_recipe_path": self.source_layer_recipe_path,
            "source_layer_overrides_path": self.source_layer_overrides_path,
        }


@dataclass(frozen=True)
class TsrSourceLayersRecipeRecord:
    """One instance-local source-layer recipe scaffold."""

    schema_version: int
    recipe_kind: str
    tsa: TsrOverlayTsaRecord
    canonical_inputs: TsrRecipeCanonicalInputs
    instance_inputs: TsrSourceLayersRecipeInstanceInputs
    recipe_contract: dict[str, Any]
    entries: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "recipe_kind": self.recipe_kind,
            "tsa": self.tsa.to_dict(),
            "canonical_inputs": self.canonical_inputs.to_dict(),
            "instance_inputs": self.instance_inputs.to_dict(),
            "recipe_contract": dict(self.recipe_contract),
            "entries": [dict(entry) for entry in self.entries],
        }


@dataclass(frozen=True)
class TsrThlbNetdownRecipeRecord:
    """One instance-local THLB netdown recipe scaffold."""

    schema_version: int
    recipe_kind: str
    tsa: TsrOverlayTsaRecord
    canonical_inputs: TsrRecipeCanonicalInputs
    instance_inputs: TsrThlbNetdownRecipeInstanceInputs
    recipe_contract: dict[str, Any]
    steps: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "recipe_kind": self.recipe_kind,
            "tsa": self.tsa.to_dict(),
            "canonical_inputs": self.canonical_inputs.to_dict(),
            "instance_inputs": self.instance_inputs.to_dict(),
            "recipe_contract": dict(self.recipe_contract),
            "steps": [dict(step) for step in self.steps],
        }


@dataclass(frozen=True)
class TsrRecipeInitResult:
    """Result payload for recipe scaffold initialization."""

    tsa: TsrOverlayTsaRecord
    source_layers_recipe_path: Path
    thlb_netdown_recipe_path: Path
    created_source_layers_recipe: bool
    created_thlb_netdown_recipe: bool


@dataclass(frozen=True)
class TsrSourceLayersRecipeBuildResult:
    """Summary of one source-layer recipe build pass."""

    recipe_path: Path
    tsa: TsrOverlayTsaRecord
    entry_count: int
    status_counts: dict[str, int]


@dataclass(frozen=True)
class TsrSourceLayersRecipeRunResult:
    """Summary of one source-layer recipe execution pass."""

    recipe_path: Path
    tsa: TsrOverlayTsaRecord
    entry_count: int
    outcome_counts: dict[str, int]


@dataclass(frozen=True)
class TsrThlbNetdownRecipeBuildResult:
    """Summary of one THLB netdown recipe build pass."""

    recipe_path: Path
    tsa: TsrOverlayTsaRecord
    step_count: int
    step_kind_counts: dict[str, int]
    status_counts: dict[str, int]
    selected_document_paths: tuple[str, ...]


@dataclass(frozen=True)
class TsrThlbNetdownRecipeRunResult:
    """Summary of one THLB netdown recipe execution pass."""

    recipe_path: Path
    tsa: TsrOverlayTsaRecord
    checkpoint_path: Path
    output_path: Path
    audit_path: Path
    execution_mode: str
    baseline_signal: str
    step_count: int
    outcome_counts: dict[str, int]
    baseline_managed_area_ha: float
    final_managed_area_ha: float
    legacy_reference_managed_area_ha: float | None
    tsr_reported_thlb_area_ha: float | None


def _read_json_object(path: Path, *, description: str) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrRecipeError(f"{description} not found: {resolved}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid {description.lower()} payload: {resolved}")
    return payload


def _normalize_tsa_token(value: str) -> str:
    return value.strip().replace("_", " ").casefold()


def _resolve_tsa_record(*, tsa: str, registry_path: Path) -> TsrOverlayTsaRecord:
    payload = _read_json_object(registry_path, description="TSR registry JSON")
    records = payload.get("tsas")
    if not isinstance(records, list):
        raise TsrRecipeError("TSR registry JSON is missing a valid `tsas` list.")
    normalized = _normalize_tsa_token(tsa)
    matches: list[TsrOverlayTsaRecord] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        record = TsrOverlayTsaRecord(
            tsa_id=str(item.get("tsa_id", "")),
            tsa_code=str(item.get("tsa_code", "")),
            tsa_name=str(item.get("tsa_name", "")),
        )
        if normalized in {
            _normalize_tsa_token(record.tsa_id),
            _normalize_tsa_token(record.tsa_code),
            _normalize_tsa_token(record.tsa_code.lstrip("0") or record.tsa_code),
            _normalize_tsa_token(record.tsa_name),
        }:
            matches.append(record)
    if not matches:
        raise TsrRecipeError(f"No canonical TSR TSA match found for `{tsa}`.")
    if len(matches) > 1:
        labels = ", ".join(f"{record.tsa_code}:{record.tsa_name}" for record in matches)
        raise TsrRecipeError(f"Ambiguous TSR TSA match for `{tsa}`: {labels}")
    return matches[0]


def _load_resource_yaml(resource_name: str) -> dict[str, Any]:
    resource = importlib_resources.files(_TSR_RECIPE_RESOURCE_PACKAGE).joinpath(
        resource_name
    )
    payload = yaml.safe_load(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid packaged TSR recipe template: {resource_name}")
    return payload


def _repo_relative(path: Path, *, source_root: Path) -> str:
    return path.expanduser().resolve().relative_to(source_root.resolve()).as_posix()


def default_tsr_source_layers_recipe_path(*, instance_root: Path) -> Path:
    """Return the default per-instance source-layer recipe path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml"
    )


def default_tsr_thlb_netdown_recipe_path(*, instance_root: Path) -> Path:
    """Return the default per-instance THLB netdown recipe path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml"
    )


def default_tsr_thlb_netdown_output_path(*, instance_root: Path) -> Path:
    """Return the default stand-level THLB checkpoint output path."""

    return (
        instance_root.expanduser().resolve()
        / "data"
        / "tsr"
        / "thlb_netdown_checkpoint.feather"
    )


def default_tsr_thlb_netdown_audit_path(*, instance_root: Path) -> Path:
    """Return the default THLB netdown audit JSON path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_netdown.audit.json"
    )


def default_tsr_thlb_reconstructed_output_path(*, instance_root: Path) -> Path:
    """Return the default reconstructed fragment/resultant THLB checkpoint path."""

    return (
        instance_root.expanduser().resolve()
        / "data"
        / "tsr"
        / "thlb_reconstructed_checkpoint.feather"
    )


def default_tsr_thlb_reconstructed_audit_path(*, instance_root: Path) -> Path:
    """Return the default reconstructed THLB audit JSON path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_reconstructed.audit.json"
    )


def _write_recipe_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def init_tsr_recipe_scaffolds(
    *,
    instance_root: Path,
    tsa: str,
    registry_path: Path,
    documents_path: Path,
    candidate_facts_path: Path,
    source_root: Path,
    overlay_path: Path,
    overrides_path: Path,
    source_layers_recipe_path: Path,
    thlb_netdown_recipe_path: Path,
    overwrite: bool = False,
) -> TsrRecipeInitResult:
    """Initialize per-instance TSR recipe scaffold YAML files."""

    resolved_instance_root = instance_root.expanduser().resolve()
    resolved_registry_path = registry_path.expanduser().resolve()
    resolved_documents_path = documents_path.expanduser().resolve()
    resolved_candidate_facts_path = candidate_facts_path.expanduser().resolve()
    resolved_overlay_path = overlay_path.expanduser().resolve()
    resolved_overrides_path = overrides_path.expanduser().resolve()
    resolved_source_layers_recipe_path = (
        source_layers_recipe_path.expanduser().resolve()
    )
    resolved_thlb_netdown_recipe_path = thlb_netdown_recipe_path.expanduser().resolve()

    for candidate_path in (
        resolved_overlay_path,
        resolved_overrides_path,
        resolved_source_layers_recipe_path,
        resolved_thlb_netdown_recipe_path,
    ):
        try:
            candidate_path.relative_to(resolved_instance_root)
        except ValueError as exc:
            raise TsrRecipeError(
                "TSR recipe paths must live under the instance root."
            ) from exc

    if not overwrite:
        existing = [
            path
            for path in (
                resolved_source_layers_recipe_path,
                resolved_thlb_netdown_recipe_path,
            )
            if path.exists()
        ]
        if existing:
            joined = ", ".join(str(path) for path in existing)
            raise TsrRecipeError(
                "TSR recipe scaffold(s) already exist: "
                f"{joined}. Use `--overwrite` to replace them."
            )

    tsa_record = _resolve_tsa_record(tsa=tsa, registry_path=resolved_registry_path)
    canonical_inputs = TsrRecipeCanonicalInputs(
        registry_path=_repo_relative(resolved_registry_path, source_root=source_root),
        documents_path=_repo_relative(resolved_documents_path, source_root=source_root),
        candidate_facts_path=_repo_relative(
            resolved_candidate_facts_path, source_root=source_root
        ),
    )
    source_layers_instance_inputs = TsrSourceLayersRecipeInstanceInputs(
        overlay_path=str(
            resolved_overlay_path.relative_to(resolved_instance_root).as_posix()
        ),
        source_layer_overrides_path=str(
            resolved_overrides_path.relative_to(resolved_instance_root).as_posix()
        ),
        download_root="data/downloads/bcdc",
    )
    thlb_instance_inputs = TsrThlbNetdownRecipeInstanceInputs(
        overlay_path=str(
            resolved_overlay_path.relative_to(resolved_instance_root).as_posix()
        ),
        source_layer_recipe_path=str(
            resolved_source_layers_recipe_path.relative_to(
                resolved_instance_root
            ).as_posix()
        ),
        source_layer_overrides_path=str(
            resolved_overrides_path.relative_to(resolved_instance_root).as_posix()
        ),
    )

    source_layers_template = _load_resource_yaml(_SOURCE_LAYERS_RECIPE_RESOURCE)
    thlb_template = _load_resource_yaml(_THLB_NETDOWN_RECIPE_RESOURCE)

    source_layers_record = TsrSourceLayersRecipeRecord(
        schema_version=int(source_layers_template.get("schema_version", 1)),
        recipe_kind=str(source_layers_template.get("recipe_kind", "source_layers")),
        tsa=tsa_record,
        canonical_inputs=canonical_inputs,
        instance_inputs=source_layers_instance_inputs,
        recipe_contract=dict(source_layers_template.get("recipe_contract", {})),
        entries=(),
    )
    thlb_record = TsrThlbNetdownRecipeRecord(
        schema_version=int(thlb_template.get("schema_version", 1)),
        recipe_kind=str(thlb_template.get("recipe_kind", "thlb_netdown")),
        tsa=tsa_record,
        canonical_inputs=canonical_inputs,
        instance_inputs=thlb_instance_inputs,
        recipe_contract=dict(thlb_template.get("recipe_contract", {})),
        steps=(),
    )

    _write_recipe_yaml(
        resolved_source_layers_recipe_path,
        source_layers_record.to_dict(),
    )
    _write_recipe_yaml(
        resolved_thlb_netdown_recipe_path,
        thlb_record.to_dict(),
    )
    return TsrRecipeInitResult(
        tsa=tsa_record,
        source_layers_recipe_path=resolved_source_layers_recipe_path,
        thlb_netdown_recipe_path=resolved_thlb_netdown_recipe_path,
        created_source_layers_recipe=True,
        created_thlb_netdown_recipe=True,
    )


def load_tsr_source_layers_recipe(path: Path) -> TsrSourceLayersRecipeRecord:
    """Load one per-instance source-layer recipe scaffold YAML file."""

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrRecipeError(f"TSR source-layer recipe not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid TSR source-layer recipe payload: {resolved}")
    if str(payload.get("recipe_kind", "")) != "source_layers":
        raise TsrRecipeError(f"Invalid TSR source-layer recipe kind: {resolved}")
    tsa_payload = payload.get("tsa")
    canonical_payload = payload.get("canonical_inputs")
    instance_payload = payload.get("instance_inputs")
    if (
        not isinstance(tsa_payload, dict)
        or not isinstance(canonical_payload, dict)
        or not isinstance(instance_payload, dict)
    ):
        raise TsrRecipeError(f"Invalid TSR source-layer recipe structure: {resolved}")
    return TsrSourceLayersRecipeRecord(
        schema_version=int(payload.get("schema_version", 1)),
        recipe_kind="source_layers",
        tsa=TsrOverlayTsaRecord(
            tsa_id=str(tsa_payload.get("tsa_id", "")),
            tsa_code=str(tsa_payload.get("tsa_code", "")),
            tsa_name=str(tsa_payload.get("tsa_name", "")),
        ),
        canonical_inputs=TsrRecipeCanonicalInputs(
            registry_path=str(canonical_payload.get("registry_path", "")),
            documents_path=str(canonical_payload.get("documents_path", "")),
            candidate_facts_path=str(canonical_payload.get("candidate_facts_path", "")),
        ),
        instance_inputs=TsrSourceLayersRecipeInstanceInputs(
            overlay_path=str(instance_payload.get("overlay_path", "")),
            source_layer_overrides_path=str(
                instance_payload.get("source_layer_overrides_path", "")
            ),
            download_root=str(instance_payload.get("download_root", "")),
        ),
        recipe_contract=dict(payload.get("recipe_contract", {})),
        entries=tuple(
            item for item in payload.get("entries", []) if isinstance(item, dict)
        ),
    )


def load_tsr_thlb_netdown_recipe(path: Path) -> TsrThlbNetdownRecipeRecord:
    """Load one per-instance THLB netdown recipe scaffold YAML file."""

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrRecipeError(f"TSR THLB netdown recipe not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid TSR THLB netdown recipe payload: {resolved}")
    if str(payload.get("recipe_kind", "")) != "thlb_netdown":
        raise TsrRecipeError(f"Invalid TSR THLB netdown recipe kind: {resolved}")
    tsa_payload = payload.get("tsa")
    canonical_payload = payload.get("canonical_inputs")
    instance_payload = payload.get("instance_inputs")
    if (
        not isinstance(tsa_payload, dict)
        or not isinstance(canonical_payload, dict)
        or not isinstance(instance_payload, dict)
    ):
        raise TsrRecipeError(f"Invalid TSR THLB netdown recipe structure: {resolved}")
    return TsrThlbNetdownRecipeRecord(
        schema_version=int(payload.get("schema_version", 1)),
        recipe_kind="thlb_netdown",
        tsa=TsrOverlayTsaRecord(
            tsa_id=str(tsa_payload.get("tsa_id", "")),
            tsa_code=str(tsa_payload.get("tsa_code", "")),
            tsa_name=str(tsa_payload.get("tsa_name", "")),
        ),
        canonical_inputs=TsrRecipeCanonicalInputs(
            registry_path=str(canonical_payload.get("registry_path", "")),
            documents_path=str(canonical_payload.get("documents_path", "")),
            candidate_facts_path=str(canonical_payload.get("candidate_facts_path", "")),
        ),
        instance_inputs=TsrThlbNetdownRecipeInstanceInputs(
            overlay_path=str(instance_payload.get("overlay_path", "")),
            source_layer_recipe_path=str(
                instance_payload.get("source_layer_recipe_path", "")
            ),
            source_layer_overrides_path=str(
                instance_payload.get("source_layer_overrides_path", "")
            ),
        ),
        recipe_contract=dict(payload.get("recipe_contract", {})),
        steps=tuple(
            item for item in payload.get("steps", []) if isinstance(item, dict)
        ),
    )


_RECIPE_ENTRY_ID_RE = re.compile(r"[^a-z0-9]+")


def _recipe_entry_id(query: str) -> str:
    slug = _RECIPE_ENTRY_ID_RE.sub("_", query.strip().casefold()).strip("_")
    return slug or "entry"


def _recipe_status_from_resolve(result: Any) -> str:
    top_match = result.top_match
    if top_match is None:
        return "no_hit"
    if any("alias/query variant" in note for note in result.notes):
        return "alias_hit"
    matched_by = top_match.matched_by
    if (
        matched_by.startswith("object_name:")
        or matched_by.startswith("object_short_name:")
        or matched_by.startswith("object_name_suffix:")
        or matched_by.startswith("object_name_stem:")
    ):
        return "exact_hit"
    return "weak_text_hit"


def _used_alias_from_notes(notes: tuple[str, ...]) -> str:
    return next(
        (
            note.split("`")[1]
            for note in notes
            if "alias/query variant" in note and "`" in note
        ),
        "",
    )


def _resource_object_names(resources: tuple[Any, ...]) -> tuple[str, ...]:
    names: list[str] = []
    for resource in resources:
        object_name = str(getattr(resource, "object_name", "") or "").strip()
        if object_name and object_name not in names:
            names.append(object_name)
    return tuple(names)


def _resolve_path_from_recipe(source_root: Path, relative_path: str) -> Path:
    return (source_root / Path(relative_path)).expanduser().resolve()


def _resolve_instance_path(instance_root: Path, relative_path: str) -> Path:
    return (instance_root / Path(relative_path)).expanduser().resolve()


def _load_override_map(
    overrides_path: Path,
) -> dict[str, TsrSourceLayerOverrideEntry]:
    if not overrides_path.exists():
        return {}
    record = load_tsr_source_layer_overrides(overrides_path)
    return {entry.query.casefold(): entry for entry in record.entries}


def _load_overlay_attempt_map(
    overlay_path: Path,
) -> dict[str, dict[str, Any]]:
    if not overlay_path.exists():
        return {}
    payload = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    review_payload = payload.get("bcdc_acquisition_review")
    if not isinstance(review_payload, dict):
        return {}
    attempts = review_payload.get("attempts", [])
    if not isinstance(attempts, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        query = str(attempt.get("query", "")).strip()
        if not query:
            continue
        result[query.casefold()] = attempt
    return result


def _review_rows_for_recipe(
    candidate_facts_path: Path,
    *,
    tsa_code: str,
) -> tuple[TsrFactReviewRow, ...]:
    report = report_tsr_candidate_facts(
        candidate_facts_path=candidate_facts_path,
        tsa=tsa_code,
        fact_families=("source_layer_candidate",),
    )
    rows = [
        row
        for row in report.rows
        if row.recommended_query and row.quality != "likely_noise"
    ]
    deduped: dict[str, TsrFactReviewRow] = {}
    grouped: dict[str, list[TsrFactReviewRow]] = {}
    quality_rank = {"likely_useful": 0, "needs_review": 1, "likely_noise": 2}
    for row in rows:
        key = row.recommended_query.casefold()
        grouped.setdefault(key, []).append(row)
        current = deduped.get(key)
        if current is None or quality_rank[row.quality] < quality_rank[current.quality]:
            deduped[key] = row
    ordered = sorted(
        deduped.values(),
        key=lambda row: (
            quality_rank[row.quality],
            row.recommended_query,
            row.page_number if row.page_number is not None else 10**9,
        ),
    )
    output_rows: list[TsrFactReviewRow] = []
    for row in ordered:
        row_group = grouped[row.recommended_query.casefold()]
        output_rows.append(
            TsrFactReviewRow(
                tsa_id=row.tsa_id,
                tsa_code=row.tsa_code,
                tsa_name=row.tsa_name,
                fact_family=row.fact_family,
                extracted_value=row.extracted_value,
                recommended_query=row.recommended_query,
                quality=row.quality,
                quality_reason=row.quality_reason,
                snippet=row.snippet,
                page_number=row.page_number,
                title=row.title,
                cycle_label=row.cycle_label,
                cycle_year=row.cycle_year,
                provenance_id=" | ".join(
                    item.provenance_id for item in row_group if item.provenance_id
                ),
                source_url=row.source_url,
            )
        )
    return tuple(output_rows)


def _replacement_family_dicts(
    entry: TsrSourceLayerOverrideEntry | None,
) -> list[dict[str, object]]:
    if entry is None:
        return []
    return [candidate.to_dict() for candidate in entry.replacement_family_candidates]


def _build_source_recipe_entry(
    row: TsrFactReviewRow,
    *,
    resolve_result: Any,
    override_entry: TsrSourceLayerOverrideEntry | None,
    overlay_attempt: dict[str, Any] | None,
    instance_root: Path,
) -> dict[str, Any]:
    top_match = resolve_result.top_match
    resources = top_match.resources if top_match is not None else ()
    resource_object_names = _resource_object_names(resources)
    current_public_status = _recipe_status_from_resolve(resolve_result)
    suggested_fetch_strategy = (
        top_match.suggested_fetch_strategy if top_match is not None else None
    )
    direct_download_candidates = (
        len(top_match.direct_download_resources) if top_match is not None else 0
    )
    has_service = any(resource.classification == SERVICE for resource in resources)
    has_wfs_queryable_service = any(resource.wfs_queryable for resource in resources)
    has_indirect_custom_download = any(
        resource.classification == INDIRECT_CUSTOM_DOWNLOAD for resource in resources
    )
    has_supporting_document = any(
        resource.classification == SUPPORTING_DOCUMENT for resource in resources
    )

    if override_entry is not None and override_entry.override_kind:
        acquisition_strategy = "override"
    elif current_public_status == "no_hit":
        acquisition_strategy = "override_required"
    elif current_public_status == "weak_text_hit":
        acquisition_strategy = "manual_review_required"
    elif suggested_fetch_strategy:
        acquisition_strategy = "wfs_fetch"
    elif direct_download_candidates:
        acquisition_strategy = "direct_download"
    elif has_indirect_custom_download:
        acquisition_strategy = "dwds_order"
    else:
        acquisition_strategy = "manual_review_required"

    notes = list(resolve_result.notes)
    if top_match is not None:
        notes.extend(list(top_match.manual_follow_up))

    used_alias = _used_alias_from_notes(resolve_result.notes)
    acquisition_query = used_alias or (
        resource_object_names[0] if resource_object_names else row.recommended_query
    )

    artifact_path = ""
    prior_run_status = "pending"
    if overlay_attempt is not None:
        raw_artifact_path = str(overlay_attempt.get("saved_path", "")).replace(
            "\\", "/"
        )
        if raw_artifact_path:
            artifact_candidate = Path(raw_artifact_path)
            if artifact_candidate.is_absolute():
                try:
                    artifact_path = str(
                        artifact_candidate.resolve()
                        .relative_to(instance_root)
                        .as_posix()
                    )
                except ValueError:
                    artifact_path = raw_artifact_path
            elif raw_artifact_path.startswith(f"external/{instance_root.name}/"):
                artifact_path = raw_artifact_path.split(
                    f"external/{instance_root.name}/", 1
                )[1]
            else:
                artifact_path = raw_artifact_path
        prior_run_status = str(overlay_attempt.get("acquisition_outcome", "pending"))
        prior_notes = str(overlay_attempt.get("notes", "")).strip()
        if prior_notes:
            notes.extend(
                part.strip() for part in prior_notes.split(" | ") if part.strip()
            )

    return {
        "entry_id": _recipe_entry_id(row.recommended_query),
        "label": row.recommended_query,
        "recommended_query": row.recommended_query,
        "acquisition_query": acquisition_query,
        "extracted_value": row.extracted_value,
        "quality": row.quality,
        "quality_reason": row.quality_reason,
        "snippet": row.snippet,
        "page_number": row.page_number,
        "document_title": row.title,
        "cycle_label": row.cycle_label,
        "cycle_year": row.cycle_year,
        "provenance_id": row.provenance_id,
        "source_url": row.source_url,
        "current_public_status": current_public_status,
        "matched_by": top_match.matched_by if top_match is not None else "",
        "used_alias": used_alias,
        "top_match_title": top_match.title if top_match is not None else "",
        "dataset_page_url": top_match.dataset_page_url if top_match is not None else "",
        "suggested_fetch_strategy": suggested_fetch_strategy or "",
        "direct_download_candidates": direct_download_candidates,
        "has_service": has_service,
        "has_wfs_queryable_service": has_wfs_queryable_service,
        "has_indirect_custom_download": has_indirect_custom_download,
        "has_supporting_document": has_supporting_document,
        "acquisition_strategy": acquisition_strategy,
        "run_status": prior_run_status,
        "artifact_path": artifact_path
        or (
            override_entry.override_value
            if override_entry is not None
            and override_entry.override_kind in {"local_path", "datalad_path"}
            else ""
        ),
        "override_kind": override_entry.override_kind
        if override_entry is not None
        else "",
        "override_value": override_entry.override_value
        if override_entry is not None
        else "",
        "replacement_family_candidates": _replacement_family_dicts(override_entry),
        "feature_count": overlay_attempt.get("feature_count", "")
        if overlay_attempt is not None
        else "",
        "order_id": overlay_attempt.get("order_id", "")
        if overlay_attempt is not None
        else "",
        "submission_status": overlay_attempt.get("submission_status", "")
        if overlay_attempt is not None
        else "",
        "failure_message": overlay_attempt.get("failure_message", "")
        if overlay_attempt is not None
        else "",
        "notes": notes,
    }


def _overlay_attempt_for_row(
    row: TsrFactReviewRow,
    *,
    resolve_result: Any,
    overlay_attempt_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    top_match = resolve_result.top_match
    resources = top_match.resources if top_match is not None else ()
    candidate_keys = [
        row.recommended_query.casefold(),
        _used_alias_from_notes(resolve_result.notes).casefold(),
    ]
    candidate_keys.extend(name.casefold() for name in _resource_object_names(resources))
    for key in candidate_keys:
        if key and key in overlay_attempt_map:
            return overlay_attempt_map[key]
    return None


def _load_tsa_documents_for_recipe(
    documents_path: Path, *, tsa_id: str
) -> tuple[dict[str, dict[str, Any]], tuple[dict[str, Any], ...]]:
    payload = _read_json_object(documents_path, description="TSR documents JSON")
    documents = payload.get("documents")
    if not isinstance(documents, list):
        raise TsrRecipeError("TSR documents JSON is missing a valid `documents` list.")

    records: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for item in documents:
        if not isinstance(item, dict):
            continue
        if str(item.get("tsa_id", "")) != tsa_id:
            continue
        record = dict(item)
        relative_path = str(record.get("relative_path", "")).strip()
        if relative_path:
            index[relative_path] = record
        records.append(record)
    return index, tuple(records)


def _provenance_document_path(provenance_id: str) -> str:
    return provenance_id.split("#", 1)[0].strip()


def _coerce_cycle_year(value: object) -> int:
    text = str(value or "").strip()
    return int(text) if text.isdigit() else 0


def _normalize_whitespace(text: str) -> str:
    return " ".join(str(text or "").split())


def _normalize_step_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")
    return slug or "step"


def _choose_preferred_thlb_documents(
    rows: tuple[TsrFactReviewRow, ...],
    *,
    documents_index: dict[str, dict[str, Any]],
    documents: tuple[dict[str, Any], ...],
) -> tuple[tuple[TsrFactReviewRow, ...], tuple[str, ...]]:
    available_paths = {
        _provenance_document_path(row.provenance_id)
        for row in rows
        if row.provenance_id.strip()
    }
    if not available_paths:
        return rows, ()

    latest_year = max(
        (_coerce_cycle_year(doc.get("cycle_year")) for doc in documents),
        default=0,
    )
    preferred_paths = tuple(
        path
        for path, doc in documents_index.items()
        if path in available_paths
        and _coerce_cycle_year(doc.get("cycle_year")) == latest_year
        and str(doc.get("document_type", "")).casefold() == "data_package"
    )
    if not preferred_paths:
        preferred_paths = tuple(
            path
            for path, doc in documents_index.items()
            if path in available_paths
            and _coerce_cycle_year(doc.get("cycle_year")) == latest_year
        )
    if not preferred_paths:
        return rows, tuple(sorted(available_paths))

    selected = tuple(
        row
        for row in rows
        if _provenance_document_path(row.provenance_id) in preferred_paths
    )
    return (selected or rows), tuple(sorted(preferred_paths))


_THLB_GENERIC_TOKENS = {
    "the",
    "and",
    "for",
    "from",
    "with",
    "that",
    "this",
    "will",
    "into",
    "have",
    "used",
    "use",
    "land",
    "base",
    "timber",
    "harvesting",
    "thlb",
    "whse",
    "reg",
    "resource",
    "resources",
    "planning",
    "management",
    "current",
    "poly",
    "line",
    "lines",
    "svw",
    "sp",
    "tsa",
    "bcgw",
    "data",
    "layer",
    "forest",
    "natural",
}


def _meaningful_tokens(text: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[A-Za-z0-9]+", str(text).casefold())
        if len(token) >= 3 and token not in _THLB_GENERIC_TOKENS
    }
    return tokens


def _build_source_recipe_index(
    source_recipe: TsrSourceLayersRecipeRecord,
) -> tuple[dict[str, Any], ...]:
    indexed = []
    for entry in source_recipe.entries:
        entry_id = str(entry.get("entry_id", "")).strip()
        if not entry_id:
            continue
        label = str(entry.get("label", "")).strip()
        recommended_query = str(entry.get("recommended_query", "")).strip()
        top_match_title = str(entry.get("top_match_title", "")).strip()
        snippet = str(entry.get("snippet", "")).strip()
        tokens = (
            _meaningful_tokens(label)
            | _meaningful_tokens(recommended_query)
            | _meaningful_tokens(top_match_title)
            | _meaningful_tokens(snippet)
        )
        indexed.append(
            {
                "entry_id": entry_id,
                "label": label,
                "recommended_query": recommended_query,
                "tokens": tokens,
            }
        )
    return tuple(indexed)


def _link_thlb_step_to_sources(
    text: str,
    *,
    source_index: tuple[dict[str, Any], ...],
) -> tuple[str, ...]:
    subject_tokens = _meaningful_tokens(text)
    if not subject_tokens:
        return ()

    scored: list[tuple[int, str]] = []
    for entry in source_index:
        overlap = subject_tokens & set(entry["tokens"])
        score = len(overlap)
        if score > 0:
            scored.append((score, str(entry["entry_id"])))
    scored.sort(key=lambda item: (-item[0], item[1]))
    if not scored:
        return ()

    top_score = scored[0][0]
    linked = [entry_id for score, entry_id in scored if score == top_score]
    if top_score == 1:
        return tuple(linked[:1])
    return tuple(linked[:3])


def _match_thlb_action(text: str) -> tuple[str, str, str]:
    normalized = _normalize_whitespace(text)
    lower = normalized.casefold()

    patterns = (
        (
            "use_land_base",
            re.compile(
                r"^(?P<subject>.+?)\s+use\s+(?P<predicate>[A-Z]{3,5})$", re.IGNORECASE
            ),
        ),
        (
            "exclude",
            re.compile(
                r"^(?P<subject>.+?)\s+exclude(?:d)?\s+(?P<predicate>.+?)\s+from the thlb",
                re.IGNORECASE,
            ),
        ),
        (
            "exclude",
            re.compile(r"^(?P<subject>.+?)\s+exclude from the thlb$", re.IGNORECASE),
        ),
        (
            "exclude",
            re.compile(
                r"^(?P<subject>.+?)\s+remove(?:d)?\s+(?P<predicate>.+?)\s+from the thlb",
                re.IGNORECASE,
            ),
        ),
        (
            "exclude",
            re.compile(
                r"^(?P<subject>.+?)\s+(?:are|is)\s+removed from the thlb", re.IGNORECASE
            ),
        ),
        (
            "exclude",
            re.compile(
                r"^(?P<subject>.+?)\s+(?:are|is)\s+excluded from the thlb",
                re.IGNORECASE,
            ),
        ),
        (
            "defer",
            re.compile(
                r"^(?P<subject>.+?)\s+included in the thlb but will be deferred from harvest for (?P<predicate>\d+\s+years?)",
                re.IGNORECASE,
            ),
        ),
        (
            "aspatial_reduction",
            re.compile(
                r"^(?P<subject>.+?)\s+will be modelled as an aspatial(?: thlb)? reduction(?: factor)?",
                re.IGNORECASE,
            ),
        ),
        (
            "no_deduction",
            re.compile(
                r"^(?P<subject>.+?)\s+will have no deduction from the thlb",
                re.IGNORECASE,
            ),
        ),
        (
            "restore",
            re.compile(
                r"^(?P<subject>.+?)\s+.*fully restored to the thlb",
                re.IGNORECASE,
            ),
        ),
    )
    for action, pattern in patterns:
        match = pattern.search(normalized)
        if match:
            subject = _normalize_whitespace(match.groupdict().get("subject", ""))
            predicate = _normalize_whitespace(match.groupdict().get("predicate", ""))
            return action, subject, predicate

    if "long-term thlb" in lower:
        return "reference_target", "long-term thlb", _normalize_whitespace(normalized)
    if "the thlb is the portion" in lower:
        return "definition", "thlb definition", ""
    if "the thlb may increase in size" in lower:
        return "increase_conditions", "thlb increase conditions", ""
    if "the thlb may also decrease in size" in lower:
        return "decrease_conditions", "thlb decrease conditions", ""
    return "", "", ""


def _is_heading_like(text: str) -> bool:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return False
    return bool(
        re.match(r"^\d+(\.\d+)*\s", normalized)
        or "timber harvesting land base definition" in normalized.casefold()
        or "identification of the timber harvesting land base" in normalized.casefold()
    )


def _classify_thlb_recipe_step(
    row: TsrFactReviewRow,
    *,
    documents_index: dict[str, dict[str, Any]],
    source_index: tuple[dict[str, Any], ...],
) -> dict[str, Any] | None:
    snippet = _normalize_whitespace(row.snippet)
    value = _normalize_whitespace(row.extracted_value)
    if not snippet:
        return None

    action, subject, predicate = _match_thlb_action(value if value else snippet)
    document_path = _provenance_document_path(row.provenance_id)
    document_record = documents_index.get(document_path, {})
    document_title = row.title or str(document_record.get("title", ""))
    document_type = str(document_record.get("document_type", "")).strip()

    if action == "reference_target":
        step_kind = "reference_target"
        label = "Long-term THLB reference"
    elif action in {"definition", "increase_conditions", "decrease_conditions"}:
        step_kind = "context"
        label = {
            "definition": "THLB definition",
            "increase_conditions": "THLB increase conditions",
            "decrease_conditions": "THLB decrease conditions",
        }[action]
    elif action:
        step_kind = "netdown_rule"
        label = subject or snippet[:80]
    elif _is_heading_like(snippet):
        step_kind = "context"
        label = snippet[:80]
        action = "section_heading"
    else:
        return None

    linked_source_entry_ids = _link_thlb_step_to_sources(
        " ".join(part for part in (label, snippet, subject, predicate) if part),
        source_index=source_index,
    )
    if step_kind == "context":
        step_status = "needs_review"
        required = False
    elif step_kind == "reference_target":
        step_status = "ready"
        required = True
    elif linked_source_entry_ids or action in {
        "use_land_base",
        "aspatial_reduction",
        "no_deduction",
        "restore",
    }:
        step_status = "ready"
        required = True
    else:
        step_status = "blocked_missing_source"
        required = True

    notes = []
    if not linked_source_entry_ids and step_kind == "netdown_rule":
        notes.append(
            "No source-layer recipe entry linked automatically; review or add an override."
        )

    return {
        "step_kind": step_kind,
        "label": _normalize_whitespace(label),
        "raw_value": value,
        "raw_text": snippet,
        "normalized_action": action,
        "normalized_subject": subject,
        "normalized_predicate": predicate,
        "linked_source_entry_ids": list(linked_source_entry_ids),
        "step_status": step_status,
        "required": required,
        "page_number": row.page_number,
        "document_title": document_title,
        "document_type": document_type,
        "cycle_label": row.cycle_label,
        "cycle_year": row.cycle_year,
        "provenance_id": row.provenance_id,
        "source_url": row.source_url,
        "notes": notes,
    }


def build_tsr_source_layers_recipe(
    *,
    recipe_path: Path,
    source_root: Path,
    limit: int = 5,
) -> TsrSourceLayersRecipeBuildResult:
    """Populate the source-layer recipe from TSR facts and current BCDC knowledge."""

    recipe = load_tsr_source_layers_recipe(recipe_path)
    source_root_resolved = source_root.expanduser().resolve()
    candidate_facts_path = _resolve_path_from_recipe(
        source_root_resolved, recipe.canonical_inputs.candidate_facts_path
    )
    instance_root = recipe_path.expanduser().resolve().parents[2]
    overrides_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_overrides_path
    )
    overlay_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.overlay_path
    )
    override_map = _load_override_map(overrides_path)
    overlay_attempt_map = _load_overlay_attempt_map(overlay_path)

    entries = []
    status_counts: Counter[str] = Counter()
    for row in _review_rows_for_recipe(
        candidate_facts_path,
        tsa_code=recipe.tsa.tsa_code,
    ):
        resolve_result = resolve_bcdc_candidates(row.recommended_query, limit=limit)
        entry = _build_source_recipe_entry(
            row,
            resolve_result=resolve_result,
            override_entry=override_map.get(row.recommended_query.casefold()),
            overlay_attempt=_overlay_attempt_for_row(
                row,
                resolve_result=resolve_result,
                overlay_attempt_map=overlay_attempt_map,
            ),
            instance_root=instance_root,
        )
        entries.append(entry)
        status_counts.update([entry["current_public_status"]])

    payload = recipe.to_dict()
    recipe_contract = dict(recipe.recipe_contract)
    recipe_contract["status"] = "built"
    recipe_contract["last_built_utc"] = datetime.now(UTC).isoformat()
    payload["recipe_contract"] = recipe_contract
    payload["entries"] = entries
    _write_recipe_yaml(recipe_path.expanduser().resolve(), payload)
    return TsrSourceLayersRecipeBuildResult(
        recipe_path=recipe_path.expanduser().resolve(),
        tsa=recipe.tsa,
        entry_count=len(entries),
        status_counts=dict(sorted(status_counts.items())),
    )


def build_tsr_thlb_netdown_recipe(
    *,
    recipe_path: Path,
    source_root: Path,
) -> TsrThlbNetdownRecipeBuildResult:
    """Populate the THLB netdown recipe from TSR facts and source-layer recipe state."""

    recipe = load_tsr_thlb_netdown_recipe(recipe_path)
    source_root_resolved = source_root.expanduser().resolve()
    candidate_facts_path = _resolve_path_from_recipe(
        source_root_resolved, recipe.canonical_inputs.candidate_facts_path
    )
    documents_path = _resolve_path_from_recipe(
        source_root_resolved, recipe.canonical_inputs.documents_path
    )
    instance_root = recipe_path.expanduser().resolve().parents[2]
    source_layer_recipe_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_recipe_path
    )
    source_recipe = load_tsr_source_layers_recipe(source_layer_recipe_path)
    source_index = _build_source_recipe_index(source_recipe)

    report_result = report_tsr_candidate_facts(
        candidate_facts_path=candidate_facts_path,
        tsa=recipe.tsa.tsa_code,
        fact_families=("thlb_reference",),
        limit=None,
    )
    documents_index, documents = _load_tsa_documents_for_recipe(
        documents_path,
        tsa_id=recipe.tsa.tsa_id,
    )
    selected_rows, selected_document_paths = _choose_preferred_thlb_documents(
        report_result.rows,
        documents_index=documents_index,
        documents=documents,
    )

    steps: list[dict[str, Any]] = []
    step_kind_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    seen_signatures: set[tuple[int, str, str]] = set()
    for order_index, row in enumerate(
        sorted(
            selected_rows,
            key=lambda item: (
                int(item.page_number or 0),
                str(item.provenance_id),
                str(item.extracted_value),
            ),
        ),
        start=1,
    ):
        classified = _classify_thlb_recipe_step(
            row,
            documents_index=documents_index,
            source_index=source_index,
        )
        if classified is None:
            continue
        signature = (
            int(classified.get("page_number") or 0),
            str(classified["step_kind"]),
            str(classified["raw_text"]),
        )
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        slug = _normalize_step_slug(
            str(classified["label"] or classified["normalized_action"])
        )
        step_id = f"thlb_step_{order_index:03d}_{slug}"
        classified["step_id"] = step_id
        classified["order_index"] = order_index
        steps.append(classified)
        step_kind_counts.update([str(classified["step_kind"])])
        status_counts.update([str(classified["step_status"])])

    payload = recipe.to_dict()
    recipe_contract = dict(recipe.recipe_contract)
    recipe_contract["status"] = "built"
    recipe_contract["last_built_utc"] = datetime.now(UTC).isoformat()
    recipe_contract["selected_document_paths"] = list(selected_document_paths)
    payload["recipe_contract"] = recipe_contract
    payload["steps"] = steps
    _write_recipe_yaml(recipe_path.expanduser().resolve(), payload)
    return TsrThlbNetdownRecipeBuildResult(
        recipe_path=recipe_path.expanduser().resolve(),
        tsa=recipe.tsa,
        step_count=len(steps),
        step_kind_counts=dict(sorted(step_kind_counts.items())),
        status_counts=dict(sorted(status_counts.items())),
        selected_document_paths=selected_document_paths,
    )


def _path_exists_under_instance(instance_root: Path, value: str) -> bool:
    if not value:
        return False
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = instance_root / candidate
    return candidate.expanduser().resolve().exists()


def run_tsr_source_layers_recipe(
    *,
    recipe_path: Path,
    bbox_epsg3005: tuple[float, float, float, float] | None = None,
    geomark: GeomarkBBox | None = None,
    limit: int = 5,
    allow_order: bool = False,
) -> TsrSourceLayersRecipeRunResult:
    """Execute safe source-layer acquisition steps from one recipe."""

    resolved_recipe_path = recipe_path.expanduser().resolve()
    recipe = load_tsr_source_layers_recipe(resolved_recipe_path)
    instance_root = resolved_recipe_path.parents[2]
    download_root = _resolve_instance_path(
        instance_root, recipe.instance_inputs.download_root
    )
    outcome_counts: Counter[str] = Counter()
    payload = recipe.to_dict()
    updated_entries: list[dict[str, Any]] = []

    needs_aoi = any(
        entry.get("acquisition_strategy") in {"wfs_fetch", "dwds_order"}
        for entry in recipe.entries
    )
    if needs_aoi and bbox_epsg3005 is None:
        raise TsrRecipeError(
            "Source-layer recipe execution needs an AOI for WFS/DWDS entries. "
            "Supply `--bbox` or `--geomark`."
        )

    for entry in recipe.entries:
        updated = dict(entry)
        strategy = str(entry.get("acquisition_strategy", ""))
        artifact_path = str(entry.get("artifact_path", ""))
        query = str(
            entry.get("acquisition_query") or entry.get("recommended_query", "")
        )
        override_kind = str(entry.get("override_kind", ""))

        if strategy == "override":
            if override_kind in {"local_path", "datalad_path", "replacement_layer"}:
                updated["run_status"] = "override_resolved"
            elif override_kind in {"dataset_url", "private", "unavailable"}:
                updated["run_status"] = "override_requires_manual_materialization"
            else:
                updated["run_status"] = "override_pending"
            outcome_counts.update([updated["run_status"]])
            updated_entries.append(updated)
            continue

        if artifact_path and _path_exists_under_instance(instance_root, artifact_path):
            updated["run_status"] = "reused"
            outcome_counts.update(["reused"])
            updated_entries.append(updated)
            continue

        if strategy == "manual_review_required":
            updated["run_status"] = "manual_review_required"
        elif strategy == "override_required":
            updated["run_status"] = "override_required"
        elif strategy == "wfs_fetch":
            assert bbox_epsg3005 is not None
            try:
                fetch_result = fetch_bcdc_wfs_data(
                    query,
                    destination_root=download_root,
                    bbox_epsg3005=bbox_epsg3005,
                    limit=limit,
                    geomark=geomark,
                    query_slug=str(
                        entry.get("recommended_query") or entry.get("entry_id") or query
                    ),
                )
                updated["artifact_path"] = str(
                    fetch_result.saved_path.relative_to(instance_root).as_posix()
                )
                updated["feature_count"] = fetch_result.feature_count
                updated["run_status"] = "fetched"
            except BcdcFetchError as exc:
                updated["run_status"] = "failed"
                updated["failure_message"] = str(exc)
        elif strategy == "direct_download":
            try:
                resolve_result = resolve_bcdc_candidates(query, limit=limit)
                download_result = download_direct_bcdc_resources(
                    resolve_result,
                    destination_root=download_root,
                    query_slug=str(
                        entry.get("recommended_query") or entry.get("entry_id") or query
                    ),
                )
                downloaded = download_result.downloaded
                if downloaded:
                    saved_path = downloaded[0].saved_path
                    updated["artifact_path"] = str(
                        saved_path.relative_to(instance_root).as_posix()
                    )
                    updated["run_status"] = "downloaded"
                else:
                    updated["run_status"] = "failed"
                    updated["failure_message"] = (
                        "Direct download returned no saved resources."
                    )
            except Exception as exc:  # pragma: no cover - network/runtime seam
                updated["run_status"] = "failed"
                updated["failure_message"] = str(exc)
        elif strategy == "dwds_order":
            if not allow_order:
                updated["run_status"] = "dwds_order_skipped"
            else:
                assert bbox_epsg3005 is not None
                try:
                    order_result = submit_bcdc_dwds_order(
                        query,
                        bbox_epsg3005=bbox_epsg3005,
                        limit=limit,
                        geomark=geomark,
                    )
                    updated["run_status"] = "ordered"
                    updated["order_id"] = order_result.order_id
                    updated["submission_status"] = order_result.submission_status
                except BcdcDwdsError as exc:
                    updated["run_status"] = "failed"
                    updated["failure_message"] = str(exc)
        else:
            updated["run_status"] = "blocked"

        outcome_counts.update([str(updated.get("run_status", "blocked"))])
        updated_entries.append(updated)

    recipe_contract = dict(recipe.recipe_contract)
    recipe_contract["last_run_utc"] = datetime.now(UTC).isoformat()
    recipe_contract["status"] = "run"
    payload["recipe_contract"] = recipe_contract
    payload["entries"] = updated_entries
    _write_recipe_yaml(resolved_recipe_path, payload)
    return TsrSourceLayersRecipeRunResult(
        recipe_path=resolved_recipe_path,
        tsa=recipe.tsa,
        entry_count=len(updated_entries),
        outcome_counts=dict(sorted(outcome_counts.items())),
    )


def _find_tsr_checkpoint_path(*, instance_root: Path, mode: str) -> Path:
    candidates = sorted(
        instance_root.expanduser()
        .resolve()
        .glob("data/ria_vri_vclr1p_checkpoint*.feather")
    )
    if not candidates:
        raise TsrRecipeError(
            "No stand checkpoint feather found under the instance data directory."
        )

    def _checkpoint_order(path: Path) -> int:
        match = re.search(r"checkpoint(\d+)", path.stem, flags=re.IGNORECASE)
        if match is None:
            return -1
        return int(match.group(1))

    if mode == "latest":
        return max(candidates, key=_checkpoint_order)
    if mode == "earliest":
        return min(candidates, key=_checkpoint_order)
    raise TsrRecipeError(f"Unsupported checkpoint lookup mode: {mode}")


def _load_checkpoint_geodataframe(path: Path) -> gpd.GeoDataFrame:
    try:
        checkpoint = gpd.read_feather(path)
    except Exception as exc:  # pragma: no cover - filesystem/runtime seam
        raise TsrRecipeError(f"Unable to read THLB checkpoint feather: {path}") from exc
    if "geometry" not in checkpoint.columns:
        raise TsrRecipeError(f"THLB checkpoint is missing a geometry column: {path}")
    checkpoint = checkpoint.copy()
    if checkpoint.crs is None:
        checkpoint = checkpoint.set_crs(BC_ALBERS_EPSG)
    else:
        checkpoint = checkpoint.to_crs(BC_ALBERS_EPSG)
    return checkpoint


def _normalize_checkpoint_thlb_fact(
    checkpoint: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, str]:
    normalized = checkpoint.copy()
    stand_area_sqm = normalized.geometry.area.astype(float)
    normalized["_stand_area_sqm"] = stand_area_sqm
    signal_source = "default_one"

    if "thlb_fact" in normalized.columns:
        thlb_fact = normalized["thlb_fact"].fillna(0).astype(float)
        signal_source = "thlb_fact"
    elif "thlb_raw" in normalized.columns:
        thlb_fact = normalized["thlb_raw"].fillna(0).astype(float)
        if float(thlb_fact.max()) > 1.0:
            thlb_fact = thlb_fact / 100.0
        signal_source = "thlb_raw"
    elif "thlb_area" in normalized.columns:
        area_ha = stand_area_sqm / 10000.0
        with_area = area_ha.where(area_ha > 0, other=1.0)
        thlb_fact = normalized["thlb_area"].fillna(0).astype(float) / with_area
        signal_source = "thlb_area"
    elif "thlb" in normalized.columns:
        thlb_fact = normalized["thlb"].fillna(0).astype(float)
        signal_source = "thlb"
    else:
        thlb_fact = stand_area_sqm.map(lambda _value: 1.0)

    normalized["thlb_fact"] = thlb_fact.clip(lower=0.0, upper=1.0)
    return normalized, signal_source


def _resolve_union_geometry(exclusion_geometries: gpd.GeoDataFrame) -> Any | None:
    if exclusion_geometries.empty:
        return None
    series = exclusion_geometries.geometry
    if hasattr(series, "union_all"):
        return series.union_all()
    return series.unary_union


def _update_geometry_measure_columns(checkpoint: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    updated = checkpoint.copy()
    area_sqm = updated.geometry.area.astype(float)
    length_m = updated.geometry.length.astype(float)
    if "FEATURE_AREA_SQM" in updated.columns:
        updated["FEATURE_AREA_SQM"] = area_sqm
    if "POLYGON_AREA" in updated.columns:
        updated["POLYGON_AREA"] = area_sqm / 10000.0
    if "GEOMETRY_AREA" in updated.columns:
        updated["GEOMETRY_AREA"] = area_sqm / 10000.0
    if "Shape_Area" in updated.columns:
        updated["Shape_Area"] = area_sqm
    if "FEATURE_LENGTH_M" in updated.columns:
        updated["FEATURE_LENGTH_M"] = length_m
    if "Shape_Length" in updated.columns:
        updated["Shape_Length"] = length_m
    return updated


def _initialize_reconstructed_land_base(
    checkpoint: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, str]:
    reconstructed = checkpoint.copy()
    if "FOR_MGMT_LAND_BASE_IND" in reconstructed.columns:
        indicator = (
            reconstructed["FOR_MGMT_LAND_BASE_IND"]
            .fillna("N")
            .astype(str)
            .str.strip()
            .str.upper()
        )
        thlb_binary = indicator.eq("Y").astype(float)
        signal_source = "FOR_MGMT_LAND_BASE_IND_a_flb_proxy"
    else:
        thlb_binary = reconstructed.geometry.map(lambda _value: 1.0).astype(float)
        signal_source = "default_one"
    if (
        "FEATURE_ID" in reconstructed.columns
        and "SOURCE_FEATURE_ID" not in reconstructed.columns
    ):
        reconstructed["SOURCE_FEATURE_ID"] = reconstructed["FEATURE_ID"]
    reconstructed["thlb_fact"] = thlb_binary
    reconstructed["thlb"] = thlb_binary.astype(int)
    reconstructed = _update_geometry_measure_columns(reconstructed)
    reconstructed["_row_id"] = range(len(reconstructed))
    reconstructed["_stand_area_sqm"] = reconstructed.geometry.area.astype(float)
    return reconstructed, signal_source


def _assign_fragment_feature_ids(checkpoint: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    updated = checkpoint.copy().reset_index(drop=True)
    updated["_row_id"] = range(len(updated))
    if "FEATURE_ID" in updated.columns:
        updated["FEATURE_ID"] = updated.index + 1
    updated = _update_geometry_measure_columns(updated)
    updated["_stand_area_sqm"] = updated.geometry.area.astype(float)
    return updated


def _fragment_binary_exclusion_step(
    *,
    checkpoint: gpd.GeoDataFrame,
    exclusion_geometries: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, int, float]:
    if checkpoint.empty or exclusion_geometries.empty:
        return checkpoint, 0, 0.0
    active = checkpoint.loc[checkpoint["thlb_fact"] > 0].copy()
    if active.empty:
        return checkpoint, 0, 0.0
    candidate_indices = active.sindex.query(
        exclusion_geometries.geometry,
        predicate="intersects",
    )
    if getattr(candidate_indices, "ndim", 1) == 2:
        candidate_values = candidate_indices[1]
    else:
        candidate_values = candidate_indices
    unique_indices = sorted({int(index) for index in candidate_values.tolist()})
    if not unique_indices:
        return checkpoint, 0, 0.0
    candidate = active.iloc[unique_indices].copy()
    mask_geometry = _resolve_union_geometry(exclusion_geometries)
    if mask_geometry is None or getattr(mask_geometry, "is_empty", False):
        return checkpoint, 0, 0.0

    untouched = checkpoint.drop(candidate.index).copy()
    mask_frame = gpd.GeoDataFrame(geometry=[mask_geometry], crs=BC_ALBERS_EPSG)
    intersections = gpd.overlay(
        candidate,
        mask_frame,
        how="intersection",
        keep_geom_type=False,
    )
    if intersections.empty:
        return checkpoint, 0, 0.0
    differences = gpd.overlay(
        candidate,
        mask_frame,
        how="difference",
        keep_geom_type=False,
    )

    intersections = intersections.copy()
    intersections["thlb_fact"] = 0.0
    intersections["thlb"] = 0
    if "FOR_MGMT_LAND_BASE_IND" in intersections.columns:
        intersections["FOR_MGMT_LAND_BASE_IND"] = "N"

    if not differences.empty:
        differences = differences.copy()
        differences["thlb_fact"] = 1.0
        differences["thlb"] = 1

    affected_area_ha = float(intersections.geometry.area.sum() / 10000.0)
    affected_fragment_count = int(len(intersections))
    rebuilt = gpd.GeoDataFrame(
        pd.concat([untouched, differences, intersections], ignore_index=True),
        crs=BC_ALBERS_EPSG,
    )
    rebuilt = rebuilt.loc[~rebuilt.geometry.is_empty].copy()
    rebuilt = _assign_fragment_feature_ids(rebuilt)
    return rebuilt, affected_fragment_count, affected_area_ha


def _apply_binary_stand_exclusion(
    *,
    checkpoint: gpd.GeoDataFrame,
    exclusion_geometries: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, int, float, float]:
    if checkpoint.empty or exclusion_geometries.empty:
        return checkpoint, 0, 0.0, 0.0
    active = checkpoint.loc[checkpoint["thlb_fact"] > 0].copy()
    if active.empty:
        return checkpoint, 0, 0.0, 0.0
    candidate_indices = active.sindex.query(
        exclusion_geometries.geometry,
        predicate="intersects",
    )
    if getattr(candidate_indices, "ndim", 1) == 2:
        candidate_values = candidate_indices[1]
    else:
        candidate_values = candidate_indices
    unique_indices = sorted({int(index) for index in candidate_values.tolist()})
    if not unique_indices:
        return checkpoint, 0, 0.0, 0.0
    candidate = active.iloc[unique_indices].copy()
    mask_geometry = _resolve_union_geometry(exclusion_geometries)
    if mask_geometry is None or getattr(mask_geometry, "is_empty", False):
        return checkpoint, 0, 0.0, 0.0
    representative = candidate.geometry.representative_point()
    selected_row_ids = candidate.loc[
        representative.intersects(mask_geometry), "_row_id"
    ]
    if selected_row_ids.empty:
        return checkpoint, 0, 0.0, 0.0
    exclude_mask = checkpoint["_row_id"].isin(selected_row_ids.tolist())
    updated = checkpoint.copy()
    updated.loc[exclude_mask, "thlb_fact"] = 0.0
    updated.loc[exclude_mask, "thlb"] = 0
    affected_area_ha = float(
        updated.loc[exclude_mask, "_stand_area_sqm"].sum() / 10000.0
    )
    overlap_area_ha = affected_area_ha
    return updated, int(exclude_mask.sum()), affected_area_ha, overlap_area_ha


def _compute_legacy_reference_managed_area_ha(
    *,
    instance_root: Path,
    checkpoint_path: Path,
) -> float | None:
    latest_checkpoint = _find_tsr_checkpoint_path(
        instance_root=instance_root, mode="latest"
    )
    if latest_checkpoint == checkpoint_path:
        return None
    comparison = _load_checkpoint_geodataframe(latest_checkpoint)
    if not {"thlb_fact", "thlb_raw", "thlb_area", "thlb"}.intersection(
        comparison.columns
    ):
        return None
    comparison["_row_id"] = range(len(comparison))
    comparison, _signal_source = _normalize_checkpoint_thlb_fact(comparison)
    return _managed_area_ha(comparison)


def _extract_tsr_reported_thlb_area_ha(
    *,
    instance_root: Path,
    recipe: TsrThlbNetdownRecipeRecord,
) -> float | None:
    selected_paths = tuple(
        str(path).strip()
        for path in recipe.recipe_contract.get("selected_document_paths", ())
        if str(path).strip()
    )
    if not selected_paths:
        return None
    try:
        from pypdf import PdfReader
    except Exception:  # pragma: no cover - dependency seam
        return None
    from femic.user_config import default_femic_tsr_corpus_root

    corpus_root = default_femic_tsr_corpus_root()
    target_document = corpus_root / "tsa" / recipe.tsa.tsa_id / Path(selected_paths[0])
    if not target_document.exists():
        return None
    try:
        reader = PdfReader(str(target_document))
    except Exception:  # pragma: no cover - runtime seam
        return None

    pattern = re.compile(
        r"Timber harvesting land\s+base\s+([\d,]+)|Long-term THLB\s+([\d,]+)",
        flags=re.IGNORECASE,
    )
    timber_harvesting_land_base: float | None = None
    long_term_thlb: float | None = None
    for page in reader.pages:
        text = page.extract_text() or ""
        for match in pattern.finditer(text):
            timber_value = match.group(1)
            long_term_value = match.group(2)
            if timber_value:
                timber_harvesting_land_base = float(timber_value.replace(",", ""))
            if long_term_value:
                long_term_thlb = float(long_term_value.replace(",", ""))
    return long_term_thlb or timber_harvesting_land_base


def _load_source_recipe_entry_map(
    source_recipe: TsrSourceLayersRecipeRecord,
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entry in source_recipe.entries:
        entry_id = str(entry.get("entry_id", "")).strip()
        if entry_id:
            index[entry_id] = dict(entry)
    return index


def _resolve_source_artifact_path(
    *,
    instance_root: Path,
    source_entry: dict[str, Any],
) -> Path | None:
    artifact_path = str(source_entry.get("artifact_path", "")).strip()
    if not artifact_path:
        return None
    candidate = instance_root / artifact_path
    resolved = candidate.expanduser().resolve()
    if not resolved.exists():
        return None
    return resolved


def _load_exclusion_geometries(
    *,
    instance_root: Path,
    linked_source_entry_ids: tuple[str, ...],
    source_entry_map: dict[str, dict[str, Any]],
) -> tuple[gpd.GeoDataFrame | None, list[str]]:
    frames: list[gpd.GeoDataFrame] = []
    missing_sources: list[str] = []
    for entry_id in linked_source_entry_ids:
        source_entry = source_entry_map.get(entry_id)
        if source_entry is None:
            missing_sources.append(entry_id)
            continue
        artifact_path = _resolve_source_artifact_path(
            instance_root=instance_root,
            source_entry=source_entry,
        )
        if artifact_path is None:
            missing_sources.append(entry_id)
            continue
        try:
            layer = gpd.read_file(artifact_path)
        except Exception:  # pragma: no cover - runtime seam
            missing_sources.append(entry_id)
            continue
        if layer.empty or "geometry" not in layer.columns:
            missing_sources.append(entry_id)
            continue
        layer = layer.copy()
        if layer.crs is None:
            layer = layer.set_crs(BC_ALBERS_EPSG)
        else:
            layer = layer.to_crs(BC_ALBERS_EPSG)
        layer = layer[["geometry"]].dropna(subset=["geometry"])
        layer = layer.loc[~layer.geometry.is_empty]
        layer = layer.loc[layer.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
        if layer.empty:
            missing_sources.append(entry_id)
            continue
        frames.append(layer)
    if not frames:
        return None, missing_sources
    merged = gpd.GeoDataFrame(
        geometry=gpd.GeoSeries(
            [geom for frame in frames for geom in frame.geometry],
            crs=BC_ALBERS_EPSG,
        ),
        crs=BC_ALBERS_EPSG,
    )
    return merged, missing_sources


def _compute_exclusion_fraction(
    *,
    checkpoint: gpd.GeoDataFrame,
    exclusion_geometries: gpd.GeoDataFrame,
) -> dict[int, float]:
    if checkpoint.empty or exclusion_geometries.empty:
        return {}
    candidate_indices = checkpoint.sindex.query(
        exclusion_geometries.geometry, predicate="intersects"
    )
    if getattr(candidate_indices, "ndim", 1) == 2:
        candidate_values = candidate_indices[1]
    else:
        candidate_values = candidate_indices
    unique_indices = sorted({int(index) for index in candidate_values.tolist()})
    if not unique_indices:
        return {}
    candidate = checkpoint.iloc[unique_indices][
        ["_row_id", "_stand_area_sqm", "geometry"]
    ].copy()
    intersections = gpd.overlay(
        candidate[["_row_id", "geometry"]],
        exclusion_geometries[["geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    if intersections.empty:
        return {}
    intersection_area = intersections.geometry.area.groupby(
        intersections["_row_id"]
    ).sum()
    stand_area = candidate.set_index("_row_id")["_stand_area_sqm"].reindex(
        intersection_area.index
    )
    fraction = (intersection_area / stand_area).clip(lower=0.0, upper=1.0)
    return {int(key): float(value) for key, value in fraction.items()}


def _count_exclusion_candidate_rows(
    *,
    checkpoint: gpd.GeoDataFrame,
    exclusion_geometries: gpd.GeoDataFrame,
) -> int:
    if checkpoint.empty or exclusion_geometries.empty:
        return 0
    candidate_indices = checkpoint.sindex.query(
        exclusion_geometries.geometry,
        predicate="intersects",
    )
    if getattr(candidate_indices, "ndim", 1) == 2:
        candidate_values = candidate_indices[1]
    else:
        candidate_values = candidate_indices
    return len({int(index) for index in candidate_values.tolist()})


def _managed_area_ha(checkpoint: gpd.GeoDataFrame) -> float:
    return float(
        (checkpoint["_stand_area_sqm"] * checkpoint["thlb_fact"]).sum() / 10000.0
    )


def run_tsr_thlb_netdown_recipe(
    *,
    recipe_path: Path,
    checkpoint_path: Path | None = None,
    output_path: Path | None = None,
    audit_path: Path | None = None,
    execution_mode: str = TSR_THLB_EXECUTION_MODE_HYBRID,
) -> TsrThlbNetdownRecipeRunResult:
    """Execute a THLB netdown recipe into either a hybrid or reconstructed checkpoint."""

    resolved_recipe_path = recipe_path.expanduser().resolve()
    recipe = load_tsr_thlb_netdown_recipe(resolved_recipe_path)
    instance_root = resolved_recipe_path.parents[2]
    if execution_mode not in _TSR_THLB_EXECUTION_MODES:
        raise TsrRecipeError(
            "Unsupported THLB execution mode: "
            f"{execution_mode}. Expected one of {sorted(_TSR_THLB_EXECUTION_MODES)}."
        )
    source_layer_recipe_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_recipe_path
    )
    source_recipe = load_tsr_source_layers_recipe(source_layer_recipe_path)
    source_entry_map = _load_source_recipe_entry_map(source_recipe)

    resolved_checkpoint_path = (
        checkpoint_path.expanduser().resolve()
        if checkpoint_path is not None
        else _find_tsr_checkpoint_path(
            instance_root=instance_root,
            mode=(
                "earliest"
                if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
                else "latest"
            ),
        )
    )
    resolved_output_path = (
        output_path.expanduser().resolve()
        if output_path is not None
        else (
            default_tsr_thlb_reconstructed_output_path(instance_root=instance_root)
            if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
            else default_tsr_thlb_netdown_output_path(instance_root=instance_root)
        )
    )
    resolved_audit_path = (
        audit_path.expanduser().resolve()
        if audit_path is not None
        else (
            default_tsr_thlb_reconstructed_audit_path(instance_root=instance_root)
            if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
            else default_tsr_thlb_netdown_audit_path(instance_root=instance_root)
        )
    )

    checkpoint = _load_checkpoint_geodataframe(resolved_checkpoint_path)
    if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
        checkpoint, baseline_signal = _initialize_reconstructed_land_base(checkpoint)
    else:
        checkpoint["_row_id"] = range(len(checkpoint))
        checkpoint, baseline_signal = _normalize_checkpoint_thlb_fact(checkpoint)
    baseline_managed_area_ha = _managed_area_ha(checkpoint)
    legacy_reference_managed_area_ha = _compute_legacy_reference_managed_area_ha(
        instance_root=instance_root,
        checkpoint_path=resolved_checkpoint_path,
    )
    tsr_reported_thlb_area_ha = _extract_tsr_reported_thlb_area_ha(
        instance_root=instance_root,
        recipe=recipe,
    )

    outcome_counts: Counter[str] = Counter()
    applied_steps: list[dict[str, Any]] = []

    for step in recipe.steps:
        updated_step = dict(step)
        normalized_action = str(step.get("normalized_action", "")).strip()
        linked_source_entry_ids = tuple(
            str(value).strip()
            for value in step.get("linked_source_entry_ids", ())
            if str(value).strip()
        )
        page_number = int(step.get("page_number") or 0)

        if normalized_action in {
            "section_heading",
            "definition",
            "increase_conditions",
            "decrease_conditions",
        }:
            updated_step["run_status"] = "needs_review"
            updated_step["run_notes"] = [
                "Context-only THLB row; no execution attempted."
            ]
        elif normalized_action in {"use_land_base", "no_deduction"}:
            updated_step["run_status"] = "applied_noop"
            updated_step["run_notes"] = ["No spatial deduction applied for this rule."]
        elif normalized_action == "exclude":
            exclusion_geometries, missing_sources = _load_exclusion_geometries(
                instance_root=instance_root,
                linked_source_entry_ids=linked_source_entry_ids,
                source_entry_map=source_entry_map,
            )
            if exclusion_geometries is None:
                updated_step["run_status"] = "blocked_missing_source"
                updated_step["run_notes"] = [
                    "No fetched polygon artifact was available for the linked source entries."
                ]
                if missing_sources:
                    updated_step["missing_source_entry_ids"] = missing_sources
            else:
                if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
                    candidate_count = _count_exclusion_candidate_rows(
                        checkpoint=checkpoint,
                        exclusion_geometries=exclusion_geometries,
                    )
                    if candidate_count == 0:
                        updated_step["run_status"] = "applied_noop"
                        updated_step["run_notes"] = [
                            "No active land-base geometries intersected the exclusion mask."
                        ]
                    elif candidate_count > _RECONSTRUCTED_FRAGMENT_ROW_THRESHOLD:
                        (
                            checkpoint,
                            affected_stand_count,
                            affected_area_ha,
                            overlap_area_ha,
                        ) = _apply_binary_stand_exclusion(
                            checkpoint=checkpoint,
                            exclusion_geometries=exclusion_geometries,
                        )
                        if affected_stand_count == 0:
                            updated_step["run_status"] = "applied_noop"
                            updated_step["run_notes"] = [
                                "Candidate rows were found, but none exceeded the stand-binary exclusion threshold."
                            ]
                        else:
                            updated_step["run_status"] = "applied"
                            updated_step["spatial_application_mode"] = (
                                "stand_binary_majority"
                            )
                            updated_step["candidate_row_count"] = candidate_count
                            updated_step["affected_stand_count"] = affected_stand_count
                            updated_step["affected_area_ha"] = affected_area_ha
                            updated_step["overlap_area_ha"] = overlap_area_ha
                            updated_step["run_notes"] = [
                                "Applied reconstructed stand-binary exclusion because the intersecting coarse-polygon workload exceeded the fragment overlay threshold.",
                                "Representative-point containment was used as the coarse-polygon stand-binary approximation.",
                            ]
                    else:
                        (
                            checkpoint,
                            affected_fragment_count,
                            affected_area_ha,
                        ) = _fragment_binary_exclusion_step(
                            checkpoint=checkpoint,
                            exclusion_geometries=exclusion_geometries,
                        )
                        if affected_fragment_count == 0:
                            updated_step["run_status"] = "applied_noop"
                            updated_step["run_notes"] = [
                                "No active fragment geometries intersected the exclusion mask."
                            ]
                        else:
                            updated_step["run_status"] = "applied"
                            updated_step["spatial_application_mode"] = (
                                "fragment_overlay"
                            )
                            updated_step["candidate_row_count"] = candidate_count
                            updated_step["affected_fragment_count"] = (
                                affected_fragment_count
                            )
                            updated_step["affected_area_ha"] = affected_area_ha
                            updated_step["run_notes"] = [
                                "Applied fragment/resultant exclusion with binary THLB output in EPSG:3005."
                            ]
                else:
                    exclusion_fraction = _compute_exclusion_fraction(
                        checkpoint=checkpoint,
                        exclusion_geometries=exclusion_geometries,
                    )
                    if not exclusion_fraction:
                        updated_step["run_status"] = "applied_noop"
                        updated_step["run_notes"] = [
                            "No stand geometries intersected the exclusion mask."
                        ]
                    else:
                        ratios = (
                            checkpoint["_row_id"].map(exclusion_fraction).fillna(0.0)
                        )
                        checkpoint["thlb_fact"] = (
                            checkpoint["thlb_fact"] - ratios
                        ).clip(lower=0.0, upper=1.0)
                        updated_step["run_status"] = "applied"
                        updated_step["affected_stand_count"] = int((ratios > 0).sum())
                        updated_step["affected_area_ha"] = float(
                            (
                                checkpoint["_stand_area_sqm"]
                                * ratios.clip(lower=0.0, upper=1.0)
                            ).sum()
                            / 10000.0
                        )
                        updated_step["run_notes"] = [
                            "Applied stand-level exclusion using overlap fractions in EPSG:3005.",
                            "Sequential stand-level subtraction may approximate overlapping exclusion masks.",
                        ]
                if missing_sources:
                    updated_step["missing_source_entry_ids"] = missing_sources
        elif normalized_action == "aspatial_reduction":
            updated_step["run_status"] = "unsupported"
            updated_step["run_notes"] = [
                "Aspatial reduction steps are preserved for review but not executed in v1."
            ]
        else:
            updated_step["run_status"] = "unsupported"
            updated_step["run_notes"] = [
                f"Normalized action `{normalized_action or 'unknown'}` is not executable in v1."
            ]

        updated_step["page_number"] = page_number
        applied_steps.append(updated_step)
        outcome_counts.update([str(updated_step.get("run_status", "unsupported"))])

    final_managed_area_ha = _managed_area_ha(checkpoint)
    if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
        checkpoint["thlb_fact"] = checkpoint["thlb_fact"].fillna(0.0).clip(0.0, 1.0)
        checkpoint["thlb"] = checkpoint["thlb_fact"].round().astype(int)
        checkpoint["thlb_raw"] = checkpoint["thlb_fact"]
        checkpoint["thlb_area"] = (
            checkpoint["_stand_area_sqm"] * checkpoint["thlb_fact"] / 10000.0
        )
    checkpoint = _update_geometry_measure_columns(checkpoint)

    payload = recipe.to_dict()
    recipe_contract = dict(recipe.recipe_contract)
    recipe_contract["status"] = "run"
    recipe_contract["last_run_utc"] = datetime.now(UTC).isoformat()
    recipe_contract["selected_checkpoint_path"] = str(
        resolved_checkpoint_path.relative_to(instance_root).as_posix()
    )
    output_contract_key = (
        "reconstructed_output_checkpoint_path"
        if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
        else "output_checkpoint_path"
    )
    audit_contract_key = (
        "reconstructed_audit_path"
        if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
        else "audit_path"
    )
    recipe_contract[output_contract_key] = str(
        resolved_output_path.relative_to(instance_root).as_posix()
    )
    recipe_contract[audit_contract_key] = str(
        resolved_audit_path.relative_to(instance_root).as_posix()
    )
    payload["recipe_contract"] = recipe_contract
    payload["steps"] = applied_steps
    _write_recipe_yaml(resolved_recipe_path, payload)

    output_frame = checkpoint.drop(
        columns=["_row_id", "_stand_area_sqm"], errors="ignore"
    )
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    output_frame.to_feather(resolved_output_path)

    audit_payload = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "tsa": recipe.tsa.to_dict(),
        "recipe_path": str(resolved_recipe_path.relative_to(instance_root).as_posix()),
        "checkpoint_path": str(
            resolved_checkpoint_path.relative_to(instance_root).as_posix()
        ),
        "output_path": str(resolved_output_path.relative_to(instance_root).as_posix()),
        "execution_mode": execution_mode,
        "baseline_signal": baseline_signal,
        "baseline_managed_area_ha": baseline_managed_area_ha,
        "final_managed_area_ha": final_managed_area_ha,
        "legacy_reference_managed_area_ha": legacy_reference_managed_area_ha,
        "tsr_reported_thlb_area_ha": tsr_reported_thlb_area_ha,
        "step_count": len(applied_steps),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "steps": applied_steps,
    }
    resolved_audit_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_audit_path.write_text(
        json.dumps(audit_payload, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    return TsrThlbNetdownRecipeRunResult(
        recipe_path=resolved_recipe_path,
        tsa=recipe.tsa,
        checkpoint_path=resolved_checkpoint_path,
        output_path=resolved_output_path,
        audit_path=resolved_audit_path,
        execution_mode=execution_mode,
        baseline_signal=baseline_signal,
        step_count=len(applied_steps),
        outcome_counts=dict(sorted(outcome_counts.items())),
        baseline_managed_area_ha=baseline_managed_area_ha,
        final_managed_area_ha=final_managed_area_ha,
        legacy_reference_managed_area_ha=legacy_reference_managed_area_ha,
        tsr_reported_thlb_area_ha=tsr_reported_thlb_area_ha,
    )
