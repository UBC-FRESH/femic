from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from femic import named_pipelines


def test_load_named_pipeline_registry_includes_builtin_tsr_thlb_strict() -> None:
    registry = named_pipelines.load_named_pipeline_registry()

    pipeline = registry.get_pipeline("tsr.thlb_strict")

    assert pipeline.label == "TSR strict THLB product lane"
    assert pipeline.get_seam("scratch").start_mode == "scratch"
    assert pipeline.get_seam("glb").checkpoint_path == Path(
        "data/tsr/glb_checkpoint.feather"
    )
    assert pipeline.get_seam("aflb_yield_ready").checkpoint_path == Path(
        "data/tsr/aflb_yield_ready_checkpoint.feather"
    )
    assert pipeline.get_recipe("tsr_thlb_netdown").default_recipe_path == Path(
        "config/tsr/thlb_netdown.recipe.yaml"
    )


def test_load_named_pipeline_registry_explicit_overlay_can_override_builtin(
    tmp_path: Path,
) -> None:
    overlay_path = tmp_path / "pipelines.yaml"
    overlay_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "registry_kind: pipeline_registry",
                "pipelines:",
                "  - pipeline_id: tsr.thlb_strict",
                '    label: "Overridden proof lane"',
                "    kind: tsr",
                '    summary: "Override."',
                "    seams:",
                "      - seam_id: scratch",
                "        start_mode: scratch",
                "      - seam_id: aflb",
                "        checkpoint_path: data/tsr/custom_aflb.feather",
                "    recipes:",
                "      - recipe_id: tsr.thlb_netdown",
                "        recipe_kind: tsr_thlb_netdown",
                "        default_recipe_path: config/tsr/custom.recipe.yaml",
                "",
            ]
        ),
        encoding="utf-8",
    )

    registry = named_pipelines.load_named_pipeline_registry(
        explicit_registry_paths=(overlay_path,)
    )

    pipeline = registry.get_pipeline("tsr.thlb_strict")
    assert pipeline.label == "Overridden proof lane"
    assert pipeline.source_kind == "explicit"
    assert pipeline.registry_path == overlay_path.resolve()
    assert pipeline.get_seam("aflb").checkpoint_path == Path(
        "data/tsr/custom_aflb.feather"
    )


def test_build_named_pipeline_execution_plan_resolves_runbook_and_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance_root = tmp_path / "instance"
    (instance_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "data" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "runbooks" / "pipelines").mkdir(parents=True, exist_ok=True)
    (instance_root / "config" / "run_profile.tsa29.yaml").write_text(
        "selection:\n  tsa:\n    - '29'\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "overlay.yaml").write_text(
        "schema_version: 1\n",
        encoding="utf-8",
    )
    thlb_recipe_path = instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml"
    thlb_recipe_path.write_text("schema_version: 1\n", encoding="utf-8")
    source_layers_recipe_path = (
        instance_root / "config" / "tsr" / "source_layers.recipe.yaml"
    )
    source_layers_recipe_path.write_text("schema_version: 1\n", encoding="utf-8")
    checkpoint_path = (
        instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather"
    )
    checkpoint_path.write_text("checkpoint\n", encoding="utf-8")
    runbook_path = instance_root / "runbooks" / "pipelines" / "tsa29.yaml"
    runbook_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "runbook_kind: femic_pipeline_runbook",
                'label: "TSA29 proof lane"',
                "pipeline_id: tsr.thlb_strict",
                "instance_root: .",
                "run_profile: config/run_profile.tsa29.yaml",
                "overlay_paths:",
                "  - config/tsr/overlay.yaml",
                "restart:",
                "  seam_id: aflb_yield_ready",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        named_pipelines,
        "load_tsr_thlb_netdown_recipe",
        lambda path: SimpleNamespace(
            instance_inputs=SimpleNamespace(
                source_layer_recipe_path="config/tsr/source_layers.recipe.yaml"
            )
        ),
    )

    plan = named_pipelines.build_named_pipeline_execution_plan(
        runbook_path=runbook_path,
        instance_root=instance_root,
    )

    assert plan.instance_root == instance_root.resolve()
    assert plan.pipeline_id == "tsr.thlb_strict"
    assert plan.seam_id == "aflb_yield_ready"
    assert plan.checkpoint_path == checkpoint_path.resolve()
    assert (
        plan.run_profile_path
        == (instance_root / "config" / "run_profile.tsa29.yaml").resolve()
    )
    assert plan.overlay_paths == (
        (instance_root / "config" / "tsr" / "overlay.yaml").resolve(),
    )
    assert plan.thlb_netdown_recipe_path == thlb_recipe_path.resolve()
    assert plan.source_layers_recipe_path == source_layers_recipe_path.resolve()
    assert plan.execution_mode == "reconstructed"
    assert plan.validation_contract is None


def test_build_named_pipeline_execution_plan_binds_required_strict_validation_recipe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance_root = tmp_path / "instance"
    (instance_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "workbench" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "data" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "runbooks" / "pipelines").mkdir(parents=True, exist_ok=True)
    (instance_root / "config" / "run_profile.tsa29.yaml").write_text(
        "selection:\n  tsa:\n    - '29'\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "overlay.yaml").write_text(
        "schema_version: 1\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "thlb_locked_chain_ledger.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.md").write_text(
        "# comparison\n",
        encoding="utf-8",
    )
    live_recipe_path = instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml"
    live_recipe_path.write_text("schema_version: 1\n", encoding="utf-8")
    locked_recipe_path = (
        instance_root / "workbench" / "tsr" / "thlb_netdown.locked.recipe.yaml"
    )
    locked_recipe_path.write_text("schema_version: 1\n", encoding="utf-8")
    source_layers_recipe_path = (
        instance_root / "config" / "tsr" / "source_layers.recipe.yaml"
    )
    source_layers_recipe_path.write_text("schema_version: 1\n", encoding="utf-8")
    checkpoint_path = (
        instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather"
    )
    checkpoint_path.write_text("checkpoint\n", encoding="utf-8")
    runbook_path = instance_root / "runbooks" / "pipelines" / "tsa29.yaml"
    runbook_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "runbook_kind: femic_pipeline_runbook",
                'label: "TSA29 strict validation lane"',
                "pipeline_id: tsr.thlb_strict",
                "instance_root: .",
                "run_profile: config/run_profile.tsa29.yaml",
                "overlay_paths:",
                "  - config/tsr/overlay.yaml",
                "restart:",
                "  seam_id: aflb_yield_ready",
                "validation_contract:",
                "  contract_kind: tsa29_locked_chain_strict",
                "  locked_chain_ledger_path: config/tsr/thlb_locked_chain_ledger.json",
                "  comparison_report_path: config/tsr/thlb_reconstruction_comparison.md",
                "  required_recipe_path: workbench/tsr/thlb_netdown.locked.recipe.yaml",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        named_pipelines,
        "load_tsr_thlb_netdown_recipe",
        lambda path: SimpleNamespace(
            instance_inputs=SimpleNamespace(
                source_layer_recipe_path="config/tsr/source_layers.recipe.yaml"
            )
        ),
    )

    plan = named_pipelines.build_named_pipeline_execution_plan(
        runbook_path=runbook_path,
        instance_root=instance_root,
    )

    assert live_recipe_path.resolve() != locked_recipe_path.resolve()
    assert plan.thlb_netdown_recipe_path == locked_recipe_path.resolve()
    assert plan.source_layers_recipe_path == source_layers_recipe_path.resolve()
    assert plan.validation_contract is not None
    assert plan.validation_contract.required_recipe_path == locked_recipe_path.resolve()


def test_build_named_pipeline_execution_plan_rejects_missing_required_validation_recipe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance_root = tmp_path / "instance"
    (instance_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "workbench" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "data" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "runbooks" / "pipelines").mkdir(parents=True, exist_ok=True)
    (instance_root / "config" / "run_profile.tsa29.yaml").write_text(
        "selection:\n  tsa:\n    - '29'\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "overlay.yaml").write_text(
        "schema_version: 1\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "thlb_locked_chain_ledger.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.md").write_text(
        "# comparison\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "source_layers.recipe.yaml").write_text(
        "schema_version: 1\n",
        encoding="utf-8",
    )
    checkpoint_path = (
        instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather"
    )
    checkpoint_path.write_text("checkpoint\n", encoding="utf-8")
    runbook_path = instance_root / "runbooks" / "pipelines" / "tsa29.yaml"
    runbook_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "runbook_kind: femic_pipeline_runbook",
                'label: "TSA29 strict validation lane"',
                "pipeline_id: tsr.thlb_strict",
                "instance_root: .",
                "run_profile: config/run_profile.tsa29.yaml",
                "overlay_paths:",
                "  - config/tsr/overlay.yaml",
                "restart:",
                "  seam_id: aflb_yield_ready",
                "validation_contract:",
                "  contract_kind: tsa29_locked_chain_strict",
                "  locked_chain_ledger_path: config/tsr/thlb_locked_chain_ledger.json",
                "  comparison_report_path: config/tsr/thlb_reconstruction_comparison.md",
                "  required_recipe_path: workbench/tsr/thlb_netdown.locked.recipe.yaml",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        named_pipelines,
        "load_tsr_thlb_netdown_recipe",
        lambda path: SimpleNamespace(
            instance_inputs=SimpleNamespace(
                source_layer_recipe_path="config/tsr/source_layers.recipe.yaml"
            )
        ),
    )

    with pytest.raises(named_pipelines.NamedPipelineError) as excinfo:
        named_pipelines.build_named_pipeline_execution_plan(
            runbook_path=runbook_path,
            instance_root=instance_root,
        )

    assert "Resolved required validation recipe path not found" in str(excinfo.value)


def test_checked_in_strict_runbook_builds_when_recipe_is_bound_to_required_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    runbook_path = (
        repo_root
        / "runbooks"
        / "pipelines"
        / "tsa29.tsr.thlb_strict.aflb_yield_ready.yaml"
    )
    instance_root = tmp_path / "instance"
    (instance_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "workbench" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "data" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "config" / "run_profile.tsa29.yaml").write_text(
        "selection:\n  tsa:\n    - '29'\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "overlay.yaml").write_text(
        "schema_version: 1\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "thlb_locked_chain_ledger.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.md").write_text(
        "# comparison\n",
        encoding="utf-8",
    )
    locked_recipe_path = (
        instance_root / "workbench" / "tsr" / "thlb_netdown.locked.recipe.yaml"
    )
    locked_recipe_path.write_text("schema_version: 1\n", encoding="utf-8")
    source_layers_recipe_path = (
        instance_root / "config" / "tsr" / "source_layers.recipe.yaml"
    )
    source_layers_recipe_path.write_text("schema_version: 1\n", encoding="utf-8")
    checkpoint_path = (
        instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather"
    )
    checkpoint_path.write_text("checkpoint\n", encoding="utf-8")

    monkeypatch.setattr(
        named_pipelines,
        "load_tsr_thlb_netdown_recipe",
        lambda path: SimpleNamespace(
            instance_inputs=SimpleNamespace(
                source_layer_recipe_path="config/tsr/source_layers.recipe.yaml"
            )
        ),
    )

    plan = named_pipelines.build_named_pipeline_execution_plan(
        runbook_path=runbook_path,
        instance_root=instance_root,
    )

    assert plan.pipeline_id == "tsr.thlb_strict"
    assert plan.thlb_netdown_recipe_path == locked_recipe_path.resolve()
    assert plan.validation_contract is not None
    assert (
        plan.validation_contract.locked_chain_ledger_path
        == (
            instance_root / "config" / "tsr" / "thlb_locked_chain_ledger.json"
        ).resolve()
    )
    assert (
        plan.validation_contract.comparison_report_path
        == (
            instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.md"
        ).resolve()
    )
    assert plan.validation_contract.required_recipe_path == locked_recipe_path.resolve()


def test_run_named_pipeline_runbook_dispatches_to_tsr_thlb_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance_root = tmp_path / "instance"
    runbook_path = instance_root / "runbooks" / "pipelines" / "tsa29.yaml"
    plan = named_pipelines.NamedPipelineExecutionPlan(
        runbook_path=runbook_path,
        instance_root=instance_root,
        pipeline_id="tsr.thlb_strict",
        pipeline_label="TSR strict THLB product lane",
        seam_id="scratch",
        checkpoint_path=None,
        run_profile_path=None,
        overlay_paths=(),
        parameter_files=(),
        validation_contract=None,
        user_registry_path=None,
        instance_registry_path=None,
        explicit_registry_paths=(),
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        execution_mode="reconstructed",
    )
    captured_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        named_pipelines,
        "build_named_pipeline_execution_plan",
        lambda **kwargs: plan,
    )

    def _fake_run(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        runtime_event_sink = kwargs.get("runtime_event_sink")
        if callable(runtime_event_sink):
            runtime_event_sink(
                {
                    "event_kind": "parent_step_started",
                    "parent_step_id": "thlb_parent_001_total_tsa_area",
                    "parent_label": "Total TSA area",
                    "row_order": 1,
                    "land_base_stage": "glb",
                }
            )
            runtime_event_sink(
                {
                    "event_kind": "compiled_step_finished",
                    "parent_step_id": "thlb_parent_001_total_tsa_area",
                    "compiled_step_id": "thlb_step_001_total_tsa_area",
                    "compiled_step_label": "Total TSA area",
                    "row_order": 1,
                    "land_base_stage": "glb",
                    "run_status": "applied_noop",
                    "remaining_area_ha": 1000.0,
                }
            )
        return SimpleNamespace(
            step_count=1,
            final_managed_area_ha=1000.0,
            runtime_status_report_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "thlb_reconstructed_status_report-20260419T000000Z.md",
            audit_path=instance_root
            / "config"
            / "tsr"
            / "thlb_reconstructed.audit.json",
        )

    monkeypatch.setattr(named_pipelines, "run_tsr_thlb_netdown_recipe", _fake_run)

    result = named_pipelines.run_named_pipeline_runbook(
        runbook_path=runbook_path,
        instance_root=instance_root,
    )

    assert captured_kwargs["recipe_path"] == plan.thlb_netdown_recipe_path
    assert captured_kwargs["checkpoint_path"] is None
    assert captured_kwargs["execution_mode"] == "reconstructed"
    assert result.plan == plan
    assert result.tsr_thlb_result.step_count == 1
    assert result.runtime_event_log_path is not None
    assert result.runtime_event_log_path.exists()
    runtime_lines = result.runtime_event_log_path.read_text(
        encoding="utf-8"
    ).splitlines()
    assert any("event_kind=pipeline_run_started" in line for line in runtime_lines)
    assert any("event_kind=parent_step_started" in line for line in runtime_lines)
    assert any("event_kind=compiled_step_finished" in line for line in runtime_lines)
    assert any("event_kind=pipeline_run_finished" in line for line in runtime_lines)


class _FixtureContractHandler:
    contract_kind = "fixture_contract"

    def __init__(self, *, pre_default_result=None) -> None:
        self.pre_default_result = pre_default_result
        self.pre_default_called = False
        self.validate_called = False

    def run_before_default(self, *, plan, runtime_logger, runtime_event_log_path):
        self.pre_default_called = True
        runtime_logger.emit({"event_kind": "fixture_contract_pre_default"})
        return self.pre_default_result

    def validate_after_default(self, *, plan, tsr_result):
        self.validate_called = True
        return named_pipelines.NamedPipelineValidationResult(
            contract_kind=plan.validation_contract.contract_kind,
            validated_parent_step_count=1,
            latest_locked_row_order=1,
            latest_locked_parent_step_id="fixture_parent_step",
            expected_final_managed_area_ha=1000.0,
            actual_final_managed_area_ha=tsr_result.final_managed_area_ha,
            max_abs_marginal_delta_ha=0.0,
            max_abs_cumulative_delta_ha=0.0,
        )


def _reset_contract_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(named_pipelines, "_NAMED_PIPELINE_CONTRACT_HANDLERS", {})
    monkeypatch.setattr(named_pipelines, "_DISCOVERED_NAMED_PIPELINE_CONTRACTS", True)


def _fixture_contract_plan(
    instance_root: Path,
) -> named_pipelines.NamedPipelineExecutionPlan:
    return named_pipelines.NamedPipelineExecutionPlan(
        runbook_path=instance_root / "runbooks" / "pipelines" / "fixture.yaml",
        instance_root=instance_root,
        pipeline_id="tsr.thlb_strict",
        pipeline_label="TSR strict THLB product lane",
        seam_id="aflb_yield_ready",
        checkpoint_path=instance_root
        / "data"
        / "tsr"
        / "aflb_yield_ready_checkpoint.feather",
        run_profile_path=None,
        overlay_paths=(),
        parameter_files=(),
        validation_contract=named_pipelines.NamedPipelineValidationContract(
            contract_kind="fixture_contract",
            locked_chain_ledger_path=None,
            comparison_report_path=None,
            required_recipe_path=None,
        ),
        user_registry_path=None,
        instance_registry_path=None,
        explicit_registry_paths=(),
        thlb_netdown_recipe_path=instance_root
        / "workbench"
        / "tsr"
        / "thlb_netdown.locked.recipe.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        execution_mode="reconstructed",
    )


def test_register_named_pipeline_contract_handler_rejects_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_contract_handlers(monkeypatch)
    named_pipelines.register_named_pipeline_contract_handler(_FixtureContractHandler())

    with pytest.raises(named_pipelines.NamedPipelineError, match="already registered"):
        named_pipelines.register_named_pipeline_contract_handler(
            _FixtureContractHandler()
        )


def test_named_pipeline_contract_handler_dispatches_default_run_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_contract_handlers(monkeypatch)
    instance_root = tmp_path / "instance"
    plan = _fixture_contract_plan(instance_root)
    handler = _FixtureContractHandler()
    named_pipelines.register_named_pipeline_contract_handler(handler)
    captured_lines: list[str] = []

    monkeypatch.setattr(
        named_pipelines,
        "build_named_pipeline_execution_plan",
        lambda **kwargs: plan,
    )
    monkeypatch.setattr(
        named_pipelines,
        "run_tsr_thlb_netdown_recipe",
        lambda **kwargs: SimpleNamespace(
            audit_path=instance_root / "runtime" / "audit.json",
            final_managed_area_ha=1000.0,
            step_count=1,
            runtime_status_report_path=instance_root / "runtime" / "status.md",
        ),
    )

    result = named_pipelines.run_named_pipeline_runbook(
        runbook_path=plan.runbook_path,
        instance_root=instance_root,
        runtime_event_sink=captured_lines.append,
    )

    assert handler.pre_default_called is True
    assert handler.validate_called is True
    assert result.validation_result is not None
    assert result.validation_result.contract_kind == "fixture_contract"
    assert any(
        "event_kind=fixture_contract_pre_default" in line for line in captured_lines
    )
    assert any(
        "event_kind=pipeline_validation_finished" in line for line in captured_lines
    )


def test_named_pipeline_contract_handler_can_return_pre_default_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_contract_handlers(monkeypatch)
    instance_root = tmp_path / "instance"
    plan = _fixture_contract_plan(instance_root)
    expected = named_pipelines.NamedPipelineExecutionResult(
        plan=plan,
        tsr_thlb_result=None,
        validation_result=named_pipelines.NamedPipelineValidationResult(
            contract_kind="fixture_contract",
            validated_parent_step_count=1,
        ),
        runtime_event_log_path=instance_root / "runtime" / "fixture.log",
    )
    handler = _FixtureContractHandler(pre_default_result=expected)
    named_pipelines.register_named_pipeline_contract_handler(handler)
    run_called = False

    monkeypatch.setattr(
        named_pipelines,
        "build_named_pipeline_execution_plan",
        lambda **kwargs: plan,
    )

    def _fake_run(**kwargs: object) -> object:
        nonlocal run_called
        run_called = True
        raise AssertionError("default runner should not be called")

    monkeypatch.setattr(named_pipelines, "run_tsr_thlb_netdown_recipe", _fake_run)

    result = named_pipelines.run_named_pipeline_runbook(
        runbook_path=plan.runbook_path,
        instance_root=instance_root,
    )

    assert result is expected
    assert handler.pre_default_called is True
    assert run_called is False


def test_named_pipeline_contract_handler_missing_errors_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_contract_handlers(monkeypatch)
    instance_root = tmp_path / "instance"
    plan = _fixture_contract_plan(instance_root)
    run_called = False
    monkeypatch.setattr(
        named_pipelines,
        "build_named_pipeline_execution_plan",
        lambda **kwargs: plan,
    )

    def _fake_run(**kwargs: object) -> object:
        nonlocal run_called
        run_called = True
        raise AssertionError("default runner should not be called")

    monkeypatch.setattr(named_pipelines, "run_tsr_thlb_netdown_recipe", _fake_run)

    with pytest.raises(named_pipelines.NamedPipelineError, match="not installed"):
        named_pipelines.run_named_pipeline_runbook(
            runbook_path=plan.runbook_path,
            instance_root=instance_root,
        )

    assert run_called is False


def test_discover_named_pipeline_contract_handlers_loads_entry_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_contract_handlers(monkeypatch)
    monkeypatch.setattr(named_pipelines, "_DISCOVERED_NAMED_PIPELINE_CONTRACTS", False)
    handler = _FixtureContractHandler()
    entry_point = SimpleNamespace(name="fixture", load=lambda: lambda: handler)
    monkeypatch.setattr(
        named_pipelines,
        "entry_points",
        lambda *, group: (
            (entry_point,)
            if group == named_pipelines.NAMED_PIPELINE_CONTRACT_ENTRY_POINT_GROUP
            else ()
        ),
    )

    resolved = named_pipelines.get_named_pipeline_contract_handler("fixture_contract")

    assert resolved is handler


def test_run_named_pipeline_runbook_emits_pipeline_run_failed_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance_root = tmp_path / "instance"
    runbook_path = instance_root / "runbooks" / "pipelines" / "tsa29.yaml"
    plan = named_pipelines.NamedPipelineExecutionPlan(
        runbook_path=runbook_path,
        instance_root=instance_root,
        pipeline_id="tsr.thlb_strict",
        pipeline_label="TSR strict THLB product lane",
        seam_id="aflb_yield_ready",
        checkpoint_path=instance_root
        / "data"
        / "tsr"
        / "aflb_yield_ready_checkpoint.feather",
        run_profile_path=None,
        overlay_paths=(),
        parameter_files=(),
        validation_contract=None,
        user_registry_path=None,
        instance_registry_path=None,
        explicit_registry_paths=(),
        thlb_netdown_recipe_path=instance_root
        / "workbench"
        / "tsr"
        / "thlb_netdown.locked.recipe.yaml",
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        execution_mode="reconstructed",
    )
    captured_lines: list[str] = []

    monkeypatch.setattr(
        named_pipelines,
        "build_named_pipeline_execution_plan",
        lambda **kwargs: plan,
    )

    def _fake_run(**kwargs: object) -> object:
        runtime_event_sink = kwargs.get("runtime_event_sink")
        if callable(runtime_event_sink):
            runtime_event_sink(
                {
                    "event_kind": "compiled_step_started",
                    "parent_step_id": "thlb_parent_001_total_tsa_area",
                    "compiled_step_id": "thlb_step_001_total_tsa_area",
                }
            )
        raise named_pipelines.NamedPipelineError("synthetic failure")

    monkeypatch.setattr(named_pipelines, "run_tsr_thlb_netdown_recipe", _fake_run)

    with pytest.raises(named_pipelines.NamedPipelineError, match="synthetic failure"):
        named_pipelines.run_named_pipeline_runbook(
            runbook_path=runbook_path,
            instance_root=instance_root,
            runtime_event_sink=captured_lines.append,
        )

    assert any("event_kind=pipeline_run_failed" in line for line in captured_lines)
    assert any('error="synthetic failure"' in line for line in captured_lines)
