# Auto-generated from 01a_run-tsa.ipynb


def run_tsa(
    *,
    tsa,
    stratum_col,
    f,
    si_levels,
    results,
    vdyp_results,
    vdyp_curves_smooth,
    scsi_au,
    au_scsi,
    tipsy_params,
    si_levelquants,
    species_list,
    runtime_config,
):
    from pathlib import Path

    import distance
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import pickle
    import seaborn as sns

    from femic.pipeline.pre_vdyp import (
        build_vdyp_prep_signature,
        load_vdyp_prep_checkpoint,
        pre_vdyp_checkpoint_path,
        save_vdyp_prep_checkpoint,
    )
    from femic.pipeline.legacy_runtime import Legacy01ARuntimeConfig
    from femic.pipeline.vdyp_logging import (
        append_jsonl,
        build_tsa_vdyp_log_paths,
        resolve_run_id,
    )
    from femic.pipeline.vdyp_curves import (
        legacy_fit_func1,
        legacy_fit_func1_bounds_func,
        process_vdyp_out,
    )
    from femic.pipeline.vdyp_stage import (
        build_bootstrap_vdyp_results_runner,
        build_curve_fit_adapter,
        build_curve_smoothing_plot_config,
        build_stratum_fit_run_config,
        build_fit_stratum_curves_runner,
        build_run_vdyp_for_stratum_runner,
        build_smoothed_curve_table,
        compile_strata_fit_results,
        execute_curve_smoothing_runs,
        load_vdyp_input_tables,
        load_or_build_vdyp_results_tsa,
        plot_curve_overlays,
    )
    from femic.pipeline.tsa import (
        apply_stratum_alias_map,
        build_strata_summary,
        build_stratum_lexmatch_alias_map,
        select_tsa_slice,
    )
    from femic.pipeline.plots import (
        build_strata_distribution_plot_config,
        plot_strata_site_index_diagnostics,
        render_strata_distribution_plot,
        resolve_strata_plot_ordering,
    )
    from femic.pipeline.vdyp_overrides import vdyp_kwarg_overrides_for_tsa
    from femic.pipeline.tipsy import (
        DEFAULT_BTC_MSYT_COLUMNS,
        build_btc_msyt_input_table,
        build_tipsy_params_for_tsa,
        build_tipsy_input_table,
        write_btc_msyt_input_csv,
        write_tipsy_input_exports,
    )
    from femic.pipeline.tipsy_legacy import (
        build_tipsy_exclusion,
        get_legacy_tipsy_builders,
    )
    from femic.pipeline.tipsy_config import (
        resolve_tipsy_runtime_options,
        resolve_tipsy_param_builder,
    )

    if not isinstance(runtime_config, Legacy01ARuntimeConfig):
        raise TypeError(
            "runtime_config must be Legacy01ARuntimeConfig, got "
            f"{type(runtime_config).__name__}"
        )

    curve_fit = build_curve_fit_adapter(
        curve_fit_impl=runtime_config.curve_fit_impl,
        np_module=np,
    )
    kwarg_overrides_for_tsa = runtime_config.kwarg_overrides_for_tsa
    if kwarg_overrides_for_tsa is None:
        kwarg_overrides_for_tsa = vdyp_kwarg_overrides_for_tsa(tsa)

    # --- cell 1 ---
    print("processing tsa", tsa)

    # --- cell 2 ---
    tsa_slice = select_tsa_slice(f_table=f, tsa_value=tsa)

    if stratum_col in tsa_slice.columns:
        f_ = tsa_slice.reset_index(drop=True)
    elif stratum_col in getattr(tsa_slice.index, "names", []):
        f_ = tsa_slice.reset_index()
    else:
        raise KeyError(
            f"{stratum_col!r} not found in TSA slice columns/index for tsa={tsa}; "
            f"columns={list(getattr(tsa_slice, 'columns', []))}, "
            f"index_names={list(getattr(tsa_slice.index, 'names', []))}"
        )
    f_ = f_.set_index(stratum_col)

    # --- cell 5 ---
    totalarea = f_.FEATURE_AREA_SQM.sum()
    f_["totalarea_p"] = f_.FEATURE_AREA_SQM / totalarea

    # --- cell 8 ---
    strata_df, _largestn_strata_codes, site_index_iqr_mean = build_strata_summary(
        f_table=f_,
        stratum_col=stratum_col,
        pd_module=pd,
        tsa_code=tsa,
        target_coverage=runtime_config.target_area_coverage,
    )
    print("mean stratum SI IQR", site_index_iqr_mean)
    print("coverage", strata_df.coverage.sum())
    print("count", strata_df.shape[0])

    # --- cell 10/12 ---
    plot_strata_site_index_diagnostics(
        strata_df=strata_df,
        np_module=np,
        plt_module=plt,
    )

    # --- cell 14 ---
    strata_plot_cfg = build_strata_distribution_plot_config()

    stratum_props, labels = resolve_strata_plot_ordering(
        strata_df=strata_df,
        sort_lex=False,
    )

    strata_plot_metadata = render_strata_distribution_plot(
        tsa_code=tsa,
        f_table=f_,
        stratum_col=stratum_col,
        labels=labels,
        stratum_props=stratum_props,
        plot_config=strata_plot_cfg,
        sns_module=sns,
        plt_module=plt,
    )
    print(
        "strata plot SI window",
        strata_plot_metadata.site_index_xlim,
        "points total/window/overlay",
        (
            strata_plot_metadata.total_points,
            strata_plot_metadata.window_points,
            strata_plot_metadata.strip_points_plotted,
        ),
        "clipped low/high",
        (
            strata_plot_metadata.clipped_low_count,
            strata_plot_metadata.clipped_high_count,
        ),
    )

    # --- cell 16 ---
    selected_strata_codes = list(strata_df.index.values)
    best_match = build_stratum_lexmatch_alias_map(
        f_table=f_,
        stratum_col=stratum_col,
        selected_strata_codes=selected_strata_codes,
        levenshtein_fn=distance.levenshtein,
    )

    # --- cell 17 ---
    f_.reset_index(inplace=True)

    # --- cell 18 ---
    stratum_col = apply_stratum_alias_map(
        f_table=f_,
        stratum_col=stratum_col,
        selected_strata_codes=selected_strata_codes,
        best_match=best_match,
    )

    # --- cell 20 ---
    f__ = f_.set_index(stratum_col)

    # --- cell 22 ---
    body_fit_func = legacy_fit_func1
    body_fit_func_bounds_func = legacy_fit_func1_bounds_func
    toe_fit_func = legacy_fit_func1
    toe_fit_func_bounds_func = legacy_fit_func1_bounds_func

    # --- cell 24 ---
    stratum_si_stats = f__.groupby(stratum_col).SITE_INDEX.describe(
        percentiles=[0, 0.05, 0.20, 0.35, 0.5, 0.65, 0.80, 0.95, 1]
    )

    # --- cell 28 ---
    stratum_fit_cfg = build_stratum_fit_run_config(
        min_stands_per_si_bin=runtime_config.min_stands_per_si_bin
    )

    vdyp_prep_checkpoint_path = pre_vdyp_checkpoint_path(tsa_code=tsa)
    prep_signature = build_vdyp_prep_signature(
        selected_strata_codes=selected_strata_codes,
        target_area_coverage=runtime_config.target_area_coverage,
        min_stands_per_si_bin=runtime_config.min_stands_per_si_bin,
    )
    prep_loaded = False
    if runtime_config.resume_effective and Path(vdyp_prep_checkpoint_path).is_file():
        try:
            results[tsa] = load_vdyp_prep_checkpoint(
                vdyp_prep_checkpoint_path,
                expected_signature=prep_signature,
            )
            prep_loaded = True
            print("resume: loaded pre-VDYP checkpoint (%s strata)" % len(results[tsa]))
        except (
            OSError,
            EOFError,
            pickle.UnpicklingError,
            TypeError,
            AttributeError,
            ModuleNotFoundError,
        ) as exc:
            print(
                "resume: failed to load pre-VDYP checkpoint %s: %s"
                % (vdyp_prep_checkpoint_path, exc)
            )

    if not prep_loaded:
        compile_one_fn = build_fit_stratum_curves_runner(
            f_table=f__,
            fit_func=body_fit_func,
            fit_func_bounds_func=body_fit_func_bounds_func,
            strata_df=strata_df,
            stratum_si_stats=stratum_si_stats,
            species_list=species_list,
            curve_fit_fn=curve_fit,
            np_module=np,
            pd_module=pd,
            sns_module=sns,
            plt_module=plt,
            fit_rawdata=stratum_fit_cfg.fit_rawdata,
            min_stands_per_si_bin=stratum_fit_cfg.min_stands_per_si_bin,
            min_age=stratum_fit_cfg.min_age,
            agg_type=stratum_fit_cfg.agg_type,
            plot=stratum_fit_cfg.plot,
            figsize=stratum_fit_cfg.figsize,
            verbose=stratum_fit_cfg.verbose,
            ylim=stratum_fit_cfg.ylim,
            xlim=stratum_fit_cfg.xlim,
            message_fn=print,
        )
        results[tsa] = compile_strata_fit_results(
            strata_df=strata_df,
            compile_one_fn=compile_one_fn,
            message_fn=print,
        )
        saved_count = save_vdyp_prep_checkpoint(
            vdyp_prep_checkpoint_path,
            results[tsa],
            signature=prep_signature,
        )
        print(
            "saved pre-VDYP checkpoint with %s strata to %s"
            % (saved_count, vdyp_prep_checkpoint_path)
        )

    def _compile_fit_results(*, f_table, stratum_si_stats_for_fit):
        compile_one_fn_local = build_fit_stratum_curves_runner(
            f_table=f_table,
            fit_func=body_fit_func,
            fit_func_bounds_func=body_fit_func_bounds_func,
            strata_df=strata_df,
            stratum_si_stats=stratum_si_stats_for_fit,
            species_list=species_list,
            curve_fit_fn=curve_fit,
            np_module=np,
            pd_module=pd,
            sns_module=sns,
            plt_module=plt,
            fit_rawdata=stratum_fit_cfg.fit_rawdata,
            min_stands_per_si_bin=stratum_fit_cfg.min_stands_per_si_bin,
            min_age=stratum_fit_cfg.min_age,
            agg_type=stratum_fit_cfg.agg_type,
            plot=stratum_fit_cfg.plot,
            figsize=stratum_fit_cfg.figsize,
            verbose=stratum_fit_cfg.verbose,
            ylim=stratum_fit_cfg.ylim,
            xlim=stratum_fit_cfg.xlim,
            message_fn=print,
        )
        return compile_strata_fit_results(
            strata_df=strata_df,
            compile_one_fn=compile_one_fn_local,
            message_fn=print,
        )

    vdyp_sampling_mode = runtime_config.vdyp_sampling_mode
    if runtime_config.vdyp_two_pass_rebin and str(vdyp_sampling_mode).lower() == "auto":
        vdyp_sampling_mode = "all"
        print("two-pass rebin enabled: forcing first-pass VDYP sampling mode to all")

    # --- cell 30/32 ---

    femic_run_id = resolve_run_id()
    vdyp_log_paths = build_tsa_vdyp_log_paths(
        tsa_code=tsa,
        run_id=femic_run_id,
        vdyp_io_dirname="vdyp_io",
    )
    vdyp_run_events_path = vdyp_log_paths["run"]
    vdyp_curve_events_path = vdyp_log_paths["curve"]
    vdyp_stdout_log_path = vdyp_log_paths["stdout"]
    vdyp_stderr_log_path = vdyp_log_paths["stderr"]

    # --- cell 38 ---
    # --- cell 40 ---
    vdyp_ply_cache_path = Path(runtime_config.vdyp_ply_feather_path)
    vdyp_lyr_cache_path = Path(runtime_config.vdyp_lyr_feather_path)
    vdyp_ply_tsa_path = vdyp_ply_cache_path.with_name(
        f"{vdyp_ply_cache_path.stem}-tsa{tsa}{vdyp_ply_cache_path.suffix}"
    )
    vdyp_lyr_tsa_path = vdyp_lyr_cache_path.with_name(
        f"{vdyp_lyr_cache_path.stem}-tsa{tsa}{vdyp_lyr_cache_path.suffix}"
    )
    vdyp_source_feature_ids: list[int] = []
    vdyp_source_map_ids: list[str] = []
    for _stratumi, _sc, _fit_out in results[tsa]:
        for _si in si_levels:
            ss = _fit_out.get(_si, {}).get("ss")
            if ss is None or "FEATURE_ID" not in ss.columns:
                continue
            vdyp_source_feature_ids.extend(
                ss["FEATURE_ID"].dropna().astype(int).tolist()
            )
            if "MAP_ID" in ss.columns:
                vdyp_source_map_ids.extend(ss["MAP_ID"].dropna().astype(str).tolist())
    vdyp_source_feature_ids = sorted(set(vdyp_source_feature_ids))
    vdyp_source_map_ids = sorted(set(vdyp_source_map_ids))

    vdyp_read_from_source = runtime_config.force_run_vdyp or not (
        vdyp_ply_tsa_path.is_file() and vdyp_lyr_tsa_path.is_file()
    )
    vdyp_ply, vdyp_lyr = load_vdyp_input_tables(
        vdyp_input_pandl_path=runtime_config.vdyp_input_pandl_path,
        vdyp_ply_feather_path=vdyp_ply_tsa_path,
        vdyp_lyr_feather_path=vdyp_lyr_tsa_path,
        read_from_source=vdyp_read_from_source,
        source_map_ids=vdyp_source_map_ids,
        source_feature_ids=vdyp_source_feature_ids,
        message_fn=print,
    )
    if vdyp_ply.shape[0] == 0 or vdyp_lyr.shape[0] == 0:
        print(
            "warning: TSA-filtered VDYP inputs are empty for tsa %s; "
            "falling back to shared cached tables" % tsa
        )
        vdyp_ply, vdyp_lyr = load_vdyp_input_tables(
            vdyp_input_pandl_path=runtime_config.vdyp_input_pandl_path,
            vdyp_ply_feather_path=runtime_config.vdyp_ply_feather_path,
            vdyp_lyr_feather_path=runtime_config.vdyp_lyr_feather_path,
            read_from_source=False,
        )

    # --- cell 42 ---
    vdyp_results_tsa_pickle_path = runtime_config.vdyp_cache_paths[
        "vdyp_results_tsa_pickle_path"
    ]
    run_vdyp_fn = build_run_vdyp_for_stratum_runner(
        tsa=tsa,
        run_id=femic_run_id,
        vdyp_ply=vdyp_ply,
        vdyp_lyr=vdyp_lyr,
        rc_len=max(int(runtime_config.parallel_worker_count), 1),
        curve_fit_fn=curve_fit,
        fit_func=body_fit_func,
        fit_func_bounds_func=body_fit_func_bounds_func,
        append_jsonl_fn=append_jsonl,
        vdyp_log_path=vdyp_run_events_path,
        vdyp_stdout_log_path=vdyp_stdout_log_path,
        vdyp_stderr_log_path=vdyp_stderr_log_path,
    )
    run_bootstrap_fn = build_bootstrap_vdyp_results_runner(
        tsa=tsa,
        run_id=femic_run_id,
        results_for_tsa=results[tsa][:],
        si_levels=si_levels,
        vdyp_run_events_path=vdyp_run_events_path,
        append_jsonl_fn=append_jsonl,
        run_vdyp_fn=run_vdyp_fn,
        vdyp_out_cache=runtime_config.vdyp_out_cache,
        nsamples_mode=vdyp_sampling_mode,
    )
    vdyp_results[tsa] = load_or_build_vdyp_results_tsa(
        tsa=tsa,
        force_run_vdyp=bool(runtime_config.force_run_vdyp),
        vdyp_results_tsa_pickle_path=vdyp_results_tsa_pickle_path,
        vdyp_results_pickle_path=runtime_config.vdyp_results_pickle_path,
        run_bootstrap_fn=run_bootstrap_fn,
        print_fn=print,
    )

    if runtime_config.vdyp_two_pass_rebin:
        print("two-pass SI rebin: deriving stand-level SI from first-pass VDYP output")

        def _coerce_feature_id(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _extract_stand_si_from_vdyp(vdyp_results_for_tsa):
            by_stratum = {}
            for stratumi_, per_si in vdyp_results_for_tsa.items():
                stand_si = {}
                if not isinstance(per_si, dict):
                    by_stratum[int(stratumi_)] = stand_si
                    continue
                for tables in per_si.values():
                    if not isinstance(tables, dict):
                        continue
                    for feature_id, table in tables.items():
                        if (
                            not isinstance(table, pd.DataFrame)
                            or "SI" not in table.columns
                        ):
                            continue
                        fid = _coerce_feature_id(feature_id)
                        if fid is None:
                            continue
                        si_values = pd.to_numeric(table["SI"], errors="coerce").dropna()
                        if si_values.empty:
                            continue
                        stand_si[fid] = float(si_values.median())
                by_stratum[int(stratumi_)] = stand_si
            return by_stratum

        def _collect_stand_tables(vdyp_results_for_tsa):
            by_stratum = {}
            for stratumi_, per_si in vdyp_results_for_tsa.items():
                stand_tables = {}
                if isinstance(per_si, dict):
                    for tables in per_si.values():
                        if not isinstance(tables, dict):
                            continue
                        for feature_id, table in tables.items():
                            fid = _coerce_feature_id(feature_id)
                            if fid is None:
                                continue
                            stand_tables[fid] = table
                by_stratum[int(stratumi_)] = stand_tables
            return by_stratum

        vdyp_si_by_stratum = _extract_stand_si_from_vdyp(vdyp_results.get(tsa, {}))
        vdyp_tables_by_stratum = _collect_stand_tables(vdyp_results.get(tsa, {}))
        f_rebin = f__.copy()
        lookup = {}
        for stratumi_, sc, _fit_out in results[tsa]:
            stand_si_map = vdyp_si_by_stratum.get(int(stratumi_), {})
            for fid, si_value in stand_si_map.items():
                lookup[(str(sc), int(fid))] = float(si_value)
        feature_ids_numeric = pd.to_numeric(f_rebin["FEATURE_ID"], errors="coerce")
        mapped_si = []
        mapped_count = 0
        for sc, fid in zip(f_rebin.index.astype(str), feature_ids_numeric):
            if pd.notna(fid):
                key = (str(sc), int(fid))
                si_value = lookup.get(key)
                if si_value is not None:
                    mapped_count += 1
                    mapped_si.append(float(si_value))
                    continue
            mapped_si.append(np.nan)
        f_rebin["_VDYP_OUTPUT_SI"] = mapped_si
        f_rebin["_VDYP_OUTPUT_SI"] = f_rebin["_VDYP_OUTPUT_SI"].fillna(
            f_rebin["SITE_INDEX"]
        )
        f_rebin["SITE_INDEX"] = f_rebin["_VDYP_OUTPUT_SI"]
        print(
            "two-pass SI rebin: mapped VDYP SI for %s/%s rows"
            % (mapped_count, f_rebin.shape[0])
        )
        stratum_si_stats_vdyp = f_rebin.groupby(stratum_col).SITE_INDEX.describe(
            percentiles=[0, 0.05, 0.20, 0.35, 0.5, 0.65, 0.80, 0.95, 1]
        )
        results[tsa] = _compile_fit_results(
            f_table=f_rebin,
            stratum_si_stats_for_fit=stratum_si_stats_vdyp,
        )
        saved_count = save_vdyp_prep_checkpoint(
            vdyp_prep_checkpoint_path,
            results[tsa],
            signature=prep_signature,
        )
        print(
            "saved pre-VDYP checkpoint (VDYP-SI rebin) with %s strata to %s"
            % (saved_count, vdyp_prep_checkpoint_path)
        )

        rebinned_vdyp_results = {}
        missing_tables = 0
        expected_tables = 0
        for stratumi_, _sc, fit_out in results[tsa]:
            stand_tables = vdyp_tables_by_stratum.get(int(stratumi_), {})
            rebinned_vdyp_results[int(stratumi_)] = {}
            for si_level in si_levels:
                ss = fit_out.get(si_level, {}).get("ss")
                if ss is None or getattr(ss, "empty", False):
                    rebinned_vdyp_results[int(stratumi_)][si_level] = {}
                    continue
                fids = (
                    pd.to_numeric(ss["FEATURE_ID"], errors="coerce")
                    .dropna()
                    .astype(int)
                    .unique()
                    .tolist()
                )
                expected_tables += len(fids)
                rebinned_tables = {}
                for fid in fids:
                    table = stand_tables.get(int(fid))
                    if table is None:
                        missing_tables += 1
                        continue
                    rebinned_tables[int(fid)] = table
                rebinned_vdyp_results[int(stratumi_)][si_level] = rebinned_tables
        vdyp_results[tsa] = rebinned_vdyp_results
        print(
            "two-pass SI rebin: rebuilt VDYP bins using cached stand tables "
            "(missing=%s of %s)" % (missing_tables, expected_tables)
        )

    # --- cell 45 ---
    vdyp_curves_smooth_tsa_feather_path = runtime_config.vdyp_cache_paths[
        "vdyp_curves_smooth_tsa_feather_path"
    ]
    should_rebuild_smooth_curves = (
        (not Path(vdyp_curves_smooth_tsa_feather_path).is_file())
        or (not bool(runtime_config.resume_effective))
        or bool(runtime_config.vdyp_two_pass_rebin)
    )
    if should_rebuild_smooth_curves:
        use_au_first_growth_selector = str(tsa).strip().zfill(2) == "29"
        smooth_plot_cfg = build_curve_smoothing_plot_config(sns_module=sns)
        smoothed_runs = execute_curve_smoothing_runs(
            tsa=tsa,
            run_id=femic_run_id,
            results_for_tsa=results[tsa],
            si_levels=si_levels,
            vdyp_results_for_tsa=vdyp_results.get(tsa, {}),
            kwarg_overrides_for_tsa=kwarg_overrides_for_tsa,
            process_vdyp_out_fn=process_vdyp_out,
            append_jsonl_fn=append_jsonl,
            vdyp_curve_events_path=vdyp_curve_events_path,
            curve_fit_fn=curve_fit,
            body_fit_func=body_fit_func,
            body_fit_func_bounds_func=body_fit_func_bounds_func,
            toe_fit_func=toe_fit_func,
            toe_fit_func_bounds_func=toe_fit_func_bounds_func,
            use_au_first_growth_selector=use_au_first_growth_selector,
            message_fn=print,
        )
        plot_curve_overlays(
            results_for_tsa=results[tsa],
            si_levels=si_levels,
            smoothed_runs=smoothed_runs,
            plot=smooth_plot_cfg.plot,
            figsize=smooth_plot_cfg.figsize,
            palette=smooth_plot_cfg.palette,
            pd_module=pd,
            plt_module=plt,
            dataframe_type=pd.core.frame.DataFrame,
            xlim=smooth_plot_cfg.xlim,
            ylim=smooth_plot_cfg.ylim,
            message_fn=print,
        )
        vdyp_curves_smooth[tsa] = build_smoothed_curve_table(
            smoothed_runs=smoothed_runs,
            pd_module=pd,
            output_path=vdyp_curves_smooth_tsa_feather_path,
        )
    else:
        vdyp_curves_smooth[tsa] = pd.read_feather(vdyp_curves_smooth_tsa_feather_path)

    tipsy_exclusion = build_tipsy_exclusion()
    legacy_tipsy_builders = get_legacy_tipsy_builders()
    tipsy_config_dir, tipsy_use_legacy = resolve_tipsy_runtime_options()

    def _missing_legacy_tipsy_builder(*_args, **_kwargs):
        raise RuntimeError(
            f"No legacy TIPSY builder registered for TSA {tsa}. "
            "Provide config/tipsy/tsaXX.yaml or use a supported legacy TSA."
        )

    tipsy_param_builder, tipsy_param_builder_message = resolve_tipsy_param_builder(
        tsa_code=tsa,
        legacy_builder=legacy_tipsy_builders.get(tsa, _missing_legacy_tipsy_builder),
        config_dir=tipsy_config_dir,
        use_legacy=tipsy_use_legacy,
    )
    print(tipsy_param_builder_message)

    exclusion = tipsy_exclusion.get(
        tsa,
        {
            "min_si": lambda _s: 0.0,
            "min_vol": lambda _s: 0.0,
            "excl_bec": [],
            "excl_leading_species": [],
        },
    )

    # --- cell 55 ---
    (
        scsi_au[tsa],
        au_scsi[tsa],
        tipsy_params[tsa],
    ) = build_tipsy_params_for_tsa(
        tsa=tsa,
        results_for_tsa=results[tsa],
        si_levels=si_levels,
        vdyp_curves_smooth_tsa=vdyp_curves_smooth[tsa],
        vdyp_results_for_tsa=vdyp_results.get(tsa, {}),
        exclusion=exclusion,
        tipsy_param_builder=tipsy_param_builder,
        vdyp_curve_events_path=vdyp_curve_events_path,
        append_jsonl_fn=append_jsonl,
        message_fn=print,
    )

    # --- cell 57 ---
    try:
        df = build_tipsy_input_table(
            tipsy_params_for_tsa=tipsy_params[tsa],
            tipsy_params_columns=runtime_config.tipsy_params_columns,
            pd_module=pd,
        )
        natural_df = build_tipsy_input_table(
            tipsy_params_for_tsa=tipsy_params[tsa],
            tipsy_params_columns=runtime_config.tipsy_params_columns,
            pd_module=pd,
            table_key="e",
        )
    except RuntimeError:
        print(
            "warning: no TIPSY parameter tables generated for TSA %s; writing empty "
            "exports. See %s for missing VDYP diagnostics."
            % (tsa, vdyp_curve_events_path)
        )
        df = pd.DataFrame(columns=list(runtime_config.tipsy_params_columns))
        natural_df = pd.DataFrame(columns=list(runtime_config.tipsy_params_columns))
    write_tipsy_input_exports(
        tipsy_table=df,
        tsa=tsa,
        tipsy_params_path_prefix=runtime_config.tipsy_params_path_prefix,
    )
    try:
        btc_msyt_df = build_btc_msyt_input_table(
            tipsy_table=df,
            natural_tipsy_table=natural_df,
            pd_module=pd,
        )
    except RuntimeError:
        print(
            "warning: no BTC MSYT input rows generated for TSA %s; writing empty "
            "03_input export."
            % tsa
        )
        btc_msyt_df = pd.DataFrame(columns=list(DEFAULT_BTC_MSYT_COLUMNS))
    write_btc_msyt_input_csv(
        btc_msyt_table=btc_msyt_df,
        tsa=tsa,
        output_root=Path(runtime_config.tipsy_params_path_prefix).parent,
    )


if __name__ == "__main__":
    raise SystemExit(
        "01a_run-tsa.py is intended to be launched by 00_data-prep.py or femic run."
    )
