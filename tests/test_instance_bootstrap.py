from __future__ import annotations

from pathlib import Path
import zipfile

from femic.instance_bootstrap import bootstrap_instance_workspace


def test_bootstrap_instance_workspace_writes_templates(tmp_path: Path) -> None:
    result = bootstrap_instance_workspace(
        instance_root=tmp_path / "instance",
        overwrite=False,
        include_bc_vri_download=False,
        message_fn=lambda _msg: None,
    )

    assert (result.instance_root / "config/run_profile.case_template.yaml").is_file()
    assert (result.instance_root / "config/rebuild.spec.yaml").is_file()
    assert (result.instance_root / "config/rebuild.allowlist.yaml").is_file()
    assert (result.instance_root / "runbooks/REBUILD_RUNBOOK.md").is_file()
    assert (result.instance_root / "config/tipsy/template.case.yaml").is_file()
    assert (result.instance_root / ".gitignore").is_file()
    assert (result.instance_root / "QUICKSTART.md").is_file()
    assert (result.instance_root / "tipsy_io/logs").is_dir()
    assert (result.instance_root / "tipsy_io/scratch").is_dir()
    assert (result.instance_root / "vdyp_io/logs").is_dir()
    assert (result.instance_root / "vdyp_io/scratch").is_dir()
    assert not result.downloaded_archives


def test_bootstrap_instance_workspace_downloads_and_extracts(tmp_path: Path) -> None:
    def _fake_download(_url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, mode="w") as zf:
            zf.writestr("dataset/example.txt", "ok\n")

    result = bootstrap_instance_workspace(
        instance_root=tmp_path / "instance",
        overwrite=False,
        include_bc_vri_download=True,
        message_fn=lambda _msg: None,
        download_url_fn=_fake_download,
    )

    assert len(result.downloaded_archives) == 2
    extracted_file = result.instance_root / "data/bc/vri/2024/dataset/example.txt"
    assert extracted_file.is_file()
