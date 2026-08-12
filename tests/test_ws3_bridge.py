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
                "landscape_unit_id": 1376,
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
    lan_text = result.lan_path.read_text()
    assert "*THEME Landscape Unit" in lan_text
    assert "*AGGREGATE masc_lu_subset" in lan_text
    assert "1376 1378 1382 1383 1384 1387 1389 1390 1391 1393 1404" in lan_text
    assert (
        "*A 29 managed 101 st101 5001 1376 1 12.500000" in result.are_path.read_text()
    )
    yld_header = next(
        line
        for line in result.yld_path.read_text().splitlines()
        if line.startswith("*Y ")
    )
    assert yld_header.split() == ["*Y", "29", "managed", "101", "st101", "5001", "?"]
    act_operable = next(
        line
        for line in result.act_path.read_text().splitlines()
        if line.startswith("29 ")
    )
    assert act_operable.split()[:6] == ["29", "managed", "101", "?", "?", "?"]
    trn_lines = result.trn_path.read_text().splitlines()
    assert next(line for line in trn_lines if line.startswith("*SOURCE")).split() == [
        "*SOURCE",
        "29",
        "managed",
        "101",
        "?",
        "?",
        "?",
    ]
    assert next(line for line in trn_lines if line.startswith("*TARGET")).split() == [
        "*TARGET",
        "29",
        "managed",
        "101",
        "st101",
        "5001",
        "?",
        "100",
    ]


def test_legacy_five_theme_yield_header_remains_compatible(tmp_path: Path) -> None:
    woodstock_dir = tmp_path / "woodstock"
    bridge_dir = tmp_path / "bridge"
    _write_minimal_woodstock(woodstock_dir)
    areas = pd.read_csv(woodstock_dir / "woodstock_areas.csv").drop(
        columns=["landscape_unit_id"]
    )
    areas.to_csv(woodstock_dir / "woodstock_areas.csv", index=False)

    result = build_ws3_sections_from_femic_woodstock(
        woodstock_dir=woodstock_dir,
        output_dir=bridge_dir,
        model_name="legacy_bridge",
    )

    yld_header = next(
        line
        for line in result.yld_path.read_text().splitlines()
        if line.startswith("*Y ")
    )
    assert yld_header.split() == ["*Y", "29", "managed", "101", "st101", "5001"]
    assert "*THEME Landscape Unit" not in result.lan_path.read_text()
    act_operable = next(
        line
        for line in result.act_path.read_text().splitlines()
        if line.startswith("29 ")
    )
    assert act_operable.split()[:5] == ["29", "managed", "101", "?", "?"]
    trn_lines = result.trn_path.read_text().splitlines()
    assert next(line for line in trn_lines if line.startswith("*SOURCE")).split() == [
        "*SOURCE",
        "29",
        "managed",
        "101",
        "?",
        "?",
    ]
    assert next(line for line in trn_lines if line.startswith("*TARGET")).split() == [
        "*TARGET",
        "29",
        "managed",
        "101",
        "st101",
        "5001",
        "100",
    ]
