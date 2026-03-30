"""Packaged built-in FEMIC instance catalog and installer helpers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
import subprocess
from typing import Any, Callable

import yaml

from femic.user_config import load_femic_user_config


BUILTIN_INSTANCE_PACKAGE = "femic.resources.builtins"
BUILTIN_INSTANCE_RESOURCE = "instances.builtin.yaml"


class BuiltinInstanceCatalogError(RuntimeError):
    """Raised when the built-in instance catalog or install state is invalid."""


@dataclass(frozen=True)
class BuiltinSupportRepoDefinition:
    """Auxiliary repo a built-in instance may rely on."""

    repo_id: str
    label: str
    repo_url: str
    target_dirname: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BuiltinInstanceDefinition:
    """Standalone FEMIC-built instance that can be installed for package users."""

    builtin_id: str
    label: str
    repo_url: str
    target_dirname: str
    support_repo_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BuiltinInstanceCatalog:
    """Shipped catalog of installable FEMIC built-ins."""

    support_repos: tuple[BuiltinSupportRepoDefinition, ...]
    instances: tuple[BuiltinInstanceDefinition, ...]

    def get_instance(self, builtin_id: str) -> BuiltinInstanceDefinition:
        normalized = str(builtin_id or "").strip()
        for item in self.instances:
            if item.builtin_id == normalized:
                return item
        raise BuiltinInstanceCatalogError(
            f"Unknown FEMIC built-in instance: {builtin_id}"
        )

    def get_support_repo(self, repo_id: str) -> BuiltinSupportRepoDefinition:
        normalized = str(repo_id or "").strip()
        for item in self.support_repos:
            if item.repo_id == normalized:
                return item
        raise BuiltinInstanceCatalogError(f"Unknown FEMIC support repo: {repo_id}")

    def known_target_dirnames(self) -> set[str]:
        return {item.target_dirname for item in self.instances}.union(
            item.target_dirname for item in self.support_repos
        )


@dataclass(frozen=True)
class BuiltinRepoStatus:
    """Install status for one built-in or support repo."""

    status: str
    path: Path


@dataclass(frozen=True)
class BuiltinInstallResult:
    """Summary of one built-in install operation."""

    managed_external_root: Path
    installed_paths: tuple[Path, ...]
    skipped_paths: tuple[Path, ...]


def _read_builtin_resource_text() -> str:
    resource = resources.files(BUILTIN_INSTANCE_PACKAGE).joinpath(
        BUILTIN_INSTANCE_RESOURCE
    )
    return resource.read_text(encoding="utf-8")


def _load_catalog_payload() -> dict[str, Any]:
    try:
        payload = yaml.safe_load(_read_builtin_resource_text())
    except yaml.YAMLError as exc:
        raise BuiltinInstanceCatalogError(
            f"Invalid built-in instance catalog {BUILTIN_INSTANCE_RESOURCE}: {exc}"
        ) from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise BuiltinInstanceCatalogError(
            f"Built-in instance catalog {BUILTIN_INSTANCE_RESOURCE} must be a mapping."
        )
    return payload


def _parse_notes(payload: Any) -> tuple[str, ...]:
    if payload in (None, ""):
        return ()
    if not isinstance(payload, (list, tuple)):
        raise BuiltinInstanceCatalogError("Built-in catalog notes must be a list.")
    return tuple(str(item).strip() for item in payload if str(item).strip())


def load_builtin_instance_catalog() -> BuiltinInstanceCatalog:
    """Load the packaged built-in instance catalog."""

    payload = _load_catalog_payload()
    support_payload = payload.get("support_repos", ())
    instance_payload = payload.get("instances", ())
    if not isinstance(support_payload, (list, tuple)):
        raise BuiltinInstanceCatalogError(
            "Built-in catalog support_repos must be a list."
        )
    if not isinstance(instance_payload, (list, tuple)):
        raise BuiltinInstanceCatalogError("Built-in catalog instances must be a list.")

    support_repos = tuple(
        BuiltinSupportRepoDefinition(
            repo_id=str(item["repo_id"]).strip(),
            label=str(item["label"]).strip(),
            repo_url=str(item["repo_url"]).strip(),
            target_dirname=str(item["target_dirname"]).strip(),
            notes=_parse_notes(item.get("notes")),
        )
        for item in support_payload
    )
    instances = tuple(
        BuiltinInstanceDefinition(
            builtin_id=str(item["builtin_id"]).strip(),
            label=str(item["label"]).strip(),
            repo_url=str(item["repo_url"]).strip(),
            target_dirname=str(item["target_dirname"]).strip(),
            support_repo_ids=tuple(
                str(repo_id).strip()
                for repo_id in item.get("support_repo_ids", ())
                if str(repo_id).strip()
            ),
            notes=_parse_notes(item.get("notes")),
        )
        for item in instance_payload
    )
    return BuiltinInstanceCatalog(support_repos=support_repos, instances=instances)


def _looks_like_git_worktree(path: Path) -> bool:
    return (path / ".git").exists()


def _source_tree_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_builtin_repo_status(
    *,
    target_dirname: str,
    source_root: Path | None = None,
    user_config_path: Path | None = None,
) -> BuiltinRepoStatus:
    """Return whether a known built-in/support repo is available locally."""

    effective_source_root = (source_root or _source_tree_root()).expanduser().resolve()
    source_candidate = (effective_source_root / "external" / target_dirname).resolve()
    if source_candidate.exists():
        return BuiltinRepoStatus(status="source-checkout", path=source_candidate)

    managed_root = load_femic_user_config(user_config_path).paths.managed_external_root
    managed_candidate = (managed_root / target_dirname).resolve()
    if _looks_like_git_worktree(managed_candidate):
        return BuiltinRepoStatus(status="installed", path=managed_candidate)
    return BuiltinRepoStatus(status="missing", path=managed_candidate)


def resolve_builtin_external_path(
    relpath: Path,
    *,
    source_root: Path | None = None,
    user_config_path: Path | None = None,
) -> Path:
    """Resolve a repo-local built-in external path for source or package installs."""

    candidate = relpath.expanduser()
    if candidate.is_absolute():
        return candidate.resolve()

    parts = candidate.parts
    effective_source_root = (source_root or _source_tree_root()).expanduser().resolve()
    source_candidate = (effective_source_root / candidate).resolve()
    if len(parts) < 2 or parts[0] != "external":
        return source_candidate
    if source_candidate.exists():
        return source_candidate

    known_dirnames = load_builtin_instance_catalog().known_target_dirnames()
    target_dirname = parts[1]
    if target_dirname not in known_dirnames:
        return source_candidate

    managed_root = load_femic_user_config(user_config_path).paths.managed_external_root
    if len(parts) == 2:
        return (managed_root / target_dirname).resolve()
    return (managed_root / target_dirname / Path(*parts[2:])).resolve()


def _clone_repo(
    *,
    repo_url: str,
    destination: Path,
    git_executable: str,
    run_fn: Callable[..., Any],
) -> None:
    try:
        completed = run_fn(
            [
                git_executable,
                "clone",
                "--recurse-submodules",
                repo_url,
                str(destination),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise BuiltinInstanceCatalogError(
            f"git clone failed for {repo_url} -> {destination}: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or f"exit={completed.returncode}"
        )
        raise BuiltinInstanceCatalogError(
            f"git clone failed for {repo_url} -> {destination}: {detail}"
        )


def _ensure_repo_present(
    *,
    repo_url: str,
    target_dirname: str,
    managed_external_root: Path,
    git_executable: str,
    run_fn: Callable[..., Any],
) -> tuple[Path, bool]:
    destination = (managed_external_root / target_dirname).resolve()
    if destination.exists():
        if _looks_like_git_worktree(destination):
            return destination, False
        raise BuiltinInstanceCatalogError(
            f"Refusing to install into existing non-git directory: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    _clone_repo(
        repo_url=repo_url,
        destination=destination,
        git_executable=git_executable,
        run_fn=run_fn,
    )
    return destination, True


def install_builtin_instances(
    builtin_id: str,
    *,
    user_config_path: Path | None = None,
    git_executable: str = "git",
    run_fn: Callable[..., Any] = subprocess.run,
) -> BuiltinInstallResult:
    """Install one built-in instance or all built-ins into the managed root."""

    catalog = load_builtin_instance_catalog()
    managed_external_root = load_femic_user_config(
        user_config_path
    ).paths.managed_external_root
    selected_instances = (
        catalog.instances
        if str(builtin_id or "").strip() == "all"
        else (catalog.get_instance(builtin_id),)
    )

    installed_paths: list[Path] = []
    skipped_paths: list[Path] = []
    ensured_support_repo_ids: set[str] = set()

    for instance in selected_instances:
        for repo_id in instance.support_repo_ids:
            if repo_id in ensured_support_repo_ids:
                continue
            support_repo = catalog.get_support_repo(repo_id)
            path, installed = _ensure_repo_present(
                repo_url=support_repo.repo_url,
                target_dirname=support_repo.target_dirname,
                managed_external_root=managed_external_root,
                git_executable=git_executable,
                run_fn=run_fn,
            )
            (installed_paths if installed else skipped_paths).append(path)
            ensured_support_repo_ids.add(repo_id)
        path, installed = _ensure_repo_present(
            repo_url=instance.repo_url,
            target_dirname=instance.target_dirname,
            managed_external_root=managed_external_root,
            git_executable=git_executable,
            run_fn=run_fn,
        )
        (installed_paths if installed else skipped_paths).append(path)

    return BuiltinInstallResult(
        managed_external_root=managed_external_root,
        installed_paths=tuple(installed_paths),
        skipped_paths=tuple(skipped_paths),
    )
