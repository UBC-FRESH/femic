from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import femic
from femic.freshforge_materialization import (
    MATERIALIZATION_PROVIDER_ID,
    FemicMaterializationProvider,
    load_materialization_overlay,
    provider_factory,
)

freshforge = pytest.importorskip("freshforge")

OVERLAY_PATH = Path("examples/freshforge/materialization_overlay.yaml")
WORKFLOW_PATH = Path("examples/freshforge/materialization_smoke_workflow.yaml")
COMMAND_NODE_TYPES = (
    "check_toolchain",
    "check_python_environment",
    "install_packages",
    "init_submodules",
    "init_annex",
    "enable_special_remote",
    "materialize_paths",
    "audit_annex_availability",
)


def _successful_runner(commands: list[tuple[str, ...]]):
    def _run(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=0,
            stdout="",
            stderr="",
        )

    return _run


def _failing_runner(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=list(command),
        returncode=7,
        stdout="",
        stderr="failed",
    )


def _audit_missing_runner(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=list(command),
        returncode=0,
        stdout="models/missing.bin\n",
        stderr="",
    )


def _workflow_node(node_type_id: str, *, overlay: str | None = None):
    from freshforge.records import WorkflowNode

    output_key_by_node_type = {
        "check_toolchain": "toolchain",
        "check_python_environment": "python_environment",
        "install_packages": "packages",
        "init_submodules": "submodules",
        "init_annex": "annex_repository",
        "enable_special_remote": "special_remote",
        "materialize_paths": "materialized_paths",
        "audit_annex_availability": "annex_audit",
        "write_materialization_report": "materialization_report",
    }
    return WorkflowNode(
        id=node_type_id,
        provider=f"femic.materialization.{node_type_id}",
        outputs={output_key_by_node_type[node_type_id]: "ok"},
        parameters={"overlay": overlay or str(OVERLAY_PATH)},
        artifacts=(
            {"report": "runtime/freshforge/materialization_report.json"}
            if node_type_id == "write_materialization_report"
            else {}
        ),
    )


def _node_type(provider: FemicMaterializationProvider, node_type_id: str):
    return next(
        item for item in provider.metadata().node_types if item.id == node_type_id
    )


def test_materialization_provider_metadata_serializes_deterministically() -> None:
    metadata = provider_factory().metadata()

    payload = metadata.to_dict()
    assert payload["id"] == MATERIALIZATION_PROVIDER_ID
    assert payload["version"] == femic.__version__
    assert [item["id"] for item in payload["node_types"]] == [
        "check_toolchain",
        "check_python_environment",
        "install_packages",
        "init_submodules",
        "init_annex",
        "enable_special_remote",
        "materialize_paths",
        "audit_annex_availability",
        "write_materialization_report",
    ]
    assert all(item["parameters"] == ["overlay"] for item in payload["node_types"])


def test_pyproject_declares_materialization_provider_entry_point() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    entry_points = pyproject["project"]["entry-points"]["freshforge.providers"]

    assert entry_points["femic"] == "femic.freshforge:provider_factory"
    assert (
        entry_points["femic.materialization"]
        == "femic.freshforge_materialization:provider_factory"
    )


def test_overlay_parser_accepts_public_safe_fixture() -> None:
    overlay, diagnostics = load_materialization_overlay(OVERLAY_PATH)

    assert diagnostics == ()
    assert overlay is not None
    assert overlay.instance_root == Path("examples/freshforge/fixture-instance")
    assert overlay.special_remote == "arbutus-s3"
    assert overlay.materialization_paths == (Path("data"), Path("models"))
    assert overlay.audit_paths == (Path("data"), Path("models"))


def test_overlay_parser_reports_missing_required_fields(tmp_path: Path) -> None:
    overlay_path = tmp_path / "bad_overlay.yaml"
    overlay_path.write_text("instance: {}\n", encoding="utf-8")

    overlay, diagnostics = load_materialization_overlay(overlay_path)

    assert overlay is None
    assert any("environment" in message for message in diagnostics)
    assert any("annex" in message for message in diagnostics)


def test_provider_validation_reports_missing_overlay_parameter() -> None:
    provider = provider_factory()
    node_type = _node_type(provider, "check_toolchain")
    node = _workflow_node("check_toolchain")
    node = type(node)(
        id=node.id,
        provider=node.provider,
        outputs=node.outputs,
        parameters={},
    )

    diagnostics = provider.validate_node(node, node_type, location="nodes.0")

    assert {diagnostic.code for diagnostic in diagnostics} == {
        "femic.materialization.parameters.missing"
    }


def test_provider_validation_reports_bad_overlay_path() -> None:
    provider = provider_factory()
    node_type = _node_type(provider, "check_toolchain")
    node = _workflow_node("check_toolchain", overlay="missing.yaml")

    diagnostics = provider.validate_node(node, node_type, location="nodes.0")

    assert any(
        diagnostic.code == "femic.materialization.overlay.invalid"
        for diagnostic in diagnostics
    )


@pytest.mark.parametrize("node_type_id", COMMAND_NODE_TYPES)
def test_materialization_command_nodes_use_mocked_runner(
    node_type_id: str,
    tmp_path: Path,
) -> None:
    from freshforge.execution import RunContext
    from freshforge.records import RunStatus

    commands: list[tuple[str, ...]] = []
    provider = FemicMaterializationProvider(command_runner=_successful_runner(commands))
    node = _workflow_node(node_type_id)

    result = provider.run_node(
        node,
        _node_type(provider, node_type_id),
        context=RunContext(workflow_id="wf", workdir=tmp_path),
    )

    assert result.status is RunStatus.SUCCESS
    assert commands
    assert result.data["commands"] == [list(command) for command in commands]


def test_materialization_command_failure_returns_diagnostic(tmp_path: Path) -> None:
    from freshforge.execution import RunContext
    from freshforge.records import RunStatus

    provider = FemicMaterializationProvider(command_runner=_failing_runner)
    node = _workflow_node("init_annex")

    result = provider.run_node(
        node,
        _node_type(provider, "init_annex"),
        context=RunContext(workflow_id="wf", workdir=tmp_path),
    )

    assert result.status is RunStatus.FAILED
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "femic.materialization.command.failed"
    }


def test_annex_audit_stdout_is_failure_even_with_zero_returncode(
    tmp_path: Path,
) -> None:
    from freshforge.execution import RunContext
    from freshforge.records import RunStatus

    provider = FemicMaterializationProvider(command_runner=_audit_missing_runner)
    node = _workflow_node("audit_annex_availability")

    result = provider.run_node(
        node,
        _node_type(provider, "audit_annex_availability"),
        context=RunContext(workflow_id="wf", workdir=tmp_path),
    )

    assert result.status is RunStatus.FAILED
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "femic.materialization.audit.missing_remote_content"
    }


def test_write_report_node_resolves_namespace_artifact(tmp_path: Path) -> None:
    from freshforge.execution import RunContext
    from freshforge.records import RunStatus

    provider = provider_factory()
    node = _workflow_node("write_materialization_report")

    result = provider.run_node(
        node,
        _node_type(provider, "write_materialization_report"),
        context=RunContext(
            workflow_id="wf",
            workdir=tmp_path,
            run_namespace="smoke",
            completed_outputs={"check": {"ok": True}},
        ),
    )

    report_path = (
        tmp_path / "smoke" / "runtime" / "freshforge" / ("materialization_report.json")
    )
    assert result.status is RunStatus.SUCCESS
    assert result.artifacts["report"] == str(
        tmp_path / "smoke" / "runtime" / "freshforge" / "materialization_report.json"
    )
    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["provider_id"] == MATERIALIZATION_PROVIDER_ID
    assert payload["completed_outputs"] == {"check": {"ok": True}}


def test_materialization_fixture_workflow_validates_and_plans() -> None:
    from freshforge.loading import load_workflow
    from freshforge.planning import create_run_plan
    from freshforge.validation import validate_workflow_with_providers

    spec, diagnostics = load_workflow(WORKFLOW_PATH)
    assert spec is not None
    diagnostics = validate_workflow_with_providers(
        spec,
        structural_diagnostics=diagnostics,
    )
    plan = create_run_plan(spec, diagnostics=diagnostics)

    assert not plan.has_errors
    assert [node.id for node in plan.nodes] == ["write_materialization_report"]


def test_materialization_fixture_cli_run_writes_report(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "freshforge",
            "run",
            str(WORKFLOW_PATH),
            "--workdir",
            str(tmp_path),
            "--namespace",
            "smoke",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["summary"]["succeeded_count"] == 1
    assert (
        tmp_path / "smoke" / "runtime" / "freshforge" / "materialization_report.json"
    ).exists()
