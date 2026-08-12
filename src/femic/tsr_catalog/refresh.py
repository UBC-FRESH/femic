"""Deterministic, additive refreshes of the public BC TSR inventory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import tempfile
from typing import Callable, cast
from urllib.request import Request, urlopen

from .crawl import (
    DEFAULT_TSR_LANDING_URL,
    TsrDocumentRecord,
    TsrIndexResult,
    index_tsr_tsa_surfaces,
)

REFRESH_SCHEMA_VERSION = 1
TOOL_VERSION = "femic-tsr-refresh/1"


@dataclass(frozen=True)
class TsrCatalogDiff:
    added: tuple[dict[str, object], ...]
    changed: tuple[dict[str, object], ...]
    missing: tuple[dict[str, object], ...]
    unreachable: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {name: list(getattr(self, name)) for name in ("added", "changed", "missing", "unreachable")}


@dataclass(frozen=True)
class TsrCatalogRefreshResult:
    generated_utc: str
    source_indexes: tuple[str, ...]
    discovered_documents: tuple[dict[str, object], ...]
    catalog_documents: tuple[dict[str, object], ...]
    diff: TsrCatalogDiff
    written: bool
    scope_tsa: str | None = None
    dry_run: bool = True
    removals_requested: bool = False
    removals_authorized: bool = False
    source_http: dict[str, dict[str, object]] | None = None
    source_failures: tuple[dict[str, object], ...] = ()
    attempted_sources: tuple[str, ...] = ()
    legacy_duplicate_cleanup: tuple[dict[str, object], ...] = ()

    def report_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "generated_utc": self.generated_utc,
            "tool_version": TOOL_VERSION,
            "schema_version": REFRESH_SCHEMA_VERSION,
            "source_indexes": list(self.source_indexes),
            "discovered_count": len(self.discovered_documents),
            "catalog_count": len(self.catalog_documents),
            "written": self.written,
            "mutation_performed": self.written,
            "mutation_blocked": not self.written,
            "scope_tsa": self.scope_tsa,
            "dry_run": self.dry_run,
            "write_mode": "dry-run" if self.dry_run else "write",
            "removals_requested": self.removals_requested,
            "removals_authorized": self.removals_authorized,
            "attempted_sources": list(self.attempted_sources),
            "source_failures": list(self.source_failures),
            "unreachable": list(self.source_failures),
            "legacy_duplicate_cleanup": list(self.legacy_duplicate_cleanup),
            "diff": self.diff.to_dict(),
        }
        if self.source_http is not None:
            payload["source_http"] = self.source_http
        return payload


def _normalize_url(url: str) -> str:
    return url.strip().replace(" ", "%20").rstrip("/")


def _key(document: dict[str, object]) -> str:
    return _normalize_url(str(document.get("url", ""))).casefold()


def _document_payload(document: TsrDocumentRecord) -> dict[str, object]:
    return document.to_dict()


def _select_tsa(documents: list[dict[str, object]], tsa: str | None) -> list[dict[str, object]]:
    if not tsa:
        return documents
    token = tsa.strip().casefold().removeprefix("tsa_").lstrip("0") or "0"
    return [item for item in documents if str(item.get("tsa_code", "")).lstrip("0") == token]


def _dedupe(documents: list[dict[str, object]]) -> list[dict[str, object]]:
    unique: dict[str, dict[str, object]] = {}
    for document in documents:
        normalized = dict(document)
        normalized["url"] = _normalize_url(str(normalized.get("url", "")))
        unique.setdefault(_key(normalized), normalized)
    return sorted(unique.values(), key=lambda item: (str(item.get("tsa_code", "")), str(item.get("relative_path", ""))))


def _duplicate_cleanup(documents: list[dict[str, object]]) -> tuple[dict[str, object], ...]:
    seen: dict[str, dict[str, object]] = {}
    duplicates: list[dict[str, object]] = []
    for document in documents:
        normalized = dict(document)
        normalized["url"] = _normalize_url(str(normalized.get("url", "")))
        key = _key(normalized)
        if key in seen:
            duplicates.append({"url": normalized["url"], "removed": normalized})
        else:
            seen[key] = normalized
    return tuple(duplicates)


def compare_tsr_catalog(existing: list[dict[str, object]], discovered: list[dict[str, object]]) -> TsrCatalogDiff:
    old = {_key(item): item for item in existing}
    new = {_key(item): item for item in discovered}
    added = tuple(new[key] for key in sorted(new.keys() - old.keys()))
    changed = tuple(
        cast(dict[str, object], {"before": old[key], "after": new[key]})
        for key in sorted(new.keys() & old.keys())
        if old[key] != new[key]
    )
    missing = tuple(old[key] for key in sorted(old.keys() - new.keys()))
    return TsrCatalogDiff(added=added, changed=changed, missing=missing, unreachable=())


def _http_metadata(url: str) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": "FEMIC TSR catalog refresh"})
    try:
        with urlopen(request, timeout=30) as response:
            return {
                "status": response.status,
                "headers": dict(response.headers.items()),
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag"),
            }
    except Exception as exc:
        return {
            "status": None,
            "headers": {},
            "error_type": type(exc).__name__,
            "error": str(exc),
            "timeout": isinstance(exc, TimeoutError),
        }


def _atomic_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_json_report_atomic(path: Path, payload: dict[str, object], *, catalog_path: Path) -> None:
    """Write a report without exposing a partial JSON file."""
    report = path.expanduser().resolve()
    catalog = catalog_path.expanduser().resolve()
    if report == catalog:
        raise ValueError("JSON report path must not collide with the catalog path")
    _atomic_write(report, payload)


def refresh_tsr_catalog(
    *,
    catalog_path: Path,
    tsa: str | None = None,
    dry_run: bool = True,
    allow_removals: bool = False,
    index_result: TsrIndexResult | None = None,
    fetch_text: Callable[[str], str] | None = None,
    collect_http_metadata: bool = False,
    source_url: str | None = None,
    timeout: float = 60,
) -> TsrCatalogRefreshResult:
    """Discover, diff, and atomically refresh an additive TSR catalog.

    Missing records are retained unless ``allow_removals`` is explicit. The
    crawl is limited to the BC MoF landing page and its linked TSA FTP index.
    """
    path = catalog_path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"TSR catalog not found: {path}")
    existing_payload = json.loads(path.read_text(encoding="utf-8"))
    existing_raw = [item for item in existing_payload.get("documents", []) if isinstance(item, dict)]
    duplicate_cleanup = _duplicate_cleanup(existing_raw)
    existing = _dedupe(existing_raw)
    result = index_result or index_tsr_tsa_surfaces(
        landing_url=source_url or DEFAULT_TSR_LANDING_URL,
        fetch_text=fetch_text,
        tsa=tsa,
        timeout=timeout,
    )
    discovered = _dedupe(_select_tsa([_document_payload(item) for item in result.documents], tsa))
    old_scope = _select_tsa(existing, tsa)
    diff = compare_tsr_catalog(old_scope, discovered)
    merged = { _key(item): item for item in existing }
    merged.update({_key(item): item for item in discovered})
    source_failures = tuple(
        failure.to_dict() if hasattr(failure, "to_dict") else dict(failure)
        for failure in getattr(result, "source_failures", ())
    )
    removals_authorized = allow_removals and not source_failures
    if removals_authorized:
        for item in diff.missing:
            merged.pop(_key(item), None)
    source_indexes = (result.landing_url, result.tsa_root_url)
    provenance: dict[str, object] = {
        "refresh_utc": datetime.now(UTC).isoformat(),
        "tool_version": TOOL_VERSION,
        "schema_version": REFRESH_SCHEMA_VERSION,
        "source_indexes": list(source_indexes),
        "scope_tsa": tsa,
        "discovery_document_count": len(discovered),
        "removals_requested": allow_removals,
        "removals_authorized": removals_authorized,
        "legacy_duplicate_cleanup": list(duplicate_cleanup),
        "source_failures": list(source_failures),
    }
    if collect_http_metadata:
        provenance["source_http"] = {url: _http_metadata(url) for url in source_indexes}
    payload = dict(existing_payload)
    payload.update(provenance)
    payload["document_count"] = len(merged)
    payload["documents"] = sorted(merged.values(), key=lambda item: (str(item.get("tsa_code", "")), str(item.get("relative_path", ""))))
    can_mutate = not dry_run and not source_failures
    if can_mutate:
        _atomic_write(path, payload)
    return TsrCatalogRefreshResult(
        generated_utc=str(provenance["refresh_utc"]),
        source_indexes=source_indexes,
        discovered_documents=tuple(discovered),
        catalog_documents=tuple(payload["documents"]),
        diff=diff,
        written=can_mutate,
        scope_tsa=tsa,
        dry_run=dry_run,
        removals_requested=allow_removals,
        removals_authorized=removals_authorized,
        source_http=cast(dict[str, dict[str, object]] | None, provenance.get("source_http")),
        source_failures=source_failures,
        attempted_sources=tuple(getattr(result, "attempted_sources", source_indexes)),
        legacy_duplicate_cleanup=duplicate_cleanup,
    )
