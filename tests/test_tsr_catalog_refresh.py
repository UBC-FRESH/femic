from __future__ import annotations

import json
from pathlib import Path

import pytest

from femic.tsr_catalog import (
    TsrDiscoveryFailure,
    compare_tsr_catalog,
    refresh_tsr_catalog,
    write_json_report_atomic,
)
from femic.cli import main as cli_main
from typer.testing import CliRunner


def _document(url: str, *, title: str = "doc", tsa: str = "29") -> dict[str, object]:
    return {
        "tsa_id": f"tsa_{tsa}", "tsa_code": tsa, "tsa_name": "Williams Lake",
        "cycle_label": "TSR_2024", "cycle_year": 2024, "title": title,
        "document_type": "supporting_document", "file_name": "doc.pdf",
        "file_extension": "pdf", "relative_path": "TSR_2024/doc.pdf",
        "url": url, "listed_modified_raw": "today", "size_bytes": 3,
    }


def test_compare_deduplicates_url_variants_and_reports_changes() -> None:
    old = [_document("https://example.test/doc.pdf", title="old")]
    new = [_document("https://example.test/doc.pdf/", title="new"), _document("https://example.test/new.pdf")]
    diff = compare_tsr_catalog(old, new)
    assert len(diff.added) == 1
    assert len(diff.changed) == 1
    assert not diff.missing


def test_refresh_is_tsa_scoped_additive_and_atomic(tmp_path: Path) -> None:
    path = tmp_path / "tsa_documents.json"
    old = _document("https://example.test/old.pdf")
    path.write_text(json.dumps({"document_count": 1, "documents": [old]}), encoding="utf-8")

    class Index:
        landing_url = "https://bc.test/landing"
        tsa_root_url = "https://bc.test/tsa/"
        documents = (
            type("Record", (), {"to_dict": lambda self: _document("https://example.test/new.pdf")})(),
            type("Record", (), {"to_dict": lambda self: _document("https://example.test/other.pdf", tsa="30")})(),
        )

    result = refresh_tsr_catalog(catalog_path=path, tsa="29", dry_run=False, index_result=Index())
    assert len(result.diff.added) == 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert {item["url"] for item in payload["documents"]} == {old["url"], "https://example.test/new.pdf"}
    assert payload["removals_authorized"] is False


def test_missing_records_are_not_silent_deletions(tmp_path: Path) -> None:
    path = tmp_path / "tsa_documents.json"
    old = _document("https://example.test/old.pdf")
    path.write_text(json.dumps({"documents": [old]}), encoding="utf-8")
    class Index:
        landing_url = "landing"
        tsa_root_url = "tsa"
        documents = ()
    result = refresh_tsr_catalog(catalog_path=path, tsa="29", dry_run=False, index_result=Index())
    assert len(result.diff.missing) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["documents"] == [old]


def test_removals_fail_closed_when_a_source_is_unreachable(tmp_path: Path) -> None:
    path = tmp_path / "tsa_documents.json"
    old = _document("https://example.test/old.pdf")
    path.write_text(json.dumps({"documents": [old]}), encoding="utf-8")

    class Index:
        landing_url = "landing"
        tsa_root_url = "tsa"
        documents = ()
        source_failures = (TsrDiscoveryFailure("tsa", "tsa:29", "tsa_directory", "TimeoutError", "timed out"),)

    result = refresh_tsr_catalog(
        catalog_path=path, tsa="29", dry_run=False, allow_removals=True, index_result=Index()
    )
    assert result.removals_authorized is False
    assert result.report_payload()["unreachable"]
    assert json.loads(path.read_text(encoding="utf-8"))["documents"] == [old]


def test_existing_duplicate_cleanup_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "tsa_documents.json"
    old = _document("https://example.test/old.pdf")
    duplicate = _document("https://example.test/old.pdf/", title="legacy duplicate")
    path.write_text(json.dumps({"documents": [old, duplicate]}), encoding="utf-8")

    class Index:
        landing_url = "landing"
        tsa_root_url = "tsa"
        documents = ()

    result = refresh_tsr_catalog(catalog_path=path, index_result=Index(), dry_run=True)
    assert len(result.legacy_duplicate_cleanup) == 1
    assert len(result.report_payload()["legacy_duplicate_cleanup"]) == 1


def test_report_path_collision_is_rejected_and_failed_write_preserves_catalog(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    catalog.write_text('{"unchanged": true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="collide"):
        write_json_report_atomic(catalog, {"new": True}, catalog_path=catalog)

    with pytest.raises(TypeError):
        write_json_report_atomic(tmp_path / "report.json", {"bad": object()}, catalog_path=catalog)
    assert catalog.read_text(encoding="utf-8") == '{"unchanged": true}\n'


def test_top_level_timeout_returns_report_and_never_writes(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    old = _document("https://example.test/old.pdf")
    original = {"documents": [old]}
    catalog.write_text(json.dumps(original), encoding="utf-8")

    def fail(_url: str) -> str:
        raise TimeoutError("landing timed out")

    result = refresh_tsr_catalog(
        catalog_path=catalog,
        dry_run=False,
        allow_removals=True,
        fetch_text=fail,
    )
    report = result.report_payload()
    assert result.written is False
    assert report["removals_authorized"] is False
    assert report["unreachable"]
    failure = report["unreachable"][0]
    assert failure["source_kind"] == "landing"
    assert failure["scope"] == "catalog"
    assert failure["exception"] == "TimeoutError"
    assert failure["message"] == "landing timed out"
    assert json.loads(catalog.read_text(encoding="utf-8")) == original


def test_catalog_refresh_cli_help_and_dispatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(cli_main.app, ["tsr", "catalog-refresh", "--help"])
    assert help_result.exit_code == 0
    for option in ("--tsa", "--dry-run", "--write", "--json-report", "--allow-removals", "--source", "--timeout"):
        assert option in help_result.stdout

    called: dict[str, object] = {}

    class FakeResult:
        def report_payload(self) -> dict[str, object]:
            return {"written": False, "scope_tsa": "29"}

    def fake_refresh(**kwargs: object) -> FakeResult:
        called.update(kwargs)
        return FakeResult()

    monkeypatch.setattr(cli_main, "refresh_tsr_catalog", fake_refresh)
    catalog = tmp_path / "catalog.json"
    catalog.write_text('{"documents": []}', encoding="utf-8")
    result = runner.invoke(
        cli_main.app,
        ["tsr", "catalog-refresh", "--catalog", str(catalog), "--tsa", "29", "--write", "--timeout", "2"],
    )
    assert result.exit_code == 0, result.stdout
    assert called["tsa"] == "29"
    assert called["dry_run"] is False
    assert called["timeout"] == 2.0
