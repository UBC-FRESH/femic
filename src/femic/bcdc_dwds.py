"""DWDS fallback helpers for BC Data Catalogue feature-type orders."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from femic.bcdc_catalog import (
    BcdcPackageMatch,
    BcdcResourceMatch,
    resolve_bcdc_candidates,
)
from femic.bcdc_fetch import GeomarkBBox


DWDS_BASE_URL = "https://apps.gov.bc.ca/pub/dwds-ofi"
DWDS_CREATE_ORDER_FILTERED_URL = f"{DWDS_BASE_URL}/order/createOrderFiltered"
DWDS_ORDER_STATUS_URL_TEMPLATE = f"{DWDS_BASE_URL}/order/{{order_id}}"
DWDS_PRODUCT_ALLOWED_URL_TEMPLATE = (
    f"{DWDS_BASE_URL}/security/productAllowedByFeatureType/{{feature_type}}"
)
DWDS_DEFAULT_ORDERING_APPLICATION = "FEMIC-BCDC-DWDS"
DWDS_DEFAULT_CRS_TYPE_ID = "0"  # BC Albers
DWDS_CLIP_METHOD_ID = "0"
DWDS_NO_CLIP_METHOD_ID = "1"
DWDS_CUSTOM_GML_AOI_TYPE_ID = "1"
DWDS_ORDER_FORMAT_IDS = {
    "shp": "0",
    "fgdb": "3",
    "geojson": "6",
    "gpkg": "7",
}
DWDS_DEFAULT_OUTPUT_FORMAT = "fgdb"


class BcdcDwdsError(RuntimeError):
    """Raised when a DWDS fallback order cannot be created or interpreted."""


@dataclass(frozen=True)
class BcdcDwdsStatusProbe:
    """One post-submission probe against the public DWDS order-status seam."""

    order_id: str
    raw_payload: dict[str, Any]
    status: str | None
    description: str | None
    value: str | None
    download_url: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "status": self.status,
            "description": self.description,
            "value": self.value,
            "download_url": self.download_url,
            "raw_payload": self.raw_payload,
        }


@dataclass(frozen=True)
class BcdcDwdsOrderResult:
    """One DWDS order submission result for a resolved BCDC query."""

    query: str
    limit: int
    generated_utc: str
    package_id: str
    package_name: str
    package_title: str
    dataset_page_url: str
    resource_id: str
    resource_name: str
    resource_url: str | None
    feature_type: str
    matched_by: str
    aoi_source: str
    bbox_epsg3005: tuple[float, float, float, float]
    geomark_id: str | None
    geomark_url: str | None
    output_format: str
    email_address: str | None
    clipping_method: str
    ordering_application: str
    request_url: str
    request_payload: dict[str, object]
    order_id: str
    order_guid: str | None
    submission_status: str
    submission_description: str
    submission_value: str | None
    status_probe: BcdcDwdsStatusProbe | None
    warnings: tuple[str, ...] = ()
    latest_followup_utc: str | None = None
    latest_followup_status_probe: BcdcDwdsStatusProbe | None = None
    materialized_artifact_path: str | None = None
    materialized_download_url: str | None = None
    materialized_content_type: str | None = None
    materialized_bytes: int | None = None
    followup_warnings: tuple[str, ...] = ()

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
            "feature_type": self.feature_type,
            "matched_by": self.matched_by,
            "aoi_source": self.aoi_source,
            "bbox_epsg3005": list(self.bbox_epsg3005),
            "geomark_id": self.geomark_id,
            "geomark_url": self.geomark_url,
            "output_format": self.output_format,
            "email_address": self.email_address,
            "clipping_method": self.clipping_method,
            "ordering_application": self.ordering_application,
            "request_url": self.request_url,
            "request_payload": self.request_payload,
            "order_id": self.order_id,
            "order_guid": self.order_guid,
            "submission_status": self.submission_status,
            "submission_description": self.submission_description,
            "submission_value": self.submission_value,
            "status_probe": (
                self.status_probe.to_dict() if self.status_probe is not None else None
            ),
            "warnings": list(self.warnings),
            "latest_followup_utc": self.latest_followup_utc,
            "latest_followup_status_probe": (
                self.latest_followup_status_probe.to_dict()
                if self.latest_followup_status_probe is not None
                else None
            ),
            "materialized_artifact_path": self.materialized_artifact_path,
            "materialized_download_url": self.materialized_download_url,
            "materialized_content_type": self.materialized_content_type,
            "materialized_bytes": self.materialized_bytes,
            "followup_warnings": list(self.followup_warnings),
        }


def _fetch_json(url: str) -> dict[str, Any]:
    try:
        with urlopen(url) as response:
            return json.load(response)
    except HTTPError as exc:  # pragma: no cover - network branch
        detail = exc.read().decode("utf-8", errors="replace")
        raise BcdcDwdsError(f"Unable to fetch DWDS JSON from {url}: {detail}") from exc
    except URLError as exc:  # pragma: no cover - network branch
        raise BcdcDwdsError(f"Unable to fetch DWDS JSON from {url}: {exc}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed branch
        raise BcdcDwdsError(f"Unable to parse DWDS JSON from {url}: {exc}") from exc


def _post_json(url: str, payload: dict[str, object]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request) as response:
            return json.load(response)
    except HTTPError as exc:  # pragma: no cover - network branch
        detail = exc.read().decode("utf-8", errors="replace")
        raise BcdcDwdsError(
            f"Unable to submit DWDS order to {url}: HTTP {exc.code}: {detail}"
        ) from exc
    except URLError as exc:  # pragma: no cover - network branch
        raise BcdcDwdsError(f"Unable to submit DWDS order to {url}: {exc}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed branch
        raise BcdcDwdsError(
            f"Unable to parse DWDS order response from {url}: {exc}"
        ) from exc


def _select_dwds_feature_resource(match: BcdcPackageMatch) -> BcdcResourceMatch | None:
    preferred = [
        resource
        for resource in match.resources
        if resource.object_name
        and resource.classification == "indirect_custom_download"
    ]
    if preferred:
        return preferred[0]
    for resource in match.resources:
        if resource.object_name:
            return resource
    return None


def _probe_dwds_product_allowed(feature_type: str) -> bool:
    payload = _fetch_json(
        DWDS_PRODUCT_ALLOWED_URL_TEMPLATE.format(
            feature_type=quote(feature_type, safe=".")
        )
    )
    return bool(payload.get("allowed"))


def _build_gml_aoi(bbox_epsg3005: tuple[float, float, float, float]) -> str:
    minx, miny, maxx, maxy = bbox_epsg3005
    coordinates = (
        f"{minx},{miny} {maxx},{miny} {maxx},{maxy} {minx},{maxy} {minx},{miny}"
    )
    return (
        '<areaOfInterest xmlns:gml="http://www.opengis.net/gml">'
        "<gml:Polygon>"
        "<gml:outerBoundaryIs>"
        "<gml:LinearRing>"
        f"<gml:coordinates>{coordinates}</gml:coordinates>"
        "</gml:LinearRing>"
        "</gml:outerBoundaryIs>"
        "</gml:Polygon>"
        "</areaOfInterest>"
    )


def _extract_download_url(payload: dict[str, Any]) -> str | None:
    queue: list[Any] = [payload]
    while queue:
        current = queue.pop(0)
        if isinstance(current, dict):
            for value in current.values():
                queue.append(value)
        elif isinstance(current, list):
            queue.extend(current)
        elif isinstance(current, str) and current.startswith(("http://", "https://")):
            return current
    return None


def _status_probe_from_payload(payload: dict[str, Any] | None) -> BcdcDwdsStatusProbe | None:
    if not isinstance(payload, dict):
        return None
    order_id = payload.get("order_id")
    if order_id is None:
        return None
    return BcdcDwdsStatusProbe(
        order_id=str(order_id),
        raw_payload=dict(payload.get("raw_payload", {}))
        if isinstance(payload.get("raw_payload"), dict)
        else payload,
        status=str(payload.get("status")) if payload.get("status") is not None else None,
        description=(
            str(payload.get("description"))
            if payload.get("description") is not None
            else None
        ),
        value=str(payload.get("value")) if payload.get("value") is not None else None,
        download_url=(
            str(payload.get("download_url"))
            if payload.get("download_url") is not None
            else None
        ),
    )


def _order_result_from_payload(payload: dict[str, Any]) -> BcdcDwdsOrderResult:
    bbox_payload = payload.get("bbox_epsg3005")
    if not isinstance(bbox_payload, list | tuple) or len(bbox_payload) != 4:
        raise BcdcDwdsError("DWDS manifest payload is missing a valid bbox_epsg3005 entry.")
    return BcdcDwdsOrderResult(
        query=str(payload["query"]),
        limit=int(payload["limit"]),
        generated_utc=str(payload["generated_utc"]),
        package_id=str(payload["package_id"]),
        package_name=str(payload["package_name"]),
        package_title=str(payload["package_title"]),
        dataset_page_url=str(payload["dataset_page_url"]),
        resource_id=str(payload["resource_id"]),
        resource_name=str(payload["resource_name"]),
        resource_url=(
            str(payload["resource_url"]) if payload.get("resource_url") is not None else None
        ),
        feature_type=str(payload["feature_type"]),
        matched_by=str(payload["matched_by"]),
        aoi_source=str(payload["aoi_source"]),
        bbox_epsg3005=tuple(float(value) for value in bbox_payload),  # type: ignore[arg-type]
        geomark_id=str(payload["geomark_id"]) if payload.get("geomark_id") is not None else None,
        geomark_url=(
            str(payload["geomark_url"]) if payload.get("geomark_url") is not None else None
        ),
        output_format=str(payload["output_format"]),
        email_address=(
            str(payload["email_address"]) if payload.get("email_address") is not None else None
        ),
        clipping_method=str(payload["clipping_method"]),
        ordering_application=str(payload["ordering_application"]),
        request_url=str(payload["request_url"]),
        request_payload=(
            dict(payload.get("request_payload", {}))
            if isinstance(payload.get("request_payload"), dict)
            else {}
        ),
        order_id=str(payload["order_id"]),
        order_guid=str(payload["order_guid"]) if payload.get("order_guid") is not None else None,
        submission_status=str(payload["submission_status"]),
        submission_description=str(payload["submission_description"]),
        submission_value=(
            str(payload["submission_value"])
            if payload.get("submission_value") is not None
            else None
        ),
        status_probe=_status_probe_from_payload(payload.get("status_probe")),
        warnings=tuple(str(item) for item in payload.get("warnings", [])),
        latest_followup_utc=(
            str(payload["latest_followup_utc"])
            if payload.get("latest_followup_utc") is not None
            else None
        ),
        latest_followup_status_probe=_status_probe_from_payload(
            payload.get("latest_followup_status_probe")
        ),
        materialized_artifact_path=(
            str(payload["materialized_artifact_path"])
            if payload.get("materialized_artifact_path") is not None
            else None
        ),
        materialized_download_url=(
            str(payload["materialized_download_url"])
            if payload.get("materialized_download_url") is not None
            else None
        ),
        materialized_content_type=(
            str(payload["materialized_content_type"])
            if payload.get("materialized_content_type") is not None
            else None
        ),
        materialized_bytes=(
            int(payload["materialized_bytes"])
            if payload.get("materialized_bytes") is not None
            else None
        ),
        followup_warnings=tuple(str(item) for item in payload.get("followup_warnings", [])),
    )


def load_bcdc_dwds_manifest(path: Path) -> list[BcdcDwdsOrderResult]:
    """Load one or more DWDS order results from a previously written manifest."""

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise BcdcDwdsError(f"DWDS manifest not found: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BcdcDwdsError(f"Unable to parse DWDS manifest {resolved}: {exc}") from exc

    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return [
            _order_result_from_payload(item)
            for item in payload["results"]
            if isinstance(item, dict)
        ]
    if isinstance(payload, list):
        return [_order_result_from_payload(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [_order_result_from_payload(payload)]
    raise BcdcDwdsError(f"Unsupported DWDS manifest payload shape in {resolved}")


def _infer_dwds_download_filename(
    *,
    download_url: str,
    feature_type: str,
    output_format: str,
    order_id: str,
    content_disposition: str | None,
    content_type: str | None,
) -> str:
    if content_disposition:
        lower = content_disposition.lower()
        marker = "filename="
        if marker in lower:
            raw = content_disposition[lower.index(marker) + len(marker) :].strip()
            candidate = raw.strip().strip('"').strip("'")
            if candidate:
                return Path(candidate).name
    parsed = urlparse(download_url)
    if parsed.path:
        candidate = Path(parsed.path).name
        if candidate:
            return candidate
    default_suffix = {
        "fgdb": ".zip",
        "shp": ".zip",
        "gpkg": ".gpkg",
        "geojson": ".geojson",
    }.get(output_format.casefold(), ".bin")
    safe_feature_type = feature_type.replace(".", "_").replace(":", "_")
    if content_type and "zip" in content_type.casefold() and default_suffix != ".zip":
        default_suffix = ".zip"
    return f"{safe_feature_type}__order_{order_id}{default_suffix}"


def _download_dwds_artifact(
    *,
    download_url: str,
    destination_root: Path,
    feature_type: str,
    output_format: str,
    order_id: str,
) -> tuple[Path, str | None, int]:
    destination_root.mkdir(parents=True, exist_ok=True)
    request = Request(download_url, headers={"Accept": "*/*"}, method="GET")
    try:
        with urlopen(request) as response:
            content_type = response.headers.get("Content-Type")
            filename = _infer_dwds_download_filename(
                download_url=download_url,
                feature_type=feature_type,
                output_format=output_format,
                order_id=order_id,
                content_disposition=response.headers.get("Content-Disposition"),
                content_type=content_type,
            )
            target_path = destination_root / filename
            content = response.read()
    except HTTPError as exc:  # pragma: no cover - network branch
        detail = exc.read().decode("utf-8", errors="replace")
        raise BcdcDwdsError(
            f"Unable to download DWDS artifact from {download_url}: HTTP {exc.code}: {detail}"
        ) from exc
    except URLError as exc:  # pragma: no cover - network branch
        raise BcdcDwdsError(f"Unable to download DWDS artifact from {download_url}: {exc}") from exc

    target_path.write_bytes(content)
    return target_path.resolve(), content_type, len(content)


def _probe_dwds_order_status(order_id: str) -> BcdcDwdsStatusProbe:
    payload = _fetch_json(DWDS_ORDER_STATUS_URL_TEMPLATE.format(order_id=order_id))
    return BcdcDwdsStatusProbe(
        order_id=order_id,
        raw_payload=payload,
        status=str(payload.get("Status"))
        if payload.get("Status") is not None
        else None,
        description=(
            str(payload.get("Description"))
            if payload.get("Description") is not None
            else None
        ),
        value=str(payload.get("Value")) if payload.get("Value") is not None else None,
        download_url=_extract_download_url(payload),
    )


def follow_up_bcdc_dwds_order(
    order_result: BcdcDwdsOrderResult,
    *,
    download_root: Path | None = None,
    poll_status: bool = True,
) -> BcdcDwdsOrderResult:
    """Re-probe a submitted DWDS order and materialize its artifact when ready."""

    latest_probe = (
        _probe_dwds_order_status(order_result.order_id)
        if poll_status
        else order_result.latest_followup_status_probe or order_result.status_probe
    )
    followup_warnings: list[str] = []
    artifact_path = order_result.materialized_artifact_path
    artifact_download_url = order_result.materialized_download_url
    artifact_content_type = order_result.materialized_content_type
    artifact_bytes = order_result.materialized_bytes

    effective_download_url = latest_probe.download_url if latest_probe is not None else None
    if effective_download_url is None:
        if poll_status:
            followup_warnings.append(
                "DWDS follow-up did not expose a download URL yet; keep the order manifest and retry later."
            )
    elif download_root is None:
        followup_warnings.append(
            "DWDS follow-up found a download URL, but no download root was supplied for materialization."
        )
    else:
        downloaded_path, content_type, byte_count = _download_dwds_artifact(
            download_url=effective_download_url,
            destination_root=download_root,
            feature_type=order_result.feature_type,
            output_format=order_result.output_format,
            order_id=order_result.order_id,
        )
        artifact_path = str(downloaded_path)
        artifact_download_url = effective_download_url
        artifact_content_type = content_type
        artifact_bytes = byte_count

    return replace(
        order_result,
        status_probe=latest_probe,
        latest_followup_utc=datetime.now(UTC).isoformat(),
        latest_followup_status_probe=latest_probe,
        materialized_artifact_path=artifact_path,
        materialized_download_url=artifact_download_url,
        materialized_content_type=artifact_content_type,
        materialized_bytes=artifact_bytes,
        followup_warnings=tuple(followup_warnings),
    )


def submit_bcdc_dwds_order(
    query: str,
    *,
    bbox_epsg3005: tuple[float, float, float, float],
    output_format: str = DWDS_DEFAULT_OUTPUT_FORMAT,
    limit: int = 5,
    geomark: GeomarkBBox | None = None,
    email_address: str | None = None,
    clip_to_aoi: bool = True,
    poll_status: bool = True,
    ordering_application: str = DWDS_DEFAULT_ORDERING_APPLICATION,
) -> BcdcDwdsOrderResult:
    """Submit a public DWDS order for the top-ranked BCDC package match."""

    format_id = DWDS_ORDER_FORMAT_IDS.get(output_format.casefold())
    if format_id is None:
        supported = ", ".join(sorted(DWDS_ORDER_FORMAT_IDS))
        raise BcdcDwdsError(
            f"Unsupported DWDS output format `{output_format}`. Use one of: {supported}."
        )

    resolve_result = resolve_bcdc_candidates(query, limit=limit)
    top_match = resolve_result.top_match
    if top_match is None:
        raise BcdcDwdsError(f"No BCDC package matches were found for `{query}`.")

    resource = _select_dwds_feature_resource(top_match)
    if resource is None or not resource.object_name:
        raise BcdcDwdsError(
            "Top-ranked BCDC package does not expose a BCGW feature type that can be "
            "submitted through DWDS."
        )

    feature_type = resource.object_name
    if not _probe_dwds_product_allowed(feature_type):
        raise BcdcDwdsError(
            f"DWDS does not report public download permission for `{feature_type}`."
        )

    request_payload: dict[str, object] = {
        "emailAddress": email_address or "",
        "aoiType": DWDS_CUSTOM_GML_AOI_TYPE_ID,
        "aoi": _build_gml_aoi(bbox_epsg3005),
        "crsType": DWDS_DEFAULT_CRS_TYPE_ID,
        "clippingMethodType": (
            DWDS_CLIP_METHOD_ID if clip_to_aoi else DWDS_NO_CLIP_METHOD_ID
        ),
        "formatType": format_id,
        "useAOIBounds": "0",
        "aoiName": f"femic_{query}",
        "prepackagedItems": "",
        "orderingApplication": ordering_application,
        "featureItems": [{"featureItem": feature_type, "filterValue": ""}],
    }
    response_payload = _post_json(DWDS_CREATE_ORDER_FILTERED_URL, request_payload)

    submission_status = str(response_payload.get("Status", ""))
    submission_description = str(response_payload.get("Description", ""))
    submission_value = (
        str(response_payload.get("Value"))
        if response_payload.get("Value") is not None
        else None
    )
    if submission_status.casefold() != "success" or not submission_value:
        raise BcdcDwdsError(
            f"DWDS order submission failed for `{feature_type}`: "
            f"{submission_description or submission_status or 'unknown error'}"
        )

    warnings: list[str] = []
    status_probe: BcdcDwdsStatusProbe | None = None
    if geomark is not None:
        warnings.append(
            "DWDS geomark passthrough is unreliable in live probes; FEMIC resolved "
            "`--geomark` to a bbox-derived custom GML AOI for this order."
        )
    if poll_status:
        status_probe = _probe_dwds_order_status(submission_value)
        if (
            status_probe.status == "FAILURE"
            and status_probe.value == "6"
            and status_probe.description is not None
        ):
            warnings.append(
                "DWDS accepted the order submission, but the public `/order/{id}` "
                "status seam still reported the order as missing in live probes."
            )

    return BcdcDwdsOrderResult(
        query=query,
        limit=limit,
        generated_utc=datetime.now(UTC).isoformat(),
        package_id=top_match.package_id,
        package_name=top_match.package_name,
        package_title=top_match.title,
        dataset_page_url=top_match.dataset_page_url,
        resource_id=resource.resource_id,
        resource_name=resource.name,
        resource_url=resource.url,
        feature_type=feature_type,
        matched_by=top_match.matched_by,
        aoi_source="geomark" if geomark is not None else "bbox",
        bbox_epsg3005=bbox_epsg3005,
        geomark_id=geomark.geomark_id if geomark is not None else None,
        geomark_url=geomark.geomark_url if geomark is not None else None,
        output_format=output_format.casefold(),
        email_address=email_address,
        clipping_method="clip_to_aoi" if clip_to_aoi else "not_clipped",
        ordering_application=ordering_application,
        request_url=DWDS_CREATE_ORDER_FILTERED_URL,
        request_payload=request_payload,
        order_id=submission_value,
        order_guid=(
            str(response_payload.get("OrderGUID"))
            if response_payload.get("OrderGUID") is not None
            else None
        ),
        submission_status=submission_status,
        submission_description=submission_description,
        submission_value=submission_value,
        status_probe=status_probe,
        warnings=tuple(warnings),
    )


def write_bcdc_dwds_manifest(
    results: BcdcDwdsOrderResult | list[BcdcDwdsOrderResult],
    path: Path,
) -> Path:
    """Write one or more DWDS order results to a JSON manifest."""

    payload = (
        [result.to_dict() for result in results]
        if isinstance(results, list)
        else results.to_dict()
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
