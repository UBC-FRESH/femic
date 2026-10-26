"""Command-line entry point for site-index reconciliation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from femic.site_index.au import load_au_site_index, summarize_au_site_index
from femic.site_index.reconcile import (
    DEFAULT_DELTA_THRESHOLD,
    DEFAULT_MIN_SIBEC_PLOT_COUNT,
    reconcile_site_index,
    summarize_reconciliation,
)
from femic.site_index.sibec import (
    aggregate_sibec_by_bgc_unit,
    combine_sibec_tables,
    load_sibec_addendum,
    load_sibec_table,
    select_sibec_source,
)
from femic.site_index.vdyp import load_vdyp_site_index
from femic.site_index.vri import load_vri_site_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m femic.site_index",
        description=(
            "Reconcile VRI, VDYP, and SIBEC site index. This reports source "
            "values and differences; it does not change curves or AAC."
        ),
    )
    parser.add_argument("--vri", required=True, type=Path, help="VRI Feather/CSV")
    parser.add_argument(
        "--vdyp", required=True, type=Path, help="VDYP layer Feather/CSV"
    )
    parser.add_argument("--sibec", required=True, type=Path, help="SIBEC XLSX or CSV")
    parser.add_argument(
        "--sibec-addendum",
        type=Path,
        help="Optional SIBEC 2014 addendum XLSX (ciReportByUnit sheet)",
    )
    parser.add_argument(
        "--sibec-sheet",
        default="0",
        help="SIBEC worksheet name or zero-based index (default: 0)",
    )
    parser.add_argument(
        "--out-csv", type=Path, help="Write the feature-level reconciliation CSV"
    )
    parser.add_argument("--out-json", type=Path, help="Write the JSON summary")
    parser.add_argument(
        "--au-input",
        type=Path,
        help="Optional TSA 03_input CSV for a separate AU-level report",
    )
    parser.add_argument(
        "--out-au-csv", type=Path, help="Write the AU-level site-index CSV"
    )
    parser.add_argument(
        "--out-au-json", type=Path, help="Write the AU-level JSON summary"
    )
    parser.add_argument(
        "--delta-threshold",
        type=float,
        default=DEFAULT_DELTA_THRESHOLD,
        help=f"Conflict threshold in metres (default: {DEFAULT_DELTA_THRESHOLD})",
    )
    parser.add_argument(
        "--min-sibec-plot-count",
        type=int,
        default=DEFAULT_MIN_SIBEC_PLOT_COUNT,
        help=(
            "Minimum SIBEC plot count for SIBEC to be the reference when VRI "
            f"has no SITE_INDEX (default: {DEFAULT_MIN_SIBEC_PLOT_COUNT})"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sheet: str | int = args.sibec_sheet
    if isinstance(sheet, str) and sheet.isdigit():
        sheet = int(sheet)

    vri = load_vri_site_index(args.vri)
    vdyp = load_vdyp_site_index(args.vdyp)
    sibec_table = load_sibec_table(args.sibec, sheet_name=sheet)
    if args.sibec_addendum is not None:
        sibec_table = combine_sibec_tables(
            sibec_table, load_sibec_addendum(args.sibec_addendum)
        )
    sibec = select_sibec_source(aggregate_sibec_by_bgc_unit(sibec_table))
    frame = reconcile_site_index(
        vri,
        vdyp,
        sibec,
        delta_threshold=args.delta_threshold,
        min_sibec_plot_count=args.min_sibec_plot_count,
    )
    summary = summarize_reconciliation(frame, delta_threshold=args.delta_threshold)

    if args.out_csv is not None:
        args.out_csv.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(args.out_csv, index=False)
    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if args.au_input is not None:
        au_table = load_au_site_index(args.au_input)
        au_summary = summarize_au_site_index(au_table)
        if args.out_au_csv is not None:
            args.out_au_csv.parent.mkdir(parents=True, exist_ok=True)
            au_table.to_csv(args.out_au_csv, index=False)
        if args.out_au_json is not None:
            args.out_au_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_au_json.write_text(
                json.dumps(au_summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(
            "AU-level report: "
            f"{au_summary['au_count']} AUs, {au_summary['row_count']} rows"
            + (f" -> {args.out_au_csv}" if args.out_au_csv is not None else ""),
            file=sys.stderr,
        )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
