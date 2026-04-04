"""User-scoped FEMIC config helpers for packaged-install workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_FEMIC_CONFIG_HOME = Path.home() / ".femic"
DEFAULT_FEMIC_USER_CONFIG_PATH = DEFAULT_FEMIC_CONFIG_HOME / "user.yaml"
DEFAULT_FEMIC_MANAGED_EXTERNAL_ROOT = DEFAULT_FEMIC_CONFIG_HOME / "external"
DEFAULT_FEMIC_RECIPE_OVERLAY_ROOT = DEFAULT_FEMIC_CONFIG_HOME / "recipe-overlays"
DEFAULT_FEMIC_TSR_ROOT = DEFAULT_FEMIC_CONFIG_HOME / "tsr"
DEFAULT_FEMIC_TSR_CORPUS_ROOT = DEFAULT_FEMIC_TSR_ROOT / "corpus"
DEFAULT_FEMIC_TSR_MANIFEST_PATH = DEFAULT_FEMIC_TSR_ROOT / "tsa_pdf_cache_manifest.json"
DEFAULT_FEMIC_USER_INSTANCE_ROOT = Path.home() / "femic" / "instances"


class FemicUserConfigError(RuntimeError):
    """Raised when the user config file is invalid."""


@dataclass(frozen=True)
class FemicUserPaths:
    """Resolved user-owned FEMIC path defaults."""

    managed_external_root: Path
    user_instance_root: Path


@dataclass(frozen=True)
class FemicUserConfig:
    """Loaded FEMIC user config plus the resolved config file path."""

    config_path: Path
    paths: FemicUserPaths
    exists: bool


def resolve_femic_user_config_path(user_config_path: Path | None = None) -> Path:
    """Return the resolved FEMIC user config path."""

    candidate = (
        user_config_path.expanduser().resolve()
        if user_config_path is not None
        else DEFAULT_FEMIC_USER_CONFIG_PATH.expanduser().resolve()
    )
    return candidate


def default_femic_user_paths() -> FemicUserPaths:
    """Return the default packaged-install FEMIC user paths."""

    return FemicUserPaths(
        managed_external_root=DEFAULT_FEMIC_MANAGED_EXTERNAL_ROOT.expanduser().resolve(),
        user_instance_root=DEFAULT_FEMIC_USER_INSTANCE_ROOT.expanduser().resolve(),
    )


def default_femic_recipe_overlay_root() -> Path:
    """Return the default user-owned recipe overlay root."""

    return DEFAULT_FEMIC_RECIPE_OVERLAY_ROOT.expanduser().resolve()


def default_femic_tsr_corpus_root() -> Path:
    """Return the default user-local TSR PDF corpus root."""

    return DEFAULT_FEMIC_TSR_CORPUS_ROOT.expanduser().resolve()


def default_femic_tsr_cache_manifest_path() -> Path:
    """Return the default user-local TSR PDF cache manifest path."""

    return DEFAULT_FEMIC_TSR_MANIFEST_PATH.expanduser().resolve()


def _load_yaml_payload(config_path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise FemicUserConfigError(
            f"Invalid FEMIC user config {config_path}: {exc}"
        ) from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise FemicUserConfigError(
            f"FEMIC user config {config_path} must be a mapping."
        )
    return payload


def load_femic_user_config(user_config_path: Path | None = None) -> FemicUserConfig:
    """Load the user config or return the default path set if no file exists."""

    config_path = resolve_femic_user_config_path(user_config_path)
    defaults = default_femic_user_paths()
    if not config_path.exists():
        return FemicUserConfig(config_path=config_path, paths=defaults, exists=False)

    payload = _load_yaml_payload(config_path)
    paths_payload = payload.get("paths", {})
    if paths_payload in (None, ""):
        paths_payload = {}
    if not isinstance(paths_payload, dict):
        raise FemicUserConfigError(
            f"FEMIC user config {config_path} field paths must be a mapping."
        )

    managed_external_root = paths_payload.get("managed_external_root")
    user_instance_root = paths_payload.get("user_instance_root")
    resolved_paths = FemicUserPaths(
        managed_external_root=(
            defaults.managed_external_root
            if managed_external_root in (None, "")
            else Path(str(managed_external_root)).expanduser().resolve()
        ),
        user_instance_root=(
            defaults.user_instance_root
            if user_instance_root in (None, "")
            else Path(str(user_instance_root)).expanduser().resolve()
        ),
    )
    return FemicUserConfig(
        config_path=config_path,
        paths=resolved_paths,
        exists=True,
    )


def write_femic_user_config(
    config: FemicUserConfig,
    *,
    user_config_path: Path | None = None,
) -> Path:
    """Persist one FEMIC user config file to disk."""

    config_path = resolve_femic_user_config_path(user_config_path or config.config_path)
    payload = {
        "paths": {
            "managed_external_root": str(config.paths.managed_external_root),
            "user_instance_root": str(config.paths.user_instance_root),
        }
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    return config_path


def with_managed_external_root(
    config: FemicUserConfig,
    managed_external_root: Path,
) -> FemicUserConfig:
    """Return a config copy with an updated managed external root."""

    return FemicUserConfig(
        config_path=config.config_path,
        exists=config.exists,
        paths=FemicUserPaths(
            managed_external_root=managed_external_root.expanduser().resolve(),
            user_instance_root=config.paths.user_instance_root,
        ),
    )


def with_user_instance_root(
    config: FemicUserConfig,
    user_instance_root: Path,
) -> FemicUserConfig:
    """Return a config copy with an updated visible user instance root."""

    return FemicUserConfig(
        config_path=config.config_path,
        exists=config.exists,
        paths=FemicUserPaths(
            managed_external_root=config.paths.managed_external_root,
            user_instance_root=user_instance_root.expanduser().resolve(),
        ),
    )
