"""Backcast the public Chapman Creek WSC annual-maxima records."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from femic.hydrology.validation import (  # type: ignore[import-untyped]
    HYDROLOGY_PILOT_RETURN_PERIODS,
    load_pilot_annual_maxima,
    load_pilot_gauges,
    run_gauge_backcast,
)

SCHEMA_VERSION = "femic.chapman_gauge_backcast.v1"
FIXTURE_ROOT = Path("tests/fixtures/hydrology/chapman_gauges")
DEFAULT_OUTPUT = Path("runtime/p118_chapman/gauge_backcast.json")


def backcast_chapman(
    fixture_root: Path = FIXTURE_ROOT,
    *,
    bootstrap_samples: int = 200,
    seed: int = 42,
    generated_utc: str | None = None,
) -> dict[str, object]:
    """Run the three-station historical gauge frequency backcast."""
    root = fixture_root.expanduser().resolve()
    gauges = load_pilot_gauges(root / "gauges.json")
    rows = load_pilot_annual_maxima(root / "annual_maxima.csv")
    timestamp = generated_utc or datetime.now(UTC).isoformat()
    backcasts = [
        run_gauge_backcast(
            gauge,
            rows,
            return_periods=HYDROLOGY_PILOT_RETURN_PERIODS,
            bootstrap_samples=bootstrap_samples,
            seed=seed,
            generated_utc=timestamp,
        )
        for gauge in gauges
    ]
    station_years = {
        gauge.station_number: sorted(
            row.year for row in rows if row.station_number == gauge.station_number
        )
        for gauge in gauges
    }
    overlapping = sorted(set(station_years["08GA046"]) & set(station_years["08GA060"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": timestamp,
        "fixture": {
            "root": str(root),
            "gauges_sha256": _sha256(root / "gauges.json"),
            "annual_maxima_sha256": _sha256(root / "annual_maxima.csv"),
        },
        "stations": [
            {
                **backcast.to_dict(),
                "record_years": station_years[backcast.gauge.station_number],
            }
            for backcast in backcasts
        ],
        "record_structure": {
            "sequential": True,
            "overlapping_years": overlapping,
            "gaps": ["1988-1992", "2004-present"],
            "pooled_record": False,
            "reason": (
                "The stations are sequential and represent different periods and "
                "diversion states. They are not one continuous record."
            ),
        },
        "decision": {
            "status": "historical_gauge_frequency_only",
            "current_baseline": False,
            "flood_map": False,
            "defensible_for": [
                "historical single-station GEV/LP3 frequency screening",
                "method development and record-length sensitivity",
            ],
            "not_defensible_for": [
                "a current flood-frequency baseline",
                "pooling the three stations without diversion/nonstationarity review",
                "a regulatory flood map or design flood",
            ],
            "reason": (
                "The public records end in 2003, are sequential, span different "
                "periods, and cross the Sechelt diversion. Each station has at "
                "least 11 annual maxima, but the combined series is not a "
                "continuous current baseline."
            ),
            "review_required": (
                "Hydrologist review of the diversion, record discontinuities, and "
                "station representativeness before operational use."
            ),
        },
        "caveats": [
            "No daily series, current SCRD record, or flood extent is included.",
            "GEV fits use the bounded-shape fallback where needed.",
            "LP3 and GEV are screening fits, not a design-flood determination.",
        ],
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bootstrap-samples", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--generated-utc")
    args = parser.parse_args(argv)
    try:
        result = backcast_chapman(
            args.fixture_root,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
            generated_utc=args.generated_utc,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        parser.exit(1, f"Chapman gauge backcast failed: {exc}\n")
    _write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
