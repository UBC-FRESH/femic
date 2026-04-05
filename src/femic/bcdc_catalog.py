"""BC Data Catalogue lookup and direct-download helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import urlopen
import shutil
import xml.etree.ElementTree as ET


BCDC_PACKAGE_SEARCH_URL = "https://catalogue.data.gov.bc.ca/api/3/action/package_search"
BCDC_DATASET_PAGE_URL = "https://catalogue.data.gov.bc.ca/dataset"
DIRECT_DATA_DOWNLOAD = "direct_data_download"
SERVICE = "service"
INDIRECT_CUSTOM_DOWNLOAD = "indirect_custom_download"
SUPPORTING_DOCUMENT = "supporting_document"
UNKNOWN = "unknown"
SERVICE_TYPE_OPENMAPS_OWS = "openmaps_ows"
FETCH_STRATEGY_WFS_GETFEATURE_BBOX = "wfs_getfeature_bbox"
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
OBJECT_NAME_SUFFIX_MATCH_SCORE = 350
OBJECT_SHORT_NAME_MATCH_SCORE = 300
OBJECT_NAME_STEM_MATCH_SCORE = 250
EXACT_TEXT_MATCH_SCORE = 200
CONTAINS_TEXT_MATCH_SCORE = 100
NO_MATCH_SCORE = 0
CURATED_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    "CONSOLIDATED_CUTBLOCKS_2011": ("CONSOLIDATED_CUTBLOCKS",),
    "SITE_PROD_BC": ("Provincial Site Productivity Layer",),
    "REG_LAND_AND_NATURAL_RESOURCE.TERRAIN_STABILITY": (
        "WHSE_TERRESTRIAL_ECOLOGY.STE_TER_STABILITY_POLYS_SVW",
    ),
    "REG_LAND_AND_NATURAL_RESOURCE.STE_TER": (
        "WHSE_TERRESTRIAL_ECOLOGY.STE_TER_STABILITY_POLYS_SVW",
    ),
    "WHSE_CADASTRE.CBM_CADASTRAL_FABRIC": (
        "WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW",
    ),
    "WHSE_WATER_MANAGEMENT.BC_COMMUNITY_WATERSHEDS": (
        "WHSE_WATER_MANAGEMENT.WLS_COMMUNITY_WS_PUB_SVW",
    ),
    "WHSE_BASEMAPPING.DRA_DIGITAL_ROAD_ATLAS_LINE_SP": (
        "WHSE_BASEMAPPING.DRA_DGTL_ROAD_ATLAS_MPAR_SP",
    ),
    "WHSE_LAND_USE_PLANNING.FADM_DESIGNATED": (
        "WHSE_ADMIN_BOUNDARIES.FADM_DESIGNATED_AREAS",
    ),
    "REG_LAND_AND_NATURAL_RESOURCE.WLD_WHA_PROPOSED_SP": (
        "WHSE_WILDLIFE_MANAGEMENT.WCP_WHA_PROPOSED_SP",
    ),
}
QUERY_NAMESPACE_PREFIXES: dict[str, str] = {
    "FADM_": "WHSE_ADMIN_BOUNDARIES.",
    "CLAB_": "WHSE_ADMIN_BOUNDARIES.",
    "TA_": "WHSE_TANTALIS.",
    "BEC_": "WHSE_FOREST_VEGETATION.",
    "VEG_": "WHSE_FOREST_VEGETATION.",
    "FTEN_": "WHSE_FOREST_TENURE.",
    "WCP_": "WHSE_WILDLIFE_MANAGEMENT.",
    "RMP_": "WHSE_LAND_USE_PLANNING.",
    "TRIM_": "WHSE_BASEMAPPING.",
    "STE_": "WHSE_TERRESTRIAL_ECOLOGY.",
}
LOCAL_TOKEN_ALIASES: dict[str, tuple[str, ...]] = {
    "FADM_BCTS_AREA": ("FADM_BCTS_AREA_SP",),
    "FADM_DESIGNATED": ("FADM_DESIGNATED_AREAS",),
    "CLAB_INDIAN": ("CLAB_INDIAN_RESERVES",),
    "TA_CROWN_TENURES": ("TA_CROWN_TENURES_SVW",),
    "TA_WILDLIFE_MGMT_AREAS": ("TA_WILDLIFE_MGMT_AREAS_SVW",),
    "TA_PARK_ECORES_PA": ("TA_PARK_ECORES_PA_SVW",),
    "RMP_OGMA_LEGAL": ("RMP_OGMA_LEGAL_CURRENT_SVW",),
    "RMP_PLAN_LEGAL": ("RMP_PLAN_LEGAL_POLY_SVW",),
    "RMP_PLAN_NON_LEGAL": ("RMP_PLAN_NON_LEGAL_POLY_SVW",),
    "RMP_LANDSCAPE_UNIT_SVW_NO_MULTIPLES": ("RMP_LANDSCAPE_UNIT_SVW",),
    "RMP_STRGC_LAND": ("RMP_STRGC_LAND_RSRCE_PLAN_SVW",),
    "RMP_STRGC_LAND_RSRCE_PLAN": ("RMP_STRGC_LAND_RSRCE_PLAN_SVW",),
    "WCP_UNGULATE": ("WCP_UNGULATE_WINTER_RANGE_SP",),
    "WCP_UNGULATE_WINTER_RANGE": ("WCP_UNGULATE_WINTER_RANGE_SP",),
    "WCP_WILDLIFE_HABITAT_AREA": ("WCP_WILDLIFE_HABITAT_AREA_POLY",),
    "REC_VISUAL_LANDSCAPE": ("REC_VISUAL_LANDSCAPE_INVENTORY",),
    "FTEN_ROAD_SECTION_LINES": ("FTEN_ROAD_SECTION_LINES_SVW",),
    "FTEN_MANAGED_LIC": (
        "FTEN_MANAGED_LICENCE_POLY_SVW",
        "FTEN_MANAGED_LICENCE_POLY",
    ),
    "FTEN_MANAGED_LIC_POLY_SVW": (
        "FTEN_MANAGED_LICENCE_POLY_SVW",
        "FTEN_MANAGED_LICENCE_POLY",
    ),
    "BEC": ("BEC_BIOGEOCLIMATIC_POLY",),
    "BC_COMMUNITY_WATERSHEDS": ("WLS_COMMUNITY_WS_PUB_SVW",),
    "DRA_DIGITAL_ROAD_ATLAS_LINE_SP": ("DRA_DGTL_ROAD_ATLAS_MPAR_SP",),
    "WLD_WHA_PROPOSED_SP": ("WCP_WHA_PROPOSED_SP",),
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

    def relative_to(self, *other: str | Path) -> Path:
        """Delegate path-style relative resolution to the saved path."""

        return self.saved_path.relative_to(*other)


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
    service_type: str | None = None
    wfs_queryable: bool = False
    wfs_capabilities_url: str | None = None
    wfs_typename: str | None = None
    suggested_fetch_strategy: str | None = None
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
            "service_type": self.service_type,
            "wfs_queryable": self.wfs_queryable,
            "wfs_capabilities_url": self.wfs_capabilities_url,
            "wfs_typename": self.wfs_typename,
            "suggested_fetch_strategy": self.suggested_fetch_strategy,
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
    suggested_fetch_strategy: str | None = None
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
            "suggested_fetch_strategy": self.suggested_fetch_strategy,
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


@dataclass(frozen=True)
class BcdcReplacementFamilyCandidate:
    """One review-only replacement candidate for a stale TSR source token."""

    title: str
    dataset_page_url: str
    object_names: tuple[str, ...]
    matched_query: str
    rationale: str

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "dataset_page_url": self.dataset_page_url,
            "object_names": list(self.object_names),
            "matched_query": self.matched_query,
            "rationale": self.rationale,
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


def _split_query_namespace(query: str) -> tuple[str | None, str]:
    namespace, separator, local_name = query.partition(".")
    if separator:
        return (namespace, local_name)
    return (None, query)


def _add_query_variant(
    variants: list[str],
    seen: set[str],
    value: str,
) -> None:
    normalized_value = value.strip()
    if normalized_value and normalized_value.casefold() not in seen:
        variants.append(normalized_value)
        seen.add(normalized_value.casefold())


def _local_query_aliases(local_name: str) -> tuple[str, ...]:
    normalized_local = local_name.strip()
    variants: list[str] = []
    seen: set[str] = set()
    for alias in LOCAL_TOKEN_ALIASES.get(normalized_local, ()):
        _add_query_variant(variants, seen, alias)
    if "_LIC_" in normalized_local:
        _add_query_variant(
            variants,
            seen,
            normalized_local.replace("_LIC_", "_LICENCE_"),
        )
    return tuple(variants)


def _build_package_search_url(query: str, *, rows: int) -> str:
    params = urlencode({"q": query, "rows": rows})
    return f"{BCDC_PACKAGE_SEARCH_URL}?{params}"


def _build_object_name_search_url(query: str, *, rows: int) -> str:
    object_query = f'res_extras_object_name:"{query.strip()}"'
    return _build_package_search_url(object_query, rows=rows)


def _build_keyword_search_url(query: str, *, rows: int) -> str:
    return _build_package_search_url(query.strip(), rows=rows)


def _normalize_url_without_query(url: str) -> str:
    parsed = urlparse(url.strip())
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _looks_like_openmaps_ows_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc.casefold() == "openmaps.gov.bc.ca"
        and parsed.path.casefold().endswith("/ows")
    )


def _build_wfs_capabilities_url(service_url: str) -> str:
    parsed = urlparse(service_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["service"] = "WFS"
    query["request"] = "GetCapabilities"
    if "version" not in query:
        query["version"] = "2.0.0"
    encoded_query = urlencode(query)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            encoded_query,
            parsed.fragment,
        )
    )


def _probe_service_resource(
    resource: dict[str, Any],
    *,
    fetch_text_fn: Callable[[str], str],
) -> tuple[str | None, bool, str | None, str | None, str | None, tuple[str, ...]]:
    resource_url = str(resource.get("url") or "").strip()
    if not _looks_like_openmaps_ows_url(resource_url):
        return (None, False, None, None, None, ())

    capabilities_url = _build_wfs_capabilities_url(resource_url)
    notes = [
        "OpenMaps `ows` service detected; probing WFS capabilities for later AOI-scoped automation.",
    ]
    try:
        payload = fetch_text_fn(capabilities_url)
        root = ET.fromstring(payload)
    except Exception as exc:
        return (
            SERVICE_TYPE_OPENMAPS_OWS,
            False,
            capabilities_url,
            None,
            None,
            tuple(notes + [f"WFS probe failed while reading capabilities: {exc}"]),
        )

    feature_names = [
        element.text.strip()
        for element in root.findall(".//{*}FeatureType/{*}Name")
        if element.text and element.text.strip()
    ]
    object_name = str(resource.get("object_name") or "").strip()
    expected_name = f"pub:{object_name}" if object_name else None
    chosen_name: str | None = None
    if expected_name and expected_name in feature_names:
        chosen_name = expected_name
    elif object_name and object_name in feature_names:
        chosen_name = object_name

    if chosen_name is not None:
        notes.append(
            f"WFS `GetFeature` is available for `{chosen_name}`; later automation can use bbox-scoped fetches."
        )
        return (
            SERVICE_TYPE_OPENMAPS_OWS,
            True,
            capabilities_url,
            chosen_name,
            FETCH_STRATEGY_WFS_GETFEATURE_BBOX,
            tuple(notes),
        )

    if feature_names:
        notes.append(
            "WFS capabilities responded, but the expected feature type name was not discovered in the advertised layer list."
        )
        return (
            SERVICE_TYPE_OPENMAPS_OWS,
            False,
            capabilities_url,
            None,
            None,
            tuple(notes),
        )

    notes.append("WFS capabilities responded without any advertised feature types.")
    return (
        SERVICE_TYPE_OPENMAPS_OWS,
        False,
        capabilities_url,
        None,
        None,
        tuple(notes),
    )


def _query_variants(query: str) -> tuple[str, ...]:
    normalized_query = query.strip()
    variants: list[str] = [normalized_query]
    seen = {normalized_query.casefold()}

    for alias in CURATED_QUERY_ALIASES.get(normalized_query, ()):
        alias_value = alias.strip()
        if alias_value and alias_value.casefold() not in seen:
            variants.append(alias_value)
            seen.add(alias_value.casefold())

    namespace, local_name = _split_query_namespace(normalized_query)
    local_aliases = _local_query_aliases(local_name)
    if namespace is not None:
        for alias in local_aliases:
            _add_query_variant(variants, seen, f"{namespace}.{alias}")
    else:
        for alias in local_aliases:
            _add_query_variant(variants, seen, alias)
        for prefix, namespace_prefix in QUERY_NAMESPACE_PREFIXES.items():
            if local_name.startswith(prefix):
                _add_query_variant(variants, seen, f"{namespace_prefix}{local_name}")
                for alias in local_aliases:
                    _add_query_variant(variants, seen, f"{namespace_prefix}{alias}")

    year_suffix_match = re.match(
        r"^(?P<stem>.+?)(?:[_\s-])(?P<year>19\d{2}|20\d{2})$", normalized_query
    )
    if year_suffix_match:
        stripped = year_suffix_match.group("stem").strip()
        if stripped and stripped.casefold() not in seen:
            variants.append(stripped)
            seen.add(stripped.casefold())

    return tuple(variants)


def _replacement_family_search_terms(query: str) -> tuple[tuple[str, str], ...]:
    normalized = query.strip().upper()
    terms: list[tuple[str, str]] = []
    if "MULE_DEER" in normalized:
        terms.append(
            (
                "MULE_DEER",
                "Broad mule-deer search surfaced a small public wildlife family that may replace a stale TSR token.",
            )
        )
    if "PIP_CONSULTATION" in normalized:
        terms.append(
            (
                "PIP_CONSULTATION",
                "Broad PIP consultation search surfaced a likely public consultation-area lead.",
            )
        )
    if "BURN_SEVERITY" in normalized:
        terms.append(
            (
                "BURN_SEVERITY",
                "Broad burn-severity search surfaced current public burn-severity dataset candidates.",
            )
        )
    return tuple(terms)


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise BcdcCatalogError("BCDC API returned a non-object JSON payload.")
    return payload


def _fetch_text(url: str) -> str:
    with urlopen(url) as response:
        return response.read().decode("utf-8")


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


def _resource_object_names(package: dict[str, Any]) -> tuple[str, ...]:
    resources = package.get("resources", [])
    if not isinstance(resources, list):
        return ()
    names: list[str] = []
    seen: set[str] = set()
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        object_name = str(resource.get("object_name") or "").strip()
        if object_name and object_name not in seen:
            names.append(object_name)
            seen.add(object_name)
    return tuple(names)


def _replacement_family_priority(
    *,
    original_query: str,
    candidate: BcdcReplacementFamilyCandidate,
) -> tuple[int, str]:
    normalized_query = original_query.strip().upper()
    title = candidate.title.upper()
    object_names = tuple(name.upper() for name in candidate.object_names)

    score = 0
    if "MULE_DEER" in normalized_query:
        if "CARIBOO" in title or any("_CAR_" in name for name in object_names):
            score += 5
        if any(
            name.startswith("REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER")
            for name in object_names
        ):
            score += 3
        if any("RNG_TOPO" in name for name in object_names) or (
            "TOPOGRAPHIC BUFFERS" in title
        ):
            score += 2
        if any("HAB_MG_ZN" in name for name in object_names) or (
            "HABITAT MANAGEMENT ZONES" in title
        ):
            score += 1
        if "LILLOOET" in title:
            score -= 2
    if "PIP_CONSULTATION" in normalized_query:
        if "CONSULTATION" in title:
            score += 3
        if "PIP" in title or "INDIGENOUS" in title:
            score += 2
    if "BURN_SEVERITY" in normalized_query:
        if any(
            name.startswith("WHSE_FOREST_VEGETATION.VEG_BURN_SEVERITY")
            for name in object_names
        ):
            score += 4
        if "BURN SEVERITY" in title:
            score += 2

    return (score, candidate.title.casefold())


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
    normalized_query = _normalize_text(query)
    if object_name and _normalize_text(object_name) == normalized_query:
        return (OBJECT_NAME_MATCH_SCORE, f"object_name:{object_name}")
    _, object_local_name = _split_query_namespace(object_name)
    normalized_object_local = _normalize_text(object_local_name)
    if object_local_name and normalized_object_local == normalized_query:
        return (OBJECT_NAME_SUFFIX_MATCH_SCORE, f"object_name_suffix:{object_name}")
    if normalized_query:
        if object_name and _normalize_text(object_name).startswith(
            f"{normalized_query}_"
        ):
            return (OBJECT_NAME_STEM_MATCH_SCORE, f"object_name_stem:{object_name}")
        if object_local_name and normalized_object_local.startswith(
            f"{normalized_query}_"
        ):
            return (OBJECT_NAME_STEM_MATCH_SCORE, f"object_name_stem:{object_name}")
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


def _build_resource_match(
    query: str,
    resource: dict[str, Any],
    *,
    probe_service_fn: Callable[
        [dict[str, Any]],
        tuple[str | None, bool, str | None, str | None, str | None, tuple[str, ...]],
    ],
) -> BcdcResourceMatch:
    match_score, matched_by = _score_resource(query, resource)
    classification, notes = _classify_resource(resource)
    (
        service_type,
        wfs_queryable,
        wfs_capabilities_url,
        wfs_typename,
        suggested_fetch_strategy,
        service_notes,
    ) = probe_service_fn(resource)
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
        service_type=service_type,
        wfs_queryable=wfs_queryable,
        wfs_capabilities_url=wfs_capabilities_url,
        wfs_typename=wfs_typename,
        suggested_fetch_strategy=suggested_fetch_strategy,
        matched_by=matched_by,
        match_score=match_score,
        notes=notes + service_notes,
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


def _package_fetchable_wfs_resource(
    resources: tuple[BcdcResourceMatch, ...],
    *,
    package_match_score: int,
) -> BcdcResourceMatch | None:
    for resource in resources:
        if (
            resource.match_score == package_match_score
            and resource.classification == SERVICE
            and resource.wfs_queryable
            and resource.wfs_typename is not None
            and resource.url is not None
            and resource.suggested_fetch_strategy is not None
        ):
            return resource
    return None


def _package_manual_follow_up(
    resources: tuple[BcdcResourceMatch, ...],
    *,
    package_match_score: int,
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
    if (
        _package_fetchable_wfs_resource(
            resources,
            package_match_score=package_match_score,
        )
        is not None
    ):
        notes.append(
            "Top match includes WFS-queryable OpenMaps service resources; a later AOI-scoped fetch path can use these service hints directly."
        )
    if any(resource.classification == SUPPORTING_DOCUMENT for resource in resources):
        notes.append(
            "Supporting documents are available for manual review but are not auto-downloaded in v1."
        )
    return tuple(notes)


def _package_suggested_fetch_strategy(
    resources: tuple[BcdcResourceMatch, ...],
    *,
    package_match_score: int,
) -> str | None:
    resource = _package_fetchable_wfs_resource(
        resources,
        package_match_score=package_match_score,
    )
    return None if resource is None else resource.suggested_fetch_strategy


def _make_service_probe_fn(
    *,
    fetch_text_fn: Callable[[str], str],
) -> Callable[
    [dict[str, Any]],
    tuple[str | None, bool, str | None, str | None, str | None, tuple[str, ...]],
]:
    def _probe(
        resource: dict[str, Any],
    ) -> tuple[
        str | None,
        bool,
        str | None,
        str | None,
        str | None,
        tuple[str, ...],
    ]:
        return _probe_service_resource(resource, fetch_text_fn=fetch_text_fn)

    return _probe


def _build_package_match(
    query: str,
    package: dict[str, Any],
    *,
    probe_service_fn: Callable[
        [dict[str, Any]],
        tuple[str | None, bool, str | None, str | None, str | None, tuple[str, ...]],
    ]
    | None = None,
) -> BcdcPackageMatch:
    if probe_service_fn is None:
        probe_service_fn = _make_service_probe_fn(fetch_text_fn=_fetch_text)
    resources = tuple(
        sorted(
            (
                _build_resource_match(
                    query,
                    resource,
                    probe_service_fn=probe_service_fn,
                )
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
        suggested_fetch_strategy=_package_suggested_fetch_strategy(
            resources,
            package_match_score=package_score,
        ),
        manual_follow_up=_package_manual_follow_up(
            resources,
            package_match_score=package_score,
        ),
    )


def _has_good_match(matches: tuple[BcdcPackageMatch, ...]) -> bool:
    return bool(matches) and matches[0].match_score >= OBJECT_SHORT_NAME_MATCH_SCORE


def _merge_package_matches(
    existing: dict[str, BcdcPackageMatch],
    query: str,
    rows: list[dict[str, Any]],
    *,
    probe_service_fn: Callable[
        [dict[str, Any]],
        tuple[str | None, bool, str | None, str | None, str | None, tuple[str, ...]],
    ],
) -> None:
    for row in rows:
        match = _build_package_match(query, row, probe_service_fn=probe_service_fn)
        current = existing.get(match.package_id)
        if current is None or (
            match.match_score,
            match.title.casefold(),
        ) > (
            current.match_score,
            current.title.casefold(),
        ):
            existing[match.package_id] = match


def suggest_bcdc_replacement_family(
    query: str,
    *,
    limit: int = 5,
    fetch_json_fn: Callable[[str], dict[str, Any]] | None = None,
) -> tuple[BcdcReplacementFamilyCandidate, ...]:
    """Return review-only public replacement candidates for selected stale TSR tokens."""

    fetch_json = fetch_json_fn or _fetch_json
    search_terms = _replacement_family_search_terms(query)
    if not search_terms:
        return ()

    candidates: list[BcdcReplacementFamilyCandidate] = []
    seen_pages: set[str] = set()
    for search_term, rationale in search_terms:
        url = _build_keyword_search_url(search_term, rows=max(limit * 2, 10))
        payload = fetch_json(url)
        for package in _extract_package_rows(payload):
            title = str(package.get("title") or "").strip()
            package_name = str(package.get("name") or "").strip()
            dataset_page_url = (
                f"{BCDC_DATASET_PAGE_URL}/{package_name}" if package_name else ""
            )
            if not title or not dataset_page_url or dataset_page_url in seen_pages:
                continue
            object_names = _resource_object_names(package)
            if not object_names and "PIP_CONSULTATION" not in query.upper():
                continue
            candidates.append(
                BcdcReplacementFamilyCandidate(
                    title=title,
                    dataset_page_url=dataset_page_url,
                    object_names=object_names,
                    matched_query=search_term,
                    rationale=rationale,
                )
            )
            seen_pages.add(dataset_page_url)
    ranked_candidates = sorted(
        candidates,
        key=lambda candidate: _replacement_family_priority(
            original_query=query,
            candidate=candidate,
        ),
        reverse=True,
    )
    return tuple(ranked_candidates[:limit])


def resolve_bcdc_candidates(query: str, *, limit: int = 5) -> BcdcResolveResult:
    """Resolve one query against the BC Data Catalogue API."""

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("BCDC query must not be blank.")

    api_urls: list[str] = []
    package_matches: dict[str, BcdcPackageMatch] = {}
    probe_service_fn = _make_service_probe_fn(fetch_text_fn=_fetch_text)

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
            probe_service_fn=probe_service_fn,
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
                probe_service_fn=probe_service_fn,
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
    query_slug: str | None = None,
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

    query_root = resolved_root / _slugify_query(query_slug or result.query)
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
