#!/usr/bin/env python
"""Deterministically rebuild and verify the TSA29 Patchworks instance."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import pandas as pd
import yaml

KEY_ACCOUNT_NAMES = (
    "product.Yield.managed.Total",
    "product.HarvestedVolume.managed.Total.CC",
    "feature.Seral.regenerating",
    "feature.Seral.young",
    "feature.Seral.immature",
    "feature.Seral.mature",
    "feature.Seral.overmature",
)
TRACKS_TABLES = (
    "blocks.csv",
    "curves.csv",
    "treatments.csv",
    "features.csv",
    "products.csv",
    "tracknames.csv",
    "strata.csv",
    "accounts.csv",
    "protoaccounts.csv",
)


@dataclass
class RebuildReport:
    run_id: str
    instance_root: str
    matrix_returncode: int
    managed_area_ha: float
    passive_area_ha: float
    seral_account_count: int
    block_join_intersection: int
    block_join_csv_only: int
    block_join_shp_only: int
    tracks_row_counts: dict[str, int]
    account_count: int
    key_accounts_present: dict[str, bool]
    artifact_timestamps_utc: dict[str, str]
    baseline_path: str | None
    baseline_match: bool | None
    baseline_differences: list[str]
    checks_passed: bool
    failures: list[str]


def _repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def _import_femic_modules(repo_root: Path) -> dict[str, Any]:
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from femic.fmg.patchworks import (
        build_forestmodel_xml_tree,
        validate_forestmodel_xml_tree,
        write_forestmodel_xml,
    )

    return {
        "build_forestmodel_xml_tree": build_forestmodel_xml_tree,
        "validate_forestmodel_xml_tree": validate_forestmodel_xml_tree,
        "write_forestmodel_xml": write_forestmodel_xml,
    }


def _backup_file(path: Path, stamp: str) -> Path:
    backup = path.with_name(path.stem + f"_backup_{stamp}" + path.suffix)
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup


def _parse_managed_and_passive_area(stderr_text: str) -> tuple[float, float]:
    managed_match = re.search(r"^Managed\s*:\s*([0-9.]+)", stderr_text, flags=re.MULTILINE)
    passive_match = re.search(r"^Passive\s*:\s*([0-9.]+)", stderr_text, flags=re.MULTILINE)
    managed = float(managed_match.group(1)) if managed_match else 0.0
    passive = float(passive_match.group(1)) if passive_match else 0.0
    return managed, passive


def _collect_tracks_row_counts(*, tracks_dir: Path) -> dict[str, int]:
    row_counts: dict[str, int] = {}
    for name in TRACKS_TABLES:
        table_path = tracks_dir / name
        if not table_path.exists():
            row_counts[name] = -1
            continue
        frame = pd.read_csv(table_path)
        row_counts[name] = int(len(frame))
    return row_counts


def _collect_key_account_presence(*, accounts: pd.DataFrame) -> dict[str, bool]:
    values = set(accounts["ACCOUNT"].astype(str).tolist())
    return {name: (name in values) for name in KEY_ACCOUNT_NAMES}


def _to_utc_iso(path: Path) -> str:
    if not path.exists():
        return "missing"
    stamp = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    return stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _collect_artifact_timestamps(*, instance_root: Path, run_id: str) -> dict[str, str]:
    model_root = instance_root / "models" / "tsa29_patchworks_model"
    tracks_dir = model_root / "tracks"
    logs_dir = instance_root / "vdyp_io" / "logs"
    artifacts = {
        "yield_forestmodel_xml": model_root / "yield" / "forestmodel.xml",
        "blocks_shp": model_root / "blocks" / "blocks.shp",
        "topology_csv": model_root / "blocks" / "topology_blocks_200r.csv",
        "tracks_accounts_csv": tracks_dir / "accounts.csv",
        "tracks_products_csv": tracks_dir / "products.csv",
        "matrix_manifest_json": logs_dir / f"patchworks_matrixbuilder_manifest-{run_id}.json",
        "matrix_stderr_log": logs_dir / f"patchworks_matrixbuilder_stderr-{run_id}.log",
        "matrix_stdout_log": logs_dir / f"patchworks_matrixbuilder_stdout-{run_id}.log",
    }
    return {name: _to_utc_iso(path) for name, path in artifacts.items()}




def _validate_existing_block_artifacts(*, model_root: Path) -> list[str]:
    failures: list[str] = []
    required = (
        model_root / "blocks" / "blocks.shp",
        model_root / "blocks" / "blocks.dbf",
        model_root / "blocks" / "topology_blocks_200r.csv",
        model_root / "tracks" / "blocks.csv",
    )
    for path in required:
        if not path.exists():
            failures.append(f"missing required existing block artifact: {path}")
    return failures

def _compare_observed_with_baseline(
    *,
    observed_row_counts: dict[str, int],
    observed_account_count: int,
    observed_key_presence: dict[str, bool],
    baseline_payload: dict[str, Any],
) -> list[str]:
    differences: list[str] = []
    baseline_row_counts = baseline_payload.get("tracks_row_counts", {})
    for name, expected in baseline_row_counts.items():
        actual = observed_row_counts.get(str(name))
        if int(actual) != int(expected):
            differences.append(f"row-count mismatch for {name}: actual={actual} expected={expected}")

    expected_account_count = baseline_payload.get("account_count")
    if expected_account_count is not None and int(observed_account_count) != int(expected_account_count):
        differences.append(
            "account-count mismatch: "
            f"actual={observed_account_count} expected={int(expected_account_count)}"
        )

    baseline_key_presence = baseline_payload.get("key_accounts_present", {})
    for name, expected in baseline_key_presence.items():
        actual = bool(observed_key_presence.get(str(name), False))
        if actual != bool(expected):
            differences.append(
                f"key-account presence mismatch for {name}: actual={actual} expected={bool(expected)}"
            )
    return differences


def rebuild_tsa29_instance(
    *,
    repo_root: Path,
    instance_root: Path,
    run_id: str,
    baseline_path: Path | None,
    write_baseline: bool,
    reuse_existing_blocks: bool,
) -> RebuildReport:
    modules = _import_femic_modules(repo_root=repo_root)
    build_forestmodel = modules["build_forestmodel_xml_tree"]
    validate_forestmodel = modules["validate_forestmodel_xml_tree"]
    write_forestmodel = modules["write_forestmodel_xml"]

    failures: list[str] = []
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    runtime_config_path = instance_root / "config" / "patchworks.runtime.windows.yaml"
    runtime_payload = yaml.safe_load(runtime_config_path.read_text(encoding="utf-8")) or {}
    matrix_cfg = runtime_payload.get("matrix_builder", {}) if isinstance(runtime_payload, dict) else {}
    fragments_rel = matrix_cfg.get("fragments_path", "")
    fragments_path = (runtime_config_path.parent / Path(str(fragments_rel))).resolve()
    if not fragments_path.exists():
        failures.append(
            f"missing fragments dataset for patchworks runtime: {fragments_path}"
        )
    seral_config_path = instance_root / "config" / "seral.tsa29.yaml"
    bundle_dir = instance_root / "data" / "model_input_bundle"
    model_root = instance_root / "models" / "tsa29_patchworks_model"

    au_table = pd.read_csv(bundle_dir / "au_table.csv")
    curve_table = pd.read_csv(bundle_dir / "curve_table.csv")
    curve_points = pd.read_csv(bundle_dir / "curve_points_table.csv")

    seral_cfg = yaml.safe_load(seral_config_path.read_text(encoding="utf-8")) or {}

    import xml.etree.ElementTree as et

    yield_xml = model_root / "yield" / "forestmodel.xml"
    output_xml = instance_root / "output" / "patchworks_tsa29_validated" / "forestmodel.xml"
    root_old = et.parse(yield_xml).getroot()
    start_year = int(root_old.get("year", "2026"))
    horizon_years = int(root_old.get("horizon", "300"))

    root_new = build_forestmodel(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        start_year=start_year,
        horizon_years=horizon_years,
        seral_stage_config=seral_cfg,
    )
    validate_forestmodel(root=root_new)

    _backup_file(yield_xml, stamp)
    if output_xml.exists():
        _backup_file(output_xml, stamp)
    write_forestmodel(root=root_new, path=yield_xml)
    write_forestmodel(root=root_new, path=output_xml)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    upstream_required = [
        instance_root / "data" / "tsa_boundaries.feather",
        instance_root / "data" / "ria_vri_vclr1p_checkpoint1.feather",
        instance_root / "VDYP7" / "VDYP7" / "VDYP7Console.exe",
    ]
    upstream_available = all(path.exists() for path in upstream_required)

    pre_steps = []
    if upstream_available:
        pre_steps = [
            [
                sys.executable,
                "-m",
                "femic",
                "prep",
                "validate-case",
                "--run-config",
                "config/run_profile.tsa29.yaml",
                "--tipsy-config-dir",
                "config/tipsy",
            ],
            [
                sys.executable,
                "-m",
                "femic",
                "prep",
                "geospatial-preflight",
            ],
            [
                sys.executable,
                "-m",
                "femic",
                "run",
                "--run-config",
                "config/run_profile.tsa29.yaml",
            ],
            [
                sys.executable,
                "-m",
                "femic",
                "tsa",
                "post-tipsy",
                "--run-config",
                "config/run_profile.tsa29.yaml",
                "--tsa",
                "29",
            ],
        ]

    patchworks_steps = [
        [
            sys.executable,
            "-m",
            "femic",
            "patchworks",
            "preflight",
            "--config",
            "config/patchworks.runtime.windows.yaml",
        ],
    ]
    if reuse_existing_blocks:
        failures.extend(_validate_existing_block_artifacts(model_root=model_root))
    else:
        patchworks_steps.append(
            [
                sys.executable,
                "-m",
                "femic",
                "patchworks",
                "build-blocks",
                "--config",
                "config/patchworks.runtime.windows.yaml",
                "--with-topology",
                "--topology-radius",
                "200",
            ]
        )

    for cmd in pre_steps + patchworks_steps:
        proc = subprocess.run(
            cmd,
            cwd=str(instance_root),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            failures.append(f"step failed ({' '.join(cmd)}): {proc.stderr.strip()}")

    matrix = subprocess.run(
        [
            sys.executable,
            "-m",
            "femic",
            "patchworks",
            "matrix-build",
            "--config",
            "config/patchworks.runtime.windows.yaml",
            "--run-id",
            run_id,
        ],
        cwd=str(instance_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    tracks_dir = model_root / "tracks"
    accounts_path = tracks_dir / "accounts.csv"
    accounts = pd.read_csv(accounts_path) if accounts_path.exists() else pd.DataFrame(columns=["ACCOUNT"])
    tracks_row_counts = _collect_tracks_row_counts(tracks_dir=tracks_dir)
    key_accounts_present = _collect_key_account_presence(accounts=accounts)

    seral_accounts = accounts[
        accounts["ACCOUNT"].astype(str).str.startswith("feature.Seral.")
        | accounts["ACCOUNT"].astype(str).str.startswith("product.Seral.area.")
    ]
    if accounts_path.exists() and seral_accounts.empty:
        failures.append("seral accounts missing from tracks/accounts.csv")

    blocks_csv = pd.read_csv(tracks_dir / "blocks.csv") if (tracks_dir / "blocks.csv").exists() else pd.DataFrame(columns=["BLOCK"])
    block_ids = set(blocks_csv["BLOCK"].astype(int).tolist()) if not blocks_csv.empty else set()

    import struct

    dbf_path = model_root / "blocks" / "blocks.dbf"
    shp_ids: set[int] = set()
    if dbf_path.exists():
        b = dbf_path.read_bytes()
        h = struct.unpack("<H", b[8:10])[0]
        rl = struct.unpack("<H", b[10:12])[0]
        n = struct.unpack("<I", b[4:8])[0]
        fields = []
        off = 32
        while off < h and b[off] != 0x0D:
            name = b[off : off + 11].split(b"\x00", 1)[0].decode("ascii", "ignore")
            flen = b[off + 16]
            fields.append((name, flen))
            off += 32
        pos = 1
        start = None
        length = None
        for name, flen in fields:
            if name == "BLOCK":
                start = pos
                length = flen
                break
            pos += flen
        if start is not None and length is not None:
            for i in range(n):
                rec = b[h + i * rl : h + (i + 1) * rl]
                if rec and rec[0] != 0x2A:
                    shp_ids.add(int(rec[start : start + length].decode("latin1", "ignore").strip()))

    block_join_intersection = len(block_ids.intersection(shp_ids))
    block_join_csv_only = len(block_ids - shp_ids)
    block_join_shp_only = len(shp_ids - block_ids)
    if block_join_csv_only or block_join_shp_only:
        failures.append(
            f"block join mismatch csv_only={block_join_csv_only} shp_only={block_join_shp_only}"
        )

    logs_dir = instance_root / "vdyp_io" / "logs"
    stderr_path = logs_dir / f"patchworks_matrixbuilder_stderr-{run_id}.log"
    stderr_text = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else matrix.stderr
    managed_area_ha, passive_area_ha = _parse_managed_and_passive_area(stderr_text)

    baseline_payload: dict[str, Any] | None = None
    baseline_differences: list[str] = []
    baseline_match: bool | None = None
    if write_baseline:
        baseline_payload = {
            "tracks_row_counts": tracks_row_counts,
            "account_count": int(len(accounts)),
            "key_accounts_present": key_accounts_present,
        }
        baseline_path = baseline_path or (repo_root / "scripts" / "tsa29" / "tsa29_tracks_baseline.json")
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(baseline_payload, indent=2), encoding="utf-8")
        baseline_match = True
    elif baseline_path is not None and baseline_path.exists():
        baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline_differences = _compare_observed_with_baseline(
            observed_row_counts=tracks_row_counts,
            observed_account_count=int(len(accounts)),
            observed_key_presence=key_accounts_present,
            baseline_payload=baseline_payload,
        )
        baseline_match = len(baseline_differences) == 0

    if matrix.returncode != 0:
        failures.append(f"patchworks matrix-build failed: {matrix.stderr.strip()}")

    checks_passed = len(failures) == 0

    report = RebuildReport(
        run_id=run_id,
        instance_root=str(instance_root),
        matrix_returncode=int(matrix.returncode),
        managed_area_ha=float(managed_area_ha),
        passive_area_ha=float(passive_area_ha),
        seral_account_count=int(len(seral_accounts)),
        block_join_intersection=int(block_join_intersection),
        block_join_csv_only=int(block_join_csv_only),
        block_join_shp_only=int(block_join_shp_only),
        tracks_row_counts=tracks_row_counts,
        account_count=int(len(accounts)),
        key_accounts_present=key_accounts_present,
        artifact_timestamps_utc=_collect_artifact_timestamps(instance_root=instance_root, run_id=run_id),
        baseline_path=str(baseline_path) if baseline_path else None,
        baseline_match=baseline_match,
        baseline_differences=baseline_differences,
        checks_passed=checks_passed,
        failures=failures,
    )

    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = logs_dir / f"tsa29_rebuild_report-{run_id}.json"
    report_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

    evidence_latest = instance_root / "evidence" / "reference_rebuild_report.latest.json"
    evidence_latest.parent.mkdir(parents=True, exist_ok=True)
    evidence_payload = {
        "status": "pass" if checks_passed else "warning",
        "regression_gate": "pass" if checks_passed else "warning",
        "summary": {
            "case_id": "tsa29",
            "run_mode": "deterministic_rebuild",
            "run_id": run_id,
            "checks_passed": checks_passed,
            "managed_area_ha": managed_area_ha,
            "passive_area_ha": passive_area_ha,
        },
        "source": {
            "report": str(report_path.relative_to(instance_root)),
            "matrix_manifest": f"vdyp_io/logs/patchworks_matrixbuilder_manifest-{run_id}.json",
        },
        "timestamp_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    evidence_latest.write_text(json.dumps(evidence_payload, indent=2), encoding="utf-8")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild and verify the TSA29 Patchworks instance deterministically."
    )
    parser.add_argument(
        "--instance-root",
        type=Path,
        default=Path("external/femic-tsa29-instance"),
        help="Path to TSA29 instance root (default: external/femic-tsa29-instance)",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=f"tsa29_rebuild_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Run id used for matrix-builder and report logs.",
    )
    parser.add_argument(
        "--baseline-json",
        type=Path,
        default=Path("scripts/tsa29/tsa29_tracks_baseline.json"),
        help="Path to baseline JSON used for structural regression checks.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Write the baseline JSON from current observed tracks summary.",
    )
    parser.add_argument(
        "--reuse-existing-blocks",
        action="store_true",
        help=(
            "Reuse existing TSA29 blocks/topology artifacts instead of rerunning "
            "`femic patchworks build-blocks`."
        ),
    )
    args = parser.parse_args()

    repo_root = _repo_root_from_script()
    instance_root = args.instance_root
    if not instance_root.is_absolute():
        instance_root = (repo_root / instance_root).resolve()
    baseline_path = args.baseline_json
    if baseline_path is not None and not baseline_path.is_absolute():
        baseline_path = (repo_root / baseline_path).resolve()

    report = rebuild_tsa29_instance(
        repo_root=repo_root,
        instance_root=instance_root,
        run_id=args.run_id,
        baseline_path=baseline_path,
        write_baseline=bool(args.write_baseline),
        reuse_existing_blocks=bool(args.reuse_existing_blocks),
    )

    logs_dir = instance_root / "vdyp_io" / "logs"
    report_path = logs_dir / f"tsa29_rebuild_report-{args.run_id}.json"

    if report.checks_passed:
        print(f"TSA29 rebuild succeeded. Report: {report_path}")
        return 0

    print(f"TSA29 rebuild completed with failures. Report: {report_path}")
    for failure in report.failures:
        print(f" - {failure}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
