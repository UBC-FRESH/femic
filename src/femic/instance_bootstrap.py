"""Bootstrap helpers for creating FEMIC deployment-instance workspaces."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
from importlib import resources
from pathlib import Path
from typing import Callable
from urllib.request import urlopen
import zipfile


INSTANCE_TEMPLATE_PACKAGE = "femic.resources.instance"


@dataclass(frozen=True)
class DatasetDownloadSpec:
    """Dataset URL and local placement rules for instance bootstrap."""

    name: str
    url: str
    archive_relpath: Path
    extract_relpath: Path


@dataclass(frozen=True)
class InstanceInitResult:
    """Result payload for deployment-instance workspace initialization."""

    instance_root: Path
    created_dirs: tuple[Path, ...]
    written_files: tuple[Path, ...]
    skipped_files: tuple[Path, ...]
    downloaded_archives: tuple[Path, ...]
    extracted_dirs: tuple[Path, ...]


INSTANCE_DIRS: tuple[Path, ...] = (
    Path("config"),
    Path("config/tipsy"),
    Path("runbooks"),
    Path("data"),
    Path("data/downloads"),
    Path("output"),
    Path("runtime/logs"),
    Path("tipsy_io/logs"),
    Path("tipsy_io/scratch"),
    Path("vdyp_io/logs"),
)
INSTANCE_TEMPLATE_FILES: tuple[Path, ...] = (
    Path(".gitignore"),
    Path("QUICKSTART.md"),
    Path("config/run_profile.case_template.yaml"),
    Path("config/silviculture.case_template.yaml"),
    Path("config/rebuild.spec.yaml"),
    Path("config/rebuild.allowlist.yaml"),
    Path("runbooks/REBUILD_RUNBOOK.md"),
    Path("config/tipsy/template.case.yaml"),
    Path("config/patchworks.runtime.windows.yaml"),
)
BC_VRI_DOWNLOADS: tuple[DatasetDownloadSpec, ...] = (
    DatasetDownloadSpec(
        name="VRI Layer 1 Rank 1 (2024)",
        url=(
            "https://pub.data.gov.bc.ca/datasets/02dba161-fdb7-48ae-a4bb-"
            "bd6ef017c36d/current/VEG_COMP_LYR_R1_POLY_2024.gdb.zip"
        ),
        archive_relpath=Path("data/downloads/VEG_COMP_LYR_R1_POLY_2024.gdb.zip"),
        extract_relpath=Path("data/bc/vri/2024"),
    ),
    DatasetDownloadSpec(
        name="VRI VDYP7 Input Polygon+Layer (2024)",
        url=(
            "https://pub.data.gov.bc.ca/datasets/02dba161-fdb7-48ae-a4bb-"
            "bd6ef017c36d/current/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb.zip"
        ),
        archive_relpath=Path(
            "data/downloads/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb.zip"
        ),
        extract_relpath=Path("data/bc/vri/2024"),
    ),
)


def _read_resource_bytes(resource_relpath: Path) -> bytes:
    resource = resources.files(INSTANCE_TEMPLATE_PACKAGE).joinpath(
        resource_relpath.as_posix()
    )
    return resource.read_bytes()


def _download_url_to_path(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _extract_archive(archive_path: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, mode="r") as zf:
        zf.extractall(extract_dir)


def bootstrap_instance_workspace(
    *,
    instance_root: Path,
    overwrite: bool = False,
    include_bc_vri_download: bool = False,
    message_fn: Callable[[str], None] = print,
    download_url_fn: Callable[[str, Path], None] = _download_url_to_path,
) -> InstanceInitResult:
    """Create a filesystem-first FEMIC deployment-instance workspace."""
    resolved_root = instance_root.expanduser().resolve()
    resolved_root.mkdir(parents=True, exist_ok=True)

    created_dirs: list[Path] = []
    written_files: list[Path] = []
    skipped_files: list[Path] = []
    downloaded_archives: list[Path] = []
    extracted_dirs: list[Path] = []

    for rel_dir in INSTANCE_DIRS:
        target_dir = resolved_root / rel_dir
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            created_dirs.append(target_dir)

    for rel_file in INSTANCE_TEMPLATE_FILES:
        destination = resolved_root / rel_file
        if destination.exists() and not overwrite:
            skipped_files.append(destination)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_read_resource_bytes(rel_file))
        written_files.append(destination)

    if include_bc_vri_download:
        for spec in BC_VRI_DOWNLOADS:
            archive_path = resolved_root / spec.archive_relpath
            extract_dir = resolved_root / spec.extract_relpath
            message_fn(f"downloading dataset: {spec.name}")
            download_url_fn(spec.url, archive_path)
            downloaded_archives.append(archive_path)
            _extract_archive(archive_path, extract_dir)
            extracted_dirs.append(extract_dir)

    return InstanceInitResult(
        instance_root=resolved_root,
        created_dirs=tuple(created_dirs),
        written_files=tuple(written_files),
        skipped_files=tuple(skipped_files),
        downloaded_archives=tuple(downloaded_archives),
        extracted_dirs=tuple(extracted_dirs),
    )
