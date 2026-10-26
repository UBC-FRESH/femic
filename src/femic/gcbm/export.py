"""Export a GCBM wallto-wall project from a FEMIC checkpoint and carbon package.

The exporter emits a walltowall-compatible JSON configuration plus a vector
inventory, a wide yield table, optional disturbance vectors, and a copied AIDB.
It does not run FLINT; the external walltowall/GCBM host is documented in the
guide.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd  # type: ignore[import-untyped]
import pandas as pd
from pyarrow import feather  # type: ignore[import-untyped]

from femic.carbon.package import SCHEMA_VERSION as CARBON_SCHEMA_VERSION

GCBM_SCHEMA_VERSION = "0.1"
DEFAULT_START_YEAR = 2020
DEFAULT_HORIZON_YEARS = 10
DEFAULT_RESOLUTION = 0.001
DEFAULT_EPSG = 4326
DEFAULT_CHECKPOINT_CRS = "EPSG:3005"
DEFAULT_MEAN_ANNUAL_TEMPERATURE = 3.0
_AU_PATTERN = re.compile(r"AU\((\d+)\)")
_IFM_PATTERN = re.compile(r"IFM\(([^)]+)\)")
_AIDB_VERSION_PATTERN = re.compile(r"^cbm_defaults_v(?P<version>.+)\.db$")


class GcbmExportError(ValueError):
    """Raised when a GCBM export cannot be prepared."""


@dataclass(frozen=True)
class GcbmExportConfig:
    """Inputs and model choices for one GCBM export.

    Attributes
    ----------
    checkpoint_path : Path
        FEMIC checkpoint feather with polygon geometry.
    carbon_package_dir : Path
        FEMIC carbon package directory.
    output_dir : Path
        Destination project directory.
    aidb_path : Path or None
        CBM defaults SQLite database. Detected from libcbm when omitted.
    start_year : int
        First GCBM simulation year.
    end_year : int
        Last GCBM simulation year.
    resolution : float
        Output cell size in degrees.
    epsg : int
        Output CRS.
    checkpoint_crs : str
        CRS assigned to the checkpoint when it has none.
    mean_annual_temperature : float
        Fallback MAT when the checkpoint has no MAT column.
    initial_age_cap : int or None
        Maximum initial age; defaults to the package's maximum yield age.
    project_name : str
        walltowall project name.
    au_filter : tuple[int, ...]
        Optional AU ids to include.
    max_fragments : int or None
        Optional cap on inventory polygons for a bounded smoke export.
    disturbance_path : Path or None
        Optional vector with ``year`` and ``disturbance_type`` columns.
    gcbm_templates : Path or None
        Optional walltowall GCBM config template directory.
    gcbm_exe : Path or None
        Optional GCBM executable recorded for a later run.
    allow_aidb_mismatch : bool
        Permit an AIDB whose hash differs from the carbon package manifest.
    copy_aidb : bool
        Copy the AIDB into the project directory.
    """

    checkpoint_path: Path
    carbon_package_dir: Path
    output_dir: Path
    aidb_path: Path | None = None
    start_year: int = DEFAULT_START_YEAR
    end_year: int = DEFAULT_START_YEAR + DEFAULT_HORIZON_YEARS
    resolution: float = DEFAULT_RESOLUTION
    epsg: int = DEFAULT_EPSG
    checkpoint_crs: str = DEFAULT_CHECKPOINT_CRS
    mean_annual_temperature: float = DEFAULT_MEAN_ANNUAL_TEMPERATURE
    initial_age_cap: int | None = None
    project_name: str | None = None
    au_filter: tuple[int, ...] = ()
    max_fragments: int | None = None
    disturbance_path: Path | None = None
    gcbm_templates: Path | None = None
    gcbm_exe: Path | None = None
    allow_aidb_mismatch: bool = False
    copy_aidb: bool = True


@dataclass(frozen=True)
class GcbmExportResult:
    """Files and totals produced by a GCBM export.

    Attributes
    ----------
    project_dir : Path
        Project directory.
    config_path : Path
        walltowall JSON configuration.
    inventory_path : Path
        Exported vector inventory.
    yield_path : Path
        Wide yield table.
    disturbance_path : Path or None
        Exported disturbance vector, when supplied.
    manifest_path : Path
        Export manifest.
    aidb_path : Path
        AIDB path recorded in the configuration.
    fragments : int
        Inventory polygon count.
    tracks : int
        Yield classifier tracks.
    area_ha : float
        Exported inventory area.
    package_id : str
        Source carbon package id.
    aidb_matches_package : bool
        Whether the AIDB hash matches the package manifest.
    warnings : tuple[str, ...]
        Non-fatal export warnings.
    """

    project_dir: Path
    config_path: Path
    inventory_path: Path
    yield_path: Path
    disturbance_path: Path | None
    manifest_path: Path
    aidb_path: Path
    fragments: int
    tracks: int
    area_ha: float
    package_id: str
    aidb_matches_package: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class _SelectedTrack:
    """One package track selected for the GCBM classifier grid."""

    track_name: str
    au: int
    ifm: str
    classifier1: int
    classifier2: int
    species: str


def export_gcbm_project(config: GcbmExportConfig) -> GcbmExportResult:
    """Export a GCBM walltowall project.

    Parameters
    ----------
    config : GcbmExportConfig
        Export inputs and choices.

    Returns
    -------
    GcbmExportResult
        The written project and totals.

    Raises
    ------
    FileNotFoundError
        When an input is missing.
    GcbmExportError
        When the package, checkpoint, AIDB, or disturbance input is invalid.
    """
    if config.end_year < config.start_year:
        raise GcbmExportError("end_year must be greater than or equal to start_year")
    if config.resolution <= 0:
        raise GcbmExportError("resolution must be positive")
    package_dir = Path(config.carbon_package_dir)
    package_manifest = _load_package_manifest(package_dir)
    tracks = _select_tracks(package_dir)
    aidb, aidb_matches, aidb_warning = _resolve_aidb(
        config.aidb_path,
        package_manifest,
        allow_mismatch=config.allow_aidb_mismatch,
    )
    checkpoint = _read_checkpoint(Path(config.checkpoint_path), config)
    if config.max_fragments is not None:
        if config.max_fragments <= 0:
            raise GcbmExportError("max_fragments must be positive")
        checkpoint = checkpoint.head(config.max_fragments).copy()
    selected_tracks = _filter_tracks_for_checkpoint(
        tracks, checkpoint, config.au_filter
    )
    package_max_age = _package_max_age(package_dir)
    inventory = _inventory_frame(
        checkpoint,
        selected_tracks,
        config,
        max_age=config.initial_age_cap or package_max_age,
    )
    if inventory.empty:
        raise GcbmExportError("checkpoint selection produced no inventory polygons")

    output = Path(config.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    inventory_path = output / "inventory.gpkg"
    inventory.to_file(inventory_path, layer="inventory", driver="GPKG", index=False)
    yield_table, yield_ages = _yield_table(package_dir, selected_tracks)
    yield_path = output / "yield.csv"
    yield_table.to_csv(yield_path, index=False)

    disturbance_path = None
    disturbance_config: dict[str, dict[str, Any]] = {}
    disturbance_warning = None
    if config.disturbance_path is not None:
        disturbance_path, disturbance_config, disturbance_warning = _write_disturbances(
            Path(config.disturbance_path),
            output,
            start_year=config.start_year,
            end_year=config.end_year,
            epsg=config.epsg,
        )

    aidb_output = _place_aidb(aidb, output, copy=config.copy_aidb)
    project_name = config.project_name or _project_name(package_manifest)
    walltowall = _walltowall_config(
        project_name=project_name,
        config=config,
        aidb=aidb_output,
        yield_path=yield_path,
        disturbance_config=disturbance_config,
        disturbance_path=disturbance_path,
    )
    config_path = output / "walltowall_config.json"
    config_path.write_text(json.dumps(walltowall, indent=2), encoding="utf-8")

    warnings = [warning for warning in (aidb_warning, disturbance_warning) if warning]
    manifest = {
        "schema_version": GCBM_SCHEMA_VERSION,
        "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project_name": project_name,
        "project_dir": str(output),
        "source": {
            "checkpoint": {
                "path": str(Path(config.checkpoint_path)),
                "sha256": _sha256(Path(config.checkpoint_path)),
                "crs": str(inventory.crs),
                "fragments": int(inventory.shape[0]),
                "aus": sorted(
                    int(value) for value in inventory["Classifier1"].unique()
                ),
                "area_ha": float(inventory["area_ha"].sum()),
            },
            "carbon_package": {
                "path": str(package_dir),
                "package_id": str(package_manifest["package_id"]),
                "sha256": _sha256(package_dir / "manifest.json"),
                "yield_tracks": len(selected_tracks),
            },
            "aidb": {
                "path": str(aidb),
                "version": _aidb_version(aidb),
                "sha256": _sha256(aidb),
                "matches_carbon_package": aidb_matches,
            },
            "disturbance": (
                {
                    "path": str(config.disturbance_path),
                    "sha256": _sha256(Path(config.disturbance_path)),
                }
                if config.disturbance_path is not None
                else None
            ),
        },
        "outputs": {
            "config": {"path": config_path.name, "sha256": _sha256(config_path)},
            "inventory": {
                "path": inventory_path.name,
                "sha256": _sha256(inventory_path),
                "fragments": int(inventory.shape[0]),
            },
            "yield": {
                "path": yield_path.name,
                "sha256": _sha256(yield_path),
                "ages": list(yield_ages),
            },
            "disturbances": (
                {
                    "path": disturbance_path.name,
                    "sha256": _sha256(disturbance_path),
                }
                if disturbance_path is not None
                else None
            ),
        },
        "model": {
            "start_year": config.start_year,
            "end_year": config.end_year,
            "resolution": config.resolution,
            "epsg": config.epsg,
            "classifiers": ["Classifier1", "Classifier2"],
            "classifier_map": {
                str(track.classifier1): {"au": track.au, "ifm": track.ifm}
                for track in selected_tracks
            },
            "layers": ["initial_age", "mean_annual_temperature"],
            "yield_interval": int(yield_ages[1] - yield_ages[0]),
        },
        "warnings": warnings,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return GcbmExportResult(
        project_dir=output,
        config_path=config_path,
        inventory_path=inventory_path,
        yield_path=yield_path,
        disturbance_path=disturbance_path,
        manifest_path=manifest_path,
        aidb_path=aidb_output,
        fragments=int(inventory.shape[0]),
        tracks=len(selected_tracks),
        area_ha=float(inventory["area_ha"].sum()),
        package_id=str(package_manifest["package_id"]),
        aidb_matches_package=aidb_matches,
        warnings=tuple(warnings),
    )


def validate_gcbm_project(project_dir: Path) -> tuple[str, ...]:
    """Check a prepared export directory for walltowall structural requirements.

    Parameters
    ----------
    project_dir : Path
        Export directory.

    Returns
    -------
    tuple of str
        Human-readable issues; empty when the project structure is valid.
    """
    root = Path(project_dir)
    issues: list[str] = []
    config_path = root / "walltowall_config.json"
    if not config_path.is_file():
        return (f"missing {config_path}",)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return (f"walltowall_config.json is not valid JSON: {exc}",)
    for key in (
        "project_name",
        "start_year",
        "end_year",
        "resolution",
        "aidb",
        "yield_table",
        "classifiers",
        "layers",
    ):
        if key not in config:
            issues.append(f"missing config key {key!r}")
    for key in ("aidb", "yield_table"):
        value = config.get(key)
        if isinstance(value, str) and not (root / value).is_file():
            issues.append(f"{key} path is missing: {value}")
    yield_path = root / str(config.get("yield_table", ""))
    if yield_path.is_file():
        table = pd.read_csv(yield_path, dtype=str)
        for column in ("Classifier1", "Classifier2", "AIDBSPP"):
            if column not in table.columns:
                issues.append(f"yield table missing {column!r}")
        if not table.empty and len(table.columns) < 4:
            issues.append("yield table has no age columns")
    inventory_path = _first_layer_path(config)
    if inventory_path and not (root / inventory_path).is_file():
        issues.append(f"inventory layer is missing: {inventory_path}")
    disturbances = config.get("disturbances") or {}
    if isinstance(disturbances, dict):
        for pattern in disturbances:
            if not (root / pattern).is_file():
                issues.append(f"disturbance layer is missing: {pattern}")
    return tuple(issues)


def _load_package_manifest(package_dir: Path) -> dict[str, Any]:
    """Read and minimally check the carbon package manifest."""
    path = package_dir / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"carbon package manifest not found: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise GcbmExportError("carbon package manifest must be a JSON object")
    if manifest.get("schema_version") != CARBON_SCHEMA_VERSION:
        raise GcbmExportError(
            f"carbon package schema {manifest.get('schema_version')!r} is not "
            f"{CARBON_SCHEMA_VERSION!r}"
        )
    return manifest


def _select_tracks(package_dir: Path) -> list[_SelectedTrack]:
    """Select one baseline track per AU/IFM from the package."""
    track_map_path = package_dir / "track_carbon_map.csv"
    yield_path = package_dir / "yield.csv"
    for path in (track_map_path, yield_path):
        if not path.is_file():
            raise FileNotFoundError(f"carbon package table not found: {path}")
    track_map = pd.read_csv(track_map_path, dtype=str, keep_default_na=False)
    yield_table = pd.read_csv(yield_path, dtype=str, keep_default_na=False)
    required = {"track_name", "leading_species"}
    if not required.issubset(track_map.columns):
        raise GcbmExportError(f"{track_map_path} is missing {sorted(required)}")
    groups: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in track_map.to_dict("records"):
        name = str(row["track_name"])
        au_match = _AU_PATTERN.search(name)
        ifm_match = _IFM_PATTERN.search(name)
        if not au_match or not ifm_match:
            raise GcbmExportError(
                f"track {name!r} does not carry AU(...) and IFM(...) tokens"
            )
        au = int(au_match.group(1))
        ifm = ifm_match.group(1).strip().lower()
        score = (
            int("ORIGIN(natural)" in name)
            + int("SILV_STATE(baseline)" in name)
            + int("RETENTION(0)" in name)
        )
        groups.setdefault((au, ifm), []).append(
            {"name": name, "species": str(row["leading_species"]), "score": score}
        )
    selected: list[_SelectedTrack] = []
    for classifier1, ((au, ifm), rows) in enumerate(sorted(groups.items()), start=1):
        rows.sort(key=lambda row: (-int(row["score"]), str(row["name"])))
        best = rows[0]
        if (
            len(rows) > 1
            and rows[1]["score"] == best["score"]
            and rows[1]["species"] != best["species"]
        ):
            raise GcbmExportError(
                f"ambiguous baseline tracks for AU {au} IFM {ifm}; "
                "supply a narrower carbon package"
            )
        selected.append(
            _SelectedTrack(
                track_name=str(best["name"]),
                au=au,
                ifm=ifm,
                classifier1=classifier1,
                classifier2=1 if ifm == "managed" else 0,
                species=str(best["species"]),
            )
        )
    if not selected:
        raise GcbmExportError("carbon package has no AU/IFM tracks")
    yield_tracks = (
        set(yield_table["track_name"]) if "track_name" in yield_table else set()
    )
    missing = [
        track.track_name for track in selected if track.track_name not in yield_tracks
    ]
    if missing:
        raise GcbmExportError(f"selected tracks have no yield rows: {missing[:5]}")
    return selected


def _read_checkpoint(path: Path, config: GcbmExportConfig) -> gpd.GeoDataFrame:
    """Read the FEMIC checkpoint and return a projected GeoDataFrame."""
    if not path.is_file():
        raise FileNotFoundError(f"checkpoint not found: {path}")
    table = feather.read_table(path)
    frame = table.to_pandas()
    required = {"au", "PROJ_AGE_1", "geometry"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise GcbmExportError(f"checkpoint is missing columns: {missing}")
    if "geometry" not in frame:
        raise GcbmExportError("checkpoint has no geometry column")
    geometry = frame["geometry"]
    if len(geometry) and not isinstance(geometry.iloc[0], (bytes, bytearray)):
        gdf = gpd.GeoDataFrame(frame, geometry="geometry", crs=config.checkpoint_crs)
    else:
        gdf = gpd.GeoDataFrame(
            frame.drop(columns=["geometry"]),
            geometry=gpd.GeoSeries.from_wkb(geometry),
            crs=config.checkpoint_crs,
        )
    if config.au_filter:
        gdf = gdf.loc[gdf["au"].astype(int).isin(set(config.au_filter))]
    gdf = gdf.loc[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if gdf.empty:
        raise GcbmExportError("checkpoint selection is empty")
    if gdf.crs is None:
        gdf = gdf.set_crs(config.checkpoint_crs)
    return gdf.to_crs(epsg=config.epsg)


def _filter_tracks_for_checkpoint(
    tracks: list[_SelectedTrack],
    checkpoint: gpd.GeoDataFrame,
    au_filter: tuple[int, ...],
) -> list[_SelectedTrack]:
    """Keep tracks whose AU/IFM occurs in the checkpoint."""
    observed = {
        (int(str(row.au)), 1 if int(str(row.ifm_flag)) > 0 else 0)
        for row in _checkpoint_keys(checkpoint).itertuples(index=False)
    }
    selected = [track for track in tracks if (track.au, track.classifier2) in observed]
    if au_filter:
        selected = [track for track in selected if track.au in set(au_filter)]
    if not selected:
        raise GcbmExportError(
            "no package track matches the checkpoint AU/IFM combinations"
        )
    return selected


def _checkpoint_keys(checkpoint: gpd.GeoDataFrame) -> pd.DataFrame:
    """Return AU/IFM keys from the checkpoint."""
    frame = checkpoint.copy()
    if "IFM_FLAG" in frame.columns:
        ifm = pd.to_numeric(frame["IFM_FLAG"], errors="coerce").fillna(0) > 0
    else:
        ifm = pd.Series(False, index=frame.index)
    return pd.DataFrame(
        {
            "au": pd.to_numeric(frame["au"], errors="coerce").fillna(0).astype(int),
            "ifm_flag": ifm.astype(int),
        }
    )


def _inventory_frame(
    checkpoint: gpd.GeoDataFrame,
    tracks: list[_SelectedTrack],
    config: GcbmExportConfig,
    *,
    max_age: int,
) -> gpd.GeoDataFrame:
    """Build the walltowall inventory polygons."""
    classifier_by_key = {
        (track.au, track.classifier2): track.classifier1 for track in tracks
    }
    keys = _checkpoint_keys(checkpoint)
    mask = [
        (int(au), int(ifm)) in classifier_by_key
        for au, ifm in zip(keys["au"], keys["ifm_flag"], strict=True)
    ]
    frame = checkpoint.loc[mask].copy()
    classifier1 = [
        classifier_by_key[(int(au), int(ifm))]
        for au, ifm in zip(keys["au"], keys["ifm_flag"], strict=True)
        if (int(au), int(ifm)) in classifier_by_key
    ]
    if frame.empty:
        raise GcbmExportError("no checkpoint polygons match the selected tracks")
    age = pd.to_numeric(frame["PROJ_AGE_1"], errors="coerce").fillna(0).clip(0, max_age)
    ifm = (
        pd.to_numeric(frame["IFM_FLAG"], errors="coerce").fillna(0) > 0
        if "IFM_FLAG" in frame
        else pd.Series(False, index=frame.index)
    )
    temperature = (
        pd.to_numeric(frame["mean_annual_temperature"], errors="coerce").fillna(
            config.mean_annual_temperature
        )
        if "mean_annual_temperature" in frame
        else pd.Series(config.mean_annual_temperature, index=frame.index)
    )
    area_ha = (
        pd.to_numeric(frame["FEATURE_AREA_SQM"], errors="coerce") / 10000.0
        if "FEATURE_AREA_SQM" in frame
        else pd.Series(0.0, index=frame.index)
    )
    result = gpd.GeoDataFrame(
        {
            "Classifier1": pd.Series(classifier1, index=frame.index, dtype="int64"),
            "Classifier2": ifm.astype("int64"),
            "initial_age": age.round().astype("int64"),
            "mean_annual_temperature": temperature.astype("float64"),
            "area_ha": area_ha.astype("float64"),
        },
        geometry=frame.geometry,
        crs=frame.crs,
    )
    return result


def _package_max_age(package_dir: Path) -> int:
    """Return the maximum yield age in the package."""
    table = pd.read_csv(package_dir / "yield.csv", usecols=["age"])
    if table.empty:
        raise GcbmExportError("yield.csv has no age rows")
    return int(pd.to_numeric(table["age"], errors="raise").max())


def _yield_table(
    package_dir: Path,
    tracks: list[_SelectedTrack],
) -> tuple[pd.DataFrame, list[int]]:
    """Build the wide walltowall yield table."""
    table = pd.read_csv(package_dir / "yield.csv", dtype=str, keep_default_na=False)
    required = {"track_name", "species", "age", "volume_m3_ha"}
    missing = sorted(required.difference(table.columns))
    if missing:
        raise GcbmExportError(f"yield.csv is missing columns: {missing}")
    table["age"] = pd.to_numeric(table["age"], errors="raise").astype(int)
    table["volume_m3_ha"] = pd.to_numeric(table["volume_m3_ha"], errors="raise")
    ages = sorted(int(value) for value in table["age"].unique())
    if not ages:
        raise GcbmExportError("yield.csv has no age rows")
    intervals = {b - a for a, b in itertools.pairwise(ages)}
    if len(intervals) != 1 or min(intervals) <= 0:
        raise GcbmExportError("yield.csv does not use one positive age interval")
    rows: list[dict[str, Any]] = []
    for track in tracks:
        track_rows = table.loc[table["track_name"] == track.track_name]
        if track_rows.empty:
            raise GcbmExportError(f"track {track.track_name!r} has no yield rows")
        by_age = {
            int(row["age"]): float(row["volume_m3_ha"])
            for row in track_rows.to_dict("records")
        }
        missing_ages = [age for age in ages if age not in by_age]
        if missing_ages:
            raise GcbmExportError(
                f"track {track.track_name!r} is missing yield ages {missing_ages[:5]}"
            )
        species = set(track_rows["species"].astype(str))
        if len(species) != 1 or track.species not in species:
            raise GcbmExportError(
                f"track {track.track_name!r} yield species does not match its leading species"
            )
        row: dict[str, Any] = {
            "Classifier1": track.classifier1,
            "Classifier2": track.classifier2,
            "AIDBSPP": track.species,
        }
        row.update({str(age): by_age[age] for age in ages})
        rows.append(row)
    return pd.DataFrame(rows), ages


def _write_disturbances(
    path: Path,
    output: Path,
    *,
    start_year: int,
    end_year: int,
    epsg: int,
) -> tuple[Path, dict[str, dict[str, Any]], str | None]:
    """Write a disturbance vector and its walltowall config entry."""
    if not path.is_file():
        raise FileNotFoundError(f"disturbance vector not found: {path}")
    frame = gpd.read_file(path)
    required = {"year", "disturbance_type", "geometry"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise GcbmExportError(f"disturbance vector is missing columns: {missing}")
    if frame.crs is None:
        raise GcbmExportError("disturbance vector has no CRS")
    frame = frame.to_crs(epsg=epsg)
    years = pd.to_numeric(frame["year"], errors="raise").astype(int)
    frame["year"] = years
    frame["disturbance_type"] = frame["disturbance_type"].astype(str)
    before = len(frame)
    frame = frame.loc[(frame["year"] >= start_year) & (frame["year"] <= end_year)]
    warning = None
    if len(frame) != before:
        warning = f"{before - len(frame)} disturbance features were outside the simulation window"
    if frame.empty:
        return output / "disturbances.gpkg", {}, warning
    destination = output / "disturbances.gpkg"
    frame.to_file(destination, layer="disturbances", driver="GPKG", index=False)
    return (
        destination,
        {
            "disturbances.gpkg": {
                "year": "year",
                "disturbance_type": "disturbance_type",
                "age_after": 0,
                "regen_delay": 0,
            }
        },
        warning,
    )


def _resolve_aidb(
    aidb_path: Path | None,
    package_manifest: dict[str, Any],
    *,
    allow_mismatch: bool,
) -> tuple[Path, bool, str | None]:
    """Resolve and verify the AIDB."""
    path = Path(aidb_path) if aidb_path is not None else _detect_aidb()
    if path is None:
        raise GcbmExportError(
            "no AIDB found; pass --aidb or install libcbm in the active environment"
        )
    if not path.is_file():
        raise FileNotFoundError(f"AIDB not found: {path}")
    if path.suffix.lower() == ".mdb":
        raise GcbmExportError(
            "Access AIDB files are not supported by this Linux export lane; use the SQLite AIDB"
        )
    digest = _sha256(path)
    expected = str((package_manifest.get("cbm_defaults") or {}).get("sha256", ""))
    matches = bool(expected) and digest == expected
    warning = None
    if not matches:
        warning = (
            "AIDB hash does not match the carbon package; "
            f"package={expected or 'missing'} export={digest}"
        )
        if not allow_mismatch:
            raise GcbmExportError(warning + " (pass --allow-aidb-mismatch to proceed)")
    return path, matches, warning


def _detect_aidb() -> Path | None:
    """Detect the SQLite AIDB bundled with libcbm."""
    try:
        from libcbm import resources  # type: ignore[import-not-found]
    except ImportError:
        return None
    return Path(resources.get_cbm_defaults_path())


def _place_aidb(aidb: Path, output: Path, *, copy: bool) -> Path:
    """Copy or reference the AIDB and return the path recorded in the config."""
    if not copy:
        return aidb.resolve()
    destination = output / "input_database" / aidb.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(aidb, destination)
    return destination


def _walltowall_config(
    *,
    project_name: str,
    config: GcbmExportConfig,
    aidb: Path,
    yield_path: Path,
    disturbance_config: dict[str, dict[str, Any]],
    disturbance_path: Path | None,
) -> dict[str, Any]:
    """Build the walltowall JSON configuration."""
    inventory = "inventory.gpkg"
    result: dict[str, Any] = {
        "project_name": project_name,
        "start_year": config.start_year,
        "end_year": config.end_year,
        "resolution": config.resolution,
        "epsg": config.epsg,
        "aidb": _relative_or_absolute(aidb, config.output_dir),
        "yield_table": yield_path.name,
        "yield_interval": _yield_interval(yield_path),
        "classifiers": {
            "Classifier1": {"layer": inventory, "attribute": "Classifier1"},
            "Classifier2": {"layer": inventory, "attribute": "Classifier2"},
        },
        "layers": {
            "initial_age": {"layer": inventory, "attribute": "initial_age"},
            "mean_annual_temperature": {
                "layer": inventory,
                "attribute": "mean_annual_temperature",
            },
        },
        "disturbances": disturbance_config,
    }
    if disturbance_path is not None and disturbance_config:
        for details in result["disturbances"].values():
            details["age_after"] = 0
            details["regen_delay"] = 0
    if config.gcbm_templates is not None:
        result["gcbm_config_templates"] = str(Path(config.gcbm_templates).resolve())
    if config.gcbm_exe is not None:
        result["gcbm_exe"] = str(Path(config.gcbm_exe).resolve())
    return result


def _yield_interval(path: Path) -> int:
    """Return the yield age interval from a wide yield table."""
    table = pd.read_csv(path, nrows=1)
    ages = [int(column) for column in table.columns if str(column).isdigit()]
    if len(ages) < 2:
        raise GcbmExportError("yield table has fewer than two age columns")
    return ages[1] - ages[0]


def _relative_or_absolute(path: Path, output: Path) -> str:
    """Return a project-relative path when possible."""
    try:
        return str(Path(path).resolve().relative_to(Path(output).resolve()))
    except ValueError:
        return str(Path(path).resolve())


def _first_layer_path(config: dict[str, Any]) -> str | None:
    """Return the first inventory/layer path in the walltowall config."""
    layers = config.get("layers")
    if not isinstance(layers, dict):
        return None
    for details in layers.values():
        if isinstance(details, str):
            return details
        if isinstance(details, dict) and isinstance(details.get("layer"), str):
            return str(details["layer"])
    return None


def _project_name(package_manifest: dict[str, Any]) -> str:
    """Derive a stable project name from the package id."""
    value = str(package_manifest.get("package_id", "femic-gcbm"))
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _aidb_version(path: Path) -> str:
    """Read the AIDB version from its filename or return unknown."""
    match = _AIDB_VERSION_PATTERN.match(path.name)
    return match.group("version") if match else "unknown"


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
