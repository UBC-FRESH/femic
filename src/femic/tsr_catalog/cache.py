"""BC TSR PDF cache/fetch helpers with corpus-root indirection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen
import shutil

from femic.user_config import (
    default_femic_tsr_cache_manifest_path,
    default_femic_tsr_corpus_root,
)


_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (compatible; FEMIC/0.1; +https://github.com/UBC-FRESH/femic)"
)


class TsrCacheError(RuntimeError):
    """Raised when TSR document inventory or PDF fetch/cache work fails."""


@dataclass(frozen=True)
class TsrInventoryDocument:
    """One document record loaded from the canonical TSA documents inventory."""

    tsa_id: str
    tsa_code: str
    tsa_name: str
    cycle_label: str
    cycle_year: int | None
    title: str
    document_type: str
    file_name: str
    file_extension: str
    relative_path: str
    url: str
    listed_modified_raw: str
    size_bytes: int | None


@dataclass(frozen=True)
class TsrDownloadedPdf:
    """One fetched or cache-hit TSR PDF with provenance details."""

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
    fetch_status: str
    fetched_utc: str
    sha256: str
    size_bytes: int
    content_type: str | None

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
            "fetch_status": self.fetch_status,
            "fetched_utc": self.fetched_utc,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "content_type": self.content_type,
        }


@dataclass(frozen=True)
class TsrCacheFailure:
    """One failed TSR PDF fetch attempt."""

    tsa_id: str
    source_url: str
    source_relative_path: str
    error: str

    def to_dict(self) -> dict[str, str]:
        return {
            "tsa_id": self.tsa_id,
            "source_url": self.source_url,
            "source_relative_path": self.source_relative_path,
            "error": self.error,
        }


@dataclass(frozen=True)
class TsrFetchResult:
    """Result payload for a TSR PDF fetch/cache run."""

    generated_utc: str
    documents_path: Path
    corpus_root: Path
    manifest_path: Path
    selected_tsa_filters: tuple[str, ...]
    selected_document_count: int
    cached_documents: tuple[TsrDownloadedPdf, ...]
    failures: tuple[TsrCacheFailure, ...]

    def manifest_payload(self, *, source_root: Path | None = None) -> dict[str, object]:
        return {
            "generated_utc": self.generated_utc,
            "documents_path": _render_manifest_path(self.documents_path, source_root),
            "corpus_root": _render_manifest_path(self.corpus_root, source_root),
            "manifest_path": _render_manifest_path(self.manifest_path, source_root),
            "selected_tsa_filters": list(self.selected_tsa_filters),
            "selected_document_count": self.selected_document_count,
            "cached_count": len(self.cached_documents),
            "failure_count": len(self.failures),
            "documents": [item.to_dict() for item in self.cached_documents],
            "failures": [item.to_dict() for item in self.failures],
        }


@dataclass(frozen=True)
class _DownloadedFileMetadata:
    content_type: str | None
    size_bytes: int


DownloadPdfFn = Callable[[str, Path], _DownloadedFileMetadata]


def _render_manifest_path(path: Path, source_root: Path | None) -> str:
    resolved = path.resolve()
    if source_root is not None:
        try:
            return resolved.relative_to(source_root.resolve()).as_posix()
        except ValueError:
            pass
    corpus_root = default_femic_tsr_corpus_root()
    if resolved == corpus_root or corpus_root in resolved.parents:
        suffix = resolved.relative_to(corpus_root)
        base = "~/.femic/tsr/corpus"
        return base if suffix == Path(".") else f"{base}/{suffix.as_posix()}"
    manifest_path = default_femic_tsr_cache_manifest_path()
    if resolved == manifest_path:
        return "~/.femic/tsr/tsa_pdf_cache_manifest.json"
    return str(resolved)


def _default_download_pdf(url: str, destination: Path) -> _DownloadedFileMetadata:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": _BROWSER_USER_AGENT})
    with urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
        info = response.info()
        content_type = info.get_content_type() if info is not None else None
    return _DownloadedFileMetadata(
        content_type=content_type,
        size_bytes=destination.stat().st_size,
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _document_from_dict(payload: dict[str, object]) -> TsrInventoryDocument:
    raw_cycle_year = payload.get("cycle_year")
    cycle_year = None if raw_cycle_year in (None, "") else int(str(raw_cycle_year))
    raw_size_bytes = payload.get("size_bytes")
    size_bytes = None if raw_size_bytes in (None, "") else int(str(raw_size_bytes))
    return TsrInventoryDocument(
        tsa_id=str(payload["tsa_id"]),
        tsa_code=str(payload["tsa_code"]),
        tsa_name=str(payload["tsa_name"]),
        cycle_label=str(payload["cycle_label"]),
        cycle_year=cycle_year,
        title=str(payload["title"]),
        document_type=str(payload["document_type"]),
        file_name=str(payload["file_name"]),
        file_extension=str(payload["file_extension"]),
        relative_path=str(payload["relative_path"]),
        url=str(payload["url"]),
        listed_modified_raw=str(payload["listed_modified_raw"]),
        size_bytes=size_bytes,
    )


def load_tsr_document_inventory(path: Path) -> tuple[TsrInventoryDocument, ...]:
    """Load the canonical TSR TSA documents inventory JSON."""

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrCacheError(f"TSR documents inventory not found: {resolved}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    documents = payload.get("documents")
    if not isinstance(documents, list):
        raise TsrCacheError(
            "TSR documents inventory is missing a valid `documents` list."
        )
    return tuple(
        _document_from_dict(item)
        for item in documents
        if isinstance(item, dict)
        and str(item.get("file_extension") or "").casefold() == "pdf"
    )


def _normalize_filter_token(value: str) -> str:
    return value.strip().replace("_", " ").casefold()


def _matches_tsa_filter(document: TsrInventoryDocument, token: str) -> bool:
    normalized = _normalize_filter_token(token)
    return normalized in {
        _normalize_filter_token(document.tsa_id),
        _normalize_filter_token(document.tsa_code),
        _normalize_filter_token(document.tsa_code.lstrip("0") or document.tsa_code),
        _normalize_filter_token(document.tsa_name),
    }


def _select_documents(
    documents: tuple[TsrInventoryDocument, ...],
    *,
    tsa_filters: tuple[str, ...],
    max_documents: int | None,
) -> tuple[TsrInventoryDocument, ...]:
    selected = documents
    if tsa_filters:
        selected = tuple(
            document
            for document in documents
            if any(_matches_tsa_filter(document, token) for token in tsa_filters)
        )
    if max_documents is not None:
        selected = selected[:max_documents]
    return selected


def _corpus_relative_path(document: TsrInventoryDocument) -> Path:
    return Path("tsa") / document.tsa_id / Path(document.relative_path)


def _existing_file_metadata(path: Path) -> _DownloadedFileMetadata:
    return _DownloadedFileMetadata(content_type=None, size_bytes=path.stat().st_size)


def fetch_tsr_pdfs(
    *,
    documents_path: Path,
    corpus_root: Path,
    manifest_path: Path,
    tsa_filters: tuple[str, ...] = (),
    max_documents: int | None = None,
    source_root: Path | None = None,
    download_pdf_fn: DownloadPdfFn = _default_download_pdf,
) -> TsrFetchResult:
    """Fetch/cache TSR PDFs referenced by the canonical TSA documents inventory."""

    inventory = load_tsr_document_inventory(documents_path)
    selected_documents = _select_documents(
        inventory,
        tsa_filters=tsa_filters,
        max_documents=max_documents,
    )
    corpus_root = corpus_root.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()

    cached: list[TsrDownloadedPdf] = []
    failures: list[TsrCacheFailure] = []
    for document in selected_documents:
        corpus_relative = _corpus_relative_path(document)
        destination = corpus_root / corpus_relative
        fetched_utc = datetime.now(UTC).isoformat()
        try:
            if destination.exists():
                metadata = _existing_file_metadata(destination)
                fetch_status = "cache_hit"
            else:
                metadata = download_pdf_fn(document.url, destination)
                fetch_status = "downloaded"
            cached.append(
                TsrDownloadedPdf(
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
                    corpus_relative_path=corpus_relative.as_posix(),
                    fetch_status=fetch_status,
                    fetched_utc=fetched_utc,
                    sha256=_file_sha256(destination),
                    size_bytes=metadata.size_bytes,
                    content_type=metadata.content_type,
                )
            )
        except Exception as exc:
            failures.append(
                TsrCacheFailure(
                    tsa_id=document.tsa_id,
                    source_url=document.url,
                    source_relative_path=document.relative_path,
                    error=str(exc),
                )
            )

    result = TsrFetchResult(
        generated_utc=datetime.now(UTC).isoformat(),
        documents_path=documents_path.expanduser().resolve(),
        corpus_root=corpus_root,
        manifest_path=manifest_path,
        selected_tsa_filters=tsa_filters,
        selected_document_count=len(selected_documents),
        cached_documents=tuple(cached),
        failures=tuple(failures),
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            result.manifest_payload(source_root=source_root), indent=2, sort_keys=True
        )
        + "\n",
        encoding="utf-8",
    )
    return result
