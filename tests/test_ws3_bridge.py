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
    assert "*TARGET 29 managed 101 st101 5001 0" in result.trn_path.read_text()
    assert "*THEME Timber Supply Area (TSA)" in result.lan_path.read_text()
    # .are/.yld ages are in periods (1 year // 5 = 0 periods)
    assert "*A 29 managed 101 st101 5001 0 12.500000" in result.are_path.read_text()
    yld_text = result.yld_path.read_text()
    assert "_AGE totvol" in yld_text
    # yearly samples collapse to one per period, midpoint-closest row wins
    # (ages 1,2 in period 0 -> midpoint 2.5 -> age 2 kept)
    assert "\n0 5.000000" in yld_text
    assert "*Y 29 managed 101 st101 5001" in result.yld_path.read_text()
    assert "*ACTION cc Y" in result.act_path.read_text()
    assert "*CASE cc" in result.trn_path.read_text()


def test_export_ws3_sections_cli_round_trip(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from femic.cli.main import app

    woodstock_dir = tmp_path / "output" / "woodstock"
    _write_minimal_woodstock(woodstock_dir)
    output_dir = tmp_path / "output" / "ws3"

    result = CliRunner().invoke(
        app,
        [
            "export",
            "ws3-sections",
            "--instance-root",
            str(tmp_path),
            "--woodstock-dir",
            "output/woodstock",
            "--output-dir",
            "output/ws3",
            "--model-name",
            "tsa29",
        ],
    )

    assert result.exit_code == 0, result.output
    for suffix in ("lan", "are", "yld", "act", "trn"):
        assert (output_dir / f"tsa29.{suffix}").is_file()


def test_ws3_bridge_writes_species_split_products(tmp_path: Path) -> None:
    woodstock_dir = tmp_path / "woodstock"
    _write_minimal_woodstock(woodstock_dir)
    yields_path = woodstock_dir / "woodstock_yields.csv"
    yields = pd.read_csv(yields_path)
    yields["product"] = "totvol"
    species_rows = yields.copy()
    species_rows["product"] = "swdvol"
    species_rows["volume"] = species_rows["volume"] * 0.8
    hardwood_rows = yields.copy()
    hardwood_rows["product"] = "hwdvol"
    hardwood_rows["volume"] = hardwood_rows["volume"] * 0.2
    pd.concat([yields, species_rows, hardwood_rows], ignore_index=True).to_csv(
        yields_path, index=False
    )

    output_dir = tmp_path / "ws3"
    result = build_ws3_sections_from_femic_woodstock(
        woodstock_dir=woodstock_dir,
        output_dir=output_dir,
        model_name="tsa29",
    )

    text = result.yld_path.read_text()
    assert "_AGE totvol" in text
    assert "_AGE swdvol" in text
    assert "_AGE hwdvol" in text
