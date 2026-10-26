#!/usr/bin/env python3
"""Run the WS3 SIT + libcbm reference trajectory for a Woodstock model.

This script is intentionally outside FEMIC's runtime dependencies. Run it in an
environment with ``ws3`` and ``libcbm`` installed, for example the WS3 lane venv.

Usage::

    python scripts/ws3_carbon_reference.py \
        --ws3-repo /path/to/ws3 \
        --model-dir /path/to/examples/data/woodstock_model_files_tsa24_clipped \
        --out notes/reports/ws3-tsa24-clipped \
        --n-steps 20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

BIOMASS_POOLS = (
    "SoftwoodMerch",
    "SoftwoodFoliage",
    "SoftwoodOther",
    "SoftwoodCoarseRoots",
    "SoftwoodFineRoots",
    "HardwoodMerch",
    "HardwoodFoliage",
    "HardwoodOther",
    "HardwoodCoarseRoots",
    "HardwoodFineRoots",
)
DOM_POOLS = (
    "AboveGroundVeryFastSoil",
    "BelowGroundVeryFastSoil",
    "AboveGroundFastSoil",
    "BelowGroundFastSoil",
    "MediumSoil",
    "AboveGroundSlowSoil",
    "BelowGroundSlowSoil",
    "SoftwoodStemSnag",
    "SoftwoodBranchSnag",
    "HardwoodStemSnag",
    "HardwoodBranchSnag",
)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ws3-repo", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-name", default="tsa24_clipped")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n-steps", type=int, default=20)
    parser.add_argument("--base-year", type=int, default=2020)
    parser.add_argument("--horizon", type=int, default=10)
    parser.add_argument("--period-length", type=int, default=10)
    parser.add_argument("--max-age", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    """Run the reference and write the handoff tables."""
    args = _parse_args()
    sys.path.insert(0, str(args.ws3_repo))
    from libcbm.input.sit import sit_cbm_factory, sit_reader  # type: ignore[import-not-found]
    from libcbm.model.cbm import cbm_simulator  # type: ignore[import-not-found]
    from libcbm.model.cbm.cbm_output import CBMOutput  # type: ignore[import-not-found]
    from ws3.forest import ForestModel  # type: ignore[import-not-found]

    fm = ForestModel(
        model_name=args.model_name,
        model_path=str(args.model_dir),
        base_year=args.base_year,
        horizon=args.horizon,
        period_length=args.period_length,
        max_age=args.max_age,
    )
    fm.import_landscape_section()
    fm.import_areas_section(convert_periods_to_years=args.period_length)
    fm.import_yields_section(convert_periods_to_years=args.period_length)
    fm.import_actions_section(convert_periods_to_years=args.period_length)
    fm.import_transitions_section(convert_periods_to_years=args.period_length)
    fm.initialize_areas()
    fm.add_null_action()
    fm.reset_actions()
    for key in fm.dtypes:
        fm.dt(key).last_pass_disturbance = "fire" if key[2] == key[4] else "harvest"
    mapping = [
        {
            "user_dist_type": "harvest",
            "default_dist_type": "Clearcut harvesting without salvage",
        },
        {"user_dist_type": "fire", "default_dist_type": "Wildfire"},
    ]
    config, tables = fm.to_cbm_sit(
        softwood_volume_yname="swdvol",
        hardwood_volume_yname="hwdvol",
        admin_boundary="British Columbia",
        eco_boundary="Montane Cordillera",
        disturbance_type_mapping=mapping,
    )
    sit_data = sit_reader.parse(
        sit_classifiers=tables["sit_classifiers"],
        sit_disturbance_types=tables["sit_disturbance_types"],
        sit_age_classes=tables["sit_age_classes"],
        sit_inventory=tables["sit_inventory"],
        sit_yield=tables["sit_yield"],
        sit_events=tables["sit_events"],
        sit_transitions=tables["sit_transitions"],
        sit_eligibilities=None,
    )
    sit = sit_cbm_factory.initialize_sit(sit_data=sit_data, config=config)
    classifiers, inventory = sit_cbm_factory.initialize_inventory(sit)
    output = CBMOutput(
        classifier_map=sit.classifier_value_names,
        disturbance_type_map=sit.disturbance_name_map,
    )
    with sit_cbm_factory.initialize_cbm(sit) as cbm:
        processor = sit_cbm_factory.create_sit_rule_based_processor(sit, cbm)
        cbm_simulator.simulate(
            cbm,
            n_steps=args.n_steps,
            classifiers=classifiers,
            inventory=inventory,
            pre_dynamics_func=processor.pre_dynamics_func,
            reporting_func=output.append_simulation_result,
        )
    pools = output.pools.to_pandas()
    available = set(pools.columns)
    biomass = [name for name in BIOMASS_POOLS if name in available]
    dom = [name for name in DOM_POOLS if name in available]
    accounts = []
    for timestep, frame in pools.groupby("timestep", sort=True):
        values = {
            "carbon.biomass.total": float(frame[biomass].sum().sum()),
            "carbon.dom.total": float(frame[dom].sum().sum()),
            "carbon.ecosystem.total": float(frame[biomass + dom].sum().sum()),
            "carbon.products.total": (
                float(frame["Products"].sum()) if "Products" in frame else 0.0
            ),
        }
        for account, value in values.items():
            accounts.append(
                {"offset": int(timestep), "account": account, "value": value}
            )
    accounts_frame = pd.DataFrame(accounts)
    ecosystem = accounts_frame.loc[
        accounts_frame["account"] == "carbon.ecosystem.total", "value"
    ]
    changes = ecosystem.diff().fillna(0.0)
    accounts_frame = pd.concat(
        [
            accounts_frame,
            pd.DataFrame(
                {
                    "offset": accounts_frame.loc[
                        accounts_frame["account"] == "carbon.ecosystem.total", "offset"
                    ].to_numpy(),
                    "account": "carbon.stock.change",
                    "value": changes.to_numpy(),
                }
            ),
        ],
        ignore_index=True,
    )
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    accounts_path = output_dir / "ws3_carbon_accounts.csv"
    pools_path = output_dir / "ws3_carbon_pools.csv"
    manifest_path = output_dir / "ws3_carbon_manifest.json"
    accounts_frame.to_csv(accounts_path, index=False)
    long = pools.melt(
        id_vars=["timestep", "identifier"],
        value_vars=[*biomass, *dom, "Products"]
        if "Products" in pools.columns
        else [*biomass, *dom],
        var_name="pool",
        value_name="value",
    )
    long.to_csv(pools_path, index=False)
    initial = accounts_frame.loc[
        (accounts_frame["offset"] == 0)
        & (accounts_frame["account"] == "carbon.ecosystem.total"),
        "value",
    ].iloc[0]
    final_offset = int(accounts_frame["offset"].max())
    final = accounts_frame.loc[
        (accounts_frame["offset"] == final_offset)
        & (accounts_frame["account"] == "carbon.ecosystem.total"),
        "value",
    ].iloc[0]
    manifest = {
        "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model_name": args.model_name,
        "model_path": str(args.model_dir),
        "base_year": args.base_year,
        "n_steps": args.n_steps,
        "period_length": args.period_length,
        "inventory_rows": len(tables["sit_inventory"]),
        "yield_rows": len(tables["sit_yield"]),
        "initial_ecosystem_tc": float(initial),
        "final_offset": final_offset,
        "final_ecosystem_tc": float(final),
        "pools_sha256": _sha256(pools_path),
        "accounts_sha256": _sha256(accounts_path),
        "libcbm_version": _libcbm_version(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"WS3 reference: inventory={len(tables['sit_inventory'])} "
        f"yield={len(tables['sit_yield'])} "
        f"ecosystem={initial:.1f}->{final:.1f} tC over {args.n_steps} steps"
    )
    print(f"accounts: {accounts_path}")
    print(f"pools: {pools_path}")
    print(f"manifest: {manifest_path}")
    return 0


def _sha256(path: Path) -> str:
    """Return a file SHA-256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _libcbm_version() -> str:
    """Return the installed libcbm version."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("libcbm")
    except PackageNotFoundError:  # pragma: no cover
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
