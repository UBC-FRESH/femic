from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import json

import numpy as np
import pandas as pd
import yaml

from femic.pipeline.mkrf_au import parse_mkrf_bec
from femic.pipeline.mkrf_first_growth import collapse_stand_assignments
from femic.pipeline.tipsy import (
    build_btc_msyt_input_table,
    parse_btc_tsr_transposed_output,
)

_MANAGED_TIPSY_SPECIES_COLUMNS = ("BA", "CW", "DR", "FD", "HW", "PW", "SS", "YC")
_DEFAULT_MANAGED_RULE_KEY = "families"


@dataclass(frozen=True)
class ManagedSpeciesPayload:
    species_1: str
    species_2: str
    species_3: str
    species_4: str
    species_5: str
    pct_1: float
    pct_2: float
    pct_3: float
    pct_4: float
    pct_5: float


@dataclass(frozen=True)
class MkrfManagedRule:
    family_id: str
    bec_zone: str
    bec_subzone: str
    bec_variant: str
    density_total: int
    regen_delay: int
    oaf1: float
    oaf2: float
    planted_percent: int
    baseline_system: str
    ct_eligible: bool
    ct_target_age: int
    ct_on_fire_origin: bool
    species_mix: Mapping[str, float]
    notes: str


@dataclass(frozen=True)
class MkrfManagedRuleConfig:
    path: Path
    fire_origin_min_age: float
    rules: tuple[MkrfManagedRule, ...]


def build_mkrf_legacy_managed_au_table(
    *,
    man_si_by_au: pd.DataFrame,
    tipsy_spp_comp: pd.DataFrame,
) -> pd.DataFrame:
    merged = man_si_by_au.merge(tipsy_spp_comp, on="AU", how="inner")
    bec_parts = merged["BEC"].apply(parse_mkrf_bec)
    merged[["bec_zone", "bec_subzone", "bec_variant"]] = pd.DataFrame(
        bec_parts.tolist(),
        index=merged.index,
    )
    species_pairs = merged.apply(_tipsy_species_pair, axis=1)
    merged["leading_species_1"] = [pair[0] for pair in species_pairs]
    merged["leading_species_2"] = [pair[1] for pair in species_pairs]
    merged["legacy_candidate_au_id"] = (
        merged["bec_zone"].astype(str)
        + "_"
        + merged["bec_subzone"].astype(str)
        + "_"
        + merged["bec_variant"].astype(str)
        + "_"
        + merged["leading_species_1"].astype(str)
        + "_"
        + merged["leading_species_2"].astype(str)
    )
    return merged


def load_mkrf_managed_rule_config(path: Path) -> MkrfManagedRuleConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    origin_rules = payload.get("origin_rules", {}) or {}
    managed_defaults = payload.get("managed_defaults", {}) or {}
    raw_rules = payload.get(_DEFAULT_MANAGED_RULE_KEY, {}) or {}
    if not isinstance(raw_rules, Mapping) or not raw_rules:
        raise ValueError(f"Managed rule config has no families: {path}")

    fire_origin_min_age = float(origin_rules.get("fire_origin_min_age", 80.0))
    defaults = {
        "density_total": int(managed_defaults.get("density_total", 1500)),
        "regen_delay": int(managed_defaults.get("regen_delay", 1)),
        "oaf1": float(managed_defaults.get("oaf1", 1.0)),
        "oaf2": float(managed_defaults.get("oaf2", 0.95)),
        "planted_percent": int(managed_defaults.get("planted_percent", 100)),
        "baseline_system": str(managed_defaults.get("baseline_system", "clearcut")),
        "ct_eligible": bool(managed_defaults.get("ct_eligible", True)),
        "ct_target_age": int(managed_defaults.get("ct_target_age", 40)),
        "ct_on_fire_origin": bool(managed_defaults.get("ct_on_fire_origin", False)),
    }

    rules: list[MkrfManagedRule] = []
    for family_id, raw_rule in raw_rules.items():
        if not isinstance(raw_rule, Mapping):
            raise ValueError(f"Managed family {family_id!r} must be a mapping in {path}")
        species_mix = raw_rule.get("species_mix", {}) or {}
        if not isinstance(species_mix, Mapping) or not species_mix:
            raise ValueError(
                f"Managed family {family_id!r} is missing a non-empty species_mix in {path}"
            )
        normalized_mix: dict[str, float] = {}
        for species, share in species_mix.items():
            code = str(species).strip().upper()
            if code not in _MANAGED_TIPSY_SPECIES_COLUMNS:
                raise ValueError(
                    f"Managed family {family_id!r} uses unsupported species code {code!r}"
                )
            normalized_mix[code] = float(share)
        rules.append(
            MkrfManagedRule(
                family_id=str(family_id),
                bec_zone=str(raw_rule.get("bec_zone", "")).strip().lower(),
                bec_subzone=str(raw_rule.get("bec_subzone", "")).strip().lower(),
                bec_variant=str(raw_rule.get("bec_variant", "")).strip().lower(),
                density_total=int(raw_rule.get("density_total", defaults["density_total"])),
                regen_delay=int(raw_rule.get("regen_delay", defaults["regen_delay"])),
                oaf1=float(raw_rule.get("oaf1", defaults["oaf1"])),
                oaf2=float(raw_rule.get("oaf2", defaults["oaf2"])),
                planted_percent=int(
                    raw_rule.get("planted_percent", defaults["planted_percent"])
                ),
                baseline_system=str(
                    raw_rule.get("baseline_system", defaults["baseline_system"])
                ),
                ct_eligible=bool(raw_rule.get("ct_eligible", defaults["ct_eligible"])),
                ct_target_age=int(
                    raw_rule.get("ct_target_age", defaults["ct_target_age"])
                ),
                ct_on_fire_origin=bool(
                    raw_rule.get(
                        "ct_on_fire_origin",
                        defaults["ct_on_fire_origin"],
                    )
                ),
                species_mix=normalized_mix,
                notes=str(raw_rule.get("notes", "")).strip(),
            )
        )
    return MkrfManagedRuleConfig(
        path=path,
        fire_origin_min_age=fire_origin_min_age,
        rules=tuple(rules),
    )


def classify_mkrf_origin(
    *,
    age_2020: Any,
    fire_origin_min_age: float = 80.0,
) -> str:
    age = pd.to_numeric(pd.Series([age_2020]), errors="coerce").iloc[0]
    if pd.isna(age):
        return "unknown"
    if float(age) >= float(fire_origin_min_age):
        return "fire_origin"
    return "logging_origin"


def build_mkrf_stand_origin_assignment(
    *,
    assignment: pd.DataFrame,
    source_table: pd.DataFrame,
    fire_origin_min_age: float = 80.0,
) -> pd.DataFrame:
    stand_assignment = collapse_stand_assignments(assignment)
    assignment_context = (
        assignment[
            [
                "au_id",
                "bec_zone",
                "bec_subzone",
                "bec_variant",
                "leading_species_1",
                "leading_species_2",
            ]
        ]
        .drop_duplicates(subset=["au_id"])
        .copy()
    )
    source_subset = source_table[
        [
            "FOREST_COVER_ID",
            "AGE_2020",
            "TCL_1_ESTIMATED_SITE_INDEX",
        ]
    ].copy()
    source_subset = source_subset.rename(
        columns={
            "FOREST_COVER_ID": "forest_cover_id",
            "AGE_2020": "age_2020",
            "TCL_1_ESTIMATED_SITE_INDEX": "site_index",
        }
    )
    source_subset["forest_cover_id"] = pd.to_numeric(
        source_subset["forest_cover_id"], errors="coerce"
    )
    source_subset["age_2020"] = pd.to_numeric(source_subset["age_2020"], errors="coerce")
    source_subset["site_index"] = pd.to_numeric(
        source_subset["site_index"], errors="coerce"
    )
    stand_source = (
        source_subset.dropna(subset=["forest_cover_id"])
        .assign(forest_cover_id=lambda df: df["forest_cover_id"].astype(int))
        .groupby("forest_cover_id", as_index=False, sort=True)
        .agg(
            age_2020=("age_2020", "median"),
            site_index=("site_index", "median"),
        )
    )
    origin_assignment = stand_assignment.merge(
        assignment_context,
        on="au_id",
        how="left",
        validate="many_to_one",
    ).merge(
        stand_source,
        on="forest_cover_id",
        how="left",
        validate="one_to_one",
    )
    origin_assignment["origin_class"] = origin_assignment["age_2020"].map(
        lambda value: classify_mkrf_origin(
            age_2020=value,
            fire_origin_min_age=fire_origin_min_age,
        )
    )
    origin_assignment["fire_origin_min_age"] = float(fire_origin_min_age)
    origin_assignment["is_fire_origin"] = origin_assignment["origin_class"].eq("fire_origin")
    origin_assignment["is_logging_origin"] = origin_assignment["origin_class"].eq(
        "logging_origin"
    )
    return origin_assignment.sort_values(
        ["au_id", "forest_cover_id"],
        kind="stable",
    ).reset_index(drop=True)


def build_mkrf_managed_au_bootstrap_table(
    *,
    selected_au_table: pd.DataFrame,
    stand_origin_assignment: pd.DataFrame,
    rule_config: MkrfManagedRuleConfig,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    ordered_selected = selected_au_table.sort_values(
        ["selected_rank", "au_id"],
        kind="stable",
    )
    for _, selected_row in ordered_selected.iterrows():
        au_id = str(selected_row["au_id"])
        rule = _match_managed_rule(
            rule_config=rule_config,
            bec_zone=str(selected_row["bec_zone"]),
            bec_subzone=str(selected_row["bec_subzone"]),
            bec_variant=str(selected_row["bec_variant"]),
        )
        support_rows = stand_origin_assignment.loc[
            stand_origin_assignment["au_id"].astype(str) == au_id
        ].copy()
        logging_si = pd.to_numeric(
            support_rows.loc[
                support_rows["origin_class"].astype(str) == "logging_origin",
                "site_index",
            ],
            errors="coerce",
        ).dropna()
        all_si = pd.to_numeric(support_rows["site_index"], errors="coerce").dropna()

        if len(logging_si) > 0:
            managed_si = float(logging_si.median())
            si_source = "logging_origin_median"
        elif len(all_si) > 0:
            managed_si = float(all_si.median())
            si_source = "all_stands_median"
        else:
            managed_si = float("nan")
            si_source = "missing_site_index"

        base_row = {
            "au_id": au_id,
            "selected_rank": int(selected_row["selected_rank"]),
            "covered_area_ha": float(selected_row["covered_area_ha"]),
            "bec_zone": str(selected_row["bec_zone"]),
            "bec_subzone": str(selected_row["bec_subzone"]),
            "bec_variant": str(selected_row["bec_variant"]),
            "leading_species_1": str(selected_row["leading_species_1"]),
            "leading_species_2": str(selected_row["leading_species_2"]),
            "managed_curve_id": 60000 + int(selected_row["selected_rank"]),
            "managed_rule_source": str(rule_config.path.as_posix()),
            "origin_fire_min_age": float(rule_config.fire_origin_min_age),
            "origin_classification": "AGE_2020 threshold",
            "logging_origin_stand_count": int(
                support_rows["origin_class"].astype(str).eq("logging_origin").sum()
            ),
            "fire_origin_stand_count": int(
                support_rows["origin_class"].astype(str).eq("fire_origin").sum()
            ),
            "logging_origin_si_count": int(len(logging_si)),
            "all_stand_si_count": int(len(all_si)),
            "managed_si_source": si_source,
        }

        if rule is None:
            rows.append(
                {
                    **base_row,
                    "bootstrap_status": "unmatched",
                    "included_in_msyt": False,
                    "mapping_path": "no_matching_managed_rule",
                    "managed_si": managed_si,
                    "managed_family_id": "",
                    "density_total": np.nan,
                    "regen_delay": np.nan,
                    "oaf1": np.nan,
                    "oaf2": np.nan,
                    "planted_percent": np.nan,
                    "baseline_system": "",
                    "ct_eligible": False,
                    "ct_target_age": np.nan,
                    "ct_on_fire_origin": False,
                    "managed_rule_notes": "",
                    **_managed_species_payload_dict(
                        ManagedSpeciesPayload("", "", "", "", "", 0, 0, 0, 0, 0)
                    ),
                }
            )
            continue

        included = not pd.isna(managed_si)
        rows.append(
            {
                **base_row,
                "bootstrap_status": "expert_rule" if included else "unmatched",
                "included_in_msyt": bool(included),
                "mapping_path": (
                    f"expert_rule_{si_source}" if included else f"expert_rule_{si_source}"
                ),
                "managed_si": managed_si,
                "managed_family_id": rule.family_id,
                "density_total": int(rule.density_total),
                "regen_delay": int(rule.regen_delay),
                "oaf1": float(rule.oaf1),
                "oaf2": float(rule.oaf2),
                "planted_percent": int(rule.planted_percent),
                "baseline_system": rule.baseline_system,
                "ct_eligible": bool(rule.ct_eligible),
                "ct_target_age": int(rule.ct_target_age),
                "ct_on_fire_origin": bool(rule.ct_on_fire_origin),
                "managed_rule_notes": rule.notes,
                **_managed_species_payload_dict(
                    _managed_species_payload_from_mix(rule.species_mix)
                ),
            }
        )

    return pd.DataFrame(rows)


def build_mkrf_managed_au_msyt_table(
    *,
    bootstrap_table: pd.DataFrame,
) -> pd.DataFrame:
    included = bootstrap_table.loc[bootstrap_table["included_in_msyt"].fillna(False)].copy()
    if included.empty:
        raise RuntimeError("No managed AU bootstrap rows available for MSYT generation.")
    included = included.sort_values(["selected_rank", "au_id"], kind="stable")
    tipsy_rows: list[dict[str, Any]] = []
    for _, row in included.iterrows():
        tipsy_row: dict[str, Any] = {
            "AU": int(row["managed_curve_id"]),
            "BEC": _format_mkrf_bec(
                str(row["bec_zone"]),
                str(row["bec_subzone"]),
                str(row["bec_variant"]),
            ),
            "Proportion": 1.0,
            "Regen_Delay": int(row["regen_delay"]),
            "Density": int(row["density_total"]),
            "OAF1": float(row["oaf1"]),
            "OAF2": float(row["oaf2"]),
            "SI": float(row["managed_si"]),
        }
        for i in range(1, 6):
            tipsy_row[f"SPP_{i}"] = row.get(f"managed_species_{i}", "")
            tipsy_row[f"PCT_{i}"] = row.get(f"managed_pct_{i}", "")
            tipsy_row[f"GW_{i}"] = ""
        tipsy_rows.append(tipsy_row)
    tipsy_table = pd.DataFrame(tipsy_rows)
    return build_btc_msyt_input_table(tipsy_table=tipsy_table, pd_module=pd)


def parse_mkrf_managed_au_curves(
    *,
    output_csv: Path,
    bootstrap_table: pd.DataFrame,
) -> pd.DataFrame:
    parsed = parse_btc_tsr_transposed_output(output_csv=output_csv, pd_module=pd)
    lookup = (
        bootstrap_table.loc[
            bootstrap_table["included_in_msyt"].fillna(False),
            ["managed_curve_id", "au_id"],
        ]
        .copy()
        .assign(managed_curve_id=lambda df: pd.to_numeric(df["managed_curve_id"]).astype(int))
    )
    merged = parsed.merge(
        lookup,
        left_on="AU",
        right_on="managed_curve_id",
        how="left",
        validate="many_to_one",
    )
    curves = merged.rename(
        columns={
            "Age": "age",
            "Yield": "volume",
            "Height": "height",
            "DBHq": "dbhq",
            "TPH": "tph",
            "GrossYield": "gross_yield",
            "CrownCover": "crown_cover",
        }
    )
    ordered_columns = [
        "au_id",
        "managed_curve_id",
        "age",
        "volume",
        "height",
        "dbhq",
        "tph",
        "gross_yield",
        "crown_cover",
    ]
    for column in ordered_columns:
        if column not in curves.columns:
            curves[column] = np.nan
    return curves[ordered_columns].sort_values(
        ["managed_curve_id", "age"],
        kind="stable",
    ).reset_index(drop=True)


def write_mkrf_managed_run_manifest(
    *,
    manifest_path: Path,
    payload: Mapping[str, Any],
) -> Path:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def _match_managed_rule(
    *,
    rule_config: MkrfManagedRuleConfig,
    bec_zone: str,
    bec_subzone: str,
    bec_variant: str,
) -> MkrfManagedRule | None:
    normalized = (
        str(bec_zone).strip().lower(),
        str(bec_subzone).strip().lower(),
        str(bec_variant).strip().lower(),
    )
    for rule in rule_config.rules:
        if (rule.bec_zone, rule.bec_subzone, rule.bec_variant) == normalized:
            return rule
    return None


def _managed_species_payload_dict(payload: ManagedSpeciesPayload) -> dict[str, Any]:
    return {
        "managed_species_1": payload.species_1,
        "managed_species_2": payload.species_2,
        "managed_species_3": payload.species_3,
        "managed_species_4": payload.species_4,
        "managed_species_5": payload.species_5,
        "managed_pct_1": payload.pct_1,
        "managed_pct_2": payload.pct_2,
        "managed_pct_3": payload.pct_3,
        "managed_pct_4": payload.pct_4,
        "managed_pct_5": payload.pct_5,
    }


def _managed_species_payload_from_mix(species_mix: Mapping[str, float]) -> ManagedSpeciesPayload:
    ranked = sorted(
        (
            (str(species).strip().upper(), float(share))
            for species, share in species_mix.items()
            if float(share) > 0.0
        ),
        key=lambda item: (-item[1], item[0]),
    )[:5]
    while len(ranked) < 5:
        ranked.append(("", 0.0))
    return ManagedSpeciesPayload(
        species_1=ranked[0][0],
        species_2=ranked[1][0],
        species_3=ranked[2][0],
        species_4=ranked[3][0],
        species_5=ranked[4][0],
        pct_1=ranked[0][1],
        pct_2=ranked[1][1],
        pct_3=ranked[2][1],
        pct_4=ranked[3][1],
        pct_5=ranked[4][1],
    )


def _tipsy_species_pair(row: pd.Series) -> tuple[str, str]:
    ranked: list[tuple[str, float]] = []
    for column in _MANAGED_TIPSY_SPECIES_COLUMNS:
        raw = row.get(column)
        try:
            share = float(raw)
        except (TypeError, ValueError):
            share = 0.0
        if not np.isfinite(share) or share <= 0.0:
            continue
        ranked.append((column.lower() if column != "FD" else "fdc", share))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    if not ranked:
        return ("x", "x")
    if len(ranked) == 1:
        return (ranked[0][0], "x")
    return (ranked[0][0], ranked[1][0])


def _format_mkrf_bec(zone: str, subzone: str, variant: str) -> str:
    base = f"{zone.upper()}{subzone}"
    if variant == "x":
        return base
    return f"{base}{variant}"
