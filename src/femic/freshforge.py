"""FreshForge provider integration for FEMIC model-build workflows.

Validation and planning remain non-mutating. Execution is only available when a
caller explicitly invokes ``freshforge run`` against providers from this module.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

FEMIC_PROVIDER_ID = "femic"
FEMIC_MKRF_PROVIDER_ID = "femic.mkrf"
FEMIC_PROVIDER_VERSION = "0.1.0a1"

CommandRunner = Callable[[tuple[str, ...]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class _NodeContract:
    id: str
    name: str
    description: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    parameters: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()


_NODE_CONTRACTS: tuple[_NodeContract, ...] = (
    _NodeContract(
        id="validate_case",
        name="Validate FEMIC case",
        description="Declare the FEMIC case-aware preflight seam.",
        outputs=("case_validation",),
        parameters=("instance_root", "run_config"),
    ),
    _NodeContract(
        id="geospatial_preflight",
        name="Geospatial preflight",
        description="Declare the generic geospatial runtime preflight seam.",
        inputs=("case_validation",),
        outputs=("geospatial_runtime",),
        parameters=("instance_root",),
    ),
    _NodeContract(
        id="compile_upstream",
        name="Compile upstream model inputs",
        description="Declare FEMIC Stage 00 and Stage 01a upstream compilation.",
        inputs=("geospatial_runtime",),
        outputs=("btc_handoff",),
        parameters=("instance_root", "run_config", "run_id"),
        artifacts=("run_manifest",),
    ),
    _NodeContract(
        id="btc_post_tipsy",
        name="BTC and post-TIPSY bundle",
        description="Declare the unattended BTC and Stage 01b bundle seam.",
        inputs=("btc_handoff",),
        outputs=("model_input_bundle",),
        parameters=("instance_root", "run_config", "tsa", "run_id"),
        artifacts=("btc_manifest", "post_tipsy_manifest"),
    ),
    _NodeContract(
        id="export_patchworks",
        name="Export Patchworks package",
        description="Declare the FEMIC Patchworks model-package export seam.",
        inputs=("model_input_bundle",),
        outputs=("patchworks_package",),
        parameters=("instance_root", "run_config", "tsa"),
        artifacts=("forestmodel_xml", "fragments"),
    ),
    _NodeContract(
        id="patchworks_preflight",
        name="Patchworks preflight",
        description="Declare Patchworks runtime/config preflight.",
        inputs=("patchworks_package",),
        outputs=("patchworks_runtime",),
        parameters=("instance_root", "patchworks_config"),
    ),
    _NodeContract(
        id="matrix_build",
        name="Patchworks matrix build",
        description="Declare Patchworks matrix-builder compilation.",
        inputs=("patchworks_runtime",),
        outputs=("compiled_patchworks_model",),
        parameters=("instance_root", "patchworks_config", "run_id"),
        artifacts=("matrix_build_manifest",),
    ),
)

_MKRF_NODE_CONTRACTS: tuple[_NodeContract, ...] = (
    _NodeContract(
        id="build_au_inputs",
        name="Build MKRF AU inputs",
        description="Build MKRF AU and stand-assignment inputs from Resultant.gdb.",
        outputs=("au_inputs",),
        parameters=("instance_root", "resultant_gdb"),
        artifacts=("au_table", "stand_assignment"),
    ),
    _NodeContract(
        id="select_aus",
        name="Select MKRF analysis units",
        description="Publish the canonical MKRF selected AU subset.",
        inputs=("au_inputs",),
        outputs=("selected_aus",),
        parameters=("instance_root",),
        artifacts=("selected_au_table",),
    ),
    _NodeContract(
        id="build_managed_au_inputs",
        name="Build MKRF managed AU inputs",
        description="Build managed AU bootstrap and MSYT input surfaces.",
        inputs=("selected_aus",),
        outputs=("managed_au_inputs",),
        parameters=("instance_root", "resultant_gdb"),
        artifacts=("stand_origin_assignment", "managed_au_msyt"),
    ),
    _NodeContract(
        id="build_managed_au_curves",
        name="Build MKRF managed AU curves",
        description="Run the managed AU BTC curve-building seam.",
        inputs=("managed_au_inputs",),
        outputs=("managed_au_curves",),
        parameters=("instance_root", "run_id"),
        artifacts=("managed_au_curves", "managed_run_manifest"),
    ),
    _NodeContract(
        id="init_runtime_package",
        name="Initialize MKRF runtime package",
        description="Initialize the canonical MKRF Patchworks runtime package.",
        inputs=("managed_au_curves",),
        outputs=("patchworks_package",),
        parameters=("instance_root",),
        artifacts=("forestmodel_xml", "runtime_manifest"),
    ),
)


class FemicFreshForgeProvider:
    """FreshForge provider for generic FEMIC workflow stages."""

    def __init__(self, command_runner: CommandRunner | None = None) -> None:
        self._command_runner = command_runner or _default_command_runner

    def metadata(self) -> Any:
        """Return FreshForge provider metadata."""
        return _provider_metadata(
            provider_id=FEMIC_PROVIDER_ID,
            name="FEMIC model-build provider",
            description=(
                "Provider for FEMIC model-build workflow validation, planning, "
                "and explicit execution."
            ),
            contracts=_NODE_CONTRACTS,
        )

    def validate_node(
        self, node: Any, node_type: Any, *, location: str
    ) -> tuple[Any, ...]:
        """Validate broad FEMIC node shape without executing FEMIC."""
        diagnostic, severity = _freshforge_diagnostic_types()
        diagnostics: list[Any] = []
        diagnostics.extend(
            _missing_key_diagnostics(
                diagnostic=diagnostic,
                severity=severity,
                required=tuple(node_type.inputs),
                actual=node.inputs,
                field_name="inputs",
                location=location,
            )
        )
        diagnostics.extend(
            _missing_key_diagnostics(
                diagnostic=diagnostic,
                severity=severity,
                required=tuple(node_type.outputs),
                actual=node.outputs,
                field_name="outputs",
                location=location,
            )
        )
        diagnostics.extend(
            _missing_key_diagnostics(
                diagnostic=diagnostic,
                severity=severity,
                required=tuple(node_type.parameters),
                actual=node.parameters,
                field_name="parameters",
                location=location,
            )
        )
        artifacts = node.artifacts if isinstance(node.artifacts, dict) else {}
        diagnostics.extend(
            _missing_key_diagnostics(
                diagnostic=diagnostic,
                severity=severity,
                required=tuple(node_type.artifacts),
                actual=artifacts,
                field_name="artifacts",
                location=location,
            )
        )
        diagnostics.extend(
            _empty_parameter_diagnostics(
                diagnostic=diagnostic,
                severity=severity,
                parameters=node.parameters,
                required=tuple(node_type.parameters),
                location=location,
            )
        )
        return tuple(diagnostics)

    def execute_node(self, node: Any, node_type: Any, *, context: Any) -> Any:
        """Execute one generic FEMIC node through the installed FEMIC CLI."""
        builders = _generic_command_builders()
        return _execute_with_builder(
            node=node,
            node_type=node_type,
            context=context,
            provider_id=FEMIC_PROVIDER_ID,
            builders=builders,
            runner=self._command_runner,
        )


class FemicMkrfFreshForgeProvider:
    """FreshForge provider for MKRF-specific runtime-package regeneration."""

    def __init__(self, command_runner: CommandRunner | None = None) -> None:
        self._command_runner = command_runner or _default_command_runner

    def metadata(self) -> Any:
        """Return FreshForge provider metadata."""
        return _provider_metadata(
            provider_id=FEMIC_MKRF_PROVIDER_ID,
            name="FEMIC MKRF model-build provider",
            description=(
                "Provider for MKRF-specific FEMIC runtime-package regeneration "
                "validation, planning, and explicit execution."
            ),
            contracts=_MKRF_NODE_CONTRACTS,
        )

    def validate_node(
        self, node: Any, node_type: Any, *, location: str
    ) -> tuple[Any, ...]:
        """Validate broad MKRF node shape without executing FEMIC."""
        return _validate_contract_node(node, node_type, location=location)

    def execute_node(self, node: Any, node_type: Any, *, context: Any) -> Any:
        """Execute one MKRF node through the installed FEMIC CLI."""
        builders = _mkrf_command_builders()
        return _execute_with_builder(
            node=node,
            node_type=node_type,
            context=context,
            provider_id=FEMIC_MKRF_PROVIDER_ID,
            builders=builders,
            runner=self._command_runner,
        )


def provider_factory() -> FemicFreshForgeProvider:
    """Return the FEMIC FreshForge provider for entry-point discovery."""
    return FemicFreshForgeProvider()


def mkrf_provider_factory() -> FemicMkrfFreshForgeProvider:
    """Return the MKRF FreshForge provider for entry-point discovery."""
    return FemicMkrfFreshForgeProvider()


def _provider_metadata(
    *,
    provider_id: str,
    name: str,
    description: str,
    contracts: Sequence[_NodeContract],
) -> Any:
    node_type_metadata, provider_metadata = _freshforge_metadata_types()
    return provider_metadata(
        id=provider_id,
        version=FEMIC_PROVIDER_VERSION,
        name=name,
        description=description,
        node_types=tuple(
            node_type_metadata(
                id=contract.id,
                name=contract.name,
                description=contract.description,
                inputs=contract.inputs,
                outputs=contract.outputs,
                parameters=contract.parameters,
                artifacts=contract.artifacts,
            )
            for contract in contracts
        ),
    )


def _validate_contract_node(
    node: Any,
    node_type: Any,
    *,
    location: str,
) -> tuple[Any, ...]:
    diagnostic, severity = _freshforge_diagnostic_types()
    diagnostics: list[Any] = []
    diagnostics.extend(
        _missing_key_diagnostics(
            diagnostic=diagnostic,
            severity=severity,
            required=tuple(node_type.inputs),
            actual=node.inputs,
            field_name="inputs",
            location=location,
        )
    )
    diagnostics.extend(
        _missing_key_diagnostics(
            diagnostic=diagnostic,
            severity=severity,
            required=tuple(node_type.outputs),
            actual=node.outputs,
            field_name="outputs",
            location=location,
        )
    )
    diagnostics.extend(
        _missing_key_diagnostics(
            diagnostic=diagnostic,
            severity=severity,
            required=tuple(node_type.parameters),
            actual=node.parameters,
            field_name="parameters",
            location=location,
        )
    )
    artifacts = node.artifacts if isinstance(node.artifacts, dict) else {}
    diagnostics.extend(
        _missing_key_diagnostics(
            diagnostic=diagnostic,
            severity=severity,
            required=tuple(node_type.artifacts),
            actual=artifacts,
            field_name="artifacts",
            location=location,
        )
    )
    diagnostics.extend(
        _empty_parameter_diagnostics(
            diagnostic=diagnostic,
            severity=severity,
            parameters=node.parameters,
            required=tuple(node_type.parameters),
            location=location,
        )
    )
    return tuple(diagnostics)


def _freshforge_metadata_types() -> tuple[Any, Any]:
    try:
        from freshforge.providers import (  # type: ignore[import-untyped]
            NodeTypeMetadata,
            ProviderMetadata,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The FEMIC FreshForge integration requires the optional "
            "`femic[freshforge]` dependency."
        ) from exc
    return NodeTypeMetadata, ProviderMetadata


def _freshforge_diagnostic_types() -> tuple[Any, Any]:
    try:
        from freshforge.records import (  # type: ignore[import-untyped]
            Diagnostic,
            DiagnosticSeverity,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The FEMIC FreshForge integration requires the optional "
            "`femic[freshforge]` dependency."
        ) from exc
    return Diagnostic, DiagnosticSeverity


def _freshforge_execution_result_type() -> Any:
    try:
        from freshforge.records import ProviderExecutionResult  # type: ignore[import-untyped]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The FEMIC FreshForge integration requires the optional "
            "`femic[freshforge]` dependency."
        ) from exc
    return ProviderExecutionResult


def _execute_with_builder(
    *,
    node: Any,
    node_type: Any,
    context: Any,
    provider_id: str,
    builders: dict[str, Callable[[Any, Any], tuple[str, ...]]],
    runner: CommandRunner,
) -> Any:
    result_type = _freshforge_execution_result_type()
    diagnostic, severity = _freshforge_diagnostic_types()
    builder = builders.get(str(node_type.id))
    if builder is None:
        return result_type(
            diagnostics=(
                diagnostic(
                    severity=severity.ERROR,
                    code="femic.execution.unsupported",
                    message=(
                        f"FEMIC provider '{provider_id}' has no execution hook "
                        f"for node type '{node_type.id}'."
                    ),
                    location=f"nodes.{node.id}",
                ),
            )
        )
    try:
        command = builder(node, context)
    except ValueError as exc:
        return result_type(
            diagnostics=(
                diagnostic(
                    severity=severity.ERROR,
                    code="femic.execution.parameters.invalid",
                    message=str(exc),
                    location=f"nodes.{node.id}.parameters",
                ),
            )
        )
    completed = runner(command)
    metadata: dict[str, Any] = {"returncode": completed.returncode}
    if completed.stdout:
        metadata["stdout"] = completed.stdout
    if completed.stderr:
        metadata["stderr"] = completed.stderr
    diagnostics: tuple[Any, ...] = ()
    if completed.returncode != 0:
        diagnostics = (
            diagnostic(
                severity=severity.ERROR,
                code="femic.execution.command.failed",
                message=(
                    f"FEMIC command for node '{node.id}' exited with "
                    f"return code {completed.returncode}."
                ),
                location=f"nodes.{node.id}",
            ),
        )
    artifacts = node.artifacts if isinstance(node.artifacts, dict) else {}
    return result_type(
        metadata=metadata,
        command=command,
        diagnostics=diagnostics,
        artifacts=artifacts,
    )


def _default_command_runner(
    command: tuple[str, ...],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
    )


def _python_m_femic(*args: str) -> tuple[str, ...]:
    return (sys.executable, "-m", "femic", *args)


def _parameter(node: Any, key: str) -> str:
    value = node.parameters.get(key)
    if value is None:
        raise ValueError(f"FEMIC node '{node.id}' requires parameter '{key}'.")
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(
                f"FEMIC node '{node.id}' parameter '{key}' must be nonempty."
            )
        return value
    return str(value)


def _optional_parameter(node: Any, key: str) -> str | None:
    value = node.parameters.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value if value.strip() else None
    return str(value)


def _append_option(command: list[str], node: Any, key: str, option: str) -> None:
    value = _optional_parameter(node, key)
    if value is not None:
        command.extend([option, value])


def _generic_command_builders() -> dict[str, Callable[[Any, Any], tuple[str, ...]]]:
    return {
        "validate_case": _build_validate_case_command,
        "geospatial_preflight": _build_geospatial_preflight_command,
        "compile_upstream": _build_compile_upstream_command,
        "btc_post_tipsy": _build_btc_post_tipsy_command,
        "export_patchworks": _build_export_patchworks_command,
        "patchworks_preflight": _build_patchworks_preflight_command,
        "matrix_build": _build_matrix_build_command,
    }


def _mkrf_command_builders() -> dict[str, Callable[[Any, Any], tuple[str, ...]]]:
    return {
        "build_au_inputs": _build_mkrf_au_inputs_command,
        "select_aus": _build_mkrf_select_aus_command,
        "build_managed_au_inputs": _build_mkrf_managed_au_inputs_command,
        "build_managed_au_curves": _build_mkrf_managed_au_curves_command,
        "init_runtime_package": _build_mkrf_init_runtime_package_command,
    }


def _build_validate_case_command(node: Any, _context: Any) -> tuple[str, ...]:
    rebuild_spec = _optional_parameter(node, "rebuild_spec")
    if rebuild_spec is not None:
        return _python_m_femic(
            "instance",
            "validate-spec",
            "--instance-root",
            _parameter(node, "instance_root"),
            "--spec",
            rebuild_spec,
        )
    command = list(
        _python_m_femic(
            "prep",
            "validate-case",
            "--instance-root",
            _parameter(node, "instance_root"),
            "--run-config",
            _parameter(node, "run_config"),
        )
    )
    _append_option(command, node, "tipsy_config_dir", "--tipsy-config-dir")
    return tuple(command)


def _build_geospatial_preflight_command(node: Any, _context: Any) -> tuple[str, ...]:
    _ = _parameter(node, "instance_root")
    return _python_m_femic("prep", "geospatial-preflight")


def _build_compile_upstream_command(node: Any, _context: Any) -> tuple[str, ...]:
    command = list(
        _python_m_femic(
            "run",
            "--instance-root",
            _parameter(node, "instance_root"),
            "--run-config",
            _parameter(node, "run_config"),
            "--run-id",
            _parameter(node, "run_id"),
        )
    )
    _append_option(command, node, "log_dir", "--log-dir")
    return tuple(command)


def _build_btc_post_tipsy_command(node: Any, _context: Any) -> tuple[str, ...]:
    command = list(
        _python_m_femic(
            "tsa",
            "btc-post-tipsy",
            "--instance-root",
            _parameter(node, "instance_root"),
            "--run-config",
            _parameter(node, "run_config"),
            "--tsa",
            _parameter(node, "tsa"),
            "--run-id",
            _parameter(node, "run_id"),
        )
    )
    _append_option(command, node, "log_dir", "--log-dir")
    _append_option(command, node, "btc_exe", "--btc-exe")
    _append_option(command, node, "scratch_dir", "--scratch-dir")
    return tuple(command)


def _build_export_patchworks_command(node: Any, _context: Any) -> tuple[str, ...]:
    command = list(
        _python_m_femic(
            "export",
            "patchworks",
            "--instance-root",
            _parameter(node, "instance_root"),
            "--tsa",
            _parameter(node, "tsa"),
        )
    )
    _append_option(command, node, "bundle_dir", "--bundle-dir")
    _append_option(command, node, "checkpoint", "--checkpoint")
    _append_option(command, node, "output_dir", "--output-dir")
    return tuple(command)


def _build_patchworks_preflight_command(node: Any, _context: Any) -> tuple[str, ...]:
    return _python_m_femic(
        "patchworks",
        "preflight",
        "--instance-root",
        _parameter(node, "instance_root"),
        "--config",
        _parameter(node, "patchworks_config"),
    )


def _build_matrix_build_command(node: Any, _context: Any) -> tuple[str, ...]:
    command = list(
        _python_m_femic(
            "patchworks",
            "matrix-build",
            "--instance-root",
            _parameter(node, "instance_root"),
            "--config",
            _parameter(node, "patchworks_config"),
            "--run-id",
            _parameter(node, "run_id"),
        )
    )
    _append_option(command, node, "log_dir", "--log-dir")
    return tuple(command)


def _build_mkrf_au_inputs_command(node: Any, _context: Any) -> tuple[str, ...]:
    command = list(
        _python_m_femic(
            "instance",
            "mkrf-build-au-inputs",
            "--instance-root",
            _parameter(node, "instance_root"),
            "--resultant-gdb",
            _parameter(node, "resultant_gdb"),
        )
    )
    _append_option(command, node, "output_dir", "--output-dir")
    return tuple(command)


def _build_mkrf_select_aus_command(node: Any, _context: Any) -> tuple[str, ...]:
    command = list(
        _python_m_femic(
            "instance",
            "mkrf-select-aus",
            "--instance-root",
            _parameter(node, "instance_root"),
        )
    )
    _append_option(command, node, "au_table_csv", "--au-table-csv")
    _append_option(command, node, "assignment_csv", "--assignment-csv")
    _append_option(command, node, "output_csv", "--output-csv")
    _append_option(command, node, "target_coverage", "--target-coverage")
    return tuple(command)


def _build_mkrf_managed_au_inputs_command(node: Any, _context: Any) -> tuple[str, ...]:
    command = list(
        _python_m_femic(
            "instance",
            "mkrf-build-managed-au-inputs",
            "--instance-root",
            _parameter(node, "instance_root"),
            "--resultant-gdb",
            _parameter(node, "resultant_gdb"),
        )
    )
    _append_option(command, node, "tipsy_rules_yaml", "--tipsy-rules-yaml")
    _append_option(command, node, "selected_au_csv", "--selected-au-csv")
    _append_option(command, node, "assignment_csv", "--assignment-csv")
    _append_option(command, node, "output_dir", "--output-dir")
    return tuple(command)


def _build_mkrf_managed_au_curves_command(node: Any, _context: Any) -> tuple[str, ...]:
    command = list(
        _python_m_femic(
            "instance",
            "mkrf-build-managed-au-curves",
            "--instance-root",
            _parameter(node, "instance_root"),
            "--run-id",
            _parameter(node, "run_id"),
        )
    )
    _append_option(command, node, "bootstrap_csv", "--bootstrap-csv")
    _append_option(command, node, "msyt_csv", "--msyt-csv")
    _append_option(command, node, "output_dir", "--output-dir")
    _append_option(command, node, "log_dir", "--log-dir")
    _append_option(command, node, "btc_executable", "--btc-executable")
    return tuple(command)


def _build_mkrf_init_runtime_package_command(
    node: Any, _context: Any
) -> tuple[str, ...]:
    command = list(
        _python_m_femic(
            "instance",
            "mkrf-init-runtime-package",
            "--instance-root",
            _parameter(node, "instance_root"),
        )
    )
    _append_option(command, node, "package_root", "--package-root")
    _append_option(command, node, "selected_au_csv", "--selected-au-csv")
    _append_option(
        command,
        node,
        "stand_origin_assignment_csv",
        "--stand-origin-assignment-csv",
    )
    _append_option(
        command, node, "stand_au_assignment_csv", "--stand-au-assignment-csv"
    )
    _append_option(command, node, "managed_bootstrap_csv", "--managed-bootstrap-csv")
    _append_option(
        command, node, "first_growth_curves_csv", "--first-growth-curves-csv"
    )
    _append_option(
        command,
        node,
        "first_growth_diagnostics_csv",
        "--first-growth-diagnostics-csv",
    )
    _append_option(command, node, "managed_curves_csv", "--managed-curves-csv")
    _append_option(
        command, node, "managed_run_manifest_json", "--managed-run-manifest-json"
    )
    _append_option(
        command,
        node,
        "bad_curve_audit_summary_csv",
        "--bad-curve-audit-summary-csv",
    )
    return tuple(command)


def _missing_key_diagnostics(
    *,
    diagnostic: Any,
    severity: Any,
    required: tuple[str, ...],
    actual: dict[str, Any],
    field_name: str,
    location: str,
) -> tuple[Any, ...]:
    return tuple(
        diagnostic(
            severity=severity.ERROR,
            code=f"femic.{field_name}.missing",
            message=(
                f"FEMIC node requires {field_name} key '{key}' for "
                "FreshForge validation, planning, and execution."
            ),
            location=f"{location}.{field_name}.{key}",
        )
        for key in required
        if key not in actual
    )


def _empty_parameter_diagnostics(
    *,
    diagnostic: Any,
    severity: Any,
    parameters: dict[str, Any],
    required: tuple[str, ...],
    location: str,
) -> tuple[Any, ...]:
    diagnostics: list[Any] = []
    for key in required:
        value = parameters.get(key)
        if isinstance(value, str) and not value.strip():
            diagnostics.append(
                diagnostic(
                    severity=severity.ERROR,
                    code="femic.parameters.empty",
                    message=f"FEMIC node parameter '{key}' must be nonempty.",
                    location=f"{location}.parameters.{key}",
                )
            )
    return tuple(diagnostics)
