from __future__ import annotations

from pathlib import Path

from femic.rebuild_invariants import (
    build_species_account_policy_invariants,
    collect_rebuild_metrics,
    evaluate_invariants,
    has_fatal_invariant_failures,
)


def test_collect_rebuild_metrics_extracts_known_risk_dimensions(
    tmp_path: Path,
) -> None:
    model_dir = tmp_path / "model"
    tracks_dir = model_dir / "tracks"
    blocks_dir = model_dir / "blocks"
    tracks_dir.mkdir(parents=True)
    blocks_dir.mkdir(parents=True)
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    (tracks_dir / "accounts.csv").write_text(
        "GROUP,ATTRIBUTE,ACCOUNT,SUM\n"
        "_MANAGED_,x,product.Yield.managed.CW,1\n"
        "_MANAGED_,x,product.Yield.managed.Total,1\n"
        "_MANAGED_,x,feature.Seral.AU1.mature,1\n",
        encoding="utf-8",
    )
    (tracks_dir / "curves.csv").write_text(
        "CURVE,X,Y\n10,0,0\n10,1,5\n11,0,0\n",
        encoding="utf-8",
    )
    (tracks_dir / "products.csv").write_text(
        "TRACK,OFFSET,LABEL,CURVE\n"
        "1,0,product.Yield.managed.CW,10\n"
        "1,0,product.Yield.managed.PL,11\n",
        encoding="utf-8",
    )
    (tracks_dir / "blocks.csv").write_text(
        "BLOCK,TYPE,TRACK,OFFSET,AREA\n1,managed,1,0,10\n2,unmanaged,2,0,3\n",
        encoding="utf-8",
    )
    (blocks_dir / "topology_blocks_200r.csv").write_text(
        "BLOCK1,BLOCK2,DISTANCE,LENGTH\n1,2,0.000,5.000\n",
        encoding="utf-8",
    )
    (log_dir / "patchworks_matrixbuilder_stdout-r1.log").write_text(
        "Block shape file contains 3 polygons that do not have corresponding blocks\n"
        "The blocks,csv input file contains 5 blocks that do not have corresponding polygons\n",
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
        f"  fragments_path: {tracks_dir / 'fragments.dbf'}\n"
        f"  output_dir: {tracks_dir}\n"
        f"  forestmodel_xml_path: {model_dir / 'yield' / 'ForestModel.xml'}\n",
        encoding="utf-8",
    )

    metrics = collect_rebuild_metrics(
        instance_root=tmp_path,
        log_dir=log_dir,
        run_id="r1",
        patchworks_config_path=runtime_config,
    )

    assert metrics["managed_area_ha"] == 10.0
    assert "product.Yield.managed.CW" in metrics["accounts.list"]
    assert "product.Yield.managed.Total" in metrics["accounts.list"]
    assert metrics["managed_species_account_count"] == 1
    assert metrics["seral_account_count"] == 1
    assert "product.Yield.managed.CW" in metrics["products.nonzero_labels"]
    assert "product.Yield.managed.PL" not in metrics["products.nonzero_labels"]
    assert metrics["block_join_mismatch_count"] == 5
    assert metrics["topology_edge_count"] == 1


def test_evaluate_invariants_flags_fatal_regressions() -> None:
    invariants = [
        {
            "invariant_id": "managed_species_nonempty",
            "severity": "fatal",
            "metric": "managed_species_account_count",
            "comparator": "gt",
            "target": 0,
            "remediation": "rebuild products/accounts",
        },
        {
            "invariant_id": "block_join_clean",
            "severity": "warn",
            "metric": "block_join_mismatch_count",
            "comparator": "eq",
            "target": 0,
            "remediation": "rebuild blocks/topology",
        },
    ]
    metrics = {
        "managed_species_account_count": 0,
        "block_join_mismatch_count": 2,
    }
    results = evaluate_invariants(invariants=invariants, metrics=metrics)

    assert results[0].status == "fail"
    assert results[1].status == "warn"
    assert has_fatal_invariant_failures(results) is True


def test_evaluate_invariants_supports_contains_comparators() -> None:
    invariants = [
        {
            "invariant_id": "plc_present",
            "severity": "fatal",
            "metric": "accounts.list",
            "comparator": "contains",
            "target": "product.Yield.managed.PLC",
            "remediation": "rebuild tracks/accounts",
        },
        {
            "invariant_id": "pl_absent",
            "severity": "fatal",
            "metric": "accounts.list",
            "comparator": "not_contains",
            "target": "product.Yield.managed.PL",
            "remediation": "check account filtering policy",
        },
    ]
    metrics = {
        "accounts.list": [
            "product.Yield.managed.PLC",
            "product.Yield.managed.Total",
        ]
    }
    results = evaluate_invariants(invariants=invariants, metrics=metrics)

    assert results[0].status == "pass"
    assert results[1].status == "pass"


def test_build_species_account_policy_invariants_emits_fatal_policy_checks() -> None:
    invariants = build_species_account_policy_invariants(
        {
            "required_present": [
                "product.Yield.managed.PLC",
                "product.Yield.managed.PLC",
            ],
            "expected_absent": ["product.Yield.managed.PL"],
        }
    )
    assert len(invariants) == 2
    assert invariants[0]["comparator"] == "contains"
    assert invariants[0]["target"] == "product.Yield.managed.PLC"
    assert invariants[1]["comparator"] == "not_contains"
    assert invariants[1]["target"] == "product.Yield.managed.PL"


def test_build_species_account_policy_invariants_supports_nonzero_policy() -> None:
    invariants = build_species_account_policy_invariants(
        {
            "required_nonzero": [
                "product.Yield.managed.PLC",
                "product.HarvestedVolume.managed.PLC.CC",
            ],
            "expected_zero": ["product.Yield.managed.PL"],
        }
    )
    assert len(invariants) == 3
    assert invariants[0]["metric"] == "products.nonzero_labels"
    assert invariants[0]["comparator"] == "contains"
    assert invariants[0]["target"] == "product.Yield.managed.PLC"
    assert invariants[1]["metric"] == "products.nonzero_labels"
    assert invariants[1]["comparator"] == "contains"
    assert invariants[1]["target"] == "product.HarvestedVolume.managed.PLC.CC"
    assert invariants[2]["metric"] == "products.nonzero_labels"
    assert invariants[2]["comparator"] == "not_contains"
    assert invariants[2]["target"] == "product.Yield.managed.PL"
