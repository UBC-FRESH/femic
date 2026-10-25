from __future__ import annotations

from pathlib import Path

import pytest

from femic.hydrology.flood import FloodSample
from femic.hydrology.process_models import (
    DEFAULT_PEAK_FLOW_FILENAME,
    HydrologyProcessModelError,
    adapter_for_model,
    build_scenario_manifest,
    find_process_model_spec,
    load_scenario_manifest,
    plan_process_model_run,
    process_model_specs,
    read_peak_flow_series,
    read_receptor_metrics,
    run_process_model,
    validate_scenario_manifest,
    write_peak_flow_series,
    write_receptor_metrics,
    write_scenario_manifest,
)

GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _manifest(model_id: str = "dhsvm"):
    return build_scenario_manifest(
        scenario_id="scenario-1",
        scenario_name="Treatment scenario",
        model_id=model_id,
        domain_id="domain-1",
        scenario_kind="treatment",
        watershed_ids=("w1",),
        start_year=2020,
        end_year=2025,
        time_step_hours=24.0,
        crs="EPSG:3005",
        climate_forcing_path="climate.csv",
        land_cover_path="landcover.gpkg",
        road_scenario_path="roads.gpkg",
        harvest_scenario_path="harvest.csv",
        model_config_path="dhsvm.config" if model_id == "dhsvm" else "fileManager.txt",
        output_dir="output",
        receptor_ids=("r1",),
        ledger_id="ledger-1",
        provenance={"source": "unit-test"},
        caveats=("Screening only.",),
    )


def _fake_executable(path: Path, *, returncode: int = 0) -> Path:
    path.write_text(
        f"""#!/usr/bin/env python3
import pathlib
import sys
pathlib.Path("peak_flows.csv").write_text(
    "year,peak_flow_m3s\\n2020,10.0\\n2021,12.5\\n2022,15.0\\n"
)
pathlib.Path("receptor_metrics.csv").write_text(
    "receptor_id,metric,value\\nr1,peak_flow_m3s,15.0\\nr1,exceedance_probability,0.1\\n"
)
sys.stderr.write("fake model stderr\\n")
sys.exit({returncode})
"""
    )
    path.chmod(0o755)
    return path


def test_process_model_registry_and_adapters() -> None:
    specs = process_model_specs()
    assert {spec.model_id for spec in specs} == {
        "dhsvm",
        "rhessys",
        "crhm",
        "summa",
        "hechms",
    }
    assert find_process_model_spec("dhsvm") is not None
    assert find_process_model_spec("missing") is None
    assert find_process_model_spec("dhsvm").to_dict()["model_id"] == "dhsvm"
    assert adapter_for_model("dhsvm").spec.model_id == "dhsvm"
    assert adapter_for_model("summa").spec.model_id == "summa"
    with pytest.raises(HydrologyProcessModelError, match="No executable adapter"):
        adapter_for_model("rhessys")


def test_scenario_manifest_round_trip_and_validation(tmp_path: Path) -> None:
    manifest = _manifest()
    assert manifest.to_dict()["scenario_id"] == "scenario-1"
    assert manifest.to_dict()["ledger_id"] == "ledger-1"
    path = write_scenario_manifest(manifest, tmp_path / "scenario.json")
    loaded = load_scenario_manifest(path)
    assert loaded.to_dict() == manifest.to_dict()

    bad = build_scenario_manifest(
        scenario_id="bad",
        scenario_name="Bad",
        model_id="dhsvm",
        domain_id="d",
        scenario_kind="baseline",
        watershed_ids=("w1",),
        start_year=2020,
        end_year=2021,
        climate_forcing_path="c",
        land_cover_path="l",
        road_scenario_path="r",
        harvest_scenario_path="h",
        model_config_path="m",
        output_dir="o",
    )
    assert validate_scenario_manifest(bad) == ()

    errors = validate_scenario_manifest(
        type(manifest)(
            **{
                **manifest.__dict__,
                "model_id": "missing",
                "scenario_kind": "bad",
                "start_year": 2025,
                "end_year": 2020,
                "time_step_hours": 0,
                "watershed_ids": (),
                "scenario_id": "",
            }
        )
    )
    assert any("Unsupported model_id" in error for error in errors)
    assert any("Unsupported scenario_kind" in error for error in errors)
    assert any("start_year" in error for error in errors)
    assert any("time_step_hours" in error for error in errors)
    assert any("watershed_id" in error for error in errors)
    assert any("scenario_id" in error for error in errors)


def test_load_scenario_errors(tmp_path: Path) -> None:
    path = tmp_path / "scenario.json"
    path.write_text('{"schema_version": "bad"}')
    with pytest.raises(HydrologyProcessModelError, match="Unsupported"):
        load_scenario_manifest(path)
    path.write_text("not-json")
    with pytest.raises(HydrologyProcessModelError, match="Invalid JSON"):
        load_scenario_manifest(path)
    path.write_text("[]")
    with pytest.raises(HydrologyProcessModelError, match="JSON object"):
        load_scenario_manifest(path)


def test_probe_and_plan(tmp_path: Path) -> None:
    executable = _fake_executable(tmp_path / "fake-model")
    adapter = adapter_for_model("dhsvm")
    availability = adapter.probe(executable)
    assert availability.available
    assert availability.source == "explicit"
    assert availability.to_dict()["model_id"] == "dhsvm"

    manifest = _manifest("dhsvm")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "dhsvm.config").write_text("config")
    plan = plan_process_model_run(adapter, manifest, run_dir, executable=executable)
    assert plan.available
    assert plan.command == (str(executable.resolve()), str(run_dir / "dhsvm.config"))
    assert plan.to_dict()["scenario_id"] == "scenario-1"

    summa = adapter_for_model("summa")
    summa_manifest = _manifest("summa")
    summa_plan = plan_process_model_run(
        summa,
        summa_manifest,
        run_dir,
        executable=executable,
    )
    assert summa_plan.command[:2] == (str(executable.resolve()), "-m")

    missing = tmp_path / "missing-model"
    unavailable = adapter.probe(missing)
    assert not unavailable.available
    assert unavailable.warnings


def test_probe_env_and_path(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = adapter_for_model("dhsvm")
    monkeypatch.setenv("FEMIC_DHSVM_EXE", "/missing/dhsvm")
    env = adapter.probe()
    assert not env.available
    assert env.source == "FEMIC_DHSVM_EXE"

    monkeypatch.delenv("FEMIC_DHSVM_EXE")
    monkeypatch.setattr(
        "femic.hydrology.process_models.shutil.which", lambda name: None
    )
    missing = adapter.probe()
    assert not missing.available
    assert missing.source == "path"


def test_run_process_model_with_fake_executable(tmp_path: Path) -> None:
    executable = _fake_executable(tmp_path / "fake-model")
    manifest = _manifest("dhsvm")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "dhsvm.config").write_text("config")

    result = run_process_model(
        adapter_for_model("dhsvm"),
        manifest,
        run_dir,
        executable=executable,
    )

    assert result.returncode == 0
    assert result.peak_series.years == (2020, 2021, 2022)
    assert result.peak_series.values == (10.0, 12.5, 15.0)
    assert result.receptor_metrics["r1"]["exceedance_probability"] == 0.1
    assert Path(result.stdout_path).is_file()
    assert Path(result.stderr_path).read_text() == "fake model stderr\n"
    assert Path(run_dir / "scenario_manifest.json").is_file()
    assert DEFAULT_PEAK_FLOW_FILENAME in Path(result.output_files[0]).name
    assert result.to_dict()["peak_series"]["station_id"] == "scenario-1"


def test_run_process_model_failure_and_missing_executable(tmp_path: Path) -> None:
    manifest = _manifest("dhsvm")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "dhsvm.config").write_text("config")
    failing = _fake_executable(tmp_path / "failing-model", returncode=3)
    with pytest.raises(HydrologyProcessModelError, match="exited with 3"):
        run_process_model(
            adapter_for_model("dhsvm"),
            manifest,
            run_dir,
            executable=failing,
        )
    with pytest.raises(HydrologyProcessModelError, match="unavailable"):
        run_process_model(
            adapter_for_model("dhsvm"),
            manifest,
            run_dir,
            executable=tmp_path / "missing",
        )


def test_peak_flow_and_receptor_csv_contract(tmp_path: Path) -> None:
    sample = FloodSample("s", (2020, 2021), (10.0, 12.0))
    peak_path = write_peak_flow_series(sample, tmp_path / "peak.csv")
    loaded = read_peak_flow_series(peak_path, station_id="s", regime="rain")
    assert loaded.values == (10.0, 12.0)
    assert loaded.regime == "rain"

    metrics_path = write_receptor_metrics(
        {"r1": {"peak_flow_m3s": 12.0, "risk": 0.2}},
        tmp_path / "metrics.csv",
    )
    assert read_receptor_metrics(metrics_path)["r1"]["risk"] == 0.2

    bad_peak = tmp_path / "bad_peak.csv"
    bad_peak.write_text("year,peak_flow_m3s\n2020,-1\n")
    with pytest.raises(HydrologyProcessModelError, match="positive"):
        read_peak_flow_series(bad_peak, station_id="s")
    bad_year = tmp_path / "bad_year.csv"
    bad_year.write_text("year,peak_flow_m3s\nx,1\n")
    with pytest.raises(HydrologyProcessModelError, match="integer"):
        read_peak_flow_series(bad_year, station_id="s")
    bad_metrics = tmp_path / "bad_metrics.csv"
    bad_metrics.write_text("receptor_id,metric,value\nr1,risk,x\n")
    with pytest.raises(HydrologyProcessModelError, match="numeric"):
        read_receptor_metrics(bad_metrics)
    with pytest.raises(HydrologyProcessModelError, match="Unable to read CSV"):
        read_receptor_metrics(tmp_path / "missing.csv")


def test_parse_output_missing_and_plan_unavailable(tmp_path: Path) -> None:
    manifest = _manifest("dhsvm")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "dhsvm.config").write_text("config")
    plan = plan_process_model_run(
        adapter_for_model("dhsvm"),
        manifest,
        run_dir,
        executable=tmp_path / "missing",
    )
    assert not plan.available
    assert plan.to_dict()["available"] is False
    with pytest.raises(HydrologyProcessModelError, match="missing"):
        adapter_for_model("dhsvm").parse_outputs(run_dir, manifest)


def test_private_payload_helpers(tmp_path: Path) -> None:
    from femic.hydrology.process_models import (
        _mapping_from_object,
        _optional_mapping,
        _optional_str,
        _optional_str_list,
        _read_csv_rows,
        _read_json_object,
        _required_float,
        _required_int,
        _required_str,
        _required_str_list,
    )

    assert _optional_str(1) is None
    assert _optional_str(" x ") == "x"
    assert _optional_str_list(["a", ""], context="test") == ("a",)
    with pytest.raises(HydrologyProcessModelError, match="must be a list"):
        _optional_str_list("x", context="test")
    with pytest.raises(HydrologyProcessModelError, match="must be strings"):
        _optional_str_list([1], context="test")
    assert _optional_mapping(None, context="test") == {}
    with pytest.raises(HydrologyProcessModelError, match="must be an object"):
        _optional_mapping("x", context="test")
    with pytest.raises(HydrologyProcessModelError, match="must be an object"):
        _mapping_from_object("x", context="test")
    with pytest.raises(HydrologyProcessModelError, match="non-empty string"):
        _required_str({"v": " "}, "v", context="test")
    with pytest.raises(HydrologyProcessModelError, match="must be a list"):
        _required_str_list("x", context="test")
    with pytest.raises(HydrologyProcessModelError, match="non-empty strings"):
        _required_str_list(["", 1], context="test")
    with pytest.raises(HydrologyProcessModelError, match="numeric"):
        _required_float({"v": "x"}, "v", context="test")
    with pytest.raises(HydrologyProcessModelError, match="integer"):
        _required_int({"v": "x"}, "v", context="test")
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    assert _read_csv_rows(empty) == ()
    with pytest.raises(HydrologyProcessModelError, match="Unable to read"):
        _read_json_object(tmp_path / "missing.json", context="test")
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json")
    with pytest.raises(HydrologyProcessModelError, match="Invalid JSON"):
        _read_json_object(invalid, context="test")
    array = tmp_path / "array.json"
    array.write_text("[]")
    with pytest.raises(HydrologyProcessModelError, match="JSON object"):
        _read_json_object(array, context="test")
