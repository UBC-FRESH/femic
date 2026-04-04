from __future__ import annotations

import json
from pathlib import Path

import pytest

from femic.release_packaging import (
    REQUIRED_PATCHWORKS_EXPORT_FILES,
    build_release_package,
)


def _touch(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_release_package_creates_manifest_and_handoff(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "data/model_input_bundle"
    _touch(bundle_dir / "au_table.csv", "a")
    _touch(bundle_dir / "curve_table.csv", "b")
    _touch(bundle_dir / "curve_points_table.csv", "c")

    patchworks_dir = tmp_path / "output/patchworks_k3z_validated"
    _touch(patchworks_dir / "forestmodel.xml", "xml")
    _touch(patchworks_dir / "fragments/fragments.shp", "shp")
    _touch(patchworks_dir / "fragments/fragments.dbf", "dbf")
    _touch(patchworks_dir / "fragments/fragments.shx", "shx")
    _touch(patchworks_dir / "fragments/fragments.prj", "prj")
    _touch(patchworks_dir / "fragments/fragments.cpg", "cpg")

    logs_dir = tmp_path / "vdyp_io/logs"
    _touch(logs_dir / "run_manifest-test.json", "{}")

    result = build_release_package(
        case_id="k3z",
        output_root=tmp_path / "releases",
        model_input_bundle_dir=bundle_dir,
        patchworks_output_dir=patchworks_dir,
        woodstock_output_dir=None,
        logs_dir=logs_dir,
        run_id="r1",
        strict=True,
    )

    assert result.release_dir.exists()
    assert result.manifest_path.exists()
    assert result.handoff_notes_path.exists()

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["release_id"] == "k3z_r1"
    paths = {entry["path"] for entry in manifest["files"]}
    assert "model_input_bundle/au_table.csv" in paths
    assert "patchworks/forestmodel.xml" in paths
    for required in REQUIRED_PATCHWORKS_EXPORT_FILES:
        assert f"patchworks/{required}" in paths
    handoff_text = result.handoff_notes_path.read_text(encoding="utf-8")
    assert "export-bundle minimum" in handoff_text
    assert "blocks/topology" in handoff_text


def test_build_release_package_strict_fails_when_required_missing(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "data/model_input_bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    patchworks_dir = tmp_path / "output/patchworks_k3z_validated"
    patchworks_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(FileNotFoundError):
        build_release_package(
            case_id="k3z",
            output_root=tmp_path / "releases",
            model_input_bundle_dir=bundle_dir,
            patchworks_output_dir=patchworks_dir,
            woodstock_output_dir=None,
            logs_dir=tmp_path / "vdyp_io/logs",
            run_id="r1",
            strict=True,
        )
