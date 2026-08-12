"""Single-PDF metadata summary helpers for FEMIC document-ingestion workflows.

This module extends the optional ``figrecover`` integration by producing a
machine-searchable JSON metadata summary for a single cached PDF. The summary
combines document-level metadata (title, author, page count, SHA-256, source
URL, fetch timestamp) with figrecover-aware figure candidates and
per-page text snippets. Each summary is written as a single deterministic
JSON object with stable keys so downstream automation can search, filter, and
cross-reference it without parsing unstructured manifests.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any


PDF_METADATA_SUMMARY_SCHEMA_VERSION = 1
PDF_METADATA_SUMMARY_SCHEMA_URL = (
    "https://github.com/UBC-FRESH/femic/blob/main/docs/reference/schemas/"
    "femic-pdf-metadata-summary.schema.json"
)

PAGE_TEXT_SNIPPET_MAX_CHARS = 240
PAGE_TEXT_TITLE_MAX_CHARS = 160
PAGE_TEXT_FULL_KEYWORD_LIMIT = 24


class PdfMetadataSummaryError(RuntimeError):
    """Raised when a PDF metadata summary cannot be produced."""


@dataclass(frozen=True)
class TsaInventoryLink:
    """Inventory link used to cross-reference the PDF in the TSA catalog."""

    tsa_id: str | None = None
    tsa_code: str | None = None
    tsa_name: str | None = None
    cycle_label: str | None = None
    cycle_year: int | None = None
    document_type: str | None = None
    inventory_relative_path: str | None = None


@dataclass(frozen=True)
class PdfProvenance:
    """Provenance and tool versions captured during a metadata summary run."""

    figrecover_version: str | None
    pymupdf_version: str | None
    pypdf_version: str | None
    femic_version: str | None
    femic_command: str | None = None
    render_manifest_path: str | None = None
    figure_manifest_path: str | None = None


@dataclass(frozen=True)
class PdfFigureMetadata:
    """One figrecover figure candidate projected into the metadata summary."""

    figure_id: str
    page_number: int
    source: str
    confidence: float
    render_dpi: int | None = None
    bbox: dict[str, float] | None = None
    label: str | None = None
    caption: str | None = None
    image_path: str | None = None
    crop_path: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PdfRenderPage:
    """One rendered PDF page projection carrying figrecover metadata."""

    page_number: int
    image_path: str
    width_px: int | None
    height_px: int | None
    dpi: int | None
    renderer: str | None = None
    source_pdf: str | None = None


@dataclass(frozen=True)
class PdfPageSummary:
    """Lightweight per-page text summary used for indexing and snippets."""

    page_number: int
    char_count: int
    snippet: str | None = None
    has_text: bool = False


@dataclass(frozen=True)
class PdfTextSummary:
    """Aggregated text-derived metadata for the document body."""

    title_page_text: str | None = None
    title_page_normalized: str | None = None
    page_count_with_text: int = 0
    page_summaries: tuple[PdfPageSummary, ...] = ()


@dataclass(frozen=True)
class PdfMetadataSummary:
    """Top-level JSON-serializable summary record for one cached PDF."""

    schema_version: int
    schema_url: str
    generated_utc: str
    document: dict[str, object]
    inventory: dict[str, object]
    text_summary: dict[str, object]
    figures: tuple[dict[str, object], ...]
    rendered_pages: tuple[dict[str, object], ...]
    provenance: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the summary."""

        return {
            "schema_version": self.schema_version,
            "schema_url": self.schema_url,
            "generated_utc": self.generated_utc,
            "document": dict(self.document),
            "inventory": dict(self.inventory),
            "text_summary": dict(self.text_summary),
            "figures": [dict(item) for item in self.figures],
            "rendered_pages": [dict(item) for item in self.rendered_pages],
            "provenance": dict(self.provenance),
        }


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _trim_snippet(value: str, *, max_chars: int) -> str:
    normalized = _normalize_whitespace(value)
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 1].rstrip()}…"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _doc_metadata_from_pymupdf(pdf_path: Path) -> dict[str, object]:
    try:
        import pymupdf  # type: ignore[import-not-found]
    except ImportError:
        return {}

    try:
        document = pymupdf.open(pdf_path)
    except Exception as exc:  # pragma: no cover - depends on PDF contents
        return {"error": f"open_failed:{exc}"}

    try:
        info = document.metadata or {}
        return {
            "format": str(info.get("format") or "") or None,
            "title": (str(info.get("title") or "").strip() or None),
            "author": (str(info.get("author") or "").strip() or None),
            "subject": (str(info.get("subject") or "").strip() or None),
            "keywords": (str(info.get("keywords") or "").strip() or None),
            "creator": (str(info.get("creator") or "").strip() or None),
            "producer": (str(info.get("producer") or "").strip() or None),
            "creation_date": (str(info.get("creationDate") or "").strip() or None),
            "mod_date": (str(info.get("modDate") or "").strip() or None),
            "page_count": int(document.page_count),
        }
    finally:
        document.close()


def _doc_metadata_from_pypdf(pdf_path: Path) -> dict[str, object]:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        return {"available": False, "reason": "pypdf_not_installed"}

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:  # pragma: no cover - depends on PDF contents
        return {"available": False, "reason": f"open_failed:{exc}"}

    info = reader.metadata
    mapping: dict[str, object] = {}
    if info is not None:
        getter = getattr(info, "get", None)
        if callable(getter):
            for raw_key in (
                "/Title",
                "/Author",
                "/Subject",
                "/Keywords",
                "/Creator",
                "/Producer",
                "/CreationDate",
                "/ModDate",
            ):
                value = info.get(raw_key)
                if value is None:
                    continue
                text_value = str(value).strip()
                if text_value:
                    mapping[raw_key.lower().lstrip("/")] = text_value
        else:
            for raw_key in (
                "/Title",
                "/Author",
                "/Subject",
                "/Keywords",
                "/Creator",
                "/Producer",
                "/CreationDate",
                "/ModDate",
            ):
                value = getattr(info, raw_key, None)
                if value is None:
                    continue
                text_value = str(value).strip()
                if text_value:
                    mapping[raw_key.lower().lstrip("/")] = text_value

    return {
        "title": mapping.get("title"),
        "author": mapping.get("author"),
        "subject": mapping.get("subject"),
        "keywords": mapping.get("keywords"),
        "creator": mapping.get("creator"),
        "producer": mapping.get("producer"),
        "creation_date": mapping.get("creationdate"),
        "mod_date": mapping.get("moddate"),
        "page_count": len(reader.pages),
    }


def _coalesce_metadata(
    pymupdf_metadata: dict[str, object],
    pypdf_metadata: dict[str, object],
) -> dict[str, object]:
    """Pick the most informative value across PyMuPDF and pypdf metadata."""

    chosen: dict[str, object] = {}
    text_keys = ("title", "author", "subject", "keywords", "creator", "producer")
    for key in text_keys:
        chosen[key] = pymupdf_metadata.get(key) or pypdf_metadata.get(key)
    page_counts = [
        int(value)
        for value in (
            pymupdf_metadata.get("page_count"),
            pypdf_metadata.get("page_count"),
        )
        if isinstance(value, int) and value > 0
    ]
    chosen["page_count"] = max(page_counts, default=0)
    chosen["creation_date"] = pymupdf_metadata.get(
        "creation_date"
    ) or pypdf_metadata.get("creation_date")
    chosen["mod_date"] = pymupdf_metadata.get("mod_date") or pypdf_metadata.get(
        "mod_date"
    )
    chosen["format"] = pymupdf_metadata.get("format") or "PDF"
    return chosen


def _extract_page_text(pdf_path: Path) -> tuple[str, ...]:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        return ()

    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:  # pragma: no cover - depends on PDF contents
            text = ""
        pages.append(text)
    return tuple(pages)


def _build_text_summary(page_texts: Sequence[str]) -> PdfTextSummary:
    if not page_texts:
        return PdfTextSummary()

    title_page_text = page_texts[0]
    title_page_normalized = (
        _trim_snippet(title_page_text or "", max_chars=PAGE_TEXT_TITLE_MAX_CHARS)
        or None
    )

    page_summaries: list[PdfPageSummary] = []
    page_count_with_text = 0
    for page_number, page_text in enumerate(page_texts, start=1):
        text = page_text or ""
        has_text = bool(text.strip())
        if has_text:
            page_count_with_text += 1
        page_summaries.append(
            PdfPageSummary(
                page_number=page_number,
                char_count=len(text),
                snippet=_trim_snippet(text, max_chars=PAGE_TEXT_SNIPPET_MAX_CHARS)
                if has_text
                else None,
                has_text=has_text,
            )
        )

    return PdfTextSummary(
        title_page_text=title_page_text or None,
        title_page_normalized=title_page_normalized,
        page_count_with_text=page_count_with_text,
        page_summaries=tuple(page_summaries),
    )


def _resolve_optional_module_version(module_name: str) -> str | None:
    try:
        import importlib.metadata as importlib_metadata

        return importlib_metadata.version(module_name)
    except Exception:  # pragma: no cover - optional metadata lookup
        return None


def _resolve_femic_version() -> str | None:
    try:
        import femic as _femic_module

        version = getattr(_femic_module, "__version__", None)
        if version is not None:
            return str(version)
    except ImportError:  # pragma: no cover - femic is the runtime host
        pass
    return _resolve_optional_module_version("femic")


def _resolve_figrecover_version_via_import() -> str | None:
    """Best-effort figrecover version lookups without requiring a packaged install."""

    version_attributes = ("__version__", "VERSION", "version")
    try:
        import figrecover as _figrecover_module
    except ImportError:
        return None
    for attribute in version_attributes:
        candidate = getattr(_figrecover_module, attribute, None)
        if isinstance(candidate, str) and candidate.strip():
            return candidate
        if isinstance(candidate, tuple) and candidate:
            first = candidate[0]
            if isinstance(first, str) and first.strip():
                return first
    return None


def _figure_to_dict(figure: PdfFigureMetadata) -> dict[str, object]:
    payload = asdict(figure)
    if payload["bbox"] is None:
        payload.pop("bbox")
    return payload


def _rendered_page_to_dict(page: PdfRenderPage) -> dict[str, object]:
    return asdict(page)


def _page_summary_to_dict(summary: PdfPageSummary) -> dict[str, object]:
    return asdict(summary)


def _text_summary_to_dict(text_summary: PdfTextSummary) -> dict[str, object]:
    return {
        "title_page_text": text_summary.title_page_text,
        "title_page_normalized": text_summary.title_page_normalized,
        "page_count_with_text": text_summary.page_count_with_text,
        "page_summaries": [
            _page_summary_to_dict(item) for item in text_summary.page_summaries
        ],
    }


def _build_rendered_pages_payload(
    rendered_pages: Sequence[object],
) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for page in rendered_pages:
        if hasattr(page, "model_dump"):
            row = page.model_dump(mode="json")
        elif isinstance(page, dict):
            row = dict(page)
        else:
            row = dict(vars(page))
        image_path = row.get("image_path")
        if image_path is not None and not isinstance(image_path, str):
            row["image_path"] = str(image_path)
        source_pdf = row.get("source_pdf")
        if source_pdf is not None and not isinstance(source_pdf, str):
            row["source_pdf"] = str(source_pdf)
        payload.append(row)
    return payload


def _build_figure_payload(figures: Sequence[object]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for figure in figures:
        if hasattr(figure, "model_dump"):
            row = figure.model_dump(mode="json")
        elif isinstance(figure, dict):
            row = dict(figure)
        else:
            row = dict(vars(figure))
        image_path = row.get("image_path")
        if image_path is not None and not isinstance(image_path, str):
            row["image_path"] = str(image_path)
        source_image_path = row.get("source_image_path")
        if source_image_path is not None and not isinstance(source_image_path, str):
            row["source_image_path"] = str(source_image_path)
        payload.append(row)
    return payload


def _inventory_to_dict(link: TsaInventoryLink) -> dict[str, object]:
    return {
        "tsa_id": link.tsa_id,
        "tsa_code": link.tsa_code,
        "tsa_name": link.tsa_name,
        "cycle_label": link.cycle_label,
        "cycle_year": link.cycle_year,
        "document_type": link.document_type,
        "inventory_relative_path": link.inventory_relative_path,
    }


def _provenance_to_dict(provenance: PdfProvenance) -> dict[str, object]:
    return {
        "figrecover_version": provenance.figrecover_version,
        "pymupdf_version": provenance.pymupdf_version,
        "pypdf_version": provenance.pypdf_version,
        "femic_version": provenance.femic_version,
        "femic_command": provenance.femic_command,
        "render_manifest_path": provenance.render_manifest_path,
        "figure_manifest_path": provenance.figure_manifest_path,
    }


def default_summary_output_path(
    instance_reference_root: Path,
    inventory_relative_path: str,
) -> Path:
    """Return the canonical JSON summary path for a cached TSR PDF.

    The convention places the summary alongside the cached PDF inside the
    instance reference tree so each cycle/TSA combination has its own
    deterministic summary path.
    """

    if not inventory_relative_path.strip():
        raise PdfMetadataSummaryError("inventory_relative_path cannot be blank")

    pdf_path = Path(inventory_relative_path)
    summary_path = pdf_path.with_name(f"{pdf_path.stem}.extracted_metadata.json")
    return (instance_reference_root / summary_path).resolve()


def write_pdf_metadata_summary(
    summary: PdfMetadataSummary,
    *,
    output_path: Path,
) -> Path:
    """Write a ``PdfMetadataSummary`` to disk as deterministic JSON."""

    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def build_pdf_metadata_summary(
    *,
    pdf_path: Path,
    source_url: str,
    fetched_at_utc: str | None,
    inventory_link: TsaInventoryLink | None,
    figrecover_render_pages: Sequence[object],
    figrecover_figure_candidates: Sequence[object],
    source_relative_path: str | None = None,
    render_manifest_path: Path | None = None,
    figure_manifest_path: Path | None = None,
    femic_command: str | None = None,
    page_texts: Sequence[str] | None = None,
    pymupdf_metadata: dict[str, object] | None = None,
    pypdf_metadata: dict[str, object] | None = None,
    femic_version: str | None = None,
    figrecover_version: str | None = None,
    pypdf_version_resolver: Callable[[], str | None] | None = None,
    pymupdf_version_resolver: Callable[[], str | None] | None = None,
) -> PdfMetadataSummary:
    """Build a deterministic ``PdfMetadataSummary`` payload for one PDF.

    The caller supplies figrecover-rendered pages alongside any figure
    candidates discovered from the rendered output. The summary captures the
    document-level metadata, fetched-at timestamp, source URL, and provenance
    information in a stable JSON shape.
    """

    if not source_url.strip():
        raise PdfMetadataSummaryError("source_url cannot be blank")

    resolved_pdf_path = Path(pdf_path).expanduser().resolve()
    if not resolved_pdf_path.exists():
        raise PdfMetadataSummaryError(f"PDF not found for summary: {resolved_pdf_path}")

    resolved_render_manifest_path = (
        str(Path(render_manifest_path).expanduser().resolve())
        if render_manifest_path is not None
        else None
    )
    resolved_figure_manifest_path = (
        str(Path(figure_manifest_path).expanduser().resolve())
        if figure_manifest_path is not None
        else None
    )

    sha256 = _file_sha256(resolved_pdf_path)
    size_bytes = resolved_pdf_path.stat().st_size

    if pymupdf_metadata is None:
        pymupdf_metadata = _doc_metadata_from_pymupdf(resolved_pdf_path)
    if pypdf_metadata is None:
        pypdf_metadata = _doc_metadata_from_pypdf(resolved_pdf_path)

    if page_texts is None:
        page_texts = _extract_page_text(resolved_pdf_path)

    coalesced = _coalesce_metadata(pymupdf_metadata, pypdf_metadata)
    text_summary = _build_text_summary(page_texts or ())

    if pymupdf_version_resolver is not None:
        pymupdf_version = pymupdf_version_resolver()
    else:
        pymupdf_version = _resolve_optional_module_version("pymupdf")
    if pypdf_version_resolver is not None:
        pypdf_version = pypdf_version_resolver()
    else:
        pypdf_version = _resolve_optional_module_version("pypdf")
    if femic_version is None:
        femic_version = _resolve_femic_version()

    document_payload: dict[str, object] = {
        "file_name": resolved_pdf_path.name,
        "local_path": str(resolved_pdf_path),
        "source_url": source_url,
        "source_relative_path": source_relative_path,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "fetched_at_utc": fetched_at_utc,
        "format": coalesced.get("format") or "PDF",
        "title": coalesced.get("title"),
        "author": coalesced.get("author"),
        "subject": coalesced.get("subject"),
        "keywords": coalesced.get("keywords"),
        "creator": coalesced.get("creator"),
        "producer": coalesced.get("producer"),
        "creation_date": coalesced.get("creation_date"),
        "mod_date": coalesced.get("mod_date"),
        "page_count": coalesced.get("page_count") or len(page_texts) or 0,
    }

    inventory_payload = (
        _inventory_to_dict(inventory_link) if inventory_link is not None else {}
    )

    rendered_pages_payload = _build_rendered_pages_payload(figrecover_render_pages)
    figure_payload = _build_figure_payload(figrecover_figure_candidates)

    provenance = PdfProvenance(
        figrecover_version=(
            figrecover_version
            or _resolve_optional_module_version("figrecover")
            or _resolve_figrecover_version_via_import()
        ),
        pymupdf_version=pymupdf_version,
        pypdf_version=pypdf_version,
        femic_version=femic_version,
        femic_command=femic_command,
        render_manifest_path=resolved_render_manifest_path,
        figure_manifest_path=resolved_figure_manifest_path,
    )

    return PdfMetadataSummary(
        schema_version=PDF_METADATA_SUMMARY_SCHEMA_VERSION,
        schema_url=PDF_METADATA_SUMMARY_SCHEMA_URL,
        generated_utc=datetime.now(tz=UTC).replace(microsecond=0).isoformat(),
        document=document_payload,
        inventory=inventory_payload,
        text_summary=_text_summary_to_dict(text_summary),
        figures=tuple(figure_payload),
        rendered_pages=tuple(rendered_pages_payload),
        provenance=_provenance_to_dict(provenance),
    )


def _safe_document_figure_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return slug or "document"


@dataclass(frozen=True)
class PdfMetadataSummaryInputs:
    """Resolved inputs captured ahead of building the summary record."""

    pdf_path: Path
    rendered_pages: tuple[object, ...]
    figure_candidates: tuple[object, ...]
    page_texts: tuple[str, ...]
    fetched_at_utc: str
    render_temp_root: Path | None = None


def _try_import_figrecover() -> tuple[Any, Any, Any, str | None]:
    """Best-effort import of the figrecover helpers needed for rendering.

    Returns a tuple of ``(render_pdf_pages, extract_image_candidates,
    FigureManifest, error_message)``. ``error_message`` is ``None`` on
    success.
    """

    try:
        import figrecover.documents as figrecover_documents
    except ImportError as exc:  # pragma: no cover - optional dependency
        return None, None, None, f"figrecover.documents import failed: {exc}"

    render_pdf_pages = getattr(figrecover_documents, "render_pdf_pages", None)
    if not callable(render_pdf_pages):
        return None, None, None, "figrecover.documents.render_pdf_pages unavailable"

    try:
        import figrecover.adapters as figrecover_adapters
    except ImportError:
        figrecover_adapters = None
        extract_image_candidates = None
        image_candidates_error: str | None = "figrecover.adapters import failed"
    else:
        extract_image_candidates = getattr(
            figrecover_adapters, "extract_pymupdf_image_candidates", None
        )
        image_candidates_error = (
            None
            if callable(extract_image_candidates)
            else "extract_pymupdf_image_candidates unavailable"
        )

    try:
        import figrecover.manifest as figrecover_manifest_module
    except ImportError:
        figrecover_manifest_class = None
        manifest_error: str | None = "figrecover.manifest import failed"
    else:
        figrecover_manifest_class = getattr(
            figrecover_manifest_module, "FigureManifest", None
        )
        manifest_error = (
            None
            if figrecover_manifest_class is not None
            else "FigureManifest unavailable"
        )

    error_message = image_candidates_error or manifest_error
    return (
        render_pdf_pages,
        extract_image_candidates,
        figrecover_manifest_class,
        error_message,
    )


def compute_pdf_metadata_summary_inputs(
    *,
    pdf_path: Path,
    source_url: str,
    source_relative_path: str | None = None,
    dpi: int = 150,
    pages: str | Sequence[int] | None = None,
    render_temp_root: Path | None = None,
) -> PdfMetadataSummaryInputs:
    """Render the PDF and discover figure candidates for the summary.

    This helper isolates the optional figrecover integration so the rest of
    the summary builder can run even when only a subset of ``figrecover``'s
    optional-extras stack (PyMuPDF, OpenCV, scikit-image) is installed.
    """

    if not source_url.strip():
        raise PdfMetadataSummaryError("source_url cannot be blank")
    _ = source_relative_path  # retained on summary payload, not used here

    resolved_pdf_path = Path(pdf_path).expanduser().resolve()
    if not resolved_pdf_path.exists():
        raise PdfMetadataSummaryError(f"PDF not found for summary: {resolved_pdf_path}")

    if not isinstance(dpi, int) or dpi < 1:
        raise PdfMetadataSummaryError("dpi must be an integer >= 1")

    if pages is not None and not isinstance(pages, (str, Sequence)):
        raise PdfMetadataSummaryError("pages must be a string, sequence, or None")

    page_texts = _extract_page_text(resolved_pdf_path)

    (
        render_pdf_pages,
        extract_image_candidates,
        _FigureManifest,
        _figrecover_error,
    ) = _try_import_figrecover()

    rendered_pages: tuple[object, ...] = ()
    figure_candidates: tuple[object, ...] = ()
    selected_render_root: Path | None = None

    if render_pdf_pages is not None:
        try:
            if render_temp_root is not None:
                render_root = Path(render_temp_root).expanduser().resolve()
                render_root.mkdir(parents=True, exist_ok=True)
                pages_dir = render_root / "pages"
            else:
                pages_dir = (
                    Path(tempfile.mkdtemp(prefix="femic-pdf-summary-")) / "pages"
                )
                render_root = pages_dir.parent
            pages_dir.mkdir(parents=True, exist_ok=True)
            rendered_pages = tuple(
                render_pdf_pages(
                    resolved_pdf_path,
                    pages_dir,
                    pages=pages,
                    dpi=dpi,
                    image_format="png",
                    overwrite=True,
                )
            )
            selected_render_root = render_root
        except Exception:  # pragma: no cover - depends on optional deps
            rendered_pages = ()
            selected_render_root = None
        else:
            if extract_image_candidates is not None and rendered_pages:
                try:
                    figure_candidates = tuple(
                        extract_image_candidates(
                            resolved_pdf_path,
                            rendered_pages,
                            pages=pages,
                        )
                    )
                except Exception:  # pragma: no cover - depends on optional deps
                    figure_candidates = ()

    return PdfMetadataSummaryInputs(
        pdf_path=resolved_pdf_path,
        rendered_pages=rendered_pages,
        figure_candidates=figure_candidates,
        page_texts=tuple(page_texts),
        fetched_at_utc=datetime.now(tz=UTC).replace(microsecond=0).isoformat(),
        render_temp_root=selected_render_root,
    )


__all__ = [
    "PAGE_TEXT_FULL_KEYWORD_LIMIT",
    "PAGE_TEXT_SNIPPET_MAX_CHARS",
    "PAGE_TEXT_TITLE_MAX_CHARS",
    "PDF_METADATA_SUMMARY_SCHEMA_URL",
    "PDF_METADATA_SUMMARY_SCHEMA_VERSION",
    "PdfFigureMetadata",
    "PdfMetadataSummary",
    "PdfMetadataSummaryError",
    "PdfMetadataSummaryInputs",
    "PdfPageSummary",
    "PdfProvenance",
    "PdfRenderPage",
    "PdfTextSummary",
    "TsaInventoryLink",
    "build_pdf_metadata_summary",
    "compute_pdf_metadata_summary_inputs",
    "default_summary_output_path",
    "write_pdf_metadata_summary",
]
