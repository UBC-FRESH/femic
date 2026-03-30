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
class PatchworksVariantMaterializationDatasetSummary:
    """Dataset-root grouped summary of variant materialization actions."""

    dataset_root: str
    action_count: int
    known_estimated_bytes: int
    has_unknown_sizes: bool
    relpaths: tuple[str, ...]


@dataclass(frozen=True)
class PatchworksVariantScenarioDefinition:
    """Named scenario contract attached to one registry variant."""

    scenario_id: str
    label: str
    mode: str
    target: str | None = None
    min_annual: float | None = None
    iterations: int | None = None
    improvement: float | None = None
    stage_label: str | None = None


@dataclass(frozen=True)
class PatchworksScenarioSetMember:
    """One variant/scenario reference inside a named scenario set."""

    variant_id: str
    scenario_id: str


@dataclass(frozen=True)
class PatchworksScenarioSetDefinition:
    """Named collection of scenarios that can be executed together."""

    scenario_set_id: str
    label: str
    mode: str
    scenarios: tuple[PatchworksScenarioSetMember, ...]
    instance_id: str | None = None
    scenario_set_family: str | None = None
    default: bool = False
    notes: tuple[str, ...] = ()


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
    default_scenario_id: str | None = None
    notes: tuple[str, ...] = ()
    materialization: tuple[PatchworksVariantMaterializationAction, ...] = ()
    scenarios: tuple[PatchworksVariantScenarioDefinition, ...] = ()
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
    default_scenario_set_id: str | None = None


@dataclass(frozen=True)
class PatchworksVariantRegistry:
    """Merged built-in plus user Patchworks variant registry."""

    variants: tuple[PatchworksVariantDefinition, ...]
    instances: tuple[PatchworksInstanceDefinition, ...]
    scenario_sets: tuple[PatchworksScenarioSetDefinition, ...]
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

    def get_scenario(
        self,
        variant_id: str,
        scenario_id: str,
    ) -> tuple[PatchworksVariantDefinition, PatchworksVariantScenarioDefinition]:
        """Return one named scenario attached to one variant."""

        variant = self.get_variant(variant_id)
        normalized_scenario_id = str(scenario_id or "").strip()
        for scenario in variant.scenarios:
            if scenario.scenario_id == normalized_scenario_id:
                return variant, scenario
        raise PatchworksVariantRegistryError(
            f"Unknown Patchworks scenario {scenario_id} for variant {variant_id}"
        )

    def get_default_scenario(
        self,
        variant_id: str,
    ) -> tuple[PatchworksVariantDefinition, PatchworksVariantScenarioDefinition]:
        """Return the default scenario for one variant."""

        variant = self.get_variant(variant_id)
        if variant.default_scenario_id:
            return self.get_scenario(variant.variant_id, variant.default_scenario_id)
        if len(variant.scenarios) == 1:
            return variant, variant.scenarios[0]
        raise PatchworksVariantRegistryError(
            f"Variant {variant_id} does not define a default Patchworks scenario."
        )

    def get_scenario_set(self, scenario_set_id: str) -> PatchworksScenarioSetDefinition:
        """Return one named scenario set or raise a registry error."""

        normalized = str(scenario_set_id or "").strip()
        for scenario_set in self.scenario_sets:
            if scenario_set.scenario_set_id == normalized:
                return scenario_set
        raise PatchworksVariantRegistryError(
            f"Unknown Patchworks scenario set: {scenario_set_id}"
        )

    def iter_scenario_sets(
        self,
        *,
        instance_id: str | None = None,
    ) -> tuple[PatchworksScenarioSetDefinition, ...]:
        """Return scenario sets, optionally filtered by instance id."""

        normalized = str(instance_id or "").strip()
        if not normalized:
            return self.scenario_sets
        return tuple(
            item for item in self.scenario_sets if item.instance_id == normalized
        )

    def get_default_scenario_set(
        self,
        instance_id: str,
    ) -> PatchworksScenarioSetDefinition:
        """Return the default scenario set for one instance."""

        normalized = str(instance_id or "").strip()
        instance = next(
            (item for item in self.instances if item.instance_id == normalized),
            None,
        )
        if instance is None:
            raise PatchworksVariantRegistryError(
                f"Unknown Patchworks instance: {instance_id}"
            )
        if instance.default_scenario_set_id:
            return self.get_scenario_set(instance.default_scenario_set_id)
        raise PatchworksVariantRegistryError(
            f"Instance {instance_id} does not define a default Patchworks scenario set."
        )


def _normalize_variant_id(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise PatchworksVariantRegistryError("Patchworks variant id must not be blank.")
    return normalized


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


def resolve_patchworks_user_registry_path(
    user_registry_path: Path | None = None,
) -> Path:
    """Resolve the writable user overlay registry path."""

    candidate = (
        user_registry_path.expanduser().resolve()
        if user_registry_path is not None
        else DEFAULT_PATCHWORKS_USER_REGISTRY_PATH.expanduser().resolve()
    )
    return candidate


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


def _parse_variant_scenarios(
    payload: Any,
    *,
    source_label: str,
) -> tuple[PatchworksVariantScenarioDefinition, ...]:
    if payload in (None, ""):
        return ()
    if not isinstance(payload, (list, tuple)):
        raise PatchworksVariantRegistryError(
            f"Patchworks variant registry {source_label} field scenarios must be a list."
        )
    scenarios: list[PatchworksVariantScenarioDefinition] = []
    for item in payload:
        if not isinstance(item, dict):
            raise PatchworksVariantRegistryError(
                f"Patchworks variant registry {source_label} scenario items must be mappings."
            )
        scenario_id = _as_str(
            item.get("scenario_id"),
            "scenario_id",
            source_label=source_label,
        )
        mode = _as_str(item.get("mode"), "mode", source_label=source_label)
        label = str(item.get("label") or scenario_id).strip() or scenario_id
        target = str(item.get("target") or "").strip() or None
        min_annual_raw = item.get("min_annual")
        iterations_raw = item.get("iterations")
        improvement_raw = item.get("improvement")
        stage_label = str(item.get("stage_label") or "").strip() or None
        scenarios.append(
            PatchworksVariantScenarioDefinition(
                scenario_id=scenario_id,
                label=label,
                mode=mode,
                target=target,
                min_annual=None
                if min_annual_raw in (None, "")
                else float(str(min_annual_raw).strip()),
                iterations=None
                if iterations_raw in (None, "")
                else int(str(iterations_raw).strip()),
                improvement=None
                if improvement_raw in (None, "")
                else float(str(improvement_raw).strip()),
                stage_label=stage_label,
            )
        )
    return tuple(scenarios)


def _parse_instance_metadata(
    payload: dict[str, Any],
    *,
    source_label: str,
) -> dict[str, dict[str, str]]:
    instances_payload = payload.get("instances", ())
    if instances_payload in (None, ""):
        return {}
    if not isinstance(instances_payload, (list, tuple)):
        raise PatchworksVariantRegistryError(
            f"Patchworks variant registry {source_label} field instances must be a list."
        )

    metadata: dict[str, dict[str, str]] = {}
    for item in instances_payload:
        if not isinstance(item, dict):
            raise PatchworksVariantRegistryError(
                f"Patchworks variant registry {source_label} instance items must be mappings."
            )
        instance_id = _as_str(
            item.get("instance_id"), "instance_id", source_label=source_label
        )
        record: dict[str, str] = {
            "label": str(item.get("label") or instance_id).strip() or instance_id,
        }
        default_scenario_set_id = str(item.get("default_scenario_set_id") or "").strip()
        if default_scenario_set_id:
            record["default_scenario_set_id"] = default_scenario_set_id
        metadata[instance_id] = record
    return metadata


def _load_variant_entries_from_payload(
    payload: dict[str, Any],
    *,
    base_dir: Path,
    source_label: str,
    source_kind: str,
    registry_path: Path | None,
) -> tuple[PatchworksVariantDefinition, ...]:
    instance_metadata = _parse_instance_metadata(payload, source_label=source_label)

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
        instance_label = instance_metadata.get(instance_id, {}).get(
            "label", instance_id
        )
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
                default_scenario_id=(
                    str(item.get("default_scenario_id") or "").strip() or None
                ),
                notes=notes,
                materialization=_parse_materialization_actions(
                    item.get("materialization"),
                    source_label=source_label,
                ),
                scenarios=_parse_variant_scenarios(
                    item.get("scenarios"),
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
    instance_metadata: dict[str, dict[str, str]] | None = None,
) -> tuple[PatchworksInstanceDefinition, ...]:
    effective_metadata = instance_metadata or {}
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
                label=effective_metadata.get(instance_id, {}).get(
                    "label",
                    items[0].instance_label,
                ),
                variant_ids=tuple(item.variant_id for item in items),
                default_variant_id=default_variant_id,
                default_scenario_set_id=effective_metadata.get(instance_id, {}).get(
                    "default_scenario_set_id"
                ),
            )
        )
    return tuple(instances)


def _merge_instance_metadata(
    builtin_payload: dict[str, Any],
    *,
    user_payload: dict[str, Any] | None,
) -> dict[str, dict[str, str]]:
    merged = dict(
        _parse_instance_metadata(
            builtin_payload,
            source_label=PATCHWORKS_BUILTIN_VARIANTS_RESOURCE,
        )
    )
    if user_payload is not None:
        merged.update(
            _parse_instance_metadata(
                user_payload,
                source_label="user Patchworks registry",
            )
        )
    return merged


def _validate_user_registry_payload(
    payload: dict[str, Any],
    *,
    source_label: str,
) -> dict[str, Any]:
    variants = payload.get("variants")
    if variants in (None, ""):
        payload["variants"] = []
    elif not isinstance(variants, list):
        raise PatchworksVariantRegistryError(
            f"Patchworks variant registry {source_label} field variants must be a list."
        )

    instances = payload.get("instances")
    if instances in (None, ""):
        payload["instances"] = []
    elif not isinstance(instances, list):
        raise PatchworksVariantRegistryError(
            f"Patchworks variant registry {source_label} field instances must be a list."
        )
    scenario_sets = payload.get("scenario_sets")
    if scenario_sets in (None, ""):
        payload["scenario_sets"] = []
    elif not isinstance(scenario_sets, list):
        raise PatchworksVariantRegistryError(
            f"Patchworks variant registry {source_label} field scenario_sets must be a list."
        )
    return payload


def _parse_scenario_set_entries(
    payload: dict[str, Any],
    *,
    source_label: str,
) -> tuple[PatchworksScenarioSetDefinition, ...]:
    scenario_sets_payload = payload.get("scenario_sets", ())
    if scenario_sets_payload in (None, ""):
        return ()
    if not isinstance(scenario_sets_payload, (list, tuple)):
        raise PatchworksVariantRegistryError(
            f"Patchworks variant registry {source_label} field scenario_sets must be a list."
        )

    scenario_sets: list[PatchworksScenarioSetDefinition] = []
    for item in scenario_sets_payload:
        if not isinstance(item, dict):
            raise PatchworksVariantRegistryError(
                f"Patchworks variant registry {source_label} scenario-set items must be mappings."
            )
        scenario_set_id = _as_str(
            item.get("scenario_set_id"),
            "scenario_set_id",
            source_label=source_label,
        )
        label = str(item.get("label") or scenario_set_id).strip() or scenario_set_id
        mode = str(item.get("mode") or "sequential").strip() or "sequential"
        instance_id = str(item.get("instance_id") or "").strip() or None
        scenario_set_family = str(item.get("scenario_set_family") or "").strip() or None
        default = bool(item.get("default", False))
        notes_payload = item.get("notes", ())
        if notes_payload in (None, ""):
            notes: tuple[str, ...] = ()
        else:
            if not isinstance(notes_payload, (list, tuple)):
                raise PatchworksVariantRegistryError(
                    f"Patchworks variant registry {source_label} field "
                    f"scenario_sets[{scenario_set_id}].notes must be a list."
                )
            notes = tuple(
                str(note).strip() for note in notes_payload if str(note).strip()
            )
        members_payload = item.get("scenarios", ())
        if not isinstance(members_payload, (list, tuple)) or not members_payload:
            raise PatchworksVariantRegistryError(
                f"Patchworks variant registry {source_label} scenario set "
                f"{scenario_set_id} must define a non-empty scenarios list."
            )
        members: list[PatchworksScenarioSetMember] = []
        for member in members_payload:
            if isinstance(member, str):
                text = member.strip()
                if "/" not in text:
                    raise PatchworksVariantRegistryError(
                        f"Patchworks variant registry {source_label} scenario set "
                        f"{scenario_set_id} member must look like variant/scenario."
                    )
                variant_id, scenario_id = text.split("/", 1)
                members.append(
                    PatchworksScenarioSetMember(
                        variant_id=variant_id.strip(),
                        scenario_id=scenario_id.strip(),
                    )
                )
                continue
            if not isinstance(member, dict):
                raise PatchworksVariantRegistryError(
                    f"Patchworks variant registry {source_label} scenario set "
                    f"{scenario_set_id} members must be strings or mappings."
                )
            members.append(
                PatchworksScenarioSetMember(
                    variant_id=_as_str(
                        member.get("variant_id"),
                        "scenario_sets[].variant_id",
                        source_label=source_label,
                    ),
                    scenario_id=_as_str(
                        member.get("scenario_id"),
                        "scenario_sets[].scenario_id",
                        source_label=source_label,
                    ),
                )
            )
        scenario_sets.append(
            PatchworksScenarioSetDefinition(
                scenario_set_id=scenario_set_id,
                label=label,
                mode=mode,
                instance_id=instance_id,
                scenario_set_family=scenario_set_family,
                default=default,
                notes=notes,
                scenarios=tuple(members),
            )
        )
    return tuple(scenario_sets)


def _merge_scenario_sets(
    builtin_payload: dict[str, Any],
    *,
    user_payload: dict[str, Any] | None,
) -> tuple[PatchworksScenarioSetDefinition, ...]:
    merged_by_id: dict[str, PatchworksScenarioSetDefinition] = {
        item.scenario_set_id: item
        for item in _parse_scenario_set_entries(
            builtin_payload,
            source_label=PATCHWORKS_BUILTIN_VARIANTS_RESOURCE,
        )
    }
    if user_payload is not None:
        for item in _parse_scenario_set_entries(
            user_payload,
            source_label="user Patchworks registry",
        ):
            merged_by_id[item.scenario_set_id] = item
    return tuple(sorted(merged_by_id.values(), key=lambda item: item.scenario_set_id))


def load_patchworks_user_registry_overlay(
    user_registry_path: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Load the writable user overlay registry payload, creating an empty view if missing."""

    resolved_path = resolve_patchworks_user_registry_path(user_registry_path)
    if resolved_path.exists():
        payload = _validate_user_registry_payload(
            _load_yaml_payload(
                resolved_path.read_text(encoding="utf-8"),
                source_label=str(resolved_path),
            ),
            source_label=str(resolved_path),
        )
    else:
        payload = {"instances": [], "variants": []}
    return resolved_path, payload


def write_patchworks_user_registry_overlay(
    registry_path: Path,
    payload: dict[str, Any],
) -> None:
    """Persist the user overlay registry YAML to disk."""

    normalized_payload = _validate_user_registry_payload(
        dict(payload),
        source_label=str(registry_path),
    )
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        yaml.safe_dump(
            normalized_payload,
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )


def serialize_patchworks_variant_definition(
    variant: PatchworksVariantDefinition,
) -> dict[str, Any]:
    """Convert one resolved variant definition back into writable YAML payload form."""

    payload: dict[str, Any] = {
        "variant_id": variant.variant_id,
        "label": variant.label,
        "instance_id": variant.instance_id,
        "variant_family": variant.variant_family,
        "kind": variant.kind,
        "instance_root": str(variant.instance_root),
        "analysis_pin": str(variant.analysis_pin),
        "runtime_config": str(variant.runtime_config),
    }
    if variant.default:
        payload["default"] = True
    if variant.default_scenario_id:
        payload["default_scenario_id"] = variant.default_scenario_id
    if variant.notes:
        payload["notes"] = list(variant.notes)
    if variant.materialization:
        payload["materialization"] = [
            {
                "kind": action.kind,
                **(
                    {"dataset_root": action.dataset_root}
                    if action.dataset_root is not None
                    else {}
                ),
                **({"relpaths": list(action.relpaths)} if action.relpaths else {}),
                **(
                    {"estimated_bytes": action.estimated_bytes}
                    if action.estimated_bytes is not None
                    else {}
                ),
            }
            for action in variant.materialization
        ]
    if variant.scenarios:
        payload["scenarios"] = [
            {
                "scenario_id": scenario.scenario_id,
                "label": scenario.label,
                "mode": scenario.mode,
                **({"target": scenario.target} if scenario.target is not None else {}),
                **(
                    {"min_annual": scenario.min_annual}
                    if scenario.min_annual is not None
                    else {}
                ),
                **(
                    {"iterations": scenario.iterations}
                    if scenario.iterations is not None
                    else {}
                ),
                **(
                    {"improvement": scenario.improvement}
                    if scenario.improvement is not None
                    else {}
                ),
                **(
                    {"stage_label": scenario.stage_label}
                    if scenario.stage_label is not None
                    else {}
                ),
            }
            for scenario in variant.scenarios
        ]
    if variant.runtime:
        payload["runtime"] = dict(variant.runtime)
    return payload


def _upsert_instance_label(
    payload: dict[str, Any],
    *,
    instance_id: str,
    instance_label: str | None,
) -> None:
    if not instance_label:
        return
    instances = payload.setdefault("instances", [])
    for item in instances:
        if str(item.get("instance_id") or "").strip() == instance_id:
            item["label"] = instance_label
            return
    instances.append({"instance_id": instance_id, "label": instance_label})


def upsert_patchworks_user_variant_entry(
    variant_entry: dict[str, Any],
    *,
    user_registry_path: Path | None = None,
    instance_label: str | None = None,
) -> Path:
    """Insert or replace one variant entry in the writable user overlay registry."""

    registry_path, payload = load_patchworks_user_registry_overlay(user_registry_path)
    normalized_variant_id = _normalize_variant_id(
        str(variant_entry.get("variant_id") or "")
    )
    variants = payload.setdefault("variants", [])
    for index, item in enumerate(variants):
        if str(item.get("variant_id") or "").strip() == normalized_variant_id:
            variants[index] = variant_entry
            _upsert_instance_label(
                payload,
                instance_id=str(variant_entry["instance_id"]),
                instance_label=instance_label,
            )
            write_patchworks_user_registry_overlay(registry_path, payload)
            return registry_path
    variants.append(variant_entry)
    _upsert_instance_label(
        payload,
        instance_id=str(variant_entry["instance_id"]),
        instance_label=instance_label,
    )
    write_patchworks_user_registry_overlay(registry_path, payload)
    return registry_path


def remove_patchworks_user_variant_entry(
    variant_id: str,
    *,
    user_registry_path: Path | None = None,
) -> Path:
    """Remove one variant entry from the writable user overlay registry."""

    normalized_variant_id = _normalize_variant_id(variant_id)
    registry_path, payload = load_patchworks_user_registry_overlay(user_registry_path)
    variants = payload.setdefault("variants", [])
    retained = [
        item
        for item in variants
        if str(item.get("variant_id") or "").strip() != normalized_variant_id
    ]
    if len(retained) == len(variants):
        raise PatchworksVariantRegistryError(
            f"Patchworks user registry does not define variant: {normalized_variant_id}"
        )
    payload["variants"] = retained
    write_patchworks_user_registry_overlay(registry_path, payload)
    return registry_path


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
    user_payload: dict[str, Any] | None = None
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
        instances=_build_instance_definitions(
            variants,
            _merge_instance_metadata(
                builtin_payload,
                user_payload=user_payload,
            ),
        ),
        scenario_sets=_merge_scenario_sets(
            builtin_payload,
            user_payload=user_payload,
        ),
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


def summarize_patchworks_variant_materialization_by_dataset(
    variant: PatchworksVariantDefinition,
) -> tuple[PatchworksVariantMaterializationDatasetSummary, ...]:
    """Group registry-declared materialization actions by dataset root."""

    grouped: dict[str, dict[str, Any]] = {}
    for action in variant.materialization:
        dataset_root = action.dataset_root or "<missing>"
        bucket = grouped.setdefault(
            dataset_root,
            {
                "action_count": 0,
                "known_estimated_bytes": 0,
                "has_unknown_sizes": False,
                "relpaths": [],
            },
        )
        bucket["action_count"] += 1
        if action.estimated_bytes is None:
            bucket["has_unknown_sizes"] = True
        else:
            bucket["known_estimated_bytes"] += action.estimated_bytes
        relpath_items = list(action.relpaths) if action.relpaths else ["."]
        for relpath in relpath_items:
            if relpath not in bucket["relpaths"]:
                bucket["relpaths"].append(relpath)

    return tuple(
        PatchworksVariantMaterializationDatasetSummary(
            dataset_root=dataset_root,
            action_count=int(payload["action_count"]),
            known_estimated_bytes=int(payload["known_estimated_bytes"]),
            has_unknown_sizes=bool(payload["has_unknown_sizes"]),
            relpaths=tuple(str(item) for item in payload["relpaths"]),
        )
        for dataset_root, payload in sorted(grouped.items())
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
