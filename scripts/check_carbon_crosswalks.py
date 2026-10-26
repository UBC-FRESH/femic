#!/usr/bin/env python3
"""Check FEMIC carbon crosswalks against a CBM defaults SQLite database.

This is a mechanical existence check, not the CBM/CFS science review. It verifies
that every mapped species, boundary, disturbance type, and land class exists in
the pinned AIDB and writes a review-ready JSON packet.

Usage::

    python scripts/check_carbon_crosswalks.py \
        --aidb path/to/cbm_defaults_v1.2.9300.391.db \
        --config-dir config/carbon \
        --out notes/reports/p1151-crosswalk-review.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


def _names(connection: sqlite3.Connection, table: str, column: str) -> set[str]:
    """Return the distinct names in one translation table."""
    table_name = table.replace('"', "")
    column_name = column.replace('"', "")
    rows = connection.execute(f'SELECT "{column_name}" FROM "{table_name}"')
    return {str(row[0]) for row in rows if row[0] is not None}


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aidb", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=Path("config/carbon"))
    parser.add_argument(
        "--vri-codes",
        type=Path,
        default=None,
        help="VRI species-code table; defaults to <config-dir>/vri_species_codes.csv.",
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """Run the existence checks and write the JSON packet."""
    args = _parse_args()
    if not args.aidb.is_file():
        raise FileNotFoundError(args.aidb)
    connection = sqlite3.connect(f"file:{args.aidb}?mode=ro", uri=True)
    try:
        species = _names(connection, "species_tr", "name")
        admin = _names(connection, "admin_boundary_tr", "name")
        eco = _names(connection, "eco_boundary_tr", "name")
        disturbance = _names(connection, "disturbance_type_tr", "name")
        land = {
            int(row[0]): str(row[1])
            for row in connection.execute(
                "SELECT land_class_id, description FROM land_class_tr"
            )
        }
        species_map = pd.read_csv(
            args.config_dir / "species_map.bc.csv", dtype=str, keep_default_na=False
        )
        vri_path = args.vri_codes or (args.config_dir / "vri_species_codes.csv")
        vri_codes: set[str] = set()
        vri_missing: list[dict[str, str]] = []
        if vri_path.is_file():
            vri_table = pd.read_csv(vri_path, dtype=str)
            vri_codes = set(vri_table["vri_code"])
            for row in species_map.itertuples(index=False):
                vri_code = str(getattr(row, "vri_code", "")).strip()
                if vri_code and vri_code not in vri_codes:
                    vri_missing.append(
                        {
                            "bc_species": str(row.bc_species),
                            "vri_code": vri_code,
                        }
                    )
        eco_map = pd.read_csv(args.config_dir / "eco_boundary.bc.csv", dtype=str)
        disturbance_map = pd.read_csv(
            args.config_dir / "disturbance_map.bc.csv", dtype=str
        )
        land_map = pd.read_csv(args.config_dir / "land_class.bc.csv", dtype=str)
        species_missing = [
            {"bc_species": row.bc_species, "cbm_species": row.cbm_species}
            for row in species_map.itertuples(index=False)
            if row.cbm_species not in species
        ]
        boundary_missing = []
        for row in eco_map.itertuples(index=False):
            if row.admin_boundary not in admin:
                boundary_missing.append(
                    {
                        "tsa_code": row.tsa_code,
                        "kind": "admin",
                        "value": row.admin_boundary,
                    }
                )
            if row.eco_boundary not in eco:
                boundary_missing.append(
                    {"tsa_code": row.tsa_code, "kind": "eco", "value": row.eco_boundary}
                )
        disturbance_missing = [
            {
                "treatment_pattern": row.treatment_pattern,
                "default_dist_type": row.default_dist_type,
            }
            for row in disturbance_map.itertuples(index=False)
            if row.default_dist_type not in disturbance
        ]
        land_missing = [
            {"ifm": row.ifm, "landclass": int(str(row.landclass))}
            for row in land_map.itertuples(index=False)
            if int(str(row.landclass)) not in land
        ]
        disturbance_details = []
        for row in disturbance_map.itertuples(index=False):
            detail = connection.execute(
                "SELECT disturbance_type_id, description FROM disturbance_type_tr "
                "WHERE name = ?",
                (row.default_dist_type,),
            ).fetchone()
            disturbance_details.append(
                {
                    "treatment_pattern": row.treatment_pattern,
                    "default_dist_type": row.default_dist_type,
                    "cbm_id": detail[0] if detail else None,
                    "cbm_description": detail[1] if detail else None,
                    "removes_biomass": row.removes_biomass,
                    "confidence": row.confidence,
                    "notes": row.notes,
                }
            )
        land_details = [
            {
                "ifm": row.ifm,
                "landclass": int(str(row.landclass)),
                "cbm_description": land.get(int(str(row.landclass))),
                "confidence": row.confidence,
                "notes": row.notes,
            }
            for row in land_map.itertuples(index=False)
        ]
        packet: dict[str, Any] = {
            "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "aidb": str(args.aidb),
            "aidb_sha256": _sha256(args.aidb),
            "config_dir": str(args.config_dir),
            "counts": {
                "species_rows": len(species_map),
                "tsa_rows": len(eco_map),
                "disturbance_rows": len(disturbance_map),
                "land_class_rows": len(land_map),
            },
            "vri_codes_path": str(vri_path),
            "missing": {
                "species": species_missing,
                "vri_codes": vri_missing,
                "boundaries": boundary_missing,
                "disturbances": disturbance_missing,
                "land_classes": land_missing,
            },
            "disturbances": disturbance_details,
            "land_classes": land_details,
            "ok": not any(
                (
                    species_missing,
                    vri_missing,
                    boundary_missing,
                    disturbance_missing,
                    land_missing,
                )
            ),
            "note": (
                "Mechanical existence check only; CBM/CFS science review, species "
                "resolution, boundary provenance, removal fractions, and transition "
                "semantics remain reviewer decisions."
            ),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    finally:
        connection.close()
    print(
        f"crosswalk existence check: ok={packet['ok']} "
        f"species={packet['counts']['species_rows']} "
        f"vri={len(vri_codes)} "
        f"tsa={packet['counts']['tsa_rows']} "
        f"disturbance={packet['counts']['disturbance_rows']}"
    )
    if not packet["ok"]:
        print(json.dumps(packet["missing"], indent=2))
    print(f"packet: {args.out}")
    return 0 if packet["ok"] else 1


def _sha256(path: Path) -> str:
    """Return a file SHA-256 digest."""
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
