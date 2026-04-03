from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from femic.pipeline.tipsy_config import (
    build_tipsy_params_from_config,
    load_tipsy_tsa_config,
    resolve_tipsy_runtime_options,
    resolve_tipsy_param_builder,
)
import femic.pipeline.tipsy_config as tipsy_config_module


def test_load_tipsy_tsa_config_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_tipsy_tsa_config(tsa_code="08", config_dir=tmp_path) is None


def test_load_tipsy_tsa_config_parses_and_validates(tmp_path: Path) -> None:
    path = tmp_path / "tsa08.yaml"
    path.write_text(
        """
schema_version: 1
tsa_code: "08"
rules:
  - id: spruce
    when:
      leading_species_in: ["SW"]
      bec_in: ["SBS"]
    assign:
      e: {Density: 1200, SPP_1: "SW", PCT_1: 100}
      f: {Density: 1100, SPP_1: "SW", PCT_1: 100}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    payload = load_tipsy_tsa_config(tsa_code="08", config_dir=tmp_path)
    assert payload is not None
    assert payload["tsa_code"] == "08"


def test_resolve_tipsy_runtime_options_defaults_and_overrides() -> None:
    default_dir, default_legacy = resolve_tipsy_runtime_options(env={})
    assert default_dir == "config/tipsy"
    assert default_legacy is False

    config_dir, use_legacy = resolve_tipsy_runtime_options(
        env={
            "FEMIC_TIPSY_CONFIG_DIR": "/tmp/custom",
            "FEMIC_TIPSY_USE_LEGACY": "1",
        }
    )
    assert config_dir == "/tmp/custom"
    assert use_legacy is True


def test_resolve_tipsy_param_builder_prefers_config_when_available(
    tmp_path: Path,
) -> None:
    (tmp_path / "tsa08.yaml").write_text(
        """
schema_version: 1
tsa_code: "08"
exclude_stratum_codes:
  - "SBS_SW+PL"
defaults:
  e: {Proportion: 1}
  f: {Proportion: 1}
rules:
  - id: spruce
    when:
      leading_species_in: ["SW"]
      bec_in: ["SBS"]
    assign:
      e: {Density: 1200, SPP_1: "SW", PCT_1: 100}
      f: {Density: 1100, SPP_1: "SW", PCT_1: 100}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    def _legacy_builder(
        *_args: object, **_kwargs: object
    ) -> dict[str, dict[str, object]]:
        raise AssertionError("legacy builder should not be used")

    builder, message = resolve_tipsy_param_builder(
        tsa_code="08",
        legacy_builder=_legacy_builder,
        config_dir=tmp_path,
        use_legacy=False,
    )
    assert "using config-driven TIPSY rules from" in message
    assert getattr(builder, "siteprod_si_fallback_by_species", {}) == {}
    assert getattr(builder, "excluded_stratum_codes", set()) == {"SBS_SW+PL"}
    out = builder(
        3001,
        {
            "ss": pd.DataFrame({"SITE_INDEX": [16.0], "BEC_ZONE_CODE": ["SBS"]}),
            "species": {"SW": {"pct": 60.0}},
        },
        {1: pd.DataFrame({"SI": [16.0], "% Stk": [90.0]})},
    )
    assert out["e"]["SPP_1"] == "SW"
    assert out["f"]["Density"] == 1100


def test_resolve_tipsy_param_builder_returns_legacy_when_enabled() -> None:
    sentinel = {"e": {"x": 1}, "f": {"y": 2}}

    def _legacy_builder(
        *_args: object, **_kwargs: object
    ) -> dict[str, dict[str, object]]:
        return sentinel

    builder, message = resolve_tipsy_param_builder(
        tsa_code="08",
        legacy_builder=_legacy_builder,
        config_dir="nonexistent",
        use_legacy=True,
    )
    assert "using legacy in-code TIPSY rules" in message
    assert builder(1, {}, {}) == sentinel


def test_resolve_tipsy_param_builder_raises_when_config_missing_and_not_legacy(
    tmp_path: Path,
) -> None:
    def _legacy_builder(
        *_args: object, **_kwargs: object
    ) -> dict[str, dict[str, object]]:
        return {"e": {}, "f": {}}

    with pytest.raises(RuntimeError, match="Missing TIPSY config for TSA 08"):
        resolve_tipsy_param_builder(
            tsa_code="08",
            legacy_builder=_legacy_builder,
            config_dir=tmp_path,
            use_legacy=False,
        )


def test_resolve_tipsy_param_builder_raises_when_cfg_path_lookup_inconsistent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tipsy_config_module,
        "load_tipsy_tsa_config",
        lambda **_kwargs: {"schema_version": 1, "tsa_code": "08", "rules": []},
    )
    monkeypatch.setattr(
        tipsy_config_module,
        "_resolve_tipsy_config_path",
        lambda **_kwargs: None,
    )

    with pytest.raises(RuntimeError, match="config path lookup returned None"):
        resolve_tipsy_param_builder(
            tsa_code="08",
            legacy_builder=lambda *_a, **_k: {"e": {}, "f": {}},
            config_dir="config/tipsy",
            use_legacy=False,
        )


def test_build_tipsy_params_from_config_assigns_rule_and_derived_fields() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "defaults": {
            "e": {"Proportion": 1, "Regen_Method": "P"},
            "f": {"Proportion": 1, "Regen_Method": "P"},
        },
        "rules": [
            {
                "id": "spruce_rule",
                "when": {"leading_species_in": ["SW"], "bec_in": ["SBS"]},
                "assign": {
                    "e": {"Density": 1200, "SPP_1": "SW", "PCT_1": 100},
                    "f": {"Density": 1100, "SPP_1": "SW", "PCT_1": 100},
                },
            }
        ],
    }
    au_data = {
        "ss": pd.DataFrame(
            {"SITE_INDEX": [16.0, 18.0], "BEC_ZONE_CODE": ["SBS", "SBS"]},
        ),
        "species": {"SW": {"pct": 60.0}},
    }
    vdyp_out = {
        1: pd.DataFrame({"SI": [17.0, 18.0], "% Stk": [85.0, 85.0]}),
        2: pd.DataFrame({"SI": [16.0, 17.0], "% Stk": [95.0, 95.0]}),
    }
    out = build_tipsy_params_from_config(
        au_id=3001,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["TBLno"] == 13001
    assert out["f"]["TBLno"] == 23001
    assert out["e"]["BEC"] == "SBS"
    assert out["e"]["SPP_1"] == "SW"
    assert out["f"]["Density"] == 1100


def test_build_tipsy_params_from_config_resolves_species_token_for_sx() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "defaults": {
            "e": {"SPP_1": "$leading_species_tipsy"},
            "f": {"SPP_1": "$leading_species_tipsy"},
        },
        "rules": [
            {
                "id": "spruce_rule",
                "when": {"leading_species_in": ["SX"]},
                "assign": {"e": {"Density": 1000}, "f": {"Density": 900}},
            }
        ],
    }
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["SBS"]}),
        "species": {"SX": {"pct": 70.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=3002,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["SPP_1"] == "SW"
    assert out["f"]["SPP_1"] == "SW"


def test_build_tipsy_params_from_config_applies_species_code_overrides() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "species_code_overrides": {"DR": "FD", "SX": "SW"},
        "defaults": {
            "e": {"SPP_1": "$leading_species_tipsy"},
            "f": {"SPP_1": "$leading_species_tipsy"},
        },
        "rules": [
            {
                "id": "decid_rule",
                "when": {"leading_species_in": ["DR"]},
                "assign": {
                    "e": {"Density": 1000, "PCT_1": 100},
                    "f": {"Density": 900, "PCT_1": 100},
                },
            }
        ],
    }
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["SBS"]}),
        "species": {"DR": {"pct": 100.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=3002,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["SPP_1"] == "FD"
    assert out["f"]["SPP_1"] == "FD"


def test_build_tipsy_params_from_config_normalizes_mix_sum_and_order() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "defaults": {"e": {}, "f": {"Regen_Method": "P"}},
        "rules": [
            {
                "id": "mix",
                "when": {"leading_species_in": ["FD"]},
                "assign": {
                    "e": {"SPP_1": "FD", "PCT_1": 100},
                    "f": {
                        "SPP_1": "FD",
                        "PCT_1": 24,
                        "SPP_2": "PLI",
                        "PCT_2": 42,
                        "SPP_3": "AT",
                        "PCT_3": 17,
                        "SPP_4": "SX",
                        "PCT_4": 15,
                        "SPP_5": "BL",
                        "PCT_5": 3,
                    },
                },
            }
        ],
    }
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["IDF"]}),
        "species": {"FD": {"pct": 100.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=3003,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    pct_sum = sum(
        int(out["f"][f"PCT_{idx}"])
        for idx in range(1, 6)
        if out["f"].get(f"PCT_{idx}") is not None
    )
    assert pct_sum == 100
    assert out["f"]["SPP_1"] == "PLI"
    assert out["f"]["PCT_1"] >= out["f"]["PCT_2"]
    assert "AT" not in [out["f"].get(f"SPP_{idx}") for idx in range(1, 6)]
    assert "SX" not in [out["f"].get(f"SPP_{idx}") for idx in range(1, 6)]
    assert "SW" in [out["f"].get(f"SPP_{idx}") for idx in range(1, 6)]


def test_build_tipsy_params_from_config_preserves_explicit_side_proportions() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "29",
        "defaults": {
            "e": {"Regen_Method": "N", "Proportion": 1},
            "f": {"Regen_Method": "P", "Proportion": 1},
        },
        "rules": [
            {
                "id": "mixed_share",
                "when": {"leading_species_in": ["PL"]},
                "assign": {
                    "e": {
                        "Proportion": 0.15,
                        "Density": 1133,
                        "SPP_1": "PL",
                        "PCT_1": 62,
                        "SPP_2": "AT",
                        "PCT_2": 17,
                    },
                    "f": {
                        "Proportion": 0.85,
                        "Density": 1133,
                        "SPP_1": "PL",
                        "PCT_1": 62,
                        "SPP_2": "FD",
                        "PCT_2": 8,
                    },
                },
            }
        ],
    }
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["IDF"]}),
        "species": {"PL": {"pct": 100.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [90.0]})}

    out = build_tipsy_params_from_config(
        au_id=3004,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )

    assert out["e"]["Proportion"] == 0.15
    assert out["f"]["Proportion"] == 0.85
    assert out["e"]["SPP_1"] == "PL"
    assert out["e"]["SPP_2"] == "AT"
    assert out["f"]["SPP_1"] == "PL"
    assert out["f"]["SPP_2"] == "FD"


def test_build_tipsy_params_from_config_applies_side_specific_si_offset() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "defaults": {
            "e": {"Regen_Method": "P"},
            "f": {"Regen_Method": "P", "SI_offset": 2},
        },
        "rules": [
            {
                "id": "spruce_rule",
                "when": {"leading_species_in": ["SW"]},
                "assign": {
                    "e": {"Density": 1200, "SPP_1": "SW", "PCT_1": 100},
                    "f": {"Density": 1100, "SPP_1": "SW", "PCT_1": 100},
                },
            }
        ],
    }
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["SBS"]}),
        "species": {"SW": {"pct": 100.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=3010,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["SI"] == 15.0
    assert out["f"]["SI"] == 17.0
    assert "SI_offset" not in out["f"]


def test_build_tipsy_params_from_config_applies_linear_si_transform() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "defaults": {
            "e": {"Regen_Method": "P"},
            "f": {"Regen_Method": "P", "SI_c1": 1.1, "SI_c2": 2.0},
        },
        "rules": [
            {
                "id": "spruce_rule",
                "when": {"leading_species_in": ["SW"]},
                "assign": {
                    "e": {"Density": 1200, "SPP_1": "SW", "PCT_1": 100},
                    "f": {"Density": 1100, "SPP_1": "SW", "PCT_1": 100},
                },
            }
        ],
    }
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["SBS"]}),
        "species": {"SW": {"pct": 100.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=3011,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["SI"] == 15.0
    assert out["f"]["SI"] == 18.5
    assert "SI_c1" not in out["f"]
    assert "SI_c2" not in out["f"]


def test_repo_tsa16_config_loads_and_matches_spruce_rule() -> None:
    cfg = load_tipsy_tsa_config(tsa_code="16", config_dir="config/tipsy")
    assert cfg is not None
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [18.0], "BEC_ZONE_CODE": ["SBS"]}),
        "species": {"SW": {"pct": 55.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [18.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=4001,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["Density"] == 1147
    assert out["f"]["Density"] == 1245
    assert out["e"]["SPP_1"] == "SW"
    assert out["f"]["SPP_2"] == "PLI"


def test_repo_tsa24_config_loads_and_matches_sbs_pine_rule() -> None:
    cfg = load_tipsy_tsa_config(tsa_code="24", config_dir="config/tipsy")
    assert cfg is not None
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [16.0], "BEC_ZONE_CODE": ["SBS"]}),
        "species": {"PL": {"pct": 70.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [16.0], "% Stk": [88.0]})}
    out = build_tipsy_params_from_config(
        au_id=5001,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["Density"] == 5700
    assert out["f"]["Density"] == 1700
    assert out["e"]["Regen_Method"] == "N"
    assert out["f"]["SPP_1"] == "PL"


def test_repo_tsa24_config_loads_and_matches_essf_spruce_rule() -> None:
    cfg = load_tipsy_tsa_config(tsa_code="24", config_dir="config/tipsy")
    assert cfg is not None
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["ESSF"]}),
        "species": {"SW": {"pct": 60.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [92.0]})}
    out = build_tipsy_params_from_config(
        au_id=5002,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["Density"] == 1500
    assert out["e"]["SPP_1"] == "SE"
    assert out["f"]["GW_1"] == 18


def test_repo_tsa40_config_uses_ranked_species_tokens() -> None:
    cfg = load_tipsy_tsa_config(tsa_code="40", config_dir="config/tipsy")
    assert cfg is not None
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [17.0], "BEC_ZONE_CODE": ["BWBS"]}),
        "species": {"SX": {"pct": 60.0}, "AT": {"pct": 30.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [17.0], "% Stk": [89.0]})}
    out = build_tipsy_params_from_config(
        au_id=6001,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["SPP_1"] == "SW"
    assert out["e"]["PCT_1"] == 60.0
    assert out["e"]["SPP_2"] == "AT"
    assert out["e"]["PCT_2"] == 30.0
    assert out["f"]["Density"] == 1167


def test_repo_tsa41_config_matches_forest_type_rule() -> None:
    cfg = load_tipsy_tsa_config(tsa_code="41", config_dir="config/tipsy")
    assert cfg is not None
    au_data = {
        "ss": pd.DataFrame(
            {"SITE_INDEX": [16.0], "BEC_ZONE_CODE": ["BWBS"], "forest_type": [1]}
        ),
        "species": {"PL": {"pct": 65.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [16.0], "% Stk": [93.0]})}
    out = build_tipsy_params_from_config(
        au_id=6002,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["SPP_1"] == "PL"
    assert out["f"]["PCT_2"] == 27
    assert out["e"]["Density"] == 1219


def test_repo_tsa29_config_matches_pine_ms_rule() -> None:
    cfg = load_tipsy_tsa_config(tsa_code="29", config_dir="config/tipsy")
    assert cfg is not None
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [12.0], "BEC_ZONE_CODE": ["MS"]}),
        "species": {"PL": {"pct": 70.0}, "SX": {"pct": 30.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [12.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=7001,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["Density"] == 1133
    assert out["e"]["SPP_1"] == "PL"
    assert out["e"]["PCT_1"] == 62
    assert out["e"]["SPP_2"] == "AT"
    assert out["f"]["GW_1"] == 3.0
    assert out["f"]["SI"] == 14.0
    assert "AT" not in [out["f"].get(f"SPP_{idx}") for idx in range(1, 6)]
    assert "SX" not in [out["f"].get(f"SPP_{idx}") for idx in range(1, 6)]
    assert out["f"]["Util_DBH_cm"] == 12.5


def test_repo_tsa29_config_matches_idf_fir_rule() -> None:
    cfg = load_tipsy_tsa_config(tsa_code="29", config_dir="config/tipsy")
    assert cfg is not None
    au_data = {
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["IDF"]}),
        "species": {"FDI": {"pct": 100.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [88.0]})}
    out = build_tipsy_params_from_config(
        au_id=7002,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["SPP_1"] == "PL"
    assert out["e"]["PCT_1"] == 41
    assert (
        sum(
            int(out["e"][f"PCT_{idx}"])
            for idx in range(1, 6)
            if out["e"].get(f"PCT_{idx}") is not None
        )
        == 100
    )
    assert out["f"]["SPP_1"] == "PLI"
    assert out["f"]["SI"] == 17.0
    assert out["f"]["GW_1"] == 9.0
    assert out["f"]["Density"] == 1139


def test_repo_all_legacy_tsa_configs_present() -> None:
    for tsa in ("08", "16", "24", "40", "41"):
        payload = load_tipsy_tsa_config(tsa_code=tsa, config_dir="config/tipsy")
        assert payload is not None


def test_build_tipsy_params_from_config_handles_missing_forest_type_mode() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "rules": [
            {
                "id": "spruce_rule",
                "when": {"leading_species_in": ["SW"], "bec_in": ["SBS"]},
                "assign": {
                    "e": {"Density": 1200, "SPP_1": "SW", "PCT_1": 100},
                    "f": {"Density": 1100, "SPP_1": "SW", "PCT_1": 100},
                },
            }
        ],
    }
    au_data = {
        "ss": pd.DataFrame(
            {
                "SITE_INDEX": [16.0, 18.0],
                "BEC_ZONE_CODE": ["SBS", "SBS"],
                "forest_type": [float("nan"), float("nan")],
            }
        ),
        "species": {"SW": {"pct": 60.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [17.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=7001,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["SPP_1"] == "SW"
    assert out["f"]["Density"] == 1100


def test_build_tipsy_params_from_config_unexpected_forest_type_error_propagates() -> (
    None
):
    class _BadInt:
        def __int__(self) -> int:
            raise ZeroDivisionError("unexpected")

    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "rules": [
            {
                "id": "spruce_rule",
                "when": {"leading_species_in": ["SW"], "bec_in": ["SBS"]},
                "assign": {
                    "e": {"Density": 1200, "SPP_1": "SW", "PCT_1": 100},
                    "f": {"Density": 1100, "SPP_1": "SW", "PCT_1": 100},
                },
            }
        ],
    }
    au_data = {
        "ss": pd.DataFrame(
            {
                "SITE_INDEX": [16.0],
                "BEC_ZONE_CODE": ["SBS"],
                "forest_type": [_BadInt()],
            }
        ),
        "species": {"SW": {"pct": 60.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [17.0], "% Stk": [90.0]})}
    with pytest.raises(ZeroDivisionError):
        build_tipsy_params_from_config(
            au_id=7002,
            au_data=au_data,
            vdyp_out=vdyp_out,
            config=cfg,
        )


def test_build_tipsy_params_from_config_matches_on_stratum_code() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "defaults": {
            "e": {"Proportion": 1, "Regen_Method": "P"},
            "f": {"Proportion": 1, "Regen_Method": "P"},
        },
        "rules": [
            {
                "id": "fd_pair",
                "when": {"stratum_code_in": ["CWHvm_HW+FDC"]},
                "assign": {
                    "e": {
                        "Density": 4000,
                        "SPP_1": "HW",
                        "PCT_1": 77.5,
                        "SPP_2": "FD",
                        "PCT_2": 22.5,
                    },
                    "f": {
                        "Density": 4000,
                        "SPP_1": "HW",
                        "PCT_1": 77.5,
                        "SPP_2": "FD",
                        "PCT_2": 22.5,
                    },
                },
            }
        ],
    }
    au_data = {
        "stratum_code": "CWHvm_HW+FDC",
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["CWH"]}),
        "species": {"HW": {"pct": 70.0}, "FD": {"pct": 30.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=3002,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["Density"] == 4000
    assert out["e"]["SPP_1"] == "HW"
    assert out["e"]["SPP_2"] == "FD"


def test_build_tipsy_params_from_config_matches_on_au_id() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "defaults": {
            "e": {"Proportion": 1, "Regen_Method": "P"},
            "f": {"Proportion": 1, "Regen_Method": "P"},
        },
        "rules": [
            {
                "id": "targeted_au",
                "when": {"au_id_in": [985503000]},
                "assign": {
                    "e": {
                        "Density": 4000,
                        "SPP_1": "HW",
                        "PCT_1": 78,
                        "SPP_2": "CW",
                        "PCT_2": 22,
                    },
                    "f": {
                        "Density": 4000,
                        "SPP_1": "HW",
                        "PCT_1": 78,
                        "SPP_2": "CW",
                        "PCT_2": 22,
                    },
                },
            },
            {
                "id": "fallback_fd_pair",
                "when": {"stratum_code_in": ["CWHvm_HW+FDC"]},
                "assign": {
                    "e": {
                        "Density": 4000,
                        "SPP_1": "HW",
                        "PCT_1": 78,
                        "SPP_2": "FD",
                        "PCT_2": 22,
                    },
                    "f": {
                        "Density": 4000,
                        "SPP_1": "HW",
                        "PCT_1": 78,
                        "SPP_2": "FD",
                        "PCT_2": 22,
                    },
                },
            },
        ],
    }
    au_data = {
        "stratum_code": "CWHvm_HW+FDC",
        "si_level": "H",
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["CWH"]}),
        "species": {"HW": {"pct": 70.0}, "FD": {"pct": 30.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=985503000,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["SPP_1"] == "HW"
    assert out["e"]["SPP_2"] == "CW"


def test_build_tipsy_params_from_config_matches_on_si_level() -> None:
    cfg = {
        "schema_version": 1,
        "tsa_code": "08",
        "defaults": {
            "e": {"Proportion": 1, "Regen_Method": "P"},
            "f": {"Proportion": 1, "Regen_Method": "P"},
        },
        "rules": [
            {
                "id": "high_si_fd_pair",
                "when": {"stratum_code_in": ["CWHvm_FDC+HW"], "si_level_in": ["H"]},
                "assign": {
                    "e": {
                        "Density": 4000,
                        "SPP_1": "HW",
                        "PCT_1": 78,
                        "SPP_2": "CW",
                        "PCT_2": 22,
                    },
                    "f": {
                        "Density": 4000,
                        "SPP_1": "HW",
                        "PCT_1": 78,
                        "SPP_2": "CW",
                        "PCT_2": 22,
                    },
                },
            },
            {
                "id": "fd_pair_fallback",
                "when": {"stratum_code_in": ["CWHvm_FDC+HW"]},
                "assign": {
                    "e": {
                        "Density": 4000,
                        "SPP_1": "HW",
                        "PCT_1": 78,
                        "SPP_2": "FD",
                        "PCT_2": 22,
                    },
                    "f": {
                        "Density": 4000,
                        "SPP_1": "HW",
                        "PCT_1": 78,
                        "SPP_2": "FD",
                        "PCT_2": 22,
                    },
                },
            },
        ],
    }
    au_data = {
        "stratum_code": "CWHvm_FDC+HW",
        "si_level": "H",
        "ss": pd.DataFrame({"SITE_INDEX": [15.0], "BEC_ZONE_CODE": ["CWH"]}),
        "species": {"HW": {"pct": 70.0}, "FD": {"pct": 30.0}},
    }
    vdyp_out = {1: pd.DataFrame({"SI": [15.0], "% Stk": [90.0]})}
    out = build_tipsy_params_from_config(
        au_id=985503001,
        au_data=au_data,
        vdyp_out=vdyp_out,
        config=cfg,
    )
    assert out["e"]["SPP_2"] == "CW"
