"""Registry-backed Patchworks variant resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
import shutil
import subprocess
from typing import Any

import yaml


PATCHWORKS_VARIANT_REGISTRY_PACKAGE = "femic.resources.patchworks"
PATCHWORKS_BUILTIN_VARIANTS_RESOURCE = "variants.builtin.yaml"
DEFAULT_PATCHWORKS_USER_REGISTRY_PATH = Path.home() / ".femic" / "variants.yaml"
DEFAULT_PATCHWORKS_MATERIALIZATION_PROMPT_BYTES = 100 * 1024 * 1024


class PatchworksVariantRegistryError(RuntimeError):
    """Raised when Patchworks variant registry content is invalid."""


@dataclass(frozen=True)
class PatchworksVariantMaterializationAction:
    """Materialization hint carried by a registry entry."""

    kind: str
    dataset_root: str | None = None
    relpaths: tuple[str, ...] = ()
    estimated_bytes: int | None = None


@dataclass(frozen=True)
class PatchworksVariantMaterializationPlan:
    """Summary of the prelaunch materialization implied by one variant."""

    action_count: int
    known_estimated_bytes: int
    has_unknown_sizes: bool
    requires_confirmation: bool


@dataclass(frozen=True)
class PatchworksVariantDefinition:
    """Resolved Patchworks variant registry entry."""

    variant_id: str
    label: str
    instance_id: str
    instance_label: str
    variant_family: str
    kind: str
    instance_root: Path
    analysis_pin: Path
    runtime_config: Path
    default: bool = False
    notes: tuple[str, ...] = ()
    materialization: tuple[PatchworksVariantMaterializationAction, ...] = ()
    runtime: dict[str, Any] | None = None
    source: str = "builtin"
    registry_path: Path | None = None


@dataclass(frozen=True)
class PatchworksInstanceDefinition:
    """Grouped view of variants that belong to one instance."""

    instance_id: str
    label: str
    variant_ids: tuple[str, ...]
    default_variant_id: str | None = None


@dataclass(frozen=True)
class PatchworksVariantRegistry:
    """Merged built-in plus user Patchworks variant registry."""

    variants: tuple[PatchworksVariantDefinition, ...]
    instances: tuple[PatchworksInstanceDefinition, ...]
    builtin_registry_loaded: bool
    user_registry_path: Path | None

    def get_variant(self, variant_id: str) -> PatchworksVariantDefinition:
        """Return one variant by id or raise a registry error."""
        normalized = variant_id.strip()
        for variant in self.variants:
            if variant.variant_id == normalized:
                return variant
        raise PatchworksVariantRegistryError(
            f"Unknown Patchworks variant: {variant_id}"
        )


def _source_tree_root() -> Path:
    """Return the FEMIC source checkout root that owns this module."""
    return Path(__file__).resolve().parents[2]


def _read_patchworks_resource_text(resource_name: str) -> str:
    resource = resources.files(PATCHWORKS_VARIANT_REGISTRY_PACKAGE).joinpath(
        resource_name
    )
    return resource.read_text(encoding="utf-8")


def _load_yaml_payload(text: str, *, source_label: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:  # pragma: no cover - exercised by callers
        raise PatchworksVariantRegistryError(
            f"Invalid Patchworks variant registry YAML in {source_label}: {exc}"
        ) from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise PatchworksVariantRegistryError(
            f"Patchworks variant registry {source_label} must be a mapping."
        )
    return payload


def _as_str(value: Any, field_name: str, *, source_label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise PatchworksVariantRegistryError(
            f"Patchworks variant registry {source_label} missing {field_name}."
        )
    return text


def _normalize_relpath(value: Any, field_name: str, *, source_label: str) -> Path:
    raw = _as_str(value, field_name, source_label=source_label)
    return Path(raw)


def _resolve_registry_path(value: Path, *, base_dir: Path) -> Path:
    candidate = value.expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (base_dir / candidate).resolve()


def _parse_materialization_actions(
    payload: Any,
    *,
    source_label: str,
) -> tuple[PatchworksVariantMaterializationAction, ...]:
    if payload in (None, ""):
        return ()
    if not isinstance(payload, (list, tuple)):
        raise PatchworksVariantRegistryError(
            f"Patchworks variant registry {source_label} field materialization "
            "must be a list."
        )
    actions: list[PatchworksVariantMaterializationAction] = []
    for item in payload:
        if not isinstance(item, dict):
            raise PatchworksVariantRegistryError(
                f"Patchworks variant registry {source_label} materialization items "
                "must be mappings."
            )
        kind = _as_str(
            item.get("kind"), "materialization.kind", source_label=source_label
        )
        dataset_root = (
            str(item.get("dataset_root")).strip() if item.get("dataset_root") else None
        )
        relpaths_payload = item.get("relpaths", ())
        if relpaths_payload in (None, ""):
            relpaths: tuple[str, ...] = ()
        else:
            if not isinstance(relpaths_payload, list):
                raise PatchworksVariantRegistryError(
                    f"Patchworks variant registry {source_label} materialization.relpaths "
                    "must be a list."
                )
            relpaths = tuple(
                str(part).strip() for part in relpaths_payload if str(part).strip()
            )
        estimated_raw = item.get("estimated_bytes")
        if estimated_raw in (None, ""):
            estimated_bytes = None
        else:
            estimated_bytes = int(str(estimated_raw).strip())
        actions.append(
            PatchworksVariantMaterializationAction(
                kind=kind,
                dataset_root=dataset_root,
                relpaths=relpaths,
                estimated_bytes=estimated_bytes,
            )
        )
    return tuple(actions)


def _load_variant_entries_from_payload(
    payload: dict[str, Any],
    *,
    base_dir: Path,
    source_label: str,
    source_kind: str,
    registry_path: Path | None,
) -> tuple[PatchworksVariantDefinition, ...]:
    instances_payload = payload.get("instances", ())
    if instances_payload in (None, ""):
        instance_labels: dict[str, str] = {}
    else:
        if not isinstance(instances_payload, (list, tuple)):
            raise PatchworksVariantRegistryError(
                f"Patchworks variant registry {source_label} field instances must be a list."
            )
        instance_labels = {}
        for item in instances_payload:
            if not isinstance(item, dict):
                raise PatchworksVariantRegistryError(
                    f"Patchworks variant registry {source_label} instance items must be mappings."
                )
            instance_id = _as_str(
                item.get("instance_id"), "instance_id", source_label=source_label
            )
            instance_labels[instance_id] = str(item.get("label") or instance_id).strip()

    variants_payload = payload.get("variants", ())
    if variants_payload in (None, ""):
        return ()
    if not isinstance(variants_payload, (list, tuple)):
        raise PatchworksVariantRegistryError(
            f"Patchworks variant registry {source_label} field variants must be a list."
        )

    variants: list[PatchworksVariantDefinition] = []
    for item in variants_payload:
        if not isinstance(item, dict):
            raise PatchworksVariantRegistryError(
                f"Patchworks variant registry {source_label} variant items must be mappings."
            )
        variant_id = _as_str(
            item.get("variant_id"), "variant_id", source_label=source_label
        )
        instance_id = _as_str(
            item.get("instance_id"), "instance_id", source_label=source_label
        )
        label = _as_str(item.get("label"), "label", source_label=source_label)
        instance_label = instance_labels.get(instance_id, instance_id)
        family = str(item.get("variant_family") or "default").strip() or "default"
        kind = str(item.get("kind") or "patchworks").strip() or "patchworks"
        instance_root = _resolve_registry_path(
            _normalize_relpath(
                item.get("instance_root"), "instance_root", source_label=source_label
            ),
            base_dir=base_dir,
        )
        analysis_pin = _resolve_registry_path(
            _normalize_relpath(
                item.get("analysis_pin"), "analysis_pin", source_label=source_label
            ),
            base_dir=base_dir,
        )
        runtime_config = _resolve_registry_path(
            _normalize_relpath(
                item.get("runtime_config"), "runtime_config", source_label=source_label
            ),
            base_dir=base_dir,
        )
        notes_payload = item.get("notes", ())
        if notes_payload in (None, ""):
            notes: tuple[str, ...] = ()
        else:
            if not isinstance(notes_payload, (list, tuple)):
                raise PatchworksVariantRegistryError(
                    f"Patchworks variant registry {source_label} field notes must be a list."
                )
            notes = tuple(
                str(note).strip() for note in notes_payload if str(note).strip()
            )
        runtime_payload = item.get("runtime")
        if runtime_payload is not None and not isinstance(runtime_payload, dict):
            raise PatchworksVariantRegistryError(
                f"Patchworks variant registry {source_label} field runtime must be a mapping."
            )
        variants.append(
            PatchworksVariantDefinition(
                variant_id=variant_id,
                label=label,
                instance_id=instance_id,
                instance_label=instance_label,
                variant_family=family,
                kind=kind,
                instance_root=instance_root,
                analysis_pin=analysis_pin,
                runtime_config=runtime_config,
                default=bool(item.get("default", False)),
                notes=notes,
                materialization=_parse_materialization_actions(
                    item.get("materialization"),
                    source_label=source_label,
                ),
                runtime=dict(runtime_payload)
                if isinstance(runtime_payload, dict)
                else None,
                source=source_kind,
                registry_path=registry_path,
            )
        )
    return tuple(variants)


def _build_instance_definitions(
    variants: tuple[PatchworksVariantDefinition, ...],
) -> tuple[PatchworksInstanceDefinition, ...]:
    grouped: dict[str, list[PatchworksVariantDefinition]] = {}
    for variant in variants:
        grouped.setdefault(variant.instance_id, []).append(variant)
    instances: list[PatchworksInstanceDefinition] = []
    for instance_id in sorted(grouped):
        items = sorted(grouped[instance_id], key=lambda item: item.variant_id)
        default_variant_id = next(
            (item.variant_id for item in items if item.default),
            None,
        )
        instances.append(
            PatchworksInstanceDefinition(
                instance_id=instance_id,
                label=items[0].instance_label,
                variant_ids=tuple(item.variant_id for item in items),
                default_variant_id=default_variant_id,
            )
        )
    return tuple(instances)


def load_patchworks_variant_registry(
    *,
    user_registry_path: Path | None = None,
    source_root: Path | None = None,
) -> PatchworksVariantRegistry:
    """Load the merged built-in and optional user Patchworks variant registry."""

    effective_source_root = (source_root or _source_tree_root()).expanduser().resolve()
    builtin_payload = _load_yaml_payload(
        _read_patchworks_resource_text(PATCHWORKS_BUILTIN_VARIANTS_RESOURCE),
        source_label=PATCHWORKS_BUILTIN_VARIANTS_RESOURCE,
    )
    merged_by_id: dict[str, PatchworksVariantDefinition] = {
        item.variant_id: item
        for item in _load_variant_entries_from_payload(
            builtin_payload,
            base_dir=effective_source_root,
            source_label=PATCHWORKS_BUILTIN_VARIANTS_RESOURCE,
            source_kind="builtin",
            registry_path=None,
        )
    }

    effective_user_registry = (
        user_registry_path.expanduser().resolve()
        if user_registry_path is not None
        else DEFAULT_PATCHWORKS_USER_REGISTRY_PATH.expanduser().resolve()
    )
    if effective_user_registry.exists():
        user_payload = _load_yaml_payload(
            effective_user_registry.read_text(encoding="utf-8"),
            source_label=str(effective_user_registry),
        )
        for item in _load_variant_entries_from_payload(
            user_payload,
            base_dir=effective_source_root,
            source_label=str(effective_user_registry),
            source_kind="user",
            registry_path=effective_user_registry,
        ):
            merged_by_id[item.variant_id] = item
        user_path_result: Path | None = effective_user_registry
    else:
        user_path_result = None

    variants = tuple(sorted(merged_by_id.values(), key=lambda item: item.variant_id))
    return PatchworksVariantRegistry(
        variants=variants,
        instances=_build_instance_definitions(variants),
        builtin_registry_loaded=True,
        user_registry_path=user_path_result,
    )


def _resolve_datalad_executable(*, source_root: Path) -> str:
    path_tool = shutil.which("datalad")
    if path_tool:
        return path_tool
    windows_candidate = source_root / ".venv" / "Scripts" / "datalad.exe"
    if windows_candidate.exists():
        return str(windows_candidate.resolve())
    posix_candidate = source_root / ".venv" / "bin" / "datalad"
    if posix_candidate.exists():
        return str(posix_candidate.resolve())
    raise PatchworksVariantRegistryError(
        "DataLad executable not found (looked on PATH and in .venv)."
    )


def _resolve_materialization_dataset_root(
    action: PatchworksVariantMaterializationAction,
    *,
    source_root: Path,
) -> Path:
    if not action.dataset_root:
        raise PatchworksVariantRegistryError(
            "Patchworks variant materialization action missing dataset_root."
        )
    return _resolve_registry_path(Path(action.dataset_root), base_dir=source_root)


def build_patchworks_variant_materialization_plan(
    variant: PatchworksVariantDefinition,
    *,
    prompt_threshold_bytes: int = DEFAULT_PATCHWORKS_MATERIALIZATION_PROMPT_BYTES,
) -> PatchworksVariantMaterializationPlan:
    """Summarize whether a variant requires guarded prelaunch materialization."""

    known_estimated_bytes = 0
    has_unknown_sizes = False
    for action in variant.materialization:
        if action.estimated_bytes is None:
            has_unknown_sizes = True
        else:
            known_estimated_bytes += action.estimated_bytes
    return PatchworksVariantMaterializationPlan(
        action_count=len(variant.materialization),
        known_estimated_bytes=known_estimated_bytes,
        has_unknown_sizes=has_unknown_sizes,
        requires_confirmation=known_estimated_bytes > prompt_threshold_bytes,
    )


def materialize_patchworks_variant(
    variant: PatchworksVariantDefinition,
    *,
    source_root: Path | None = None,
) -> None:
    """Run any declared materialization actions required before Patchworks launch."""

    if not variant.materialization:
        return

    effective_source_root = (source_root or _source_tree_root()).expanduser().resolve()
    datalad_executable = _resolve_datalad_executable(source_root=effective_source_root)

    for action in variant.materialization:
        if action.kind != "datalad-get":
            raise PatchworksVariantRegistryError(
                f"Unsupported Patchworks materialization action kind: {action.kind}"
            )

        dataset_root = _resolve_materialization_dataset_root(
            action,
            source_root=effective_source_root,
        )
        if not dataset_root.exists():
            raise PatchworksVariantRegistryError(
                f"Patchworks materialization dataset root not found: {dataset_root}"
            )

        relpaths = list(action.relpaths) if action.relpaths else ["."]
        completed = subprocess.run(
            [datalad_executable, "get", *relpaths],
            cwd=dataset_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise PatchworksVariantRegistryError(
                "Patchworks variant materialization failed: "
                f"datalad get in {dataset_root} returned {completed.returncode}"
                + (f" ({detail})" if detail else "")
            )
