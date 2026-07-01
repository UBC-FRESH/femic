from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from femic.freshforge import (
    FEMIC_PROVIDER_ID,
    FEMIC_MKRF_PROVIDER_ID,
    FemicFreshForgeProvider,
    FemicMkrfFreshForgeProvider,
    mkrf_provider_factory,
    provider_factory,
)

freshforge = pytest.importorskip("freshforge")


EXAMPLE_PATH = Path("examples/freshforge/model_build_workflow.yaml")
MKRF_WORKFLOW_PATH = Path(
    "external/femic-mkrf-instance/workflows/freshforge/mkrf_model_build_workflow.yaml"
)
EXPECTED_GENERIC_MODEL_BUILD_ORDER = [
    "validate_case",
    "geospatial_preflight",
    "compile_upstream",
    "btc_post_tipsy",
    "export_patchworks",
    "patchworks_preflight",
    "matrix_build",
]
EXPECTED_MKRF_MODEL_BUILD_ORDER = [
    "validate_case",
    "geospatial_preflight",
    "build_au_inputs",
    "select_aus",
    "build_managed_au_inputs",
    "build_managed_au_curves",
    "init_runtime_package",
    "patchworks_preflight",
    "matrix_build",
]


def _registry_with_femic_provider():
    from freshforge.providers import ProviderRegistry

    registry = ProviderRegistry()
    registry.register(provider_factory())
    registry.register(mkrf_provider_factory())
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
        "version": "0.1.0a1",
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


def test_mkrf_provider_metadata_serializes_deterministically() -> None:
    metadata = mkrf_provider_factory().metadata()

    assert metadata.id == FEMIC_MKRF_PROVIDER_ID
    assert [node_type.id for node_type in metadata.node_types] == [
        "build_au_inputs",
        "select_aus",
        "build_managed_au_inputs",
        "build_managed_au_curves",
        "init_runtime_package",
    ]
    assert metadata.to_dict()["node_types"][0]["parameters"] == [
        "instance_root",
        "resultant_gdb",
    ]


def test_pyproject_declares_freshforge_extra_and_entry_point() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    optional = pyproject["project"]["optional-dependencies"]
    assert any("freshforge" in item for item in optional["freshforge"])
    assert any("freshforge" in item for item in optional["dev"])
    entry_points = pyproject["project"]["entry-points"]["freshforge.providers"]
    assert entry_points["femic"] == "femic.freshforge:provider_factory"
    assert entry_points["femic_mkrf"] == "femic.freshforge:mkrf_provider_factory"


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
    assert registry.get("femic.mkrf") is not None


def test_generic_provider_execution_constructs_femic_command() -> None:
    from freshforge.records import ExecutionContext, WorkflowNode

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

    result = provider.execute_node(
        node,
        node_type,
        context=ExecutionContext(workflow_id="wf", run_id="run"),
    )

    assert result.diagnostics == ()
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


def test_mkrf_provider_execution_constructs_mkrf_command() -> None:
    from freshforge.records import ExecutionContext, WorkflowNode

    commands: list[tuple[str, ...]] = []
    provider = FemicMkrfFreshForgeProvider(command_runner=_successful_runner(commands))
    node_type = next(
        item for item in provider.metadata().node_types if item.id == "build_au_inputs"
    )
    node = WorkflowNode(
        id="build_au_inputs",
        provider="femic.mkrf.build_au_inputs",
        parameters={
            "instance_root": ".",
            "resultant_gdb": "data/source/03_MappingAnalysisData/Resultant.gdb",
        },
    )

    result = provider.execute_node(
        node,
        node_type,
        context=ExecutionContext(workflow_id="wf", run_id="run"),
    )

    assert result.diagnostics == ()
    assert commands == [
        (
            sys.executable,
            "-m",
            "femic",
            "instance",
            "mkrf-build-au-inputs",
            "--instance-root",
            ".",
            "--resultant-gdb",
            "data/source/03_MappingAnalysisData/Resultant.gdb",
        )
    ]


def test_provider_execution_failure_returns_freshforge_diagnostic() -> None:
    from freshforge.records import ExecutionContext, WorkflowNode

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

    result = provider.execute_node(
        node,
        node_type,
        context=ExecutionContext(workflow_id="wf", run_id="run"),
    )

    assert result.metadata["returncode"] == 9
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "femic.execution.command.failed"
    }


def test_mkrf_instance_workflow_validates_and_plans_when_available() -> None:
    if not MKRF_WORKFLOW_PATH.exists():
        pytest.skip("MKRF instance FreshForge workflow is not available")

    from freshforge.loading import load_workflow
    from freshforge.planning import create_run_plan
    from freshforge.validation import validate_workflow_with_providers

    spec, load_diagnostics = load_workflow(MKRF_WORKFLOW_PATH)
    assert spec is not None
    assert load_diagnostics == []
    assert spec.id == "mkrf_model_build"

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
    assert [node.id for node in plan.nodes] == EXPECTED_MKRF_MODEL_BUILD_ORDER
    assert {node.provider_id for node in plan.nodes} == {"femic", "femic.mkrf"}


def test_mkrf_instance_workflow_dry_run_when_available() -> None:
    if not MKRF_WORKFLOW_PATH.exists():
        pytest.skip("MKRF instance FreshForge workflow is not available")

    from freshforge.execution import execute_workflow
    from freshforge.loading import load_workflow

    spec, load_diagnostics = load_workflow(MKRF_WORKFLOW_PATH)
    assert spec is not None

    report = execute_workflow(
        spec,
        run_id="mkrf_freshforge_exec",
        diagnostics=load_diagnostics,
        registry=_registry_with_femic_provider(),
        dry_run=True,
    )

    assert not report.failed
    assert report.dry_run
    assert report.planned_order == tuple(EXPECTED_MKRF_MODEL_BUILD_ORDER)
