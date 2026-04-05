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

import yaml

from femic.bcdc_catalog import (
    INDIRECT_CUSTOM_DOWNLOAD,
    SERVICE,
    SUPPORTING_DOCUMENT,
    download_direct_bcdc_resources,
    resolve_bcdc_candidates,
)
from femic.bcdc_dwds import BcdcDwdsError, submit_bcdc_dwds_order
from femic.bcdc_fetch import BcdcFetchError, GeomarkBBox, fetch_bcdc_wfs_data

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
