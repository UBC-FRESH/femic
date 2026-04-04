"""BC TSR PDF candidate-fact extraction helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import re
from typing import Callable

from femic.tsr_catalog.cache import (
    TsrInventoryDocument,
    _render_manifest_path,
    _select_documents,
    load_tsr_document_inventory,
)


_INCOMPLETE_TOKEN_TAIL_RE = re.compile(r"[A-Z][A-Z0-9_]*_(?:[A-Z0-9_]*)?$")
_SOURCE_LAYER_OBJECT_RE = re.compile(r"\b[A-Z][A-Z0-9_]+(?:\.[A-Z0-9_]+)+\b")
_SOURCE_LAYER_TOKEN_RE = re.compile(
    r"\b(?:SITE_PROD_BC|CONSOLIDATED_CUTBLOCKS(?:_\d{4})?|[A-Z][A-Z0-9]+(?:_[A-Z0-9]+){2,})\b"
)
_SOURCE_LAYER_PREFIXES = (
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
_SOURCE_LAYER_STOPWORDS = {
    "TSR_1995",
    "TSR_2021",
    "TSR_2024",
    "DATA_PACKAGE_2024",
    "DISCUSSION_PAPER",
}
_AU_LINE_RE = re.compile(
    r"(?i)\b(analysis unit|analysis units|productivity unit|au\b)\b"
)
_THLB_LINE_RE = re.compile(r"(?i)\b(thlb|timber harvesting land base)\b")
_TIPSY_LINE_RE = re.compile(
    r"(?i)\b(tipsy|oaf1|oaf2|regen delay|regeneration delay|initial density|site index|si\b|operable age)\b"
)
_HECTARE_VALUE_RE = re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*ha\b", re.IGNORECASE)
_NUMERIC_VALUE_RE = re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b")
logging.getLogger("pypdf").setLevel(logging.ERROR)


class TsrExtractError(RuntimeError):
    """Raised when cached TSR PDFs cannot be parsed into candidate facts."""


@dataclass(frozen=True)
class TsrCandidateFact:
    """One extracted TSR candidate fact with lightweight provenance."""

    tsa_id: str
    tsa_code: str
    tsa_name: str
    cycle_label: str
    cycle_year: int | None
    title: str
    document_type: str
    file_name: str
    source_url: str
    source_relative_path: str
    corpus_relative_path: str
    fact_family: str
    value: str
    page_number: int | None
    snippet: str
    provenance_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "tsa_id": self.tsa_id,
            "tsa_code": self.tsa_code,
            "tsa_name": self.tsa_name,
            "cycle_label": self.cycle_label,
            "cycle_year": self.cycle_year,
            "title": self.title,
            "document_type": self.document_type,
            "file_name": self.file_name,
            "source_url": self.source_url,
            "source_relative_path": self.source_relative_path,
            "corpus_relative_path": self.corpus_relative_path,
            "fact_family": self.fact_family,
            "value": self.value,
            "page_number": self.page_number,
            "snippet": self.snippet,
            "provenance_id": self.provenance_id,
        }


@dataclass(frozen=True)
class TsrExtractionFailure:
    """One failed candidate-fact extraction attempt."""

    tsa_id: str
    source_relative_path: str
    corpus_relative_path: str
    error: str

    def to_dict(self) -> dict[str, str]:
        return {
            "tsa_id": self.tsa_id,
            "source_relative_path": self.source_relative_path,
            "corpus_relative_path": self.corpus_relative_path,
            "error": self.error,
        }


@dataclass(frozen=True)
class TsrExtractResult:
    """Result payload for one TSR candidate-fact extraction run."""

    generated_utc: str
    documents_path: Path
    corpus_root: Path
    output_path: Path
    selected_tsa_filters: tuple[str, ...]
    selected_document_count: int
    extracted_documents_count: int
    facts: tuple[TsrCandidateFact, ...]
    failures: tuple[TsrExtractionFailure, ...]

    def fact_family_counts(self) -> dict[str, int]:
        counts = Counter(fact.fact_family for fact in self.facts)
        return dict(sorted(counts.items()))

    def payload(self, *, source_root: Path | None = None) -> dict[str, object]:
        return {
            "generated_utc": self.generated_utc,
            "documents_path": _render_manifest_path(self.documents_path, source_root),
            "corpus_root": _render_manifest_path(self.corpus_root, source_root),
            "output_path": _render_manifest_path(self.output_path, source_root),
            "selected_tsa_filters": list(self.selected_tsa_filters),
            "selected_document_count": self.selected_document_count,
            "extracted_documents_count": self.extracted_documents_count,
            "fact_count": len(self.facts),
            "failure_count": len(self.failures),
            "fact_family_counts": self.fact_family_counts(),
            "facts": [fact.to_dict() for fact in self.facts],
            "failures": [failure.to_dict() for failure in self.failures],
        }


ExtractPdfPagesFn = Callable[[Path], tuple[str, ...]]


def _default_extract_pdf_pages(path: Path) -> tuple[str, ...]:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise TsrExtractError(
            "TSR extraction requires `pypdf`. Install FEMIC dependencies again or "
            "run `python -m pip install pypdf` in the active environment."
        ) from exc

    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pragma: no cover - depends on external PDFs
        raise TsrExtractError(f"Unable to open cached TSR PDF: {path}: {exc}") from exc

    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover - depends on external PDFs
            raise TsrExtractError(
                f"Unable to extract text from cached TSR PDF: {path}: {exc}"
            ) from exc
    return tuple(pages)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _trim_snippet(text: str, *, max_chars: int = 280) -> str:
    normalized = _normalize_whitespace(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def _document_corpus_relative_path(document: TsrInventoryDocument) -> Path:
    return Path("tsa") / document.tsa_id / Path(document.relative_path)


def _build_fact(
    document: TsrInventoryDocument,
    *,
    corpus_relative_path: Path,
    fact_family: str,
    value: str,
    page_number: int | None,
    snippet: str,
) -> TsrCandidateFact:
    provenance = (
        f"{document.relative_path}#page={page_number}"
        if page_number
        else document.relative_path
    )
    return TsrCandidateFact(
        tsa_id=document.tsa_id,
        tsa_code=document.tsa_code,
        tsa_name=document.tsa_name,
        cycle_label=document.cycle_label,
        cycle_year=document.cycle_year,
        title=document.title,
        document_type=document.document_type,
        file_name=document.file_name,
        source_url=document.url,
        source_relative_path=document.relative_path,
        corpus_relative_path=corpus_relative_path.as_posix(),
        fact_family=fact_family,
        value=value,
        page_number=page_number,
        snippet=snippet,
        provenance_id=provenance,
    )


def _looks_like_source_layer_token(token: str) -> bool:
    if token in _SOURCE_LAYER_STOPWORDS:
        return False
    if any(token.startswith(prefix) for prefix in _SOURCE_LAYER_PREFIXES):
        return True
    return "." in token


def _rewrap_split_tokens(lines: list[str]) -> list[str]:
    """Join consecutive lines where a source-layer token is split across the wrap."""
    if not lines:
        return lines
    result: list[str] = [lines[0]]
    for line in lines[1:]:
        prev = result[-1]
        prev_tail = prev.rstrip()
        line_head = line.lstrip()
        should_join = False
        # Previous line ends with trailing underscore suffix (e.g. "L_MULE_DEER_")
        if prev_tail and prev_tail[-1] == "_" and _INCOMPLETE_TOKEN_TAIL_RE.search(prev_tail):
            should_join = True
        if should_join:
            result[-1] = f"{prev_tail}{line}"
        else:
            result.append(line)
    return result


def _iter_source_layer_facts(
    document: TsrInventoryDocument,
    *,
    corpus_relative_path: Path,
    page_number: int,
    page_text: str,
) -> tuple[TsrCandidateFact, ...]:
    facts: list[TsrCandidateFact] = []
    seen: set[str] = set()
    for raw_line in _rewrap_split_tokens(page_text.splitlines()):
        line = _trim_snippet(raw_line)
        if not line:
            continue
        for pattern in (_SOURCE_LAYER_OBJECT_RE, _SOURCE_LAYER_TOKEN_RE):
            for match in pattern.finditer(line):
                token = match.group(0)
                if pattern is _SOURCE_LAYER_TOKEN_RE and f"{token}." in line:
                    continue
                if not _looks_like_source_layer_token(token):
                    continue
                dedupe_key = f"{page_number}:{token}"
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                facts.append(
                    _build_fact(
                        document,
                        corpus_relative_path=corpus_relative_path,
                        fact_family="source_layer_candidate",
                        value=token,
                        page_number=page_number,
                        snippet=line,
                    )
                )
    return tuple(facts)


def _iter_keyword_line_facts(
    document: TsrInventoryDocument,
    *,
    corpus_relative_path: Path,
    page_number: int,
    page_text: str,
    fact_family: str,
    line_re: re.Pattern[str],
    value_fn: Callable[[str], str],
) -> tuple[TsrCandidateFact, ...]:
    facts: list[TsrCandidateFact] = []
    seen: set[str] = set()
    for raw_line in page_text.splitlines():
        line = _trim_snippet(raw_line)
        if not line or not line_re.search(line):
            continue
        value = value_fn(line)
        dedupe_key = f"{page_number}:{value}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        facts.append(
            _build_fact(
                document,
                corpus_relative_path=corpus_relative_path,
                fact_family=fact_family,
                value=value,
                page_number=page_number,
                snippet=line,
            )
        )
    return tuple(facts)


def _thlb_value_from_line(line: str) -> str:
    hectare_match = _HECTARE_VALUE_RE.search(line)
    if hectare_match:
        return hectare_match.group(0)
    numeric_match = _NUMERIC_VALUE_RE.search(line)
    return numeric_match.group(0) if numeric_match else _trim_snippet(line)


def _document_metadata_fact(
    document: TsrInventoryDocument,
    *,
    corpus_relative_path: Path,
) -> TsrCandidateFact:
    metadata_value = f"{document.title} [{document.document_type}]"
    metadata_snippet = (
        f"{document.tsa_name} {document.cycle_label} {document.title} "
        f"({document.document_type})"
    )
    return _build_fact(
        document,
        corpus_relative_path=corpus_relative_path,
        fact_family="document_metadata",
        value=metadata_value,
        page_number=None,
        snippet=_trim_snippet(metadata_snippet),
    )


def extract_tsr_candidate_facts(
    *,
    documents_path: Path,
    corpus_root: Path,
    output_path: Path,
    tsa_filters: tuple[str, ...] = (),
    max_documents: int | None = None,
    source_root: Path | None = None,
    extract_pdf_pages_fn: ExtractPdfPagesFn = _default_extract_pdf_pages,
) -> TsrExtractResult:
    """Extract reviewable TSR candidate facts from cached PDFs."""

    inventory = load_tsr_document_inventory(documents_path)
    selected_documents = _select_documents(
        inventory,
        tsa_filters=tsa_filters,
        max_documents=max_documents,
    )
    resolved_corpus_root = corpus_root.expanduser().resolve()
    resolved_output_path = output_path.expanduser().resolve()

    facts: list[TsrCandidateFact] = []
    failures: list[TsrExtractionFailure] = []
    extracted_documents_count = 0
    for document in selected_documents:
        corpus_relative_path = _document_corpus_relative_path(document)
        cached_pdf_path = resolved_corpus_root / corpus_relative_path
        if not cached_pdf_path.exists():
            failures.append(
                TsrExtractionFailure(
                    tsa_id=document.tsa_id,
                    source_relative_path=document.relative_path,
                    corpus_relative_path=corpus_relative_path.as_posix(),
                    error="cached_pdf_missing",
                )
            )
            continue

        try:
            page_texts = extract_pdf_pages_fn(cached_pdf_path)
        except Exception as exc:
            failures.append(
                TsrExtractionFailure(
                    tsa_id=document.tsa_id,
                    source_relative_path=document.relative_path,
                    corpus_relative_path=corpus_relative_path.as_posix(),
                    error=str(exc),
                )
            )
            continue

        extracted_documents_count += 1
        facts.append(
            _document_metadata_fact(
                document,
                corpus_relative_path=corpus_relative_path,
            )
        )
        for idx, page_text in enumerate(page_texts, start=1):
            if not page_text or not page_text.strip():
                continue
            facts.extend(
                _iter_source_layer_facts(
                    document,
                    corpus_relative_path=corpus_relative_path,
                    page_number=idx,
                    page_text=page_text,
                )
            )
            facts.extend(
                _iter_keyword_line_facts(
                    document,
                    corpus_relative_path=corpus_relative_path,
                    page_number=idx,
                    page_text=page_text,
                    fact_family="au_definition_candidate",
                    line_re=_AU_LINE_RE,
                    value_fn=_trim_snippet,
                )
            )
            facts.extend(
                _iter_keyword_line_facts(
                    document,
                    corpus_relative_path=corpus_relative_path,
                    page_number=idx,
                    page_text=page_text,
                    fact_family="thlb_reference",
                    line_re=_THLB_LINE_RE,
                    value_fn=_thlb_value_from_line,
                )
            )
            facts.extend(
                _iter_keyword_line_facts(
                    document,
                    corpus_relative_path=corpus_relative_path,
                    page_number=idx,
                    page_text=page_text,
                    fact_family="tipsy_input_candidate",
                    line_re=_TIPSY_LINE_RE,
                    value_fn=_trim_snippet,
                )
            )

    deduped_facts: list[TsrCandidateFact] = []
    seen_fact_keys: set[tuple[str, str, str, int | None]] = set()
    for fact in facts:
        key = (
            fact.source_relative_path,
            fact.fact_family,
            fact.value,
            fact.page_number,
        )
        if key in seen_fact_keys:
            continue
        seen_fact_keys.add(key)
        deduped_facts.append(fact)

    result = TsrExtractResult(
        generated_utc=datetime.now(UTC).isoformat(),
        documents_path=documents_path.expanduser().resolve(),
        corpus_root=resolved_corpus_root,
        output_path=resolved_output_path,
        selected_tsa_filters=tsa_filters,
        selected_document_count=len(selected_documents),
        extracted_documents_count=extracted_documents_count,
        facts=tuple(deduped_facts),
        failures=tuple(failures),
    )
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(
        json.dumps(result.payload(source_root=source_root), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return result
