from __future__ import annotations

from pathlib import Path

import pytest

from femic.pipeline.vdyp_overrides import (
    load_vdyp_override_policy,
    vdyp_kwarg_overrides_for_tsa,
)


def test_vdyp_kwarg_overrides_for_known_tsa() -> None:
    overrides = vdyp_kwarg_overrides_for_tsa("40")
    assert overrides[("BWBS_SX", "L")]["skip1"] == 30
    assert overrides[("SWB_SX", "L")]["dx_c1"] == 1.0
    assert overrides[("SWB_SX", "L")]["dx_c2"] == 0.0


def test_vdyp_kwarg_overrides_for_unknown_tsa_is_empty() -> None:
    assert vdyp_kwarg_overrides_for_tsa("99") == {}


def test_vdyp_kwarg_overrides_for_tsa29_contains_sbps_pl_low_si_fix() -> None:
    overrides = vdyp_kwarg_overrides_for_tsa("29")
    assert overrides[("SBPS_PL", "L")]["skip1"] == 50


def test_vdyp_kwarg_overrides_for_k3z_are_loaded_from_instance_overlay() -> None:
    overrides = vdyp_kwarg_overrides_for_tsa(
        "k3z",
        instance_root=Path("external/femic-k3z-instance"),
    )
    assert overrides[("CWHvm_DR+HW", "L")]["body_c_min"] == -40
    assert overrides[("CWHvm_DR+HW", "H")]["tail_blend_years"] == 150
    assert (
        overrides[("CWHvm_DR+HW", "M")]["tail_linear_allow_quantile_fallback"] is True
    )


def test_vdyp_kwarg_overrides_returns_defensive_copy() -> None:
    first = vdyp_kwarg_overrides_for_tsa("24")
    first[("ESSF_BL", "L")]["skip1"] = 999
    second = vdyp_kwarg_overrides_for_tsa("24")
    assert second[("ESSF_BL", "L")]["skip1"] == 30


def test_load_vdyp_override_policy_merges_instance_overlay(tmp_path: Path) -> None:
    default_path = tmp_path / "default.yaml"
    default_path.write_text(
        """
version: 1
tsa_overrides:
  "08":
    - stratum: "BWBS_SB"
      si: "H"
      kwargs:
        skip1: 30
        dx_c1: 0.5
""".strip(),
        encoding="utf-8",
    )
    instance_path = tmp_path / "instance.yaml"
    instance_path.write_text(
        """
version: 1
tsa_overrides:
  "08":
    - stratum: "BWBS_SB"
      si: "H"
      kwargs:
        dx_c1: 2.0
        custom_flag: true
""".strip(),
        encoding="utf-8",
    )

    merged = load_vdyp_override_policy(
        default_policy_path=default_path,
        instance_policy_path=instance_path,
    )

    assert merged["08"][("BWBS_SB", "H")]["skip1"] == 30
    assert merged["08"][("BWBS_SB", "H")]["dx_c1"] == 2.0
    assert merged["08"][("BWBS_SB", "H")]["custom_flag"] is True


def test_load_vdyp_override_policy_uses_code_fallback_when_default_yaml_missing() -> (
    None
):
    merged = load_vdyp_override_policy(default_policy_path=Path("missing-policy.yaml"))
    assert merged["29"][("SBPS_PL", "L")]["skip1"] == 50


def test_load_vdyp_override_policy_rejects_invalid_instance_yaml(
    tmp_path: Path,
) -> None:
    instance_path = tmp_path / "instance.yaml"
    instance_path.write_text(
        """
version: 1
tsa_overrides:
  "k3z":
    - stratum: "CWHvm_DR+HW"
      si: "L"
      kwargs:
        nested:
          unsupported: true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must be a scalar value"):
        load_vdyp_override_policy(
            default_policy_path=Path("missing-policy.yaml"),
            instance_policy_path=instance_path,
        )
