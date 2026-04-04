from __future__ import annotations

import json
from pathlib import Path

from femic import tsr_catalog


def _fixture_fetcher_factory() -> dict[str, str]:
    landing_url = tsr_catalog.DEFAULT_TSR_LANDING_URL
    tsa_root_url = tsr_catalog.DEFAULT_TSR_TSA_ROOT_URL
    tsa_url = f"{tsa_root_url}Williams_Lake_29/"
    cycle_url = f"{tsa_url}TSR_2024/"
    dpkg_url = f"{cycle_url}Data_Package_2024/"
    return {
        landing_url: """
            <html><body>
            <a href="https://www.for.gov.bc.ca/ftp/HTS/external/!publish/Timber_Supply_Review/">
              TSR publish root
            </a>
            <a href="https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/forestry/stewardship/timber-supply-review/tsr_document_descriptions.pdf">
              TSR document descriptions
            </a>
            </body></html>
        """,
        tsa_root_url: """
            4/3/2026 12:01 PM       &lt;dir&gt; <A HREF="Williams_Lake_29/">Williams_Lake_29</A><br>
        """,
        tsa_url: """
            4/3/2026 12:02 PM       &lt;dir&gt; <A HREF="TSR_2024/">TSR_2024</A><br>
        """,
        cycle_url: """
            4/3/2026 12:03 PM       &lt;dir&gt; <A HREF="Data_Package_2024/">Data_Package_2024</A><br>
            4/3/2026 12:04 PM              12,345 <A HREF="29ts_ra_2024.pdf">29ts_ra_2024.pdf</A><br>
        """,
        dpkg_url: """
            4/3/2026 12:05 PM             456,789 <A HREF="29ts_dpkg_2024.pdf">29ts_dpkg_2024.pdf</A><br>
        """,
    }


def test_index_tsr_tsa_surfaces_builds_registry_and_documents() -> None:
    html_map = _fixture_fetcher_factory()

    def _fetch(url: str) -> str:
        return html_map[url]

    result = tsr_catalog.index_tsr_tsa_surfaces(fetch_text=_fetch)

    assert len(result.landing_resources) == 2
    assert len(result.registry) == 1
    assert len(result.documents) == 2

    tsa_record = result.registry[0]
    assert tsa_record.tsa_id == "tsa_29"
    assert tsa_record.tsa_name == "Williams Lake"
    assert len(tsa_record.cycles) == 1
    assert tsa_record.cycles[0].cycle_year == 2024
    assert tsa_record.document_count == 2

    relative_paths = {document.relative_path for document in result.documents}
    assert relative_paths == {
        "TSR_2024/29ts_ra_2024.pdf",
        "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf",
    }
    document_types = {document.document_type for document in result.documents}
    assert document_types == {"rationale", "data_package"}


def test_write_tsr_index_writes_canonical_json_outputs(tmp_path: Path) -> None:
    html_map = _fixture_fetcher_factory()

    def _fetch(url: str) -> str:
        return html_map[url]

    result = tsr_catalog.index_tsr_tsa_surfaces(fetch_text=_fetch)
    written = tsr_catalog.write_tsr_index(result, tmp_path)

    assert written.registry_path == tmp_path / "tsa_registry.json"
    assert written.documents_path == tmp_path / "tsa_documents.json"
    assert written.tsa_count == 1
    assert written.document_count == 2

    registry_payload = json.loads(written.registry_path.read_text(encoding="utf-8"))
    documents_payload = json.loads(written.documents_path.read_text(encoding="utf-8"))
    assert registry_payload["tsa_count"] == 1
    assert registry_payload["document_count"] == 2
    assert registry_payload["tsas"][0]["tsa_id"] == "tsa_29"
    assert documents_payload["document_count"] == 2
    assert documents_payload["documents"][1]["document_type"] == "data_package"
