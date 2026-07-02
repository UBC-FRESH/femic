"""Packaged built-in FEMIC instance catalog and installer helpers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata, resources
from pathlib import Path
import subprocess
from typing import Any, Callable, Protocol

import yaml

from femic.user_config import load_femic_user_config


BUILTIN_INSTANCE_PACKAGE = "femic.resources.builtins"
BUILTIN_INSTANCE_RESOURCE = "instances.builtin.yaml"
INSTANCE_CATALOG_ENTRY_POINT_GROUP = "femic.instance_catalogs"

_REGISTERED_INSTANCE_CATALOG_PROVIDERS: dict[str, "InstanceCatalogProvider"] = {}
_DISCOVERED_INSTANCE_CATALOG_PROVIDERS = False


class BuiltinInstanceCatalogError(RuntimeError):
    """Raised when the instance catalog or install state is invalid."""


class InstanceCatalogProvider(Protocol):
    """Provider for installable FEMIC instance catalog metadata."""

    provider_id: str

    def load_catalog_payload(self) -> dict[str, Any]:
        """Return a FEMIC instance catalog payload mapping."""


@dataclass(frozen=True)
class BuiltinSupportRepoDefinition:
    """Auxiliary repo a registered instance may rely on."""

    repo_id: str
    label: str
    repo_url: str
    target_dirname: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BuiltinInstanceDefinition:
    """Standalone FEMIC instance that can be installed for package users."""

    builtin_id: str
    label: str
    repo_url: str
    target_dirname: str
    support_repo_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BuiltinInstanceCatalog:
    """Catalog of installable FEMIC instances."""

    support_repos: tuple[BuiltinSupportRepoDefinition, ...]
    instances: tuple[BuiltinInstanceDefinition, ...]

    def get_instance(self, builtin_id: str) -> BuiltinInstanceDefinition:
        normalized = str(builtin_id or "").strip()
        for item in self.instances:
            if item.builtin_id == normalized:
                return item
        raise BuiltinInstanceCatalogError(
            f"Unknown FEMIC registered instance: {builtin_id}"
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
    """Install status for one registered instance or support repo."""

    status: str
    path: Path


@dataclass(frozen=True)
class BuiltinInstallResult:
    """Summary of one instance catalog install operation."""

    managed_external_root: Path
    installed_paths: tuple[Path, ...]
    skipped_paths: tuple[Path, ...]


def _normalize_provider_id(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise BuiltinInstanceCatalogError(
            "Instance catalog provider id must not be blank."
        )
    return normalized


def register_instance_catalog_provider(provider: InstanceCatalogProvider) -> None:
    """Register one in-process instance catalog provider."""

    provider_id = _normalize_provider_id(getattr(provider, "provider_id", ""))
    if provider_id in _REGISTERED_INSTANCE_CATALOG_PROVIDERS:
        raise BuiltinInstanceCatalogError(
            f"Duplicate instance catalog provider id: {provider_id}"
        )
    payload = provider.load_catalog_payload()
    if not isinstance(payload, dict):
        raise BuiltinInstanceCatalogError(
            f"Instance catalog provider {provider_id} must return a mapping payload."
        )
    _REGISTERED_INSTANCE_CATALOG_PROVIDERS[provider_id] = provider


def clear_instance_catalog_providers() -> None:
    """Clear in-process instance catalog providers for tests and diagnostics."""

    global _DISCOVERED_INSTANCE_CATALOG_PROVIDERS
    _REGISTERED_INSTANCE_CATALOG_PROVIDERS.clear()
    _DISCOVERED_INSTANCE_CATALOG_PROVIDERS = False


def _iter_instance_catalog_entry_points() -> tuple[metadata.EntryPoint, ...]:
    entry_points: Any = metadata.entry_points()
    if hasattr(entry_points, "select"):
        selected = entry_points.select(group=INSTANCE_CATALOG_ENTRY_POINT_GROUP)
    else:  # pragma: no cover - compatibility for older importlib.metadata APIs
        selected = entry_points.get(INSTANCE_CATALOG_ENTRY_POINT_GROUP, ())
    return tuple(selected)


def discover_instance_catalog_providers() -> tuple[str, ...]:
    """Discover installed FEMIC instance catalog providers."""

    global _DISCOVERED_INSTANCE_CATALOG_PROVIDERS
    if _DISCOVERED_INSTANCE_CATALOG_PROVIDERS:
        return tuple(sorted(_REGISTERED_INSTANCE_CATALOG_PROVIDERS))

    for entry_point in _iter_instance_catalog_entry_points():
        try:
            loaded = entry_point.load()
            provider = loaded()
        except Exception as exc:  # pragma: no cover - exercised through tests
            raise BuiltinInstanceCatalogError(
                f"Could not load instance catalog provider {entry_point.name}: {exc}"
            ) from exc
        try:
            register_instance_catalog_provider(provider)
        except BuiltinInstanceCatalogError as exc:
            raise BuiltinInstanceCatalogError(
                f"Invalid instance catalog provider {entry_point.name}: {exc}"
            ) from exc

    _DISCOVERED_INSTANCE_CATALOG_PROVIDERS = True
    return tuple(sorted(_REGISTERED_INSTANCE_CATALOG_PROVIDERS))


def _read_builtin_resource_text() -> str:
    resource = resources.files(BUILTIN_INSTANCE_PACKAGE).joinpath(
        BUILTIN_INSTANCE_RESOURCE
    )
    return resource.read_text(encoding="utf-8")


def _load_packaged_catalog_payload() -> dict[str, Any]:
    try:
        payload = yaml.safe_load(_read_builtin_resource_text())
    except yaml.YAMLError as exc:
        raise BuiltinInstanceCatalogError(
            f"Invalid packaged instance catalog {BUILTIN_INSTANCE_RESOURCE}: {exc}"
        ) from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise BuiltinInstanceCatalogError(
            f"Packaged instance catalog {BUILTIN_INSTANCE_RESOURCE} must be a mapping."
        )
    return payload


def _load_yaml_catalog_path(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise BuiltinInstanceCatalogError(
            f"Invalid instance catalog {path}: {exc}"
        ) from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise BuiltinInstanceCatalogError(f"Instance catalog {path} must be a mapping.")
    return payload


def _parse_notes(payload: Any) -> tuple[str, ...]:
    if payload in (None, ""):
        return ()
    if not isinstance(payload, (list, tuple)):
        raise BuiltinInstanceCatalogError("Instance catalog notes must be a list.")
    return tuple(str(item).strip() for item in payload if str(item).strip())


def _parse_catalog_payload(payload: dict[str, Any]) -> BuiltinInstanceCatalog:
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


def _merge_catalogs(
    catalogs: tuple[BuiltinInstanceCatalog, ...],
) -> BuiltinInstanceCatalog:
    support_by_id: dict[str, BuiltinSupportRepoDefinition] = {}
    instance_by_id: dict[str, BuiltinInstanceDefinition] = {}
    for catalog in catalogs:
        for support_repo in catalog.support_repos:
            support_by_id[support_repo.repo_id] = support_repo
        for instance in catalog.instances:
            instance_by_id[instance.builtin_id] = instance
    return BuiltinInstanceCatalog(
        support_repos=tuple(support_by_id[key] for key in sorted(support_by_id)),
        instances=tuple(instance_by_id[key] for key in sorted(instance_by_id)),
    )


def load_instance_catalog(
    *,
    catalog_path: Path | None = None,
    include_entry_points: bool = True,
) -> BuiltinInstanceCatalog:
    """Load packaged, provider, and optional explicit FEMIC instance catalogs."""

    catalogs = [_parse_catalog_payload(_load_packaged_catalog_payload())]
    if include_entry_points:
        discover_instance_catalog_providers()
    for provider_id in sorted(_REGISTERED_INSTANCE_CATALOG_PROVIDERS):
        payload = _REGISTERED_INSTANCE_CATALOG_PROVIDERS[
            provider_id
        ].load_catalog_payload()
        if not isinstance(payload, dict):
            raise BuiltinInstanceCatalogError(
                f"Instance catalog provider {provider_id} must return a mapping payload."
            )
        catalogs.append(_parse_catalog_payload(payload))
    if catalog_path is not None:
        catalogs.append(_parse_catalog_payload(_load_yaml_catalog_path(catalog_path)))
    return _merge_catalogs(tuple(catalogs))


def load_builtin_instance_catalog() -> BuiltinInstanceCatalog:
    """Load the merged installable FEMIC instance catalog."""

    return load_instance_catalog()


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
    """Return whether a known registered/support repo is available locally."""

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
    """Resolve a repo-local external path for source or package installs."""

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
    """Install one registered instance or all registered instances into the managed root."""

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
