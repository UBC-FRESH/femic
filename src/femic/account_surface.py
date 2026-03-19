"""Helpers for summarizing Patchworks account/target coverage surfaces."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

_YIELD_SPECIES_PATTERN = re.compile(r"^product\.Yield\.managed\.([^.]+)$")
_HARVEST_SPECIES_PATTERN = re.compile(
    r"^product\.HarvestedVolume\.managed\.([^.]+)\.CC$"
)
_FEATURE_SERAL_PATTERN = re.compile(r"^feature\.Seral\.([^.]+)\.([^.]+)$")
_PRODUCT_SERAL_PATTERN = re.compile(r"^product\.Seral\.area\.([^.]+)\.([^.]+)\.CC$")
_TOTAL_YIELD_LABEL = "product.Yield.managed.Total"
_TOTAL_HARVEST_LABEL = "product.HarvestedVolume.managed.Total.CC"


def summarize_account_surface(
    accounts_csv_path: Path,
    *,
    products_csv_path: Path | None = None,
    curves_csv_path: Path | None = None,
) -> dict[str, Any]:
    """Build species/AU account coverage summary from tracks/accounts.csv."""
    accounts: set[str] = set()
    with accounts_csv_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            account = str(row.get("ACCOUNT", "")).strip()
            if account:
                accounts.add(account)

    species_summary: dict[str, dict[str, Any]] = {}
    au_summary: dict[str, dict[str, Any]] = {}
    for account in sorted(accounts):
        yield_match = _YIELD_SPECIES_PATTERN.match(account)
        if yield_match:
            species = yield_match.group(1)
            item = species_summary.setdefault(
                species,
                {"yield_account_present": False, "harvest_cc_account_present": False},
            )
            item["yield_account_present"] = True
            continue

        harvest_match = _HARVEST_SPECIES_PATTERN.match(account)
        if harvest_match:
            species = harvest_match.group(1)
            item = species_summary.setdefault(
                species,
                {"yield_account_present": False, "harvest_cc_account_present": False},
            )
            item["harvest_cc_account_present"] = True
            continue

        feature_seral_match = _FEATURE_SERAL_PATTERN.match(account)
        if feature_seral_match:
            au = feature_seral_match.group(1)
            stage = feature_seral_match.group(2)
            item = au_summary.setdefault(
                au,
                {
                    "feature_seral_stages": [],
                    "product_seral_cc_stages": [],
                    "feature_seral_count": 0,
                    "product_seral_cc_count": 0,
                },
            )
            stages = item["feature_seral_stages"]
            if stage not in stages:
                stages.append(stage)
            continue

        product_seral_match = _PRODUCT_SERAL_PATTERN.match(account)
        if product_seral_match:
            stage = product_seral_match.group(1)
            au = product_seral_match.group(2)
            item = au_summary.setdefault(
                au,
                {
                    "feature_seral_stages": [],
                    "product_seral_cc_stages": [],
                    "feature_seral_count": 0,
                    "product_seral_cc_count": 0,
                },
            )
            stages = item["product_seral_cc_stages"]
            if stage not in stages:
                stages.append(stage)

    complete_species = 0
    missing_yield: list[str] = []
    missing_harvest_cc: list[str] = []
    for species in sorted(species_summary):
        row = species_summary[species]
        if row["yield_account_present"] and row["harvest_cc_account_present"]:
            complete_species += 1
        if not row["yield_account_present"]:
            missing_yield.append(species)
        if not row["harvest_cc_account_present"]:
            missing_harvest_cc.append(species)

    for au in sorted(au_summary):
        item = au_summary[au]
        item["feature_seral_stages"] = sorted(item["feature_seral_stages"])
        item["product_seral_cc_stages"] = sorted(item["product_seral_cc_stages"])
        item["feature_seral_count"] = len(item["feature_seral_stages"])
        item["product_seral_cc_count"] = len(item["product_seral_cc_stages"])

    nonzero_labels = _nonzero_product_labels(
        products_csv_path=products_csv_path,
        curves_csv_path=curves_csv_path,
    )
    nonzero_species_yield: list[str] | None = None
    nonzero_species_harvest: list[str] | None = None
    total_nonzero_from_products: bool | None = None
    if nonzero_labels is not None:
        nonzero_species_yield = []
        nonzero_species_harvest = []
        for label in nonzero_labels:
            yield_match = _YIELD_SPECIES_PATTERN.match(label)
            if yield_match:
                species = yield_match.group(1)
                if species != "Total" and species not in nonzero_species_yield:
                    nonzero_species_yield.append(species)
                continue
            harvest_match = _HARVEST_SPECIES_PATTERN.match(label)
            if harvest_match:
                species = harvest_match.group(1)
                if species != "Total" and species not in nonzero_species_harvest:
                    nonzero_species_harvest.append(species)
        total_nonzero_from_products = (
            _TOTAL_YIELD_LABEL in nonzero_labels
            or _TOTAL_HARVEST_LABEL in nonzero_labels
        )

    has_total_accounts = (
        _TOTAL_YIELD_LABEL in accounts or _TOTAL_HARVEST_LABEL in accounts
    )
    species_account_surface_present = len(species_summary) > 0
    species_nonzero_present = (
        None
        if nonzero_labels is None
        else bool(nonzero_species_yield or nonzero_species_harvest)
    )
    total_ok_species_empty_signature = (
        bool(total_nonzero_from_products)
        and species_nonzero_present is not None
        and not species_nonzero_present
    ) or (
        nonzero_labels is None
        and has_total_accounts
        and not species_account_surface_present
    )

    return {
        "accounts_path": str(accounts_csv_path),
        "total_accounts": len(accounts),
        "target_count_inferred": len(accounts),
        "species_count": len(species_summary),
        "species_complete_count": complete_species,
        "species_missing_yield": missing_yield,
        "species_missing_harvest_cc": missing_harvest_cc,
        "species": species_summary,
        "nonzero_labels": nonzero_labels,
        "nonzero_species_yield": nonzero_species_yield,
        "nonzero_species_harvest_cc": nonzero_species_harvest,
        "au_count": len(au_summary),
        "au": au_summary,
        "diagnosis": {
            "has_total_accounts": has_total_accounts,
            "total_nonzero_from_products": total_nonzero_from_products,
            "species_account_surface_present": species_account_surface_present,
            "species_nonzero_present": species_nonzero_present,
            "total_ok_species_empty_signature": total_ok_species_empty_signature,
            "recommended_next_checks": _recommended_next_checks(
                total_ok_species_empty_signature=total_ok_species_empty_signature,
                has_products_signal=(nonzero_labels is not None),
            ),
        },
    }


def _recommended_next_checks(
    *,
    total_ok_species_empty_signature: bool,
    has_products_signal: bool,
) -> list[str]:
    if not total_ok_species_empty_signature:
        return []
    checks = [
        "Run `femic instance account-surface --output <path>` and archive JSON evidence.",
        "Verify `tracks/products.csv` contains species labels and nonzero curve mappings.",
        "Verify `tracks/curves.csv` has nonzero Y values for expected managed species curves.",
        "Inspect matrix-build manifest `accounts_sync.excluded_patterns` for overly broad regex filters.",
        "Re-run `femic instance rebuild --with-patchworks` and confirm fatal species policy invariants.",
    ]
    if not has_products_signal:
        checks.insert(
            1,
            "Ensure `tracks/products.csv` and `tracks/curves.csv` exist (re-run matrix build if missing).",
        )
    return checks


def _nonzero_product_labels(
    *,
    products_csv_path: Path | None,
    curves_csv_path: Path | None,
) -> list[str] | None:
    if products_csv_path is None or curves_csv_path is None:
        return None
    if not products_csv_path.exists() or not curves_csv_path.exists():
        return None
    curve_max: dict[str, float] = {}
    with curves_csv_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            curve_id = str(row.get("CURVE", "")).strip()
            if not curve_id:
                continue
            try:
                value = float(row.get("Y", "0") or 0.0)
            except (TypeError, ValueError):
                continue
            previous = curve_max.get(curve_id)
            curve_max[curve_id] = value if previous is None else max(previous, value)
    label_max: dict[str, float] = {}
    with products_csv_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            label = str(row.get("LABEL", "")).strip()
            curve_id = str(row.get("CURVE", "")).strip()
            if not label or not curve_id:
                continue
            value = curve_max.get(curve_id, 0.0)
            previous = label_max.get(label)
            label_max[label] = value if previous is None else max(previous, value)
    return sorted(label for label, value in label_max.items() if value > 0.0)
