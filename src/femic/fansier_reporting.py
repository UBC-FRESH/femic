"""Parse FAN$IER batch text reports into structured FEMIC-owned tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import csv
import json
import math
from pathlib import Path
import re
from typing import Any


DEFAULT_FANSIER_PARSED_OUTPUT_DIR = Path("tipsy_io/logs/fansier_parsed")
_NUMERIC_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")


class FansierReportParseError(RuntimeError):
    """Raised when a FAN$IER batch report cannot be parsed safely."""


@dataclass(frozen=True)
class FansierReportMetadata:
    """Filename-derived metadata for one FAN$IER batch report."""

    source_report_path: Path
    run_id: str | None
    regime_file: str | None
    settings_label: str | None
    discount_name: str | None
    selected_product_group: str | None
    selected_harvest_age: str | None


@dataclass(frozen=True)
class FansierParsedReport:
    """Structured rows parsed from one FAN$IER long-report text file."""

    metadata: FansierReportMetadata
    calculation_summary: dict[str, Any]
    harvest_summary_rows: tuple[dict[str, Any], ...]
    cost_line_rows: tuple[dict[str, Any], ...]
    product_price_factor_rows: tuple[dict[str, Any], ...]
    benefit_line_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class FansierBatchParseResult:
    """Paths and row counts for one parsed FAN$IER batch-output directory."""

    report_dir: Path
    out_dir: Path
    report_count: int
    calculation_summary_path: Path
    harvest_summary_path: Path
    cost_lines_path: Path
    product_price_factors_path: Path
    benefit_lines_path: Path
    manifest_path: Path
    calculation_summary_rows: int
    harvest_summary_rows: int
    cost_line_rows: int
    product_price_factor_rows: int
    benefit_line_rows: int


def _normalize_scalar(value: str) -> Any:
    stripped = value.strip()
    if stripped == "":
        return None
    lowered = stripped.lower()
    if lowered in {"n/a", "n/c"}:
        return None
    if stripped in {"∞", "âˆž"}:
        return math.inf
    if stripped in {"-∞", "-âˆž"}:
        return -math.inf
    numeric_candidate = stripped.replace(",", "")
    if _NUMERIC_RE.fullmatch(numeric_candidate):
        if "." in numeric_candidate:
            return float(numeric_candidate)
        return int(numeric_candidate)
    return stripped


def _normalize_key(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace(" ", "_")
    normalized = normalized.replace("(", "").replace(")", "")
    normalized = normalized.replace("/", "_per_")
    normalized = normalized.replace(".", "")
    return normalized


def _split_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in lines:
        line = raw.rstrip("\r")
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _parse_filename_metadata(path: Path) -> FansierReportMetadata:
    parts = path.stem.rsplit(" - ", 5)
    if len(parts) == 6:
        (
            run_id,
            regime_file,
            settings_label,
            discount_name,
            product_group,
            harvest_age,
        ) = parts
        return FansierReportMetadata(
            source_report_path=path,
            run_id=run_id,
            regime_file=regime_file,
            settings_label=settings_label,
            discount_name=discount_name,
            selected_product_group=product_group,
            selected_harvest_age=harvest_age,
        )
    return FansierReportMetadata(
        source_report_path=path,
        run_id=None,
        regime_file=None,
        settings_label=None,
        discount_name=None,
        selected_product_group=None,
        selected_harvest_age=None,
    )


def _row_with_metadata(
    metadata: FansierReportMetadata,
    row: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_report_path": str(metadata.source_report_path),
        "run_id": metadata.run_id,
        "regime_file": metadata.regime_file,
        "settings_label": metadata.settings_label,
        "discount_name": metadata.discount_name,
        "selected_product_group": metadata.selected_product_group,
        "selected_harvest_age": metadata.selected_harvest_age,
        **row,
    }


def _parse_key_value_lines(lines: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[_normalize_key(key)] = _normalize_scalar(value)
    return parsed


def _parse_table_block(
    *,
    title: str,
    header_line: str,
    data_lines: list[str],
    metadata: FansierReportMetadata,
    extra_fields: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    header_cells = [cell.strip() for cell in header_line.split("\t")]
    value_headers = header_cells[1:]
    rows: list[dict[str, Any]] = []
    for line in data_lines:
        cells = [cell.strip() for cell in line.split("\t")]
        if len(cells) < len(header_cells):
            cells.extend([""] * (len(header_cells) - len(cells)))
        row = {_normalize_key(title): _normalize_scalar(cells[0])}
        for header, value in zip(value_headers, cells[1:], strict=False):
            row[_normalize_key(header)] = _normalize_scalar(value)
        if extra_fields:
            row.update(extra_fields)
        rows.append(_row_with_metadata(metadata, row))
    return rows


def _is_cost_header(line: str) -> bool:
    if "\t" not in line or "Undiscounted Cost" not in line:
        return False
    table_title = line.split("\t", 1)[0].strip()
    return table_title.endswith("Costs") or table_title == "Final Harvest"


def parse_fansier_batch_report(report_path: Path) -> FansierParsedReport:
    """Parse one FAN$IER long-report text file into normalized row groups."""

    path = report_path.expanduser().resolve()
    if path.suffix.lower() != ".txt":
        raise FansierReportParseError(
            f"Only .txt FAN$IER batch reports are supported: {path}"
        )

    blocks = _split_blocks(path.read_text(encoding="utf-8-sig").splitlines())
    if not blocks or blocks[0][0].lstrip("\ufeff") != "Results":
        raise FansierReportParseError(f"Expected 'Results' header in {path}")

    metadata = _parse_filename_metadata(path)
    calculation_summary = _row_with_metadata(
        metadata, _parse_key_value_lines(blocks[0][1:])
    )

    harvest_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []
    factor_rows: list[dict[str, Any]] = []
    benefit_rows: list[dict[str, Any]] = []
    current_benefit_stage: str | None = None
    last_benefit_header: str | None = None
    pending_benefits_intro = False

    for block in blocks[1:]:
        first = block[0]

        if first == "Harvest Summary":
            harvest_rows.extend(
                _parse_table_block(
                    title="harvest",
                    header_line=block[1],
                    data_lines=block[2:],
                    metadata=metadata,
                )
            )
            continue

        if first == "Discount Assumptions":
            calculation_summary.update(_parse_key_value_lines(block[1:]))
            continue

        if first == "Jobs":
            calculation_summary["jobs_note"] = " ".join(
                part.strip() for part in block[1:]
            )
            continue

        if first == "Benefits":
            if "Product Price Adjustment Factors" in block:
                calculation_summary["benefits_group_name"] = _normalize_scalar(block[1])
                start = block.index("Product Price Adjustment Factors") + 1
                for line in block[start:]:
                    cells = [cell.strip() for cell in line.split("\t")]
                    if len(cells) != 2:
                        continue
                    factor_rows.append(
                        _row_with_metadata(
                            metadata,
                            {
                                "factor_name": _normalize_scalar(cells[0]),
                                "factor_value": _normalize_scalar(cells[1]),
                            },
                        )
                    )
                continue
            pending_benefits_intro = True
            continue

        if pending_benefits_intro and "Product Price Adjustment Factors" in block:
            calculation_summary["benefits_group_name"] = _normalize_scalar(block[0])
            start = block.index("Product Price Adjustment Factors") + 1
            for line in block[start:]:
                cells = [cell.strip() for cell in line.split("\t")]
                if len(cells) != 2:
                    continue
                factor_rows.append(
                    _row_with_metadata(
                        metadata,
                        {
                            "factor_name": _normalize_scalar(cells[0]),
                            "factor_value": _normalize_scalar(cells[1]),
                        },
                    )
                )
            pending_benefits_intro = False
            continue

        if first == "Costs" or _is_cost_header(first):
            header_line = block[1] if first == "Costs" else block[0]
            data_lines = block[2:] if first == "Costs" else block[1:]
            table_title = header_line.split("\t", 1)[0].strip()
            cost_rows.extend(
                _parse_table_block(
                    title="cost_group",
                    header_line=header_line,
                    data_lines=data_lines,
                    metadata=metadata,
                    extra_fields={"cost_table_name": table_title},
                )
            )
            continue

        if "\t" not in first:
            current_benefit_stage = first
            if len(block) == 1:
                continue
            last_benefit_header = block[1]
            benefit_family = last_benefit_header.split("\t", 1)[0].strip()
            benefit_rows.extend(
                _parse_table_block(
                    title="species_group",
                    header_line=last_benefit_header,
                    data_lines=block[2:],
                    metadata=metadata,
                    extra_fields={
                        "benefit_stage": current_benefit_stage,
                        "benefit_family": benefit_family,
                    },
                )
            )
            continue

        if first.startswith("Grand Total\t") and last_benefit_header is not None:
            benefit_rows.extend(
                _parse_table_block(
                    title="species_group",
                    header_line=last_benefit_header,
                    data_lines=block,
                    metadata=metadata,
                    extra_fields={
                        "benefit_stage": current_benefit_stage,
                        "benefit_family": "Grand Total",
                    },
                )
            )
            continue

        if "\t" in first:
            last_benefit_header = first
            benefit_family = first.split("\t", 1)[0].strip()
            benefit_rows.extend(
                _parse_table_block(
                    title="species_group",
                    header_line=first,
                    data_lines=block[1:],
                    metadata=metadata,
                    extra_fields={
                        "benefit_stage": current_benefit_stage,
                        "benefit_family": benefit_family,
                    },
                )
            )

    return FansierParsedReport(
        metadata=metadata,
        calculation_summary=calculation_summary,
        harvest_summary_rows=tuple(harvest_rows),
        cost_line_rows=tuple(cost_rows),
        product_price_factor_rows=tuple(factor_rows),
        benefit_line_rows=tuple(benefit_rows),
    )


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def parse_fansier_batch_output_dir(
    *,
    report_dir: Path,
    out_dir: Path = DEFAULT_FANSIER_PARSED_OUTPUT_DIR,
    report_glob: str = "*.txt",
) -> FansierBatchParseResult:
    """Parse a directory of FAN$IER batch text reports into normalized CSV tables."""

    resolved_report_dir = report_dir.expanduser().resolve()
    resolved_out_dir = out_dir.expanduser().resolve()
    report_paths = sorted(
        path for path in resolved_report_dir.glob(report_glob) if path.is_file()
    )
    if not report_paths:
        raise FansierReportParseError(
            f"No FAN$IER report files matched {report_glob!r} under {resolved_report_dir}"
        )

    calculation_rows: list[dict[str, Any]] = []
    harvest_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []
    factor_rows: list[dict[str, Any]] = []
    benefit_rows: list[dict[str, Any]] = []

    for report_path in report_paths:
        parsed = parse_fansier_batch_report(report_path)
        calculation_rows.append(parsed.calculation_summary)
        harvest_rows.extend(parsed.harvest_summary_rows)
        cost_rows.extend(parsed.cost_line_rows)
        factor_rows.extend(parsed.product_price_factor_rows)
        benefit_rows.extend(parsed.benefit_line_rows)

    calculation_summary_path = resolved_out_dir / "calculation_summary.csv"
    harvest_summary_path = resolved_out_dir / "harvest_summary.csv"
    cost_lines_path = resolved_out_dir / "cost_lines.csv"
    product_price_factors_path = resolved_out_dir / "product_price_factors.csv"
    benefit_lines_path = resolved_out_dir / "benefit_lines.csv"
    manifest_path = resolved_out_dir / "fansier_batch_parse_manifest.json"

    _write_rows_csv(calculation_summary_path, calculation_rows)
    _write_rows_csv(harvest_summary_path, harvest_rows)
    _write_rows_csv(cost_lines_path, cost_rows)
    _write_rows_csv(product_price_factors_path, factor_rows)
    _write_rows_csv(benefit_lines_path, benefit_rows)

    result = FansierBatchParseResult(
        report_dir=resolved_report_dir,
        out_dir=resolved_out_dir,
        report_count=len(report_paths),
        calculation_summary_path=calculation_summary_path,
        harvest_summary_path=harvest_summary_path,
        cost_lines_path=cost_lines_path,
        product_price_factors_path=product_price_factors_path,
        benefit_lines_path=benefit_lines_path,
        manifest_path=manifest_path,
        calculation_summary_rows=len(calculation_rows),
        harvest_summary_rows=len(harvest_rows),
        cost_line_rows=len(cost_rows),
        product_price_factor_rows=len(factor_rows),
        benefit_line_rows=len(benefit_rows),
    )
    manifest_path.write_text(
        json.dumps(
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "mode": "fansier_batch_parse",
                "inputs": {
                    "report_dir": str(resolved_report_dir),
                    "report_glob": report_glob,
                },
                "outputs": {
                    "out_dir": str(resolved_out_dir),
                    "report_count": result.report_count,
                    "calculation_summary_path": str(result.calculation_summary_path),
                    "harvest_summary_path": str(result.harvest_summary_path),
                    "cost_lines_path": str(result.cost_lines_path),
                    "product_price_factors_path": str(
                        result.product_price_factors_path
                    ),
                    "benefit_lines_path": str(result.benefit_lines_path),
                    "calculation_summary_rows": result.calculation_summary_rows,
                    "harvest_summary_rows": result.harvest_summary_rows,
                    "cost_line_rows": result.cost_line_rows,
                    "product_price_factor_rows": result.product_price_factor_rows,
                    "benefit_line_rows": result.benefit_line_rows,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return result
