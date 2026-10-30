"""Split a tile manifest into download shards and compute batches."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--download-shards", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.download_shards <= 0 or args.batch_size <= 0:
        raise SystemExit("download-shards and batch-size must be positive")
    frame = pd.read_csv(args.manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    batches = args.output_dir / "batches"
    batches.mkdir(exist_ok=True)
    for index in range(args.download_shards):
        frame.iloc[index::args.download_shards].to_csv(
            args.output_dir / f"download_{chr(ord('a') + index)}.csv", index=False
        )
    for start in range(0, len(frame), args.batch_size):
        frame.iloc[start : start + args.batch_size].to_csv(
            batches / f"batch_{start // args.batch_size:04d}.csv", index=False
        )
    print(f"wrote {args.download_shards} download shards and {(len(frame) + args.batch_size - 1) // args.batch_size} batches")


if __name__ == "__main__":
    main()
