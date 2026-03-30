from __future__ import annotations

from pathlib import Path

from femic.user_config import (
    FemicUserConfig,
    FemicUserPaths,
    default_femic_user_paths,
    load_femic_user_config,
    with_managed_external_root,
    with_user_instance_root,
    write_femic_user_config,
)


def test_load_femic_user_config_defaults_when_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "user.yaml"

    config = load_femic_user_config(config_path)

    assert config.config_path == config_path.resolve()
    assert config.exists is False
    assert config.paths == default_femic_user_paths()


def test_write_femic_user_config_round_trips(tmp_path: Path) -> None:
    config_path = tmp_path / "user.yaml"
    config = FemicUserConfig(
        config_path=config_path,
        exists=False,
        paths=FemicUserPaths(
            managed_external_root=tmp_path / "managed",
            user_instance_root=tmp_path / "instances",
        ),
    )

    write_femic_user_config(config)
    loaded = load_femic_user_config(config_path)

    assert loaded.exists is True
    assert loaded.paths.managed_external_root == (tmp_path / "managed").resolve()
    assert loaded.paths.user_instance_root == (tmp_path / "instances").resolve()


def test_with_path_helpers_preserve_other_values(tmp_path: Path) -> None:
    config = FemicUserConfig(
        config_path=tmp_path / "user.yaml",
        exists=True,
        paths=FemicUserPaths(
            managed_external_root=tmp_path / "managed",
            user_instance_root=tmp_path / "instances",
        ),
    )

    updated_managed = with_managed_external_root(config, tmp_path / "other-managed")
    updated_instances = with_user_instance_root(config, tmp_path / "other-instances")

    assert (
        updated_managed.paths.managed_external_root
        == (tmp_path / "other-managed").resolve()
    )
    assert (
        updated_managed.paths.user_instance_root == (tmp_path / "instances").resolve()
    )
    assert (
        updated_instances.paths.managed_external_root
        == (tmp_path / "managed").resolve()
    )
    assert (
        updated_instances.paths.user_instance_root
        == (tmp_path / "other-instances").resolve()
    )
