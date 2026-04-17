"""Helpers for legacy VRI table normalization/filtering stages."""

from __future__ import annotations

from typing import Any, Sequence


_BEC_KEY_LEVELS = {"zone", "subzone", "variant", "phase"}


def _coerce_text_token(value: Any, *, fallback: str = "X") -> str:
    text = str(value).strip() if value is not None else ""
    if not text or text.lower() == "nan":
        return fallback
    return text


def _value_from_row(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (KeyError, TypeError, IndexError):
        return getattr(row, key, None)


def _bec_key_from_row(
    row: Any,
    *,
    bec_grouping: str,
    lexmatch: bool = False,
    lexmatch_fieldname_suffix: str = "_lexmatch",
) -> str:
    level = str(bec_grouping).strip().lower()
    if level not in _BEC_KEY_LEVELS:
        level = "zone"

    zone_key = (
        f"BEC_ZONE_CODE{lexmatch_fieldname_suffix}" if lexmatch else "BEC_ZONE_CODE"
    )
    zone = _coerce_text_token(_value_from_row(row, zone_key))
    if lexmatch:
        zone = zone * 3

    if level == "zone":
        return zone

    subzone = _coerce_text_token(_value_from_row(row, "BEC_SUBZONE"), fallback="")
    if level == "subzone":
        return f"{zone}{subzone}"

    variant = _coerce_text_token(_value_from_row(row, "BEC_VARIANT"), fallback="")
    if level == "variant":
        return f"{zone}{subzone}{variant}"

    phase = _coerce_text_token(_value_from_row(row, "BEC_PHASE"), fallback="")
    return f"{zone}{subzone}{variant}{phase}"


def _species_combo_from_row(
    row: Any,
    *,
    species_combo_count: int,
    lexmatch: bool = False,
    lexmatch_fieldname_suffix: str = "_lexmatch",
    include_tm_species2_for_single: bool = True,
) -> str:
    combo_count = max(int(species_combo_count), 1)
    if combo_count == 1:
        first_key = (
            f"SPECIES_CD_1{lexmatch_fieldname_suffix}" if lexmatch else "SPECIES_CD_1"
        )
        first_species = _coerce_text_token(_value_from_row(row, first_key))
        result = first_species * 2 if lexmatch else first_species
        if include_tm_species2_for_single:
            level_4 = _coerce_text_token(
                _value_from_row(row, "BCLCS_LEVEL_4"), fallback=""
            )
            species_2 = _value_from_row(row, "SPECIES_CD_2")
            if level_4 == "TM" and species_2 is not None:
                second_key = (
                    f"SPECIES_CD_2{lexmatch_fieldname_suffix}"
                    if lexmatch
                    else "SPECIES_CD_2"
                )
                second_species = _coerce_text_token(
                    _value_from_row(row, second_key), fallback=""
                )
                if second_species:
                    result += "+" + second_species
        return result

    species_entries: list[tuple[float, int, str]] = []
    seen_codes: set[str] = set()
    for idx in range(1, 7):
        species_key = (
            f"SPECIES_CD_{idx}{lexmatch_fieldname_suffix}"
            if lexmatch
            else f"SPECIES_CD_{idx}"
        )
        species_text = _coerce_text_token(
            _value_from_row(row, species_key), fallback=""
        )
        if not species_text or species_text == "X":
            continue
        base_species_text = _coerce_text_token(
            _value_from_row(row, f"SPECIES_CD_{idx}"),
            fallback="",
        )
        if not base_species_text or base_species_text in {"X", "XX"}:
            continue
        if base_species_text in seen_codes:
            continue
        seen_codes.add(base_species_text)
        pct_raw = _value_from_row(row, f"SPECIES_PCT_{idx}")
        try:
            pct = float(pct_raw)
        except (TypeError, ValueError):
            pct = 0.0
        if pct <= 0.0:
            continue
        species_entries.append((pct, idx, species_text))
    if not species_entries:
        return _coerce_text_token(
            _value_from_row(
                row,
                f"SPECIES_CD_1{lexmatch_fieldname_suffix}"
                if lexmatch
                else "SPECIES_CD_1",
            )
        )
    species_entries.sort(key=lambda entry: (-entry[0], entry[1]))
    parts = [entry[2] for entry in species_entries[:combo_count]]
    return "+".join(parts)


def stratify_stand(
    row: Any,
    *,
    lexmatch: bool = False,
    lexmatch_fieldname_suffix: str = "_lexmatch",
    bec_grouping: str = "zone",
    species_combo_count: int = 1,
    include_tm_species2_for_single: bool = True,
) -> str:
    """Build stratum code from BEC grouping + leading species combination."""
    bec = _bec_key_from_row(
        row,
        bec_grouping=bec_grouping,
        lexmatch=lexmatch,
        lexmatch_fieldname_suffix=lexmatch_fieldname_suffix,
    )
    species_combo = _species_combo_from_row(
        row,
        species_combo_count=species_combo_count,
        lexmatch=lexmatch,
        lexmatch_fieldname_suffix=lexmatch_fieldname_suffix,
        include_tm_species2_for_single=include_tm_species2_for_single,
    )
    return f"{bec}_{species_combo}"


def assign_stratum_codes_with_lexmatch(
    *,
    f_table: Any,
    row_apply_fn: Any,
    bec_col: str = "BEC_ZONE_CODE",
    species_col_prefix: str = "SPECIES_CD_",
    lexmatch_suffix: str = "_lexmatch",
    stratum_col: str = "stratum",
    stratum_lexmatch_col: str = "stratum_lexmatch",
    bec_grouping: str = "zone",
    species_combo_count: int = 1,
    include_tm_species2_for_single: bool = True,
) -> Any:
    """Populate legacy stratum and stratum_lexmatch fields from stand attributes."""
    table = f_table.copy()
    table[f"{bec_col}{lexmatch_suffix}"] = table[bec_col].str.ljust(4, fillchar="x")
    for idx in range(1, 7):
        species_col = f"{species_col_prefix}{idx}"
        if species_col not in table.columns:
            continue
        lex_col = f"{species_col}{lexmatch_suffix}"
        table[lex_col] = table[species_col].str.ljust(4, "x")
        table[lex_col] = table[species_col].str[:1] + table[species_col]

    table[stratum_col] = row_apply_fn(
        table,
        lambda row: stratify_stand(
            row,
            bec_grouping=bec_grouping,
            species_combo_count=species_combo_count,
            include_tm_species2_for_single=include_tm_species2_for_single,
        ),
        axis=1,
    )
    table[stratum_lexmatch_col] = row_apply_fn(
        table,
        lambda row: stratify_stand(
            row,
            lexmatch=True,
            lexmatch_fieldname_suffix=lexmatch_suffix,
            bec_grouping=bec_grouping,
            species_combo_count=species_combo_count,
            include_tm_species2_for_single=include_tm_species2_for_single,
        ),
        axis=1,
    )
    return table


def is_conifer_species_code(species_code: str) -> bool:
    """Return True if species code represents a conifer species."""
    return str(species_code)[:1] in ["B", "C", "F", "H", "J", "L", "P", "S", "T", "Y"]


def is_deciduous_species_code(species_code: str) -> bool:
    """Return True if species code represents a deciduous species."""
    return str(species_code)[:1] in ["A", "D", "E", "G", "M", "Q", "R", "U", "V", "W"]


def pconif(
    row: Any,
    *,
    species_slot_count: int = 6,
) -> float:
    """Return conifer percent share from species-percent slots."""
    return (
        sum(
            row[f"SPECIES_PCT_{idx}"]
            for idx in range(1, int(species_slot_count) + 1)
            if is_conifer_species_code(row[f"SPECIES_CD_{idx}"])
        )
        / 100.0
    )


def pdecid(
    row: Any,
    *,
    species_slot_count: int = 6,
) -> float:
    """Return deciduous percent share from species-percent slots."""
    return (
        sum(
            row[f"SPECIES_PCT_{idx}"]
            for idx in range(1, int(species_slot_count) + 1)
            if is_deciduous_species_code(row[f"SPECIES_CD_{idx}"])
        )
        / 100.0
    )


def classify_stand_cdm(row: Any) -> str:
    """Classify stand as conifer/deciduous/mixed (c/d/m)."""
    if pconif(row) >= 0.8:
        return "c"
    if pdecid(row) >= 0.8:
        return "d"
    return "m"


def classify_stand_forest_type(row: Any) -> int:
    """Classify stand into 1..4 forest-type classes from conifer proportion."""
    conif_share = pconif(row)
    if conif_share >= 0.75:
        return 1
    if conif_share >= 0.50:
        return 2
    if conif_share >= 0.25:
        return 3
    return 4


def assign_forest_type_from_species_pct(
    *,
    f_table: Any,
    out_col: str = "forest_type",
    apply_fn: Any | None = None,
    classify_fn: Any = classify_stand_forest_type,
) -> Any:
    """Assign forest-type class column using supplied row-apply callable."""
    table = f_table.copy()
    if apply_fn is None:
        apply_fn = table.apply
        table[out_col] = apply_fn(classify_fn, axis=1)
    else:
        table[out_col] = apply_fn(table, classify_fn, axis=1)
    return table


def normalize_and_filter_checkpoint2_records(
    *,
    f_table: Any,
    species_slot_count: int = 6,
    fill_token: str = "X",
    excluded_bec_zones: Sequence[str] = ("BAFA", "IMA"),
    required_bclcs_level_2: str = "T",
    required_for_mgmt_land_base: str = "Y",
    min_proj_age: int = 30,
    min_basal_area: int = 5,
    min_live_stand_volume: int = 1,
) -> Any:
    """Apply legacy checkpoint2 fillna defaults and row filters."""
    table = normalize_vri_problem_values(
        f_table=f_table,
        species_slot_count=species_slot_count,
        fill_token=fill_token,
    )
    table = table[table.BCLCS_LEVEL_2 == required_bclcs_level_2]
    # Keep productive stands: NON_PRODUCTIVE_CD is null for productive land.
    table = table[table.NON_PRODUCTIVE_CD.isna()]
    table = table[table.FOR_MGMT_LAND_BASE_IND == required_for_mgmt_land_base]
    table = table[~table.BEC_ZONE_CODE.isin(list(excluded_bec_zones))]
    table = table[table.PROJ_AGE_1 >= min_proj_age]
    table = table[table.BASAL_AREA >= min_basal_area]
    table = table[table.LIVE_STAND_VOLUME_125 >= min_live_stand_volume]
    return table


def normalize_vri_problem_values(
    *,
    f_table: Any,
    species_slot_count: int = 6,
    fill_token: str = "X",
) -> Any:
    """Normalize null/problematic VRI values shared by downstream workflows."""
    table = f_table.copy()
    pd_module = __import__("pandas")

    for idx in range(1, int(species_slot_count) + 1):
        species_col = f"SPECIES_CD_{idx}"
        species_pct_col = f"SPECIES_PCT_{idx}"
        live_vol_col = f"LIVE_VOL_PER_HA_SPP{idx}_125"
        if species_col in table.columns:
            table[species_col] = table[species_col].fillna(fill_token)
        if species_pct_col in table.columns:
            table[species_pct_col] = pd_module.to_numeric(
                table[species_pct_col], errors="coerce"
            ).fillna(0)
        if live_vol_col in table.columns:
            table[live_vol_col] = pd_module.to_numeric(
                table[live_vol_col], errors="coerce"
            ).fillna(0)

    for column in (
        "SOIL_NUTRIENT_REGIME",
        "SOIL_MOISTURE_REGIME_1",
        "SITE_POSITION_MESO",
        "BCLCS_LEVEL_3",
        "BCLCS_LEVEL_4",
        "BCLCS_LEVEL_5",
        "BEC_VARIANT",
    ):
        if column in table.columns:
            table[column] = table[column].fillna(fill_token)
    if "LIVE_STAND_VOLUME_125" in table.columns:
        table["LIVE_STAND_VOLUME_125"] = pd_module.to_numeric(
            table["LIVE_STAND_VOLUME_125"], errors="coerce"
        ).fillna(0)
    if "PROJ_AGE_1" in table.columns:
        table["PROJ_AGE_1"] = pd_module.to_numeric(table["PROJ_AGE_1"], errors="coerce")
    if "BASAL_AREA" in table.columns:
        table["BASAL_AREA"] = pd_module.to_numeric(table["BASAL_AREA"], errors="coerce")
    return table


def initialize_aflb_land_base_records(
    *,
    f_table: Any,
    species_slot_count: int = 6,
    fill_token: str = "X",
    required_bclcs_level_2: str = "T",
    required_for_mgmt_land_base: str = "Y",
    excluded_bec_zones: Sequence[str] = (),
) -> Any:
    """Build an AFLB-style reconstruction start without AU/VDYP-only pruning.

    This keeps productive/regrowing forest in play for THLB reconstruction,
    leaving stricter age/volume filters to later yield/strata preparation.
    """
    table = normalize_vri_problem_values(
        f_table=f_table,
        species_slot_count=species_slot_count,
        fill_token=fill_token,
    )

    table = table[table.BCLCS_LEVEL_2 == required_bclcs_level_2]
    # Keep productive stands: NON_PRODUCTIVE_CD is null for productive land.
    table = table[table.NON_PRODUCTIVE_CD.isna()]
    table = table[table.FOR_MGMT_LAND_BASE_IND == required_for_mgmt_land_base]
    if excluded_bec_zones:
        table = table[~table.BEC_ZONE_CODE.isin(list(excluded_bec_zones))]
    return table


def filter_post_thlb_stands(
    *,
    f_table: Any,
    required_bclcs_level_2: str = "T",
    required_for_mgmt_land_base: str = "Y",
    excluded_bec_zones: Sequence[str] = ("BAFA", "IMA"),
    species_col: str = "SPECIES_CD_1",
    bclcs_level_5_col: str = "BCLCS_LEVEL_5",
    site_index_col: str = "SITE_INDEX",
) -> Any:
    """Apply legacy checkpoint83 post-THLB stand filters."""
    table = f_table.copy()
    table = table[table.BCLCS_LEVEL_2 == required_bclcs_level_2]
    table = table[table.FOR_MGMT_LAND_BASE_IND == required_for_mgmt_land_base]
    table = table[~table.BEC_ZONE_CODE.isin(list(excluded_bec_zones))]
    table = table[~table[species_col].isnull()]
    table = table[~table[bclcs_level_5_col].isnull()]
    table = table[~table[site_index_col].isnull()]
    return table


def derive_species_list_from_slots(
    *,
    f_table: Any,
    species_slot_count: int = 6,
    species_col_prefix: str = "SPECIES_CD_",
) -> list[str]:
    """Derive unique non-null species codes from species slot columns."""
    values = set().union(
        *[
            f_table[f"{species_col_prefix}{idx}"].unique()
            for idx in range(1, int(species_slot_count) + 1)
        ]
    )
    output: list[str] = []
    for species in values:
        if species is None:
            continue
        try:
            if species != species:
                continue
        except Exception:
            pass
        output.append(species)
    return output
