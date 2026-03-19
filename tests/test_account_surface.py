from __future__ import annotations

from pathlib import Path

from femic.account_surface import summarize_account_surface


def test_summarize_account_surface_extracts_species_and_au_coverage(
    tmp_path: Path,
) -> None:
    accounts_csv = tmp_path / "accounts.csv"
    accounts_csv.write_text(
        "GROUP,ATTRIBUTE,ACCOUNT,SUM\n"
        "_MANAGED_,x,product.Yield.managed.CW,1\n"
        "_MANAGED_,x,product.HarvestedVolume.managed.CW.CC,1\n"
        "_MANAGED_,x,product.Yield.managed.PL,1\n"
        "_MANAGED_,x,feature.Seral.985501000.regenerating,1\n"
        "_MANAGED_,x,feature.Seral.985501000.mature,1\n"
        "_MANAGED_,x,product.Seral.area.regenerating.985501000.CC,1\n",
        encoding="utf-8",
    )

    summary = summarize_account_surface(accounts_csv_path=accounts_csv)

    assert summary["total_accounts"] == 6
    assert summary["target_count_inferred"] == 6
    assert summary["species_count"] == 2
    assert summary["species_complete_count"] == 1
    assert summary["species_missing_harvest_cc"] == ["PL"]
    assert summary["species"]["CW"]["yield_account_present"] is True
    assert summary["species"]["CW"]["harvest_cc_account_present"] is True
    assert summary["au_count"] == 1
    assert summary["au"]["985501000"]["feature_seral_count"] == 2
    assert summary["au"]["985501000"]["product_seral_cc_count"] == 1


def test_summarize_account_surface_flags_total_ok_species_empty_signature(
    tmp_path: Path,
) -> None:
    accounts_csv = tmp_path / "accounts.csv"
    products_csv = tmp_path / "products.csv"
    curves_csv = tmp_path / "curves.csv"
    accounts_csv.write_text(
        "GROUP,ATTRIBUTE,ACCOUNT,SUM\n"
        "_MANAGED_,x,product.Yield.managed.Total,1\n"
        "_MANAGED_,x,product.HarvestedVolume.managed.Total.CC,1\n",
        encoding="utf-8",
    )
    curves_csv.write_text(
        "CURVE,X,Y\n1,0,0\n1,1,10\n",
        encoding="utf-8",
    )
    products_csv.write_text(
        "TRACK,OFFSET,LABEL,CURVE\n1,0,product.Yield.managed.Total,1\n",
        encoding="utf-8",
    )

    summary = summarize_account_surface(
        accounts_csv_path=accounts_csv,
        products_csv_path=products_csv,
        curves_csv_path=curves_csv,
    )
    diagnosis = summary["diagnosis"]
    assert diagnosis["total_nonzero_from_products"] is True
    assert diagnosis["species_nonzero_present"] is False
    assert diagnosis["total_ok_species_empty_signature"] is True
    assert diagnosis["recommended_next_checks"]
