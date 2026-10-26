from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from femic.hydrology.validation import (  # type: ignore[import-untyped]
    load_pilot_annual_maxima,
    load_pilot_gauges,
)

FIXTURE = Path("tests/fixtures/hydrology/chapman_gauges")


def _backcast_module() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[1] / "scripts" / "backcast_chapman_gauges.py"
    )
    spec = importlib.util.spec_from_file_location("backcast_chapman_gauges", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the Chapman backcast script.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backcast = _backcast_module()


def test_fixture_has_three_sequential_stations() -> None:
    gauges = load_pilot_gauges(FIXTURE / "gauges.json")
    rows = load_pilot_annual_maxima(FIXTURE / "annual_maxima.csv")

    assert [gauge.station_number for gauge in gauges] == [
        "08GA046",
        "08GA060",
        "08GA078",
    ]
    assert len(rows) == 40
    assert sum(row.station_number == "08GA046" for row in rows) == 11
    assert sum(row.station_number == "08GA060" for row in rows) == 18
    assert sum(row.station_number == "08GA078" for row in rows) == 11


def test_backcast_is_historical_only_and_not_pooled() -> None:
    result = backcast.backcast_chapman(
        FIXTURE,
        bootstrap_samples=10,
        seed=42,
        generated_utc="2026-10-26T00:00:00+00:00",
    )

    assert result["schema_version"] == backcast.SCHEMA_VERSION
    stations = result["stations"]
    assert isinstance(stations, list)
    assert len(stations) == 3
    for station in stations:
        assert station["year_count"] >= 11
        assert set(station["usable_fits"]) == {"gev", "lp3"}
        assert station["fits"]["gev"]["quantiles"][-1] > 0
        assert station["fits"]["lp3"]["quantiles"][-1] > 0
    decision = result["decision"]
    assert isinstance(decision, dict)
    assert decision["status"] == "historical_gauge_frequency_only"
    assert decision["current_baseline"] is False
    assert decision["flood_map"] is False
    structure = result["record_structure"]
    assert isinstance(structure, dict)
    assert structure["pooled_record"] is False
    assert structure["overlapping_years"] == [1970]
    assert "1988-1992" in structure["gaps"]


def test_cli_writes_backcast(tmp_path: Path) -> None:
    output = tmp_path / "backcast.json"
    code = backcast.main(
        [
            "--fixture-root",
            str(FIXTURE),
            "--output",
            str(output),
            "--bootstrap-samples",
            "10",
            "--generated-utc",
            "2026-10-26T00:00:00+00:00",
        ]
    )
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["decision"]["status"] == "historical_gauge_frequency_only"
    assert payload["fixture"]["gauges_sha256"]
