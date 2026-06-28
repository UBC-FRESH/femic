from __future__ import annotations

import json
from pathlib import Path

import pytest

from femic.document_figures import (
    DOCUMENT_FIGURE_RUNTIME_RELATIVE,
    DocumentFigureProvenanceError,
    DocumentFigureProvenanceRecord,
    append_document_figure_review_manifest_jsonl,
    build_document_figure_artifact_paths,
    build_document_figure_corpus_root,
    compute_document_figure_file_sha256,
    current_document_figure_review_timestamp,
    write_document_figure_provenance_json,
)


def _valid_record(tmp_path: Path, **overrides: object) -> DocumentFigureProvenanceRecord:
    output_path = tmp_path / "recovered" / "figure-1.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("x,y\n1,2\n", encoding="utf-8")
    payload: dict[str, object] = {
        "corpus_id": "tfl6-mp11",
        "document_title": "TFL 6 Management Plan 11",
        "page_number": 42,
        "series_name": "base case",
        "visual_selection_rule": "blue line mask",
        "figrecover_version": "0.1.0a1",
        "extraction_method": "deterministic_line_mask",
        "output_path": output_path,
        "output_checksum": compute_document_figure_file_sha256(output_path),
        "review_status": "raw_extraction",
        "downstream_use_classification": "unclassified",
        "source_url": "https://example.test/tfl6-mp11.pdf",
        "figure_id": "Figure 12",
        "crop_path": tmp_path / "crops" / "figure-12.png",
        "crop_checksum": "crop-sha",
        "calibration_spec": {"x_axis": "linear", "y_axis": "linear"},
        "extraction_parameters": {"mask": "blue"},
    }
    payload.update(overrides)
    return DocumentFigureProvenanceRecord(**payload)


def test_document_figure_corpus_root_uses_runtime_convention(
    tmp_path: Path,
) -> None:
    root = build_document_figure_corpus_root(tmp_path, "tfl6-mp11")

    assert root == tmp_path / DOCUMENT_FIGURE_RUNTIME_RELATIVE / "tfl6-mp11"


def test_document_figure_artifact_paths_match_phase78_convention(
    tmp_path: Path,
) -> None:
    paths = build_document_figure_artifact_paths(tmp_path / "corpus")

    assert paths.source_manifest_path == paths.corpus_root / "source_manifest.yaml"
    assert paths.pages_dir == paths.corpus_root / "pages"
    assert paths.figure_candidates_path == paths.corpus_root / "figure_candidates.csv"
    assert paths.crops_dir == paths.corpus_root / "crops"
    assert paths.calibration_dir == paths.corpus_root / "calibration"
    assert paths.recovered_dir == paths.corpus_root / "recovered"
    assert paths.overlays_dir == paths.corpus_root / "overlays"
    assert paths.review_manifest_path == paths.corpus_root / "review_manifest.jsonl"
    assert paths.accepted_dir == paths.corpus_root / "accepted"
    assert paths.as_dict()["corpus_root"] == str(tmp_path / "corpus")


def test_document_figure_artifact_paths_create_directories(
    tmp_path: Path,
) -> None:
    paths = build_document_figure_artifact_paths(tmp_path / "corpus")

    paths.ensure_directories()

    assert paths.corpus_root.is_dir()
    assert paths.pages_dir.is_dir()
    assert paths.crops_dir.is_dir()
    assert paths.calibration_dir.is_dir()
    assert paths.recovered_dir.is_dir()
    assert paths.overlays_dir.is_dir()
    assert paths.accepted_dir.is_dir()


def test_document_figure_file_sha256_is_deterministic(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.csv"
    artifact.write_text("x,y\n1,2\n", encoding="utf-8")

    digest = compute_document_figure_file_sha256(artifact)

    assert len(digest) == 64
    assert digest == compute_document_figure_file_sha256(artifact)


def test_document_figure_provenance_serializes_json_paths(
    tmp_path: Path,
) -> None:
    record = _valid_record(tmp_path)

    payload = record.as_dict()

    assert payload["output_path"].endswith("figure-1.csv")
    assert payload["crop_path"].endswith("figure-12.png")
    assert payload["source_path"] is None
    assert payload["review_status"] == "raw_extraction"


def test_document_figure_provenance_requires_source(tmp_path: Path) -> None:
    with pytest.raises(
        DocumentFigureProvenanceError,
        match="source_url or source_path is required",
    ):
        _valid_record(tmp_path, source_url=None, source_path=None)


def test_document_figure_provenance_requires_figure_or_table_id(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        DocumentFigureProvenanceError,
        match="figure_id or table_id is required",
    ):
        _valid_record(tmp_path, figure_id=None, table_id=None)


def test_document_figure_provenance_rejects_unknown_review_status(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        DocumentFigureProvenanceError,
        match="review_status must be one of",
    ):
        _valid_record(tmp_path, review_status="approved_without_review")


def test_document_figure_provenance_requires_reviewer_for_reviewed_status(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        DocumentFigureProvenanceError,
        match="reviewer is required",
    ):
        _valid_record(
            tmp_path,
            review_status="accepted_for_model_input",
            downstream_use_classification="model_input",
        )


def test_document_figure_provenance_allows_reviewed_status_with_reviewer(
    tmp_path: Path,
) -> None:
    record = _valid_record(
        tmp_path,
        review_status="accepted_for_comparison",
        downstream_use_classification="comparison_evidence",
        reviewer="Gregory Paradis",
        review_timestamp=current_document_figure_review_timestamp(),
    )

    assert record.review_status == "accepted_for_comparison"


def test_write_document_figure_provenance_json(tmp_path: Path) -> None:
    record = _valid_record(tmp_path)
    output_path = tmp_path / "provenance" / "figure-12.json"

    written_path = write_document_figure_provenance_json(record, output_path)
    payload = json.loads(written_path.read_text(encoding="utf-8"))

    assert written_path == output_path
    assert payload["corpus_id"] == "tfl6-mp11"
    assert payload["output_checksum"] == record.output_checksum


def test_append_document_figure_review_manifest_jsonl(tmp_path: Path) -> None:
    record = _valid_record(tmp_path)
    manifest_path = tmp_path / "review_manifest.jsonl"

    append_document_figure_review_manifest_jsonl(record, manifest_path)
    append_document_figure_review_manifest_jsonl(record, manifest_path)

    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["figure_id"] == "Figure 12"
