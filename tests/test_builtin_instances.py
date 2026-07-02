from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from femic.builtin_instances import (
    BuiltinInstanceCatalogError,
    clear_instance_catalog_providers,
    install_builtin_instances,
    load_instance_catalog,
    register_instance_catalog_provider,
    discover_instance_catalog_providers,
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


class _FixtureInstanceCatalogProvider:
    provider_id = "fixture"

    def load_catalog_payload(self) -> dict:
        return {
            "support_repos": [
                {
                    "repo_id": "fixture-public-data",
                    "label": "Fixture public data",
                    "repo_url": "https://example.test/fixture-public-data.git",
                    "target_dirname": "fixture-public-data",
                    "notes": ["Fixture support data."],
                }
            ],
            "instances": [
                {
                    "builtin_id": "demo",
                    "label": "Demo instance",
                    "repo_url": "https://example.test/demo-instance.git",
                    "target_dirname": "demo-instance",
                    "support_repo_ids": ["fixture-public-data"],
                    "notes": ["Fixture installable instance."],
                }
            ],
        }


class _FixtureEntryPoint:
    name = "fixture"

    def load(self):
        return _FixtureInstanceCatalogProvider


@pytest.fixture(autouse=True)
def _clear_instance_catalog_registry() -> None:
    clear_instance_catalog_providers()
    yield
    clear_instance_catalog_providers()


def test_load_instance_catalog_core_has_no_named_example_instances() -> None:
    catalog = load_instance_catalog(include_entry_points=False)

    assert catalog.instances == ()
    assert catalog.support_repos == ()


def test_core_catalog_status_does_not_require_external_submodules(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "repo-without-submodules"
    config_path = _write_user_config(tmp_path)

    catalog = load_instance_catalog(
        include_entry_points=False,
    )
    status = resolve_builtin_repo_status(
        target_dirname="demo-instance",
        source_root=source_root,
        user_config_path=config_path,
    )

    assert catalog.instances == ()
    assert catalog.support_repos == ()
    assert status.status == "missing"
    assert status.path == (tmp_path / "managed-external" / "demo-instance").resolve()


def test_load_instance_catalog_includes_registered_provider() -> None:
    register_instance_catalog_provider(_FixtureInstanceCatalogProvider())

    catalog = load_instance_catalog(include_entry_points=False)

    assert catalog.get_instance("demo").target_dirname == "demo-instance"
    assert (
        catalog.get_support_repo("fixture-public-data").target_dirname
        == "fixture-public-data"
    )


def test_load_instance_catalog_supports_explicit_yaml(tmp_path: Path) -> None:
    catalog_path = tmp_path / "instances.yaml"
    catalog_path.write_text(
        "\n".join(
            [
                "instances:",
                "  - builtin_id: demo",
                "    label: Demo instance",
                "    repo_url: https://example.test/demo-instance.git",
                "    target_dirname: demo-instance",
                "",
            ]
        ),
        encoding="utf-8",
    )

    catalog = load_instance_catalog(
        catalog_path=catalog_path,
        include_entry_points=False,
    )

    assert catalog.get_instance("demo").repo_url.endswith("demo-instance.git")


def test_register_instance_catalog_provider_rejects_duplicate() -> None:
    register_instance_catalog_provider(_FixtureInstanceCatalogProvider())

    with pytest.raises(BuiltinInstanceCatalogError, match="Duplicate"):
        register_instance_catalog_provider(_FixtureInstanceCatalogProvider())


def test_discover_instance_catalog_providers_loads_entry_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "femic.builtin_instances._iter_instance_catalog_entry_points",
        lambda: (_FixtureEntryPoint(),),
    )

    assert discover_instance_catalog_providers() == ("fixture",)
    catalog = load_instance_catalog(include_entry_points=False)
    assert catalog.get_instance("demo").target_dirname == "demo-instance"


def test_resolve_builtin_repo_status_prefers_source_checkout(tmp_path: Path) -> None:
    source_root = tmp_path / "repo"
    source_repo = source_root / "external" / "demo-instance"
    source_repo.mkdir(parents=True)

    status = resolve_builtin_repo_status(
        target_dirname="demo-instance",
        source_root=source_root,
    )

    assert status.status == "source-checkout"
    assert status.path == source_repo.resolve()


def test_resolve_builtin_external_path_uses_managed_root_when_source_missing(
    tmp_path: Path,
) -> None:
    register_instance_catalog_provider(_FixtureInstanceCatalogProvider())
    source_root = tmp_path / "repo"
    config_path = _write_user_config(tmp_path)

    resolved = resolve_builtin_external_path(
        Path("external/demo-instance/models/demo/base.pin"),
        source_root=source_root,
        user_config_path=config_path,
    )

    assert (
        resolved
        == (
            tmp_path
            / "managed-external"
            / "demo-instance"
            / "models"
            / "demo"
            / "base.pin"
        ).resolve()
    )


def test_install_builtin_instances_clones_support_repo_and_instance(
    tmp_path: Path,
) -> None:
    register_instance_catalog_provider(_FixtureInstanceCatalogProvider())
    config_path = _write_user_config(tmp_path)
    calls: list[list[str]] = []

    def _fake_run(args, **_kwargs):
        calls.append(list(args))
        destination = Path(args[-1])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / ".git").write_text("gitdir", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = install_builtin_instances(
        "demo",
        user_config_path=config_path,
        run_fn=_fake_run,
    )

    assert len(result.installed_paths) == 2
    assert result.skipped_paths == ()
    assert any("fixture-public-data.git" in " ".join(call) for call in calls)
    assert any("demo-instance.git" in " ".join(call) for call in calls)


def test_install_builtin_instances_skips_existing_git_worktrees(tmp_path: Path) -> None:
    register_instance_catalog_provider(_FixtureInstanceCatalogProvider())
    config_path = _write_user_config(tmp_path)
    managed_root = tmp_path / "managed-external"
    for dirname in ("fixture-public-data", "demo-instance"):
        target = managed_root / dirname
        target.mkdir(parents=True)
        (target / ".git").write_text("gitdir", encoding="utf-8")

    result = install_builtin_instances("demo", user_config_path=config_path)

    assert result.installed_paths == ()
    assert len(result.skipped_paths) == 2


def test_install_builtin_instances_fails_for_non_git_target(tmp_path: Path) -> None:
    register_instance_catalog_provider(_FixtureInstanceCatalogProvider())
    config_path = _write_user_config(tmp_path)
    target = tmp_path / "managed-external" / "demo-instance"
    target.mkdir(parents=True)

    with pytest.raises(BuiltinInstanceCatalogError):
        install_builtin_instances("demo", user_config_path=config_path)
