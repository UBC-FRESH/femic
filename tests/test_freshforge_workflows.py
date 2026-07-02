from __future__ import annotations

import builtins
import json
from pathlib import Path

from typer.testing import CliRunner

from femic.cli.main import app
from femic.freshforge_workflows import (
    FreshForgeWorkflowDiscoveryError,
    build_freshforge_command_block,
    discover_freshforge_workflows,
    suggest_freshforge_namespace,
)


runner = CliRunner()


def _write_workflow(path: Path, *, provider: str = "femic.validate_case") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "workflow:",
                "  id: fixture_workflow",
                "  name: Fixture workflow",
                "nodes:",
                "  - id: validate_case",
                f"    provider: {provider}",
                "    parameters:",
                "      instance_root: .",
                "      run_config: config/run_profile.fixture.yaml",
            ]
        ),
        encoding="utf-8",
    )


def test_discovery_finds_example_workflows() -> None:
    records = discover_freshforge_workflows(Path("."))
    paths = {record.path.as_posix() for record in records}

    assert "examples/freshforge/model_build_workflow.yaml" in paths
    assert "examples/freshforge/materialization_smoke_workflow.yaml" in paths
    assert all(record.to_dict()["path"] == record.path.as_posix() for record in records)


def test_discovery_finds_synthetic_external_workflow(tmp_path: Path) -> None:
    workflow_path = (
        tmp_path
        / "external"
        / "fixture-instance"
        / "workflows"
        / "freshforge"
        / "fixture_model_build_workflow.yaml"
    )
    _write_workflow(workflow_path)

    records = discover_freshforge_workflows(tmp_path)

    assert [record.path.as_posix() for record in records] == [
        "external/fixture-instance/workflows/freshforge/fixture_model_build_workflow.yaml"
    ]
    assert records[0].workflow_id == "fixture_workflow"
    assert records[0].kind == "model-build"
    assert records[0].provider_refs == ("femic.validate_case",)


def test_discovery_classifies_materialization_workflow(tmp_path: Path) -> None:
    workflow_path = (
        tmp_path
        / "external"
        / "fixture-instance"
        / "workflows"
        / "freshforge"
        / "fixture_materialization_workflow.yaml"
    )
    _write_workflow(
        workflow_path,
        provider="femic.materialization.check_toolchain",
    )

    records = discover_freshforge_workflows(tmp_path)

    assert records[0].kind == "materialization"


def test_discovery_reports_missing_freshforge(monkeypatch) -> None:
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "freshforge.loading":
            raise ImportError("missing freshforge")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        discover_freshforge_workflows(Path("."))
    except FreshForgeWorkflowDiscoveryError as exc:
        assert "femic[freshforge]" in str(exc)
    else:  # pragma: no cover - guards against a false-positive test.
        raise AssertionError("expected FreshForgeWorkflowDiscoveryError")


def test_namespace_suggestion_is_filename_driven() -> None:
    assert (
        suggest_freshforge_namespace(
            "external/example/workflows/freshforge/foo_model_build_workflow.yaml"
        )
        == "foo/model-build"
    )
    assert (
        suggest_freshforge_namespace(
            "external/example/workflows/freshforge/foo_materialization_workflow.yaml"
        )
        == "foo/materialization"
    )


def test_command_block_uses_released_freshforge_cli_shape() -> None:
    commands = build_freshforge_command_block(
        Path("examples/freshforge/materialization_smoke_workflow.yaml")
    )

    assert commands == (
        "freshforge validate examples/freshforge/materialization_smoke_workflow.yaml",
        "freshforge inspect examples/freshforge/materialization_smoke_workflow.yaml",
        "freshforge plan examples/freshforge/materialization_smoke_workflow.yaml",
        (
            "freshforge run examples/freshforge/materialization_smoke_workflow.yaml "
            "--workdir runtime/freshforge --namespace materialization/smoke --json"
        ),
    )


def test_command_block_rejects_missing_workflow() -> None:
    try:
        build_freshforge_command_block(Path("missing.yaml"))
    except FreshForgeWorkflowDiscoveryError as exc:
        assert "not found" in str(exc)
    else:  # pragma: no cover - guards against a false-positive test.
        raise AssertionError("expected FreshForgeWorkflowDiscoveryError")


def test_cli_workflow_list_json() -> None:
    result = runner.invoke(app, ["freshforge", "workflows", "list", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    paths = {item["path"] for item in payload}
    assert "examples/freshforge/model_build_workflow.yaml" in paths


def test_cli_workflow_commands() -> None:
    result = runner.invoke(
        app,
        [
            "freshforge",
            "workflows",
            "commands",
            "examples/freshforge/materialization_smoke_workflow.yaml",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (
        "freshforge validate examples/freshforge/materialization_smoke_workflow.yaml"
        in result.output
    )
    assert "--workdir runtime/freshforge" in result.output
    assert "--namespace materialization/smoke" in result.output
    assert "--json" in result.output


def test_cli_workflow_commands_rejects_missing_path() -> None:
    result = runner.invoke(
        app,
        ["freshforge", "workflows", "commands", "missing.yaml"],
    )

    assert result.exit_code == 1
    assert "not found" in result.output
