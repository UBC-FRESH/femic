from __future__ import annotations

import subprocess
import sys
import tomllib
import json
from pathlib import Path

import pytest
import yaml

import femic
from femic.freshforge import (
    FEMIC_PROVIDER_ID,
    FemicFreshForgeProvider,
    provider_factory,
)

freshforge = pytest.importorskip("freshforge")


EXAMPLE_PATH = Path("examples/freshforge/model_build_workflow.yaml")
EXPECTED_GENERIC_MODEL_BUILD_ORDER = [
    "validate_case",
    "geospatial_preflight",
    "compile_upstream",
    "btc_post_tipsy",
    "export_patchworks",
    "patchworks_preflight",
    "matrix_build",
]


def _registry_with_femic_provider():
    from freshforge.providers import ProviderRegistry

    registry = ProviderRegistry()
    registry.register(provider_factory())
    return registry


def _successful_runner(commands: list[tuple[str, ...]]):
    def _run(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=0,
            stdout="ok",
            stderr="",
        )

    return _run


def _example_document() -> dict[str, object]:
    return yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_provider_metadata_serializes_deterministically() -> None:
    metadata = provider_factory().metadata()

    assert metadata.to_dict() == {
        "id": "femic",
        "version": femic.__version__,
        "node_types": [
            {
                "id": "validate_case",
                "inputs": [],
                "outputs": ["case_validation"],
                "parameters": ["instance_root", "run_config"],
                "artifacts": [],
                "name": "Validate FEMIC case",
                "description": "Declare the FEMIC case-aware preflight seam.",
            },
            {
                "id": "geospatial_preflight",
                "inputs": ["case_validation"],
                "outputs": ["geospatial_runtime"],
                "parameters": ["instance_root"],
                "artifacts": [],
                "name": "Geospatial preflight",
                "description": (
                    "Declare the generic geospatial runtime preflight seam."
                ),
            },
            {
                "id": "compile_upstream",
                "inputs": ["geospatial_runtime"],
                "outputs": ["btc_handoff"],
                "parameters": ["instance_root", "run_config", "run_id"],
                "artifacts": ["run_manifest"],
                "name": "Compile upstream model inputs",
                "description": (
                    "Declare FEMIC Stage 00 and Stage 01a upstream compilation."
                ),
            },
            {
                "id": "accepted_btc_handoff",
                "inputs": ["geospatial_runtime"],
                "outputs": ["btc_handoff"],
                "parameters": [
                    "instance_root",
                    "btc_input",
                    "btc_output",
                    "treated_curves",
                ],
                "artifacts": ["btc_input", "btc_output", "treated_curves"],
                "name": "Accepted BTC handoff",
                "description": "Declare an accepted BTC input/output handoff preflight.",
            },
            {
                "id": "btc_post_tipsy",
                "inputs": ["btc_handoff"],
                "outputs": ["model_input_bundle"],
                "parameters": ["instance_root", "run_config", "tsa", "run_id"],
                "artifacts": ["btc_manifest", "post_tipsy_manifest"],
                "name": "BTC and post-TIPSY bundle",
                "description": (
                    "Declare the unattended BTC and Stage 01b bundle seam."
                ),
            },
            {
                "id": "export_patchworks",
                "inputs": ["model_input_bundle"],
                "outputs": ["patchworks_package"],
                "parameters": ["instance_root", "run_config", "tsa"],
                "artifacts": ["forestmodel_xml", "fragments"],
                "name": "Export Patchworks package",
                "description": (
                    "Declare the FEMIC Patchworks model-package export seam."
                ),
            },
            {
                "id": "patchworks_preflight",
                "inputs": ["patchworks_package"],
                "outputs": ["patchworks_runtime"],
                "parameters": ["instance_root", "patchworks_config"],
                "artifacts": [],
                "name": "Patchworks preflight",
                "description": "Declare Patchworks runtime/config preflight.",
            },
            {
                "id": "matrix_build",
                "inputs": ["patchworks_runtime"],
                "outputs": ["compiled_patchworks_model"],
                "parameters": ["instance_root", "patchworks_config", "run_id"],
                "artifacts": ["matrix_build_manifest"],
                "name": "Patchworks matrix build",
                "description": "Declare Patchworks matrix-builder compilation.",
            },
        ],
        "name": "FEMIC model-build provider",
        "description": (
            "Provider for FEMIC model-build workflow validation, planning, "
            "and explicit execution."
        ),
    }


def test_provider_factory_returns_femic_provider() -> None:
    assert provider_factory().metadata().id == FEMIC_PROVIDER_ID


def test_pyproject_declares_freshforge_extra_and_entry_point() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    optional = pyproject["project"]["optional-dependencies"]
    assert "freshforge" in optional
    assert optional["freshforge"] == ["freshforge==0.1.0a5"]
    assert all("git+" not in item for deps in optional.values() for item in deps)
    entry_points = pyproject["project"]["entry-points"]["freshforge.providers"]
    assert entry_points["femic"] == "femic.freshforge:provider_factory"
    assert (
        entry_points["femic.materialization"]
        == "femic.freshforge_materialization:provider_factory"
    )
    assert "femic_mkrf" not in entry_points


def test_femic_import_does_not_import_freshforge_eagerly() -> None:
    script = "import sys; import femic; print('freshforge' in sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "False"


def test_example_workflow_is_generic_and_public_safe() -> None:
    document = _example_document()

    assert document["workflow"]["id"] == "femic_model_build_example"
    assert "k3z" not in yaml.safe_dump(document).lower()


def test_example_workflow_validates_and_plans() -> None:
    from freshforge.loading import load_workflow
    from freshforge.planning import create_run_plan
    from freshforge.validation import validate_workflow_with_providers

    spec, load_diagnostics = load_workflow(EXAMPLE_PATH)
    assert spec is not None
    assert load_diagnostics == []

    diagnostics = validate_workflow_with_providers(
        spec,
        registry=_registry_with_femic_provider(),
        structural_diagnostics=load_diagnostics,
    )
    assert diagnostics == []

    plan = create_run_plan(
        spec,
        diagnostics=diagnostics,
        registry=_registry_with_femic_provider(),
    )
    assert not plan.has_errors
    assert [node.id for node in plan.nodes] == EXPECTED_GENERIC_MODEL_BUILD_ORDER
    assert {node.provider_id for node in plan.nodes} == {"femic"}
    assert [node.node_type for node in plan.nodes] == EXPECTED_GENERIC_MODEL_BUILD_ORDER


def test_missing_required_parameter_returns_provider_diagnostic() -> None:
    from freshforge.validation import validate_workflow_document
    from freshforge.validation import validate_workflow_with_providers

    document = _example_document()
    del document["nodes"][0]["parameters"]["run_config"]
    spec, structural = validate_workflow_document(document)

    assert spec is not None
    diagnostics = validate_workflow_with_providers(
        spec,
        registry=_registry_with_femic_provider(),
        structural_diagnostics=structural,
    )

    assert {diagnostic.code for diagnostic in diagnostics} == {
        "femic.parameters.missing"
    }
    assert diagnostics[0].location == "nodes[0].parameters.run_config"


def test_unknown_femic_node_type_fails_provider_validation() -> None:
    from freshforge.validation import validate_workflow_document
    from freshforge.validation import validate_workflow_with_providers

    document = _example_document()
    document["nodes"][0]["provider"] = "femic.not_a_stage"
    spec, structural = validate_workflow_document(document)

    assert spec is not None
    diagnostics = validate_workflow_with_providers(
        spec,
        registry=_registry_with_femic_provider(),
        structural_diagnostics=structural,
    )

    assert {diagnostic.code for diagnostic in diagnostics} == {
        "node.provider.node_type.unknown"
    }


def test_default_freshforge_registry_discovers_installed_femic_provider() -> None:
    from freshforge.providers import default_provider_registry

    registry, diagnostics = default_provider_registry()

    assert not diagnostics
    assert registry.get("femic") is not None
    assert registry.get("femic.materialization") is not None
    assert registry.get("femic.mkrf") is None


def test_generic_provider_execution_constructs_femic_command() -> None:
    from freshforge.execution import RunContext
    from freshforge.records import RunStatus, WorkflowNode

    commands: list[tuple[str, ...]] = []
    provider = FemicFreshForgeProvider(command_runner=_successful_runner(commands))
    node_type = next(
        item for item in provider.metadata().node_types if item.id == "validate_case"
    )
    node = WorkflowNode(
        id="validate_case",
        provider="femic.validate_case",
        parameters={
            "instance_root": ".",
            "run_config": "config/run_profile.mkrf.yaml",
        },
    )

    result = provider.run_node(
        node,
        node_type,
        context=RunContext(workflow_id="wf", workdir=Path(".")),
    )

    assert result.status is RunStatus.SUCCESS
    assert result.diagnostics == ()
    assert result.data["returncode"] == 0
    assert result.outputs == {}
    assert commands == [
        (
            sys.executable,
            "-m",
            "femic",
            "prep",
            "validate-case",
            "--instance-root",
            ".",
            "--run-config",
            "config/run_profile.mkrf.yaml",
        )
    ]


def test_provider_run_resolves_relative_artifacts_under_workdir(tmp_path: Path) -> None:
    from freshforge.execution import RunContext
    from freshforge.records import WorkflowNode

    commands: list[tuple[str, ...]] = []
    provider = FemicFreshForgeProvider(command_runner=_successful_runner(commands))
    node_type = next(
        item for item in provider.metadata().node_types if item.id == "validate_case"
    )
    node = WorkflowNode(
        id="validate_case",
        provider="femic.validate_case",
        parameters={
            "instance_root": ".",
            "run_config": "config/run_profile.example.yaml",
        },
        artifacts={"run_manifest": "runtime/logs/a.json"},
    )

    result = provider.run_node(
        node,
        node_type,
        context=RunContext(workflow_id="wf", workdir=tmp_path),
    )

    assert result.artifacts == {
        "run_manifest": str(tmp_path / "runtime" / "logs" / "a.json")
    }
    assert commands == [
        (
            sys.executable,
            "-m",
            "femic",
            "prep",
            "validate-case",
            "--instance-root",
            ".",
            "--run-config",
            "config/run_profile.example.yaml",
        )
    ]


def test_provider_run_resolves_relative_artifacts_under_namespace(
    tmp_path: Path,
) -> None:
    from freshforge.execution import RunContext
    from freshforge.records import WorkflowNode

    provider = FemicFreshForgeProvider(command_runner=_successful_runner([]))
    node_type = next(
        item for item in provider.metadata().node_types if item.id == "validate_case"
    )
    node = WorkflowNode(
        id="validate_case",
        provider="femic.validate_case",
        parameters={
            "instance_root": ".",
            "run_config": "config/run_profile.example.yaml",
        },
        artifacts={"run_manifest": "runtime/logs/a.json"},
    )

    result = provider.run_node(
        node,
        node_type,
        context=RunContext(workflow_id="wf", workdir=tmp_path, run_namespace="smoke"),
    )

    assert result.artifacts == {
        "run_manifest": str(tmp_path / "smoke" / "runtime" / "logs" / "a.json")
    }


def test_provider_run_preserves_absolute_artifact_paths(tmp_path: Path) -> None:
    from freshforge.execution import RunContext
    from freshforge.records import WorkflowNode

    absolute_artifact = tmp_path / "absolute" / "a.json"
    provider = FemicFreshForgeProvider(command_runner=_successful_runner([]))
    node_type = next(
        item for item in provider.metadata().node_types if item.id == "validate_case"
    )
    node = WorkflowNode(
        id="validate_case",
        provider="femic.validate_case",
        parameters={
            "instance_root": ".",
            "run_config": "config/run_profile.example.yaml",
        },
        artifacts={"run_manifest": absolute_artifact},
    )

    result = provider.run_node(
        node,
        node_type,
        context=RunContext(workflow_id="wf", workdir=tmp_path, run_namespace="smoke"),
    )

    assert result.artifacts == {"run_manifest": str(absolute_artifact)}


def test_provider_run_preserves_json_safe_non_string_artifact_metadata(
    tmp_path: Path,
) -> None:
    from freshforge.execution import RunContext
    from freshforge.records import WorkflowNode

    provider = FemicFreshForgeProvider(command_runner=_successful_runner([]))
    node_type = next(
        item for item in provider.metadata().node_types if item.id == "validate_case"
    )
    node = WorkflowNode(
        id="validate_case",
        provider="femic.validate_case",
        parameters={
            "instance_root": ".",
            "run_config": "config/run_profile.example.yaml",
        },
        artifacts={
            "run_manifest": "runtime/logs/a.json",
            "count": 3,
            "metadata": {"kind": "declared"},
        },
    )

    result = provider.run_node(
        node,
        node_type,
        context=RunContext(workflow_id="wf", workdir=tmp_path, run_namespace="smoke"),
    )

    assert result.artifacts["run_manifest"] == str(
        tmp_path / "smoke" / "runtime" / "logs" / "a.json"
    )
    assert result.artifacts["count"] == 3
    assert result.artifacts["metadata"] == {"kind": "declared"}
    json.dumps(result.to_dict())


def test_legacy_execute_node_shim_delegates_to_run_node() -> None:
    from freshforge.execution import RunContext
    from freshforge.records import RunStatus, WorkflowNode

    commands: list[tuple[str, ...]] = []
    provider = FemicFreshForgeProvider(command_runner=_successful_runner(commands))
    node_type = next(
        item
        for item in provider.metadata().node_types
        if item.id == "geospatial_preflight"
    )
    node = WorkflowNode(
        id="geospatial_preflight",
        provider="femic.geospatial_preflight",
        parameters={"instance_root": "."},
    )

    result = provider.execute_node(
        node,
        node_type,
        context=RunContext(workflow_id="wf", workdir=Path(".")),
    )

    assert result.status is RunStatus.SUCCESS
    assert commands == [(sys.executable, "-m", "femic", "prep", "geospatial-preflight")]


def test_accepted_btc_handoff_execution_constructs_preflight_command() -> None:
    from freshforge.execution import RunContext
    from freshforge.records import RunStatus, WorkflowNode

    commands: list[tuple[str, ...]] = []
    provider = FemicFreshForgeProvider(command_runner=_successful_runner(commands))
    node_type = next(
        item
        for item in provider.metadata().node_types
        if item.id == "accepted_btc_handoff"
    )
    node = WorkflowNode(
        id="accepted_btc_handoff",
        provider="femic.accepted_btc_handoff",
        parameters={
            "instance_root": "external/femic-example-instance",
            "btc_input": "data/03_input-example.csv",
            "btc_output": "data/04_output-example.csv",
            "treated_curves": "planning/example_treated_curves.csv",
            "btc_error": "data/04_error-example.csv",
            "treated_curve_diagnostics": "planning/example_curve_diagnostics.csv",
            "tipsy_parameter_crosswalk": "planning/example_parameter_crosswalk.csv",
            "curve_id_map": "planning/example_curve_id_map.csv",
        },
    )

    result = provider.run_node(
        node,
        node_type,
        context=RunContext(workflow_id="wf", workdir=Path(".")),
    )

    assert result.status is RunStatus.SUCCESS
    assert commands == [
        (
            sys.executable,
            "-m",
            "femic",
            "prep",
            "accepted-btc-handoff",
            "--instance-root",
            "external/femic-example-instance",
            "--btc-input",
            "data/03_input-example.csv",
            "--btc-output",
            "data/04_output-example.csv",
            "--treated-curves",
            "planning/example_treated_curves.csv",
            "--btc-error",
            "data/04_error-example.csv",
            "--treated-curve-diagnostics",
            "planning/example_curve_diagnostics.csv",
            "--tipsy-parameter-crosswalk",
            "planning/example_parameter_crosswalk.csv",
            "--curve-id-map",
            "planning/example_curve_id_map.csv",
        )
    ]


def test_provider_execution_failure_returns_freshforge_diagnostic() -> None:
    from freshforge.execution import RunContext
    from freshforge.records import RunStatus, WorkflowNode

    def _failing_runner(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=9,
            stdout="",
            stderr="failed",
        )

    provider = FemicFreshForgeProvider(command_runner=_failing_runner)
    node_type = next(
        item for item in provider.metadata().node_types if item.id == "matrix_build"
    )
    node = WorkflowNode(
        id="matrix_build",
        provider="femic.matrix_build",
        parameters={
            "instance_root": ".",
            "patchworks_config": "config/patchworks.runtime.mkrf_rebuild.windows.yaml",
            "run_id": "mkrf_freshforge_exec",
        },
    )

    result = provider.run_node(
        node,
        node_type,
        context=RunContext(workflow_id="wf", workdir=Path(".")),
    )

    assert result.status is RunStatus.FAILED
    assert result.data["returncode"] == 9
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "femic.execution.command.failed"
    }
