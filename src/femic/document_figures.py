"""Helpers for FEMIC document-figure recovery artifacts and provenance.

The functions in this module define FEMIC-side conventions for wrapping
``figrecover`` outputs. They intentionally do not import ``figrecover`` so the
normal FEMIC runtime remains independent of optional figure-recovery tooling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


DOCUMENT_FIGURE_RUNTIME_RELATIVE = Path("runtime") / "document_ingestion"

DOCUMENT_FIGURE_REVIEW_STATUSES = (
    "raw_extraction",
    "needs_calibration_review",
    "needs_value_review",
    "reviewed_for_planning",
    "accepted_for_comparison",
    "accepted_for_model_input",
    "rejected",
    "superseded",
)

DOCUMENT_FIGURE_REVIEWED_STATUSES = (
    "reviewed_for_planning",
    "accepted_for_comparison",
    "accepted_for_model_input",
    "rejected",
    "superseded",
)

DOCUMENT_FIGURE_DOWNSTREAM_USE_CLASSES = (
    "unclassified",
    "planning_evidence",
    "comparison_evidence",
    "sensitivity_input",
    "model_input_candidate",
    "model_input",
    "rejected",
)


class DocumentFigureProvenanceError(ValueError):
    """Raised when a document-figure provenance record is incomplete."""


@dataclass(frozen=True)
class DocumentFigureArtifactPaths:
    """Resolved artifact paths for one document-figure recovery corpus."""

    corpus_root: Path
    source_manifest_path: Path
    pages_dir: Path
    figure_candidates_path: Path
    crops_dir: Path
    calibration_dir: Path
    recovered_dir: Path
    overlays_dir: Path
    review_manifest_path: Path
    accepted_dir: Path

    def ensure_directories(self) -> None:
        """Create the directory structure used by a figure-recovery corpus."""

        self.corpus_root.mkdir(parents=True, exist_ok=True)
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.crops_dir.mkdir(parents=True, exist_ok=True)
        self.calibration_dir.mkdir(parents=True, exist_ok=True)
        self.recovered_dir.mkdir(parents=True, exist_ok=True)
        self.overlays_dir.mkdir(parents=True, exist_ok=True)
        self.accepted_dir.mkdir(parents=True, exist_ok=True)

    def as_dict(self) -> dict[str, str]:
        """Return JSON-friendly string paths for this corpus layout."""

        return {key: str(value) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class DocumentFigureProvenanceRecord:
    """Provenance for one recovered figure-derived table or series.

    A record is intentionally compact enough to store in a JSONL review
    manifest while still capturing the minimum evidence FEMIC needs before a
    recovered value can be referenced by planning or model-input work.
    """

    corpus_id: str
    document_title: str
    page_number: int
    series_name: str
    visual_selection_rule: str
    figrecover_version: str
    extraction_method: str
    output_path: Path
    output_checksum: str
    review_status: str
    downstream_use_classification: str
    source_url: str | None = None
    source_path: Path | None = None
    source_checksum: str | None = None
    package_component: str | None = None
    figure_id: str | None = None
    table_id: str | None = None
    crop_path: Path | None = None
    crop_checksum: str | None = None
    calibration_spec: dict[str, Any] | None = None
    extraction_parameters: dict[str, Any] | None = None
    reviewer: str | None = None
    review_timestamp: str | None = None
    created_timestamp: str | None = None

    def __post_init__(self) -> None:
        validate_document_figure_provenance(self)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the provenance record."""

        payload = asdict(self)
        for key in ("source_path", "crop_path", "output_path"):
            if payload[key] is not None:
                payload[key] = str(payload[key])
        return payload


def build_document_figure_corpus_root(
    instance_root: str | Path,
    corpus_id: str,
) -> Path:
    """Return the default ignored runtime root for a document-figure corpus."""

    if not corpus_id.strip():
        raise DocumentFigureProvenanceError("corpus_id cannot be blank")
    return Path(instance_root) / DOCUMENT_FIGURE_RUNTIME_RELATIVE / corpus_id


def build_document_figure_artifact_paths(
    corpus_root: str | Path,
) -> DocumentFigureArtifactPaths:
    """Resolve FEMIC's standard artifact paths for a figure-recovery corpus."""

    root = Path(corpus_root)
    return DocumentFigureArtifactPaths(
        corpus_root=root,
        source_manifest_path=root / "source_manifest.yaml",
        pages_dir=root / "pages",
        figure_candidates_path=root / "figure_candidates.csv",
        crops_dir=root / "crops",
        calibration_dir=root / "calibration",
        recovered_dir=root / "recovered",
        overlays_dir=root / "overlays",
        review_manifest_path=root / "review_manifest.jsonl",
        accepted_dir=root / "accepted",
    )


def compute_document_figure_file_sha256(path: str | Path) -> str:
    """Return the SHA256 checksum for a local document-figure artifact."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_document_figure_review_timestamp() -> str:
    """Return a UTC ISO-8601 timestamp for human-review provenance."""

    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def validate_document_figure_provenance(
    record: DocumentFigureProvenanceRecord,
) -> None:
    """Validate FEMIC's minimum provenance requirements for recovered figures."""

    if not record.corpus_id.strip():
        raise DocumentFigureProvenanceError("corpus_id cannot be blank")
    if not record.document_title.strip():
        raise DocumentFigureProvenanceError("document_title cannot be blank")
    if record.page_number < 1:
        raise DocumentFigureProvenanceError("page_number must be >= 1")
    if record.source_url is None and record.source_path is None:
        raise DocumentFigureProvenanceError("source_url or source_path is required")
    if record.figure_id is None and record.table_id is None:
        raise DocumentFigureProvenanceError("figure_id or table_id is required")
    if not record.series_name.strip():
        raise DocumentFigureProvenanceError("series_name cannot be blank")
    if not record.visual_selection_rule.strip():
        raise DocumentFigureProvenanceError("visual_selection_rule cannot be blank")
    if record.calibration_spec is None:
        raise DocumentFigureProvenanceError("calibration_spec is required")
    if not record.figrecover_version.strip():
        raise DocumentFigureProvenanceError("figrecover_version cannot be blank")
    if not record.extraction_method.strip():
        raise DocumentFigureProvenanceError("extraction_method cannot be blank")
    if record.extraction_parameters is None:
        raise DocumentFigureProvenanceError("extraction_parameters is required")
    if not record.output_checksum.strip():
        raise DocumentFigureProvenanceError("output_checksum cannot be blank")
    if record.review_status not in DOCUMENT_FIGURE_REVIEW_STATUSES:
        raise DocumentFigureProvenanceError(
            f"review_status must be one of {DOCUMENT_FIGURE_REVIEW_STATUSES}"
        )
    if (
        record.downstream_use_classification
        not in DOCUMENT_FIGURE_DOWNSTREAM_USE_CLASSES
    ):
        raise DocumentFigureProvenanceError(
            "downstream_use_classification must be one of "
            f"{DOCUMENT_FIGURE_DOWNSTREAM_USE_CLASSES}"
        )
    if record.review_status in DOCUMENT_FIGURE_REVIEWED_STATUSES:
        if record.reviewer is None or not record.reviewer.strip():
            raise DocumentFigureProvenanceError(
                "reviewer is required for reviewed or accepted statuses"
            )
        if record.review_timestamp is None or not record.review_timestamp.strip():
            raise DocumentFigureProvenanceError(
                "review_timestamp is required for reviewed or accepted statuses"
            )


def write_document_figure_provenance_json(
    record: DocumentFigureProvenanceRecord,
    path: str | Path,
) -> Path:
    """Write one provenance record as formatted JSON and return its path."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(record.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def append_document_figure_review_manifest_jsonl(
    record: DocumentFigureProvenanceRecord,
    path: str | Path,
) -> Path:
    """Append one provenance record to a JSONL review manifest."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(record.as_dict(), sort_keys=True) + "\n")
    return destination


__all__ = [
    "DOCUMENT_FIGURE_DOWNSTREAM_USE_CLASSES",
    "DOCUMENT_FIGURE_REVIEW_STATUSES",
    "DOCUMENT_FIGURE_REVIEWED_STATUSES",
    "DOCUMENT_FIGURE_RUNTIME_RELATIVE",
    "DocumentFigureArtifactPaths",
    "DocumentFigureProvenanceError",
    "DocumentFigureProvenanceRecord",
    "append_document_figure_review_manifest_jsonl",
    "build_document_figure_artifact_paths",
    "build_document_figure_corpus_root",
    "compute_document_figure_file_sha256",
    "current_document_figure_review_timestamp",
    "validate_document_figure_provenance",
    "write_document_figure_provenance_json",
]
