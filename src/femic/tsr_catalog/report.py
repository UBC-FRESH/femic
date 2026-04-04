"""Review/report helpers for TSR candidate facts."""

from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


class TsrFactReportError(RuntimeError):
    """Raised when TSR candidate facts cannot be rendered into review reports."""


_SUPPORTED_FACT_FAMILIES: tuple[str, ...] = (
    "source_layer_candidate",
    "thlb_reference",
)
_QUALITY_RANK = {
    "likely_useful": 0,
    "needs_review": 1,
    "likely_noise": 2,
}
_OBJECT_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]+(?:\.[A-Z0-9_]+)+$")
_SHORT_LAYER_RE = re.compile(r"^[A-Z][A-Z0-9]+(?:_[A-Z0-9]+){1,}$")
_LIBRARY_CALL_RE = re.compile(r"^[A-Z]{1,3}\d+(?:\.\w+)+$")
_SECTION_ONLY_RE = re.compile(r"^\d+(?:\.\d+)*$")
_HECTARE_RE = re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*ha\b", re.IGNORECASE)
_THLB_PHRASE_RE = re.compile(r"\b(thlb|timber harvesting land base)\b", re.IGNORECASE)
_TABLE_OF_CONTENTS_DOT_RE = re.compile(r"\.{5,}")
_USEFUL_SOURCE_PREFIXES: tuple[str, ...] = (
    "WHSE_",
    "REG_",
    "SITE_PROD_BC",
    "CONSOLIDATED_CUTBLOCKS",
    "BCMPB.",
    "FADM_",
    "FTEN_",
    "TA_",
    "FNIRS_",
    "WCP_",
    "RMP_",
    "BEC_",
    "TRIM_",
    "PROT_",
    "VEG_",
    "REC_",
    "CLAB_",
)


@dataclass(frozen=True)
class TsrFactReviewRow:
    """One reviewable row rendered from the canonical TSR candidate-fact pool."""

    tsa_id: str
    tsa_code: str
    tsa_name: str
    fact_family: str
    extracted_value: str
    recommended_query: str
    quality: str
    quality_reason: str
    snippet: str
    page_number: int | None
    title: str
    cycle_label: str
    cycle_year: int | None
    provenance_id: str
    source_url: str

    def to_dict(self) -> dict[str, object]:
        return {
            "tsa_id": self.tsa_id,
            "tsa_code": self.tsa_code,
            "tsa_name": self.tsa_name,
            "fact_family": self.fact_family,
            "extracted_value": self.extracted_value,
            "recommended_query": self.recommended_query,
            "quality": self.quality,
            "quality_reason": self.quality_reason,
            "snippet": self.snippet,
            "page_number": self.page_number,
            "title": self.title,
            "cycle_label": self.cycle_label,
            "cycle_year": self.cycle_year,
            "provenance_id": self.provenance_id,
            "source_url": self.source_url,
        }


@dataclass(frozen=True)
class TsrFactReportResult:
    """Structured result for one guided TSR fact review query."""

    candidate_facts_path: Path
    tsa_id: str
    tsa_code: str
    tsa_name: str
    selected_fact_families: tuple[str, ...]
    rows: tuple[TsrFactReviewRow, ...]

    def quality_counts(self) -> dict[str, int]:
        counts = Counter(row.quality for row in self.rows)
        return {
            "likely_useful": counts.get("likely_useful", 0),
            "needs_review": counts.get("needs_review", 0),
            "likely_noise": counts.get("likely_noise", 0),
        }

    def fact_family_counts(self) -> dict[str, int]:
        counts = Counter(row.fact_family for row in self.rows)
        return dict(sorted(counts.items()))


def _load_candidate_facts(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrFactReportError(
            f"Required TSR candidate-facts artifact not found: {resolved}"
        )
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrFactReportError(f"Expected JSON object at {resolved}")
    facts = payload.get("facts")
    if not isinstance(facts, list):
        raise TsrFactReportError(
            "TSR candidate-facts JSON is missing a valid `facts` list."
        )
    return payload, facts


def _normalize_tsa_token(value: str) -> str:
    return value.strip().replace("_", " ").casefold()


def _normalize_fact_family(value: str) -> str:
    normalized = value.strip().casefold()
    for family in _SUPPORTED_FACT_FAMILIES:
        if normalized == family.casefold():
            return family
    raise TsrFactReportError(
        f"Unsupported TSR fact family `{value}`. Supported values: "
        + ", ".join(_SUPPORTED_FACT_FAMILIES)
    )


def _resolve_tsa_identity(
    facts: list[dict[str, Any]],
    *,
    tsa: str,
) -> tuple[str, str, str]:
    normalized = _normalize_tsa_token(tsa)
    matches: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for fact in facts:
        tsa_id = str(fact.get("tsa_id", ""))
        tsa_code = str(fact.get("tsa_code", ""))
        tsa_name = str(fact.get("tsa_name", ""))
        candidate = (tsa_id, tsa_code, tsa_name)
        if candidate in seen:
            continue
        if normalized in {
            _normalize_tsa_token(tsa_id),
            _normalize_tsa_token(tsa_code),
            _normalize_tsa_token(tsa_code.lstrip("0") or tsa_code),
            _normalize_tsa_token(tsa_name),
        }:
            matches.append(candidate)
            seen.add(candidate)
    if not matches:
        raise TsrFactReportError(f"No TSR candidate facts found for TSA `{tsa}`.")
    if len(matches) > 1:
        labels = ", ".join(
            f"{tsa_code}:{tsa_name}" for _, tsa_code, tsa_name in matches
        )
        raise TsrFactReportError(f"Ambiguous TSA match for `{tsa}`: {labels}")
    return matches[0]


def _clean_source_query(value: str) -> str:
    token = value.strip().strip(".,;:()[]{}")
    token = token.rstrip("_")
    if token.startswith("."):
        token = token[1:]
    return token


def _classify_source_layer(value: str, snippet: str) -> tuple[str, str, str]:
    token = _clean_source_query(value)
    snippet_norm = " ".join(snippet.split())
    upper_token = token.upper()
    upper_snippet = snippet_norm.upper()

    if not token:
        return ("likely_noise", "", "empty candidate token")
    if "____" in token or token.endswith("TSA.") or "________________" in token:
        return ("likely_noise", "", "decorative placeholder token")
    if _SECTION_ONLY_RE.fullmatch(token):
        return ("likely_noise", "", "section/table numbering token")
    if token.startswith("TABLE ") or token.startswith("FIGURE "):
        return ("likely_noise", "", "table/figure label")
    if _LIBRARY_CALL_RE.fullmatch(token):
        return ("likely_noise", "", "library-style call number")
    if _OBJECT_NAME_RE.fullmatch(token):
        return ("likely_useful", token, "BCGW object-name style token")
    if any(upper_token.startswith(prefix) for prefix in _USEFUL_SOURCE_PREFIXES):
        return ("likely_useful", token, "recognized forestry shorthand/prefix")
    if _SHORT_LAYER_RE.fullmatch(token):
        if any(prefix in upper_snippet for prefix in ("BCGW", "WHSE_", "REG_")):
            return ("likely_useful", token, "layer shorthand with BCGW context")
        return ("needs_review", token, "layer shorthand candidate")
    if token.isupper() and len(token) >= 8 and "_" in token:
        return ("needs_review", token, "all-caps underscore token")
    return ("likely_noise", "", "sentence fragment or unrecognized token")


def _classify_thlb_reference(value: str, snippet: str) -> tuple[str, str]:
    snippet_norm = " ".join(snippet.split())
    value_norm = value.strip()
    combined = f"{value_norm} {snippet_norm}".strip()
    upper = combined.upper()

    if not combined:
        return ("likely_noise", "empty THLB candidate")
    if _TABLE_OF_CONTENTS_DOT_RE.search(combined):
        return ("likely_noise", "table-of-contents style entry")
    if _SECTION_ONLY_RE.fullmatch(value_norm):
        return ("likely_noise", "section-number only")
    if _HECTARE_RE.search(combined) and _THLB_PHRASE_RE.search(combined):
        return ("likely_useful", "explicit THLB area reference")
    if _HECTARE_RE.search(combined):
        return ("likely_useful", "hectare value with nearby context")
    if "TIMBER HARVESTING LAND BASE" in upper or "THLB" in upper:
        return ("needs_review", "THLB phrase without explicit area")
    return ("likely_noise", "generic context without concrete THLB signal")


def _row_from_fact(fact: dict[str, Any]) -> TsrFactReviewRow | None:
    family = str(fact.get("fact_family", ""))
    value = str(fact.get("value", "") or "")
    snippet = str(fact.get("snippet", "") or "")
    if family == "source_layer_candidate":
        quality, recommended_query, reason = _classify_source_layer(value, snippet)
    elif family == "thlb_reference":
        quality, reason = _classify_thlb_reference(value, snippet)
        recommended_query = ""
    else:
        return None

    return TsrFactReviewRow(
        tsa_id=str(fact.get("tsa_id", "")),
        tsa_code=str(fact.get("tsa_code", "")),
        tsa_name=str(fact.get("tsa_name", "")),
        fact_family=family,
        extracted_value=value,
        recommended_query=recommended_query,
        quality=quality,
        quality_reason=reason,
        snippet=snippet,
        page_number=fact.get("page_number"),
        title=str(fact.get("title", "")),
        cycle_label=str(fact.get("cycle_label", "")),
        cycle_year=fact.get("cycle_year"),
        provenance_id=str(fact.get("provenance_id", "")),
        source_url=str(fact.get("source_url", "")),
    )


def report_tsr_candidate_facts(
    *,
    candidate_facts_path: Path,
    tsa: str,
    fact_families: tuple[str, ...],
    limit: int | None = None,
) -> TsrFactReportResult:
    """Render review-friendly rows from the canonical TSR candidate-fact pool."""

    resolved_path = candidate_facts_path.expanduser().resolve()
    _, facts = _load_candidate_facts(resolved_path)
    tsa_id, tsa_code, tsa_name = _resolve_tsa_identity(facts, tsa=tsa)
    normalized_families = tuple(
        dict.fromkeys(_normalize_fact_family(f) for f in fact_families)
    )
    if not normalized_families:
        raise TsrFactReportError("At least one `--fact-family` value is required.")

    rows: list[TsrFactReviewRow] = []
    for fact in facts:
        if str(fact.get("tsa_id", "")) != tsa_id:
            continue
        if str(fact.get("fact_family", "")) not in normalized_families:
            continue
        row = _row_from_fact(fact)
        if row is not None:
            rows.append(row)

    rows.sort(
        key=lambda row: (
            _QUALITY_RANK[row.quality],
            row.fact_family,
            row.title,
            row.page_number if row.page_number is not None else 10**9,
            row.extracted_value,
        )
    )
    if limit is not None:
        rows = rows[:limit]

    return TsrFactReportResult(
        candidate_facts_path=resolved_path,
        tsa_id=tsa_id,
        tsa_code=tsa_code,
        tsa_name=tsa_name,
        selected_fact_families=normalized_families,
        rows=tuple(rows),
    )


def write_tsr_fact_report_csv(
    result: TsrFactReportResult,
    *,
    path: Path,
) -> Path:
    """Write review-friendly TSR fact rows to a CSV file."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tsa_id",
        "tsa_code",
        "tsa_name",
        "fact_family",
        "quality",
        "quality_reason",
        "extracted_value",
        "recommended_query",
        "snippet",
        "page_number",
        "title",
        "cycle_label",
        "cycle_year",
        "provenance_id",
        "source_url",
    ]
    with resolved.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in result.rows:
            writer.writerow(row.to_dict())
    return resolved
