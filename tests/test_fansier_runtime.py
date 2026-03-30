from __future__ import annotations

import json
from pathlib import Path

from femic.fansier_runtime import (
    FansierBatchRunResult,
    _build_fansier_batch_manifest_payload,
    parse_fansier_calculation_counts,
)


def test_parse_fansier_calculation_counts_handles_commas() -> None:
    counts = parse_fansier_calculation_counts(
        "1 Regimes X 1 Assumptions X 6 Products X 300 Ages = 1,800 calculations"
    )

    assert counts is not None
    assert counts.regimes == 1
    assert counts.settings == 1
    assert counts.products == 6
    assert counts.ages == 300
    assert counts.calculations == 1800


def test_parse_fansier_calculation_counts_returns_none_for_nonmatch() -> None:
    assert parse_fansier_calculation_counts("status Done") is None


def test_build_fansier_batch_manifest_payload_includes_outputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "fansier"
    output_dir.mkdir()
    first_output = output_dir / "demo.txt"
    first_output.write_text("Results\n", encoding="utf-8")
    manifest_path = tmp_path / "fansier_manifest.json"
    result = FansierBatchRunResult(
        run_id="demo",
        fansier_exe_path=Path("C:/Program Files/TIPSY 4.7/Fansier/Fansier.exe"),
        rgm_path=Path("C:/tmp/demo.rgm"),
        output_dir=output_dir,
        report_type="txt",
        long_report=True,
        product_cols=True,
        activity_cols=False,
        discount_name="FEMIC Raw 0%",
        product_count=6,
        age_count=300,
        calculations=1800,
        first_output_path=first_output,
        output_files=(first_output,),
        manifest_path=manifest_path,
        status_label="Done",
    )

    payload = _build_fansier_batch_manifest_payload(result=result)

    assert payload["run_id"] == "demo"
    assert payload["inputs"]["discount_name"] == "FEMIC Raw 0%"
    assert payload["outputs"]["output_file_count"] == 1
    assert payload["outputs"]["calculations"] == 1800
    assert payload["outputs"]["status_label"] == "Done"
    assert payload["outputs"]["first_output_path"] == str(first_output)
    json.dumps(payload)
