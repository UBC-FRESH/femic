"""Download point-cloud and DEM tiles listed in a manifest."""
from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("laz_dir", type=Path)
    parser.add_argument("dem_dir", type=Path)
    parser.add_argument("workers", type=int, nargs="?", default=8)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    args.laz_dir.mkdir(parents=True, exist_ok=True)
    args.dem_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(args.manifest)
    tasks: dict[str, Path] = {}
    for row in frame.to_dict("records"):
        tasks.setdefault(str(row["url"]), args.laz_dir / str(row["filename"]))
        tasks.setdefault(str(row["dem_url"]), args.dem_dir / str(row["dem_filename"]))
    print(f"rows={len(frame)} unique_files={len(tasks)} workers={args.workers}", flush=True)

    def fetch(item: tuple[str, Path]) -> tuple[str, str, int]:
        url, destination = item
        if destination.exists() and destination.stat().st_size > 0:
            return url, "exists", destination.stat().st_size
        part = destination.with_name(destination.name + ".part")
        command = [
            "curl", "-k", "-L", "--fail", "--retry", "5", "--retry-all-errors",
            "--retry-delay", "5", "--max-time", str(args.timeout),
            "--continue-at", "-", "-o", str(part), url,
        ]
        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            part.replace(destination)
            return url, "ok", destination.stat().st_size
        except subprocess.CalledProcessError as exc:
            error = exc.stderr.decode("utf-8", "replace")[-300:] if exc.stderr else ""
            if exc.returncode == 22 and "416" in error and part.exists() and part.stat().st_size > 0:
                part.replace(destination)
                return url, "ok-complete-part", destination.stat().st_size
            return url, "fail:" + error, 0

    ok = exists = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for index, result in enumerate(pool.map(fetch, tasks.items()), 1):
            url, status, _ = result
            if status == "ok":
                ok += 1
            elif status == "exists" or status == "ok-complete-part":
                exists += 1
            else:
                fail += 1
                print("FAIL", status, url, flush=True)
            if index % 100 == 0 or index == len(tasks):
                print(f"progress {index}/{len(tasks)} ok={ok} exists={exists} fail={fail}", flush=True)
    print(f"done ok={ok} exists={exists} fail={fail}", flush=True)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
