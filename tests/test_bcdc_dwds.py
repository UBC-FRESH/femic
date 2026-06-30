from __future__ import annotations

from pathlib import Path

import pytest

from femic import bcdc_catalog
from femic import bcdc_dwds
from femic.bcdc_fetch import GeomarkBBox


def _resolve_result_with_f_own() -> bcdc_catalog.BcdcResolveResult:
    return bcdc_catalog.BcdcResolveResult(
        query="WHSE_FOREST_VEGETATION.F_OWN",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        api_urls=("https://example.invalid/package_search",),
        matches=(
            bcdc_catalog.BcdcPackageMatch(
                package_id="pkg-f-own",
                package_name="generalized-forest-cover-ownership",
                title="Generalized Forest Cover Ownership",
                dataset_page_url=(
                    "https://catalogue.data.gov.bc.ca/dataset/"
                    "generalized-forest-cover-ownership"
                ),
                organization_name="forest-analysis-and-inventory",
                organization_title="Forest Analysis and Inventory Branch",
                license_title="Access Only",
                download_audience="Public",
                matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
                match_score=400,
                resources=(
                    bcdc_catalog.BcdcResourceMatch(
                        resource_id="dwds-id",
                        name="BC Geographic Warehouse Custom Download",
                        classification="indirect_custom_download",
                        url=None,
                        format="multiple",
                        bcdc_type="geographic",
                        object_name="WHSE_FOREST_VEGETATION.F_OWN",
                        object_short_name="F_OWN",
                        resource_access_method="indirect access",
                        resource_type="data",
                        resource_storage_location="bc geographic warehouse",
                        matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
                        match_score=400,
                        notes=(),
                    ),
                ),
                manual_follow_up=(),
            ),
        ),
        notes=(),
    )


def test_build_gml_aoi_contains_bbox_coordinates() -> None:
    gml = bcdc_dwds._build_gml_aoi((1170000.0, 450000.0, 1180000.0, 460000.0))

    assert "1170000.0,450000.0" in gml
    assert "1180000.0,460000.0" in gml
    assert "<areaOfInterest" in gml


def test_submit_bcdc_dwds_order_builds_payload_and_parses_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bcdc_dwds,
        "resolve_bcdc_candidates",
        lambda query, limit: _resolve_result_with_f_own(),
    )
    monkeypatch.setattr(bcdc_dwds, "_probe_dwds_product_allowed", lambda _ft: True)

    captured_payloads: list[dict[str, object]] = []

    def _fake_post(url: str, payload: dict[str, object]) -> dict[str, object]:
        captured_payloads.append(payload)
        return {
            "Status": "SUCCESS",
            "OrderGUID": "guid-123",
            "Description": "submitted",
            "Value": "2551000",
            "Warnings": "",
        }

    monkeypatch.setattr(bcdc_dwds, "_post_json", _fake_post)
    monkeypatch.setattr(
        bcdc_dwds,
        "_probe_dwds_order_status",
        lambda order_id: bcdc_dwds.BcdcDwdsStatusProbe(
            order_id=order_id,
            raw_payload={"Status": "FAILURE", "Description": "missing", "Value": "6"},
            status="FAILURE",
            description="missing",
            value="6",
            download_url=None,
        ),
    )

    result = bcdc_dwds.submit_bcdc_dwds_order(
        "WHSE_FOREST_VEGETATION.F_OWN",
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        output_format="fgdb",
        clip_to_aoi=True,
    )

    assert result.order_id == "2551000"
    assert result.order_guid == "guid-123"
    assert result.output_format == "fgdb"
    assert result.feature_type == "WHSE_FOREST_VEGETATION.F_OWN"
    assert result.status_probe is not None
    assert any("/order/{id}" in warning for warning in result.warnings)
    assert captured_payloads[0]["formatType"] == "3"
    assert captured_payloads[0]["clippingMethodType"] == "0"
    assert captured_payloads[0]["aoiType"] == "1"


def test_submit_bcdc_dwds_order_warns_when_geomark_is_bbox_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bcdc_dwds,
        "resolve_bcdc_candidates",
        lambda query, limit: _resolve_result_with_f_own(),
    )
    monkeypatch.setattr(bcdc_dwds, "_probe_dwds_product_allowed", lambda _ft: True)
    monkeypatch.setattr(
        bcdc_dwds,
        "_post_json",
        lambda url, payload: {
            "Status": "SUCCESS",
            "OrderGUID": "guid-123",
            "Description": "submitted",
            "Value": "2551001",
            "Warnings": "",
        },
    )
    monkeypatch.setattr(
        bcdc_dwds,
        "_probe_dwds_order_status",
        lambda order_id: bcdc_dwds.BcdcDwdsStatusProbe(
            order_id=order_id,
            raw_payload={},
            status=None,
            description=None,
            value=None,
            download_url=None,
        ),
    )

    result = bcdc_dwds.submit_bcdc_dwds_order(
        "WHSE_FOREST_VEGETATION.F_OWN",
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        geomark=GeomarkBBox(
            geomark_id="gm-demo",
            geomark_url="https://apps.gov.bc.ca/pub/geomark/geomarks/gm-demo",
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        ),
    )

    assert result.aoi_source == "geomark"
    assert result.geomark_id == "gm-demo"
    assert any("bbox-derived custom GML AOI" in warning for warning in result.warnings)


def test_submit_bcdc_dwds_order_rejects_unsupported_format() -> None:
    with pytest.raises(bcdc_dwds.BcdcDwdsError):
        bcdc_dwds.submit_bcdc_dwds_order(
            "WHSE_FOREST_VEGETATION.F_OWN",
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
            output_format="csv",
        )


def test_write_bcdc_dwds_manifest_writes_json(tmp_path: Path) -> None:
    result = bcdc_dwds.BcdcDwdsOrderResult(
        query="WHSE_FOREST_VEGETATION.F_OWN",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        package_id="pkg-f-own",
        package_name="generalized-forest-cover-ownership",
        package_title="Generalized Forest Cover Ownership",
        dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
        resource_id="dwds-id",
        resource_name="BC Geographic Warehouse Custom Download",
        resource_url=None,
        feature_type="WHSE_FOREST_VEGETATION.F_OWN",
        matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
        aoi_source="bbox",
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        geomark_id=None,
        geomark_url=None,
        output_format="fgdb",
        email_address=None,
        clipping_method="clip_to_aoi",
        ordering_application="FEMIC-BCDC-DWDS",
        request_url="https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
        request_payload={"featureItems": []},
        order_id="2551000",
        order_guid="guid-123",
        submission_status="SUCCESS",
        submission_description="submitted",
        submission_value="2551000",
        status_probe=None,
        warnings=(),
    )

    path = bcdc_dwds.write_bcdc_dwds_manifest(result, tmp_path / "manifest.json")

    assert path.is_file()
    assert '"order_id": "2551000"' in path.read_text(encoding="utf-8")


def test_load_bcdc_dwds_manifest_reads_single_payload(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        """
        {
          "query": "WHSE_FOREST_VEGETATION.F_OWN",
          "limit": 5,
          "generated_utc": "2026-04-04T00:00:00+00:00",
          "package_id": "pkg-f-own",
          "package_name": "generalized-forest-cover-ownership",
          "package_title": "Generalized Forest Cover Ownership",
          "dataset_page_url": "https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
          "resource_id": "dwds-id",
          "resource_name": "BC Geographic Warehouse Custom Download",
          "resource_url": null,
          "feature_type": "WHSE_FOREST_VEGETATION.F_OWN",
          "matched_by": "object_name:WHSE_FOREST_VEGETATION.F_OWN",
          "aoi_source": "bbox",
          "bbox_epsg3005": [1170000.0, 450000.0, 1180000.0, 460000.0],
          "geomark_id": null,
          "geomark_url": null,
          "output_format": "fgdb",
          "email_address": null,
          "clipping_method": "clip_to_aoi",
          "ordering_application": "FEMIC-BCDC-DWDS",
          "request_url": "https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
          "request_payload": {"featureItems": []},
          "order_id": "2551000",
          "order_guid": "guid-123",
          "submission_status": "SUCCESS",
          "submission_description": "submitted",
          "submission_value": "2551000",
          "status_probe": {
            "order_id": "2551000",
            "status": "FAILURE",
            "description": "missing",
            "value": "6",
            "download_url": null,
            "raw_payload": {"Status": "FAILURE", "Value": "6"}
          },
          "warnings": []
        }
        """,
        encoding="utf-8",
    )

    results = bcdc_dwds.load_bcdc_dwds_manifest(manifest_path)

    assert len(results) == 1
    assert results[0].order_id == "2551000"
    assert results[0].status_probe is not None
    assert results[0].status_probe.value == "6"


def test_extract_dwds_pickup_download_url_parses_launcher_page() -> None:
    html_text = """
    <html>
      <body>
        <p>
          Your download should begin shortly. If it does not, click
          <a id='pickup_link' href=https://distribution.data.gov.bc.ca/example.zip>here</a>.
        </p>
      </body>
    </html>
    """

    resolved = bcdc_dwds._extract_dwds_pickup_download_url(
        pickup_url="https://apps.gov.bc.ca/pub/dwds-rasp/pickupByGUID/guid-123",
        html_text=html_text,
    )

    assert resolved == "https://distribution.data.gov.bc.ca/example.zip"


def test_follow_up_bcdc_dwds_order_downloads_when_probe_has_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result = bcdc_dwds.BcdcDwdsOrderResult(
        query="WHSE_FOREST_VEGETATION.F_OWN",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        package_id="pkg-f-own",
        package_name="generalized-forest-cover-ownership",
        package_title="Generalized Forest Cover Ownership",
        dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
        resource_id="dwds-id",
        resource_name="BC Geographic Warehouse Custom Download",
        resource_url=None,
        feature_type="WHSE_FOREST_VEGETATION.F_OWN",
        matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
        aoi_source="bbox",
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        geomark_id=None,
        geomark_url=None,
        output_format="fgdb",
        email_address=None,
        clipping_method="clip_to_aoi",
        ordering_application="FEMIC-BCDC-DWDS",
        request_url="https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
        request_payload={"featureItems": []},
        order_id="2551000",
        order_guid="guid-123",
        submission_status="SUCCESS",
        submission_description="submitted",
        submission_value="2551000",
        status_probe=None,
        warnings=(),
    )
    monkeypatch.setattr(
        bcdc_dwds,
        "_probe_dwds_order_status",
        lambda order_id: bcdc_dwds.BcdcDwdsStatusProbe(
            order_id=order_id,
            raw_payload={"Status": "SUCCESS"},
            status="SUCCESS",
            description="ready",
            value="2551000",
            download_url="https://example.invalid/order_2551000.zip",
        ),
    )
    monkeypatch.setattr(
        bcdc_dwds,
        "_download_dwds_artifact",
        lambda **_kwargs: (tmp_path / "order_2551000.zip", "application/zip", 1234),
    )

    updated = bcdc_dwds.follow_up_bcdc_dwds_order(
        result,
        download_root=tmp_path,
        poll_status=True,
    )

    assert updated.materialized_artifact_path == str(tmp_path / "order_2551000.zip")
    assert updated.materialized_bytes == 1234
    assert updated.latest_followup_status_probe is not None
    assert updated.latest_followup_status_probe.download_url is not None


def test_follow_up_bcdc_dwds_order_uses_pickup_guid_when_status_probe_has_no_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result = bcdc_dwds.BcdcDwdsOrderResult(
        query="WHSE_FOREST_VEGETATION.F_OWN",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        package_id="pkg-f-own",
        package_name="generalized-forest-cover-ownership",
        package_title="Generalized Forest Cover Ownership",
        dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
        resource_id="dwds-id",
        resource_name="BC Geographic Warehouse Custom Download",
        resource_url=None,
        feature_type="WHSE_FOREST_VEGETATION.F_OWN",
        matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
        aoi_source="bbox",
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        geomark_id=None,
        geomark_url=None,
        output_format="fgdb",
        email_address="person@example.invalid",
        clipping_method="clip_to_aoi",
        ordering_application="FEMIC-BCDC-DWDS",
        request_url="https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
        request_payload={"featureItems": []},
        order_id="2551000",
        order_guid="guid-123",
        submission_status="SUCCESS",
        submission_description="submitted",
        submission_value="2551000",
        status_probe=None,
        warnings=(),
    )
    monkeypatch.setattr(
        bcdc_dwds,
        "_probe_dwds_order_status",
        lambda order_id: bcdc_dwds.BcdcDwdsStatusProbe(
            order_id=order_id,
            raw_payload={"Status": "FAILURE", "Value": "6"},
            status="FAILURE",
            description="missing",
            value="6",
            download_url=None,
        ),
    )
    monkeypatch.setattr(
        bcdc_dwds,
        "_resolve_dwds_pickup_download_url",
        lambda order_guid: (
            f"https://apps.gov.bc.ca/pub/dwds-rasp/pickupByGUID/{order_guid}",
            "https://distribution.data.gov.bc.ca/example.zip",
        ),
    )
    monkeypatch.setattr(
        bcdc_dwds,
        "_download_dwds_artifact",
        lambda **_kwargs: (tmp_path / "order_2551000.zip", "application/zip", 1234),
    )

    updated = bcdc_dwds.follow_up_bcdc_dwds_order(
        result,
        download_root=tmp_path,
        poll_status=True,
    )

    assert (
        updated.latest_followup_pickup_url
        == "https://apps.gov.bc.ca/pub/dwds-rasp/pickupByGUID/guid-123"
    )
    assert (
        updated.latest_followup_pickup_download_url
        == "https://distribution.data.gov.bc.ca/example.zip"
    )
    assert updated.materialized_artifact_path == str(tmp_path / "order_2551000.zip")
    assert (
        updated.materialized_download_url
        == "https://distribution.data.gov.bc.ca/example.zip"
    )


def test_follow_up_bcdc_dwds_order_records_warning_when_probe_has_no_download_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = bcdc_dwds.BcdcDwdsOrderResult(
        query="WHSE_FOREST_VEGETATION.F_OWN",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        package_id="pkg-f-own",
        package_name="generalized-forest-cover-ownership",
        package_title="Generalized Forest Cover Ownership",
        dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
        resource_id="dwds-id",
        resource_name="BC Geographic Warehouse Custom Download",
        resource_url=None,
        feature_type="WHSE_FOREST_VEGETATION.F_OWN",
        matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
        aoi_source="bbox",
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        geomark_id=None,
        geomark_url=None,
        output_format="fgdb",
        email_address=None,
        clipping_method="clip_to_aoi",
        ordering_application="FEMIC-BCDC-DWDS",
        request_url="https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
        request_payload={"featureItems": []},
        order_id="2551000",
        order_guid=None,
        submission_status="SUCCESS",
        submission_description="submitted",
        submission_value="2551000",
        status_probe=None,
        warnings=(),
    )
    monkeypatch.setattr(
        bcdc_dwds,
        "_probe_dwds_order_status",
        lambda order_id: bcdc_dwds.BcdcDwdsStatusProbe(
            order_id=order_id,
            raw_payload={"Status": "SUCCESS"},
            status="SUCCESS",
            description="queued",
            value="2551000",
            download_url=None,
        ),
    )

    updated = bcdc_dwds.follow_up_bcdc_dwds_order(result, download_root=None)

    assert updated.materialized_artifact_path is None
    assert any(
        "did not expose a download URL" in warning
        for warning in updated.followup_warnings
    )


def test_follow_up_bcdc_dwds_order_records_pickup_warning_when_launcher_has_no_distribution_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = bcdc_dwds.BcdcDwdsOrderResult(
        query="WHSE_FOREST_VEGETATION.F_OWN",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        package_id="pkg-f-own",
        package_name="generalized-forest-cover-ownership",
        package_title="Generalized Forest Cover Ownership",
        dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
        resource_id="dwds-id",
        resource_name="BC Geographic Warehouse Custom Download",
        resource_url=None,
        feature_type="WHSE_FOREST_VEGETATION.F_OWN",
        matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
        aoi_source="bbox",
        bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        geomark_id=None,
        geomark_url=None,
        output_format="fgdb",
        email_address="person@example.invalid",
        clipping_method="clip_to_aoi",
        ordering_application="FEMIC-BCDC-DWDS",
        request_url="https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
        request_payload={"featureItems": []},
        order_id="2551000",
        order_guid="guid-123",
        submission_status="SUCCESS",
        submission_description="submitted",
        submission_value="2551000",
        status_probe=None,
        warnings=(),
    )
    monkeypatch.setattr(
        bcdc_dwds,
        "_probe_dwds_order_status",
        lambda order_id: bcdc_dwds.BcdcDwdsStatusProbe(
            order_id=order_id,
            raw_payload={"Status": "FAILURE", "Value": "6"},
            status="FAILURE",
            description="missing",
            value="6",
            download_url=None,
        ),
    )
    monkeypatch.setattr(
        bcdc_dwds,
        "_resolve_dwds_pickup_download_url",
        lambda order_guid: (
            f"https://apps.gov.bc.ca/pub/dwds-rasp/pickupByGUID/{order_guid}",
            None,
        ),
    )

    updated = bcdc_dwds.follow_up_bcdc_dwds_order(result, download_root=None)

    assert updated.materialized_artifact_path is None
    assert any(
        "pickup-by-GUID launcher page" in warning
        for warning in updated.followup_warnings
    )
