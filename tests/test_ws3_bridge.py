from __future__ import annotations

from pathlib import Path

import pandas as pd

from femic.ws3_bridge import build_ws3_sections_from_femic_woodstock


def _write_minimal_woodstock(woodstock_dir: Path) -> None:
    woodstock_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "tsa": "29",
                "au_id": 101,
                "stratum_code": "st101",
                "si_level": 14,
                "ifm": "managed",
                "curve_id": 5001,
                "age": 1,
                "volume": 2.5,
            },
            {
                "tsa": "29",
                "au_id": 101,
                "stratum_code": "st101",
                "si_level": 14,
                "ifm": "managed",
                "curve_id": 5001,
                "age": 2,
                "volume": 5.0,
            },
        ]
    ).to_csv(woodstock_dir / "woodstock_yields.csv", index=False)
    pd.DataFrame(
        [
            {
                "stand_id": 1,
                "tsa": "29",
                "au_id": 101,
                "ifm": "managed",
                "age": 1,
                "area_ha": 12.5,
            }
        ]
    ).to_csv(woodstock_dir / "woodstock_areas.csv", index=False)
    pd.DataFrame(
        [
            {
                "tsa": "29",
                "au_id": 101,
                "action_id": "cc",
                "from_ifm": "managed",
                "to_ifm": "managed",
                "min_age": 1,
                "max_age": 250,
                "managed_curve_id": 5001,
            }
        ]
    ).to_csv(woodstock_dir / "woodstock_actions.csv", index=False)
    pd.DataFrame(
        [
            {
                "tsa": "29",
                "au_id": 101,
                "action_id": "cc",
                "from_ifm": "managed",
                "to_ifm": "managed",
                "next_au_id": 101,
            }
        ]
    ).to_csv(woodstock_dir / "woodstock_transitions.csv", index=False)


def test_build_ws3_sections_from_femic_woodstock(tmp_path: Path) -> None:
    woodstock_dir = tmp_path / "woodstock"
    bridge_dir = tmp_path / "bridge"
    _write_minimal_woodstock(woodstock_dir)

    result = build_ws3_sections_from_femic_woodstock(
        woodstock_dir=woodstock_dir,
        output_dir=bridge_dir,
        model_name="tsa29_bridge",
    )

    assert result.lan_path.exists()
    assert result.are_path.exists()
    assert result.yld_path.exists()
    assert result.act_path.exists()
    assert result.trn_path.exists()
    assert "*THEME Timber Supply Area (TSA)" in result.lan_path.read_text()
    assert "*A 29 managed 101 st101 5001 1 12.500000" in result.are_path.read_text()
    assert "*Y 29 managed 101 st101 5001" in result.yld_path.read_text()
    assert "*ACTION cc Y" in result.act_path.read_text()
    assert "*CASE cc" in result.trn_path.read_text()
