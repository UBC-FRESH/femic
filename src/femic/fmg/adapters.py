"""Bundle-table adapters into shared FMG core objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from femic.pipeline.tsa import (
    assign_si_levels_from_stratum_quantiles,
    assign_stratum_matches_from_au_table,
    lookup_scsi_au_base,
)
from femic.pipeline.vri import assign_stratum_codes_with_lexmatch

from .core import (
    AnalysisUnitDefinition,
    BundleModelContext,
    CurveDefinition,
    CurvePoint,
    QmdSupportDefinition,
)


def normalize_tsa_code(value: Any) -> str:
    """Normalize TSA code to zero-padded numeric or lowercase text."""
    code = str(value).strip()
    if code.isdigit():
        return code.zfill(2)
    return code.lower()


def _coerce_int(value: Any) -> int:
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return int(value)
    return int(str(value))


def _load_bundle_tables(
    bundle_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    au_table = pd.read_csv(bundle_dir / "au_table.csv")
    curve_table = pd.read_csv(bundle_dir / "curve_table.csv")
    curve_points_table = pd.read_csv(bundle_dir / "curve_points_table.csv")
    return au_table, curve_table, curve_points_table


def _dedupe_au_table(au_table: pd.DataFrame) -> pd.DataFrame:
    if "au_id" not in au_table.columns:
        raise ValueError("au_table.csv missing required column: au_id")
    curve_cols = {
        "managed_curve_id": (
            "managed_curve_id"
            if "managed_curve_id" in au_table.columns
            else "treated_curve_id"
        ),
        "unmanaged_curve_id": (
            "unmanaged_curve_id"
            if "unmanaged_curve_id" in au_table.columns
            else "untreated_curve_id"
        ),
    }
    missing_curve_cols = [
        alias for alias, source in curve_cols.items() if source not in au_table.columns
    ]
    if missing_curve_cols:
        raise ValueError(
            "au_table.csv missing required curve id columns "
            "(need treated/untreated or managed/unmanaged ids)"
        )
    table = au_table.copy()
    table["managed_curve_id"] = table[curve_cols["managed_curve_id"]]
    table["unmanaged_curve_id"] = table[curve_cols["unmanaged_curve_id"]]
    deduped = (
        table.sort_values(["au_id"])
        .groupby("au_id", as_index=False)
        .agg(
            {
                "tsa": "first",
                "stratum_code": "first",
                "si_level": "first",
                "managed_curve_id": "first",
                "unmanaged_curve_id": "first",
            }
        )
    )
    deduped["au_id"] = deduped["au_id"].astype(int)
    deduped["managed_curve_id"] = deduped["managed_curve_id"].astype(int)
    deduped["unmanaged_curve_id"] = deduped["unmanaged_curve_id"].astype(int)
    return deduped


def _curve_points_by_id(
    curve_points_table: pd.DataFrame,
) -> dict[int, list[CurvePoint]]:
    if not {"curve_id", "x", "y"}.issubset(curve_points_table.columns):
        raise ValueError(
            "curve_points_table.csv missing required columns: curve_id,x,y"
        )

    out: dict[int, list[CurvePoint]] = {}
    for curve_id_raw, subdf in curve_points_table.groupby("curve_id"):
        curve_id = _coerce_int(curve_id_raw)
        rows = subdf.sort_values("x")
        out[curve_id] = [
            CurvePoint(x=float(x), y=float(y))
            for x, y in zip(rows["x"].tolist(), rows["y"].tolist())
        ]
    return out


def _thin_curve_points_to_decadal_knots(
    points: tuple[CurvePoint, ...],
) -> tuple[CurvePoint, ...]:
    if len(points) <= 2:
        return points
    thinned: list[CurvePoint] = []
    last_index = len(points) - 1
    for idx, point in enumerate(points):
        x_val = float(point.x)
        rounded_x = int(round(x_val))
        keep = (
            idx == 0
            or idx == last_index
            or (float(rounded_x) == x_val and rounded_x >= 0 and rounded_x % 10 == 0)
        )
        if keep:
            if not thinned or (
                float(thinned[-1].x) != x_val or float(thinned[-1].y) != float(point.y)
            ):
                thinned.append(point)
    return tuple(thinned)


def _species_curve_maps(
    curve_table: pd.DataFrame,
) -> tuple[dict[int, dict[str, int]], dict[int, dict[str, int]]]:
    managed: dict[int, dict[str, int]] = {}
    unmanaged: dict[int, dict[str, int]] = {}
    if not {"curve_id", "curve_type"}.issubset(curve_table.columns):
        return managed, unmanaged

    for _, row in curve_table.iterrows():
        curve_id = _coerce_int(row["curve_id"])
        curve_type = str(row["curve_type"])
        if curve_type.startswith(("managed_species_prop_", "treated_species_prop_")):
            if curve_type.startswith("managed_species_prop_"):
                species = curve_type.removeprefix("managed_species_prop_")
            else:
                species = curve_type.removeprefix("treated_species_prop_")
            base = curve_id // 1000
            managed.setdefault(base, {})[species] = curve_id
        elif curve_type.startswith(
            ("unmanaged_species_prop_", "untreated_species_prop_")
        ):
            if curve_type.startswith("unmanaged_species_prop_"):
                species = curve_type.removeprefix("unmanaged_species_prop_")
            else:
                species = curve_type.removeprefix("untreated_species_prop_")
            base = curve_id // 1000
            unmanaged.setdefault(base, {})[species] = curve_id
    return managed, unmanaged


_DEFAULT_QMD_SITE_INDEX_BY_LEVEL = {"L": 15.0, "M": 25.0, "H": 35.0}


def _curve_matches_points(
    curve_points: tuple[CurvePoint, ...],
    source_rows: pd.DataFrame,
) -> bool:
    if source_rows.empty or not curve_points:
        return False
    curve_df = pd.DataFrame(
        {
            "age": [float(point.x) for point in curve_points],
            "yield": [round(float(point.y), 1) for point in curve_points],
        }
    )
    source_df = source_rows.loc[:, ["Age", "Yield"]].copy()
    source_df["age"] = pd.to_numeric(source_df["Age"], errors="coerce")
    source_df["yield"] = pd.to_numeric(source_df["Yield"], errors="coerce").round(1)
    source_df = source_df.dropna(subset=["age", "yield"]).sort_values("age")
    curve_df = curve_df.sort_values("age")
    if len(curve_df) != len(source_df):
        return False
    return bool(
        np.array_equal(curve_df["age"].to_numpy(), source_df["age"].to_numpy())
        and np.array_equal(curve_df["yield"].to_numpy(), source_df["yield"].to_numpy())
    )


def _load_site_index_by_au_from_tipsy_input(data_dir: Path) -> dict[int, float]:
    workbook_path = data_dir / "tipsy_params_tsak3z.xlsx"
    if not workbook_path.is_file():
        return {}
    input_df = pd.read_excel(
        workbook_path,
        sheet_name="TIPSY_inputTBL",
        usecols=["AU", "SI"],
    )
    input_df["AU"] = pd.to_numeric(input_df["AU"], errors="coerce")
    input_df["SI"] = pd.to_numeric(input_df["SI"], errors="coerce")
    input_df = input_df.dropna(subset=["AU", "SI"])
    if input_df.empty:
        return {}
    return {
        _coerce_int(au): float(si)
        for au, si in input_df.groupby("AU")["SI"].median().items()
        if np.isfinite(float(si))
    }


def _load_managed_qmd_support_from_tipsy(
    *,
    data_dir: Path,
    analysis_units: tuple[AnalysisUnitDefinition, ...],
    points_by_id: dict[int, list[CurvePoint]],
) -> dict[int, dict[str, Any]]:
    tipsy_path = data_dir / "tipsy_curves_tsak3z.csv"
    if not tipsy_path.is_file():
        return {}
    tipsy_df = pd.read_csv(tipsy_path)
    required = {"AU", "Age", "Yield", "Height", "TPH"}
    if not required.issubset(tipsy_df.columns):
        return {}
    tipsy_df["AU"] = pd.to_numeric(tipsy_df["AU"], errors="coerce")
    tipsy_df["Age"] = pd.to_numeric(tipsy_df["Age"], errors="coerce")
    tipsy_df["Yield"] = pd.to_numeric(tipsy_df["Yield"], errors="coerce")
    tipsy_df["Height"] = pd.to_numeric(tipsy_df["Height"], errors="coerce")
    tipsy_df["TPH"] = pd.to_numeric(tipsy_df["TPH"], errors="coerce")
    tipsy_df = tipsy_df.dropna(subset=["AU", "Age", "Yield"])
    if tipsy_df.empty:
        return {}

    site_index_by_local_au = _load_site_index_by_au_from_tipsy_input(data_dir=data_dir)
    grouped = {_coerce_int(au): sub.copy() for au, sub in tipsy_df.groupby("AU")}
    out: dict[int, dict[str, Any]] = {}
    for au in analysis_units:
        managed_curve_points = tuple(points_by_id.get(int(au.managed_curve_id), []))
        matched_local_au: int | None = None
        for local_au, subdf in grouped.items():
            if _curve_matches_points(managed_curve_points, subdf):
                matched_local_au = int(local_au)
                break
        if matched_local_au is None:
            continue
        matched_rows = grouped[matched_local_au].sort_values("Age")
        height_points = tuple(
            CurvePoint(x=float(age), y=float(height))
            for age, height in zip(
                matched_rows["Age"].tolist(), matched_rows["Height"].tolist()
            )
            if np.isfinite(float(age)) and np.isfinite(float(height))
        )
        tph_points = tuple(
            CurvePoint(x=float(age), y=float(tph))
            for age, tph in zip(
                matched_rows["Age"].tolist(), matched_rows["TPH"].tolist()
            )
            if np.isfinite(float(age)) and np.isfinite(float(tph))
        )
        out[int(au.au_id)] = {
            "site_index": site_index_by_local_au.get(matched_local_au),
            "managed_height_points": height_points,
            "managed_tph_points": tph_points,
        }
    return out


def _load_unmanaged_qmd_support_from_checkpoint(
    *,
    data_dir: Path,
    au_table: pd.DataFrame,
) -> dict[int, dict[str, Any]]:
    checkpoint_path = data_dir / "ria_vri_vclr1p_checkpoint1-tsak3z.feather"
    vdyp_layer_path = data_dir / "vdyp_lyr-tsak3z.feather"
    if not checkpoint_path.is_file() or not vdyp_layer_path.is_file():
        return {}

    checkpoint = pd.read_feather(checkpoint_path)
    vdyp_lyr = pd.read_feather(vdyp_layer_path)
    if "FEATURE_ID" not in checkpoint.columns or "FEATURE_ID" not in vdyp_lyr.columns:
        return {}

    def _row_apply(table: pd.DataFrame, func: Any, axis: int = 1) -> Any:
        _ = axis
        return table.apply(func, axis=1)

    assigned = checkpoint.copy()
    assigned["tsa_code"] = "k3z"
    assigned = assign_stratum_codes_with_lexmatch(
        f_table=assigned,
        row_apply_fn=_row_apply,
        bec_grouping="subzone",
        species_combo_count=2,
        include_tm_species2_for_single=True,
    )
    assigned["stratum_matched"] = None
    assigned = assign_stratum_matches_from_au_table(
        f_table=assigned,
        au_table=au_table,
        tsa_list=["k3z"],
        stratum_col="stratum",
        message_fn=lambda *_: None,
    )
    allowed_levels_by_stratum: dict[str, list[str]] = {
        str(stratum_code): sorted({str(value) for value in levels.dropna().values})
        for stratum_code, levels in au_table.groupby("stratum_code")["si_level"]
    }
    assigned, _ = assign_si_levels_from_stratum_quantiles(
        f_table=assigned,
        si_levelquants={"L": [5, 20, 35], "M": [35, 50, 65], "H": [65, 80, 95]},
        allowed_levels_by_stratum=allowed_levels_by_stratum,
        stratum_matched_col="stratum_matched",
        site_index_col="SITE_INDEX",
        si_level_col="si_level",
        message_fn=lambda *_: None,
    )
    assigned["au_base"] = [
        lookup_scsi_au_base(
            scsi_au={
                "k3z": {
                    (str(row.stratum_code), str(row.si_level)): _coerce_int(row.au_id)
                    for row in au_table.itertuples(index=False)
                }
            },
            tsa_code="k3z",
            stratum_code=stratum_code,
            si_level=si_level,
        )
        for stratum_code, si_level in zip(
            assigned["stratum_matched"].tolist(), assigned["si_level"].tolist()
        )
    ]
    assigned = assigned.reset_index()
    merged = assigned.merge(
        vdyp_lyr.loc[:, ["FEATURE_ID", "STEMS_PER_HA_75"]],
        on="FEATURE_ID",
        how="left",
    )
    merged["SITE_INDEX"] = pd.to_numeric(merged["SITE_INDEX"], errors="coerce")
    merged["STEMS_PER_HA_75"] = pd.to_numeric(
        merged["STEMS_PER_HA_75"], errors="coerce"
    )
    merged = merged.dropna(subset=["au_base"])
    if merged.empty:
        return {}

    summary = (
        merged.groupby("au_base", as_index=False)
        .agg(
            site_index=("SITE_INDEX", "median"),
            unmanaged_stems_per_ha=("STEMS_PER_HA_75", "median"),
        )
        .dropna(subset=["site_index"], how="all")
    )
    return {
        _coerce_int(row.au_base): {
            "site_index": (
                float(row.site_index)
                if pd.notna(row.site_index) and np.isfinite(float(row.site_index))
                else None
            ),
            "unmanaged_stems_per_ha": (
                float(row.unmanaged_stems_per_ha)
                if pd.notna(row.unmanaged_stems_per_ha)
                and np.isfinite(float(row.unmanaged_stems_per_ha))
                else None
            ),
        }
        for row in summary.itertuples(index=False)
    }


def _build_qmd_support_by_au(
    *,
    bundle_dir: Path,
    analysis_units: tuple[AnalysisUnitDefinition, ...],
    au_table: pd.DataFrame,
    points_by_id: dict[int, list[CurvePoint]],
) -> dict[int, QmdSupportDefinition]:
    data_dir = bundle_dir.parent
    unmanaged_support = _load_unmanaged_qmd_support_from_checkpoint(
        data_dir=data_dir,
        au_table=au_table,
    )
    managed_support = _load_managed_qmd_support_from_tipsy(
        data_dir=data_dir,
        analysis_units=analysis_units,
        points_by_id=points_by_id,
    )
    out: dict[int, QmdSupportDefinition] = {}
    for au in analysis_units:
        fallback_site_index = _DEFAULT_QMD_SITE_INDEX_BY_LEVEL.get(
            str(au.si_level).strip().upper()
        )
        unmanaged_payload = unmanaged_support.get(int(au.au_id), {})
        managed_payload = managed_support.get(int(au.au_id), {})
        site_index = managed_payload.get(
            "site_index", unmanaged_payload.get("site_index", fallback_site_index)
        )
        out[int(au.au_id)] = QmdSupportDefinition(
            site_index=float(site_index) if site_index is not None else None,
            unmanaged_stems_per_ha=(
                float(unmanaged_payload["unmanaged_stems_per_ha"])
                if unmanaged_payload.get("unmanaged_stems_per_ha") is not None
                else None
            ),
            managed_height_points=tuple(
                managed_payload.get("managed_height_points", ())
            ),
            managed_tph_points=tuple(managed_payload.get("managed_tph_points", ())),
        )
    return out


def build_bundle_model_context_from_tables(
    *,
    au_table: pd.DataFrame,
    curve_table: pd.DataFrame,
    curve_points_table: pd.DataFrame,
    tsa_list: Iterable[str] | None = None,
    bundle_dir: Path | None = None,
) -> BundleModelContext:
    """Build shared bundle context from in-memory bundle tables."""
    if tsa_list is None:
        normalized_tsa = sorted(
            {normalize_tsa_code(value) for value in au_table.get("tsa", pd.Series())}
        )
    else:
        normalized_tsa = sorted({normalize_tsa_code(value) for value in tsa_list})
    if not normalized_tsa:
        raise ValueError("provide at least one TSA code for bundle context")

    scoped_au = au_table.copy()
    if "tsa" not in scoped_au.columns:
        raise ValueError("au_table.csv missing required column: tsa")
    scoped_au["tsa"] = scoped_au["tsa"].map(normalize_tsa_code)
    scoped_au = scoped_au[scoped_au["tsa"].isin(normalized_tsa)].copy()
    if scoped_au.empty:
        raise ValueError("no au_table rows matched requested TSA list")

    deduped_au = _dedupe_au_table(scoped_au)
    analysis_units = tuple(
        AnalysisUnitDefinition(
            au_id=_coerce_int(row.au_id),
            tsa=str(row.tsa),
            stratum_code=str(row.stratum_code),
            si_level=str(row.si_level),
            managed_curve_id=_coerce_int(row.managed_curve_id),
            unmanaged_curve_id=_coerce_int(row.unmanaged_curve_id),
        )
        for row in deduped_au.itertuples(index=False)
    )

    points_by_id = _curve_points_by_id(curve_points_table=curve_points_table)
    curve_type_map: dict[int, str] = {}
    if {"curve_id", "curve_type"}.issubset(curve_table.columns):
        for _, row in curve_table.iterrows():
            curve_type_map[_coerce_int(row["curve_id"])] = str(row["curve_type"])
    curves_by_id = {
        curve_id: CurveDefinition(
            curve_id=curve_id,
            curve_type=curve_type_map.get(curve_id, ""),
            points=(
                _thin_curve_points_to_decadal_knots(tuple(points))
                if curve_type_map.get(curve_id, "") in {"unmanaged", "untreated"}
                else tuple(points)
            ),
        )
        for curve_id, points in points_by_id.items()
    }

    managed_species_curve_ids, unmanaged_species_curve_ids = _species_curve_maps(
        curve_table=curve_table
    )
    qmd_support_by_au = (
        _build_qmd_support_by_au(
            bundle_dir=bundle_dir,
            analysis_units=analysis_units,
            au_table=deduped_au,
            points_by_id=points_by_id,
        )
        if bundle_dir is not None
        else {}
    )
    return BundleModelContext(
        tsa_list=normalized_tsa,
        analysis_units=analysis_units,
        curves_by_id=curves_by_id,
        managed_species_curve_ids=managed_species_curve_ids,
        unmanaged_species_curve_ids=unmanaged_species_curve_ids,
        qmd_support_by_au=qmd_support_by_au,
        curve_row_count=int(curve_table.shape[0]),
    )


def build_bundle_model_context(
    *,
    bundle_dir: Path,
    tsa_list: Iterable[str],
) -> BundleModelContext:
    """Build shared bundle context from bundle directory CSV files."""
    au_table, curve_table, curve_points_table = _load_bundle_tables(
        bundle_dir=bundle_dir
    )
    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points_table,
        tsa_list=tsa_list,
        bundle_dir=bundle_dir,
    )
    return context
