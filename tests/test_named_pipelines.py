from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import pytest
from shapely.geometry import box

from femic import named_pipelines


def test_load_named_pipeline_registry_includes_builtin_tsr_thlb_strict() -> None:
    registry = named_pipelines.load_named_pipeline_registry()

    pipeline = registry.get_pipeline("tsr.thlb_strict")

    assert pipeline.label == "TSR strict THLB product lane"
    assert pipeline.get_seam("scratch").start_mode == "scratch"
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
        == (instance_root / "config" / "tsr" / "thlb_locked_chain_ledger.json").resolve()
    )
    assert (
        plan.validation_contract.comparison_report_path
        == (instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.md").resolve()
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
            audit_path=instance_root / "config" / "tsr" / "thlb_reconstructed.audit.json",
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
    runtime_lines = result.runtime_event_log_path.read_text(encoding="utf-8").splitlines()
    assert any("event_kind=pipeline_run_started" in line for line in runtime_lines)
    assert any("event_kind=parent_step_started" in line for line in runtime_lines)
    assert any("event_kind=compiled_step_finished" in line for line in runtime_lines)
    assert any("event_kind=pipeline_run_finished" in line for line in runtime_lines)


def _write_checkpoint_with_area(path: Path, *, area_ha: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {
            "_stand_area_sqm": [area_ha * 10000.0],
            "thlb_fact": [1.0],
        },
        geometry=[box(0.0, 0.0, 1.0, 1.0)],
        crs="EPSG:3005",
    ).to_feather(path)


def test_run_named_pipeline_runbook_validates_tsa29_locked_chain_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance_root = tmp_path / "instance"
    (instance_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "workbench" / "tsr").mkdir(parents=True, exist_ok=True)
    audit_path = instance_root / "config" / "tsr" / "thlb_reconstructed.audit.json"
    ledger_path = instance_root / "config" / "tsr" / "thlb_locked_chain_ledger.json"
    comparison_path = (
        instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.md"
    )
    comparison_path.write_text("# comparison\n", encoding="utf-8")
    _write_checkpoint_with_area(
        instance_root / "data" / "tsr" / "aflb_checkpoint.feather",
        area_ha=800.0,
    )
    _write_checkpoint_with_area(
        instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather",
        area_ha=800.0,
    )
    audit_path.write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "parent_step_id": "thlb_parent_005_analysis_forest_land_base",
                        "order_index": 5,
                        "parent_label": "Analysis forest land base",
                        "net_removed_area_ha": 0.0,
                        "remaining_area_ha": 800.0,
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ledger_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "row_order": 5,
                        "parent_step_id": "thlb_parent_005_analysis_forest_land_base",
                        "locked_net_removed_area_ha": None,
                        "locked_cumulative_remaining_area_ha": 800.0,
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    plan = named_pipelines.NamedPipelineExecutionPlan(
        runbook_path=instance_root / "runbooks" / "pipelines" / "tsa29.yaml",
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
            contract_kind="tsa29_locked_chain_strict",
            locked_chain_ledger_path=ledger_path,
            comparison_report_path=comparison_path,
            required_recipe_path=instance_root
            / "workbench"
            / "tsr"
            / "thlb_netdown.locked.recipe.yaml",
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

    monkeypatch.setattr(
        named_pipelines,
        "build_named_pipeline_execution_plan",
        lambda **kwargs: plan,
    )
    monkeypatch.setattr(
        named_pipelines,
        "run_tsr_thlb_netdown_recipe",
        lambda **kwargs: SimpleNamespace(
            audit_path=audit_path,
            final_managed_area_ha=800.0,
            step_count=2,
            runtime_status_report_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "thlb_reconstructed_status_report-20260419T000000Z.md",
        ),
    )

    result = named_pipelines.run_named_pipeline_runbook(
        runbook_path=plan.runbook_path,
        instance_root=instance_root,
    )

    assert result.validation_result is not None
    assert result.validation_result.contract_kind == "tsa29_locked_chain_strict"
    assert result.validation_result.validated_parent_step_count == 1
    assert result.validation_result.latest_locked_row_order == 5
    assert (
        result.validation_result.latest_locked_parent_step_id
        == "thlb_parent_005_analysis_forest_land_base"
    )
    assert result.validation_result.expected_final_managed_area_ha == pytest.approx(800.0)
    assert result.validation_result.actual_final_managed_area_ha == pytest.approx(800.0)
    assert result.validation_result.max_abs_marginal_delta_ha == pytest.approx(0.0)
    assert result.validation_result.max_abs_cumulative_delta_ha == pytest.approx(0.0)


def test_run_named_pipeline_runbook_rejects_tsa29_locked_chain_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance_root = tmp_path / "instance"
    (instance_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "workbench" / "tsr").mkdir(parents=True, exist_ok=True)
    audit_path = instance_root / "config" / "tsr" / "thlb_reconstructed.audit.json"
    ledger_path = instance_root / "config" / "tsr" / "thlb_locked_chain_ledger.json"
    comparison_path = (
        instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.md"
    )
    comparison_path.write_text("# comparison\n", encoding="utf-8")
    _write_checkpoint_with_area(
        instance_root / "data" / "tsr" / "aflb_checkpoint.feather",
        area_ha=800.0,
    )
    _write_checkpoint_with_area(
        instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather",
        area_ha=800.0,
    )
    audit_path.write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "parent_step_id": "thlb_parent_005_analysis_forest_land_base",
                        "order_index": 5,
                        "parent_label": "Analysis forest land base",
                        "net_removed_area_ha": 10.0,
                        "remaining_area_ha": 790.0,
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ledger_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "row_order": 5,
                        "parent_step_id": "thlb_parent_005_analysis_forest_land_base",
                        "locked_net_removed_area_ha": None,
                        "locked_cumulative_remaining_area_ha": 800.0,
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    plan = named_pipelines.NamedPipelineExecutionPlan(
        runbook_path=instance_root / "runbooks" / "pipelines" / "tsa29.yaml",
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
            contract_kind="tsa29_locked_chain_strict",
            locked_chain_ledger_path=ledger_path,
            comparison_report_path=comparison_path,
            required_recipe_path=instance_root
            / "workbench"
            / "tsr"
            / "thlb_netdown.locked.recipe.yaml",
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

    monkeypatch.setattr(
        named_pipelines,
        "build_named_pipeline_execution_plan",
        lambda **kwargs: plan,
    )
    monkeypatch.setattr(
        named_pipelines,
        "run_tsr_thlb_netdown_recipe",
        lambda **kwargs: SimpleNamespace(
            audit_path=audit_path,
            final_managed_area_ha=790.0,
            step_count=2,
            runtime_status_report_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "thlb_reconstructed_status_report-20260419T000000Z.md",
        ),
    )

    with pytest.raises(named_pipelines.NamedPipelineError) as excinfo:
        named_pipelines.run_named_pipeline_runbook(
            runbook_path=plan.runbook_path,
            instance_root=instance_root,
        )

    assert "Strict validation contract mismatch at row `5`" in str(excinfo.value)


def test_run_named_pipeline_runbook_rejects_tsa29_preflight_mismatch_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance_root = tmp_path / "instance"
    (instance_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "workbench" / "tsr").mkdir(parents=True, exist_ok=True)
    ledger_path = instance_root / "config" / "tsr" / "thlb_locked_chain_ledger.json"
    comparison_path = (
        instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.md"
    )
    comparison_path.write_text("# comparison\n", encoding="utf-8")
    _write_checkpoint_with_area(
        instance_root / "data" / "tsr" / "aflb_checkpoint.feather",
        area_ha=810.0,
    )
    _write_checkpoint_with_area(
        instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather",
        area_ha=810.0,
    )
    ledger_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "row_order": 5,
                        "parent_step_id": "thlb_parent_005_analysis_forest_land_base",
                        "locked_net_removed_area_ha": None,
                        "locked_cumulative_remaining_area_ha": 800.0,
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    plan = named_pipelines.NamedPipelineExecutionPlan(
        runbook_path=instance_root / "runbooks" / "pipelines" / "tsa29.yaml",
        instance_root=instance_root,
        pipeline_id="tsr.thlb_strict",
        pipeline_label="TSR strict THLB product lane",
        seam_id="aflb_yield_ready",
        checkpoint_path=instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather",
        run_profile_path=None,
        overlay_paths=(),
        parameter_files=(),
        validation_contract=named_pipelines.NamedPipelineValidationContract(
            contract_kind="tsa29_locked_chain_strict",
            locked_chain_ledger_path=ledger_path,
            comparison_report_path=comparison_path,
            required_recipe_path=instance_root
            / "workbench"
            / "tsr"
            / "thlb_netdown.locked.recipe.yaml",
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
    captured_lines: list[str] = []
    run_called = False

    monkeypatch.setattr(
        named_pipelines,
        "build_named_pipeline_execution_plan",
        lambda **kwargs: plan,
    )

    def _fake_run(**kwargs: object) -> object:
        nonlocal run_called
        run_called = True
        raise AssertionError("downstream runner should not be called")

    monkeypatch.setattr(named_pipelines, "run_tsr_thlb_netdown_recipe", _fake_run)

    with pytest.raises(named_pipelines.NamedPipelineError) as excinfo:
        named_pipelines.run_named_pipeline_runbook(
            runbook_path=plan.runbook_path,
            instance_root=instance_root,
            runtime_event_sink=captured_lines.append,
        )

    error_message = str(excinfo.value)
    assert "Strict validation preflight mismatch for seam `aflb_yield_ready`" in error_message
    assert "locked row `5`" in error_message
    assert "expected `800.000 ha`" in error_message
    assert "got `810.000 ha`" in error_message
    assert "delta `10.000 ha`" in error_message
    assert run_called is False
    assert any(
        "event_kind=pipeline_validation_preflight_started" in line for line in captured_lines
    )
    assert any("event_kind=pipeline_run_failed" in line for line in captured_lines)
    assert not any("event_kind=parent_step_started" in line for line in captured_lines)


def test_run_named_pipeline_runbook_rejects_tsa29_preflight_scratch_without_raw_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance_root = tmp_path / "instance"
    (instance_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    (instance_root / "workbench" / "tsr").mkdir(parents=True, exist_ok=True)
    ledger_path = instance_root / "config" / "tsr" / "thlb_locked_chain_ledger.json"
    comparison_path = (
        instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.md"
    )
    comparison_path.write_text("# comparison\n", encoding="utf-8")
    ledger_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "row_order": 1,
                        "parent_step_id": "thlb_parent_001_total_tsa_area",
                        "locked_net_removed_area_ha": None,
                        "locked_cumulative_remaining_area_ha": 1000.0,
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    plan = named_pipelines.NamedPipelineExecutionPlan(
        runbook_path=instance_root / "runbooks" / "pipelines" / "tsa29.yaml",
        instance_root=instance_root,
        pipeline_id="tsr.thlb_strict",
        pipeline_label="TSR strict THLB product lane",
        seam_id="scratch",
        checkpoint_path=None,
        run_profile_path=None,
        overlay_paths=(),
        parameter_files=(),
        validation_contract=named_pipelines.NamedPipelineValidationContract(
            contract_kind="tsa29_locked_chain_strict",
            locked_chain_ledger_path=ledger_path,
            comparison_report_path=comparison_path,
            required_recipe_path=instance_root
            / "workbench"
            / "tsr"
            / "thlb_netdown.locked.recipe.yaml",
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
    run_called = False

    monkeypatch.setattr(
        named_pipelines,
        "build_named_pipeline_execution_plan",
        lambda **kwargs: plan,
    )

    def _fake_run(**kwargs: object) -> object:
        nonlocal run_called
        run_called = True
        raise AssertionError("downstream runner should not be called")

    monkeypatch.setattr(named_pipelines, "run_tsr_thlb_netdown_recipe", _fake_run)

    with pytest.raises(named_pipelines.NamedPipelineError) as excinfo:
        named_pipelines.run_named_pipeline_runbook(
            runbook_path=plan.runbook_path,
            instance_root=instance_root,
        )

    assert "validated raw-start comparison surface for TSA29" in str(excinfo.value)
    assert run_called is False


def test_resolve_tsa29_locked_chain_strict_row_order() -> None:
    assert named_pipelines._resolve_tsa29_locked_chain_strict_row_order(seam_id="scratch") == 1
    assert named_pipelines._resolve_tsa29_locked_chain_strict_row_order(seam_id="aflb") == 5
    assert (
        named_pipelines._resolve_tsa29_locked_chain_strict_row_order(
            seam_id="aflb_yield_ready"
        )
        == 5
    )
    with pytest.raises(named_pipelines.NamedPipelineError, match="does not yet support seam"):
        named_pipelines._resolve_tsa29_locked_chain_strict_row_order(seam_id="lhlb_curve_ready")


def test_managed_area_ha_from_checkpoint_uses_explicit_tsr_checkpoint(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather"
    _write_checkpoint_with_area(checkpoint_path, area_ha=812.5)

    assert named_pipelines._managed_area_ha_from_checkpoint(checkpoint_path) == pytest.approx(
        812.5
    )


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
    assert any("error=\"synthetic failure\"" in line for line in captured_lines)
