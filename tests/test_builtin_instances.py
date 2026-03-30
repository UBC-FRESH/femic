from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from femic.builtin_instances import (
    BuiltinInstanceCatalogError,
    install_builtin_instances,
    load_builtin_instance_catalog,
    resolve_builtin_external_path,
    resolve_builtin_repo_status,
)
from femic.user_config import FemicUserConfig, FemicUserPaths, write_femic_user_config


def _write_user_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "user.yaml"
    write_femic_user_config(
        FemicUserConfig(
            config_path=config_path,
            exists=False,
            paths=FemicUserPaths(
                managed_external_root=tmp_path / "managed-external",
                user_instance_root=tmp_path / "instances",
            ),
        )
    )
    return config_path


def test_load_builtin_instance_catalog_includes_k3z_and_tsa29() -> None:
    catalog = load_builtin_instance_catalog()

    assert catalog.get_instance("k3z").target_dirname == "femic-k3z-instance"
    assert catalog.get_instance("tsa29").target_dirname == "femic-tsa29-instance"
    assert (
        catalog.get_support_repo("femic-public-data").target_dirname
        == "femic-public-data"
    )


def test_resolve_builtin_repo_status_prefers_source_checkout(tmp_path: Path) -> None:
    source_root = tmp_path / "repo"
    source_repo = source_root / "external" / "femic-k3z-instance"
    source_repo.mkdir(parents=True)

    status = resolve_builtin_repo_status(
        target_dirname="femic-k3z-instance",
        source_root=source_root,
    )

    assert status.status == "source-checkout"
    assert status.path == source_repo.resolve()


def test_resolve_builtin_external_path_uses_managed_root_when_source_missing(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "repo"
    config_path = _write_user_config(tmp_path)

    resolved = resolve_builtin_external_path(
        Path("external/femic-k3z-instance/models/demo/base.pin"),
        source_root=source_root,
        user_config_path=config_path,
    )

    assert (
        resolved
        == (
            tmp_path
            / "managed-external"
            / "femic-k3z-instance"
            / "models"
            / "demo"
            / "base.pin"
        ).resolve()
    )


def test_install_builtin_instances_clones_support_repo_and_instance(
    tmp_path: Path,
) -> None:
    config_path = _write_user_config(tmp_path)
    calls: list[list[str]] = []

    def _fake_run(args, **_kwargs):
        calls.append(list(args))
        destination = Path(args[-1])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / ".git").write_text("gitdir", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = install_builtin_instances(
        "k3z",
        user_config_path=config_path,
        run_fn=_fake_run,
    )

    assert len(result.installed_paths) == 2
    assert result.skipped_paths == ()
    assert any("femic-public-data.git" in " ".join(call) for call in calls)
    assert any("femic-k3z-instance.git" in " ".join(call) for call in calls)


def test_install_builtin_instances_skips_existing_git_worktrees(tmp_path: Path) -> None:
    config_path = _write_user_config(tmp_path)
    managed_root = tmp_path / "managed-external"
    for dirname in ("femic-public-data", "femic-k3z-instance"):
        target = managed_root / dirname
        target.mkdir(parents=True)
        (target / ".git").write_text("gitdir", encoding="utf-8")

    result = install_builtin_instances("k3z", user_config_path=config_path)

    assert result.installed_paths == ()
    assert len(result.skipped_paths) == 2


def test_install_builtin_instances_fails_for_non_git_target(tmp_path: Path) -> None:
    config_path = _write_user_config(tmp_path)
    target = tmp_path / "managed-external" / "femic-k3z-instance"
    target.mkdir(parents=True)

    with pytest.raises(BuiltinInstanceCatalogError):
        install_builtin_instances("k3z", user_config_path=config_path)
