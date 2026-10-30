"""Process one batch of point-cloud tiles into a Parquet feature part."""
from __future__ import annotations

import argparse
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from femic.lidar.inventory import build_pointcloud_grid_features


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("part_out", type=Path)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--grid-size-m", type=float, default=25.0)
    parser.add_argument("--origin-x", type=float, required=True)
    parser.add_argument("--origin-y", type=float, required=True)
    parser.add_argument("--min-returns", type=int, default=10)
    parser.add_argument("--min-cover-pct", type=float, default=10.0)
    args = parser.parse_args()
    tmp = args.part_out.parent / "tmp" / args.part_out.stem
    tmp.mkdir(parents=True, exist_ok=True)
    rows = pd.read_csv(args.manifest).to_dict("records")
    print(f"batch={args.part_out.stem} tiles={len(rows)} workers={args.workers}", flush=True)

    def one(row: dict[str, object]) -> str | tuple[str, ...]:
        filename = str(row["filename"])
        laz = args.raw_root / "laz" / filename
        dem = args.raw_root / "dem" / str(row["dem_filename"])
        out = tmp / (filename.replace(".laz", ".csv"))
        if out.exists() and out.stat().st_size > 0:
            return str(out)
        if not laz.exists() or not dem.exists():
            return ("MISSING", filename, str(laz.exists()), str(dem.exists()))
        try:
            build_pointcloud_grid_features(
                [laz],
                dem,
                out,
                grid_size_m=args.grid_size_m,
                min_returns=args.min_returns,
                min_cover_pct=args.min_cover_pct,
                grid_origin_x=args.origin_x,
                grid_origin_y=args.origin_y,
                source_tile=filename,
            )
            return str(out)
        except Exception as exc:  # noqa: BLE001 - report the tile and keep the batch usable
            return ("ERROR", filename, repr(exc)[:300])

    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, row) for row in rows]
        for index, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if index % 8 == 0 or index == len(futures):
                print(f"progress {index}/{len(futures)}", flush=True)
    bad = [item for item in results if not isinstance(item, str) or item.startswith(("MISSING", "ERROR"))]
    for item in bad:
        print("BAD", item, flush=True)
    files = [Path(item) for item in results if isinstance(item, str) and Path(item).exists()]
    if not files:
        print("no successful tiles", flush=True)
        raise SystemExit(1)
    frame = pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
    frame["batch"] = args.part_out.stem
    args.part_out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.part_out, index=False)
    print(f"wrote {args.part_out} rows={len(frame)} tiles={len(files)} bad={len(bad)}", flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
