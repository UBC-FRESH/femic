from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import pytest

from femic.patchworks_variants import (
    PatchworksVariantMaterializationAction,
    PatchworksVariantDefinition,
    PatchworksVariantRegistryError,
    PatchworksScenarioSetMember,
    build_patchworks_variant_materialization_plan,
    load_patchworks_variant_registry,
    load_patchworks_user_registry_overlay,
    materialize_patchworks_variant,
    remove_patchworks_user_variant_entry,
    upsert_patchworks_user_variant_entry,
)


def test_load_patchworks_variant_registry_includes_builtin_k3z_base() -> None:
    registry = load_patchworks_variant_registry()

    variant = registry.get_variant("k3z.base")
    assert variant.instance_id == "k3z"
    assert variant.default is True
    assert variant.analysis_pin.name == "base.pin"
    assert variant.runtime_config.name == "patchworks.runtime.windows.yaml"
    assert variant.scenarios[0].scenario_id == "even_flow_smoke"
    assert variant.scenarios[0].mode == "max-even-flow-smoke"
    assert variant.scenarios[0].target == "product.Yield.managed.Total"
    scenario_set = registry.get_scenario_set("k3z.proving_ground")
    assert scenario_set.mode == "sequential"
    assert scenario_set.scenarios[0].variant_id == "k3z.base"
    assert scenario_set.scenarios[1].variant_id == "k3z.intensive_light_standstructure"
    default_variant, default_scenario = registry.get_default_scenario("k3z.base")
    assert default_variant.variant_id == "k3z.base"
    assert default_scenario.scenario_id == "even_flow_smoke"


def test_load_patchworks_variant_registry_user_overlay_can_override_builtin(
    tmp_path: Path,
) -> None:
    overlay_path = tmp_path / "variants.yaml"
    overlay_path.write_text(
        "\n".join(
            [
                "variants:",
                "  - variant_id: k3z.base",
                '    label: "Overridden K3Z base"',
                "    instance_id: k3z",
                "    variant_family: baseline",
                "    kind: patchworks",
                "    instance_root: external/femic-k3z-instance",
                "    analysis_pin: external/femic-k3z-instance/models/k3z_patchworks_model/analysis/base.pin",
                "    runtime_config: external/femic-k3z-instance/config/patchworks.runtime.windows.yaml",
                "    default: true",
                "",
            ]
        ),
        encoding="utf-8",
    )

    registry = load_patchworks_variant_registry(user_registry_path=overlay_path)

    variant = registry.get_variant("k3z.base")
    assert variant.label == "Overridden K3Z base"
    assert variant.source == "user"
    assert variant.registry_path == overlay_path.resolve()


def test_patchworks_variant_registry_unknown_variant_raises() -> None:
    registry = load_patchworks_variant_registry()

    with pytest.raises(PatchworksVariantRegistryError):
        registry.get_variant("missing.variant")


def test_load_patchworks_variant_registry_parses_materialization_actions(
    tmp_path: Path,
) -> None:
    overlay_path = tmp_path / "variants.yaml"
    overlay_path.write_text(
        "\n".join(
            [
                "variants:",
                "  - variant_id: k3z.base",
                '    label: "Overridden K3Z base"',
                "    instance_id: k3z",
                "    variant_family: baseline",
                "    kind: patchworks",
                "    instance_root: external/femic-k3z-instance",
                "    analysis_pin: external/femic-k3z-instance/models/k3z_patchworks_model/analysis/base.pin",
                "    runtime_config: external/femic-k3z-instance/config/patchworks.runtime.windows.yaml",
                "    materialization:",
                "      - kind: datalad-get",
                "        dataset_root: external/femic-public-data",
                "        relpaths:",
                "          - data",
                "        estimated_bytes: 1024",
                "",
            ]
        ),
        encoding="utf-8",
    )

    registry = load_patchworks_variant_registry(user_registry_path=overlay_path)

    variant = registry.get_variant("k3z.base")
    assert len(variant.materialization) == 1
    assert variant.materialization[0].kind == "datalad-get"
    assert variant.materialization[0].dataset_root == "external/femic-public-data"
    assert variant.materialization[0].relpaths == ("data",)
    assert variant.materialization[0].estimated_bytes == 1024


def test_build_patchworks_variant_materialization_plan_requires_confirmation() -> None:
    variant = PatchworksVariantDefinition(
        variant_id="k3z.base",
        label="K3Z base",
        instance_id="k3z",
        instance_label="K3Z",
        variant_family="baseline",
        kind="patchworks",
        instance_root=Path("external/femic-k3z-instance"),
        analysis_pin=Path("analysis/base.pin"),
        runtime_config=Path("config/runtime.yaml"),
        materialization=(
            PatchworksVariantMaterializationAction(
                kind="datalad-get",
                dataset_root="external/data",
                relpaths=("a",),
                estimated_bytes=80 * 1024 * 1024,
            ),
            PatchworksVariantMaterializationAction(
                kind="datalad-get",
                dataset_root="external/data",
                relpaths=("b",),
                estimated_bytes=30 * 1024 * 1024,
            ),
        ),
    )

    plan = build_patchworks_variant_materialization_plan(
        variant,
        prompt_threshold_bytes=100 * 1024 * 1024,
    )

    assert plan.action_count == 2
    assert plan.known_estimated_bytes == 110 * 1024 * 1024
    assert plan.has_unknown_sizes is False
    assert plan.requires_confirmation is True


def test_materialize_patchworks_variant_runs_datalad_get(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dataset_root = tmp_path / "external" / "femic-public-data"
    dataset_root.mkdir(parents=True)

    variant = PatchworksVariantDefinition(
        variant_id="k3z.base",
        label="K3Z base",
        instance_id="k3z",
        instance_label="K3Z",
        variant_family="baseline",
        kind="patchworks",
        instance_root=tmp_path / "external" / "femic-k3z-instance",
        analysis_pin=Path("analysis/base.pin"),
        runtime_config=Path("config/runtime.yaml"),
        materialization=(
            PatchworksVariantMaterializationAction(
                kind="datalad-get",
                dataset_root="external/femic-public-data",
                relpaths=("data",),
                estimated_bytes=1024,
            ),
        ),
    )

    monkeypatch.setattr(
        "femic.patchworks_variants.shutil.which", lambda _name: "datalad"
    )
    calls: list[tuple[list[str], Path]] = []

    def _fake_run(args, **kwargs):
        calls.append((list(args), Path(kwargs["cwd"])))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("femic.patchworks_variants.subprocess.run", _fake_run)

    materialize_patchworks_variant(variant, source_root=tmp_path)

    assert calls == [(["datalad", "get", "data"], dataset_root.resolve())]


def test_upsert_patchworks_user_variant_entry_writes_overlay_file(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "variants.yaml"

    written_path = upsert_patchworks_user_variant_entry(
        {
            "variant_id": "demo.base",
            "label": "Demo base",
            "instance_id": "demo",
            "variant_family": "baseline",
            "kind": "patchworks",
            "instance_root": "external/demo-instance",
            "analysis_pin": "external/demo-instance/models/demo/analysis/base.pin",
            "runtime_config": "external/demo-instance/config/runtime.yaml",
        },
        user_registry_path=registry_path,
        instance_label="Demo instance",
    )

    assert written_path == registry_path.resolve()
    _, payload = load_patchworks_user_registry_overlay(registry_path)
    assert payload["instances"] == [{"instance_id": "demo", "label": "Demo instance"}]
    assert payload["variants"][0]["variant_id"] == "demo.base"


def test_remove_patchworks_user_variant_entry_removes_entry(tmp_path: Path) -> None:
    registry_path = tmp_path / "variants.yaml"
    registry_path.write_text(
        "\n".join(
            [
                "variants:",
                "  - variant_id: demo.base",
                '    label: "Demo base"',
                "    instance_id: demo",
                "    variant_family: baseline",
                "    kind: patchworks",
                "    instance_root: external/demo-instance",
                "    analysis_pin: external/demo-instance/models/demo/analysis/base.pin",
                "    runtime_config: external/demo-instance/config/runtime.yaml",
                "",
            ]
        ),
        encoding="utf-8",
    )

    remove_patchworks_user_variant_entry("demo.base", user_registry_path=registry_path)

    _, payload = load_patchworks_user_registry_overlay(registry_path)
    assert payload["variants"] == []


def test_load_patchworks_variant_registry_parses_scenarios_from_overlay(
    tmp_path: Path,
) -> None:
    overlay_path = tmp_path / "variants.yaml"
    overlay_path.write_text(
        "\n".join(
            [
                "variants:",
                "  - variant_id: demo.base",
                '    label: "Demo base"',
                "    instance_id: demo",
                "    variant_family: baseline",
                "    kind: patchworks",
                "    instance_root: external/demo-instance",
                "    analysis_pin: external/demo-instance/models/demo/analysis/base.pin",
                "    runtime_config: external/demo-instance/config/runtime.yaml",
                "    scenarios:",
                "      - scenario_id: smoke",
                '        label: "Demo smoke"',
                "        mode: max-even-flow-smoke",
                "        target: product.Yield.managed.Total",
                "        iterations: 123",
                "        improvement: 0.5",
                "",
            ]
        ),
        encoding="utf-8",
    )

    registry = load_patchworks_variant_registry(user_registry_path=overlay_path)

    variant, scenario = registry.get_scenario("demo.base", "smoke")
    assert variant.variant_id == "demo.base"
    assert scenario.label == "Demo smoke"
    assert scenario.mode == "max-even-flow-smoke"
    assert scenario.iterations == 123
    assert scenario.improvement == 0.5


def test_load_patchworks_variant_registry_parses_scenario_sets_from_overlay(
    tmp_path: Path,
) -> None:
    overlay_path = tmp_path / "variants.yaml"
    overlay_path.write_text(
        "\n".join(
            [
                "variants:",
                "  - variant_id: demo.base",
                '    label: "Demo base"',
                "    instance_id: demo",
                "    variant_family: baseline",
                "    kind: patchworks",
                "    instance_root: external/demo-instance",
                "    analysis_pin: external/demo-instance/models/demo/analysis/base.pin",
                "    runtime_config: external/demo-instance/config/runtime.yaml",
                "    scenarios:",
                "      - scenario_id: smoke",
                "        mode: max-even-flow-smoke",
                "scenario_sets:",
                "  - scenario_set_id: demo.set",
                '    label: "Demo set"',
                "    mode: sequential",
                "    scenarios:",
                "      - demo.base/smoke",
                "",
            ]
        ),
        encoding="utf-8",
    )

    registry = load_patchworks_variant_registry(user_registry_path=overlay_path)

    scenario_set = registry.get_scenario_set("demo.set")
    assert scenario_set.label == "Demo set"
    assert scenario_set.mode == "sequential"
    assert scenario_set.scenarios == (
        PatchworksScenarioSetMember(variant_id="demo.base", scenario_id="smoke"),
    )


def test_load_patchworks_variant_registry_default_scenario_falls_back_to_single(
    tmp_path: Path,
) -> None:
    overlay_path = tmp_path / "variants.yaml"
    overlay_path.write_text(
        "\n".join(
            [
                "variants:",
                "  - variant_id: demo.base",
                '    label: "Demo base"',
                "    instance_id: demo",
                "    variant_family: baseline",
                "    kind: patchworks",
                "    instance_root: external/demo-instance",
                "    analysis_pin: external/demo-instance/models/demo/analysis/base.pin",
                "    runtime_config: external/demo-instance/config/runtime.yaml",
                "    scenarios:",
                "      - scenario_id: smoke",
                "        mode: max-even-flow-smoke",
                "",
            ]
        ),
        encoding="utf-8",
    )

    registry = load_patchworks_variant_registry(user_registry_path=overlay_path)

    variant, scenario = registry.get_default_scenario("demo.base")
    assert variant.variant_id == "demo.base"
    assert scenario.scenario_id == "smoke"
