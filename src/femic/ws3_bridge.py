"""Adapter utilities to convert FEMIC Woodstock CSV exports into ws3 section files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, cast

import pandas as pd

from femic.fmg.woodstock import (
    DEFAULT_WOODSTOCK_CC_MAX_AGE,
    DEFAULT_WOODSTOCK_CC_MIN_AGE,
    export_woodstock_package,
    WoodstockExportResult,
)
from .fmg.adapters import build_bundle_model_context


@dataclass(frozen=True)
class Ws3BridgeResult:
    """Paths for generated ws3-compatible Woodstock section files."""

    model_name: str
    output_dir: Path
    lan_path: Path
    are_path: Path
    yld_path: Path
    act_path: Path
    trn_path: Path


def build_ws3_sections_from_femic_woodstock(
    *,
    woodstock_dir: Path,
    output_dir: Path,
    model_name: str = "femic_ws3_bridge",
) -> Ws3BridgeResult:
    """Convert FEMIC Woodstock CSV outputs to ws3 Woodstock section text files."""
    resolved_input = woodstock_dir.expanduser().resolve()
    resolved_output = output_dir.expanduser().resolve()
    yields = pd.read_csv(resolved_input / "woodstock_yields.csv")
    areas = pd.read_csv(resolved_input / "woodstock_areas.csv")
    actions = pd.read_csv(resolved_input / "woodstock_actions.csv")
    transitions = pd.read_csv(resolved_input / "woodstock_transitions.csv")

    for frame, name in (
        (yields, "yields"),
        (areas, "areas"),
        (actions, "actions"),
        (transitions, "transitions"),
    ):
        if frame.empty:
            raise ValueError(f"Woodstock {name} table is empty.")

    # Normalize primitive string/int fields used as Woodstock theme keys.
    yields["tsa"] = yields["tsa"].astype(str).str.lower()
    yields["ifm"] = yields["ifm"].astype(str).str.lower()
    yields["au_id"] = (
        pd.to_numeric(yields["au_id"], errors="coerce").fillna(-1).astype(int)
    )
    if "stratum_code" not in yields.columns:
        yields["stratum_code"] = yields["au_id"].map(lambda value: f"au{int(value)}")
    yields["curve_id"] = (
        pd.to_numeric(yields["curve_id"], errors="coerce").fillna(-1).astype(int)
    )
    yields["stratum_code"] = yields["stratum_code"].astype(str).str.lower()
    yields["age"] = pd.to_numeric(yields["age"], errors="coerce").fillna(0).astype(int)
    yields["volume"] = pd.to_numeric(yields["volume"], errors="coerce").fillna(0.0)

    areas["tsa"] = areas["tsa"].astype(str).str.lower()
    areas["ifm"] = areas["ifm"].astype(str).str.lower()
    areas["au_id"] = (
        pd.to_numeric(areas["au_id"], errors="coerce").fillna(-1).astype(int)
    )
    areas["age"] = pd.to_numeric(areas["age"], errors="coerce").fillna(0).astype(int)
    areas["area_ha"] = pd.to_numeric(areas["area_ha"], errors="coerce").fillna(0.0)

    actions["tsa"] = actions["tsa"].astype(str).str.lower()
    actions["from_ifm"] = actions["from_ifm"].astype(str).str.lower()
    actions["to_ifm"] = actions["to_ifm"].astype(str).str.lower()
    actions["au_id"] = (
        pd.to_numeric(actions["au_id"], errors="coerce").fillna(-1).astype(int)
    )
    if "min_age" not in actions.columns:
        actions["min_age"] = 0
    if "max_age" not in actions.columns:
        actions["max_age"] = 1000
    actions["action_id"] = actions["action_id"].astype(str).str.lower()
    actions["min_age"] = (
        pd.to_numeric(actions["min_age"], errors="coerce").fillna(0).astype(int)
    )
    actions["max_age"] = (
        pd.to_numeric(actions["max_age"], errors="coerce").fillna(1000).astype(int)
    )

    transitions["tsa"] = transitions["tsa"].astype(str).str.lower()
    transitions["from_ifm"] = transitions["from_ifm"].astype(str).str.lower()
    transitions["to_ifm"] = transitions["to_ifm"].astype(str).str.lower()
    transitions["action_id"] = transitions["action_id"].astype(str).str.lower()
    transitions["au_id"] = (
        pd.to_numeric(transitions["au_id"], errors="coerce").fillna(-1).astype(int)
    )
    if "next_au_id" not in transitions.columns:
        transitions["next_au_id"] = transitions["au_id"]
    transitions["next_au_id"] = (
        pd.to_numeric(transitions["next_au_id"], errors="coerce").fillna(-1).astype(int)
    )

    # Curve map picks one representative curve per (tsa, ifm, au).
    curve_map = (
        yields.sort_values(["tsa", "ifm", "au_id", "curve_id"])
        .groupby(["tsa", "ifm", "au_id"], as_index=False)
        .agg(curve_id=("curve_id", "first"), stratum_code=("stratum_code", "first"))
    )
    if curve_map.empty:
        raise ValueError(
            "No curve mapping could be inferred from woodstock_yields.csv."
        )

    resolved_output.mkdir(parents=True, exist_ok=True)
    lan_path = resolved_output / f"{model_name}.lan"
    are_path = resolved_output / f"{model_name}.are"
    yld_path = resolved_output / f"{model_name}.yld"
    act_path = resolved_output / f"{model_name}.act"
    trn_path = resolved_output / f"{model_name}.trn"

    _write_lan(
        path=lan_path,
        tsa_codes=sorted(set(curve_map["tsa"].tolist())),
        ifm_codes=sorted(set(curve_map["ifm"].tolist())),
        au_ids=sorted(set(int(v) for v in curve_map["au_id"].tolist())),
        stratum_codes=sorted(set(curve_map["stratum_code"].tolist())),
        curve_ids=sorted(set(int(v) for v in curve_map["curve_id"].tolist())),
    )

    _write_are(
        path=are_path,
        areas=areas,
        curve_map=curve_map,
    )

    _write_yld(
        path=yld_path,
        yields=yields,
        curve_map=curve_map,
    )

    _write_act(path=act_path, actions=actions)
    _write_trn(path=trn_path, transitions=transitions, curve_map=curve_map)

    return Ws3BridgeResult(
        model_name=model_name,
        output_dir=resolved_output,
        lan_path=lan_path,
        are_path=are_path,
        yld_path=yld_path,
        act_path=act_path,
        trn_path=trn_path,
    )


def _write_lan(
    *,
    path: Path,
    tsa_codes: list[str],
    ifm_codes: list[str],
    au_ids: list[int],
    stratum_codes: list[str],
    curve_ids: list[int],
) -> None:
    lines: list[str] = []
    lines.append("*THEME Timber Supply Area (TSA)")
    lines.extend(tsa_codes)
    lines.append("*THEME Managed state")
    lines.extend(ifm_codes)
    lines.append("*THEME Analysis Unit (AU)")
    lines.extend(str(v) for v in au_ids)
    lines.append("*THEME Stratum code")
    lines.extend(str(v) for v in stratum_codes)
    lines.append("*THEME Yield curve ID")
    lines.extend(str(v) for v in curve_ids)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_are(*, path: Path, areas: pd.DataFrame, curve_map: pd.DataFrame) -> None:
    merged = areas.merge(curve_map, on=["tsa", "ifm", "au_id"], how="left")
    merged = merged.dropna(subset=["curve_id", "stratum_code"])
    merged["curve_id"] = merged["curve_id"].astype(int)
    grouped = (
        merged.groupby(
            ["tsa", "ifm", "au_id", "stratum_code", "curve_id", "age"], as_index=False
        )
        .agg(area_ha=("area_ha", "sum"))
        .sort_values(["tsa", "ifm", "au_id", "curve_id", "age"])
    )
    lines = [
        (
            f"*A {row.tsa} {row.ifm} {_to_int(row.au_id)} {row.stratum_code} "
            f"{_to_int(row.curve_id)} {_to_int(row.age)} {_to_float(row.area_ha):.6f}"
        )
        for row in grouped.itertuples()
        if _to_float(row.area_ha) > 0
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_yld(*, path: Path, yields: pd.DataFrame, curve_map: pd.DataFrame) -> None:
    lines: list[str] = []
    seen_blocks: set[tuple[str, str, int, str, int]] = set()
    for row in curve_map.sort_values(["tsa", "ifm", "au_id", "curve_id"]).itertuples():
        key = (
            str(row.tsa),
            str(row.ifm),
            _to_int(row.au_id),
            str(row.stratum_code),
            _to_int(row.curve_id),
        )
        if key in seen_blocks:
            continue
        seen_blocks.add(key)
        subset = yields[
            (yields["tsa"] == key[0])
            & (yields["ifm"] == key[1])
            & (yields["au_id"] == key[2])
            & (yields["curve_id"] == key[4])
        ].sort_values("age")
        if subset.empty:
            continue
        lines.append(f"*Y {key[0]} {key[1]} {key[2]} {key[3]} {key[4]}")
        lines.append("_AGE totvol")
        for r in subset.itertuples():
            lines.append(f"{_to_int(r.age)} {_to_float(r.volume):.6f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_act(*, path: Path, actions: pd.DataFrame) -> None:
    lines: list[str] = ["ACTIONS"]
    for action_id, block in actions.groupby("action_id"):
        lines.append(f"*ACTION {action_id} Y")
        lines.append(f"*OPERABLE {action_id}")
        for row in (
            block[["tsa", "from_ifm", "au_id", "min_age", "max_age"]]
            .drop_duplicates()
            .itertuples(index=False)
        ):
            lines.append(
                f"{row.tsa} {row.from_ifm} {_to_int(row.au_id)} ? ? "
                f"_AGE >= {_to_int(row.min_age)} AND _AGE <= {_to_int(row.max_age)}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_trn(
    *,
    path: Path,
    transitions: pd.DataFrame,
    curve_map: pd.DataFrame,
) -> None:
    curve_lookup: dict[tuple[str, str, int], tuple[str, int]] = {}
    for row in curve_map.itertuples(index=False):
        curve_lookup[(str(row.tsa), str(row.ifm), _to_int(row.au_id))] = (
            str(row.stratum_code),
            _to_int(row.curve_id),
        )

    lines: list[str] = []
    for action_id, block in transitions.groupby("action_id"):
        lines.append(f"*CASE {action_id}")
        for row in (
            block[["tsa", "from_ifm", "au_id", "to_ifm", "next_au_id"]]
            .drop_duplicates()
            .itertuples(index=False)
        ):
            lines.append(f"*SOURCE {row.tsa} {row.from_ifm} {_to_int(row.au_id)} ? ?")
            target_key = (str(row.tsa), str(row.to_ifm), _to_int(row.next_au_id))
            target = curve_lookup.get(target_key)
            if target is None:
                # fallback: retain source AU and IFM
                target = curve_lookup.get(
                    (str(row.tsa), str(row.from_ifm), _to_int(row.au_id))
                )
            if target is None:
                continue
            stratum_code, curve_id = target
            lines.append(
                f"*TARGET {row.tsa} {row.to_ifm} {_to_int(row.next_au_id)} {stratum_code} {curve_id} 100"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _to_int(value: object) -> int:
    return int(cast(Any, value))


def _to_float(value: object) -> float:
    return float(cast(Any, value))


@dataclass(frozen=True)
class Ws3ExportResult:
    """Paths and counts from a FEMIC → ws3 section file export."""

    woodstock: WoodstockExportResult
    model_name: str
    output_dir: Path
    woodstock_dir: Path
    ws3_dir: Path
    lan_path: Path
    are_path: Path
    yld_path: Path
    act_path: Path
    trn_path: Path
    tsa_list: list[str]
    au_count: int
    yield_rows: int
    area_rows: int
    action_rows: int
    transition_rows: int


# Default operability bounds for clearcut actions in TSA models.
DEFAULT_WS3_CC_MIN_AGE = 60
DEFAULT_WS3_CC_MAX_AGE = 300


def export_ws3_package(
    *,
    bundle_dir: Path,
    checkpoint_path: Path | None = None,
    woodstock_dir: Path | None = None,
    output_dir: Path,
    model_name: str = "femic_ws3",
    tsa_list: Iterable[str],
    cc_min_age: int = DEFAULT_WS3_CC_MIN_AGE,
    cc_max_age: int = DEFAULT_WS3_CC_MAX_AGE,
    fragments_crs: str = "EPSG:3005",
) -> Ws3ExportResult:
    """Export ws3-compatible section files from FEMIC bundle inputs.

    Two modes:
    1. With ``checkpoint_path``: full pipeline
       bundle + checkpoint → woodstock CSVs → ws3 section files
    2. With ``woodstock_dir``: bypass step 1; use pre-built woodstock CSVs
       (e.g. from a prior run or external source).

    Parameters
    ----------
    bundle_dir:
        Path to the model-input-bundle directory containing ``au_table.csv``,
        ``curve_table.csv``, and ``curve_points_table.csv``.
    checkpoint_path:
        Path to the FEMIC checkpoint Feather file (containing fragment geometries
        and age/IFM attributes used to build the areas table).
        Required when ``woodstock_dir`` is not provided.
    woodstock_dir:
        Path to a directory containing pre-built ``woodstock_yields.csv``,
        ``woodstock_areas.csv``, ``woodstock_actions.csv``, and
        ``woodstock_transitions.csv``.  When provided, the function skips the
        woodstock CSV generation step entirely.  Useful for instances built
        before the checkpoint Feather file was added to the pipeline, or when
        areas were computed by a separate process.
    output_dir:
        Directory where the final ws3 section files will be written
        (subdirectory ``<output_dir>/ws3/``).
    model_name:
        Stem for ws3 section files (default ``"femic_ws3"`` → ``femic_ws3.lan``,
        etc.).
    tsa_list:
        Iterable of TSA code strings to include in the model.
    cc_min_age:
        Lower operability bound for the clearcut action (default 60 yr).
    cc_max_age:
        Upper operability bound for the clearcut action (default 300 yr).
    fragments_crs:
        EPSG CRS string for the fragments shapefile
        (default ``"EPSG:3005"``).

    Returns
    -------
    Ws3ExportResult
        Paths to all generated files plus row/area counts for QA.
    """
    normalized_tsa = sorted({str(t).strip().lower() for t in tsa_list})
    if not normalized_tsa:
        raise ValueError("provide at least one TSA code for ws3 export")

    ws3_dir = Path(output_dir) / "ws3"

    if woodstock_dir is not None:
        # Mode 2: use pre-built woodstock CSVs, skip generation entirely
        woodstock_result = WoodstockExportResult(
            yields_csv_path=Path(woodstock_dir) / "woodstock_yields.csv",
            areas_csv_path=Path(woodstock_dir) / "woodstock_areas.csv",
            actions_csv_path=Path(woodstock_dir) / "woodstock_actions.csv",
            transitions_csv_path=Path(woodstock_dir) / "woodstock_transitions.csv",
            tsa_list=normalized_tsa,
            yield_rows=int(pd.read_csv(Path(woodstock_dir) / "woodstock_yields.csv").shape[0]),
            area_rows=int(pd.read_csv(Path(woodstock_dir) / "woodstock_areas.csv").shape[0]),
            action_rows=int(pd.read_csv(Path(woodstock_dir) / "woodstock_actions.csv").shape[0]),
            transition_rows=int(pd.read_csv(Path(woodstock_dir) / "woodstock_transitions.csv").shape[0]),
        )
        woodstock_dir_resolved = Path(woodstock_dir)
    elif checkpoint_path is not None:
        # Mode 1: generate woodstock CSVs from bundle + checkpoint
        woodstock_dir_resolved = Path(output_dir) / "woodstock"
        woodstock_result = export_woodstock_package(
            bundle_dir=bundle_dir,
            checkpoint_path=checkpoint_path,
            output_dir=woodstock_dir_resolved,
            tsa_list=normalized_tsa,
            cc_min_age=cc_min_age,
            cc_max_age=cc_max_age,
            fragments_crs=fragments_crs,
        )
    else:
        raise ValueError(
            "export_ws3_package requires either ``checkpoint_path`` or "
            "``woodstock_dir`` to be provided."
        )

    # Convert woodstock CSVs → ws3 section files
    bridge_result = build_ws3_sections_from_femic_woodstock(
        woodstock_dir=woodstock_dir_resolved,
        output_dir=ws3_dir,
        model_name=model_name,
    )

    # Count AUs from bundle context for accurate metadata
    context = build_bundle_model_context(
        bundle_dir=bundle_dir,
        tsa_list=normalized_tsa,
    )
    au_count = len(context.analysis_units)

    return Ws3ExportResult(
        woodstock=woodstock_result,
        model_name=model_name,
        output_dir=Path(output_dir),
        woodstock_dir=woodstock_dir_resolved,
        ws3_dir=ws3_dir,
        lan_path=bridge_result.lan_path,
        are_path=bridge_result.are_path,
        yld_path=bridge_result.yld_path,
        act_path=bridge_result.act_path,
        trn_path=bridge_result.trn_path,
        tsa_list=normalized_tsa,
        au_count=au_count,
        yield_rows=woodstock_result.yield_rows,
        area_rows=woodstock_result.area_rows,
        action_rows=woodstock_result.action_rows,
        transition_rows=woodstock_result.transition_rows,
    )
