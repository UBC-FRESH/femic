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


def test_build_named_pipeline_execution_plan_rejects_strict_validation_recipe_mismatch(
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

    assert "Strict validation contract mismatch" in str(excinfo.value)
    assert str(live_recipe_path.resolve()) in str(excinfo.value)
    assert str(locked_recipe_path.resolve()) in str(excinfo.value)


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
    (instance_root / "config" / "pipelines.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "registry_kind: pipeline_registry",
                "pipelines:",
                "  - pipeline_id: tsr.thlb_strict",
                '    label: "TSR strict THLB product lane"',
                "    kind: tsr",
                '    summary: "Strict locked validation lane."',
                "    seams:",
                "      - seam_id: scratch",
                "        start_mode: scratch",
                "      - seam_id: aflb_yield_ready",
                "        checkpoint_path: data/tsr/aflb_yield_ready_checkpoint.feather",
                "    recipes:",
                "      - recipe_id: tsr.thlb_netdown",
                "        recipe_kind: tsr_thlb_netdown",
                "        default_recipe_path: workbench/tsr/thlb_netdown.locked.recipe.yaml",
                "",
            ]
        ),
        encoding="utf-8",
    )
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
        return "tsr-result"

    monkeypatch.setattr(named_pipelines, "run_tsr_thlb_netdown_recipe", _fake_run)

    result = named_pipelines.run_named_pipeline_runbook(
        runbook_path=runbook_path,
        instance_root=instance_root,
    )

    assert captured_kwargs["recipe_path"] == plan.thlb_netdown_recipe_path
    assert captured_kwargs["checkpoint_path"] is None
    assert captured_kwargs["execution_mode"] == "reconstructed"
    assert result.plan == plan
    assert result.tsr_thlb_result == "tsr-result"
