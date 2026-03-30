from __future__ import annotations

import csv
import math
from pathlib import Path

from femic.fansier_reporting import (
    parse_fansier_batch_output_dir,
    parse_fansier_batch_report,
)


_SAMPLE_REPORT = """Results
Regime File:\tBatchbiomass-10000.rgm
Program Version:\t 2.03
Calculation Date:\t3/29/2026 5:49 PM
Products:\tLumber & Mill Residues (All Grades)
Final Harvest Age (yrs):\t170.0
Base Year (yrs):\t0.0
Discounted Benefits ($/ha):\t96,347
Discounted Costs ($/ha):\t-29,179
NPV ($/ha):\t67,168
Site Value ($/ha):\t∞
IRR (%):\t2.433


Harvest Summary
Harvest\tAge (yrs)\tMerch. Volume (m³/ha)\tUndiscounted Benefit ($/ha)\tDiscounted Benefit ($/ha)
Final Harvest\t170\t268.3\t96,347\t96,347


Discount Assumptions
Name:\tFEMIC Raw 0%
Discount Rate (%):\t0.0
Reinvestment Rate (%):\t0.0
Analysis Base Age (yrs):\t0
Real Price Increase (%):\t0.0
Real Cost Increase (%):\t0.0
Real Increase Duration (yrs):\t0
Financial (Inc. Tax):\tno
Include Sunk Costs:\tno
Deflation Rate (%):\tn/a
Regen. Costs:\tStand Establishment
(All revenues and costs are in constant 2006 Canadian dollars)


Costs
Silviculture Treatment Costs\tMethod\tYear\tUndiscounted Cost ($/ha)\tDiscounted Cost ($/ha)
Survey & Prescription\tRegional Average\t0.0\t18\t18
Site Preparation\tDistrict Average\t0.0\t666\t666
Planting (1)\tPlanting Function\t0.0\t463\t463
Total\t\t\t1,147\t1,147

Road and Infrastructure Costs\tMethod\tYear\tUndiscounted Cost ($/ha)\tDiscounted Cost ($/ha)
Roads and Infrastructure\tDistrict Average\t170.0\t888\t888
Total\t\t\t888\t888

Benefits
Lumber & Mill Residues (All Grades)
Product Price Adjustment Factors
LumberSS\t1.00
Mill Residues\t1.00

Final Harvest (age 170)
LumberSS\tProduct\tQuantity (mbf/ha)\tRate ($/mbf)\tUndiscounted Benefit ($/ha)\tDiscounted Benefit ($/ha)
Interior Douglas Fir\t2x4\t5.8\t644.67\t3,747\t
\tTotal\t36.4\t\t23,787\t23,787

Mill Residues\tProduct\tQuantity (odt/ha)\tRate ($/odt)\tUndiscounted Benefit ($/ha)\tDiscounted Benefit ($/ha)
Interior Douglas Fir\tChips\t77.6\t120.00\t9,307\t
\tTotal\t165.0\t\t11,931\t11,931

Grand Total\t\t\t\t96,347\t96,347
"""


def test_parse_fansier_batch_report_normalizes_long_report_sections(
    tmp_path: Path,
) -> None:
    report_path = (
        tmp_path
        / "cli_smoke_all - Batchbiomass-10000.rgm - {defaults} - FEMIC Raw 0% - "
        "Lumber & Mill Residues (All Grades) - 170.00.txt"
    )
    report_path.write_text(_SAMPLE_REPORT, encoding="utf-8")

    parsed = parse_fansier_batch_report(report_path)

    assert parsed.metadata.run_id == "cli_smoke_all"
    assert parsed.metadata.regime_file == "Batchbiomass-10000.rgm"
    assert parsed.calculation_summary["discounted_benefits_$_per_ha"] == 96347
    assert math.isinf(parsed.calculation_summary["site_value_$_per_ha"])
    assert parsed.calculation_summary["deflation_rate_%"] is None
    assert parsed.harvest_summary_rows[0]["harvest"] == "Final Harvest"
    assert parsed.harvest_summary_rows[0]["discounted_benefit_$_per_ha"] == 96347
    assert parsed.cost_line_rows[0]["cost_table_name"] == "Silviculture Treatment Costs"
    assert parsed.cost_line_rows[0]["undiscounted_cost_$_per_ha"] == 18
    assert parsed.product_price_factor_rows[0]["factor_name"] == "LumberSS"
    assert parsed.product_price_factor_rows[0]["factor_value"] == 1.0
    assert parsed.benefit_line_rows[0]["benefit_stage"] == "Final Harvest (age 170)"
    assert parsed.benefit_line_rows[0]["benefit_family"] == "LumberSS"
    assert parsed.benefit_line_rows[-1]["benefit_family"] == "Grand Total"
    assert parsed.benefit_line_rows[-1]["undiscounted_benefit_$_per_ha"] == 96347


def test_parse_fansier_batch_output_dir_writes_normalized_csvs(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    report_path = (
        report_dir
        / "cli_smoke_all - Batchbiomass-10000.rgm - {defaults} - FEMIC Raw 0% - "
        "Lumber & Mill Residues (All Grades) - 170.00.txt"
    )
    report_path.write_text(_SAMPLE_REPORT, encoding="utf-8")
    out_dir = tmp_path / "parsed"

    result = parse_fansier_batch_output_dir(report_dir=report_dir, out_dir=out_dir)

    assert result.report_count == 1
    assert result.calculation_summary_rows == 1
    assert result.harvest_summary_rows == 1
    assert result.cost_line_rows == 6
    assert result.product_price_factor_rows == 2
    assert result.benefit_line_rows == 5
    assert result.manifest_path.exists()

    with result.calculation_summary_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["run_id"] == "cli_smoke_all"
    assert rows[0]["discount_name"] == "FEMIC Raw 0%"

    with result.benefit_lines_path.open(encoding="utf-8", newline="") as handle:
        benefit_rows = list(csv.DictReader(handle))
    assert benefit_rows[0]["benefit_family"] == "LumberSS"
    assert benefit_rows[-1]["benefit_family"] == "Grand Total"
