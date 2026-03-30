from __future__ import annotations

from pathlib import Path

import pytest

from femic.fansier_reporting import FansierBatchParseResult
from femic.fansier_runtime import FansierBatchRunResult
from femic.fansier_workflow import (
    FansierWorkflowError,
    run_fansier_batch_and_parse,
)


def test_run_fansier_batch_and_parse_uses_run_scoped_txt_glob(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_out_dir = tmp_path / "batch"
    parsed_out_dir = tmp_path / "parsed"
    batch_result = FansierBatchRunResult(
        run_id="demo",
        fansier_exe_path=Path("Fansier.exe"),
        rgm_path=Path("demo.rgm"),
        output_dir=batch_out_dir,
        report_type="txt",
        long_report=True,
        product_cols=True,
        activity_cols=False,
        discount_name="FEMIC Raw 0%",
        product_count=6,
        age_count=300,
        calculations=1800,
        first_output_path=batch_out_dir / "demo.txt",
        output_files=(batch_out_dir / "demo.txt",),
        manifest_path=tmp_path / "batch_manifest.json",
        status_label="done",
    )
    parse_result = FansierBatchParseResult(
        report_dir=batch_out_dir,
        out_dir=parsed_out_dir,
        report_count=1,
        calculation_summary_path=parsed_out_dir / "calculation_summary.csv",
        harvest_summary_path=parsed_out_dir / "harvest_summary.csv",
        cost_lines_path=parsed_out_dir / "cost_lines.csv",
        product_price_factors_path=parsed_out_dir / "product_price_factors.csv",
        benefit_lines_path=parsed_out_dir / "benefit_lines.csv",
        manifest_path=parsed_out_dir / "manifest.json",
        calculation_summary_rows=1,
        harvest_summary_rows=1,
        cost_line_rows=1,
        product_price_factor_rows=1,
        benefit_line_rows=1,
    )
    calls: dict[str, object] = {}

    def _fake_run_fansier_batch(**kwargs):
        calls["batch_kwargs"] = kwargs
        return batch_result

    def _fake_parse_fansier_batch_output_dir(**kwargs):
        calls["parse_kwargs"] = kwargs
        return parse_result

    monkeypatch.setattr(
        "femic.fansier_workflow.run_fansier_batch", _fake_run_fansier_batch
    )
    monkeypatch.setattr(
        "femic.fansier_workflow.parse_fansier_batch_output_dir",
        _fake_parse_fansier_batch_output_dir,
    )

    result = run_fansier_batch_and_parse(
        rgm_path=Path("demo.rgm"),
        out_dir=batch_out_dir,
        parsed_out_dir=parsed_out_dir,
        log_dir=tmp_path / "logs",
        run_id="demo",
        fansier_exe_path=Path("Fansier.exe"),
        discount_name="FEMIC Raw 0%",
        discount_dis_path=Path("demo.dis"),
        report_type="txt",
        long_report=True,
        product_cols=True,
        activity_cols=False,
        select_all_products=True,
        select_all_ages=True,
        product_name="Logs",
        age_name="10.00",
    )

    assert result.batch_result == batch_result
    assert result.parse_result == parse_result
    assert calls["parse_kwargs"] == {
        "report_dir": batch_out_dir,
        "out_dir": parsed_out_dir,
        "report_glob": "demo*.txt",
    }


def test_run_fansier_batch_and_parse_rejects_non_txt_reports(tmp_path: Path) -> None:
    with pytest.raises(FansierWorkflowError):
        run_fansier_batch_and_parse(
            rgm_path=Path("demo.rgm"),
            out_dir=tmp_path / "batch",
            parsed_out_dir=tmp_path / "parsed",
            log_dir=tmp_path / "logs",
            run_id="demo",
            fansier_exe_path=Path("Fansier.exe"),
            discount_name="FEMIC Raw 0%",
            discount_dis_path=None,
            report_type="csv",
            long_report=True,
            product_cols=True,
            activity_cols=False,
            select_all_products=True,
            select_all_ages=True,
            product_name="Logs",
            age_name="10.00",
        )
