from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import pytest

from femic.patchworks_variants import (
    PatchworksVariantMaterializationAction,
    PatchworksVariantDefinition,
    PatchworksVariantRegistryError,
    build_patchworks_variant_materialization_plan,
    load_patchworks_variant_registry,
    materialize_patchworks_variant,
)


def test_load_patchworks_variant_registry_includes_builtin_k3z_base() -> None:
    registry = load_patchworks_variant_registry()

    variant = registry.get_variant("k3z.base")
    assert variant.instance_id == "k3z"
    assert variant.default is True
    assert variant.analysis_pin.name == "base.pin"
    assert variant.runtime_config.name == "patchworks.runtime.windows.yaml"


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
