from __future__ import annotations

from pathlib import Path

import pytest

from femic.patchworks_variants import (
    PatchworksVariantRegistryError,
    load_patchworks_variant_registry,
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
