"""Named-pipeline registry, runbook, and proof-runner helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module, resources
import json
from pathlib import Path
from typing import Any, Callable, Mapping, cast

import yaml

from femic.glb import build_tsa_raw_glb
from femic.tsr_catalog import (
    TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
    TsrThlbParentStepRunResult,
    TsrThlbNetdownRecipeRunResult,
    default_tsr_thlb_netdown_recipe_path,
    load_tsr_thlb_netdown_recipe,
    run_tsr_thlb_parent_step,
    run_tsr_thlb_netdown_recipe,
)
from femic.user_config import DEFAULT_FEMIC_CONFIG_HOME


PIPELINE_REGISTRY_RESOURCE_PACKAGE = "femic.resources.pipelines"
PIPELINE_REGISTRY_RESOURCE_NAME = "registry.yaml"
_SUPPORTED_TSR_THLB_PIPELINE_IDS = {"tsr.thlb_strict", "tsr.thlb_reviewed"}
DEFAULT_NAMED_PIPELINE_USER_REGISTRY_PATH = DEFAULT_FEMIC_CONFIG_HOME / "pipelines.yaml"
DEFAULT_NAMED_PIPELINE_INSTANCE_REGISTRY_RELATIVE_PATH = Path("config/pipelines.yaml")
_PIPELINE_REGISTRY_ALLOWED_KEYS = {"schema_version", "registry_kind", "pipelines"}
_PIPELINE_RUNBOOK_ALLOWED_KEYS = {
    "schema_version",
    "runbook_kind",
    "label",
    "pipeline_id",
    "instance_root",
    "run_profile",
    "registry_paths",
    "overlay_paths",
    "parameter_files",
    "restart",
    "validation_contract",
    "target_parent_step_id",
    "notes",
}


class NamedPipelineError(RuntimeError):
    """Raised when a named-pipeline registry or runbook is invalid."""


@dataclass(frozen=True)
class NamedPipelineRecipe:
    """One named-pipeline recipe entry."""

    recipe_id: str
    recipe_kind: str
    default_recipe_path: Path | None = None
    default_config_path: Path | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class NamedPipelineSeam:
    """One named restart seam for a pipeline."""

    seam_id: str
    start_mode: str = "checkpoint"
    checkpoint_path: Path | None = None
    stage_label: str | None = None
    baseline_signal: str | None = None
    checkpoint_kind: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class NamedPipelineDefinition:
    """Resolved definition for one named pipeline."""

    pipeline_id: str
    label: str
    kind: str
    summary: str
    recipes: tuple[NamedPipelineRecipe, ...]
    seams: tuple[NamedPipelineSeam, ...]
    default_instance_runbook: Path | None = None
    source_kind: str = "builtin"
    registry_path: Path | None = None

    def get_seam(self, seam_id: str) -> NamedPipelineSeam:
        normalized = seam_id.strip()
        for seam in self.seams:
            if seam.seam_id == normalized:
                return seam
        raise NamedPipelineError(
            f"Named pipeline `{self.pipeline_id}` does not define seam `{normalized}`."
        )

    def get_recipe(self, recipe_kind: str) -> NamedPipelineRecipe:
        for recipe in self.recipes:
            if recipe.recipe_kind == recipe_kind:
                return recipe
        raise NamedPipelineError(
            f"Named pipeline `{self.pipeline_id}` does not define recipe kind "
            f"`{recipe_kind}`."
        )


@dataclass(frozen=True)
class NamedPipelineRegistry:
    """Merged named-pipeline registry."""

    pipelines: tuple[NamedPipelineDefinition, ...]
    builtin_registry_loaded: bool
    user_registry_path: Path | None
    instance_registry_path: Path | None
    explicit_registry_paths: tuple[Path, ...]

    def get_pipeline(self, pipeline_id: str) -> NamedPipelineDefinition:
        normalized = pipeline_id.strip()
        for pipeline in self.pipelines:
            if pipeline.pipeline_id == normalized:
                return pipeline
        raise NamedPipelineError(f"Named pipeline not found: {normalized}")


@dataclass(frozen=True)
class NamedPipelineRestart:
    """Resolved restart selection from a pipeline runbook."""

    seam_id: str
    checkpoint_path: Path | None = None
    policy: str | None = None


@dataclass(frozen=True)
class NamedPipelineValidationContract:
    """Resolved validation contract for one named-pipeline runbook."""

    contract_kind: str
    locked_chain_ledger_path: Path | None = None
    comparison_report_path: Path | None = None
    required_recipe_path: Path | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class NamedPipelineRunbook:
    """Machine-readable pipeline runbook."""

    path: Path
    label: str
    pipeline_id: str
    instance_root: Path
    run_profile: Path | None
    registry_paths: tuple[Path, ...]
    overlay_paths: tuple[Path, ...]
    parameter_files: tuple[Path, ...]
    restart: NamedPipelineRestart
    validation_contract: NamedPipelineValidationContract | None = None
    target_parent_step_id: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class NamedPipelineExecutionPlan:
    """Resolved execution plan for one named pipeline runbook."""

    runbook_path: Path
    instance_root: Path
    pipeline_id: str
    pipeline_label: str
    seam_id: str
    checkpoint_path: Path | None
    run_profile_path: Path | None
    overlay_paths: tuple[Path, ...]
    parameter_files: tuple[Path, ...]
    validation_contract: NamedPipelineValidationContract | None
    user_registry_path: Path | None
    instance_registry_path: Path | None
    explicit_registry_paths: tuple[Path, ...]
    thlb_netdown_recipe_path: Path
    source_layers_recipe_path: Path
    execution_mode: str
    target_parent_step_id: str | None = None


@dataclass(frozen=True)
class NamedPipelineValidationResult:
    """Validation summary for one named-pipeline execution."""

    contract_kind: str
    validated_parent_step_count: int
    latest_locked_row_order: int | None = None
    latest_locked_parent_step_id: str | None = None
    expected_final_managed_area_ha: float | None = None
    actual_final_managed_area_ha: float | None = None
    max_abs_marginal_delta_ha: float | None = None
    max_abs_cumulative_delta_ha: float | None = None


@dataclass(frozen=True)
class NamedPipelineExecutionResult:
    """Result of running one named-pipeline proof surface."""

    plan: NamedPipelineExecutionPlan
    tsr_thlb_result: TsrThlbNetdownRecipeRunResult | None
    tsr_parent_step_result: TsrThlbParentStepRunResult | None = None
    validation_result: NamedPipelineValidationResult | None = None
    runtime_event_log_path: Path | None = None


_RUNTIME_EVENT_CORE_FIELDS = (
    "event_kind",
    "timestamp_utc",
    "pipeline_id",
    "runbook_path",
    "instance_root",
    "execution_mode",
    "seam_id",
    "recipe_path",
    "checkpoint_path",
)
_RUNTIME_EVENT_IMPORTANT_FIELDS = (
    "validation_contract_kind",
    "locked_chain_ledger_path",
    "required_recipe_path",
    "locked_row_order",
    "locked_parent_step_id",
    "expected_benchmark_area_ha",
    "actual_start_area_ha",
    "area_delta_ha",
    "summary_json_path",
    "summary_markdown_path",
    "parent_step_id",
    "parent_label",
    "row_order",
    "land_base_stage",
    "compiled_step_id",
    "compiled_step_label",
    "run_status",
    "remaining_area_ha",
    "completed_lus",
    "total_lus",
    "fraction_complete",
    "current_lu",
    "bundle_label",
    "bundle_status",
    "validated_parent_step_count",
    "latest_locked_row_order",
    "latest_locked_parent_step_id",
    "expected_final_managed_area_ha",
    "actual_final_managed_area_ha",
    "error",
    "notes",
)


def default_named_pipeline_runtime_event_log_path(
    *, instance_root: Path, pipeline_id: str
) -> Path:
    """Return the default runtime event log path for one named-pipeline run."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = pipeline_id.strip().replace(".", "_") or "pipeline"
    return (
        instance_root
        / "runtime"
        / "logs"
        / "tsr"
        / f"named_pipeline_events-{slug}-{timestamp}.log"
    )


def _normalize_runtime_event_value(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, (list, tuple)):
        return json.dumps(
            [_normalize_runtime_event_value(item) for item in value],
            sort_keys=False,
        )
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


def format_named_pipeline_runtime_event_line(event: Mapping[str, Any]) -> str:
    """Format one named-pipeline runtime event as stable key=value text."""

    ordered_keys: list[str] = []
    for key in (*_RUNTIME_EVENT_CORE_FIELDS, *_RUNTIME_EVENT_IMPORTANT_FIELDS):
        if key in event and key not in ordered_keys:
            ordered_keys.append(key)
    for key in sorted(event):
        if key not in ordered_keys:
            ordered_keys.append(key)
    parts: list[str] = []
    for key in ordered_keys:
        value = event.get(key)
        if value in (None, "", (), [], {}):
            continue
        normalized = _normalize_runtime_event_value(value)
        if any(char.isspace() for char in normalized) or any(
            char in normalized for char in ['"', "=", "[", "]", "{", "}"]
        ):
            normalized = json.dumps(normalized)
        parts.append(f"{key}={normalized}")
    return " ".join(parts)


class _NamedPipelineRuntimeEventLogger:
    """Mirror runtime events to disk and optionally to a user-visible sink."""

    def __init__(
        self,
        *,
        log_path: Path,
        default_fields: Mapping[str, Any],
        line_sink: Callable[[str], None] | None = None,
    ) -> None:
        self.log_path = log_path
        self.default_fields = dict(default_fields)
        self.line_sink = line_sink
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, payload: Mapping[str, Any]) -> None:
        event = dict(self.default_fields)
        event.update(payload)
        event["timestamp_utc"] = datetime.now(UTC).isoformat()
        line = format_named_pipeline_runtime_event_line(event)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        if self.line_sink is not None:
            self.line_sink(line)


def _read_pipeline_resource_text(resource_name: str) -> str:
    return (
        resources.files(PIPELINE_REGISTRY_RESOURCE_PACKAGE)
        .joinpath(resource_name)
        .read_text(encoding="utf-8")
    )


def _load_yaml_mapping(*, text: str, source_label: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise NamedPipelineError(f"Invalid YAML in {source_label}: {exc}") from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise NamedPipelineError(f"{source_label} must be a mapping.")
    return cast(dict[str, Any], payload)


def _load_json_mapping(*, path: Path, source_label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NamedPipelineError(f"Invalid JSON in {source_label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise NamedPipelineError(f"{source_label} must be a mapping.")
    return cast(dict[str, Any], payload)


def _normalize_string(value: Any, *, field_name: str, source_label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise NamedPipelineError(f"{source_label} field `{field_name}` is required.")
    return normalized


def _normalize_optional_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value))


def _normalize_float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise NamedPipelineError(f"Expected float-compatible value, got {value!r}.") from exc


def _normalize_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NamedPipelineError(f"Expected int-compatible value, got {value!r}.") from exc


def _normalize_string_tuple(
    value: Any, *, field_name: str, source_label: str
) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise NamedPipelineError(f"{source_label} field `{field_name}` must be a list.")
    return tuple(str(item).strip() for item in value if str(item).strip())


def _normalize_path_tuple(
    value: Any, *, field_name: str, source_label: str
) -> tuple[Path, ...]:
    return tuple(
        Path(item)
        for item in _normalize_string_tuple(
            value, field_name=field_name, source_label=source_label
        )
    )


def _parse_pipeline_recipe(
    payload: dict[str, Any], *, source_label: str
) -> NamedPipelineRecipe:
    return NamedPipelineRecipe(
        recipe_id=_normalize_string(
            payload.get("recipe_id"), field_name="recipe_id", source_label=source_label
        ),
        recipe_kind=_normalize_string(
            payload.get("recipe_kind"),
            field_name="recipe_kind",
            source_label=source_label,
        ),
        default_recipe_path=_normalize_optional_path(
            payload.get("default_recipe_path")
        ),
        default_config_path=_normalize_optional_path(
            payload.get("default_config_path")
        ),
        notes=_normalize_string_tuple(
            payload.get("notes"), field_name="notes", source_label=source_label
        ),
    )


def _parse_pipeline_seam(
    payload: dict[str, Any], *, source_label: str
) -> NamedPipelineSeam:
    seam_id = _normalize_string(
        payload.get("seam_id"), field_name="seam_id", source_label=source_label
    )
    start_mode = str(payload.get("start_mode") or "checkpoint").strip()
    checkpoint_path = _normalize_optional_path(payload.get("checkpoint_path"))
    if start_mode == "scratch":
        checkpoint_path = None
    elif checkpoint_path is None:
        raise NamedPipelineError(
            f"{source_label} seam `{seam_id}` must define `checkpoint_path` unless "
            "`start_mode: scratch` is used."
        )
    return NamedPipelineSeam(
        seam_id=seam_id,
        start_mode=start_mode,
        checkpoint_path=checkpoint_path,
        stage_label=(
            str(payload.get("stage_label")).strip()
            if payload.get("stage_label") not in (None, "")
            else None
        ),
        baseline_signal=(
            str(payload.get("baseline_signal")).strip()
            if payload.get("baseline_signal") not in (None, "")
            else None
        ),
        checkpoint_kind=(
            str(payload.get("checkpoint_kind")).strip()
            if payload.get("checkpoint_kind") not in (None, "")
            else None
        ),
        notes=_normalize_string_tuple(
            payload.get("notes"), field_name="notes", source_label=source_label
        ),
    )


def _parse_pipeline_definition(
    payload: dict[str, Any],
    *,
    source_label: str,
    source_kind: str,
    registry_path: Path | None,
) -> NamedPipelineDefinition:
    recipes_payload = payload.get("recipes")
    if not isinstance(recipes_payload, list) or not recipes_payload:
        raise NamedPipelineError(
            f"{source_label} field `recipes` must be a non-empty list."
        )
    seams_payload = payload.get("seams")
    if not isinstance(seams_payload, list) or not seams_payload:
        raise NamedPipelineError(
            f"{source_label} field `seams` must be a non-empty list."
        )
    return NamedPipelineDefinition(
        pipeline_id=_normalize_string(
            payload.get("pipeline_id"),
            field_name="pipeline_id",
            source_label=source_label,
        ),
        label=_normalize_string(
            payload.get("label"), field_name="label", source_label=source_label
        ),
        kind=_normalize_string(
            payload.get("kind"), field_name="kind", source_label=source_label
        ),
        summary=_normalize_string(
            payload.get("summary"), field_name="summary", source_label=source_label
        ),
        recipes=tuple(
            _parse_pipeline_recipe(item, source_label=source_label)
            for item in recipes_payload
            if isinstance(item, dict)
        ),
        seams=tuple(
            _parse_pipeline_seam(item, source_label=source_label)
            for item in seams_payload
            if isinstance(item, dict)
        ),
        default_instance_runbook=_normalize_optional_path(
            payload.get("default_instance_runbook")
        ),
        source_kind=source_kind,
        registry_path=registry_path,
    )


def _load_pipeline_entries_from_payload(
    payload: dict[str, Any],
    *,
    source_label: str,
    source_kind: str,
    registry_path: Path | None,
) -> tuple[NamedPipelineDefinition, ...]:
    unknown_keys = sorted(set(payload) - _PIPELINE_REGISTRY_ALLOWED_KEYS)
    if unknown_keys:
        raise NamedPipelineError(
            f"{source_label} contains unsupported top-level keys: {', '.join(unknown_keys)}"
        )
    if payload.get("registry_kind") != "pipeline_registry":
        raise NamedPipelineError(
            f"{source_label} field `registry_kind` must equal `pipeline_registry`."
        )
    pipelines_payload = payload.get("pipelines")
    if not isinstance(pipelines_payload, list):
        raise NamedPipelineError(f"{source_label} field `pipelines` must be a list.")
    parsed = tuple(
        _parse_pipeline_definition(
            item,
            source_label=source_label,
            source_kind=source_kind,
            registry_path=registry_path,
        )
        for item in pipelines_payload
        if isinstance(item, dict)
    )
    seen: set[str] = set()
    for item in parsed:
        if item.pipeline_id in seen:
            raise NamedPipelineError(
                f"{source_label} defines duplicate pipeline_id `{item.pipeline_id}`."
            )
        seen.add(item.pipeline_id)
    return parsed


def _load_pipeline_payload_from_path(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise NamedPipelineError(f"Named pipeline registry not found: {resolved}")
    return _load_yaml_mapping(
        text=resolved.read_text(encoding="utf-8"),
        source_label=str(resolved),
    )


def load_named_pipeline_registry(
    *,
    instance_root: Path | None = None,
    explicit_registry_paths: tuple[Path, ...] = (),
    user_registry_path: Path | None = None,
) -> NamedPipelineRegistry:
    """Load the merged built-in, user, instance, and explicit registries."""

    builtin_payload = _load_yaml_mapping(
        text=_read_pipeline_resource_text(PIPELINE_REGISTRY_RESOURCE_NAME),
        source_label=PIPELINE_REGISTRY_RESOURCE_NAME,
    )
    merged_by_id: dict[str, NamedPipelineDefinition] = {
        item.pipeline_id: item
        for item in _load_pipeline_entries_from_payload(
            builtin_payload,
            source_label=PIPELINE_REGISTRY_RESOURCE_NAME,
            source_kind="builtin",
            registry_path=None,
        )
    }

    effective_user_registry = (
        user_registry_path.expanduser().resolve()
        if user_registry_path is not None
        else DEFAULT_NAMED_PIPELINE_USER_REGISTRY_PATH.expanduser().resolve()
    )
    user_path_result: Path | None = None
    if effective_user_registry.exists():
        user_payload = _load_pipeline_payload_from_path(effective_user_registry)
        for item in _load_pipeline_entries_from_payload(
            user_payload,
            source_label=str(effective_user_registry),
            source_kind="user",
            registry_path=effective_user_registry,
        ):
            merged_by_id[item.pipeline_id] = item
        user_path_result = effective_user_registry

    instance_path_result: Path | None = None
    if instance_root is not None:
        effective_instance_registry = (
            instance_root.expanduser().resolve()
            / DEFAULT_NAMED_PIPELINE_INSTANCE_REGISTRY_RELATIVE_PATH
        )
        if effective_instance_registry.exists():
            instance_payload = _load_pipeline_payload_from_path(
                effective_instance_registry
            )
            for item in _load_pipeline_entries_from_payload(
                instance_payload,
                source_label=str(effective_instance_registry),
                source_kind="instance",
                registry_path=effective_instance_registry,
            ):
                merged_by_id[item.pipeline_id] = item
            instance_path_result = effective_instance_registry

    loaded_explicit_paths: list[Path] = []
    seen_explicit: set[Path] = set()
    for path in explicit_registry_paths:
        resolved = path.expanduser().resolve()
        if resolved in seen_explicit:
            continue
        explicit_payload = _load_pipeline_payload_from_path(resolved)
        for item in _load_pipeline_entries_from_payload(
            explicit_payload,
            source_label=str(resolved),
            source_kind="explicit",
            registry_path=resolved,
        ):
            merged_by_id[item.pipeline_id] = item
        loaded_explicit_paths.append(resolved)
        seen_explicit.add(resolved)

    return NamedPipelineRegistry(
        pipelines=tuple(
            sorted(merged_by_id.values(), key=lambda item: item.pipeline_id)
        ),
        builtin_registry_loaded=True,
        user_registry_path=user_path_result,
        instance_registry_path=instance_path_result,
        explicit_registry_paths=tuple(loaded_explicit_paths),
    )


def _infer_runbook_instance_root(runbook_path: Path) -> Path:
    resolved = runbook_path.expanduser().resolve()
    for candidate in (resolved.parent,) + tuple(resolved.parents):
        if (candidate / "config").exists() and (candidate / "data").exists():
            return candidate
    raise NamedPipelineError(
        f"Could not infer instance root from runbook path: {resolved}"
    )


def _resolve_relative_to_instance(
    instance_root: Path, value: Path | None
) -> Path | None:
    if value is None:
        return None
    if value.is_absolute():
        return value.expanduser().resolve()
    return (instance_root / value).resolve()


def load_named_pipeline_runbook(
    *,
    runbook_path: Path,
    instance_root: Path | None = None,
) -> NamedPipelineRunbook:
    """Load and resolve one machine-readable named-pipeline runbook."""

    resolved_runbook_path = runbook_path.expanduser().resolve()
    if not resolved_runbook_path.exists():
        raise NamedPipelineError(f"Pipeline runbook not found: {resolved_runbook_path}")
    payload = _load_yaml_mapping(
        text=resolved_runbook_path.read_text(encoding="utf-8"),
        source_label=str(resolved_runbook_path),
    )
    unknown_keys = sorted(set(payload) - _PIPELINE_RUNBOOK_ALLOWED_KEYS)
    if unknown_keys:
        raise NamedPipelineError(
            f"{resolved_runbook_path} contains unsupported top-level keys: "
            + ", ".join(unknown_keys)
        )
    if payload.get("runbook_kind") != "femic_pipeline_runbook":
        raise NamedPipelineError(
            f"{resolved_runbook_path} field `runbook_kind` must equal "
            "`femic_pipeline_runbook`."
        )

    base_instance_root = (
        instance_root.expanduser().resolve()
        if instance_root is not None
        else _infer_runbook_instance_root(resolved_runbook_path)
    )
    instance_root_value = _normalize_optional_path(payload.get("instance_root"))
    resolved_instance_root = (
        base_instance_root
        if instance_root_value is None
        else _resolve_relative_to_instance(base_instance_root, instance_root_value)
    )
    assert resolved_instance_root is not None

    restart_payload = payload.get("restart")
    if not isinstance(restart_payload, dict):
        raise NamedPipelineError(
            f"{resolved_runbook_path} field `restart` must be a mapping."
        )
    restart = NamedPipelineRestart(
        seam_id=_normalize_string(
            restart_payload.get("seam_id"),
            field_name="restart.seam_id",
            source_label=str(resolved_runbook_path),
        ),
        checkpoint_path=_resolve_relative_to_instance(
            resolved_instance_root,
            _normalize_optional_path(restart_payload.get("checkpoint_path")),
        ),
        policy=(
            str(restart_payload.get("policy")).strip()
            if restart_payload.get("policy") not in (None, "")
            else None
        ),
    )

    validation_contract_payload = payload.get("validation_contract")
    validation_contract: NamedPipelineValidationContract | None = None
    if validation_contract_payload not in (None, ""):
        if not isinstance(validation_contract_payload, dict):
            raise NamedPipelineError(
                f"{resolved_runbook_path} field `validation_contract` must be a mapping."
            )
        validation_contract = NamedPipelineValidationContract(
            contract_kind=_normalize_string(
                validation_contract_payload.get("contract_kind"),
                field_name="validation_contract.contract_kind",
                source_label=str(resolved_runbook_path),
            ),
            locked_chain_ledger_path=_resolve_relative_to_instance(
                resolved_instance_root,
                _normalize_optional_path(
                    validation_contract_payload.get("locked_chain_ledger_path")
                ),
            ),
            comparison_report_path=_resolve_relative_to_instance(
                resolved_instance_root,
                _normalize_optional_path(
                    validation_contract_payload.get("comparison_report_path")
                ),
            ),
            required_recipe_path=_resolve_relative_to_instance(
                resolved_instance_root,
                _normalize_optional_path(
                    validation_contract_payload.get("required_recipe_path")
                ),
            ),
            notes=_normalize_string_tuple(
                validation_contract_payload.get("notes"),
                field_name="validation_contract.notes",
                source_label=str(resolved_runbook_path),
            ),
        )

    return NamedPipelineRunbook(
        path=resolved_runbook_path,
        label=_normalize_string(
            payload.get("label"),
            field_name="label",
            source_label=str(resolved_runbook_path),
        ),
        pipeline_id=_normalize_string(
            payload.get("pipeline_id"),
            field_name="pipeline_id",
            source_label=str(resolved_runbook_path),
        ),
        instance_root=resolved_instance_root,
        run_profile=_resolve_relative_to_instance(
            resolved_instance_root, _normalize_optional_path(payload.get("run_profile"))
        ),
        registry_paths=tuple(
            filter(
                None,
                (
                    _resolve_relative_to_instance(resolved_instance_root, path)
                    for path in _normalize_path_tuple(
                        payload.get("registry_paths"),
                        field_name="registry_paths",
                        source_label=str(resolved_runbook_path),
                    )
                ),
            )
        ),
        overlay_paths=tuple(
            filter(
                None,
                (
                    _resolve_relative_to_instance(resolved_instance_root, path)
                    for path in _normalize_path_tuple(
                        payload.get("overlay_paths"),
                        field_name="overlay_paths",
                        source_label=str(resolved_runbook_path),
                    )
                ),
            )
        ),
        parameter_files=tuple(
            filter(
                None,
                (
                    _resolve_relative_to_instance(resolved_instance_root, path)
                    for path in _normalize_path_tuple(
                        payload.get("parameter_files"),
                        field_name="parameter_files",
                        source_label=str(resolved_runbook_path),
                    )
                ),
            )
        ),
        restart=restart,
        validation_contract=validation_contract,
        target_parent_step_id=(
            _normalize_string(
                payload.get("target_parent_step_id"),
                field_name="target_parent_step_id",
                source_label=str(resolved_runbook_path),
            )
            if payload.get("target_parent_step_id") not in (None, "")
            else None
        ),
        notes=_normalize_string_tuple(
            payload.get("notes"),
            field_name="notes",
            source_label=str(resolved_runbook_path),
        ),
    )


def build_named_pipeline_execution_plan(
    *,
    runbook_path: Path,
    instance_root: Path | None = None,
) -> NamedPipelineExecutionPlan:
    """Resolve one runbook into a concrete proof-runner execution plan."""

    runbook = load_named_pipeline_runbook(
        runbook_path=runbook_path,
        instance_root=instance_root,
    )
    registry = load_named_pipeline_registry(
        instance_root=runbook.instance_root,
        explicit_registry_paths=runbook.registry_paths,
    )
    pipeline = registry.get_pipeline(runbook.pipeline_id)
    seam = pipeline.get_seam(runbook.restart.seam_id)
    checkpoint_path = runbook.restart.checkpoint_path
    if seam.start_mode == "scratch":
        checkpoint_path = None
    elif checkpoint_path is None and seam.checkpoint_path is not None:
        checkpoint_path = _resolve_relative_to_instance(
            runbook.instance_root, seam.checkpoint_path
        )
    if checkpoint_path is not None and not checkpoint_path.exists():
        raise NamedPipelineError(
            f"Resolved checkpoint path not found: {checkpoint_path}"
        )
    if runbook.run_profile is not None and not runbook.run_profile.exists():
        raise NamedPipelineError(
            f"Resolved run profile not found: {runbook.run_profile}"
        )
    for overlay_path in runbook.overlay_paths:
        if not overlay_path.exists():
            raise NamedPipelineError(f"Resolved overlay path not found: {overlay_path}")
    if runbook.validation_contract is not None:
        if runbook.validation_contract.locked_chain_ledger_path is not None and (
            not runbook.validation_contract.locked_chain_ledger_path.exists()
        ):
            raise NamedPipelineError(
                "Resolved locked-chain ledger path not found: "
                f"{runbook.validation_contract.locked_chain_ledger_path}"
            )
        if runbook.validation_contract.comparison_report_path is not None and (
            not runbook.validation_contract.comparison_report_path.exists()
        ):
            raise NamedPipelineError(
                "Resolved strict comparison report path not found: "
                f"{runbook.validation_contract.comparison_report_path}"
            )
        if runbook.validation_contract.required_recipe_path is not None and (
            not runbook.validation_contract.required_recipe_path.exists()
        ):
            raise NamedPipelineError(
                "Resolved required validation recipe path not found: "
                f"{runbook.validation_contract.required_recipe_path}"
            )

    if pipeline.pipeline_id not in _SUPPORTED_TSR_THLB_PIPELINE_IDS:
        raise NamedPipelineError(
            "The first proof runner only supports pipelines "
            "`tsr.thlb_strict` and `tsr.thlb_reviewed`."
        )
    recipe = pipeline.get_recipe("tsr_thlb_netdown")
    thlb_recipe_path = (
        runbook.validation_contract.required_recipe_path
        if (
            runbook.validation_contract is not None
            and runbook.validation_contract.required_recipe_path is not None
        )
        else (
            _resolve_relative_to_instance(runbook.instance_root, recipe.default_recipe_path)
            if recipe.default_recipe_path is not None
            else default_tsr_thlb_netdown_recipe_path(instance_root=runbook.instance_root)
        )
    )
    assert thlb_recipe_path is not None
    if not thlb_recipe_path.exists():
        raise NamedPipelineError(
            f"Resolved THLB recipe path not found: {thlb_recipe_path}"
        )
    thlb_recipe = load_tsr_thlb_netdown_recipe(thlb_recipe_path)
    source_layers_recipe_path = _resolve_relative_to_instance(
        runbook.instance_root,
        Path(thlb_recipe.instance_inputs.source_layer_recipe_path),
    )
    assert source_layers_recipe_path is not None
    if not source_layers_recipe_path.exists():
        raise NamedPipelineError(
            f"Resolved source-layers recipe path not found: {source_layers_recipe_path}"
        )
    return NamedPipelineExecutionPlan(
        runbook_path=runbook.path,
        instance_root=runbook.instance_root,
        pipeline_id=pipeline.pipeline_id,
        pipeline_label=pipeline.label,
        seam_id=seam.seam_id,
        checkpoint_path=checkpoint_path,
        run_profile_path=runbook.run_profile,
        overlay_paths=runbook.overlay_paths,
        parameter_files=runbook.parameter_files,
        validation_contract=runbook.validation_contract,
        target_parent_step_id=runbook.target_parent_step_id,
        user_registry_path=registry.user_registry_path,
        instance_registry_path=registry.instance_registry_path,
        explicit_registry_paths=registry.explicit_registry_paths,
        thlb_netdown_recipe_path=thlb_recipe_path,
        source_layers_recipe_path=source_layers_recipe_path,
        execution_mode=TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
    )


def _validate_tsa29_locked_chain_strict_result(
    *,
    plan: NamedPipelineExecutionPlan,
    tsr_result: TsrThlbNetdownRecipeRunResult,
    tolerance_ha: float = 1e-3,
) -> NamedPipelineValidationResult:
    validation_contract = plan.validation_contract
    if validation_contract is None:
        raise NamedPipelineError("Strict validation contract is required for this validator.")
    if validation_contract.locked_chain_ledger_path is None:
        raise NamedPipelineError(
            "Strict validation contract requires `locked_chain_ledger_path`."
        )
    ledger_payload = _load_json_mapping(
        path=validation_contract.locked_chain_ledger_path,
        source_label=str(validation_contract.locked_chain_ledger_path),
    )
    audit_path = getattr(tsr_result, "audit_path", None)
    if audit_path in (None, ""):
        raise NamedPipelineError(
            "Strict validation contract requires a THLB run result with an `audit_path`."
        )
    resolved_audit_path = Path(str(audit_path)).expanduser().resolve()
    if not resolved_audit_path.exists():
        raise NamedPipelineError(
            f"Resolved strict validation audit path not found: {resolved_audit_path}"
        )
    audit_payload = _load_json_mapping(
        path=resolved_audit_path,
        source_label=str(resolved_audit_path),
    )
    ledger_entries = ledger_payload.get("entries")
    if not isinstance(ledger_entries, list):
        raise NamedPipelineError(
            f"{validation_contract.locked_chain_ledger_path} field `entries` must be a list."
        )
    audit_steps = audit_payload.get("steps")
    if not isinstance(audit_steps, list):
        raise NamedPipelineError(f"{resolved_audit_path} field `steps` must be a list.")

    parent_step_totals: dict[str, dict[str, float | int | str | None]] = {}
    for step in audit_steps:
        if not isinstance(step, dict):
            raise NamedPipelineError(
                f"{resolved_audit_path} field `steps` must contain mappings."
            )
        parent_step_id = str(step.get("parent_step_id", "")).strip()
        if not parent_step_id:
            continue
        entry = parent_step_totals.setdefault(
            parent_step_id,
            {
                "row_order": _normalize_int_or_none(step.get("order_index")),
                "parent_label": str(step.get("parent_label", "")).strip() or None,
                "net_removed_area_ha": 0.0,
                "remaining_area_ha": None,
            },
        )
        net_removed_area_ha = _normalize_float_or_none(
            step.get("net_removed_area_ha", step.get("removed_area_ha"))
        )
        if net_removed_area_ha is not None:
            entry["net_removed_area_ha"] = float(entry["net_removed_area_ha"] or 0.0) + float(
                net_removed_area_ha
            )
        remaining_area_ha = _normalize_float_or_none(step.get("remaining_area_ha"))
        if remaining_area_ha is not None:
            entry["remaining_area_ha"] = remaining_area_ha

    validated_parent_step_count = 0
    max_abs_marginal_delta_ha = 0.0
    max_abs_cumulative_delta_ha = 0.0
    latest_locked_row_order: int | None = None
    latest_locked_parent_step_id: str | None = None
    expected_final_managed_area_ha: float | None = None

    for ledger_entry in ledger_entries:
        if not isinstance(ledger_entry, dict):
            raise NamedPipelineError(
                f"{validation_contract.locked_chain_ledger_path} field `entries` must contain mappings."
            )
        parent_step_id = str(ledger_entry.get("parent_step_id", "")).strip()
        row_order = _normalize_int_or_none(ledger_entry.get("row_order"))
        if not parent_step_id or row_order is None:
            raise NamedPipelineError(
                f"{validation_contract.locked_chain_ledger_path} contains an invalid ledger entry."
            )
        parent_audit = parent_step_totals.get(parent_step_id)
        if parent_audit is None:
            raise NamedPipelineError(
                "Strict validation contract mismatch: missing audited parent step "
                f"`{parent_step_id}` for locked ledger row `{row_order}`."
            )
        expected_net_removed_area_ha = _normalize_float_or_none(
            ledger_entry.get("locked_net_removed_area_ha")
        )
        actual_net_removed_area_ha = _normalize_float_or_none(
            parent_audit.get("net_removed_area_ha")
        )
        expected_marginal_compare = (
            0.0 if expected_net_removed_area_ha is None else expected_net_removed_area_ha
        )
        actual_marginal_compare = (
            0.0 if actual_net_removed_area_ha is None else actual_net_removed_area_ha
        )
        marginal_delta_ha = abs(actual_marginal_compare - expected_marginal_compare)
        max_abs_marginal_delta_ha = max(max_abs_marginal_delta_ha, marginal_delta_ha)
        if marginal_delta_ha > tolerance_ha:
            raise NamedPipelineError(
                "Strict validation contract mismatch at row "
                f"`{row_order}` (`{parent_step_id}`): expected locked marginal "
                f"`{expected_marginal_compare:.3f} ha`, got "
                f"`{actual_marginal_compare:.3f} ha`."
            )
        expected_cumulative_remaining_area_ha = _normalize_float_or_none(
            ledger_entry.get("locked_cumulative_remaining_area_ha")
        )
        actual_cumulative_remaining_area_ha = _normalize_float_or_none(
            parent_audit.get("remaining_area_ha")
        )
        if expected_cumulative_remaining_area_ha is None:
            raise NamedPipelineError(
                "Strict validation contract ledger entry is missing "
                f"`locked_cumulative_remaining_area_ha` for `{parent_step_id}`."
            )
        if actual_cumulative_remaining_area_ha is None:
            raise NamedPipelineError(
                "Strict validation contract mismatch: audited parent step "
                f"`{parent_step_id}` is missing `remaining_area_ha`."
            )
        cumulative_delta_ha = abs(
            actual_cumulative_remaining_area_ha - expected_cumulative_remaining_area_ha
        )
        max_abs_cumulative_delta_ha = max(max_abs_cumulative_delta_ha, cumulative_delta_ha)
        if cumulative_delta_ha > tolerance_ha:
            raise NamedPipelineError(
                "Strict validation contract mismatch at row "
                f"`{row_order}` (`{parent_step_id}`): expected locked cumulative "
                f"`{expected_cumulative_remaining_area_ha:.3f} ha`, got "
                f"`{actual_cumulative_remaining_area_ha:.3f} ha`."
            )
        latest_locked_row_order = row_order
        latest_locked_parent_step_id = parent_step_id
        expected_final_managed_area_ha = expected_cumulative_remaining_area_ha
        validated_parent_step_count += 1

    actual_final_managed_area_ha = _normalize_float_or_none(
        getattr(tsr_result, "final_managed_area_ha", None)
    )
    if expected_final_managed_area_ha is None or actual_final_managed_area_ha is None:
        raise NamedPipelineError(
            "Strict validation contract requires both expected and actual final managed area."
        )
    final_delta_ha = abs(actual_final_managed_area_ha - expected_final_managed_area_ha)
    max_abs_cumulative_delta_ha = max(max_abs_cumulative_delta_ha, final_delta_ha)
    if final_delta_ha > tolerance_ha:
        raise NamedPipelineError(
            "Strict validation contract mismatch at final managed area: expected "
            f"`{expected_final_managed_area_ha:.3f} ha`, got "
            f"`{actual_final_managed_area_ha:.3f} ha`."
        )

    return NamedPipelineValidationResult(
        contract_kind=validation_contract.contract_kind,
        validated_parent_step_count=validated_parent_step_count,
        latest_locked_row_order=latest_locked_row_order,
        latest_locked_parent_step_id=latest_locked_parent_step_id,
        expected_final_managed_area_ha=expected_final_managed_area_ha,
        actual_final_managed_area_ha=actual_final_managed_area_ha,
        max_abs_marginal_delta_ha=max_abs_marginal_delta_ha,
        max_abs_cumulative_delta_ha=max_abs_cumulative_delta_ha,
    )


def _load_locked_chain_entries(
    validation_contract: NamedPipelineValidationContract,
) -> list[Mapping[str, Any]]:
    if validation_contract.locked_chain_ledger_path is None:
        raise NamedPipelineError(
            "Strict validation contract requires `locked_chain_ledger_path`."
        )
    ledger_payload = _load_json_mapping(
        path=validation_contract.locked_chain_ledger_path,
        source_label=str(validation_contract.locked_chain_ledger_path),
    )
    ledger_entries = ledger_payload.get("entries")
    if not isinstance(ledger_entries, list):
        raise NamedPipelineError(
            f"{validation_contract.locked_chain_ledger_path} field `entries` must be a list."
        )
    normalized_entries: list[Mapping[str, Any]] = []
    for entry in ledger_entries:
        if not isinstance(entry, dict):
            raise NamedPipelineError(
                f"{validation_contract.locked_chain_ledger_path} field `entries` must contain mappings."
            )
        normalized_entries.append(entry)
    return normalized_entries


def _resolve_tsa29_locked_chain_strict_row_order(*, seam_id: str) -> int:
    if seam_id in {"scratch", "glb"}:
        return 1
    if seam_id in {"aflb", "aflb_yield_ready"}:
        return 5
    raise NamedPipelineError(
        "Strict validation preflight does not yet support seam "
        f"`{seam_id}` for `tsa29_locked_chain_strict`."
    )


def _resolve_tsa29_locked_chain_entry(
    *,
    validation_contract: NamedPipelineValidationContract,
    row_order: int,
) -> Mapping[str, Any]:
    for entry in _load_locked_chain_entries(validation_contract):
        if _normalize_int_or_none(entry.get("row_order")) == row_order:
            return entry
    raise NamedPipelineError(
        "Strict validation contract is missing locked-chain row "
        f"`{row_order}` in {validation_contract.locked_chain_ledger_path}."
    )


def _resolve_tsa29_locked_chain_entry_by_parent_step_id(
    *,
    validation_contract: NamedPipelineValidationContract,
    parent_step_id: str,
) -> Mapping[str, Any]:
    normalized_parent_step_id = parent_step_id.strip()
    for entry in _load_locked_chain_entries(validation_contract):
        if str(entry.get("parent_step_id", "")).strip() == normalized_parent_step_id:
            return entry
    raise NamedPipelineError(
        "Strict validation contract is missing parent step "
        f"`{normalized_parent_step_id}` in {validation_contract.locked_chain_ledger_path}."
    )


def _is_reference_only_parent_step(parent_step: Mapping[str, Any]) -> bool:
    parent_kind = str(parent_step.get("parent_kind", "")).strip().casefold()
    execution_class = str(parent_step.get("execution_class", "")).strip().casefold()
    return parent_kind == "milestone" or execution_class == "reference_only"


def _resolve_locked_parent_step_sequence(
    *,
    recipe_path: Path,
    stop_after_parent_step_id: str | None = None,
) -> tuple[Mapping[str, Any], ...]:
    recipe = load_tsr_thlb_netdown_recipe(recipe_path)
    sequence: list[Mapping[str, Any]] = []
    normalized_stop_after = (
        stop_after_parent_step_id.strip() if stop_after_parent_step_id is not None else None
    )
    found_stop_after = normalized_stop_after is None
    for parent_step in recipe.parent_steps:
        parent_step_id = str(parent_step.get("parent_step_id", "")).strip()
        row_order = _normalize_int_or_none(parent_step.get("row_order"))
        if not parent_step_id or row_order is None:
            raise NamedPipelineError(
                f"Locked THLB recipe contains an invalid parent-step entry: {parent_step!r}"
            )
        if row_order <= 1:
            continue
        sequence.append(parent_step)
        if normalized_stop_after is not None and parent_step_id == normalized_stop_after:
            found_stop_after = True
            break
    if not found_stop_after:
        raise NamedPipelineError(
            "Strict scratch pipeline stop target is not present in the locked recipe: "
            f"`{normalized_stop_after}`."
        )
    return tuple(sequence)


def _source_tree_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _managed_area_ha_from_checkpoint(checkpoint_path: Path) -> float:
    if not checkpoint_path.exists():
        raise NamedPipelineError(f"Strict validation checkpoint not found: {checkpoint_path}")
    gpd = import_module("geopandas")
    checkpoint = gpd.read_feather(checkpoint_path)
    if "_stand_area_sqm" in checkpoint.columns and "thlb_fact" in checkpoint.columns:
        return float(
            (
                checkpoint["_stand_area_sqm"].astype(float)
                * checkpoint["thlb_fact"].astype(float)
            ).sum()
            / 10000.0
        )
    if "geometry" in checkpoint.columns:
        return float(checkpoint.geometry.area.sum() / 10000.0)
    raise NamedPipelineError(
        "Strict validation checkpoint is missing both managed-area columns and geometry: "
        f"{checkpoint_path}"
    )


def _materialize_tsa29_glb_checkpoint_from_result(
    *,
    instance_root: Path,
    clipped_glb_gdb_path: Path,
    clipped_glb_feature_class: str,
) -> Path:
    gpd = import_module("geopandas")
    checkpoint = gpd.read_file(
        clipped_glb_gdb_path,
        layer=clipped_glb_feature_class,
    )
    if len(checkpoint) == 0:
        raise NamedPipelineError(
            "Raw-source GLB build produced no features for TSA29; cannot materialize "
            "step-001 checkpoint."
        )
    area_sqm = checkpoint.geometry.area.astype(float)
    if "FEATURE_AREA_SQM" in checkpoint.columns:
        checkpoint["FEATURE_AREA_SQM"] = area_sqm
    if "POLYGON_AREA" in checkpoint.columns:
        checkpoint["POLYGON_AREA"] = area_sqm / 10000.0
    if "Shape_Area" in checkpoint.columns:
        checkpoint["Shape_Area"] = area_sqm
    if "GEOMETRY_AREA" in checkpoint.columns:
        checkpoint["GEOMETRY_AREA"] = area_sqm / 10000.0
    checkpoint_path = instance_root / "data" / "tsr" / "glb_checkpoint.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.to_feather(checkpoint_path)
    return checkpoint_path


def _validate_tsa29_locked_chain_strict_preflight(
    *,
    plan: NamedPipelineExecutionPlan,
    tolerance_ha: float = 1e-3,
) -> Mapping[str, Any]:
    validation_contract = plan.validation_contract
    if validation_contract is None:
        raise NamedPipelineError("Strict validation contract is required for this preflight.")
    locked_row_order = _resolve_tsa29_locked_chain_strict_row_order(seam_id=plan.seam_id)
    locked_entry = _resolve_tsa29_locked_chain_entry(
        validation_contract=validation_contract,
        row_order=locked_row_order,
    )
    locked_parent_step_id = str(locked_entry.get("parent_step_id", "")).strip()
    expected_benchmark_area_ha = _normalize_float_or_none(
        locked_entry.get("locked_cumulative_remaining_area_ha")
    )
    if expected_benchmark_area_ha is None:
        raise NamedPipelineError(
            "Strict validation contract ledger entry is missing "
            f"`locked_cumulative_remaining_area_ha` for row `{locked_row_order}`."
        )

    if plan.seam_id == "scratch":
        glb_result = build_tsa_raw_glb(
            source_root=_source_tree_root(),
            instance_root=plan.instance_root,
            tsa="29",
            stash_public_data_glb=False,
        )
        actual_start_area_ha = float(glb_result.clipped_area_ha)
        area_delta_ha = actual_start_area_ha - expected_benchmark_area_ha
        if abs(area_delta_ha) > tolerance_ha:
            raise NamedPipelineError(
                "Strict validation preflight mismatch for seam "
                f"`{plan.seam_id}` at locked row `{locked_row_order}` "
                f"(`{locked_parent_step_id}`): expected `{expected_benchmark_area_ha:.3f} ha`, "
                f"got `{actual_start_area_ha:.3f} ha`, delta `{area_delta_ha:.3f} ha`."
            )
        return {
            "locked_row_order": locked_row_order,
            "locked_parent_step_id": locked_parent_step_id,
            "expected_benchmark_area_ha": expected_benchmark_area_ha,
            "actual_start_area_ha": actual_start_area_ha,
            "area_delta_ha": area_delta_ha,
            "clipped_glb_gdb_path": glb_result.clipped_glb_gdb_path,
            "clipped_glb_feature_class": glb_result.clipped_glb_feature_class,
            "summary_json_path": glb_result.summary_json_path,
            "summary_markdown_path": glb_result.summary_markdown_path,
        }

    if plan.checkpoint_path is None:
        raise NamedPipelineError(
            "Strict validation preflight requires an explicit checkpoint path for seam "
            f"`{plan.seam_id}`."
        )
    actual_start_area_ha = _managed_area_ha_from_checkpoint(plan.checkpoint_path)

    if plan.seam_id == "aflb_yield_ready":
        aflb_checkpoint_path = plan.instance_root / "data" / "tsr" / "aflb_checkpoint.feather"
        aflb_area_ha = _managed_area_ha_from_checkpoint(aflb_checkpoint_path)
        aflb_delta_ha = actual_start_area_ha - aflb_area_ha
        if abs(aflb_delta_ha) > tolerance_ha:
            raise NamedPipelineError(
                "Strict validation preflight mismatch for seam `aflb_yield_ready`: expected "
                "yield-ready area to preserve AFLB area from "
                f"`{aflb_checkpoint_path}`; AFLB `{aflb_area_ha:.3f} ha`, "
                f"yield-ready `{actual_start_area_ha:.3f} ha`, "
                f"delta `{aflb_delta_ha:.3f} ha`."
            )

    area_delta_ha = actual_start_area_ha - expected_benchmark_area_ha
    if abs(area_delta_ha) > tolerance_ha:
        raise NamedPipelineError(
            "Strict validation preflight mismatch for seam "
            f"`{plan.seam_id}` at locked row `{locked_row_order}` "
            f"(`{locked_parent_step_id}`): expected `{expected_benchmark_area_ha:.3f} ha`, "
            f"got `{actual_start_area_ha:.3f} ha`, delta `{area_delta_ha:.3f} ha`."
        )

    return {
        "locked_row_order": locked_row_order,
        "locked_parent_step_id": locked_parent_step_id,
        "expected_benchmark_area_ha": expected_benchmark_area_ha,
        "actual_start_area_ha": actual_start_area_ha,
        "area_delta_ha": area_delta_ha,
    }


def _validate_tsa29_locked_chain_parent_step(
    *,
    validation_contract: NamedPipelineValidationContract,
    parent_step_id: str,
    removed_area_ha: float | None,
    remaining_area_ha: float,
    tolerance_ha: float = 1e-3,
) -> NamedPipelineValidationResult:
    locked_entry = _resolve_tsa29_locked_chain_entry_by_parent_step_id(
        validation_contract=validation_contract,
        parent_step_id=parent_step_id,
    )
    row_order = _normalize_int_or_none(locked_entry.get("row_order"))
    if row_order is None:
        raise NamedPipelineError(
            "Strict validation contract ledger entry is missing row order for "
            f"`{parent_step_id}`."
        )
    expected_removed_ha = _normalize_float_or_none(
        locked_entry.get("locked_net_removed_area_ha")
    )
    expected_remaining_ha = _normalize_float_or_none(
        locked_entry.get("locked_cumulative_remaining_area_ha")
    )
    locked_parent_step_id = str(locked_entry.get("parent_step_id", "")).strip() or None
    if expected_removed_ha is None or expected_remaining_ha is None:
        if expected_remaining_ha is None:
            raise NamedPipelineError(
                "Strict validation contract ledger entry is missing locked cumulative "
                f"value for row `{row_order}`."
            )
        expected_removed_ha = 0.0
    actual_removed_ha = 0.0 if removed_area_ha is None else removed_area_ha
    marginal_delta_ha = actual_removed_ha - expected_removed_ha
    cumulative_delta_ha = remaining_area_ha - expected_remaining_ha
    if abs(marginal_delta_ha) > tolerance_ha or abs(cumulative_delta_ha) > tolerance_ha:
        raise NamedPipelineError(
            "Strict validation mismatch at row "
            f"`{row_order}` (`{locked_parent_step_id}`): expected marginal "
            f"`{expected_removed_ha:.3f} ha`, got `{actual_removed_ha:.3f} ha`, "
            f"delta `{marginal_delta_ha:.3f} ha`; expected cumulative "
            f"`{expected_remaining_ha:.3f} ha`, got `{remaining_area_ha:.3f} ha`, "
            f"delta `{cumulative_delta_ha:.3f} ha`."
        )
    return NamedPipelineValidationResult(
        contract_kind=validation_contract.contract_kind,
        validated_parent_step_count=row_order,
        latest_locked_row_order=row_order,
        latest_locked_parent_step_id=locked_parent_step_id,
        expected_final_managed_area_ha=expected_remaining_ha,
        actual_final_managed_area_ha=remaining_area_ha,
        max_abs_marginal_delta_ha=abs(marginal_delta_ha),
        max_abs_cumulative_delta_ha=abs(cumulative_delta_ha),
    )


def _run_tsa29_strict_sequence_from_checkpoint(
    *,
    plan: NamedPipelineExecutionPlan,
    start_checkpoint_path: Path,
    start_validated_row_order: int,
    start_validated_parent_step_id: str,
    start_remaining_area_ha: float,
    runtime_logger: "_NamedPipelineRuntimeEventLogger",
) -> tuple[TsrThlbParentStepRunResult | None, NamedPipelineValidationResult]:
    validation_contract = plan.validation_contract
    if validation_contract is None:
        raise NamedPipelineError(
            "Strict pipeline sequencing requires a validation contract."
        )
    current_checkpoint_path = start_checkpoint_path
    sequence = _resolve_locked_parent_step_sequence(
        recipe_path=plan.thlb_netdown_recipe_path,
        stop_after_parent_step_id=plan.target_parent_step_id,
    )
    latest_validation = NamedPipelineValidationResult(
        contract_kind=validation_contract.contract_kind,
        validated_parent_step_count=start_validated_row_order,
        latest_locked_row_order=start_validated_row_order,
        latest_locked_parent_step_id=start_validated_parent_step_id,
        expected_final_managed_area_ha=start_remaining_area_ha,
        actual_final_managed_area_ha=start_remaining_area_ha,
        max_abs_marginal_delta_ha=0.0,
        max_abs_cumulative_delta_ha=0.0,
    )
    last_parent_step_result: TsrThlbParentStepRunResult | None = None
    for parent_step in sequence:
        parent_step_id = str(parent_step.get("parent_step_id", "")).strip()
        parent_label = str(parent_step.get("parent_label", "")).strip() or None
        row_order = _normalize_int_or_none(parent_step.get("row_order"))
        land_base_stage = str(parent_step.get("land_base_stage", "")).strip() or None
        runtime_logger.emit(
            {
                "event_kind": "parent_step_started",
                "parent_step_id": parent_step_id,
                "parent_label": parent_label,
                "row_order": row_order,
                "land_base_stage": land_base_stage,
                "checkpoint_path": current_checkpoint_path,
            }
        )
        if _is_reference_only_parent_step(parent_step):
            remaining_area_ha = _managed_area_ha_from_checkpoint(current_checkpoint_path)
            latest_validation = _validate_tsa29_locked_chain_parent_step(
                validation_contract=validation_contract,
                parent_step_id=parent_step_id,
                removed_area_ha=None,
                remaining_area_ha=remaining_area_ha,
            )
            runtime_logger.emit(
                {
                    "event_kind": "parent_step_finished",
                    "parent_step_id": parent_step_id,
                    "parent_label": parent_label,
                    "row_order": row_order,
                    "land_base_stage": land_base_stage,
                    "run_status": "reference_validated",
                    "remaining_area_ha": remaining_area_ha,
                    "checkpoint_path": current_checkpoint_path,
                }
            )
            continue
        parent_step_result = run_tsr_thlb_parent_step(
            recipe_path=plan.thlb_netdown_recipe_path,
            parent_step_id=parent_step_id,
            checkpoint_path=current_checkpoint_path,
            auto_map_id_smoke_subset=False,
        )
        last_parent_step_result = parent_step_result
        current_checkpoint_path = parent_step_result.output_path
        latest_validation = _validate_tsa29_locked_chain_parent_step(
            validation_contract=validation_contract,
            parent_step_id=parent_step_id,
            removed_area_ha=parent_step_result.removed_area_ha,
            remaining_area_ha=parent_step_result.remaining_area_ha,
        )
        runtime_logger.emit(
            {
                "event_kind": "parent_step_finished",
                "parent_step_id": parent_step_result.parent_step_id,
                "parent_label": parent_step_result.parent_label,
                "row_order": row_order,
                "land_base_stage": land_base_stage,
                "run_status": parent_step_result.status,
                "remaining_area_ha": parent_step_result.remaining_area_ha,
                "checkpoint_path": current_checkpoint_path,
            }
        )
    return last_parent_step_result, latest_validation


def run_named_pipeline_runbook(
    *,
    runbook_path: Path,
    instance_root: Path | None = None,
    runtime_event_sink: Callable[[str], None] | None = None,
) -> NamedPipelineExecutionResult:
    """Run the first named-pipeline proof surface from one machine-readable runbook."""

    plan = build_named_pipeline_execution_plan(
        runbook_path=runbook_path,
        instance_root=instance_root,
    )
    runtime_event_log_path = default_named_pipeline_runtime_event_log_path(
        instance_root=plan.instance_root,
        pipeline_id=plan.pipeline_id,
    )
    runtime_logger = _NamedPipelineRuntimeEventLogger(
        log_path=runtime_event_log_path,
        default_fields={
            "pipeline_id": plan.pipeline_id,
            "runbook_path": plan.runbook_path,
            "instance_root": plan.instance_root,
            "execution_mode": plan.execution_mode,
            "seam_id": plan.seam_id,
            "recipe_path": plan.thlb_netdown_recipe_path,
            "checkpoint_path": (
                plan.checkpoint_path if plan.checkpoint_path is not None else "<scratch>"
            ),
        },
        line_sink=runtime_event_sink,
    )
    runtime_logger.emit(
        {
            "event_kind": "pipeline_run_started",
            "pipeline_label": plan.pipeline_label,
        }
    )
    runtime_logger.emit(
        {
            "event_kind": "pipeline_preflight_resolved",
            "run_profile_path": plan.run_profile_path,
            "validation_contract_kind": (
                plan.validation_contract.contract_kind
                if plan.validation_contract is not None
                else None
            ),
            "locked_chain_ledger_path": (
                plan.validation_contract.locked_chain_ledger_path
                if plan.validation_contract is not None
                else None
            ),
            "comparison_report_path": (
                plan.validation_contract.comparison_report_path
                if plan.validation_contract is not None
                else None
            ),
            "required_recipe_path": (
                plan.validation_contract.required_recipe_path
                if plan.validation_contract is not None
                else None
            ),
        }
    )
    validation_result: NamedPipelineValidationResult | None = None
    try:
        if (
            plan.validation_contract is not None
            and plan.validation_contract.contract_kind == "tsa29_locked_chain_strict"
        ):
            runtime_logger.emit(
                {
                    "event_kind": "pipeline_validation_preflight_started",
                    "validation_contract_kind": plan.validation_contract.contract_kind,
                }
            )
            preflight_result = _validate_tsa29_locked_chain_strict_preflight(plan=plan)
            runtime_logger.emit(
                {
                    "event_kind": "pipeline_validation_preflight_finished",
                    "validation_contract_kind": plan.validation_contract.contract_kind,
                    **preflight_result,
                }
            )
            if plan.seam_id in {"scratch", "glb"}:
                start_checkpoint_path = plan.checkpoint_path
                if plan.seam_id == "scratch":
                    glb_checkpoint_path = _materialize_tsa29_glb_checkpoint_from_result(
                        instance_root=plan.instance_root,
                        clipped_glb_gdb_path=cast(
                            Path, preflight_result["clipped_glb_gdb_path"]
                        ),
                        clipped_glb_feature_class=cast(
                            str, preflight_result["clipped_glb_feature_class"]
                        ),
                    )
                    start_checkpoint_path = glb_checkpoint_path
                    runtime_logger.emit(
                        {
                            "event_kind": "pipeline_preflight_resolved",
                            "notes": f"glb_checkpoint_path={glb_checkpoint_path}",
                        }
                    )
                if plan.target_parent_step_id is not None:
                    parent_step_result, validation_result = (
                        _run_tsa29_strict_sequence_from_checkpoint(
                            plan=plan,
                            start_checkpoint_path=cast(Path, start_checkpoint_path),
                            start_validated_row_order=cast(
                                int, preflight_result["locked_row_order"]
                            ),
                            start_validated_parent_step_id=cast(
                                str, preflight_result["locked_parent_step_id"]
                            ),
                            start_remaining_area_ha=cast(
                                float, preflight_result["actual_start_area_ha"]
                            ),
                            runtime_logger=runtime_logger,
                        )
                    )
                    runtime_logger.emit(
                        {
                            "event_kind": "pipeline_run_finished",
                            "validated_parent_step_count": (
                                validation_result.validated_parent_step_count
                            ),
                            "latest_locked_row_order": (
                                validation_result.latest_locked_row_order
                            ),
                            "latest_locked_parent_step_id": (
                                validation_result.latest_locked_parent_step_id
                            ),
                            "expected_final_managed_area_ha": (
                                validation_result.expected_final_managed_area_ha
                            ),
                            "actual_final_managed_area_ha": (
                                validation_result.actual_final_managed_area_ha
                            ),
                            "notes": (
                                "strict scratch seam executed the locked parent-step "
                                "sequence through the requested stop target"
                            ),
                        }
                    )
                    return NamedPipelineExecutionResult(
                        plan=plan,
                        tsr_thlb_result=None,
                        tsr_parent_step_result=parent_step_result,
                        validation_result=validation_result,
                        runtime_event_log_path=runtime_event_log_path,
                    )
                validation_result = NamedPipelineValidationResult(
                    contract_kind=plan.validation_contract.contract_kind,
                    validated_parent_step_count=1,
                    latest_locked_row_order=cast(
                        int | None, preflight_result.get("locked_row_order")
                    ),
                    latest_locked_parent_step_id=cast(
                        str | None, preflight_result.get("locked_parent_step_id")
                    ),
                    expected_final_managed_area_ha=cast(
                        float | None, preflight_result.get("expected_benchmark_area_ha")
                    ),
                    actual_final_managed_area_ha=cast(
                        float | None, preflight_result.get("actual_start_area_ha")
                    ),
                    max_abs_marginal_delta_ha=0.0,
                    max_abs_cumulative_delta_ha=abs(
                        cast(float, preflight_result.get("area_delta_ha", 0.0))
                    ),
                )
                runtime_logger.emit(
                    {
                        "event_kind": "pipeline_run_finished",
                        "validated_parent_step_count": 1,
                        "latest_locked_row_order": (
                            validation_result.latest_locked_row_order
                        ),
                        "latest_locked_parent_step_id": (
                            validation_result.latest_locked_parent_step_id
                        ),
                        "expected_final_managed_area_ha": (
                            validation_result.expected_final_managed_area_ha
                        ),
                        "actual_final_managed_area_ha": (
                            validation_result.actual_final_managed_area_ha
                        ),
                        "notes": (
                            "strict scratch seam validated locked-chain row 1 and "
                            "stopped before step 002"
                        ),
                    }
                )
                return NamedPipelineExecutionResult(
                    plan=plan,
                    tsr_thlb_result=None,
                    validation_result=validation_result,
                    runtime_event_log_path=runtime_event_log_path,
                )
        tsr_result = run_tsr_thlb_netdown_recipe(
            recipe_path=plan.thlb_netdown_recipe_path,
            checkpoint_path=plan.checkpoint_path,
            execution_mode=plan.execution_mode,
            runtime_event_sink=runtime_logger.emit,
        )
    except Exception as exc:
        runtime_logger.emit(
            {
                "event_kind": "pipeline_run_failed",
                "error": str(exc),
            }
        )
        raise
    try:
        if (
            plan.validation_contract is not None
            and plan.validation_contract.contract_kind == "tsa29_locked_chain_strict"
        ):
            runtime_logger.emit(
                {
                    "event_kind": "pipeline_validation_started",
                    "validation_contract_kind": plan.validation_contract.contract_kind,
                }
            )
            validation_result = _validate_tsa29_locked_chain_strict_result(
                plan=plan,
                tsr_result=tsr_result,
            )
            runtime_logger.emit(
                {
                    "event_kind": "pipeline_validation_finished",
                    "validation_contract_kind": validation_result.contract_kind,
                    "validated_parent_step_count": (
                        validation_result.validated_parent_step_count
                    ),
                    "latest_locked_row_order": (
                        validation_result.latest_locked_row_order
                    ),
                    "latest_locked_parent_step_id": (
                        validation_result.latest_locked_parent_step_id
                    ),
                    "expected_final_managed_area_ha": (
                        validation_result.expected_final_managed_area_ha
                    ),
                    "actual_final_managed_area_ha": (
                        validation_result.actual_final_managed_area_ha
                    ),
                }
            )
    except Exception as exc:
        runtime_logger.emit(
            {
                "event_kind": "pipeline_run_failed",
                "error": str(exc),
            }
        )
        raise
    runtime_logger.emit(
        {
            "event_kind": "pipeline_run_finished",
            "step_count": tsr_result.step_count,
            "final_managed_area_ha": tsr_result.final_managed_area_ha,
            "runtime_status_report_path": tsr_result.runtime_status_report_path,
            "audit_path": tsr_result.audit_path,
        }
    )
    return NamedPipelineExecutionResult(
        plan=plan,
        tsr_thlb_result=tsr_result,
        validation_result=validation_result,
        runtime_event_log_path=runtime_event_log_path,
    )
