"""Helpers for legacy site productivity raster export/stack orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping


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
    with rio_module.open(siteprod_tif_path) as src:

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


def list_siteprod_layers(
    *,
    arc_raster_rescue_exe_path: str | Path,
    siteprod_gdb_path: str | Path,
    run_fn: Callable[..., Any],
) -> tuple[dict[int, str], dict[str, int]]:
    """Run ArcRasterRescue layer listing and return parsed species mappings."""
    result = run_fn(
        [arc_raster_rescue_exe_path, siteprod_gdb_path],
        capture_output=True,
    )
    return parse_arc_raster_rescue_layer_mappings(
        stdout_text=result.stdout.decode(),
    )


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
    for layer_index, species in site_prod_bc_layerspecies.items():
        message_fn("... processing species", species)
        run_fn(
            [
                arc_raster_rescue_exe_path,
                site_prod_bc_gdb_path,
                str(layer_index),
                build_siteprod_layer_tif_path(
                    siteprod_tmpexport_tif_path_prefix=siteprod_tmpexport_tif_path_prefix,
                    species=species,
                ),
            ]
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
