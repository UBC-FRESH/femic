from __future__ import annotations

import json
from pathlib import Path

import pytest

from femic import tsr_catalog
from femic.tsr_catalog import cache as tsr_cache


def _write_inventory(tmp_path: Path) -> Path:
    payload = {
        "generated_utc": "2026-04-04T00:00:00+00:00",
        "document_count": 2,
        "documents": [
            {
                "tsa_id": "tsa_29",
                "tsa_code": "29",
                "tsa_name": "Williams Lake",
                "cycle_label": "TSR_2024",
                "cycle_year": 2024,
                "title": "29ts_dpkg_2024",
                "document_type": "data_package",
                "file_name": "29ts_dpkg_2024.pdf",
                "file_extension": "pdf",
                "relative_path": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf",
                "url": "https://example.invalid/29ts_dpkg_2024.pdf",
                "listed_modified_raw": "4/3/2026 12:00 PM",
                "size_bytes": 100,
            },
            {
                "tsa_id": "tsa_08",
                "tsa_code": "08",
                "tsa_name": "Kamloops",
                "cycle_label": "TSR_2021",
                "cycle_year": 2021,
                "title": "08ts_ra_2021",
                "document_type": "rationale",
                "file_name": "08ts_ra_2021.pdf",
                "file_extension": "pdf",
                "relative_path": "TSR_2021/08ts_ra_2021.pdf",
                "url": "https://example.invalid/08ts_ra_2021.pdf",
                "listed_modified_raw": "4/3/2026 12:01 PM",
                "size_bytes": 120,
            },
        ],
    }
    inventory_path = tmp_path / "metadata" / "tsr" / "tsa_documents.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(payload), encoding="utf-8")
    return inventory_path


def test_fetch_tsr_pdfs_downloads_selected_pdfs_and_writes_manifest(
    tmp_path: Path,
) -> None:
    inventory_path = _write_inventory(tmp_path)
    corpus_root = tmp_path / "runtime" / "tsr_corpus"
    manifest_path = tmp_path / "metadata" / "tsr" / "tsa_pdf_cache_manifest.json"

    def _fake_download(url: str, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(f"downloaded:{url}".encode("utf-8"))
        return tsr_cache._DownloadedFileMetadata(
            content_type="application/pdf",
            size_bytes=destination.stat().st_size,
        )

    result = tsr_catalog.fetch_tsr_pdfs(
        documents_path=inventory_path,
        corpus_root=corpus_root,
        manifest_path=manifest_path,
        tsa_filters=("29",),
        source_root=tmp_path,
        download_pdf_fn=_fake_download,
    )

    assert result.selected_document_count == 1
    assert len(result.cached_documents) == 1
    cached = result.cached_documents[0]
    assert cached.tsa_id == "tsa_29"
    assert cached.fetch_status == "downloaded"
    assert cached.corpus_relative_path == (
        "tsa/tsa_29/TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf"
    )
    assert (corpus_root / cached.corpus_relative_path).is_file()

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["selected_document_count"] == 1
    assert manifest_payload["cached_count"] == 1
    assert (
        manifest_payload["documents"][0]["corpus_relative_path"]
        == cached.corpus_relative_path
    )
    assert manifest_payload["corpus_root"] == "runtime/tsr_corpus"


def test_fetch_tsr_pdfs_reuses_cached_file_without_redownloading(
    tmp_path: Path,
) -> None:
    inventory_path = _write_inventory(tmp_path)
    corpus_root = tmp_path / "runtime" / "tsr_corpus"
    manifest_path = tmp_path / "metadata" / "tsr" / "tsa_pdf_cache_manifest.json"
    cached_path = (
        corpus_root
        / "tsa"
        / "tsa_29"
        / "TSR_2024"
        / "Data_Package_2024"
        / "29ts_dpkg_2024.pdf"
    )
    cached_path.parent.mkdir(parents=True, exist_ok=True)
    cached_path.write_bytes(b"existing pdf bytes")

    calls: list[str] = []

    def _fake_download(url: str, destination: Path):
        calls.append(url)
        raise AssertionError(
            "download should not be called for an existing cached file"
        )

    result = tsr_catalog.fetch_tsr_pdfs(
        documents_path=inventory_path,
        corpus_root=corpus_root,
        manifest_path=manifest_path,
        tsa_filters=("tsa_29",),
        source_root=tmp_path,
        download_pdf_fn=_fake_download,
    )

    assert calls == []
    assert len(result.cached_documents) == 1
    assert result.cached_documents[0].fetch_status == "cache_hit"


def test_fetch_tsr_pdfs_renders_user_local_default_corpus_placeholder(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inventory_path = _write_inventory(tmp_path)
    user_corpus_root = tmp_path / ".femic" / "tsr" / "corpus"
    user_manifest_path = tmp_path / ".femic" / "tsr" / "tsa_pdf_cache_manifest.json"

    monkeypatch.setattr(
        tsr_cache,
        "default_femic_tsr_corpus_root",
        lambda: user_corpus_root,
    )
    monkeypatch.setattr(
        tsr_cache,
        "default_femic_tsr_cache_manifest_path",
        lambda: user_manifest_path,
    )

    def _fake_download(url: str, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(f"downloaded:{url}".encode("utf-8"))
        return tsr_cache._DownloadedFileMetadata(
            content_type="application/pdf",
            size_bytes=destination.stat().st_size,
        )

    tsr_catalog.fetch_tsr_pdfs(
        documents_path=inventory_path,
        corpus_root=user_corpus_root,
        manifest_path=user_manifest_path,
        tsa_filters=("29",),
        download_pdf_fn=_fake_download,
    )

    payload = json.loads(user_manifest_path.read_text(encoding="utf-8"))
    assert payload["corpus_root"] == "~/.femic/tsr/corpus"
    assert payload["manifest_path"] == "~/.femic/tsr/tsa_pdf_cache_manifest.json"
