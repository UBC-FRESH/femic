"""Higher-level FAN$IER extraction workflows built from tracked seams."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from femic.fansier_reporting import (
    DEFAULT_FANSIER_PARSED_OUTPUT_DIR,
    FansierBatchParseResult,
    parse_fansier_batch_output_dir,
)
from femic.fansier_runtime import FansierBatchRunResult, run_fansier_batch


class FansierWorkflowError(RuntimeError):
    """Raised when a composed FAN$IER workflow cannot be completed."""


@dataclass(frozen=True)
class FansierBatchParseWorkflowResult:
    """Outputs from one FAN$IER batch-run plus parse workflow."""

    batch_result: FansierBatchRunResult
    parse_result: FansierBatchParseResult


def run_fansier_batch_and_parse(
    *,
    rgm_path: Path,
    out_dir: Path,
    log_dir: Path,
    run_id: str,
    parsed_out_dir: Path = DEFAULT_FANSIER_PARSED_OUTPUT_DIR,
    fansier_exe_path: Path,
    discount_name: str,
    discount_dis_path: Path | None,
    report_type: str,
    long_report: bool,
    product_cols: bool,
    activity_cols: bool,
    select_all_products: bool,
    select_all_ages: bool,
    product_name: str,
    age_name: str,
) -> FansierBatchParseWorkflowResult:
    """Run unattended FAN$IER extraction, then normalize the resulting text reports."""

    if report_type.lower() != "txt":
        raise FansierWorkflowError(
            "run_fansier_batch_and_parse currently supports only report_type='txt'."
        )

    batch_result = run_fansier_batch(
        rgm_path=rgm_path,
        out_dir=out_dir,
        log_dir=log_dir,
        run_id=run_id,
        fansier_exe_path=fansier_exe_path,
        discount_name=discount_name,
        discount_dis_path=discount_dis_path,
        report_type=report_type,
        long_report=long_report,
        product_cols=product_cols,
        activity_cols=activity_cols,
        select_all_products=select_all_products,
        select_all_ages=select_all_ages,
        product_name=product_name,
        age_name=age_name,
    )
    parse_result = parse_fansier_batch_output_dir(
        report_dir=batch_result.output_dir,
        out_dir=parsed_out_dir,
        report_glob=f"{run_id}*.txt",
    )
    return FansierBatchParseWorkflowResult(
        batch_result=batch_result,
        parse_result=parse_result,
    )
