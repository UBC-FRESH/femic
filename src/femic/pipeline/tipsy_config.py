"""Config-driven TIPSY rule loading and evaluation helpers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import re
import os
from typing import Any, Mapping

import yaml

from femic.pipeline.tipsy import compute_vdyp_oaf1, compute_vdyp_site_index

TipsyParamBuilder = Callable[
    [int, Mapping[str, Any], Mapping[Any, Any]], dict[str, dict[str, Any]]
]

BROADLEAF_SPECIES_CODES = {
    "A",
    "AC",
    "ACB",
    "ACT",
    "AD",
    "AT",
    "AX",
    "D",
    "DR",
    "E",
    "EA",
    "EB",
    "EE",
    "EP",
    "EW",
    "EXP",
    "GP",
    "M",
    "MB",
    "MV",
    "OA",
    "Q",
    "V",
    "W",
    "WA",
    "WB",
    "WD",
    "WP",
    "WS",
}

DEFAULT_TIPSY_SPECIES_CODE_OVERRIDES: dict[str, str] = {
    "SX": "SW",
}


def resolve_tipsy_runtime_options(
    env: Mapping[str, str] | None = None,
    *,
    default_config_dir: str = "config/tipsy",
) -> tuple[str, bool]:
    """Resolve TIPSY runtime config-dir and legacy-toggle flags from environment."""
    env_map = dict(env) if env is not None else os.environ
    config_dir = env_map.get("FEMIC_TIPSY_CONFIG_DIR", default_config_dir)
    use_legacy = env_map.get("FEMIC_TIPSY_USE_LEGACY", "0") == "1"
    return config_dir, use_legacy


def tipsy_config_path_for_tsa(tsa_code: str, config_dir: str | Path) -> Path:
    """Resolve legacy default config path (`tsaXX.yaml`) for a case code."""
    tsa = str(tsa_code).zfill(2)
    return Path(config_dir) / f"tsa{tsa}.yaml"


def _tipsy_config_path_candidates(tsa_code: str, config_dir: str | Path) -> list[Path]:
    code = str(tsa_code).zfill(2)
    base = Path(config_dir)
    return [
        base / f"{code}.yaml",
        base / f"{code}.yml",
        base / f"tsa{code}.yaml",
        base / f"tsa{code}.yml",
    ]


def _resolve_tipsy_config_path(
    *,
    tsa_code: str,
    config_dir: str | Path,
) -> Path | None:
    for path in _tipsy_config_path_candidates(tsa_code, config_dir):
        if path.exists():
            return path
    return None


def load_tipsy_tsa_config(
    *,
    tsa_code: str,
    config_dir: str | Path = "config/tipsy",
) -> dict[str, Any] | None:
    """Load and validate TSA config; return `None` if no TSA config file exists."""
    path = _resolve_tipsy_config_path(tsa_code=tsa_code, config_dir=config_dir)
    if path is None:
        return None
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"TIPSY config is not a mapping: {path}")
    validate_tipsy_tsa_config(payload, tsa_code=tsa_code, path=path)
    return payload


def resolve_tipsy_param_builder(
    *,
    tsa_code: str,
    legacy_builder: TipsyParamBuilder,
    config_dir: str | Path = "config/tipsy",
    use_legacy: bool = False,
) -> tuple[TipsyParamBuilder, str]:
    """Resolve active TIPSY param builder (config-driven or legacy) for a TSA."""
    tsa = str(tsa_code).zfill(2)
    cfg = load_tipsy_tsa_config(tsa_code=tsa, config_dir=config_dir)
    if cfg is not None and not use_legacy:
        cfg_path = _resolve_tipsy_config_path(tsa_code=tsa, config_dir=config_dir)
        if cfg_path is None:
            raise RuntimeError(
                "Resolved TIPSY config payload but config path lookup returned None "
                f"for TSA {tsa} in {config_dir}"
            )

        def _tipsy_params_from_config(
            au_id: int,
            au_data: Mapping[str, Any],
            vdyp_out: Mapping[Any, Any],
        ) -> dict[str, dict[str, Any]]:
            return build_tipsy_params_from_config(
                au_id=au_id,
                au_data=au_data,
                vdyp_out=vdyp_out,
                config=cfg,
            )

        setattr(
            _tipsy_params_from_config,
            "siteprod_si_fallback_by_species",
            _resolve_siteprod_si_fallback_by_species(config=cfg),
        )
        setattr(
            _tipsy_params_from_config,
            "species_code_overrides",
            _resolve_species_code_overrides(config=cfg),
        )
        setattr(
            _tipsy_params_from_config,
            "excluded_stratum_codes",
            _resolve_excluded_stratum_codes(config=cfg),
        )
        return (
            _tipsy_params_from_config,
            f"using config-driven TIPSY rules from {cfg_path}",
        )
    if use_legacy:
        return (
            legacy_builder,
            "using legacy in-code TIPSY rules (FEMIC_TIPSY_USE_LEGACY=1)",
        )
    raise RuntimeError(
        f"Missing TIPSY config for TSA {tsa} in {config_dir}. "
        "Provide config/tipsy/tsaXX.yaml or set FEMIC_TIPSY_USE_LEGACY=1."
    )


def discover_tipsy_config_tsas(
    config_dir: str | Path = "config/tipsy",
) -> dict[str, Path]:
    """Discover TSA config files under a directory."""
    base = Path(config_dir)
    found: dict[str, Path] = {}
    if not base.exists():
        return found
    for path in sorted(base.glob("*.y*ml")):
        match = re.fullmatch(r"(?:tsa)?([A-Za-z0-9_-]+)\.ya?ml", path.name)
        if not match:
            continue
        code = match.group(1)
        normalized = code.zfill(2) if code.isdigit() else code
        found[normalized] = path
    return found


def validate_tipsy_tsa_config(
    payload: Mapping[str, Any],
    *,
    tsa_code: str,
    path: Path,
) -> None:
    """Perform lightweight structural validation for config-driven rules."""
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise ValueError(
            f"Unsupported TIPSY schema_version in {path}: {schema_version!r}"
        )
    tsa_value = str(payload.get("tsa_code", "")).zfill(2)
    if tsa_value != str(tsa_code).zfill(2):
        raise ValueError(
            f"TIPSY config TSA mismatch in {path}: expected {str(tsa_code).zfill(2)!r}, "
            f"found {tsa_value!r}"
        )
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"TIPSY config {path} must include non-empty 'rules'")
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(f"TIPSY config {path} rule[{idx}] must be a mapping")
        if not isinstance(rule.get("id"), str) or not rule["id"].strip():
            raise ValueError(f"TIPSY config {path} rule[{idx}] missing non-empty 'id'")
        when = rule.get("when")
        if not isinstance(when, dict):
            raise ValueError(f"TIPSY config {path} rule[{idx}] missing mapping 'when'")
        assign = rule.get("assign")
        if not isinstance(assign, dict):
            raise ValueError(
                f"TIPSY config {path} rule[{idx}] missing mapping 'assign'"
            )
        for side in ("e", "f"):
            if not isinstance(assign.get(side), dict):
                raise ValueError(
                    f"TIPSY config {path} rule[{idx}] assign.{side} must be a mapping"
                )


def _rule_matches(
    rule: Mapping[str, Any],
    *,
    au_id: int,
    leading_species: str,
    bec: str,
    forest_type: int | None,
    stratum_code: str | None,
    si_level: str | None,
) -> bool:
    when = rule.get("when", {})
    if not isinstance(when, Mapping):
        return False
    au_allow = when.get("au_id_in")
    if isinstance(au_allow, list):
        normalized_au_ids = set()
        for raw_value in au_allow:
            try:
                normalized_au_ids.add(int(raw_value))
            except (TypeError, ValueError):
                continue
        if normalized_au_ids and int(au_id) not in normalized_au_ids:
            return False
    species_allow = when.get("leading_species_in")
    if isinstance(species_allow, list) and leading_species not in species_allow:
        return False
    bec_allow = when.get("bec_in")
    if isinstance(bec_allow, list) and bec not in bec_allow:
        return False
    forest_allow = when.get("forest_type_in")
    if isinstance(forest_allow, list) and forest_type not in forest_allow:
        return False
    stratum_allow = when.get("stratum_code_in")
    if isinstance(stratum_allow, list) and str(stratum_code or "") not in stratum_allow:
        return False
    si_allow = when.get("si_level_in")
    normalized_si = str(si_level or "").strip().upper()
    if isinstance(si_allow, list):
        allowed_si = {
            str(value).strip().upper() for value in si_allow if str(value).strip()
        }
        if allowed_si and normalized_si not in allowed_si:
            return False
    return True


def _normalize_species_for_tipsy(species: str) -> str:
    """Normalize species codes for TIPSY compatibility where needed."""
    return _normalize_species_for_tipsy_with_overrides(
        species,
        species_code_overrides=DEFAULT_TIPSY_SPECIES_CODE_OVERRIDES,
    )


def _normalize_species_for_tipsy_with_overrides(
    species: str,
    *,
    species_code_overrides: Mapping[str, str],
) -> str:
    code = str(species).strip().upper()
    if not code:
        return code
    mapped = species_code_overrides.get(code, code)
    return str(mapped).strip().upper()


def _resolve_species_code_overrides(
    *,
    config: Mapping[str, Any],
) -> dict[str, str]:
    overrides = dict(DEFAULT_TIPSY_SPECIES_CODE_OVERRIDES)
    configured = config.get("species_code_overrides")
    if not isinstance(configured, Mapping):
        return overrides
    for raw_key, raw_value in configured.items():
        key = str(raw_key).strip().upper()
        value = str(raw_value).strip().upper()
        if key and value:
            overrides[key] = value
    return overrides


def _resolve_excluded_stratum_codes(
    *,
    config: Mapping[str, Any],
) -> set[str]:
    configured = config.get("exclude_stratum_codes")
    if not isinstance(configured, list):
        return set()
    return {str(value).strip() for value in configured if str(value).strip()}


def _resolve_siteprod_si_fallback_by_species(
    *,
    config: Mapping[str, Any],
) -> dict[str, float]:
    configured = config.get("siteprod_si_fallback_by_species")
    if not isinstance(configured, Mapping):
        return {}
    fallback_map: dict[str, float] = {}
    for raw_key, raw_value in configured.items():
        key = str(raw_key).strip().upper()
        if not key:
            continue
        try:
            fallback_map[key] = float(raw_value)
        except (TypeError, ValueError):
            continue
    return fallback_map


def _resolve_assignment_value(
    value: Any,
    *,
    leading_species: str,
    bec: str,
    forest_type: int | None,
    species_ranked: list[tuple[str, float]],
    species_code_overrides: Mapping[str, str],
) -> Any:
    if not isinstance(value, str):
        return value
    if value == "$leading_species":
        return leading_species
    if value == "$leading_species_tipsy":
        return _normalize_species_for_tipsy_with_overrides(
            leading_species,
            species_code_overrides=species_code_overrides,
        )
    if value == "$bec":
        return bec
    if value == "$forest_type":
        return forest_type
    match_spp = re.fullmatch(r"\$species_rank_(\d+)_tipsy", value)
    if match_spp:
        idx = int(match_spp.group(1)) - 1
        if 0 <= idx < len(species_ranked):
            return _normalize_species_for_tipsy_with_overrides(
                species_ranked[idx][0],
                species_code_overrides=species_code_overrides,
            )
        return None
    match_pct = re.fullmatch(r"\$species_pct_(\d+)", value)
    if match_pct:
        idx = int(match_pct.group(1)) - 1
        if 0 <= idx < len(species_ranked):
            return species_ranked[idx][1]
        return None
    return value


def _resolve_assignment_block(
    block: Mapping[str, Any],
    *,
    leading_species: str,
    bec: str,
    forest_type: int | None,
    species_ranked: list[tuple[str, float]],
    species_code_overrides: Mapping[str, str],
) -> dict[str, Any]:
    return {
        key: _resolve_assignment_value(
            value,
            leading_species=leading_species,
            bec=bec,
            forest_type=forest_type,
            species_ranked=species_ranked,
            species_code_overrides=species_code_overrides,
        )
        for key, value in block.items()
    }


def _round_percentages_to_100(percentages: list[float]) -> list[int]:
    if not percentages:
        return []
    clipped = [max(0.0, float(value)) for value in percentages]
    floors = [int(value) for value in clipped]
    remainder = 100 - sum(floors)
    if remainder > 0:
        fractions = [(value - int(value), idx) for idx, value in enumerate(clipped)]
        for _fraction, idx in sorted(fractions, reverse=True)[:remainder]:
            floors[idx] += 1
    elif remainder < 0:
        over = -remainder
        fractions = [(value - int(value), idx) for idx, value in enumerate(clipped)]
        for _fraction, idx in sorted(fractions)[:over]:
            if floors[idx] > 0:
                floors[idx] -= 1
    return floors


def _finalize_species_mix(
    *,
    side_map: dict[str, Any],
    leading_species: str,
    species_code_overrides: Mapping[str, str],
) -> None:
    entries: list[tuple[str, float]] = []
    for idx in range(1, 6):
        spp_key = f"SPP_{idx}"
        pct_key = f"PCT_{idx}"
        spp_raw = side_map.get(spp_key)
        pct_raw = side_map.get(pct_key)
        if spp_raw in (None, ""):
            continue
        if pct_raw is None:
            continue
        try:
            pct = float(pct_raw)
        except (TypeError, ValueError):
            continue
        if pct <= 0:
            continue
        entries.append(
            (
                _normalize_species_for_tipsy_with_overrides(
                    str(spp_raw),
                    species_code_overrides=species_code_overrides,
                ),
                pct,
            )
        )

    if not entries:
        entries = [
            (
                _normalize_species_for_tipsy_with_overrides(
                    leading_species,
                    species_code_overrides=species_code_overrides,
                ),
                100.0,
            )
        ]

    # In treated rows, strip broadleaf species and re-allocate their share to a
    # conifer species to avoid BatchTIPSY treated-curve/mapping failures.
    if str(side_map.get("Regen_Method", "P")).upper() == "P":
        broadleaf_pct = sum(
            pct for spp, pct in entries if spp.upper() in BROADLEAF_SPECIES_CODES
        )
        entries = [
            (spp, pct)
            for spp, pct in entries
            if spp.upper() not in BROADLEAF_SPECIES_CODES
        ]
        if not entries:
            entries = [
                (
                    _normalize_species_for_tipsy_with_overrides(
                        leading_species,
                        species_code_overrides=species_code_overrides,
                    ),
                    broadleaf_pct,
                )
            ]
        elif broadleaf_pct > 0:
            spp0, pct0 = entries[0]
            entries[0] = (spp0, pct0 + broadleaf_pct)

    entries.sort(key=lambda item: item[1], reverse=True)

    if len(entries) > 5:
        spp5, pct5 = entries[4]
        pct5 += sum(pct for _spp, pct in entries[5:])
        entries = entries[:4] + [(spp5, pct5)]

    rounded = _round_percentages_to_100([pct for _spp, pct in entries])
    entries = [(spp, pct) for (spp, _pct), pct in zip(entries, rounded)]

    for idx in range(1, 6):
        side_map[f"SPP_{idx}"] = None
        side_map[f"PCT_{idx}"] = None
    for idx, (spp, pct) in enumerate(entries, start=1):
        side_map[f"SPP_{idx}"] = spp
        side_map[f"PCT_{idx}"] = int(pct)


def build_tipsy_params_from_config(
    *,
    au_id: int,
    au_data: Mapping[str, Any],
    vdyp_out: Mapping[Any, Any],
    config: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build TIPSY parameter rows using configured rule assignments."""
    tp: dict[str, dict[str, Any]] = {"e": {}, "f": {}}
    species_code_overrides = _resolve_species_code_overrides(config=config)
    ss = au_data["ss"]
    species = au_data["species"]
    leading_species = list(species.keys())[0]
    species_ranked = [
        (str(spp), float(species[spp]["pct"]))
        for spp in species
        if isinstance(species[spp], Mapping) and "pct" in species[spp]
    ]
    bec = ss.BEC_ZONE_CODE.iloc[0]
    stratum_code = str(au_data.get("stratum_code", "")).strip()
    si_level = str(au_data.get("si_level", "")).strip().upper()
    if (not stratum_code) and "stratum_code" in ss:
        try:
            stratum_code = str(ss["stratum_code"].mode().iloc[0]).strip()
        except (ValueError, TypeError, IndexError, KeyError, AttributeError):
            stratum_code = ""
    forest_type: int | None = None
    if "forest_type" in ss:
        try:
            forest_type = int(ss["forest_type"].mode().iloc[0])
        except (ValueError, TypeError, IndexError, KeyError, AttributeError):
            forest_type = None

    for side in ("e", "f"):
        defaults = config.get("defaults", {}).get(side, {})
        if isinstance(defaults, Mapping):
            tp[side].update(
                _resolve_assignment_block(
                    defaults,
                    leading_species=leading_species,
                    bec=bec,
                    forest_type=forest_type,
                    species_ranked=species_ranked,
                    species_code_overrides=species_code_overrides,
                )
            )
    for rule in config["rules"]:
        if _rule_matches(
            rule,
            au_id=au_id,
            leading_species=leading_species,
            bec=bec,
            forest_type=forest_type,
            stratum_code=stratum_code,
            si_level=si_level,
        ):
            for side in ("e", "f"):
                tp[side].update(
                    _resolve_assignment_block(
                        rule["assign"][side],
                        leading_species=leading_species,
                        bec=bec,
                        forest_type=forest_type,
                        species_ranked=species_ranked,
                        species_code_overrides=species_code_overrides,
                    )
                )
            break
    else:
        raise ValueError(
            f"No TIPSY config rule matched AU {au_id} (leading_species={leading_species}, "
            f"BEC={bec}, forest_type={forest_type})"
        )

    si = compute_vdyp_site_index(vdyp_out)
    if si != si:  # NaN
        si = round(float(ss.SITE_INDEX.median()), 1)
    oaf1 = compute_vdyp_oaf1(vdyp_out)
    if oaf1 != oaf1:  # NaN
        oaf1 = 0.85

    tp["e"]["AU"] = tp["e"]["TBLno"] = 10000 + int(au_id)
    tp["f"]["AU"] = tp["f"]["TBLno"] = 20000 + int(au_id)
    for side in ("e", "f"):
        c1_raw = tp[side].pop("SI_c1", tp[side].pop("si_c1", 1.0))
        c2_raw = tp[side].pop("SI_c2", tp[side].pop("si_c2", 0.0))
        # Backward-compatible additive offset alias.
        offset_raw = tp[side].pop("SI_offset", tp[side].pop("si_offset", 0.0))

        c1 = 1.0 if c1_raw in (None, "") else float(c1_raw)
        c2 = 0.0 if c2_raw in (None, "") else float(c2_raw)
        offset = 0.0 if offset_raw in (None, "") else float(offset_raw)

        tp[side]["SI"] = round((c1 * si) + c2 + offset, 1)
    tp["e"]["BEC"] = tp["f"]["BEC"] = bec
    tp["e"]["OAF1"] = tp["f"]["OAF1"] = oaf1
    if str(tp["e"].get("Regen_Method", "")).upper() == "N":
        _finalize_species_mix(
            side_map=tp["e"],
            leading_species=leading_species,
            species_code_overrides=species_code_overrides,
        )
    _finalize_species_mix(
        side_map=tp["f"],
        leading_species=leading_species,
        species_code_overrides=species_code_overrides,
    )
    return tp
