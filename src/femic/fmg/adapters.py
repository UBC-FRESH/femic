"""Bundle-table adapters into shared FMG core objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable, Protocol, cast

import numpy as np
import pandas as pd

from .core import (
    AnalysisUnitDefinition,
    BundleModelContext,
    CurveDefinition,
    CurvePoint,
    QmdSupportDefinition,
)

FMG_BUNDLE_AUXILIARY_ENTRY_POINT_GROUP = "femic.fmg_bundle_auxiliary"


@dataclass(frozen=True)
class BundleAuxiliaryData:
    """Auxiliary bundle data supplied by instance-owned providers."""

    qmd_support_by_au: dict[int, QmdSupportDefinition] = field(default_factory=dict)
    managed_indicator_curves_by_au: dict[int, dict[str, tuple[CurvePoint, ...]]] = (
        field(default_factory=dict)
    )


@dataclass(frozen=True)
class BundleAuxiliaryRequest:
    """Context passed to an FMG bundle auxiliary provider."""

    bundle_dir: Path | None
    analysis_units: tuple[AnalysisUnitDefinition, ...]
    au_table: pd.DataFrame
    curve_table: pd.DataFrame
    curve_points_table: pd.DataFrame
    points_by_id: dict[int, list[CurvePoint]]
    tsa_list: tuple[str, ...]


class BundleAuxiliaryProvider(Protocol):
    """Protocol for instance-owned FMG bundle auxiliary providers."""

    provider_id: str

    def build_bundle_auxiliary(
        self, request: BundleAuxiliaryRequest
    ) -> BundleAuxiliaryData:
        """Return auxiliary QMD and indicator data for a bundle context."""
        ...


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
                **{
                    column: "first"
                    for column in (
                        "source_local_au_id",
                        "source_managed_local_au_id",
                        "source_unmanaged_local_au_id",
                    )
                    if column in table.columns
                },
            }
        )
    )
    deduped["au_id"] = deduped["au_id"].astype(int)
    deduped["managed_curve_id"] = deduped["managed_curve_id"].astype(int)
    deduped["unmanaged_curve_id"] = deduped["unmanaged_curve_id"].astype(int)
    for column in (
        "source_local_au_id",
        "source_managed_local_au_id",
        "source_unmanaged_local_au_id",
    ):
        if column in deduped.columns:
            deduped[column] = pd.to_numeric(deduped[column], errors="coerce")
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


def _build_qmd_support_by_au(
    *,
    analysis_units: tuple[AnalysisUnitDefinition, ...],
    auxiliary_data: BundleAuxiliaryData,
) -> dict[int, QmdSupportDefinition]:
    out: dict[int, QmdSupportDefinition] = {}
    for au in analysis_units:
        fallback_site_index = _DEFAULT_QMD_SITE_INDEX_BY_LEVEL.get(
            str(au.si_level).strip().upper()
        )
        provider_support = auxiliary_data.qmd_support_by_au.get(int(au.au_id))
        if provider_support is None:
            out[int(au.au_id)] = QmdSupportDefinition(
                site_index=fallback_site_index,
                unmanaged_stems_per_ha=None,
                managed_stems_per_ha=None,
                managed_height_points=(),
                managed_tph_points=(),
            )
            continue
        out[int(au.au_id)] = QmdSupportDefinition(
            site_index=(
                provider_support.site_index
                if provider_support.site_index is not None
                else fallback_site_index
            ),
            unmanaged_stems_per_ha=provider_support.unmanaged_stems_per_ha,
            managed_stems_per_ha=provider_support.managed_stems_per_ha,
            managed_height_points=tuple(provider_support.managed_height_points),
            managed_tph_points=tuple(provider_support.managed_tph_points),
        )
    return out


def discover_bundle_auxiliary_providers() -> tuple[BundleAuxiliaryProvider, ...]:
    """Load installed FMG bundle auxiliary providers from Python entry points."""
    selected = metadata.entry_points().select(
        group=FMG_BUNDLE_AUXILIARY_ENTRY_POINT_GROUP
    )
    providers: list[BundleAuxiliaryProvider] = []
    for entry_point in selected:
        loaded = entry_point.load()
        provider = loaded() if callable(loaded) else loaded
        if not hasattr(provider, "provider_id") or not hasattr(
            provider, "build_bundle_auxiliary"
        ):
            raise TypeError(
                "FMG bundle auxiliary entry point "
                f"{entry_point.name!r} did not return a provider"
            )
        providers.append(cast(BundleAuxiliaryProvider, provider))
    return tuple(sorted(providers, key=lambda provider: str(provider.provider_id)))


def _merge_auxiliary_data(
    sources: Iterable[BundleAuxiliaryData],
) -> BundleAuxiliaryData:
    qmd_support_by_au: dict[int, QmdSupportDefinition] = {}
    managed_indicator_curves_by_au: dict[int, dict[str, tuple[CurvePoint, ...]]] = {}
    for source in sources:
        qmd_support_by_au.update(
            {int(key): value for key, value in source.qmd_support_by_au.items()}
        )
        for au_id, curves in source.managed_indicator_curves_by_au.items():
            managed_indicator_curves_by_au.setdefault(int(au_id), {}).update(curves)
    return BundleAuxiliaryData(
        qmd_support_by_au=qmd_support_by_au,
        managed_indicator_curves_by_au=managed_indicator_curves_by_au,
    )


def build_bundle_model_context_from_tables(
    *,
    au_table: pd.DataFrame,
    curve_table: pd.DataFrame,
    curve_points_table: pd.DataFrame,
    tsa_list: Iterable[str] | None = None,
    bundle_dir: Path | None = None,
    auxiliary_data: BundleAuxiliaryData | None = None,
    auxiliary_providers: Iterable[BundleAuxiliaryProvider] | None = None,
    discover_auxiliary: bool = False,
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
            source_local_au_id=(
                _coerce_int(row.source_local_au_id)
                if pd.notna(getattr(row, "source_local_au_id", None))
                else None
            ),
            source_managed_local_au_id=(
                _coerce_int(row.source_managed_local_au_id)
                if pd.notna(getattr(row, "source_managed_local_au_id", None))
                else None
            ),
            source_unmanaged_local_au_id=(
                _coerce_int(row.source_unmanaged_local_au_id)
                if pd.notna(getattr(row, "source_unmanaged_local_au_id", None))
                else None
            ),
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
    auxiliary_sources: list[BundleAuxiliaryData] = []
    if auxiliary_data is not None:
        auxiliary_sources.append(auxiliary_data)
    providers = list(auxiliary_providers or ())
    if discover_auxiliary:
        providers.extend(discover_bundle_auxiliary_providers())
    if providers:
        request = BundleAuxiliaryRequest(
            bundle_dir=bundle_dir,
            analysis_units=analysis_units,
            au_table=deduped_au,
            curve_table=curve_table,
            curve_points_table=curve_points_table,
            points_by_id=points_by_id,
            tsa_list=tuple(normalized_tsa),
        )
        for provider in sorted(providers, key=lambda item: str(item.provider_id)):
            auxiliary_sources.append(provider.build_bundle_auxiliary(request))
    merged_auxiliary_data = _merge_auxiliary_data(auxiliary_sources)
    qmd_support_by_au = (
        _build_qmd_support_by_au(
            analysis_units=analysis_units,
            auxiliary_data=merged_auxiliary_data,
        )
        if bundle_dir is not None or auxiliary_sources
        else {}
    )
    managed_indicator_curves_by_au = (
        merged_auxiliary_data.managed_indicator_curves_by_au
    )
    return BundleModelContext(
        tsa_list=normalized_tsa,
        analysis_units=analysis_units,
        curves_by_id=curves_by_id,
        managed_species_curve_ids=managed_species_curve_ids,
        unmanaged_species_curve_ids=unmanaged_species_curve_ids,
        qmd_support_by_au=qmd_support_by_au,
        managed_indicator_curves_by_au=managed_indicator_curves_by_au,
        curve_row_count=int(curve_table.shape[0]),
    )


def build_bundle_model_context(
    *,
    bundle_dir: Path,
    tsa_list: Iterable[str],
    auxiliary_providers: Iterable[BundleAuxiliaryProvider] | None = None,
    discover_auxiliary: bool = True,
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
        auxiliary_providers=auxiliary_providers,
        discover_auxiliary=discover_auxiliary,
    )
    return context
