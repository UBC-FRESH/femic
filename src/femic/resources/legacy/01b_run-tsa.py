# Auto-generated from 01b_run-tsa.ipynb

import os


def _plot_vdyp_overlay(
    *,
    ax,
    vdyp_curves_by_scsi,
    stratum_code,
    si_level,
    message_fn=print,
):
    """Plot VDYP comparison curve when the expected stratum/SI key exists."""
    key = (stratum_code, si_level)
    if key not in vdyp_curves_by_scsi.index:
        message_fn(
            "warning: missing VDYP comparison curve for stratum=%s si_level=%s; "
            "continuing without overlay" % (stratum_code, si_level)
        )
        return False
    vdyp_curves_by_scsi.loc[key].set_index("age").volume.plot(label="VDYP", ax=ax)
    return True


def run_tsa(
    *,
    tsa,
    results,
    au_scsi,
    tipsy_curves,
    vdyp_curves_smooth,
    runtime_config,
):
    from pathlib import Path

    # --- cell 1 ---
    #!mv ./data/04_output.out ./data/tipsy_output_tsa08.out
    #!mv ./data/04_output.out ./data/tipsy_output_tsa16.out
    #!mv ./data/04_output.out ./data/tipsy_output_tsa24.out
    #!mv ./data/04_output.out ./data/tipsy_output_tsa40.out
    #!mv ./data/04_output.out ./data/tipsy_output_tsa41.out

    # --- cell 2 ---
    ##################################################################################
    # Code below is adapted from a script developed by Cosmin Man (cman@forsite.ca).
    ##################################################################################

    import pandas as pd
    from matplotlib import pyplot as plt
    import seaborn as sns
    from femic.pipeline.legacy_runtime import Legacy01BRuntimeConfig
    from femic.pipeline.managed_curves import build_transformed_managed_curves_for_tsa
    from femic.pipeline.plots import tipsy_vdyp_ylim_for_tsa
    from femic.pipeline.tipsy import (
        parse_btc_tsr_transposed_output,
        btc_msyt_input_csv_path,
        tipsy_params_excel_path,
        tipsy_stage_output_paths,
        validate_tipsy_output_is_fresh,
        write_tipsy_output_input_fingerprint,
    )

    if not isinstance(runtime_config, Legacy01BRuntimeConfig):
        raise TypeError(
            "runtime_config must be Legacy01BRuntimeConfig, got "
            f"{type(runtime_config).__name__}"
        )

    #############no need to change the code below
    tipsy_excel = str(
        tipsy_params_excel_path(
            tsa=tsa,
            tipsy_params_path_prefix=runtime_config.tipsy_params_path_prefix,
        )
    )
    tipsy_output_root = Path(runtime_config.tipsy_output_root)
    tipsyout = str(
        tipsy_output_root
        / runtime_config.tipsy_output_filename_template.format(tsa=tsa)
    )
    tipsy_input_csv = str(btc_msyt_input_csv_path(tsa=tsa))
    outYield_path, outSPP_path = tipsy_stage_output_paths(
        tsa=tsa, output_root=runtime_config.tipsy_output_root
    )
    outYield = str(outYield_path)
    outSPP = str(outSPP_path)

    def _load_tipsy_input_df(*, tipsy_input_csv_path: str):
        csv_path = Path(tipsy_input_csv_path)
        if not csv_path.is_file():
            raise FileNotFoundError(
                "Missing canonical BatchTIPSY input CSV: "
                f"{csv_path}. Regenerate 03_input-tsaXX.csv in Stage 01a before "
                "running legacy 01b/post-TIPSY."
            )

        btc_df = pd.read_csv(csv_path)
        if btc_df.empty:
            return pd.DataFrame(
                columns=[
                    "AU",
                    "TBLno",
                    "SI",
                    "Proportion",
                    "SPP_1",
                    "PCT_1",
                    "SPP_2",
                    "PCT_2",
                    "SPP_3",
                    "PCT_3",
                    "SPP_4",
                    "PCT_4",
                    "SPP_5",
                    "PCT_5",
                ]
            )

        planted_density_cols = [
            f"planted_density{i}"
            for i in range(1, 6)
            if f"planted_density{i}" in btc_df.columns
        ]
        species_si_cols = [col for col in btc_df.columns if col.endswith("_si")]

        def _row_to_legacy(record: pd.Series) -> dict[str, object]:
            planted_total = sum(
                float(pd.to_numeric(record.get(col), errors="coerce") or 0.0)
                for col in planted_density_cols
            )
            row: dict[str, object] = {
                "AU": int(record["feature_id"]),
                "TBLno": int(record["feature_id"]),
                "SI": 0.0,
                "Proportion": float(
                    pd.to_numeric(record.get("planted_percent"), errors="coerce") or 0.0
                )
                / 100.0,
            }
            si_values = [
                float(value)
                for value in (
                    pd.to_numeric(record.get(col), errors="coerce")
                    for col in species_si_cols
                )
                if pd.notna(value) and float(value) > 0.0
            ]
            row["SI"] = max(si_values) if si_values else 0.0
            for idx in range(1, 6):
                spp = record.get(f"planted_species{idx}", "")
                density = pd.to_numeric(
                    record.get(f"planted_density{idx}"), errors="coerce"
                )
                row[f"SPP_{idx}"] = (
                    str(spp).strip().upper() if pd.notna(spp) and str(spp).strip() else ""
                )
                if planted_total > 0 and pd.notna(density) and float(density) > 0.0:
                    row[f"PCT_{idx}"] = (float(density) / planted_total) * 100.0
                else:
                    row[f"PCT_{idx}"] = 0.0
            return row

        legacy_rows = [_row_to_legacy(record) for _, record in btc_df.iterrows()]
        return pd.DataFrame(legacy_rows)

    managed_curve_mode = (
        os.environ.get("FEMIC_MANAGED_CURVE_MODE", "tipsy").strip().lower()
    )
    managed_curve_x_scale = float(os.environ.get("FEMIC_MANAGED_CURVE_X_SCALE", "0.8"))
    managed_curve_y_scale = float(os.environ.get("FEMIC_MANAGED_CURVE_Y_SCALE", "1.2"))
    managed_curve_max_age = int(os.environ.get("FEMIC_MANAGED_CURVE_MAX_AGE", "300"))
    managed_curve_truncate_at_culm = os.environ.get(
        "FEMIC_MANAGED_CURVE_TRUNCATE_AT_CULM", "1"
    ).strip().lower() in {"1", "true", "yes"}
    allow_stale_tipsy_output = os.environ.get(
        "FEMIC_ALLOW_STALE_TIPSY_OUTPUT", "0"
    ).strip().lower() in {"1", "true", "yes"}
    strict_timestamp_mismatch = os.environ.get(
        "FEMIC_STRICT_TIPSY_TIMESTAMP_MISMATCH", "0"
    ).strip().lower() in {"1", "true", "yes"}

    requires_batch_tipsy = managed_curve_mode == "tipsy"
    if requires_batch_tipsy:
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=tipsy_excel,
            btc_input_csv_path=tipsy_input_csv,
            tipsy_output_path=tipsyout,
            allow_stale=allow_stale_tipsy_output,
            strict_timestamp_mismatch=strict_timestamp_mismatch,
        )
    else:
        print(
            "managed curve mode %s: skipping BatchTIPSY freshness guard"
            % managed_curve_mode
        )

    tipsy_input_df = _load_tipsy_input_df(tipsy_input_csv_path=tipsy_input_csv)
    tipsy_input_df = tipsy_input_df.query("SI > 0").copy()
    if tipsy_input_df.empty:
        print(
            f"warning: no valid TIPSY input rows for TSA {tsa}; writing empty 01b outputs"
        )
        pd.DataFrame(columns=["AU"]).to_csv(outSPP, header=True, index=False)
        pd.DataFrame(columns=["AU", "Age", "Yield", "Height", "DBHq", "TPH"]).to_csv(
            outYield,
            header=True,
            index=False,
        )
    else:
        # reformat data
        for i in range(1, 6):
            tipsy_input_df[["PCT_" + str(i)]] = tipsy_input_df[
                ["PCT_" + str(i)]
            ].fillna(0)
            if tipsy_input_df["PCT_" + str(i)].dtype == object:
                tipsy_input_df["PCT_" + str(i)] = pd.to_numeric(
                    tipsy_input_df["PCT_" + str(i)]
                ).astype(int)
            else:
                tipsy_input_df["PCT_" + str(i)] = tipsy_input_df[
                    "PCT_" + str(i)
                ].astype(int)

        # consolidate species
        for i in range(1, 4):
            ds = tipsy_input_df.groupby(
                ["AU", "Proportion", "SPP_" + str(i)], as_index=False
            )[["PCT_" + str(i)]].mean()
            ds["SPP"] = ds["SPP_" + str(i)]
            ds["PCT"] = ds["Proportion"] * ds["PCT_" + str(i)]
            ds = ds.query("PCT>0")
            ds = ds.groupby(["AU", "SPP"], as_index=False)[["PCT"]].sum()
            if i == 1:
                dspp = ds
            else:
                dspp = pd.concat([dspp, ds], ignore_index=True)
        dspp = dspp.groupby(["AU", "SPP"])[["PCT"]].sum()

        # unstack and remove extra columns
        dspp = dspp.unstack()
        dspp.columns = dspp.columns.droplevel(0)
        dspp.reset_index(inplace=True)
        dspp.to_csv(outSPP, header=True, index=False)

        if not Path(tipsyout).is_file():
            print(
                f"warning: missing TIPSY output file for TSA {tsa} at {tipsyout}; "
                "writing empty yield table"
            )
            pd.DataFrame(
                columns=["AU", "Age", "Yield", "Height", "DBHq", "TPH"]
            ).to_csv(outYield, header=True, index=False)
        else:
            # consolidate yields
            if Path(tipsyout).suffix.lower() == ".csv":
                dyf = parse_btc_tsr_transposed_output(
                    output_csv=tipsyout,
                    pd_module=pd,
                )
            else:
                cols = [
                    "TABLE_NO",
                    "Empty",
                    "Age",
                    "Yield",
                    "Vol_gross",
                    "DBHq",
                    "Height",
                    "TPH",
                    "Crown_C",
                    "Crown_L",
                    "CWD_TPH",
                ]
                dy = pd.read_csv(
                    tipsyout,
                    low_memory=False,
                    header=None,
                    skiprows=4,
                    sep=r"\s+",
                )
                dy.columns = cols
                dy.drop("Empty", axis=1, inplace=True)
                dy.set_index("TABLE_NO", inplace=True)
                dp = tipsy_input_df.groupby(["AU", "TBLno"], as_index=False)[
                    ["Proportion"]
                ].sum()
                dp.set_index("TBLno", inplace=True)
                dy = dy.join(dp)
                dy.reset_index(inplace=True)
                dyf = dy.groupby(["AU", "Age"], as_index=False).agg(
                    {
                        "Yield": ["sum"],
                        "Height": ["max"],
                        "DBHq": ["max"],
                        "TPH": ["sum"],
                    }
                )
                dyf.columns = dyf.columns.droplevel(1)  # drop the sum/max labels

            # export result to a CSV file
            dyf.to_csv(outYield, header=True, index=False)

    # --- cell 4 ---
    yield_df = pd.read_csv(outYield)
    if "AU" in yield_df.columns and not yield_df.empty:
        yield_df["AU"] = yield_df["AU"].astype("int")

    palette = sns.color_palette("Greens", 3)  # , len(df.index.unique(level=0)))
    sns.set_palette(palette)
    vdyp_curves_by_scsi = (
        vdyp_curves_smooth[tsa]
        .sort_values(["stratum_code", "si_level", "age"])
        .set_index(["stratum_code", "si_level"])
        .sort_index()
    )
    if managed_curve_mode == "vdyp_transform":
        au_values = (
            tipsy_input_df["AU"].astype(int).tolist()
            if "AU" in tipsy_input_df.columns
            else []
        )
        transformed = build_transformed_managed_curves_for_tsa(
            tsa=tsa,
            au_values=au_values,
            au_scsi=au_scsi,
            vdyp_curves_by_scsi=vdyp_curves_by_scsi,
            x_scale=managed_curve_x_scale,
            y_scale=managed_curve_y_scale,
            max_age=managed_curve_max_age,
            truncate_after_culmination=managed_curve_truncate_at_culm,
            pd_module=pd,
        )
        if transformed.empty:
            print(
                f"warning: managed curve mode 'vdyp_transform' yielded no rows for tsa {tsa}; "
                "falling back to TIPSY output"
            )
        else:
            yield_df = transformed.copy()
            yield_df.to_csv(outYield, header=True, index=False)
            print(
                "managed curve mode vdyp_transform: "
                f"x_scale={managed_curve_x_scale:.3f} "
                f"y_scale={managed_curve_y_scale:.3f} "
                f"truncate={managed_curve_truncate_at_culm} "
                f"max_age={managed_curve_max_age}"
            )

    yield_df.set_index(["AU", "Age"], inplace=True)
    tipsy_curves[tsa] = yield_df
    y_limits = tipsy_vdyp_ylim_for_tsa(tsa)

    for i, au in enumerate(yield_df.index.unique(level=0)):
        print(i, au)
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        au_full = int(au)
        au_suffix = int(str(au)[-4:])
        scsi = au_scsi[tsa].get(au_full) or au_scsi[tsa].get(au_suffix)
        if scsi is None:
            print(
                f"warning: missing AU->(stratum,si) mapping for AU {au_full}; "
                "continuing without VDYP overlay"
            )
            sc = f"AU {au_full}"
            si_level = "?"
        else:
            sc, si_level = scsi
            print(au, sc, si_level)
        # (df.loc[au].Yield * ss.CROWN_CLOSURE.median() * 0.01).plot(ax=ax, label='TIPSY (scaled by CC)', linestyle='--')
        (yield_df.loc[au].Yield * 1.00).plot(ax=ax, label="TIPSY (raw)", linestyle="--")
        if scsi is not None:
            _plot_vdyp_overlay(
                ax=ax,
                vdyp_curves_by_scsi=vdyp_curves_by_scsi,
                stratum_code=sc,
                si_level=si_level,
                message_fn=print,
            )
        # plt.plot(df.loc[au].Age, df.loc[au].Yield, linestyle='-', alpha=0.5, label=au, linewidth=2)s
        plt.xlabel("Age")
        plt.ylabel("Yield (m3/ha)")
        plt.title("%s %s (AU %i)" % (sc, si_level, au))
        plt.legend()
        plt.xlim([0, 300])
        plt.ylim(list(y_limits))
        plt.savefig("./plots/tipsy_vdyp_tsa%s-%s.png" % (tsa, au), facecolor="white")
        plt.close(fig)

    if requires_batch_tipsy:
        write_tipsy_output_input_fingerprint(
            btc_input_csv_path=tipsy_input_csv,
            tipsy_output_path=tipsyout,
        )


if __name__ == "__main__":
    raise SystemExit(
        "01b_run-tsa.py is intended to be launched by 00_data-prep.py or femic run."
    )
