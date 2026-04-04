"""Instance-local TSR source-layer override helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from femic.bcdc_catalog import (
    BcdcCatalogError,
    BcdcReplacementFamilyCandidate,
    suggest_bcdc_replacement_family,
)

from .overlay import TsrOverlayError, TsrOverlayTsaRecord


class TsrSourceLayerOverridesError(RuntimeError):
    """Raised when TSR source-layer override initialization or reporting fails."""


ALLOWED_OVERRIDE_KINDS: tuple[str, ...] = (
    "local_path",
    "dataset_url",
    "datalad_path",
    "replacement_layer",
    "private",
    "unavailable",
)
DEFAULT_OVERRIDE_OUTCOMES: tuple[str, ...] = ("no_catalog_match", "failed")


@dataclass(frozen=True)
class TsrSourceLayerOverrideEntry:
    """One unresolved TSR source-layer row plus any reviewed user override."""

    query: str
    current_public_status: str
    matched_by: str
    top_match_title: str
    dataset_page_url: str
    suggested_fetch_strategy: str
    current_public_notes: tuple[str, ...]
    replacement_family_candidates: tuple[BcdcReplacementFamilyCandidate, ...] = ()
    override_kind: str | None = None
    override_value: str | None = None
    notes: str | None = None

    @property
    def is_resolved(self) -> bool:
        return bool(self.override_kind)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "query": self.query,
            "current_public_status": self.current_public_status,
            "matched_by": self.matched_by,
            "top_match_title": self.top_match_title,
            "dataset_page_url": self.dataset_page_url,
            "suggested_fetch_strategy": self.suggested_fetch_strategy,
            "current_public_notes": list(self.current_public_notes),
            "replacement_family_candidates": [
                candidate.to_dict() for candidate in self.replacement_family_candidates
            ],
            "override_kind": self.override_kind or "",
            "override_value": self.override_value or "",
            "notes": self.notes or "",
        }
        return payload


@dataclass(frozen=True)
class TsrSourceLayerOverridesRecord:
    """User-maintained instance-local source-layer overrides."""

    schema_version: int
    tsa: TsrOverlayTsaRecord
    source_overlay_path: str
    entries: tuple[TsrSourceLayerOverrideEntry, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "tsa": self.tsa.to_dict(),
            "source_overlay_path": self.source_overlay_path,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class TsrSourceLayerOverridesInitResult:
    """Result payload for source-layer override initialization."""

    overrides_path: Path
    overlay_path: Path
    tsa: TsrOverlayTsaRecord
    entry_count: int
    created: bool


@dataclass(frozen=True)
class TsrSourceLayerOverridesReport:
    """Summary of user-supplied source-layer override coverage."""

    overrides_path: Path
    overlay_path: Path
    tsa: TsrOverlayTsaRecord
    total_entries: int
    resolved_entries: int
    pending_entries: int
    entries_with_suggestions: int
    total_suggestion_candidates: int
    unresolved_overlay_queries: tuple[str, ...]
    override_kind_counts: dict[str, int]


def _read_yaml_object(path: Path, *, description: str) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrSourceLayerOverridesError(f"{description} not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrSourceLayerOverridesError(
            f"Invalid {description.lower()} payload: {resolved}"
        )
    return payload


def _load_overlay_payload(path: Path) -> dict[str, Any]:
    try:
        return _read_yaml_object(path, description="TSR overlay")
    except TsrSourceLayerOverridesError as exc:
        raise TsrOverlayError(str(exc)) from exc


def _normalize_notes(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(" | ")]
        return tuple(part for part in parts if part)
    return ()


def _extract_overlay_tsa(payload: dict[str, Any], *, path: Path) -> TsrOverlayTsaRecord:
    tsa_payload = payload.get("tsa")
    if not isinstance(tsa_payload, dict):
        raise TsrSourceLayerOverridesError(f"Invalid TSR overlay structure: {path}")
    return TsrOverlayTsaRecord(
        tsa_id=str(tsa_payload.get("tsa_id", "")),
        tsa_code=str(tsa_payload.get("tsa_code", "")),
        tsa_name=str(tsa_payload.get("tsa_name", "")),
    )


def _overlay_unresolved_entries(
    payload: dict[str, Any],
    *,
    outcomes: tuple[str, ...],
) -> tuple[TsrSourceLayerOverrideEntry, ...]:
    review_payload = payload.get("bcdc_acquisition_review")
    if not isinstance(review_payload, dict):
        return ()
    attempts = review_payload.get("attempts", [])
    if not isinstance(attempts, list):
        return ()

    normalized_outcomes = {item.casefold() for item in outcomes}
    entries: list[TsrSourceLayerOverrideEntry] = []
    seen: set[str] = set()
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        query = str(attempt.get("query", "")).strip()
        outcome = str(attempt.get("acquisition_outcome", "")).strip()
        if not query or outcome.casefold() not in normalized_outcomes:
            continue
        normalized_query = query.casefold()
        if normalized_query in seen:
            continue
        seen.add(normalized_query)
        entries.append(
            TsrSourceLayerOverrideEntry(
                query=query,
                current_public_status=outcome,
                matched_by=str(attempt.get("matched_by", "")).strip(),
                top_match_title=str(attempt.get("top_match_title", "")).strip(),
                dataset_page_url=str(attempt.get("dataset_page_url", "")).strip(),
                suggested_fetch_strategy=str(
                    attempt.get("suggested_fetch_strategy", "")
                ).strip(),
                current_public_notes=_normalize_notes(attempt.get("notes")),
                replacement_family_candidates=_suggest_replacement_family_candidates(
                    query
                ),
            )
        )
    return tuple(entries)


def _suggest_replacement_family_candidates(
    query: str,
) -> tuple[BcdcReplacementFamilyCandidate, ...]:
    try:
        return suggest_bcdc_replacement_family(query, limit=3)
    except (BcdcCatalogError, OSError, ValueError):
        return ()


def default_tsr_source_layer_overrides_path(*, instance_root: Path) -> Path:
    """Return the default per-instance source-layer override file path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "source_layer_overrides.yaml"
    )


def init_tsr_source_layer_overrides(
    *,
    instance_root: Path,
    overlay_path: Path,
    overrides_path: Path,
    include_outcomes: tuple[str, ...] = DEFAULT_OVERRIDE_OUTCOMES,
    overwrite: bool = False,
) -> TsrSourceLayerOverridesInitResult:
    """Initialize a per-instance source-layer override template from the TSR overlay."""

    resolved_instance_root = instance_root.expanduser().resolve()
    resolved_overlay_path = overlay_path.expanduser().resolve()
    resolved_overrides_path = overrides_path.expanduser().resolve()
    try:
        resolved_overlay_path.relative_to(resolved_instance_root)
        resolved_overrides_path.relative_to(resolved_instance_root)
    except ValueError as exc:
        raise TsrSourceLayerOverridesError(
            "TSR source-layer override paths must live under the instance root."
        ) from exc
    if resolved_overrides_path.exists() and not overwrite:
        raise TsrSourceLayerOverridesError(
            "TSR source-layer overrides already exist: "
            f"{resolved_overrides_path}. Use `--overwrite` to replace them."
        )

    overlay_payload = _load_overlay_payload(resolved_overlay_path)
    tsa_record = _extract_overlay_tsa(overlay_payload, path=resolved_overlay_path)
    entries = _overlay_unresolved_entries(
        overlay_payload,
        outcomes=include_outcomes,
    )
    record = TsrSourceLayerOverridesRecord(
        schema_version=1,
        tsa=tsa_record,
        source_overlay_path=str(
            resolved_overlay_path.relative_to(resolved_instance_root).as_posix()
        ),
        entries=entries,
    )
    resolved_overrides_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_overrides_path.write_text(
        yaml.safe_dump(
            record.to_dict(),
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    return TsrSourceLayerOverridesInitResult(
        overrides_path=resolved_overrides_path,
        overlay_path=resolved_overlay_path,
        tsa=tsa_record,
        entry_count=len(entries),
        created=True,
    )


def load_tsr_source_layer_overrides(path: Path) -> TsrSourceLayerOverridesRecord:
    """Load one instance-local TSR source-layer override YAML file."""

    resolved = path.expanduser().resolve()
    payload = _read_yaml_object(resolved, description="TSR source-layer overrides")
    tsa_payload = payload.get("tsa")
    entries_payload = payload.get("entries", [])
    if not isinstance(tsa_payload, dict) or not isinstance(entries_payload, list):
        raise TsrSourceLayerOverridesError(
            f"Invalid TSR source-layer overrides structure: {resolved}"
        )

    entries: list[TsrSourceLayerOverrideEntry] = []
    for raw in entries_payload:
        if not isinstance(raw, dict):
            continue
        override_kind = str(raw.get("override_kind", "")).strip() or None
        if override_kind is not None and override_kind not in ALLOWED_OVERRIDE_KINDS:
            raise TsrSourceLayerOverridesError(
                "Invalid TSR source-layer override kind "
                f"`{override_kind}` in {resolved}"
            )
        entries.append(
            TsrSourceLayerOverrideEntry(
                query=str(raw.get("query", "")).strip(),
                current_public_status=str(raw.get("current_public_status", "")).strip(),
                matched_by=str(raw.get("matched_by", "")).strip(),
                top_match_title=str(raw.get("top_match_title", "")).strip(),
                dataset_page_url=str(raw.get("dataset_page_url", "")).strip(),
                suggested_fetch_strategy=str(
                    raw.get("suggested_fetch_strategy", "")
                ).strip(),
                current_public_notes=_normalize_notes(raw.get("current_public_notes")),
                replacement_family_candidates=tuple(
                    BcdcReplacementFamilyCandidate(
                        title=str(item.get("title", "")).strip(),
                        dataset_page_url=str(item.get("dataset_page_url", "")).strip(),
                        object_names=tuple(
                            str(value).strip()
                            for value in item.get("object_names", [])
                            if str(value).strip()
                        ),
                        matched_query=str(item.get("matched_query", "")).strip(),
                        rationale=str(item.get("rationale", "")).strip(),
                    )
                    for item in raw.get("replacement_family_candidates", [])
                    if isinstance(item, dict)
                ),
                override_kind=override_kind,
                override_value=str(raw.get("override_value", "")).strip() or None,
                notes=str(raw.get("notes", "")).strip() or None,
            )
        )
    return TsrSourceLayerOverridesRecord(
        schema_version=int(payload.get("schema_version", 1)),
        tsa=TsrOverlayTsaRecord(
            tsa_id=str(tsa_payload.get("tsa_id", "")),
            tsa_code=str(tsa_payload.get("tsa_code", "")),
            tsa_name=str(tsa_payload.get("tsa_name", "")),
        ),
        source_overlay_path=str(payload.get("source_overlay_path", "")),
        entries=tuple(entries),
    )


def build_tsr_source_layer_override_report(
    *,
    overlay_path: Path,
    overrides_path: Path,
) -> TsrSourceLayerOverridesReport:
    """Summarize one source-layer override file against unresolved overlay rows."""

    resolved_overlay_path = overlay_path.expanduser().resolve()
    resolved_overrides_path = overrides_path.expanduser().resolve()
    overlay_payload = _load_overlay_payload(resolved_overlay_path)
    unresolved_overlay_entries = _overlay_unresolved_entries(
        overlay_payload,
        outcomes=DEFAULT_OVERRIDE_OUTCOMES,
    )
    overrides = load_tsr_source_layer_overrides(resolved_overrides_path)
    override_by_query = {
        entry.query.casefold(): entry
        for entry in overrides.entries
        if entry.query.strip()
    }
    unresolved_overlay_queries = tuple(
        entry.query
        for entry in unresolved_overlay_entries
        if not override_by_query.get(entry.query.casefold(), None)
        or not override_by_query[entry.query.casefold()].is_resolved
    )
    override_kind_counts = {kind: 0 for kind in ALLOWED_OVERRIDE_KINDS}
    resolved_entries = 0
    pending_entries = 0
    entries_with_suggestions = 0
    total_suggestion_candidates = 0
    for entry in overrides.entries:
        if entry.override_kind:
            resolved_entries += 1
            override_kind_counts[entry.override_kind] += 1
        else:
            pending_entries += 1
        if entry.replacement_family_candidates:
            entries_with_suggestions += 1
            total_suggestion_candidates += len(entry.replacement_family_candidates)
    override_kind_counts = {
        kind: count for kind, count in override_kind_counts.items() if count > 0
    }
    return TsrSourceLayerOverridesReport(
        overrides_path=resolved_overrides_path,
        overlay_path=resolved_overlay_path,
        tsa=overrides.tsa,
        total_entries=len(overrides.entries),
        resolved_entries=resolved_entries,
        pending_entries=pending_entries,
        entries_with_suggestions=entries_with_suggestions,
        total_suggestion_candidates=total_suggestion_candidates,
        unresolved_overlay_queries=unresolved_overlay_queries,
        override_kind_counts=override_kind_counts,
    )
