"""AOI-scoped WFS acquisition helpers for BC Data Catalogue resources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import urlopen

import geopandas as gpd  # type: ignore[import-untyped]
from pyproj import Transformer
from shapely import wkt  # type: ignore[import-untyped]
from shapely.ops import transform as shapely_transform  # type: ignore[import-untyped]

from femic.bcdc_catalog import (
    BcdcPackageMatch,
    BcdcResourceMatch,
    SERVICE,
    resolve_bcdc_candidates,
)


GEOMARK_BOUNDING_BOX_URL_TEMPLATE = (
    "https://apps.gov.bc.ca/pub/geomark/geomarks/{geomark_id}/boundingBox.json"
)
DEFAULT_WFS_OUTPUT_FORMAT = "gpkg"
SUPPORTED_WFS_OUTPUT_FORMATS = {"gpkg", "geojson"}
BC_ALBERS_EPSG = "EPSG:3005"
WGS84_EPSG = "EPSG:4326"
DEFAULT_WFS_PAGE_SIZE = 10000
DEFAULT_WFS_TILE_MAX_DEPTH = 8


class BcdcFetchError(RuntimeError):
    """Raised when WFS-backed BCDC acquisition cannot proceed."""


@dataclass(frozen=True)
class GeomarkBBox:
    """Normalized Geomark AOI as an EPSG:3005 bounding box."""

    geomark_id: str
    geomark_url: str
    bbox_epsg3005: tuple[float, float, float, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "geomark_id": self.geomark_id,
            "geomark_url": self.geomark_url,
            "bbox_epsg3005": list(self.bbox_epsg3005),
        }


@dataclass(frozen=True)
class BcdcFetchResult:
    """One AOI-scoped WFS fetch result for a resolved query."""

    query: str
    limit: int
    generated_utc: str
    package_id: str
    package_name: str
    package_title: str
    dataset_page_url: str
    resource_id: str
    resource_name: str
    resource_url: str
    wfs_typename: str
    matched_by: str
    suggested_fetch_strategy: str | None
    aoi_source: str
    bbox_epsg3005: tuple[float, float, float, float]
    geomark_id: str | None
    geomark_url: str | None
    request_url: str
    saved_path: Path
    output_format: str
    feature_count: int
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "limit": self.limit,
            "generated_utc": self.generated_utc,
            "package_id": self.package_id,
            "package_name": self.package_name,
            "package_title": self.package_title,
            "dataset_page_url": self.dataset_page_url,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "resource_url": self.resource_url,
            "wfs_typename": self.wfs_typename,
            "matched_by": self.matched_by,
            "suggested_fetch_strategy": self.suggested_fetch_strategy,
            "aoi_source": self.aoi_source,
            "bbox_epsg3005": list(self.bbox_epsg3005),
            "geomark_id": self.geomark_id,
            "geomark_url": self.geomark_url,
            "request_url": self.request_url,
            "saved_path": str(self.saved_path),
            "output_format": self.output_format,
            "feature_count": self.feature_count,
            "warnings": list(self.warnings),
        }


def _slugify_query(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
    return slug or "query"


def _fetch_json_payload(url: str) -> dict[str, Any]:
    try:
        with urlopen(url) as response:
            return json.load(response)
    except OSError as exc:  # pragma: no cover - network failure branch
        raise BcdcFetchError(f"Unable to fetch JSON from {url}: {exc}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed branch
        raise BcdcFetchError(f"Unable to parse JSON from {url}: {exc}") from exc


def _fetch_text_payload(url: str) -> str:
    try:
        with urlopen(url) as response:
            return response.read().decode("utf-8")
    except OSError as exc:  # pragma: no cover - network failure branch
        raise BcdcFetchError(f"Unable to fetch text from {url}: {exc}") from exc


def _normalize_geomark_id(value: str) -> str:
    text = value.strip()
    match = re.search(r"(gm-[A-Za-z0-9-]+)", text)
    if match is None:
        raise BcdcFetchError(
            "Invalid `--geomark` value. Supply a bare Geomark ID or a full Geomark URL."
        )
    return match.group(1)


def _parse_geomark_geometry_bounds_3005(
    geometry_text: str,
) -> tuple[float, float, float, float]:
    if ";" in geometry_text:
        _, wkt_text = geometry_text.split(";", 1)
    else:
        wkt_text = geometry_text
    try:
        geom_4326 = wkt.loads(wkt_text)
    except Exception as exc:  # pragma: no cover - malformed upstream geometry
        raise BcdcFetchError(f"Invalid Geomark geometry payload: {exc}") from exc
    transformer = Transformer.from_crs(WGS84_EPSG, BC_ALBERS_EPSG, always_xy=True)
    geom_3005 = shapely_transform(transformer.transform, geom_4326)
    minx, miny, maxx, maxy = geom_3005.bounds
    return (float(minx), float(miny), float(maxx), float(maxy))


def resolve_geomark_bbox_3005(geomark_ref: str) -> GeomarkBBox:
    """Resolve a Geomark reference into a normalized EPSG:3005 bounding box."""

    geomark_id = _normalize_geomark_id(geomark_ref)
    url = GEOMARK_BOUNDING_BOX_URL_TEMPLATE.format(geomark_id=geomark_id)
    payload = _fetch_json_payload(url)
    geometry_text = str(payload.get("geometry", "")).strip()
    if not geometry_text:
        raise BcdcFetchError(
            f"Geomark {geomark_id} did not return a usable geometry payload."
        )
    bbox_epsg3005 = _parse_geomark_geometry_bounds_3005(geometry_text)
    return GeomarkBBox(
        geomark_id=geomark_id,
        geomark_url=str(
            payload.get("url")
            or f"https://apps.gov.bc.ca/pub/geomark/geomarks/{geomark_id}"
        ),
        bbox_epsg3005=bbox_epsg3005,
    )


def build_bbox_3005(value: str) -> tuple[float, float, float, float]:
    """Parse a CLI bbox string into an EPSG:3005 bbox tuple."""

    pieces = [piece.strip() for piece in value.split(",")]
    if len(pieces) != 4:
        raise BcdcFetchError(
            "Invalid `--bbox` value. Use `minx,miny,maxx,maxy` in EPSG:3005."
        )
    try:
        minx, miny, maxx, maxy = (float(piece) for piece in pieces)
    except ValueError as exc:
        raise BcdcFetchError(
            "Invalid `--bbox` value. Use numeric `minx,miny,maxx,maxy` in EPSG:3005."
        ) from exc
    if minx >= maxx or miny >= maxy:
        raise BcdcFetchError(
            "Invalid `--bbox` value. Expected `minx < maxx` and `miny < maxy`."
        )
    return (minx, miny, maxx, maxy)


def _build_wfs_getfeature_url(
    base_url: str,
    *,
    typename: str,
    bbox_epsg3005: tuple[float, float, float, float],
    count: int | None = None,
    start_index: int | None = None,
) -> str:
    parsed = urlparse(base_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    minx, miny, maxx, maxy = bbox_epsg3005
    params.update(
        {
            "service": "WFS",
            "request": "GetFeature",
            "version": "2.0.0",
            "typeNames": typename,
            "bbox": f"{minx},{miny},{maxx},{maxy},{BC_ALBERS_EPSG}",
            "outputFormat": "application/json",
            "srsName": BC_ALBERS_EPSG,
        }
    )
    if count is not None:
        params["count"] = str(int(count))
    if start_index is not None:
        params["startIndex"] = str(int(start_index))
    return urlunparse(parsed._replace(query=urlencode(params)))


def _select_wfs_resource(match: BcdcPackageMatch) -> BcdcResourceMatch | None:
    for resource in match.resources:
        if (
            resource.classification == SERVICE
            and resource.wfs_queryable
            and resource.wfs_typename
            and resource.url
        ):
            return resource
    return None


def _write_geojson_payload(payload: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_gpkg_payload(
    payload: dict[str, Any],
    *,
    destination: Path,
    layer_name: str,
) -> None:
    features = payload.get("features", [])
    if not isinstance(features, list):
        raise BcdcFetchError(
            "WFS response did not contain a valid GeoJSON feature list."
        )
    if features:
        gdf = gpd.GeoDataFrame.from_features(features, crs=BC_ALBERS_EPSG)
    else:
        gdf = gpd.GeoDataFrame(geometry=[], crs=BC_ALBERS_EPSG)
    destination.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(destination, driver="GPKG", layer=layer_name)


def _save_wfs_payload(
    payload: dict[str, Any],
    *,
    destination_root: Path,
    query: str,
    query_slug: str | None,
    output_format: str,
) -> Path:
    slug = _slugify_query(query_slug or query)
    output_dir = destination_root / slug
    if output_format == "geojson":
        destination = output_dir / f"{slug}.geojson"
        _write_geojson_payload(payload, destination)
        return destination
    if output_format == "gpkg":
        destination = output_dir / f"{slug}.gpkg"
        _write_gpkg_payload(payload, destination=destination, layer_name=slug[:63])
        return destination
    raise BcdcFetchError(
        f"Unsupported WFS output format `{output_format}`. "
        f"Expected one of: {', '.join(sorted(SUPPORTED_WFS_OUTPUT_FORMATS))}."
    )


def _feature_count_from_payload(payload: dict[str, Any]) -> int:
    raw_count = payload.get("numberReturned")
    if isinstance(raw_count, int):
        return raw_count
    features = payload.get("features", [])
    if isinstance(features, list):
        return len(features)
    return 0


def _coerce_number_matched(payload: dict[str, Any]) -> int | None:
    raw = payload.get("numberMatched")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return None


def _fetch_wfs_payload_paged(
    *,
    base_url: str,
    typename: str,
    bbox_epsg3005: tuple[float, float, float, float],
    page_size: int = DEFAULT_WFS_PAGE_SIZE,
) -> tuple[dict[str, Any], str, tuple[str, ...]]:
    first_request_url = _build_wfs_getfeature_url(
        base_url,
        typename=typename,
        bbox_epsg3005=bbox_epsg3005,
        count=page_size,
    )
    first_payload = _fetch_json_payload(first_request_url)
    number_matched = _coerce_number_matched(first_payload)
    first_features = first_payload.get("features", [])
    if not isinstance(first_features, list):
        raise BcdcFetchError(
            "WFS response did not contain a valid GeoJSON feature list."
        )
    if number_matched is None or number_matched <= len(first_features):
        return first_payload, first_request_url, ()

    all_features = list(first_features)
    start_index = len(first_features)
    while start_index < number_matched:
        page_url = _build_wfs_getfeature_url(
            base_url,
            typename=typename,
            bbox_epsg3005=bbox_epsg3005,
            count=page_size,
            start_index=start_index,
        )
        try:
            page_payload = _fetch_json_payload(page_url)
        except BcdcFetchError as exc:
            if "HTTP Error 400" not in str(exc):
                raise
            tiled_payload, tiled_warnings = _fetch_wfs_payload_tiled(
                base_url=base_url,
                typename=typename,
                bbox_epsg3005=bbox_epsg3005,
                page_size=page_size,
            )
            return tiled_payload, first_request_url, (
                "Paged WFS fetch fell back to recursive bbox tiling after the "
                "service rejected `startIndex` pagination.",
                *tiled_warnings,
            )
        page_features = page_payload.get("features", [])
        if not isinstance(page_features, list):
            raise BcdcFetchError(
                "Paged WFS response did not contain a valid GeoJSON feature list."
            )
        if not page_features:
            break
        all_features.extend(page_features)
        start_index += len(page_features)
        if len(page_features) < page_size:
            break

    merged_payload = dict(first_payload)
    merged_payload["features"] = all_features
    merged_payload["numberReturned"] = len(all_features)
    if number_matched is not None:
        merged_payload["numberMatched"] = number_matched
    warnings: list[str] = []
    if len(all_features) != number_matched:
        warnings.append(
            f"Paged WFS fetch expected `{number_matched}` features but assembled "
            f"`{len(all_features)}`."
        )
    else:
        warnings.append(
            f"Paged WFS fetch assembled `{len(all_features)}` features across multiple requests."
        )
    return merged_payload, first_request_url, tuple(warnings)


def _split_bbox_quadrants(
    bbox_epsg3005: tuple[float, float, float, float],
) -> tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]:
    minx, miny, maxx, maxy = bbox_epsg3005
    midx = (minx + maxx) / 2.0
    midy = (miny + maxy) / 2.0
    return (
        (minx, miny, midx, midy),
        (midx, miny, maxx, midy),
        (minx, midy, midx, maxy),
        (midx, midy, maxx, maxy),
    )


def _feature_dedupe_key(feature: dict[str, Any]) -> str:
    raw_id = feature.get("id")
    if raw_id not in (None, ""):
        return f"id:{raw_id}"
    properties = json.dumps(feature.get("properties", {}), sort_keys=True, default=str)
    geometry = json.dumps(feature.get("geometry", {}), sort_keys=True, default=str)
    return f"fallback:{properties}|{geometry}"


def _fetch_wfs_payload_tiled(
    *,
    base_url: str,
    typename: str,
    bbox_epsg3005: tuple[float, float, float, float],
    page_size: int,
    depth: int = 0,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    request_url = _build_wfs_getfeature_url(
        base_url,
        typename=typename,
        bbox_epsg3005=bbox_epsg3005,
        count=page_size,
    )
    payload = _fetch_json_payload(request_url)
    number_matched = _coerce_number_matched(payload)
    features = payload.get("features", [])
    if not isinstance(features, list):
        raise BcdcFetchError(
            "Tiled WFS response did not contain a valid GeoJSON feature list."
        )
    if number_matched is None or number_matched <= len(features):
        return payload, ()
    if depth >= DEFAULT_WFS_TILE_MAX_DEPTH:
        raise BcdcFetchError(
            "Recursive bbox tiling reached the maximum depth before the WFS "
            "response could be materialized without truncation."
        )

    merged_features: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen_keys: set[str] = set()
    for child_bbox in _split_bbox_quadrants(bbox_epsg3005):
        child_payload, child_warnings = _fetch_wfs_payload_tiled(
            base_url=base_url,
            typename=typename,
            bbox_epsg3005=child_bbox,
            page_size=page_size,
            depth=depth + 1,
        )
        child_features = child_payload.get("features", [])
        if not isinstance(child_features, list):
            raise BcdcFetchError(
                "Tiled WFS child response did not contain a valid GeoJSON feature list."
            )
        for feature in child_features:
            key = _feature_dedupe_key(feature)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            merged_features.append(feature)
        warnings.extend(child_warnings)

    merged_payload = dict(payload)
    merged_payload["features"] = merged_features
    merged_payload["numberReturned"] = len(merged_features)
    merged_payload["numberMatched"] = len(merged_features)
    warnings.append(
        f"Tiled WFS fetch assembled `{len(merged_features)}` unique features "
        f"at recursion depth `{depth + 1}`."
    )
    return merged_payload, tuple(warnings)


def fetch_bcdc_wfs_data(
    query: str,
    *,
    destination_root: Path,
    bbox_epsg3005: tuple[float, float, float, float],
    output_format: str = DEFAULT_WFS_OUTPUT_FORMAT,
    limit: int = 5,
    geomark: GeomarkBBox | None = None,
    query_slug: str | None = None,
) -> BcdcFetchResult:
    """Fetch AOI-scoped WFS data for the top-ranked WFS-capable BCDC resource."""

    normalized_format = output_format.strip().casefold()
    if normalized_format not in SUPPORTED_WFS_OUTPUT_FORMATS:
        raise BcdcFetchError(
            f"Unsupported `--output-format` value `{output_format}`. Use "
            "`gpkg` or `geojson`."
        )

    resolved = resolve_bcdc_candidates(query, limit=limit)
    top_match = resolved.top_match
    if top_match is None:
        raise BcdcFetchError(
            f"No catalogue match found for `{query}`. Run `femic data bcdc-resolve` "
            "first to inspect candidate packages."
        )

    wfs_resource = _select_wfs_resource(top_match)
    if wfs_resource is None:
        if top_match.direct_download_resources:
            raise BcdcFetchError(
                f"Top match for `{query}` exposes stable direct-download resources but "
                "no WFS-queryable service resource. Use "
                "`femic data bcdc-resolve --download-direct` instead."
            )
        raise BcdcFetchError(
            f"Top match for `{query}` does not expose a WFS-queryable service "
            "resource yet. Use `femic data bcdc-resolve` to inspect the package "
            "manually."
        )

    assert wfs_resource.url is not None
    assert wfs_resource.wfs_typename is not None
    payload, request_url, warnings = _fetch_wfs_payload_paged(
        base_url=wfs_resource.url,
        typename=wfs_resource.wfs_typename,
        bbox_epsg3005=bbox_epsg3005,
    )
    saved_path = _save_wfs_payload(
        payload,
        destination_root=destination_root.expanduser().resolve(),
        query=query,
        query_slug=query_slug,
        output_format=normalized_format,
    )

    return BcdcFetchResult(
        query=query,
        limit=limit,
        generated_utc=datetime.now(UTC).isoformat(),
        package_id=top_match.package_id,
        package_name=top_match.package_name,
        package_title=top_match.title,
        dataset_page_url=top_match.dataset_page_url,
        resource_id=wfs_resource.resource_id,
        resource_name=wfs_resource.name,
        resource_url=wfs_resource.url,
        wfs_typename=wfs_resource.wfs_typename,
        matched_by=top_match.matched_by,
        suggested_fetch_strategy=top_match.suggested_fetch_strategy,
        aoi_source="geomark" if geomark is not None else "bbox",
        bbox_epsg3005=bbox_epsg3005,
        geomark_id=geomark.geomark_id if geomark is not None else None,
        geomark_url=geomark.geomark_url if geomark is not None else None,
        request_url=request_url,
        saved_path=saved_path,
        output_format=normalized_format,
        feature_count=_feature_count_from_payload(payload),
        warnings=warnings,
    )


def write_bcdc_fetch_manifest(result: BcdcFetchResult, path: Path) -> Path:
    """Write one BCDC WFS fetch result to JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return resolved
