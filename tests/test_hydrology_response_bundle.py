from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from femic.cli.main import app
from femic.hydrology.disturbance import (
    load_disturbance_ledger,
    validate_disturbance_ledger,
)
from femic.hydrology.domain import (
    load_hydrology_domain_manifest,
    validate_hydrology_domain,
)
from femic.hydrology.response_bundle import (
    HYDROLOGY_RESPONSE_PLAN_SCHEMA_VERSION,
    FloodRiskRow,
    HydrologyResponseError,
    HydrologyResponsePlan,
    ResponseArtifactSpec,
    audit_hydrology_response_bundle,
    build_flood_risk_table,
    build_hydrology_response_bundle,
    load_hydrology_response_manifest,
    load_hydrology_response_plan,
    read_flood_risk_table,
    validate_hydrology_response_bundle,
    validate_hydrology_response_plan,
    write_flood_risk_table,
    write_hydrology_response_plan,
)
from femic.hydrology.surrogate import load_surrogate

FIXTURE_ROOT = Path("tests/fixtures/hydrology/response_bundle")
PLAN_PATH = FIXTURE_ROOT / "response_plan.json"
runner = CliRunner()
GENERATED_UTC = "2026-10-25T12:00:00+00:00"


def _build(tmp_path: Path, name: str = "bundle") -> Path:
    result = build_hydrology_response_bundle(
        PLAN_PATH,
        tmp_path / name,
        generated_utc=GENERATED_UTC,
    )
    return result.bundle_dir


def test_fixture_provenance_artifacts_validate() -> None:
    domain = load_hydrology_domain_manifest(FIXTURE_ROOT / "domain.json")
    ledger = load_disturbance_ledger(FIXTURE_ROOT / "disturbance.json")
    model = load_surrogate(FIXTURE_ROOT / "surrogate_model.json")

    assert validate_hydrology_domain(domain).is_valid
    assert validate_disturbance_ledger(ledger).is_valid
    assert model.family == "linear"


def test_fixture_plan_loads_with_expected_roles() -> None:
    plan = load_hydrology_response_plan(PLAN_PATH)

    assert plan.schema_version == HYDROLOGY_RESPONSE_PLAN_SCHEMA_VERSION
    assert plan.domain_id == "fixture-domain"
    assert plan.ledger_id == "fixture-ledger"
    assert plan.response_surface_id == "fixture-surface"
    assert validate_hydrology_response_plan(plan) == ()
    assert {artifact.role for artifact in plan.artifacts} == {
        "response_surface",
        "flood_risk",
        "surrogate_model",
        "surrogate_validation",
        "domain",
        "disturbance_ledger",
    }


def test_build_response_bundle_is_deterministic_and_complete(tmp_path: Path) -> None:
    first = build_hydrology_response_bundle(
        PLAN_PATH,
        tmp_path / "first",
        generated_utc=GENERATED_UTC,
    )
    second = build_hydrology_response_bundle(
        PLAN_PATH,
        tmp_path / "second",
        generated_utc=GENERATED_UTC,
    )

    assert first.manifest.bundle_id == second.manifest.bundle_id
    assert first.manifest.bundle_id.startswith("hydro-response-")
    assert first.manifest.bundle_name == (f"{first.manifest.bundle_id}-2026.10.0")
    assert first.manifest.generated_utc == GENERATED_UTC
    assert first.manifest.response_surface["baseline_name"] == "baseline"
    assert first.manifest.flood_risk["row_count"] == 2
    assert first.manifest.applicability_domain["max_distance"] == 3.0
    assert first.manifest.uncertainty["coverage_95"] == 0.93
    assert first.manifest.uncertainty["basis"] == "synthetic held-out validation"
    assert first.manifest.consumer_contract["consumer_phases"] == {
        "ws4": "P49",
        "fhops": "P14",
    }
    assert (first.bundle_dir / "manifest.json").is_file()
    assert (first.bundle_dir / "provenance" / "response_plan.json").is_file()
    assert all(
        (first.bundle_dir / artifact.relative_path).is_file()
        for artifact in first.manifest.artifacts
    )

    loaded = load_hydrology_response_manifest(first.manifest_path)
    assert loaded.bundle_id == first.manifest.bundle_id
    assert validate_hydrology_response_bundle(loaded) == ()


def test_audit_verifies_checksums_and_reports_completeness(tmp_path: Path) -> None:
    bundle_dir = _build(tmp_path)

    audit = audit_hydrology_response_bundle(
        bundle_dir,
        checked_utc=GENERATED_UTC,
    )

    assert audit.is_valid
    assert audit.is_complete
    assert audit.errors == ()
    assert audit.checked_utc == GENERATED_UTC
    assert len(audit.artifacts) == 6
    assert all(item.exists for item in audit.artifacts)
    assert all(item.checksum_ok for item in audit.artifacts)


def test_audit_detects_tampered_artifact(tmp_path: Path) -> None:
    bundle_dir = _build(tmp_path)
    surface = bundle_dir / "artifacts" / "response_surface" / "response_surface.json"
    surface.write_text(surface.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    audit = audit_hydrology_response_bundle(bundle_dir)

    assert not audit.is_valid
    assert any("size mismatch" in error for error in audit.errors)
    assert any("checksum mismatch" in error for error in audit.errors)


def test_build_refuses_to_overwrite_non_bundle_directory(tmp_path: Path) -> None:
    output = tmp_path / "not-a-bundle"
    output.mkdir()
    (output / "keep.txt").write_text("user data", encoding="utf-8")

    with pytest.raises(HydrologyResponseError, match="Refusing to overwrite"):
        build_hydrology_response_bundle(PLAN_PATH, output, overwrite=True)


def test_build_requires_overwrite_for_existing_bundle(tmp_path: Path) -> None:
    bundle_dir = _build(tmp_path)

    with pytest.raises(HydrologyResponseError, match="not empty"):
        build_hydrology_response_bundle(
            PLAN_PATH,
            bundle_dir,
            generated_utc=GENERATED_UTC,
        )

    replaced = build_hydrology_response_bundle(
        PLAN_PATH,
        bundle_dir,
        overwrite=True,
        generated_utc=GENERATED_UTC,
    )
    assert replaced.bundle_dir == bundle_dir
    assert audit_hydrology_response_bundle(bundle_dir).is_valid


def test_plan_validation_requires_roles_and_matching_schemas(tmp_path: Path) -> None:
    plan = HydrologyResponsePlan(
        bundle_version="2026.10.0",
        domain_id="domain",
        ledger_id="ledger",
        response_surface_id="surface",
        artifacts=(
            ResponseArtifactSpec(
                role="response_surface",
                path="surface.json",
                schema_version="femic.hydrology.flood_response.v1",
            ),
        ),
    )
    errors = validate_hydrology_response_plan(plan)
    assert any("missing required artifact roles" in error for error in errors)
    assert any("flood_risk" in error for error in errors)

    invalid = HydrologyResponsePlan(
        bundle_version="2026.10.0",
        domain_id="domain",
        ledger_id="ledger",
        response_surface_id="surface",
        artifacts=(
            ResponseArtifactSpec(
                role="response_surface",
                path="surface.json",
                schema_version="femic.hydrology.wrong.v1",
            ),
        ),
    )
    assert any(
        "does not match" in error for error in validate_hydrology_response_plan(invalid)
    )


def test_plan_writer_round_trip(tmp_path: Path) -> None:
    plan = load_hydrology_response_plan(PLAN_PATH)
    path = write_hydrology_response_plan(plan, tmp_path / "plan.json")

    assert load_hydrology_response_plan(path) == plan


def test_flood_risk_table_round_trip_and_validation(tmp_path: Path) -> None:
    table = build_flood_risk_table(
        (
            FloodRiskRow(
                receptor_id="receptor-1",
                watershed_id="watershed-1",
                return_period=100.0,
                baseline_peak_flow_m3s=120.0,
                scenario_peak_flow_m3s=150.0,
                ratio=1.25,
                exceedance_probability=0.01,
                expected_annual_damage=42000.0,
            ),
        ),
        source_surface_id="surface",
        baseline_name="baseline",
        generated_utc=GENERATED_UTC,
    )
    path = write_flood_risk_table(table, tmp_path / "risk.json")

    assert table.table_id.startswith("hydro-risk-")
    assert read_flood_risk_table(path) == table

    with pytest.raises(HydrologyResponseError, match="ratio"):
        build_flood_risk_table(
            (
                FloodRiskRow(
                    receptor_id="receptor-1",
                    watershed_id="watershed-1",
                    return_period=100.0,
                    baseline_peak_flow_m3s=120.0,
                    scenario_peak_flow_m3s=150.0,
                    ratio=1.0,
                ),
            ),
            source_surface_id="surface",
            baseline_name="baseline",
        )


def test_flood_risk_table_rejects_duplicate_receptor_period() -> None:
    row = FloodRiskRow(
        receptor_id="receptor-1",
        watershed_id="watershed-1",
        return_period=100.0,
        baseline_peak_flow_m3s=120.0,
        scenario_peak_flow_m3s=150.0,
        ratio=1.25,
    )

    with pytest.raises(HydrologyResponseError, match="Duplicate"):
        build_flood_risk_table(
            (row, row),
            source_surface_id="surface",
            baseline_name="baseline",
        )


def test_cli_build_and_inspect(tmp_path: Path) -> None:
    output = tmp_path / "cli-bundle"

    build = runner.invoke(
        app,
        [
            "hydrology",
            "bundle",
            "--plan",
            str(PLAN_PATH),
            "--output-dir",
            str(output),
            "--generated-utc",
            GENERATED_UTC,
        ],
    )
    assert build.exit_code == 0, build.output
    assert "bundle_id: hydro-response-" in build.stdout

    inspect = runner.invoke(
        app,
        [
            "hydrology",
            "inspect",
            str(output),
            "--json",
            "--checked-utc",
            GENERATED_UTC,
        ],
    )
    assert inspect.exit_code == 0, inspect.output
    payload = json.loads(inspect.stdout)
    assert payload["is_valid"] is True
    assert payload["is_complete"] is True
    assert len(payload["artifacts"]) == 6


def test_cli_inspect_fails_for_tampered_bundle(tmp_path: Path) -> None:
    bundle_dir = _build(tmp_path)
    surface = bundle_dir / "artifacts" / "response_surface" / "response_surface.json"
    surface.write_text("{}\n", encoding="utf-8")

    inspect = runner.invoke(app, ["hydrology", "inspect", str(bundle_dir)])

    assert inspect.exit_code == 1
    assert "checksum mismatch" in inspect.stdout


def test_build_rejects_missing_artifact(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    shutil.copytree(FIXTURE_ROOT, fixture)
    (fixture / "surrogate_validation.json").unlink()

    with pytest.raises(HydrologyResponseError, match="missing"):
        build_hydrology_response_bundle(
            fixture / "response_plan.json",
            tmp_path / "bundle",
            generated_utc=GENERATED_UTC,
        )


def test_build_rejects_artifact_schema_mismatch(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    shutil.copytree(FIXTURE_ROOT, fixture)
    surface_path = fixture / "response_surface.json"
    payload = json.loads(surface_path.read_text(encoding="utf-8"))
    payload["schema_version"] = "femic.hydrology.wrong.v1"
    surface_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HydrologyResponseError, match="expected"):
        build_hydrology_response_bundle(
            fixture / "response_plan.json",
            tmp_path / "bundle",
            generated_utc=GENERATED_UTC,
        )


def test_build_rejects_response_surface_id_mismatch(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    shutil.copytree(FIXTURE_ROOT, fixture)
    surface_path = fixture / "response_surface.json"
    payload = json.loads(surface_path.read_text(encoding="utf-8"))
    payload["surface_id"] = "different-surface"
    surface_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HydrologyResponseError, match="surface ID"):
        build_hydrology_response_bundle(
            fixture / "response_plan.json",
            tmp_path / "bundle",
            generated_utc=GENERATED_UTC,
        )


def test_audit_reports_missing_artifact(tmp_path: Path) -> None:
    bundle_dir = _build(tmp_path)
    (bundle_dir / "artifacts" / "domain" / "domain.json").unlink()

    audit = audit_hydrology_response_bundle(bundle_dir)

    assert not audit.is_valid
    assert any(
        "missing file" in issue for item in audit.artifacts for issue in item.issues
    )
    assert any("missing" in error for error in audit.errors)


def test_manifest_validation_requires_consumer_contract(tmp_path: Path) -> None:
    bundle_dir = _build(tmp_path)
    manifest = load_hydrology_response_manifest(bundle_dir)
    broken = replace(manifest, consumer_contract={"manifest_path": "manifest.json"})

    errors = validate_hydrology_response_bundle(broken)

    assert any("Consumer contract" in error for error in errors)
    assert any("consumer_phases" in error for error in errors)


def test_load_plan_rejects_unsupported_schema(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "femic.hydrology.response_plan.v99",
                "bundle_version": "1",
                "domain_id": "d",
                "ledger_id": "l",
                "response_surface_id": "s",
                "artifacts": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(HydrologyResponseError, match="Unsupported"):
        load_hydrology_response_plan(path)


def test_read_risk_table_rejects_unsupported_schema(tmp_path: Path) -> None:
    payload = json.loads((FIXTURE_ROOT / "flood_risk.json").read_text(encoding="utf-8"))
    payload["schema_version"] = "femic.hydrology.flood_risk.v99"
    path = tmp_path / "risk.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HydrologyResponseError, match="Unsupported"):
        read_flood_risk_table(path)


def test_plan_rejects_absolute_and_parent_artifact_paths() -> None:
    plan = HydrologyResponsePlan(
        bundle_version="1",
        domain_id="d",
        ledger_id="l",
        response_surface_id="s",
        artifacts=(
            ResponseArtifactSpec(
                role="response_surface",
                path="/tmp/surface.json",
                schema_version="femic.hydrology.flood_response.v1",
            ),
            ResponseArtifactSpec(
                role="flood_risk",
                path="../risk.json",
                schema_version="femic.hydrology.flood_risk.v1",
            ),
            ResponseArtifactSpec(
                role="domain",
                path="domain.json",
                schema_version="femic.hydrology.domain.v1",
            ),
            ResponseArtifactSpec(
                role="disturbance_ledger",
                path="ledger.json",
                schema_version="femic.hydrology.disturbance.v1",
            ),
        ),
    )

    errors = validate_hydrology_response_plan(plan)

    assert any("must be relative" in error for error in errors)
    assert any("traverse parent" in error for error in errors)


def test_build_rejects_flood_risk_source_surface_mismatch(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    shutil.copytree(FIXTURE_ROOT, fixture)
    risk_path = fixture / "flood_risk.json"
    payload = json.loads(risk_path.read_text(encoding="utf-8"))
    payload["source_surface_id"] = "different-surface"
    risk_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HydrologyResponseError, match="source surface"):
        build_hydrology_response_bundle(
            fixture / "response_plan.json",
            tmp_path / "bundle",
            generated_utc=GENERATED_UTC,
        )


def test_build_rejects_domain_and_ledger_id_mismatch(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    shutil.copytree(FIXTURE_ROOT, fixture)
    domain_path = fixture / "domain.json"
    domain_payload = json.loads(domain_path.read_text(encoding="utf-8"))
    domain_payload["domain_id"] = "different-domain"
    domain_path.write_text(json.dumps(domain_payload), encoding="utf-8")

    with pytest.raises(HydrologyResponseError, match="Domain artifact ID"):
        build_hydrology_response_bundle(
            fixture / "response_plan.json",
            tmp_path / "bundle",
            generated_utc=GENERATED_UTC,
        )

    shutil.copytree(FIXTURE_ROOT, fixture / "ledger-case")
    ledger_path = fixture / "ledger-case" / "disturbance.json"
    ledger_payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger_payload["ledger_id"] = "different-ledger"
    ledger_path.write_text(json.dumps(ledger_payload), encoding="utf-8")

    with pytest.raises(HydrologyResponseError, match="ledger ID"):
        build_hydrology_response_bundle(
            fixture / "ledger-case" / "response_plan.json",
            tmp_path / "ledger-bundle",
            generated_utc=GENERATED_UTC,
        )


def test_read_risk_table_rejects_summary_mismatch(tmp_path: Path) -> None:
    payload = json.loads((FIXTURE_ROOT / "flood_risk.json").read_text(encoding="utf-8"))
    payload["summary"]["row_count"] = 99
    path = tmp_path / "risk.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HydrologyResponseError, match="summary row count"):
        read_flood_risk_table(path)
