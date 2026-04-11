"""Helpers for legacy site productivity raster export/stack orchestration."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from femic.arcgis_pro import run_arcgis_python
from femic.pipeline.io import resolve_windows_annex_pointer_payload_path


def _list_siteprod_layers_arcgis(
    *, siteprod_gdb_path: str | Path
) -> tuple[dict[int, str], dict[str, int]]:
    code = (
        "import arcpy, json, sys; "
        "arcpy.env.workspace=sys.argv[1]; "
        "rasters=arcpy.ListRasters() or []; "
        "print(json.dumps(rasters))"
    )
    result = run_arcgis_python(code=code, args=[str(siteprod_gdb_path)])
    rasters = json.loads(result.stdout.strip() or "[]")
    layer_species = {
        idx: str(name).removeprefix("Site_Prod_").upper()
        for idx, name in enumerate(rasters)
    }
    species_layer = {species: idx for idx, species in layer_species.items()}
    return layer_species, species_layer


def _export_siteprod_layer_arcgis(
    *,
    site_prod_bc_gdb_path: str | Path,
    species: str,
    destination: str | Path,
) -> None:
    code = (
        "import arcpy, sys; "
        "arcpy.env.workspace=sys.argv[1]; "
        "arcpy.env.overwriteOutput=True; "
        "raster='Site_Prod_' + sys.argv[2].title(); "
        "arcpy.management.CopyRaster(raster, sys.argv[3])"
    )
    run_arcgis_python(
        code=code,
        args=[str(site_prod_bc_gdb_path), str(species), str(destination)],
    )


def _export_siteprod_layers_arcgis_batch(
    *,
    site_prod_bc_gdb_path: str | Path,
    destinations: Mapping[str, str | Path],
) -> None:
    payload = json.dumps(
        {str(species): str(path) for species, path in destinations.items()}
    )
    code = (
        "import arcpy, json, sys; "
        "arcpy.env.workspace=sys.argv[1]; "
        "arcpy.env.overwriteOutput=True; "
        "mapping=json.loads(sys.argv[2]); "
        "[arcpy.management.CopyRaster('Site_Prod_' + species.title(), dest) for species, dest in mapping.items()]"
    )
    run_arcgis_python(
        code=code,
        args=[str(site_prod_bc_gdb_path), payload],
    )


DEFAULT_SITEPROD_SPECIES_LOOKUP: dict[str, str] = {
    "AC": "AT",
    "PLI": "PL",
    "FDI": "FD",
    "S": "SW",
    "SXL": "SX",
    "ACT": "AT",
    "E": "EP",
    "P": "PL",
    "EA": "EP",
    "SXW": "SX",
    "W": "EP",
    "T": "LT",
    "L": "LT",
    "B": "BL",
    "ACB": "AT",
    "PJ": "PL",
    "WS": "EP",
    "LA": "LT",
    "AX": "AT",
    "BB": "BL",
    "H": "HW",
    "BM": "BL",
    "V": "DR",
    "F": "FD",
    "C": "CW",
    "XC": "PL",
    "XD": "SW",
    "X": "SW",
    "A": "AT",
    "D": "DR",
    "Z": "SW",
    "Q": "AT",
    "Y": "YC",
    "R": "DR",
    "G": "DR",
}


def siteprod_species_lookup(
    species_code: str,
    *,
    mapping: Mapping[str, str] = DEFAULT_SITEPROD_SPECIES_LOOKUP,
) -> str:
    """Map VRI species code to siteprod layer code with first-letter fallback."""
    code = str(species_code)
    if code in mapping:
        return mapping[code]
    first = code[:1]
    if first in mapping:
        return mapping[first]
    raise ValueError(f"bad species code: {species_code!r}")


def mean_siteprod_for_row(
    *,
    row: Any,
    raster_src: Any,
    mask_fn: Callable[..., Any],
    np_module: Any,
    siteprod_specieslayer: Mapping[str, int],
    species_lookup_fn: Callable[[str], str] = siteprod_species_lookup,
) -> float:
    """Compute mean positive siteprod value for one stand record."""
    values, _ = mask_fn(raster_src, [row.geometry], crop=True)
    species = row.SPECIES_CD_1
    species = (
        species if species in siteprod_specieslayer else species_lookup_fn(str(species))
    )
    band_index = siteprod_specieslayer[species]
    band_values = values[band_index]
    positive_values = band_values[band_values > 0]
    if positive_values.size == 0:
        return float("nan")
    return float(np_module.mean(positive_values))


def assign_siteprod_from_raster(
    *,
    f_table: Any,
    siteprod_tif_path: str | Path,
    siteprod_specieslayer: Mapping[str, int],
    rio_module: Any,
    mask_fn: Callable[..., Any],
    np_module: Any,
    row_apply_fn: Callable[..., Any],
    species_lookup_fn: Callable[[str], str] = siteprod_species_lookup,
    out_col: str = "siteprod",
) -> Any:
    """Assign siteprod column by masking the stacked siteprod raster per stand row."""
    table = f_table.copy()
    readable_path = resolve_windows_annex_pointer_payload_path(Path(siteprod_tif_path))
    with rio_module.open(readable_path) as src:

        def _mean(row: Any) -> float:
            return mean_siteprod_for_row(
                row=row,
                raster_src=src,
                mask_fn=mask_fn,
                np_module=np_module,
                siteprod_specieslayer=siteprod_specieslayer,
                species_lookup_fn=species_lookup_fn,
            )

        table[out_col] = row_apply_fn(table, _mean, axis=1)
    return table


def load_siteprod_bandmap(
    *,
    bandmap_path: str | Path,
) -> tuple[dict[int, str], dict[str, int]]:
    """Load canonical SiteProd species<->band mappings from JSON sidecar."""
    payload = json.loads(Path(bandmap_path).read_text(encoding="utf-8"))
    bands_0_based = payload.get("bands_0_based")
    bands_1_based = payload.get("bands_1_based")
    ordered_species = payload.get("ordered_species")
    if isinstance(bands_0_based, dict) and bands_0_based:
        species_layer = {
            str(species).upper(): int(index) for species, index in bands_0_based.items()
        }
        layer_species = {
            int(index): str(species).upper() for species, index in species_layer.items()
        }
        return layer_species, species_layer
    if isinstance(bands_1_based, dict) and bands_1_based:
        species_layer = {
            str(species).upper(): int(index) - 1
            for species, index in bands_1_based.items()
        }
        layer_species = {
            int(index): str(species).upper() for species, index in species_layer.items()
        }
        return layer_species, species_layer
    if isinstance(ordered_species, list) and ordered_species:
        layer_species = {
            idx: str(species).upper() for idx, species in enumerate(ordered_species)
        }
        species_layer = {species: idx for idx, species in layer_species.items()}
        return layer_species, species_layer
    raise ValueError(f"Invalid SiteProd band map payload: {bandmap_path}")


def parse_arc_raster_rescue_layer_mappings(
    *,
    stdout_text: str,
) -> tuple[dict[int, str], dict[str, int]]:
    """Parse ArcRasterRescue layer listing into index<->species mappings."""
    lines = [line.strip() for line in stdout_text.splitlines()[1:] if line.strip()]
    layer_species = {
        int(layer_index): layer_name[10:].upper()
        for layer_index, layer_name in (line.split(" ", 1) for line in lines)
    }
    species_layer = {species: layer for layer, species in layer_species.items()}
    return layer_species, species_layer


def resolve_arc_raster_rescue_executable_path(
    *,
    configured_path: str | Path,
    source_root_env: str | None = None,
    instance_root_env: str | None = None,
    env_override: str | None = None,
) -> Path:
    """Resolve ArcRasterRescue executable using override + source-root fallbacks."""
    configured = Path(configured_path).expanduser()
    candidates: list[Path] = []
    if env_override:
        candidates.append(Path(env_override).expanduser())
    candidates.append(configured)
    if not configured.is_absolute():
        for base in [instance_root_env, source_root_env]:
            if base:
                candidates.append((Path(base).expanduser() / configured).resolve())
    seen: set[Path] = set()
    for candidate in candidates:
        normalized = candidate.resolve()
        if normalized in seen:
            continue
        seen.add(normalized)
        if normalized.exists():
            return normalized
    return candidates[0].resolve()


def _arc_raster_rescue_gdb_arg(siteprod_gdb_path: str | Path) -> str:
    """Normalize FileGDB path syntax expected by ArcRasterRescue."""
    text = str(siteprod_gdb_path)
    if text.endswith(".gdb") and not text.endswith(".gdb/"):
        return f"{text}/"
    return text


def list_siteprod_layers(
    *,
    arc_raster_rescue_exe_path: str | Path,
    siteprod_gdb_path: str | Path,
    run_fn: Callable[..., Any],
) -> tuple[dict[int, str], dict[str, int]]:
    """Run ArcRasterRescue layer listing and return parsed species mappings."""
    arc_path = resolve_arc_raster_rescue_executable_path(
        configured_path=arc_raster_rescue_exe_path,
        source_root_env=os.environ.get("FEMIC_SOURCE_ROOT"),
        instance_root_env=os.environ.get("FEMIC_INSTANCE_ROOT"),
        env_override=os.environ.get("FEMIC_ARC_RASTER_RESCUE_EXE"),
    )
    if arc_path.exists():
        gdb_arg = _arc_raster_rescue_gdb_arg(siteprod_gdb_path)
        result = run_fn(
            [str(arc_path), gdb_arg],
            capture_output=True,
        )
        return parse_arc_raster_rescue_layer_mappings(
            stdout_text=result.stdout.decode(),
        )
    if os.name == "nt":
        return _list_siteprod_layers_arcgis(siteprod_gdb_path=siteprod_gdb_path)
    raise FileNotFoundError(f"ArcRasterRescue executable not found: {arc_path}")


def build_siteprod_layer_tif_path(
    *,
    siteprod_tmpexport_tif_path_prefix: str | Path,
    species: str,
) -> Path:
    """Build temporary GeoTIFF path for one species export."""
    prefix = Path(siteprod_tmpexport_tif_path_prefix)
    return prefix.parent / f"{prefix.name}{species}.tif"


def enumerate_siteprod_layer_tif_paths(
    *,
    siteprod_tmpexport_tif_path_prefix: str | Path,
) -> list[Path]:
    """Enumerate exported temporary siteprod layer GeoTIFF paths."""
    prefix = Path(siteprod_tmpexport_tif_path_prefix)
    return sorted(prefix.parent.glob(f"{prefix.name}*.tif"))


def _normalize_arc_raster_rescue_stream_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _resolve_arc_raster_rescue_timeout_seconds() -> float:
    raw_value = os.environ.get("FEMIC_ARC_RASTER_RESCUE_TIMEOUT_SEC", "900")
    try:
        value = float(raw_value)
    except ValueError:
        return 900.0
    if value <= 0:
        return 900.0
    return value


def export_and_stack_siteprod_layers(
    *,
    arc_raster_rescue_exe_path: str | Path,
    site_prod_bc_gdb_path: str | Path,
    site_prod_bc_layerspecies: Mapping[int, str],
    siteprod_layerspecies: Mapping[int, str],
    siteprod_tmpexport_tif_path_prefix: str | Path,
    siteprod_tif_path: str | Path,
    run_fn: Callable[..., Any],
    rio_module: Any,
    message_fn: Callable[..., Any] = print,
) -> None:
    """Export per-species rasters, stack into one GeoTIFF, and clean temps."""
    arc_path = resolve_arc_raster_rescue_executable_path(
        configured_path=arc_raster_rescue_exe_path,
        source_root_env=os.environ.get("FEMIC_SOURCE_ROOT"),
        instance_root_env=os.environ.get("FEMIC_INSTANCE_ROOT"),
        env_override=os.environ.get("FEMIC_ARC_RASTER_RESCUE_EXE"),
    )
    timeout_seconds = _resolve_arc_raster_rescue_timeout_seconds()
    destinations: dict[str, Path] = {}
    for layer_index, species in site_prod_bc_layerspecies.items():
        message_fn("... processing species", species)
        destination = build_siteprod_layer_tif_path(
            siteprod_tmpexport_tif_path_prefix=siteprod_tmpexport_tif_path_prefix,
            species=species,
        )
        for existing in destination.parent.glob(f"{destination.name}*"):
            existing.unlink(missing_ok=True)
        destinations[species] = destination
        if arc_path.exists():
            gdb_arg = _arc_raster_rescue_gdb_arg(site_prod_bc_gdb_path)
            command = [
                str(arc_path),
                gdb_arg,
                str(layer_index),
                destination,
            ]
            message_fn(
                "... ArcRasterRescue launch",
                species,
                f"layer={layer_index}",
                f"timeout={timeout_seconds:.1f}s",
            )
            started = time.perf_counter()
            try:
                try:
                    result = run_fn(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds,
                        check=False,
                    )
                except TypeError:
                    result = run_fn(command, capture_output=True)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    "ArcRasterRescue timed out for species "
                    f"{species} (layer={layer_index}, timeout_sec={timeout_seconds}): {command}"
                ) from exc

            returncode = getattr(result, "returncode", 0)
            stderr_text = _normalize_arc_raster_rescue_stream_text(
                getattr(result, "stderr", "")
            )
            if returncode not in (0, None):
                raise RuntimeError(
                    "ArcRasterRescue failed for species "
                    f"{species} (layer={layer_index}, returncode={returncode}): "
                    f"{stderr_text[:500]}"
                )
            elapsed = time.perf_counter() - started
            message_fn(
                "... ArcRasterRescue completed",
                species,
                f"layer={layer_index}",
                f"sec={elapsed:.2f}",
            )
        elif os.name != "nt":
            raise FileNotFoundError(f"ArcRasterRescue executable not found: {arc_path}")

    if (not arc_path.exists()) and os.name == "nt":
        _export_siteprod_layers_arcgis_batch(
            site_prod_bc_gdb_path=site_prod_bc_gdb_path,
            destinations=destinations,
        )

    file_list = enumerate_siteprod_layer_tif_paths(
        siteprod_tmpexport_tif_path_prefix=siteprod_tmpexport_tif_path_prefix
    )
    with rio_module.open(file_list[0]) as src:
        meta = src.meta
        meta.update(
            count=len(file_list),
            compress="lzw",
            crs=rio_module.crs.CRS({"init": "epsg:3005"}),
        )

    with rio_module.open(siteprod_tif_path, "w", **meta) as dst:
        message_fn(
            "\nStacking siteprod raster data into a single multiband GeoTIFF file..."
        )
        for idx, layer in enumerate(file_list, start=1):
            message_fn("... processing species", siteprod_layerspecies[idx - 1])
            with rio_module.open(layer) as src:
                dst.write_band(idx, src.read(1))
            layer.unlink()
