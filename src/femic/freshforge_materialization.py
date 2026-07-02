"""FreshForge provider for FEMIC model-instance materialization workflows."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from femic import __version__

MATERIALIZATION_PROVIDER_ID = "femic.materialization"
MATERIALIZATION_PROVIDER_VERSION = __version__

CommandRunner = Callable[[tuple[str, ...]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class _NodeContract:
    id: str
    name: str
    description: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    parameters: tuple[str, ...] = ("overlay",)
    artifacts: tuple[str, ...] = ()


@dataclass(frozen=True)
class MaterializationOverlay:
    """Generic model-instance materialization overlay."""

    instance_root: Path
    venv_path: Path
    special_remote: str
    materialization_paths: tuple[Path, ...]
    audit_paths: tuple[Path, ...]
    report_path: Path
    submodule_path: Path | None = None
    install_requirements: tuple[Path, ...] = ()
    install_editable_paths: tuple[Path, ...] = ()
    install_extras: tuple[str, ...] = ()
    install_packages: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "instance_root": str(self.instance_root),
            "venv_path": str(self.venv_path),
            "special_remote": self.special_remote,
            "materialization_paths": [str(path) for path in self.materialization_paths],
            "audit_paths": [str(path) for path in self.audit_paths],
            "report_path": str(self.report_path),
            "install_requirements": [str(path) for path in self.install_requirements],
            "install_editable_paths": [
                str(path) for path in self.install_editable_paths
            ],
            "install_extras": list(self.install_extras),
            "install_packages": list(self.install_packages),
        }
        if self.submodule_path is not None:
            data["submodule_path"] = str(self.submodule_path)
        return data


_NODE_CONTRACTS: tuple[_NodeContract, ...] = (
    _NodeContract(
        id="check_toolchain",
        name="Check toolchain",
        description="Check Git, Python, FEMIC, FreshForge, DataLad, and git-annex.",
        outputs=("toolchain",),
    ),
    _NodeContract(
        id="check_python_environment",
        name="Check Python environment",
        description="Create or validate the configured Python virtual environment.",
        inputs=("toolchain",),
        outputs=("python_environment",),
    ),
    _NodeContract(
        id="install_packages",
        name="Install packages",
        description="Install configured FEMIC/FreshForge and instance packages.",
        inputs=("python_environment",),
        outputs=("packages",),
    ),
    _NodeContract(
        id="init_submodules",
        name="Initialize submodules",
        description="Initialize or update configured Git submodules.",
        inputs=("packages",),
        outputs=("submodules",),
    ),
    _NodeContract(
        id="init_annex",
        name="Initialize git-annex",
        description="Initialize git-annex in the configured instance repository.",
        inputs=("submodules",),
        outputs=("annex_repository",),
    ),
    _NodeContract(
        id="enable_special_remote",
        name="Enable special remote",
        description="Enable the configured git-annex special remote.",
        inputs=("annex_repository",),
        outputs=("special_remote",),
    ),
    _NodeContract(
        id="materialize_paths",
        name="Materialize required paths",
        description="Materialize configured DataLad/git-annex payload paths.",
        inputs=("special_remote",),
        outputs=("materialized_paths",),
    ),
    _NodeContract(
        id="audit_annex_availability",
        name="Audit annex availability",
        description="Audit configured payload families against the special remote.",
        inputs=("materialized_paths",),
        outputs=("annex_audit",),
    ),
    _NodeContract(
        id="write_materialization_report",
        name="Write materialization report",
        description="Write a deterministic user-facing materialization report.",
        outputs=("materialization_report",),
        artifacts=("report",),
    ),
)


class FemicMaterializationProvider:
    """FreshForge provider for generic FEMIC model-instance materialization."""

    def __init__(self, command_runner: CommandRunner | None = None) -> None:
        self._command_runner = command_runner or _default_command_runner

    def metadata(self) -> Any:
        """Return FreshForge provider metadata."""
        node_type_metadata, provider_metadata = _freshforge_metadata_types()
        return provider_metadata(
            id=MATERIALIZATION_PROVIDER_ID,
            version=MATERIALIZATION_PROVIDER_VERSION,
            name="FEMIC materialization provider",
            description=(
                "Provider for generic FEMIC model-instance bootstrap and "
                "DataLad/git-annex materialization workflows."
            ),
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
                for contract in _NODE_CONTRACTS
            ),
        )

    def validate_node(
        self, node: Any, node_type: Any, *, location: str
    ) -> tuple[Any, ...]:
        """Validate broad materialization node shape without executing commands."""
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
        overlay_path = _optional_parameter(node, "overlay")
        if overlay_path:
            overlay, overlay_errors = load_materialization_overlay(Path(overlay_path))
            diagnostics.extend(
                _overlay_diagnostics(
                    diagnostic=diagnostic,
                    severity=severity,
                    errors=overlay_errors,
                    location=f"{location}.parameters.overlay",
                )
            )
            if overlay is not None and node_type.id == "write_materialization_report":
                if not str(overlay.report_path).strip():
                    diagnostics.append(
                        diagnostic(
                            severity=severity.ERROR,
                            code="femic.materialization.overlay.report_missing",
                            message="Materialization overlay requires report.path.",
                            location=f"{location}.parameters.overlay",
                        )
                    )
        return tuple(diagnostics)

    def run_node(self, node: Any, node_type: Any, *, context: Any) -> Any:
        """Run one materialization node through the released FreshForge API."""
        result_type, run_status = _freshforge_run_result_types()
        diagnostic, severity = _freshforge_diagnostic_types()
        overlay, overlay_errors = load_materialization_overlay(
            Path(_parameter(node, "overlay"))
        )
        if overlay is None:
            return result_type(
                status=run_status.FAILED,
                diagnostics=tuple(
                    diagnostic(
                        severity=severity.ERROR,
                        code="femic.materialization.overlay.invalid",
                        message=error,
                        location=f"nodes.{node.id}.parameters.overlay",
                    )
                    for error in overlay_errors
                ),
            )
        if str(node_type.id) == "write_materialization_report":
            return _write_report_result(
                node=node,
                context=context,
                overlay=overlay,
                result_type=result_type,
                run_status=run_status,
            )

        commands = _commands_for_node(str(node_type.id), overlay)
        if commands is None:
            return result_type(
                status=run_status.FAILED,
                diagnostics=(
                    diagnostic(
                        severity=severity.ERROR,
                        code="femic.materialization.execution.unsupported",
                        message=(
                            "FEMIC materialization provider has no execution hook "
                            f"for node type '{node_type.id}'."
                        ),
                        location=f"nodes.{node.id}",
                    ),
                ),
            )
        completed = [self._command_runner(command) for command in commands]
        diagnostics = _command_diagnostics(
            completed=completed,
            diagnostic=diagnostic,
            severity=severity,
            node_id=node.id,
            node_type=str(node_type.id),
        )
        status = run_status.FAILED if diagnostics else run_status.SUCCESS
        return result_type(
            status=status,
            outputs=node.outputs if isinstance(node.outputs, dict) else {},
            artifacts=_resolved_artifacts(node, context),
            diagnostics=tuple(diagnostics),
            data={
                "commands": [list(command) for command in commands],
                "returncodes": [item.returncode for item in completed],
                "stdout": [item.stdout for item in completed if item.stdout],
                "stderr": [item.stderr for item in completed if item.stderr],
            },
        )


def provider_factory() -> FemicMaterializationProvider:
    """Return the FEMIC materialization provider for entry-point discovery."""
    return FemicMaterializationProvider()


def load_materialization_overlay(
    path: Path,
) -> tuple[MaterializationOverlay | None, tuple[str, ...]]:
    """Load and validate a materialization overlay YAML document."""
    if not path.exists():
        return None, (f"Materialization overlay does not exist: {path}",)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, (f"Could not read materialization overlay '{path}': {exc}",)
    if not isinstance(payload, Mapping):
        return None, ("Materialization overlay must be a mapping.",)

    errors: list[str] = []
    instance = _mapping(payload.get("instance"), "instance", errors)
    environment = _mapping(payload.get("environment"), "environment", errors)
    install = _mapping(payload.get("install"), "install", errors)
    annex = _mapping(payload.get("annex"), "annex", errors)
    materialization = _mapping(
        payload.get("materialization"), "materialization", errors
    )
    audit = _mapping(payload.get("audit"), "audit", errors)
    report = _mapping(payload.get("report"), "report", errors)
    if errors:
        return None, tuple(errors)

    instance_root = _required_path(instance, "root", "instance.root", errors)
    venv_path = _required_path(
        environment, "venv_path", "environment.venv_path", errors
    )
    special_remote = _required_str(
        annex, "special_remote", "annex.special_remote", errors
    )
    report_path = _required_path(report, "path", "report.path", errors)
    materialization_paths = _path_list(
        materialization, "required_paths", "materialization.required_paths", errors
    )
    audit_paths = _path_list(audit, "required_paths", "audit.required_paths", errors)
    if errors:
        return None, tuple(errors)

    install_requirements = _path_list(
        install, "requirements", "install.requirements", errors
    )
    install_editable_paths = _path_list(
        install, "editable_paths", "install.editable_paths", errors
    )
    install_extras = _str_list(install, "extras", "install.extras", errors)
    install_packages = _str_list(install, "packages", "install.packages", errors)
    if errors:
        return None, tuple(errors)

    return (
        MaterializationOverlay(
            instance_root=instance_root,
            submodule_path=_optional_path(instance.get("submodule_path")),
            venv_path=venv_path,
            special_remote=special_remote,
            materialization_paths=tuple(materialization_paths),
            audit_paths=tuple(audit_paths),
            report_path=report_path,
            install_requirements=tuple(install_requirements),
            install_editable_paths=tuple(install_editable_paths),
            install_extras=tuple(install_extras),
            install_packages=tuple(install_packages),
        ),
        (),
    )


def _commands_for_node(
    node_type_id: str,
    overlay: MaterializationOverlay,
) -> tuple[tuple[str, ...], ...] | None:
    builders: dict[
        str, Callable[[MaterializationOverlay], tuple[tuple[str, ...], ...]]
    ] = {
        "check_toolchain": _check_toolchain_commands,
        "check_python_environment": _python_environment_commands,
        "install_packages": _install_package_commands,
        "init_submodules": _init_submodule_commands,
        "init_annex": _init_annex_commands,
        "enable_special_remote": _enable_remote_commands,
        "materialize_paths": _materialize_path_commands,
        "audit_annex_availability": _audit_annex_commands,
    }
    builder = builders.get(node_type_id)
    return None if builder is None else builder(overlay)


def _check_toolchain_commands(
    _overlay: MaterializationOverlay,
) -> tuple[tuple[str, ...], ...]:
    return (
        ("git", "--version"),
        (sys.executable, "--version"),
        (sys.executable, "-m", "femic", "--help"),
        (sys.executable, "-m", "freshforge", "--version"),
        ("datalad", "--version"),
        ("git", "annex", "version"),
    )


def _python_environment_commands(
    overlay: MaterializationOverlay,
) -> tuple[tuple[str, ...], ...]:
    python = _venv_python(overlay.venv_path)
    if Path(python).exists():
        return ((python, "--version"),)
    return ((sys.executable, "-m", "venv", str(overlay.venv_path)),)


def _install_package_commands(
    overlay: MaterializationOverlay,
) -> tuple[tuple[str, ...], ...]:
    python = _venv_python(overlay.venv_path)
    commands: list[tuple[str, ...]] = []
    if overlay.install_extras:
        commands.append(
            (
                python,
                "-m",
                "pip",
                "install",
                "-e",
                f".[{','.join(overlay.install_extras)}]",
            )
        )
    for requirement in overlay.install_requirements:
        commands.append((python, "-m", "pip", "install", "-r", str(requirement)))
    for editable_path in overlay.install_editable_paths:
        commands.append((python, "-m", "pip", "install", "-e", str(editable_path)))
    for package in overlay.install_packages:
        commands.append((python, "-m", "pip", "install", package))
    return tuple(commands)


def _init_submodule_commands(
    overlay: MaterializationOverlay,
) -> tuple[tuple[str, ...], ...]:
    command = ["git", "submodule", "update", "--init", "--recursive"]
    if overlay.submodule_path is not None:
        command.append(str(overlay.submodule_path))
    return (tuple(command),)


def _init_annex_commands(
    overlay: MaterializationOverlay,
) -> tuple[tuple[str, ...], ...]:
    return (("git", "-C", str(overlay.instance_root), "annex", "init"),)


def _enable_remote_commands(
    overlay: MaterializationOverlay,
) -> tuple[tuple[str, ...], ...]:
    return (
        (
            "git",
            "-C",
            str(overlay.instance_root),
            "annex",
            "enableremote",
            overlay.special_remote,
        ),
    )


def _materialize_path_commands(
    overlay: MaterializationOverlay,
) -> tuple[tuple[str, ...], ...]:
    return tuple(
        ("datalad", "get", "-r", str(_instance_path(overlay, path)))
        for path in overlay.materialization_paths
    )


def _audit_annex_commands(
    overlay: MaterializationOverlay,
) -> tuple[tuple[str, ...], ...]:
    return tuple(
        (
            "git",
            "-C",
            str(overlay.instance_root),
            "annex",
            "find",
            "--not",
            "--in",
            overlay.special_remote,
            "--",
            str(path),
        )
        for path in overlay.audit_paths
    )


def _write_report_result(
    *,
    node: Any,
    context: Any,
    overlay: MaterializationOverlay,
    result_type: Any,
    run_status: Any,
) -> Any:
    report_path = _resolve_run_path(context, overlay.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "workflow_id": getattr(context, "workflow_id", None),
        "provider_id": MATERIALIZATION_PROVIDER_ID,
        "node_id": node.id,
        "overlay": overlay.to_dict(),
        "completed_outputs": getattr(context, "completed_outputs", {}),
        "completed_artifacts": getattr(context, "completed_artifacts", {}),
    }
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts = _resolved_artifacts(node, context)
    artifacts.setdefault("report", str(report_path))
    return result_type(
        status=run_status.SUCCESS,
        outputs=node.outputs if isinstance(node.outputs, dict) else {},
        artifacts=artifacts,
        data={"report_path": str(report_path)},
    )


def _command_diagnostics(
    *,
    completed: Sequence[subprocess.CompletedProcess[str]],
    diagnostic: Any,
    severity: Any,
    node_id: str,
    node_type: str,
) -> list[Any]:
    diagnostics: list[Any] = []
    for index, item in enumerate(completed, start=1):
        if item.returncode != 0:
            diagnostics.append(
                diagnostic(
                    severity=severity.ERROR,
                    code="femic.materialization.command.failed",
                    message=(
                        f"Materialization command {index} for node '{node_id}' "
                        f"exited with return code {item.returncode}."
                    ),
                    location=f"nodes.{node_id}",
                )
            )
        if node_type == "audit_annex_availability" and item.stdout.strip():
            diagnostics.append(
                diagnostic(
                    severity=severity.ERROR,
                    code="femic.materialization.audit.missing_remote_content",
                    message=(
                        "Annex audit found paths that are not present in the "
                        "configured special remote."
                    ),
                    location=f"nodes.{node_id}",
                )
            )
    return diagnostics


def _mapping(value: object, field_name: str, errors: list[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        errors.append(f"Materialization overlay requires mapping field '{field_name}'.")
        return {}
    return value


def _required_path(
    payload: Mapping[str, object],
    key: str,
    label: str,
    errors: list[str],
) -> Path:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"Materialization overlay requires nonempty '{label}'.")
        return Path("")
    return Path(value)


def _required_str(
    payload: Mapping[str, object],
    key: str,
    label: str,
    errors: list[str],
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"Materialization overlay requires nonempty '{label}'.")
        return ""
    return value


def _optional_path(value: object) -> Path | None:
    if isinstance(value, str) and value.strip():
        return Path(value)
    return None


def _path_list(
    payload: Mapping[str, object],
    key: str,
    label: str,
    errors: list[str],
) -> list[Path]:
    values = payload.get(key)
    if not isinstance(values, list):
        errors.append(f"Materialization overlay requires list field '{label}'.")
        return []
    paths: list[Path] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"Materialization overlay field '{label}[{index}]' is invalid."
            )
        else:
            paths.append(Path(value))
    return paths


def _str_list(
    payload: Mapping[str, object],
    key: str,
    label: str,
    errors: list[str],
) -> list[str]:
    values = payload.get(key, [])
    if not isinstance(values, list):
        errors.append(f"Materialization overlay field '{label}' must be a list.")
        return []
    strings: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"Materialization overlay field '{label}[{index}]' is invalid."
            )
        else:
            strings.append(value)
    return strings


def _overlay_diagnostics(
    *,
    diagnostic: Any,
    severity: Any,
    errors: Sequence[str],
    location: str,
) -> tuple[Any, ...]:
    return tuple(
        diagnostic(
            severity=severity.ERROR,
            code="femic.materialization.overlay.invalid",
            message=error,
            location=location,
        )
        for error in errors
    )


def _missing_key_diagnostics(
    *,
    diagnostic: Any,
    severity: Any,
    required: Sequence[str],
    actual: dict[str, object],
    field_name: str,
    location: str,
) -> list[Any]:
    diagnostics: list[Any] = []
    for key in required:
        if key not in actual:
            diagnostics.append(
                diagnostic(
                    severity=severity.ERROR,
                    code=f"femic.materialization.{field_name}.missing",
                    message=(
                        f"FEMIC materialization node requires {field_name} key '{key}'."
                    ),
                    location=f"{location}.{field_name}.{key}",
                )
            )
    return diagnostics


def _parameter(node: Any, key: str) -> str:
    value = node.parameters.get(key)
    if value is None:
        raise ValueError(f"FEMIC materialization node '{node.id}' requires '{key}'.")
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(
                f"FEMIC materialization node '{node.id}' parameter '{key}' "
                "must be nonempty."
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


def _venv_python(venv_path: Path) -> str:
    if sys.platform.startswith("win"):
        return str(venv_path / "Scripts" / "python.exe")
    return str(venv_path / "bin" / "python")


def _instance_path(overlay: MaterializationOverlay, path: Path) -> Path:
    return path if path.is_absolute() else overlay.instance_root / path


def _resolve_run_path(context: Any, path: Path) -> Path:
    resolve_path = getattr(context, "resolve_path", None)
    if callable(resolve_path):
        return Path(resolve_path(path))
    return path


def _resolved_artifacts(node: Any, context: Any) -> dict[str, Any]:
    artifacts = node.artifacts if isinstance(node.artifacts, dict) else {}
    resolved: dict[str, Any] = {}
    for key, value in artifacts.items():
        if isinstance(value, (str, Path)):
            resolved[key] = str(_resolve_run_path(context, Path(value)))
        else:
            resolved[key] = value
    return resolved


def _default_command_runner(
    command: tuple[str, ...],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
    )


def _freshforge_metadata_types() -> tuple[Any, Any]:
    try:
        from freshforge.providers import (  # type: ignore[import-untyped]
            NodeTypeMetadata,
            ProviderMetadata,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The FEMIC materialization provider requires the optional "
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
            "The FEMIC materialization provider requires the optional "
            "`femic[freshforge]` dependency."
        ) from exc
    return Diagnostic, DiagnosticSeverity


def _freshforge_run_result_types() -> tuple[Any, Any]:
    try:
        from freshforge.records import (  # type: ignore[import-untyped]
            ProviderRunResult,
            RunStatus,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The FEMIC materialization provider requires the optional "
            "`femic[freshforge]` dependency."
        ) from exc
    return ProviderRunResult, RunStatus
