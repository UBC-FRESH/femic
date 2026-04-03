"""Student-facing release packaging helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil

REQUIRED_MODEL_INPUT_FILES = (
    "au_table.csv",
    "curve_table.csv",
    "curve_points_table.csv",
)

REQUIRED_PATCHWORKS_EXPORT_FILES = (
    "forestmodel.xml",
    "fragments/fragments.shp",
    "fragments/fragments.dbf",
    "fragments/fragments.shx",
    "fragments/fragments.prj",
    "fragments/fragments.cpg",
)
# Backward-compatible alias for existing callers/tests. This constant covers
# the export-bundle Patchworks minimum only, not the full standalone runtime
# package needed to launch a compiled model directly in Patchworks.
REQUIRED_PATCHWORKS_FILES = REQUIRED_PATCHWORKS_EXPORT_FILES


@dataclass(frozen=True)
class ReleasePackageResult:
    """Metadata for a generated release package."""

    release_id: str
    release_dir: Path
    manifest_path: Path
    handoff_notes_path: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_file(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def _copy_tree(src: Path, dst: Path) -> list[Path]:
    copied: list[Path] = []
    for item in sorted(src.rglob("*")):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        copied.append(_copy_file(item, dst / rel))
    return copied


def _resolve_release_id(case_id: str, run_id: str | None) -> str:
    token = (
        run_id.strip()
        if run_id and run_id.strip()
        else datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    )
    return f"{case_id}_{token}"


def build_release_package(
    *,
    case_id: str,
    output_root: Path,
    model_input_bundle_dir: Path,
    patchworks_output_dir: Path,
    woodstock_output_dir: Path | None,
    logs_dir: Path,
    run_id: str | None,
    strict: bool,
) -> ReleasePackageResult:
    """Create a versioned release bundle with core artifacts and notes."""

    normalized_case = case_id.strip().lower()
    if not normalized_case:
        raise ValueError("case_id must not be empty")

    release_id = _resolve_release_id(normalized_case, run_id)
    release_dir = output_root.expanduser().resolve() / release_id
    if release_dir.exists():
        raise ValueError(f"Release directory already exists: {release_dir}")

    bundle_dir = model_input_bundle_dir.expanduser().resolve()
    patchworks_dir = patchworks_output_dir.expanduser().resolve()
    woodstock_dir = (
        woodstock_output_dir.expanduser().resolve() if woodstock_output_dir else None
    )
    logs_root = logs_dir.expanduser().resolve()

    errors: list[str] = []
    for required in REQUIRED_MODEL_INPUT_FILES:
        candidate = bundle_dir / required
        if not candidate.exists():
            errors.append(f"Missing required model-input file: {candidate}")

    for required in REQUIRED_PATCHWORKS_EXPORT_FILES:
        candidate = patchworks_dir / required
        if not candidate.exists():
            errors.append(f"Missing required Patchworks artifact: {candidate}")

    if strict and errors:
        raise FileNotFoundError("; ".join(errors))

    copied_paths: list[Path] = []
    warnings: list[str] = []

    # model_input_bundle
    target_bundle = release_dir / "model_input_bundle"
    for required in REQUIRED_MODEL_INPUT_FILES:
        src = bundle_dir / required
        if src.exists():
            copied_paths.append(_copy_file(src, target_bundle / required))
        else:
            warnings.append(f"Skipped missing optional file: {src}")

    # patchworks
    target_patchworks = release_dir / "patchworks"
    if patchworks_dir.exists():
        copied_paths.extend(_copy_tree(patchworks_dir, target_patchworks))
    else:
        warnings.append(f"Patchworks output directory missing: {patchworks_dir}")

    # woodstock optional
    target_woodstock = release_dir / "woodstock"
    if woodstock_dir and woodstock_dir.exists():
        copied_paths.extend(_copy_tree(woodstock_dir, target_woodstock))

    # logs optional copy (just manifests + patchworks runtime logs)
    target_logs = release_dir / "logs"
    if logs_root.exists():
        for candidate in sorted(logs_root.glob("run_manifest-*.json")):
            copied_paths.append(_copy_file(candidate, target_logs / candidate.name))
        for pattern in (
            "patchworks_matrixbuilder_manifest-*.json",
            "patchworks_matrixbuilder_stdout-*.log",
            "patchworks_matrixbuilder_stderr-*.log",
        ):
            for candidate in sorted(logs_root.glob(pattern)):
                copied_paths.append(_copy_file(candidate, target_logs / candidate.name))

    file_entries = []
    for path in sorted(set(copied_paths)):
        rel = path.relative_to(release_dir)
        file_entries.append(
            {
                "path": rel.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )

    manifest = {
        "release_id": release_id,
        "created_utc": datetime.now(UTC).isoformat(),
        "case_id": normalized_case,
        "source": {
            "model_input_bundle_dir": str(bundle_dir),
            "patchworks_output_dir": str(patchworks_dir),
            "woodstock_output_dir": str(woodstock_dir) if woodstock_dir else None,
            "logs_dir": str(logs_root),
        },
        "warnings": warnings,
        "files": file_entries,
    }
    manifest_path = release_dir / "release_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    handoff_notes = release_dir / "HANDOFF.md"
    handoff_notes.write_text(
        "\n".join(
            [
                f"# FEMIC Release Package: {release_id}",
                "",
                "## Contents",
                "- `model_input_bundle/`: AU and curve tables",
                "- `patchworks/`: ForestModel XML + fragments shapefile",
                "- `woodstock/`: optional Woodstock compatibility CSVs (if present)",
                "- `logs/`: run manifests and Patchworks runtime logs",
                "- `release_manifest.json`: file inventory with SHA256 hashes",
                "",
                "## Quick Validation",
                "1. Confirm `patchworks/forestmodel.xml` exists.",
                "2. Confirm the full `patchworks/fragments/` shapefile sidecar set exists:",
                "   `fragments.{shp,dbf,shx,prj,cpg}`.",
                "3. Confirm all three `model_input_bundle/*.csv` files exist.",
                "4. Treat this release as the export-bundle minimum, not the full standalone runtime package.",
                "5. For a launch-ready standalone Patchworks instance, also ship blocks/topology,",
                "   analysis/PIN surfaces, and compiled tracks beside the validated XML/fragments pair.",
                "6. Review `release_manifest.json` warnings before delivery.",
                "",
                "## Suggested Operator Commands",
                "```bash",
                "PYTHONPATH=src python -m femic patchworks preflight --config config/patchworks.runtime.yaml",
                "PYTHONPATH=src python -m femic patchworks matrix-build --config config/patchworks.runtime.yaml",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return ReleasePackageResult(
        release_id=release_id,
        release_dir=release_dir,
        manifest_path=manifest_path,
        handoff_notes_path=handoff_notes,
    )
