from __future__ import annotations

import ast
from pathlib import Path


def _load_legacy_orchestration_tree() -> ast.AST:
    source_path = Path(__file__).resolve().parents[1] / "00_data-prep.py"
    return ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))


def _find_method_calls(
    tree: ast.AST, module_name: str, method_name: str
) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr != method_name:
            continue
        if isinstance(func.value, ast.Name) and func.value.id == module_name:
            calls.append(node)
    return calls


def _find_function_def(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Function {name!r} not found")


def _find_return_dict_keys(func_def: ast.FunctionDef) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(func_def):
        if not isinstance(node, ast.Return):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not isinstance(node.value.func, ast.Name) or node.value.func.id != "dict":
            continue
        for kw in node.value.keywords:
            if kw.arg is not None:
                keys.add(kw.arg)
    if not keys:
        raise AssertionError(f"No dict(...) return found in {func_def.name!r}")
    return keys


def test_run01a_call_uses_explicit_keyword_handoff() -> None:
    tree = _load_legacy_orchestration_tree()
    func_def = _find_function_def(tree, "_build_01a_run_kwargs")
    kwargs = _find_return_dict_keys(func_def)
    expected = {
        "tsa",
        "stratum_col",
        "f",
        "si_levels",
        "results",
        "vdyp_results",
        "vdyp_curves_smooth",
        "scsi_au",
        "au_scsi",
        "tipsy_params",
        "si_levelquants",
        "species_list",
        "runtime_config",
    }
    assert kwargs == expected


def test_run01a_call_passes_runtime_config_variable() -> None:
    tree = _load_legacy_orchestration_tree()
    func_def = _find_function_def(tree, "_build_01a_run_kwargs")
    assign_targets = {
        target.id
        for node in ast.walk(func_def)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert "runtime_config" in assign_targets


def test_run01b_call_uses_explicit_keyword_handoff() -> None:
    tree = _load_legacy_orchestration_tree()
    func_def = _find_function_def(tree, "_build_01b_run_kwargs")
    kwargs = _find_return_dict_keys(func_def)
    assert kwargs == {
        "tsa",
        "results",
        "au_scsi",
        "tipsy_curves",
        "vdyp_curves_smooth",
        "runtime_config",
    }


def test_no_context_binder_call_remains_in_legacy_orchestration() -> None:
    tree = _load_legacy_orchestration_tree()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "bind_legacy_module_context":
            raise AssertionError(
                "bind_legacy_module_context call should not be present"
            )


def test_no_globals_get_handoff_in_legacy_orchestration() -> None:
    tree = _load_legacy_orchestration_tree()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr != "get":
            continue
        if isinstance(func.value, ast.Call):
            inner = func.value.func
            if isinstance(inner, ast.Name) and inner.id == "globals":
                raise AssertionError("globals().get(...) handoff should not be present")


def test_legacy_orchestration_uses_shared_stage_loop_and_loader_helpers() -> None:
    tree = _load_legacy_orchestration_tree()
    execute_stage_calls = 0
    loader_calls = 0
    loop_calls = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "execute_legacy_tsa_stage":
            execute_stage_calls += 1
        if isinstance(func, ast.Name) and func.id == "load_legacy_module":
            loader_calls += 1
        if isinstance(func, ast.Name) and func.id == "run_legacy_tsa_loop":
            loop_calls += 1
    assert execute_stage_calls == 2
    assert loader_calls == 0
    assert loop_calls == 0


def test_legacy_orchestration_uses_runtime_and_stage_setup_helpers() -> None:
    tree = _load_legacy_orchestration_tree()
    required_calls = {
        "initialize_legacy_tsa_stage_state": 1,
        "initialize_parallel_execution_backend": 1,
        "resolve_legacy_external_data_paths": 1,
        "build_legacy_data_artifact_paths": 1,
        "build_ria_vri_checkpoint_paths": 1,
        "build_vdyp_cache_paths": 1,
        "list_siteprod_layers": 1,
        "export_and_stack_siteprod_layers": 1,
        "assign_thlb_raw_from_raster": 1,
        "derive_species_list_from_slots": 1,
        "normalize_and_filter_checkpoint2_records": 1,
        "filter_post_thlb_stands": 1,
        "assign_stratum_codes_with_lexmatch": 2,
        "assign_siteprod_from_raster": 1,
        "assign_forest_type_from_species_pct": 1,
        "compile_species_volume_columns": 1,
        "prepare_tsa_index": 1,
        "build_legacy_01a_runtime_config": 1,
        "build_legacy_01b_runtime_config": 1,
        "execute_legacy_tsa_stage": 2,
        "should_skip_if_outputs_exist": 2,
        "resolve_bundle_paths": 1,
        "bundle_tables_ready": 1,
        "load_bundle_tables": 1,
        "build_bundle_tables_from_curves": 1,
        "emit_missing_au_curve_mapping_warning": 1,
        "ensure_au_table_index": 1,
        "write_bundle_tables": 1,
        "ensure_scsi_au_from_table": 2,
        "assign_stratum_matches_from_au_table": 1,
        "assign_si_levels_from_stratum_quantiles": 1,
        "assign_au_ids_from_scsi": 1,
        "summarize_missing_au_mappings": 1,
        "emit_missing_au_mapping_warning": 1,
        "validate_nonempty_au_assignment": 1,
        "assign_curve_ids_from_au_table": 1,
        "assign_thlb_area_and_flag": 1,
        "tipsy_input_dat_path": 1,
        "tipsy_params_excel_path": 1,
        "tipsy_stage_output_paths": 1,
        "build_stands_column_map": 1,
        "should_skip_stands_export": 1,
        "export_stands_shapefiles": 1,
    }
    observed = {name: 0 for name in required_calls}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in observed:
            observed[func.id] += 1

    assert observed == required_calls
