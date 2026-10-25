"""Build the static carbon input package consumed by WS4 and WS3.

The package is the producer-side contract described in
``docs/reference/contracts/carbon-domain.rst``. It contains the CBM classifiers,
disturbance map, age classes, initial inventory, merchantable yield table, track and
species maps, boundaries, and a manifest with provenance.

This module does not run a carbon engine and does not know a WS4 schedule.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module, metadata
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from femic import __version__

if TYPE_CHECKING:
    from femic.fmg.core import BundleModelContext, CurvePoint

SCHEMA_VERSION = "0.1"
DEFAULT_AGE_INTERVAL = 10
DEFAULT_MAX_AGE = 300
DEFAULT_VOLUME_FEATURE_LABEL = "feature.Volume"
DEFAULT_HISTORIC_DISTURBANCE = "fire"

TABLE_FILES: dict[str, str] = {
    "classifiers": "classifiers.csv",
    "disturbance_types": "disturbance_types.csv",
    "age_classes": "age_classes.csv",
    "inventory": "inventory.csv",
    "yield": "yield.csv",
    "track_carbon_map": "track_carbon_map.csv",
    "curve_carbon_map": "curve_carbon_map.csv",
    "species_map": "species_map.csv",
    "boundaries": "boundaries.csv",
}

UNITS: dict[str, str] = {
    "area": "ha",
    "volume": "m3/ha",
    "carbon": "tC",
    "carbon_density": "tC/ha",
    "co2e": "tCO2e",
}


@dataclass(frozen=True)
class SpeciesMapping:
    """One BC species to CBM species crosswalk row.

    Attributes
    ----------
    bc_species : str
        BC species code.
    common_name : str
        Human-readable common name.
    cbm_species : str
        CBM default species name.
    wood_type : {"softwood", "hardwood"}
        Softwood or hardwood.
    confidence : str
        Review confidence.
    source : str
        Provenance note.
    notes : str
        Further caveats.
    """

    bc_species: str
    common_name: str
    cbm_species: str
    wood_type: str
    confidence: str
    source: str
    notes: str


@dataclass(frozen=True)
class DisturbanceMapping:
    """One treatment to CBM disturbance crosswalk row.

    Attributes
    ----------
    treatment_pattern : str
        Normalized treatment label.
    default_dist_type : str
        CBM default disturbance type.
    removes_biomass : bool
        Whether the disturbance removes biomass.
    transition_reset_age : int
        Reset age used by the transition rule.
    regen_delay : int
        Regeneration delay used by the transition rule.
    confidence : str
        Review confidence.
    notes : str
        Further caveats.
    """

    treatment_pattern: str
    default_dist_type: str
    removes_biomass: bool
    transition_reset_age: int
    regen_delay: int
    confidence: str
    notes: str


@dataclass(frozen=True)
class CarbonExportConfig:
    """The crosswalks and provenance used by one package export.

    Attributes
    ----------
    admin_boundary : str
        CBM administrative boundary.
    eco_boundary : str
        CBM eco boundary.
    species_map : dict of str to SpeciesMapping
        BC species code (uppercase) to mapping.
    disturbance_map : dict of str to DisturbanceMapping
        Normalized treatment label to mapping.
    land_class_by_ifm : dict of str to int
        IFM state to CBM land class.
    fallback_softwood : str
        CBM species used for an unmapped conifer.
    fallback_hardwood : str
        CBM species used for an unmapped broadleaf.
    fallback_wood_type : {"softwood", "hardwood"}
        Fallback when an unmapped species cannot be classified.
    cbm_defaults_version : str
        CBM defaults database version.
    cbm_defaults_sha256 : str
        CBM defaults database digest.
    cbm_defaults_source : str
        Where the database came from.
    age_interval : int
        Yield grid width in years.
    max_age : int
        Maximum yield age.
    volume_feature_label : str
        WS4 feature label that carries merchantable volume.
    """

    admin_boundary: str
    eco_boundary: str
    species_map: Mapping[str, SpeciesMapping]
    disturbance_map: Mapping[str, DisturbanceMapping]
    land_class_by_ifm: Mapping[str, int]
    fallback_softwood: str
    fallback_hardwood: str
    fallback_wood_type: str
    cbm_defaults_version: str
    cbm_defaults_sha256: str
    cbm_defaults_source: str
    age_interval: int = DEFAULT_AGE_INTERVAL
    max_age: int = DEFAULT_MAX_AGE
    volume_feature_label: str = DEFAULT_VOLUME_FEATURE_LABEL


@dataclass(frozen=True)
class CarbonExportResult:
    """The files and totals produced by a package export.

    Attributes
    ----------
    package_dir : Path
        Package directory.
    manifest_path : Path
        Manifest path.
    table_paths : dict of str to Path
        Logical table name to written CSV path.
    package_id : str
        Producer-assigned identifier.
    fingerprint : str
        Stable package digest.
    track_count : int
        Number of package tracks.
    inventory_area_ha : float
        Total initial inventory area.
    yield_rows : int
        Number of yield rows.
    """

    package_dir: Path
    manifest_path: Path
    table_paths: Mapping[str, Path]
    package_id: str
    fingerprint: str
    track_count: int
    inventory_area_ha: float
    yield_rows: int


def load_carbon_export_config(
    config_dir: Path = Path("config/carbon"),
    *,
    admin_boundary: str,
    eco_boundary: str,
    cbm_defaults_version: str | None = None,
    cbm_defaults_sha256: str | None = None,
    cbm_defaults_source: str = "libcbm",
    age_interval: int = DEFAULT_AGE_INTERVAL,
    max_age: int = DEFAULT_MAX_AGE,
    volume_feature_label: str = DEFAULT_VOLUME_FEATURE_LABEL,
) -> CarbonExportConfig:
    """Load the draft crosswalks and the CBM defaults provenance.

    Parameters
    ----------
    config_dir : Path, optional
        Directory holding the crosswalk CSVs. Defaults to ``config/carbon``.
    admin_boundary : str
        CBM administrative boundary.
    eco_boundary : str
        CBM eco boundary.
    cbm_defaults_version : str or None, optional
        CBM defaults version. Detected from libcbm when omitted.
    cbm_defaults_sha256 : str or None, optional
        CBM defaults digest. Detected from libcbm when omitted.
    cbm_defaults_source : str, optional
        Source label. Defaults to ``libcbm``.
    age_interval : int, optional
        Yield grid width. Defaults to 10.
    max_age : int, optional
        Maximum yield age. Defaults to 300.
    volume_feature_label : str, optional
        WS4 feature label for merchantable volume.

    Returns
    -------
    CarbonExportConfig
        The validated export configuration.

    Raises
    ------
    FileNotFoundError
        When a crosswalk file is missing.
    ValueError
        When a required column or value is missing, or the CBM defaults cannot be
        identified.
    """
    root = Path(config_dir)
    species = _load_species_map(root / "species_map.bc.csv")
    disturbances = _load_disturbance_map(root / "disturbance_map.bc.csv")
    land_classes = _load_land_classes(root / "land_class.bc.csv")
    detected_version, detected_sha = _detect_cbm_defaults()
    version = cbm_defaults_version or detected_version
    sha256 = cbm_defaults_sha256 or detected_sha
    if not version or not sha256:
        raise ValueError(
            "cbm_defaults version and sha256 are required when libcbm is not installed"
        )
    fallback_softwood = _fallback_species(species, "softwood")
    fallback_hardwood = _fallback_species(species, "hardwood")
    return CarbonExportConfig(
        admin_boundary=admin_boundary,
        eco_boundary=eco_boundary,
        species_map=species,
        disturbance_map=disturbances,
        land_class_by_ifm=land_classes,
        fallback_softwood=fallback_softwood,
        fallback_hardwood=fallback_hardwood,
        fallback_wood_type="softwood",
        cbm_defaults_version=version,
        cbm_defaults_sha256=sha256,
        cbm_defaults_source=cbm_defaults_source,
        age_interval=age_interval,
        max_age=max_age,
        volume_feature_label=volume_feature_label,
    )


def build_carbon_package_tables(
    *,
    context: BundleModelContext,
    inventory: pd.DataFrame,
    config: CarbonExportConfig,
    track_names: Mapping[tuple[int, str], str] | None = None,
    species_by_au: Mapping[int, str] | None = None,
    shares_by_au: Mapping[int, tuple[float, float]] | None = None,
) -> dict[str, pd.DataFrame]:
    """Build the package tables from a bundle context and an inventory.

    Parameters
    ----------
    context : BundleModelContext
        The bundle's analysis units and curves.
    inventory : pandas.DataFrame
        Initial inventory with ``au_id``, ``ifm``, ``age``, and ``area_ha``.
    config : CarbonExportConfig
        Crosswalks and provenance.
    track_names : dict, optional
        ``(au_id, ifm)`` to exact WS4 track name. When omitted, the canonical
        ``AU(<id>)+IFM(<ifm>)+treatment()`` name is used.
    species_by_au : dict, optional
        ``au_id`` to BC species code override.
    shares_by_au : dict, optional
        ``au_id`` to ``(softwood_share, hardwood_share)``.

    Returns
    -------
    dict of str to pandas.DataFrame
        Table name to frame.

    Raises
    ------
    ValueError
        When the inventory is missing required columns or a track cannot be
        resolved.
    """
    required = {"au_id", "ifm", "age", "area_ha"}
    missing = sorted(required.difference(inventory.columns))
    if missing:
        raise ValueError(f"carbon inventory missing required columns: {missing}")
    if config.age_interval <= 0 or config.max_age < config.age_interval:
        raise ValueError("age_interval and max_age must define a positive yield grid")

    analysis_units = {au.au_id: au for au in context.analysis_units}
    normalized = inventory.copy()
    normalized["au_id"] = pd.to_numeric(normalized["au_id"], errors="raise").astype(int)
    normalized["ifm"] = normalized["ifm"].astype(str).str.strip().str.lower()
    normalized["age"] = pd.to_numeric(normalized["age"], errors="raise").astype(int)
    normalized["area_ha"] = pd.to_numeric(normalized["area_ha"], errors="raise").astype(
        float
    )
    if "track_name" not in normalized.columns:
        normalized["track_name"] = [
            _track_name(int(str(row.au_id)), str(row.ifm), track_names)
            for row in normalized.itertuples(index=False)
        ]

    track_species: dict[str, SpeciesMapping] = {}
    track_shares: dict[str, tuple[float, float]] = {}
    for track_name, block in normalized.groupby("track_name", sort=True):
        first = block.iloc[0]
        au_id = int(first["au_id"])
        au = analysis_units.get(au_id)
        if au is None:
            raise ValueError(f"track {track_name!r} names unknown AU {au_id}")
        mapping = _species_for_au(
            au_id=au_id,
            stratum_code=au.stratum_code,
            config=config,
            species_by_au=species_by_au,
        )
        track_species[str(track_name)] = mapping
        shares = shares_by_au.get(au_id) if shares_by_au else None
        track_shares[str(track_name)] = _normalize_shares(shares, mapping.wood_type)

    ys = _yield_tables(context, normalized, track_species, track_shares, config)
    classifiers = _classifier_table(normalized, track_species)
    track_map = _track_map(normalized, track_species, track_shares, config)
    return {
        "classifiers": classifiers,
        "disturbance_types": _disturbance_table(config),
        "age_classes": _age_classes(config),
        "inventory": _inventory_table(normalized, config),
        "yield": ys["yield"],
        "track_carbon_map": track_map,
        "curve_carbon_map": ys["curve_carbon_map"],
        "species_map": _species_table(config),
        "boundaries": pd.DataFrame(
            [
                {
                    "admin_boundary": config.admin_boundary,
                    "eco_boundary": config.eco_boundary,
                }
            ]
        ),
    }


def write_carbon_package(
    *,
    tables: Mapping[str, pd.DataFrame],
    output_dir: Path,
    config: CarbonExportConfig,
    source_hashes: Sequence[tuple[str, str]],
    package_label: str,
) -> CarbonExportResult:
    """Write package tables and a manifest, then return the file record.

    Parameters
    ----------
    tables : mapping of str to pandas.DataFrame
        Table name to frame.
    output_dir : Path
        Package directory.
    config : CarbonExportConfig
        Crosswalks and provenance.
    source_hashes : sequence of (str, str)
        Public-safe source label and SHA-256 digest.
    package_label : str
        Short label used in the package id.

    Returns
    -------
    CarbonExportResult
        The written package and its totals.

    Raises
    ------
    ValueError
        When a required table is missing.
    """
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    missing = sorted(set(TABLE_FILES).difference(tables))
    if missing:
        raise ValueError(f"carbon package missing tables: {missing}")

    table_paths: dict[str, Path] = {}
    table_hashes: dict[str, str] = {}
    for name, file_name in TABLE_FILES.items():
        path = root / file_name
        tables[name].to_csv(path, index=False)
        table_paths[name] = path
        table_hashes[name] = _sha256(path)

    fingerprint = _fingerprint(table_hashes, source_hashes, config)
    package_id = f"femic-carbon-{package_label}-{fingerprint[:12]}"
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "package_id": package_id,
        "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "producer": {"name": "femic", "version": _producer_version()},
        "sources": [{"path": path, "sha256": digest} for path, digest in source_hashes],
        "cbm_defaults": {
            "version": config.cbm_defaults_version,
            "sha256": config.cbm_defaults_sha256,
            "source": config.cbm_defaults_source,
        },
        "units": UNITS,
        "boundaries": {"admin": config.admin_boundary, "eco": config.eco_boundary},
        "mapping": {
            "track_key": "track_name",
            "species_classifier": "species",
            "disturbance_classifier": "user_dist_type",
        },
        "event_source": "ws4.schedule",
        "transition_source": "ws4.treatments",
        "table_files": TABLE_FILES,
        "table_hashes": table_hashes,
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return CarbonExportResult(
        package_dir=root,
        manifest_path=manifest_path,
        table_paths=table_paths,
        package_id=package_id,
        fingerprint=fingerprint,
        track_count=int(tables["track_carbon_map"].shape[0]),
        inventory_area_ha=float(
            pd.to_numeric(tables["inventory"]["area_ha"], errors="coerce").sum()
        ),
        yield_rows=int(tables["yield"].shape[0]),
    )


def export_carbon_package(
    *,
    bundle_dir: Path,
    checkpoint_path: Path,
    output_dir: Path = Path("output/carbon"),
    tsa_list: Sequence[str],
    config: CarbonExportConfig,
    dataset_dir: Path | None = None,
    species_checkpoint_path: Path | None = None,
    fragments_crs: str = "EPSG:3005",
    initial_age_cap: int | None = None,
    age_class_width: int | None = None,
    thlb_min: float | None = None,
    species_by_au: Mapping[int, str] | None = None,
) -> CarbonExportResult:
    """Export a carbon package from a FEMIC bundle and checkpoint.

    Parameters
    ----------
    bundle_dir : Path
        Bundle directory with ``au_table.csv``, ``curve_table.csv``, and
        ``curve_points_table.csv``.
    checkpoint_path : Path
        FEMIC checkpoint feather with the fragment inventory.
    output_dir : Path, optional
        Package directory. Defaults to ``output/carbon``.
    tsa_list : sequence of str
        TSA or FMU codes to include.
    config : CarbonExportConfig
        Crosswalks and provenance.
    dataset_dir : Path or None, optional
        A compiled WS4 dataset used to resolve exact ``track_name`` values from
        its ``tracks.parquet``. When omitted, canonical names are generated.
    species_checkpoint_path : Path or None, optional
        Species checkpoint used for softwood/hardwood shares.
    fragments_crs : str, optional
        CRS assigned to the fragment inventory. Defaults to ``EPSG:3005``.
    initial_age_cap : int or None, optional
        Optional initial-age cap.
    age_class_width : int or None, optional
        Optional initial-age snapping width.
    thlb_min : float or None, optional
        Optional THLB signal threshold.
    species_by_au : mapping, optional
        AU id to BC species code override.

    Returns
    -------
    CarbonExportResult
        The written package and its totals.
    """
    from femic.fmg.adapters import build_bundle_model_context, normalize_tsa_code
    from femic.fmg.woodstock import (
        DEFAULT_SPECIES_CHECKPOINT_NAME,
        build_woodstock_areas_table,
        compute_au_species_shares,
    )

    normalized_tsa = sorted({normalize_tsa_code(value) for value in tsa_list})
    if not normalized_tsa:
        raise ValueError("provide at least one TSA/code for the carbon export")
    context = build_bundle_model_context(
        bundle_dir=Path(bundle_dir), tsa_list=normalized_tsa
    )
    au_table = pd.DataFrame(
        [
            {
                "au_id": au.au_id,
                "tsa": au.tsa,
                "stratum_code": au.stratum_code,
                "si_level": au.si_level,
                "managed_curve_id": au.managed_curve_id,
                "unmanaged_curve_id": au.unmanaged_curve_id,
            }
            for au in context.analysis_units
        ]
    )
    areas = build_woodstock_areas_table(
        checkpoint_path=Path(checkpoint_path),
        au_table=au_table,
        tsa_list=normalized_tsa,
        fragments_crs=fragments_crs,
        initial_age_cap=initial_age_cap,
        age_class_width=age_class_width,
        thlb_min=thlb_min,
    )
    shares: dict[int, tuple[float, float]] = {}
    resolved_species_checkpoint = (
        Path(species_checkpoint_path)
        if species_checkpoint_path is not None
        else Path(checkpoint_path).parent / DEFAULT_SPECIES_CHECKPOINT_NAME
    )
    if resolved_species_checkpoint.is_file():
        raw_shares = compute_au_species_shares(
            species_checkpoint_path=resolved_species_checkpoint,
            au_checkpoint_path=Path(checkpoint_path),
            min_thlb=thlb_min,
        )
        shares = {
            int(au_id): (float(values.get("sw", 0.0)), float(values.get("hw", 0.0)))
            for au_id, values in raw_shares.items()
        }
    track_names = (
        track_names_from_compiled_dataset(Path(dataset_dir))
        if dataset_dir is not None
        else None
    )
    inventory = areas.loc[:, ["au_id", "ifm", "age", "area_ha"]].copy()
    tables = build_carbon_package_tables(
        context=context,
        inventory=inventory,
        config=config,
        track_names=track_names,
        species_by_au=species_by_au,
        shares_by_au=shares,
    )
    source_hashes = [
        (f"bundle/{name}", _sha256(Path(bundle_dir) / name))
        for name in ("au_table.csv", "curve_table.csv", "curve_points_table.csv")
        if (Path(bundle_dir) / name).is_file()
    ]
    source_hashes.append(
        (f"checkpoint/{Path(checkpoint_path).name}", _sha256(Path(checkpoint_path)))
    )
    label = "-".join(normalized_tsa)
    return write_carbon_package(
        tables=tables,
        output_dir=Path(output_dir),
        config=config,
        source_hashes=source_hashes,
        package_label=label,
    )


def track_names_from_compiled_dataset(dataset_dir: Path) -> dict[tuple[int, str], str]:
    """Read exact track names from a compiled WS4 dataset.

    The parser understands the canonical ``AU(<id>)`` and ``IFM(<state>)`` tokens
    used by the simple matrix builder. A model with additional themes can still use
    the result when each AU/IFM pair has one track; otherwise the caller should
    supply an explicit map.

    Parameters
    ----------
    dataset_dir : Path
        Compiled dataset directory with ``tracks.parquet``.

    Returns
    -------
    dict of (int, str) to str
        ``(au_id, ifm)`` to track name.

    Raises
    ------
    ValueError
        When an AU/IFM pair resolves to more than one track.
    """
    import re

    tracks = pd.read_parquet(Path(dataset_dir) / "tracks.parquet")
    result: dict[tuple[int, str], str] = {}
    for row in tracks.itertuples(index=False):
        name = str(row.name)
        au_match = re.search(r"AU\((\d+)\)", name)
        ifm_match = re.search(r"IFM\(([^)]+)\)", name)
        if not au_match or not ifm_match:
            continue
        key = (int(au_match.group(1)), ifm_match.group(1).strip().lower())
        if key in result and result[key] != name:
            raise ValueError(
                f"AU {key[0]} / IFM {key[1]} resolves to more than one track; "
                "supply an explicit track-name map"
            )
        result[key] = name
    return result


def _load_species_map(path: Path) -> dict[str, SpeciesMapping]:
    """Load the species crosswalk."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {"bc_species", "cbm_species", "wood_type", "confidence"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}")
    result: dict[str, SpeciesMapping] = {}
    for row in frame.to_dict("records"):
        code = str(row["bc_species"]).strip().upper()
        if not code:
            raise ValueError(f"{path} has an empty bc_species")
        result[code] = SpeciesMapping(
            bc_species=code,
            common_name=str(row.get("common_name", "")).strip(),
            cbm_species=str(row["cbm_species"]).strip(),
            wood_type=str(row["wood_type"]).strip().lower(),
            confidence=str(row["confidence"]).strip(),
            source=str(row.get("source", "")).strip(),
            notes=str(row.get("notes", "")).strip(),
        )
    return result


def _load_disturbance_map(path: Path) -> dict[str, DisturbanceMapping]:
    """Load the disturbance crosswalk."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {
        "treatment_pattern",
        "default_dist_type",
        "removes_biomass",
        "transition_reset_age",
        "regen_delay",
        "confidence",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}")
    result: dict[str, DisturbanceMapping] = {}
    for row in frame.to_dict("records"):
        pattern = str(row["treatment_pattern"]).strip().lower()
        if not pattern:
            raise ValueError(f"{path} has an empty treatment_pattern")
        result[pattern] = DisturbanceMapping(
            treatment_pattern=pattern,
            default_dist_type=str(row["default_dist_type"]).strip(),
            removes_biomass=str(row["removes_biomass"]).strip().lower()
            in {"true", "1", "yes", "y"},
            transition_reset_age=int(str(row["transition_reset_age"])),
            regen_delay=int(str(row["regen_delay"])),
            confidence=str(row["confidence"]).strip(),
            notes=str(row.get("notes", "")).strip(),
        )
    return result


def _load_land_classes(path: Path) -> dict[str, int]:
    """Load the IFM to land-class map."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {"ifm", "landclass"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}")
    return {
        str(row["ifm"]).strip().lower(): int(str(row["landclass"]))
        for row in frame.to_dict("records")
    }


def _fallback_species(species: Mapping[str, SpeciesMapping], wood_type: str) -> str:
    """Return the explicit fallback species for a wood type."""
    code = "UNK_SW" if wood_type == "softwood" else "UNK_HW"
    mapping = species.get(code)
    if mapping is not None:
        return mapping.cbm_species
    return (
        "Unspecified softwood species"
        if wood_type == "softwood"
        else "Unspecified hardwood species"
    )


def _detect_cbm_defaults() -> tuple[str | None, str | None]:
    """Detect the bundled libcbm CBM defaults version and digest."""
    try:
        resources = import_module("libcbm.resources")
    except ImportError:
        return None, None
    path = Path(resources.get_cbm_defaults_path())
    version = path.stem.removeprefix("cbm_defaults_v")
    return version, _sha256(path)


def _producer_version() -> str:
    """Return the installed FEMIC version, falling back to the source constant."""
    try:
        return metadata.version("femic")
    except metadata.PackageNotFoundError:
        return __version__


def _track_name(
    au_id: int,
    ifm: str,
    track_names: Mapping[tuple[int, str], str] | None,
) -> str:
    """Return the exact or canonical track name for an AU/IFM pair."""
    if track_names is not None:
        name = track_names.get((au_id, ifm))
        if name is None:
            raise ValueError(f"no track name for AU {au_id} / IFM {ifm}")
        return name
    return f"AU({au_id})+IFM({ifm})+treatment()"


def _species_for_au(
    *,
    au_id: int,
    stratum_code: str,
    config: CarbonExportConfig,
    species_by_au: Mapping[int, str] | None,
) -> SpeciesMapping:
    """Resolve the CBM species for an AU."""
    code = None
    if species_by_au is not None:
        code = species_by_au.get(au_id)
    if not code:
        code = str(stratum_code).split("_")[-1].split("+")[0].strip().upper()
    mapping = config.species_map.get(str(code).upper())
    if mapping is not None:
        return mapping
    if config.fallback_wood_type == "hardwood":
        return SpeciesMapping(
            bc_species=str(code or "UNK_HW"),
            common_name="unmapped broadleaf",
            cbm_species=config.fallback_hardwood,
            wood_type="hardwood",
            confidence="low",
            source="fallback",
            notes="species code not in the crosswalk",
        )
    return SpeciesMapping(
        bc_species=str(code or "UNK_SW"),
        common_name="unmapped conifer",
        cbm_species=config.fallback_softwood,
        wood_type="softwood",
        confidence="low",
        source="fallback",
        notes="species code not in the crosswalk",
    )


def _normalize_shares(
    shares: tuple[float, float] | None,
    wood_type: str,
) -> tuple[float, float]:
    """Return non-negative shares that sum to at most one."""
    if shares is None:
        return (1.0, 0.0) if wood_type == "softwood" else (0.0, 1.0)
    softwood = max(0.0, float(shares[0]))
    hardwood = max(0.0, float(shares[1]))
    total = softwood + hardwood
    if total > 1.0:
        softwood /= total
        hardwood /= total
    if total <= 0.0:
        return (1.0, 0.0) if wood_type == "softwood" else (0.0, 1.0)
    return softwood, hardwood


def _yield_tables(
    context: BundleModelContext,
    inventory: pd.DataFrame,
    track_species: Mapping[str, SpeciesMapping],
    track_shares: Mapping[str, tuple[float, float]],
    config: CarbonExportConfig,
) -> dict[str, pd.DataFrame]:
    """Build the long yield table and the curve map."""
    yield_rows: list[dict[str, object]] = []
    curve_rows: list[dict[str, object]] = []
    ages = list(range(0, config.max_age + 1, config.age_interval))
    for track_name, block in inventory.groupby("track_name", sort=True):
        first = block.iloc[0]
        au_id = int(first["au_id"])
        ifm = str(first["ifm"])
        au = next(
            (item for item in context.analysis_units if item.au_id == au_id), None
        )
        if au is None:
            raise ValueError(f"track {track_name!r} names unknown AU {au_id}")
        curve_id = au.managed_curve_id if ifm == "managed" else au.unmanaged_curve_id
        curve = context.curves_by_id.get(curve_id)
        if curve is None:
            raise ValueError(f"AU {au_id} has no {ifm} curve {curve_id}")
        mapping = track_species[str(track_name)]
        softwood, hardwood = track_shares[str(track_name)]
        component = "softwood" if softwood >= hardwood else "hardwood"
        for age in ages:
            yield_rows.append(
                {
                    "track_name": str(track_name),
                    "species": component,
                    "leading_species": mapping.cbm_species,
                    "age": age,
                    "volume_m3_ha": _curve_value(curve.points, age),
                }
            )
        curve_rows.append(
            {
                "track_name": str(track_name),
                "feature_label": config.volume_feature_label,
                "species": component,
                "share": 1.0,
            }
        )
    return {
        "yield": pd.DataFrame(
            yield_rows,
            columns=["track_name", "species", "leading_species", "age", "volume_m3_ha"],
        ),
        "curve_carbon_map": pd.DataFrame(
            curve_rows, columns=["track_name", "feature_label", "species", "share"]
        ),
    }


def _curve_value(points: Sequence[CurvePoint], age: int) -> float:
    """Linearly interpolate a curve at an age, clamping at the endpoints."""
    if not points:
        return 0.0
    ordered = sorted((float(point.x), float(point.y)) for point in points)
    if age <= ordered[0][0]:
        return ordered[0][1]
    if age >= ordered[-1][0]:
        return ordered[-1][1]
    for (x0, y0), (x1, y1) in itertools.pairwise(ordered):
        if x0 <= age <= x1:
            if x1 == x0:
                return y1
            fraction = (age - x0) / (x1 - x0)
            return y0 + fraction * (y1 - y0)
    return ordered[-1][1]


def _classifier_table(
    inventory: pd.DataFrame,
    track_species: Mapping[str, SpeciesMapping],
) -> pd.DataFrame:
    """Build the long-form classifier table."""
    rows: list[dict[str, object]] = []
    for track_name in sorted(inventory["track_name"].astype(str).unique()):
        rows.append(
            {
                "classifier_id": 1,
                "classifier": "track",
                "value": track_name,
                "description": track_name,
            }
        )
    components = sorted({mapping.wood_type for mapping in track_species.values()})
    for component in components:
        rows.append(
            {
                "classifier_id": 2,
                "classifier": "species",
                "value": component,
                "description": component,
            }
        )
    return pd.DataFrame(
        rows, columns=["classifier_id", "classifier", "value", "description"]
    )


def _track_map(
    inventory: pd.DataFrame,
    track_species: Mapping[str, SpeciesMapping],
    track_shares: Mapping[str, tuple[float, float]],
    config: CarbonExportConfig,
) -> pd.DataFrame:
    """Build the track carbon map."""
    rows: list[dict[str, object]] = []
    for track_name, block in inventory.groupby("track_name", sort=True):
        first = block.iloc[0]
        mapping = track_species[str(track_name)]
        softwood, hardwood = track_shares[str(track_name)]
        component = "softwood" if softwood >= hardwood else "hardwood"
        rows.append(
            {
                "track_name": str(track_name),
                "classifier_set": f"{track_name};{component}",
                "leading_species": mapping.cbm_species,
                "softwood_share": softwood,
                "hardwood_share": hardwood,
                "landclass": config.land_class_by_ifm.get(str(first["ifm"]).lower(), 0),
                "last_disturbance": "CC"
                if str(first["ifm"]).lower() == "managed"
                else "fire",
                "eco_boundary": config.eco_boundary,
                "volume_feature_label": config.volume_feature_label,
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "track_name",
            "classifier_set",
            "leading_species",
            "softwood_share",
            "hardwood_share",
            "landclass",
            "last_disturbance",
            "eco_boundary",
            "volume_feature_label",
        ],
    )


def _disturbance_table(config: CarbonExportConfig) -> pd.DataFrame:
    """Build the disturbance-type table."""
    rows = [
        {
            "user_dist_type": mapping.treatment_pattern,
            "default_dist_type": mapping.default_dist_type,
            "removes_biomass": mapping.removes_biomass,
            "transition_reset_age": mapping.transition_reset_age,
            "regen_delay": mapping.regen_delay,
            "confidence": mapping.confidence,
            "notes": mapping.notes,
        }
        for mapping in config.disturbance_map.values()
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "user_dist_type",
            "default_dist_type",
            "removes_biomass",
            "transition_reset_age",
            "regen_delay",
            "confidence",
            "notes",
        ],
    )


def _age_classes(config: CarbonExportConfig) -> pd.DataFrame:
    """Build the age-class table."""
    rows: list[dict[str, object]] = [{"name": "age_0", "class_size": 0}]
    count = config.max_age // config.age_interval
    for index in range(1, count + 1):
        rows.append({"name": f"age_{index}", "class_size": config.age_interval})
    return pd.DataFrame(rows, columns=["name", "class_size"])


def _inventory_table(
    inventory: pd.DataFrame, config: CarbonExportConfig
) -> pd.DataFrame:
    """Build the initial inventory table."""
    rows: list[dict[str, object]] = []
    for row in inventory.itertuples(index=False):
        ifm = str(row.ifm).strip().lower()
        rows.append(
            {
                "track_name": str(row.track_name),
                "age": int(str(row.age)),
                "area_ha": float(str(row.area_ha)),
                "delay": 0,
                "landclass": config.land_class_by_ifm.get(ifm, 0),
                "historic_disturbance": DEFAULT_HISTORIC_DISTURBANCE,
                "last_pass_disturbance": "cc" if ifm == "managed" else "fire",
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "track_name",
            "age",
            "area_ha",
            "delay",
            "landclass",
            "historic_disturbance",
            "last_pass_disturbance",
        ],
    )


def _species_table(config: CarbonExportConfig) -> pd.DataFrame:
    """Build the species crosswalk table."""
    rows = [
        {
            "bc_species": mapping.bc_species,
            "common_name": mapping.common_name,
            "cbm_species": mapping.cbm_species,
            "wood_type": mapping.wood_type,
            "confidence": mapping.confidence,
            "source": mapping.source,
            "notes": mapping.notes,
        }
        for mapping in config.species_map.values()
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "bc_species",
            "common_name",
            "cbm_species",
            "wood_type",
            "confidence",
            "source",
            "notes",
        ],
    )


def _sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of a file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fingerprint(
    table_hashes: Mapping[str, str],
    source_hashes: Sequence[tuple[str, str]],
    config: CarbonExportConfig,
) -> str:
    """Return a stable package digest."""
    digest = hashlib.sha256()
    for name in sorted(table_hashes):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(table_hashes[name].encode("ascii"))
        digest.update(b"\0")
    for path, sha256 in source_hashes:
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256.encode("ascii"))
        digest.update(b"\0")
    digest.update(config.admin_boundary.encode("utf-8"))
    digest.update(b"\0")
    digest.update(config.eco_boundary.encode("utf-8"))
    digest.update(b"\0")
    digest.update(config.cbm_defaults_sha256.encode("ascii"))
    return digest.hexdigest()
