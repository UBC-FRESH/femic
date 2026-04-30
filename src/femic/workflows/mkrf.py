"""MKRF-specific rebuild workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd

from femic.pipeline.mkrf_au import build_mkrf_au_tables


@dataclass(frozen=True)
class MkrfAuBuildResult:
    """Result payload for MKRF AU-input bundle materialization."""

    resultant_gdb: Path
    output_dir: Path
    au_table_path: Path
    stand_assignment_path: Path
    source_row_count: int
    au_count: int


def build_mkrf_au_input_bundle(
    *,
    resultant_gdb: Path,
    output_dir: Path,
    layer: str = "Resultant",
) -> MkrfAuBuildResult:
    """Materialize MKRF AU and stand-assignment inputs from Resultant.gdb."""
    output_dir.mkdir(parents=True, exist_ok=True)
    source_table = gpd.read_file(resultant_gdb, layer=layer, ignore_geometry=True)
    au_table, assignment = build_mkrf_au_tables(source_table)

    au_table_path = output_dir / "au_table.csv"
    stand_assignment_path = output_dir / "stand_au_assignment.csv"
    au_table.to_csv(au_table_path, index=False)
    assignment.to_csv(stand_assignment_path, index=False)

    return MkrfAuBuildResult(
        resultant_gdb=resultant_gdb,
        output_dir=output_dir,
        au_table_path=au_table_path,
        stand_assignment_path=stand_assignment_path,
        source_row_count=len(assignment),
        au_count=len(au_table),
    )
