from __future__ import annotations

import json
from pathlib import Path

from femic.rebuild_baseline import (
    apply_diff_allowlist,
    build_current_snapshot,
    diff_snapshots,
    load_diff_allowlist,
    load_snapshot,
    resolve_baseline_path,
    save_snapshot,
)


def test_resolve_baseline_path_defaults_to_instance_config(tmp_path: Path) -> None:
    resolved = resolve_baseline_path(baseline_path=None, instance_root=tmp_path)
    assert resolved == (tmp_path / "config/rebuild.baseline.json").resolve()


def test_build_current_snapshot_and_diff_detects_table_and_xml_drift(
    tmp_path: Path,
) -> None:
    model_dir = tmp_path / "model"
    tracks_dir = model_dir / "tracks"
    yield_dir = model_dir / "yield"
    tracks_dir.mkdir(parents=True)
    yield_dir.mkdir(parents=True)

    (tracks_dir / "accounts.csv").write_text(
        "GROUP,ATTRIBUTE,ACCOUNT,SUM\n_MANAGED_,x,feature.Area.managed,1\n",
        encoding="utf-8",
    )
    (yield_dir / "ForestModel.xml").write_text(
        "<forestmodel><curve id='c1'/><attribute id='a1'/></forestmodel>",
        encoding="utf-8",
    )

    runtime_config = tmp_path / "patchworks.runtime.yaml"
    runtime_config.write_text(
        "patchworks:\n"
        "  jar_path: C:/patchworks/patchworks.jar\n"
        "  license_env: SPS_LICENSE_SERVER\n"
        "  license_value: user@server\n"
        "  spshome: C:/patchworks\n"
        "matrix_builder:\n"
        f"  fragments_path: {model_dir / 'data' / 'fragments.dbf'}\n"
        f"  output_dir: {tracks_dir}\n"
        f"  forestmodel_xml_path: {yield_dir / 'ForestModel.xml'}\n",
        encoding="utf-8",
    )

    baseline = build_current_snapshot(patchworks_config_path=runtime_config)
    (tracks_dir / "accounts.csv").write_text(
        "GROUP,ATTRIBUTE,ACCOUNT,SUM\n_MANAGED_,x,feature.Area.managed,1\n"
        "_MANAGED_,x,feature.Seral.AU1.mature,1\n",
        encoding="utf-8",
    )
    (yield_dir / "ForestModel.xml").write_text(
        "<forestmodel><curve id='c1'/><curve id='c2'/><attribute id='a1'/></forestmodel>",
        encoding="utf-8",
    )
    current = build_current_snapshot(patchworks_config_path=runtime_config)

    diff = diff_snapshots(baseline=baseline, current=current)

    assert diff["baseline_match"] is False
    assert diff["diff_count"] >= 1
    assert any(item["table"] == "accounts.csv" for item in diff["table_diffs"])
    assert diff["xml_diff"]["status"] == "changed"


def test_save_and_load_snapshot_roundtrip(tmp_path: Path) -> None:
    payload = {"schema_version": "1.0", "track_tables": {}}
    target = tmp_path / "config" / "rebuild.baseline.json"
    save_snapshot(path=target, snapshot=payload)
    loaded = load_snapshot(target)
    assert loaded == payload
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == "1.0"


def test_allowlist_filters_expected_diffs(tmp_path: Path) -> None:
    allowlist_path = tmp_path / "config/rebuild.allowlist.yaml"
    allowlist_path.parent.mkdir(parents=True, exist_ok=True)
    allowlist_path.write_text(
        "allowed_table_diffs:\n  - accounts.csv\nallowed_xml_keys:\n  - curve_count\n",
        encoding="utf-8",
    )
    allowlist = load_diff_allowlist(allowlist_path)
    diff = {
        "table_diffs": [
            {"table": "accounts.csv", "status": "changed"},
            {"table": "products.csv", "status": "changed"},
        ],
        "xml_diff": {
            "status": "changed",
            "changed_keys": ["curve_count", "attribute_count"],
        },
    }
    filtered = apply_diff_allowlist(diff_payload=diff, allowlist_payload=allowlist)

    assert filtered["allowlist_match"] is False
    assert filtered["unexpected_diff_count"] == 2
    assert filtered["unexpected_xml_keys"] == ["attribute_count"]
    assert len(filtered["unexpected_table_diffs"]) == 1
