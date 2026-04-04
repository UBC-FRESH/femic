"""BC Data Catalogue lookup and direct-download helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any, Callable
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen
import shutil


BCDC_PACKAGE_SEARCH_URL = "https://catalogue.data.gov.bc.ca/api/3/action/package_search"
BCDC_DATASET_PAGE_URL = "https://catalogue.data.gov.bc.ca/dataset"
DIRECT_DATA_DOWNLOAD = "direct_data_download"
SERVICE = "service"
INDIRECT_CUSTOM_DOWNLOAD = "indirect_custom_download"
SUPPORTING_DOCUMENT = "supporting_document"
UNKNOWN = "unknown"
DIRECT_DOWNLOAD_CLASSIFICATIONS = {DIRECT_DATA_DOWNLOAD}
DIRECT_DATA_FORMATS = {
    "zip",
    "csv",
    "json",
    "geojson",
    "gpkg",
    "shp",
    "gdb",
    "fgdb",
    "kml",
    "kmz",
    "tif",
    "tiff",
    "xls",
    "xlsx",
}
SERVICE_FORMATS = {"wms", "wfs", "wmts", "kml"}
DOCUMENT_FORMATS = {"pdf", "html", "htm", "doc", "docx", "txt", "rtf"}
DATA_BCDC_TYPES = {"geographic"}
DOCUMENT_BCDC_TYPES = {"document"}
SERVICE_BCDC_TYPES = {"webservice"}
DIRECT_DATA_RESOURCE_TYPES = {"data"}
INDIRECT_ACCESS_METHODS = {"indirect access"}
SERVICE_ACCESS_METHODS = {"service"}
OBJECT_NAME_MATCH_SCORE = 400
OBJECT_SHORT_NAME_MATCH_SCORE = 300
EXACT_TEXT_MATCH_SCORE = 200
CONTAINS_TEXT_MATCH_SCORE = 100
NO_MATCH_SCORE = 0
CURATED_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    "CONSOLIDATED_CUTBLOCKS_2011": ("CONSOLIDATED_CUTBLOCKS",),
}


class BcdcCatalogError(RuntimeError):
    """Raised when the BC Data Catalogue API cannot be queried or parsed."""


@dataclass
class BcdcDownloadedResource:
    """One downloaded direct-access resource."""

    resource_name: str
    resource_url: str
    saved_path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "resource_name": self.resource_name,
            "resource_url": self.resource_url,
            "saved_path": str(self.saved_path),
        }


@dataclass
class BcdcDownloadFailure:
    """One failed direct-download attempt."""

    resource_name: str
    resource_url: str
    error: str

    def to_dict(self) -> dict[str, object]:
        return {
            "resource_name": self.resource_name,
            "resource_url": self.resource_url,
            "error": self.error,
        }


@dataclass
class BcdcDownloadResult:
    """Direct-download outcome for the chosen top match."""

    destination_root: Path
    downloaded: tuple[BcdcDownloadedResource, ...] = ()
    skipped_resources: tuple[str, ...] = ()
    failures: tuple[BcdcDownloadFailure, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "destination_root": str(self.destination_root),
            "downloaded": [item.to_dict() for item in self.downloaded],
            "skipped_resources": list(self.skipped_resources),
            "failures": [item.to_dict() for item in self.failures],
        }


@dataclass
class BcdcResourceMatch:
    """Normalized BC Data Catalogue resource metadata."""

    resource_id: str
    name: str
    classification: str
    url: str | None
    format: str | None
    bcdc_type: str | None
    object_name: str | None
    object_short_name: str | None
    resource_access_method: str | None
    resource_type: str | None
    resource_storage_location: str | None
    matched_by: str
    match_score: int
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "classification": self.classification,
            "url": self.url,
            "format": self.format,
            "bcdc_type": self.bcdc_type,
            "object_name": self.object_name,
            "object_short_name": self.object_short_name,
            "resource_access_method": self.resource_access_method,
            "resource_type": self.resource_type,
            "resource_storage_location": self.resource_storage_location,
            "matched_by": self.matched_by,
            "match_score": self.match_score,
            "notes": list(self.notes),
        }


@dataclass
class BcdcPackageMatch:
    """Normalized package match plus scored resource list."""

    package_id: str
    package_name: str
    title: str
    dataset_page_url: str
    organization_name: str | None
    organization_title: str | None
    license_title: str | None
    download_audience: str | None
    matched_by: str
    match_score: int
    resources: tuple[BcdcResourceMatch, ...]
    manual_follow_up: tuple[str, ...] = ()

    @property
    def direct_download_resources(self) -> tuple[BcdcResourceMatch, ...]:
        return tuple(
            resource
            for resource in self.resources
            if resource.classification in DIRECT_DOWNLOAD_CLASSIFICATIONS
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "package_id": self.package_id,
            "package_name": self.package_name,
            "title": self.title,
            "dataset_page_url": self.dataset_page_url,
            "organization_name": self.organization_name,
            "organization_title": self.organization_title,
            "license_title": self.license_title,
            "download_audience": self.download_audience,
            "matched_by": self.matched_by,
            "match_score": self.match_score,
            "resources": [resource.to_dict() for resource in self.resources],
            "manual_follow_up": list(self.manual_follow_up),
        }


@dataclass
class BcdcResolveResult:
    """Normalized result for one BCDC query."""

    query: str
    limit: int
    generated_utc: str
    api_urls: tuple[str, ...]
    matches: tuple[BcdcPackageMatch, ...]
    download_result: BcdcDownloadResult | None = None
    notes: tuple[str, ...] = ()

    @property
    def top_match(self) -> BcdcPackageMatch | None:
        return self.matches[0] if self.matches else None

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "limit": self.limit,
            "generated_utc": self.generated_utc,
            "api_urls": list(self.api_urls),
            "matches": [match.to_dict() for match in self.matches],
            "top_match": self.top_match.to_dict() if self.top_match else None,
            "download_result": (
                self.download_result.to_dict()
                if self.download_result is not None
                else None
            ),
            "notes": list(self.notes),
        }


def _download_url_to_path(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _slugify_query(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
    return slug or "query"


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().casefold()


def _build_package_search_url(query: str, *, rows: int) -> str:
    params = urlencode({"q": query, "rows": rows})
    return f"{BCDC_PACKAGE_SEARCH_URL}?{params}"


def _build_object_name_search_url(query: str, *, rows: int) -> str:
    object_query = f'res_extras_object_name:"{query.strip()}"'
    return _build_package_search_url(object_query, rows=rows)


def _build_keyword_search_url(query: str, *, rows: int) -> str:
    return _build_package_search_url(query.strip(), rows=rows)


def _query_variants(query: str) -> tuple[str, ...]:
    normalized_query = query.strip()
    variants: list[str] = [normalized_query]
    seen = {normalized_query.casefold()}

    for alias in CURATED_QUERY_ALIASES.get(normalized_query, ()):
        alias_value = alias.strip()
        if alias_value and alias_value.casefold() not in seen:
            variants.append(alias_value)
            seen.add(alias_value.casefold())

    year_suffix_match = re.match(r"^(?P<stem>.+?)(?:[_\s-])(?P<year>19\d{2}|20\d{2})$", normalized_query)
    if year_suffix_match:
        stripped = year_suffix_match.group("stem").strip()
        if stripped and stripped.casefold() not in seen:
            variants.append(stripped)
            seen.add(stripped.casefold())

    return tuple(variants)


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise BcdcCatalogError("BCDC API returned a non-object JSON payload.")
    return payload


def _extract_package_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not payload.get("success"):
        raise BcdcCatalogError(
            "BCDC API reported an unsuccessful package_search result."
        )
    result = payload.get("result")
    if not isinstance(result, dict):
        raise BcdcCatalogError("BCDC API package_search payload is missing `result`.")
    rows = result.get("results", [])
    if not isinstance(rows, list):
        raise BcdcCatalogError("BCDC API package_search payload has invalid `results`.")
    return [row for row in rows if isinstance(row, dict)]


def _looks_like_document(resource: dict[str, Any]) -> bool:
    if _normalize_text(str(resource.get("bcdc_type") or "")) in DOCUMENT_BCDC_TYPES:
        return True
    fmt = _normalize_text(str(resource.get("format") or ""))
    if fmt in DOCUMENT_FORMATS:
        return True
    resource_type = _normalize_text(str(resource.get("resource_type") or ""))
    name = _normalize_text(str(resource.get("name") or ""))
    return resource_type == "abstraction" or name.endswith(".pdf")


def _looks_like_service(resource: dict[str, Any]) -> bool:
    fmt = _normalize_text(str(resource.get("format") or ""))
    bcdc_type = _normalize_text(str(resource.get("bcdc_type") or ""))
    access_method = _normalize_text(str(resource.get("resource_access_method") or ""))
    return (
        fmt in SERVICE_FORMATS
        or bcdc_type in SERVICE_BCDC_TYPES
        or access_method in SERVICE_ACCESS_METHODS
    )


def _looks_like_indirect_custom_download(resource: dict[str, Any]) -> bool:
    access_method = _normalize_text(str(resource.get("resource_access_method") or ""))
    bcdc_type = _normalize_text(str(resource.get("bcdc_type") or ""))
    name = _normalize_text(str(resource.get("name") or ""))
    return (
        access_method in INDIRECT_ACCESS_METHODS
        or "custom download" in name
        or (bcdc_type == "geographic" and access_method == "indirect access")
    )


def _looks_like_direct_data_resource(resource: dict[str, Any]) -> bool:
    url = str(resource.get("url") or "").strip()
    if not url:
        return False
    if _looks_like_document(resource) or _looks_like_service(resource):
        return False
    if _looks_like_indirect_custom_download(resource):
        return False
    fmt = _normalize_text(str(resource.get("format") or ""))
    bcdc_type = _normalize_text(str(resource.get("bcdc_type") or ""))
    resource_type = _normalize_text(str(resource.get("resource_type") or ""))
    return (
        fmt in DIRECT_DATA_FORMATS
        or bcdc_type in DATA_BCDC_TYPES
        or resource_type in DIRECT_DATA_RESOURCE_TYPES
    )


def _classify_resource(resource: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    if _looks_like_indirect_custom_download(resource):
        return (
            INDIRECT_CUSTOM_DOWNLOAD,
            (
                "Requires the BC Geographic Warehouse custom-download flow rather than a stable direct data URL.",
            ),
        )
    if _looks_like_service(resource):
        return (
            SERVICE,
            (
                "Service-style resource; inspect the URL or dataset page rather than treating it as a file download.",
            ),
        )
    if _looks_like_document(resource):
        return (
            SUPPORTING_DOCUMENT,
            (
                "Supporting documentation or abstract resource; not downloaded automatically in v1.",
            ),
        )
    if _looks_like_direct_data_resource(resource):
        return (
            DIRECT_DATA_DOWNLOAD,
            ("Stable direct-access data URL suitable for opt-in v1 downloads.",),
        )
    return (UNKNOWN, ("Resource could not be classified confidently in v1.",))


def _score_text_match(query: str, values: tuple[str | None, ...]) -> tuple[int, str]:
    normalized_query = _normalize_text(query)
    raw_query = query.strip()
    for value in values:
        if value and _normalize_text(value) == normalized_query:
            return (EXACT_TEXT_MATCH_SCORE, f"exact_text:{raw_query}")
    for value in values:
        if value and normalized_query and normalized_query in _normalize_text(value):
            return (CONTAINS_TEXT_MATCH_SCORE, f"text_contains:{raw_query}")
    return (NO_MATCH_SCORE, "none")


def _score_resource(query: str, resource: dict[str, Any]) -> tuple[int, str]:
    object_name = str(resource.get("object_name") or "").strip()
    object_short_name = str(resource.get("object_short_name") or "").strip()
    if object_name and _normalize_text(object_name) == _normalize_text(query):
        return (OBJECT_NAME_MATCH_SCORE, f"object_name:{object_name}")
    if object_short_name and _normalize_text(object_short_name) == _normalize_text(
        query
    ):
        return (OBJECT_SHORT_NAME_MATCH_SCORE, f"object_short_name:{object_short_name}")
    return _score_text_match(
        query,
        (
            str(resource.get("name") or ""),
            object_name,
            object_short_name,
            str(resource.get("object_table_comments") or ""),
        ),
    )


def _build_resource_match(query: str, resource: dict[str, Any]) -> BcdcResourceMatch:
    match_score, matched_by = _score_resource(query, resource)
    classification, notes = _classify_resource(resource)
    return BcdcResourceMatch(
        resource_id=str(resource.get("id") or ""),
        name=str(resource.get("name") or ""),
        classification=classification,
        url=str(resource.get("url") or "").strip() or None,
        format=str(resource.get("format") or "").strip() or None,
        bcdc_type=str(resource.get("bcdc_type") or "").strip() or None,
        object_name=str(resource.get("object_name") or "").strip() or None,
        object_short_name=str(resource.get("object_short_name") or "").strip() or None,
        resource_access_method=(
            str(resource.get("resource_access_method") or "").strip() or None
        ),
        resource_type=str(resource.get("resource_type") or "").strip() or None,
        resource_storage_location=(
            str(resource.get("resource_storage_location") or "").strip() or None
        ),
        matched_by=matched_by,
        match_score=match_score,
        notes=notes,
    )


def _package_text_score(query: str, package: dict[str, Any]) -> tuple[int, str]:
    return _score_text_match(
        query,
        (
            str(package.get("title") or ""),
            str(package.get("name") or ""),
            str(package.get("notes") or ""),
        ),
    )


def _package_manual_follow_up(
    resources: tuple[BcdcResourceMatch, ...],
) -> tuple[str, ...]:
    notes: list[str] = []
    if any(
        resource.classification == INDIRECT_CUSTOM_DOWNLOAD for resource in resources
    ):
        notes.append(
            "Top match includes BCGW indirect/custom-download resources; use the dataset page for manual access if a direct data URL is unavailable."
        )
    if not any(
        resource.classification == DIRECT_DATA_DOWNLOAD for resource in resources
    ) and any(resource.classification == SERVICE for resource in resources):
        notes.append(
            "Top match currently exposes service resources but no direct-access data file for v1 automation."
        )
    if any(resource.classification == SUPPORTING_DOCUMENT for resource in resources):
        notes.append(
            "Supporting documents are available for manual review but are not auto-downloaded in v1."
        )
    return tuple(notes)


def _build_package_match(query: str, package: dict[str, Any]) -> BcdcPackageMatch:
    resources = tuple(
        sorted(
            (
                _build_resource_match(query, resource)
                for resource in package.get("resources", [])
                if isinstance(resource, dict)
            ),
            key=lambda resource: (
                resource.match_score,
                resource.classification == DIRECT_DATA_DOWNLOAD,
                resource.name.casefold(),
            ),
            reverse=True,
        )
    )
    package_score, package_matched_by = _package_text_score(query, package)
    if resources:
        best_resource = resources[0]
        if best_resource.match_score >= package_score:
            package_score = best_resource.match_score
            package_matched_by = best_resource.matched_by
    package_name = str(package.get("name") or "")
    organization = package.get("organization") or {}
    return BcdcPackageMatch(
        package_id=str(package.get("id") or ""),
        package_name=package_name,
        title=str(package.get("title") or package_name),
        dataset_page_url=f"{BCDC_DATASET_PAGE_URL}/{package_name}",
        organization_name=(
            str(organization.get("name") or "").strip() or None
            if isinstance(organization, dict)
            else None
        ),
        organization_title=(
            str(organization.get("title") or "").strip() or None
            if isinstance(organization, dict)
            else None
        ),
        license_title=str(package.get("license_title") or "").strip() or None,
        download_audience=(str(package.get("download_audience") or "").strip() or None),
        matched_by=package_matched_by,
        match_score=package_score,
        resources=resources,
        manual_follow_up=_package_manual_follow_up(resources),
    )


def _has_good_match(matches: tuple[BcdcPackageMatch, ...]) -> bool:
    return bool(matches) and matches[0].match_score >= OBJECT_SHORT_NAME_MATCH_SCORE


def _merge_package_matches(
    existing: dict[str, BcdcPackageMatch],
    query: str,
    rows: list[dict[str, Any]],
) -> None:
    for row in rows:
        match = _build_package_match(query, row)
        current = existing.get(match.package_id)
        if current is None or (
            match.match_score,
            match.title.casefold(),
        ) > (
            current.match_score,
            current.title.casefold(),
        ):
            existing[match.package_id] = match


def resolve_bcdc_candidates(query: str, *, limit: int = 5) -> BcdcResolveResult:
    """Resolve one query against the BC Data Catalogue API."""

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("BCDC query must not be blank.")

    api_urls: list[str] = []
    package_matches: dict[str, BcdcPackageMatch] = {}

    query_variants = _query_variants(normalized_query)
    notes_list: list[str] = []

    alias_variant_used: str | None = None
    for variant in query_variants:
        object_url = _build_object_name_search_url(variant, rows=limit)
        api_urls.append(object_url)
        before_count = len(package_matches)
        _merge_package_matches(
            package_matches,
            variant,
            _extract_package_rows(_fetch_json(object_url)),
        )
        if variant != normalized_query and len(package_matches) > before_count:
            alias_variant_used = variant

        ranked_matches = tuple(
            sorted(
                package_matches.values(),
                key=lambda match: (match.match_score, match.title.casefold()),
                reverse=True,
            )[:limit]
        )
        if _has_good_match(ranked_matches):
            if variant != normalized_query:
                notes_list.append(
                    f"Used alias/query variant `{variant}` after the original query did not produce a strong exact match."
                )
            break

    ranked_matches = tuple(
        sorted(
            package_matches.values(),
            key=lambda match: (match.match_score, match.title.casefold()),
            reverse=True,
        )[:limit]
    )
    if not _has_good_match(ranked_matches):
        for variant in query_variants:
            keyword_url = _build_keyword_search_url(variant, rows=limit)
            api_urls.append(keyword_url)
            before_count = len(package_matches)
            _merge_package_matches(
                package_matches,
                variant,
                _extract_package_rows(_fetch_json(keyword_url)),
            )
            if variant != normalized_query and len(package_matches) > before_count:
                alias_variant_used = variant
            ranked_matches = tuple(
                sorted(
                    package_matches.values(),
                    key=lambda match: (match.match_score, match.title.casefold()),
                    reverse=True,
                )[:limit]
            )
            if _has_good_match(ranked_matches):
                if variant != normalized_query:
                    notes_list.append(
                        f"Used alias/query variant `{variant}` during keyword fallback."
                    )
                break

    ranked_matches = tuple(
        sorted(
            package_matches.values(),
            key=lambda match: (match.match_score, match.title.casefold()),
            reverse=True,
        )[:limit]
    )
    notes: tuple[str, ...] = tuple(notes_list)
    if alias_variant_used is not None and not any(
        alias_variant_used in note for note in notes
    ):
        notes = notes + (
            f"Used alias/query variant `{alias_variant_used}` to surface the current top match.",
        )
    if not ranked_matches:
        notes = notes + ("No catalogue matches found for the supplied query.",)
    return BcdcResolveResult(
        query=normalized_query,
        limit=limit,
        generated_utc=datetime.now(UTC).isoformat(),
        api_urls=tuple(api_urls),
        matches=ranked_matches,
        notes=notes,
    )


def _resource_filename(resource: BcdcResourceMatch) -> str:
    parsed = urlparse(resource.url or "")
    name = Path(parsed.path).name
    if name:
        return name
    base = _slugify_query(resource.object_name or resource.name or "resource")
    suffix = ""
    if resource.format:
        suffix = f".{resource.format.lower()}"
    return f"{base}{suffix}"


def download_direct_bcdc_resources(
    result: BcdcResolveResult,
    *,
    destination_root: Path,
    download_url_fn: Callable[[str, Path], None] = _download_url_to_path,
) -> BcdcDownloadResult:
    """Download direct-access resources from the top-ranked package only."""

    resolved_root = destination_root.expanduser().resolve()
    top_match = result.top_match
    if top_match is None:
        download_result = BcdcDownloadResult(
            destination_root=resolved_root,
            skipped_resources=(
                "No top-ranked package match was available to download.",
            ),
        )
        result.download_result = download_result
        return download_result

    query_root = resolved_root / _slugify_query(result.query)
    downloaded: list[BcdcDownloadedResource] = []
    skipped: list[str] = []
    failures: list[BcdcDownloadFailure] = []

    for resource in top_match.resources:
        if (
            resource.classification not in DIRECT_DOWNLOAD_CLASSIFICATIONS
            or not resource.url
        ):
            skipped.append(f"{resource.name}: {resource.classification}")
            continue
        destination = query_root / _resource_filename(resource)
        try:
            download_url_fn(resource.url, destination)
        except Exception as exc:  # pragma: no cover - exercised via tests
            failures.append(
                BcdcDownloadFailure(
                    resource_name=resource.name,
                    resource_url=resource.url,
                    error=str(exc),
                )
            )
            continue
        downloaded.append(
            BcdcDownloadedResource(
                resource_name=resource.name,
                resource_url=resource.url,
                saved_path=destination,
            )
        )

    download_result = BcdcDownloadResult(
        destination_root=resolved_root,
        downloaded=tuple(downloaded),
        skipped_resources=tuple(skipped),
        failures=tuple(failures),
    )
    result.download_result = download_result
    return download_result


def write_bcdc_manifest(result: BcdcResolveResult, path: Path) -> Path:
    """Write one resolve-result manifest as pretty-printed JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return resolved
