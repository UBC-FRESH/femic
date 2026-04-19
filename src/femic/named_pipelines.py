"""Named-pipeline registry, runbook, and proof-runner helpers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, cast

import yaml

from femic.tsr_catalog import (
    TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
    TsrThlbNetdownRecipeRunResult,
    default_tsr_thlb_netdown_recipe_path,
    load_tsr_thlb_netdown_recipe,
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


@dataclass(frozen=True)
class NamedPipelineExecutionResult:
    """Result of running one named-pipeline proof surface."""

    plan: NamedPipelineExecutionPlan
    tsr_thlb_result: TsrThlbNetdownRecipeRunResult


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


def _normalize_string(value: Any, *, field_name: str, source_label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise NamedPipelineError(f"{source_label} field `{field_name}` is required.")
    return normalized


def _normalize_optional_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value))


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
        user_registry_path=registry.user_registry_path,
        instance_registry_path=registry.instance_registry_path,
        explicit_registry_paths=registry.explicit_registry_paths,
        thlb_netdown_recipe_path=thlb_recipe_path,
        source_layers_recipe_path=source_layers_recipe_path,
        execution_mode=TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
    )


def run_named_pipeline_runbook(
    *,
    runbook_path: Path,
    instance_root: Path | None = None,
) -> NamedPipelineExecutionResult:
    """Run the first named-pipeline proof surface from one machine-readable runbook."""

    plan = build_named_pipeline_execution_plan(
        runbook_path=runbook_path,
        instance_root=instance_root,
    )
    tsr_result = run_tsr_thlb_netdown_recipe(
        recipe_path=plan.thlb_netdown_recipe_path,
        checkpoint_path=plan.checkpoint_path,
        execution_mode=plan.execution_mode,
    )
    return NamedPipelineExecutionResult(plan=plan, tsr_thlb_result=tsr_result)
