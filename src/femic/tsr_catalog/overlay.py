"""Instance-local TSR reviewed overlay helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml


class TsrOverlayError(RuntimeError):
    """Raised when TSR overlay initialization or reporting fails."""


@dataclass(frozen=True)
class TsrOverlayTsaRecord:
    """Canonical TSA identity used by instance-local TSR overlays."""

    tsa_id: str
    tsa_code: str
    tsa_name: str

    def to_dict(self) -> dict[str, str]:
        return {
            "tsa_id": self.tsa_id,
            "tsa_code": self.tsa_code,
            "tsa_name": self.tsa_name,
        }


@dataclass(frozen=True)
class TsrOverlayCanonicalSummary:
    """Canonical candidate-fact summary surfaced into the reviewed overlay."""

    candidate_fact_count: int
    document_count: int
    fact_family_counts: dict[str, int]
    candidate_facts_path: str
    documents_path: str
    registry_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_fact_count": self.candidate_fact_count,
            "document_count": self.document_count,
            "fact_family_counts": dict(self.fact_family_counts),
            "candidate_facts_path": self.candidate_facts_path,
            "documents_path": self.documents_path,
            "registry_path": self.registry_path,
        }


@dataclass(frozen=True)
class TsrOverlayRecord:
    """Reviewed/adopted per-instance TSR overlay payload."""

    schema_version: int
    tsa: TsrOverlayTsaRecord
    canonical_summary: TsrOverlayCanonicalSummary
    adopted: dict[str, list[dict[str, Any]]]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "tsa": self.tsa.to_dict(),
            "canonical_summary": self.canonical_summary.to_dict(),
            "adopted": self.adopted,
        }


@dataclass(frozen=True)
class TsrOverlayInitResult:
    """Result payload for TSR overlay initialization."""

    overlay_path: Path
    tsa: TsrOverlayTsaRecord
    canonical_summary: TsrOverlayCanonicalSummary
    created: bool


@dataclass(frozen=True)
class TsrOverlayReport:
    """Comparison of canonical candidate facts vs adopted instance overlay state."""

    overlay_path: Path
    tsa: TsrOverlayTsaRecord
    canonical_summary: TsrOverlayCanonicalSummary
    adopted_counts: dict[str, int]


_ADOPTED_SECTION_KEYS: tuple[str, ...] = (
    "source_layers",
    "au_definitions",
    "thlb_references",
    "tipsy_inputs",
    "notes",
)
_FACT_FAMILY_TO_ADOPTED_KEY = {
    "source_layer_candidate": "source_layers",
    "au_definition_candidate": "au_definitions",
    "thlb_reference": "thlb_references",
    "tipsy_input_candidate": "tipsy_inputs",
}


def _load_json(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrOverlayError(f"Required TSR metadata artifact not found: {resolved}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrOverlayError(f"Expected JSON object at {resolved}")
    return payload


def _normalize_tsa_token(value: str) -> str:
    return value.strip().replace("_", " ").casefold()


def _resolve_tsa_record(
    *,
    tsa: str,
    registry_path: Path,
) -> TsrOverlayTsaRecord:
    payload = _load_json(registry_path)
    records = payload.get("tsas")
    if not isinstance(records, list):
        raise TsrOverlayError("TSR registry JSON is missing a valid `tsas` list.")
    normalized = _normalize_tsa_token(tsa)
    matches: list[TsrOverlayTsaRecord] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        record = TsrOverlayTsaRecord(
            tsa_id=str(item["tsa_id"]),
            tsa_code=str(item["tsa_code"]),
            tsa_name=str(item["tsa_name"]),
        )
        if normalized in {
            _normalize_tsa_token(record.tsa_id),
            _normalize_tsa_token(record.tsa_code),
            _normalize_tsa_token(record.tsa_code.lstrip("0") or record.tsa_code),
            _normalize_tsa_token(record.tsa_name),
        }:
            matches.append(record)
    if not matches:
        raise TsrOverlayError(f"No canonical TSR TSA match found for `{tsa}`.")
    if len(matches) > 1:
        labels = ", ".join(f"{record.tsa_code}:{record.tsa_name}" for record in matches)
        raise TsrOverlayError(f"Ambiguous TSR TSA match for `{tsa}`: {labels}")
    return matches[0]


def _canonical_summary_for_tsa(
    *,
    tsa_record: TsrOverlayTsaRecord,
    candidate_facts_path: Path,
    documents_path: Path,
    registry_path: Path,
    source_root: Path,
) -> TsrOverlayCanonicalSummary:
    candidate_payload = _load_json(candidate_facts_path)
    fact_items = candidate_payload.get("facts")
    if not isinstance(fact_items, list):
        raise TsrOverlayError(
            "TSR candidate-facts JSON is missing a valid `facts` list."
        )
    family_counts = {key: 0 for key in _FACT_FAMILY_TO_ADOPTED_KEY}
    candidate_fact_count = 0
    for item in fact_items:
        if not isinstance(item, dict):
            continue
        if str(item.get("tsa_id")) != tsa_record.tsa_id:
            continue
        fact_family = str(item.get("fact_family", ""))
        if fact_family not in family_counts:
            continue
        family_counts[fact_family] += 1
        candidate_fact_count += 1

    documents_payload = _load_json(documents_path)
    document_items = documents_payload.get("documents")
    if not isinstance(document_items, list):
        raise TsrOverlayError("TSR documents JSON is missing a valid `documents` list.")
    document_count = sum(
        1
        for item in document_items
        if isinstance(item, dict) and str(item.get("tsa_id")) == tsa_record.tsa_id
    )

    def _repo_relative(path: Path) -> str:
        return path.expanduser().resolve().relative_to(source_root.resolve()).as_posix()

    return TsrOverlayCanonicalSummary(
        candidate_fact_count=candidate_fact_count,
        document_count=document_count,
        fact_family_counts=dict(sorted(family_counts.items())),
        candidate_facts_path=_repo_relative(candidate_facts_path),
        documents_path=_repo_relative(documents_path),
        registry_path=_repo_relative(registry_path),
    )


def _empty_adopted_payload() -> dict[str, list[dict[str, Any]]]:
    return {key: [] for key in _ADOPTED_SECTION_KEYS}


def init_tsr_overlay(
    *,
    instance_root: Path,
    overlay_path: Path,
    tsa: str,
    registry_path: Path,
    documents_path: Path,
    candidate_facts_path: Path,
    source_root: Path,
    overwrite: bool = False,
) -> TsrOverlayInitResult:
    """Create a reviewed/adopted TSR overlay skeleton for one TSA instance."""

    resolved_instance_root = instance_root.expanduser().resolve()
    resolved_overlay_path = overlay_path.expanduser().resolve()
    try:
        resolved_overlay_path.relative_to(resolved_instance_root)
    except ValueError as exc:
        raise TsrOverlayError(
            f"TSR overlay path must live under the instance root: {resolved_overlay_path}"
        ) from exc
    if resolved_overlay_path.exists() and not overwrite:
        raise TsrOverlayError(
            f"TSR overlay already exists: {resolved_overlay_path}. Use `--overwrite` to replace it."
        )

    tsa_record = _resolve_tsa_record(tsa=tsa, registry_path=registry_path)
    canonical_summary = _canonical_summary_for_tsa(
        tsa_record=tsa_record,
        candidate_facts_path=candidate_facts_path,
        documents_path=documents_path,
        registry_path=registry_path,
        source_root=source_root,
    )
    overlay = TsrOverlayRecord(
        schema_version=1,
        tsa=tsa_record,
        canonical_summary=canonical_summary,
        adopted=_empty_adopted_payload(),
    )

    resolved_overlay_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_overlay_path.write_text(
        yaml.safe_dump(
            overlay.to_dict(),
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    return TsrOverlayInitResult(
        overlay_path=resolved_overlay_path,
        tsa=tsa_record,
        canonical_summary=canonical_summary,
        created=True,
    )


def load_tsr_overlay(path: Path) -> TsrOverlayRecord:
    """Load one reviewed/adopted TSR overlay YAML file."""

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrOverlayError(f"TSR overlay not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrOverlayError(f"Invalid TSR overlay payload: {resolved}")
    tsa_payload = payload.get("tsa")
    canonical_payload = payload.get("canonical_summary")
    adopted_payload = payload.get("adopted")
    if not isinstance(tsa_payload, dict) or not isinstance(canonical_payload, dict):
        raise TsrOverlayError(f"Invalid TSR overlay structure: {resolved}")
    if not isinstance(adopted_payload, dict):
        raise TsrOverlayError(f"Invalid TSR overlay adopted payload: {resolved}")
    adopted: dict[str, list[dict[str, Any]]] = {}
    for key in _ADOPTED_SECTION_KEYS:
        value = adopted_payload.get(key, [])
        if not isinstance(value, list):
            raise TsrOverlayError(
                f"Invalid adopted overlay section `{key}` in {resolved}"
            )
        adopted[key] = [item for item in value if isinstance(item, dict)]
    return TsrOverlayRecord(
        schema_version=int(payload.get("schema_version", 1)),
        tsa=TsrOverlayTsaRecord(
            tsa_id=str(tsa_payload["tsa_id"]),
            tsa_code=str(tsa_payload["tsa_code"]),
            tsa_name=str(tsa_payload["tsa_name"]),
        ),
        canonical_summary=TsrOverlayCanonicalSummary(
            candidate_fact_count=int(canonical_payload.get("candidate_fact_count", 0)),
            document_count=int(canonical_payload.get("document_count", 0)),
            fact_family_counts={
                str(key): int(value)
                for key, value in dict(
                    canonical_payload.get("fact_family_counts", {})
                ).items()
            },
            candidate_facts_path=str(canonical_payload.get("candidate_facts_path", "")),
            documents_path=str(canonical_payload.get("documents_path", "")),
            registry_path=str(canonical_payload.get("registry_path", "")),
        ),
        adopted=adopted,
    )


def build_tsr_overlay_report(
    *,
    overlay_path: Path,
) -> TsrOverlayReport:
    """Summarize one reviewed overlay against its canonical candidate summary."""

    overlay = load_tsr_overlay(overlay_path)
    adopted_counts = {
        key: len(overlay.adopted.get(key, [])) for key in _ADOPTED_SECTION_KEYS
    }
    return TsrOverlayReport(
        overlay_path=overlay_path.expanduser().resolve(),
        tsa=overlay.tsa,
        canonical_summary=overlay.canonical_summary,
        adopted_counts=adopted_counts,
    )
