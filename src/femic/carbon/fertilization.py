"""Public-data fertilization response and emissions audit.

The growth response is a temporary speedup of an existing FEMIC yield curve,
matching the curve construction used by the patchworks fertilization states. The
emission factors are the public thesis values recorded in
``config/carbon/fertilization.bc.yaml``.
"""

from __future__ import annotations

import hashlib
import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd
import yaml


@dataclass(frozen=True)
class FertilizationConfig:
    """Fertilization response and emissions assumptions.

    Attributes
    ----------
    schema_version : str
        Configuration schema version.
    dose_kg_n_ha : float
        Nitrogen application dose.
    response_years : int
        Duration of the growth response in years.
    speedup_fraction : float
        Annual curve-age speedup during the response.
    co2_kg_ha : float
        CO2 emissions per fertilized hectare per action.
    ch4_kg_ha : float
        CH4 emissions per fertilized hectare per action.
    n2o_kg_ha : dict of str to float
        N2O emissions per fertilized hectare by application count (f1/f2/f3).
    gwp_ch4 : float
        GWP100 for CH4 used by the audit.
    gwp_n2o : float
        GWP100 for N2O used by the audit.
    response_method : str
        Growth-response method (``tipsy_mof_response``).
    response_file : Path or None
        Public TIPSY response file.
    response_sha256 : str or None
        Expected response-file digest.
    effectiveness : float
        Applied effectiveness fraction.
    source : dict
        Source metadata.
    """

    schema_version: str
    dose_kg_n_ha: float
    response_years: int
    speedup_fraction: float
    co2_kg_ha: float
    ch4_kg_ha: float
    n2o_kg_ha: dict[str, float]
    gwp_ch4: float
    gwp_n2o: float
    response_method: str
    response_file: Path | None
    response_sha256: str | None
    effectiveness: float
    source: dict[str, Any]


@dataclass(frozen=True)
class FertilizationAuditResult:
    """Accounts and totals from a fertilization audit.

    Attributes
    ----------
    accounts : pandas.DataFrame
        ``offset``, ``account``, and ``value`` rows.
    total_area_ha : float
        Fertilized area in the schedule.
    total_co2e_t : float
        Total CO2e emissions in tonnes.
    source_schedule : Path
        Schedule used by the audit.
    """

    accounts: pd.DataFrame
    total_area_ha: float
    total_co2e_t: float
    source_schedule: Path


def load_fertilization_config(path: Path) -> FertilizationConfig:
    """Load and validate a fertilization config.

    Parameters
    ----------
    path : Path
        YAML config path.

    Returns
    -------
    FertilizationConfig
        The validated assumptions.

    Raises
    ------
    FileNotFoundError
        When the config is missing.
    ValueError
        When required fields are malformed.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"fertilization config not found: {source}")
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise TypeError(f"{source} must contain a YAML mapping")
    factors = payload.get("factors_kg_ha") or {}
    if not isinstance(factors, dict):
        raise TypeError(f"{source}: factors_kg_ha must be a mapping")
    gwp = payload.get("gwp100") or {}
    if not isinstance(gwp, dict):
        raise TypeError(f"{source}: gwp100 must be a mapping")
    growth = payload.get("growth_response") or {}
    if not isinstance(growth, dict):
        raise TypeError(f"{source}: growth_response must be a mapping")
    n2o = {
        "f1": float(factors.get("n2o_once", 20.00206748)),
        "f2": float(factors.get("n2o_twice", 40.00206748)),
        "f3": float(factors.get("n2o_thrice", 60.00206748)),
    }
    config = FertilizationConfig(
        schema_version=str(payload.get("schema_version", "0.1")),
        dose_kg_n_ha=float(payload.get("dose_kg_n_ha", 200)),
        response_years=int(payload.get("response_years", 10)),
        speedup_fraction=float(growth.get("speedup_fraction", 0.10)),
        co2_kg_ha=float(factors.get("co2", 17.13779467)),
        ch4_kg_ha=float(factors.get("ch4", 0.055734646)),
        n2o_kg_ha=n2o,
        gwp_ch4=float(gwp.get("ch4", 27.9)),
        gwp_n2o=float(gwp.get("n2o", 273.0)),
        response_method=str(growth.get("method", "tipsy_mof_response")),
        response_file=(
            (source.parent / str(growth["response_file"])).resolve()
            if growth.get("response_file")
            else None
        ),
        response_sha256=(
            str(growth["response_file_sha256"])
            if growth.get("response_file_sha256")
            else None
        ),
        effectiveness=float(growth.get("effectiveness", 0.8)),
        source=(
            cast(dict[str, Any], payload.get("source"))
            if isinstance(payload.get("source"), dict)
            else {}
        ),
    )
    if config.response_years <= 0:
        raise ValueError("fertilization response_years must be positive")
    if config.speedup_fraction < 0:
        raise ValueError("fertilization speedup_fraction must be non-negative")
    if config.dose_kg_n_ha <= 0:
        raise ValueError("fertilization dose_kg_n_ha must be positive")
    if not 0.0 <= config.effectiveness <= 1.0:
        raise ValueError("fertilization effectiveness must be between 0 and 1")
    if config.response_file is not None:
        if not config.response_file.is_file():
            raise FileNotFoundError(
                f"fertilization response file not found: {config.response_file}"
            )
        if config.response_sha256 is not None:
            digest = hashlib.sha256(config.response_file.read_bytes()).hexdigest()
            if digest != config.response_sha256:
                raise ValueError(
                    "fertilization response file hash mismatch: "
                    f"expected {config.response_sha256}, got {digest}"
                )
    return config


@dataclass(frozen=True)
class TipsyFertilizationResponse:
    """Public TIPSY MOF fertilization response tables.

    Attributes
    ----------
    tables : dict
        ``(species_code, bec, site_index)`` to ``(age, pervol)`` rows.
    path : Path
        Source file.
    sha256 : str
        Source digest.
    """

    tables: dict[tuple[str, str, int], tuple[tuple[int, float], ...]]
    path: Path
    sha256: str


def load_tipsy_fertilization_response(path: Path) -> TipsyFertilizationResponse:
    """Parse a TIPSY ``FertRespMOF.txt`` file.

    Parameters
    ----------
    path : Path
        Public TIPSY response file.

    Returns
    -------
    TipsyFertilizationResponse
        Parsed response tables.

    Raises
    ------
    FileNotFoundError
        When the file is missing.
    ValueError
        When a section or row is malformed.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"TIPSY fertilization response not found: {source}")
    tables: dict[tuple[str, str, int], tuple[tuple[int, float], ...]] = {}
    current: tuple[str, str, int] | None = None
    rows: list[tuple[int, float]] = []
    for raw in source.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("'"):
            continue
        if line.startswith(("$", "#")):
            continue
        if line.startswith("["):
            if current is not None:
                tables[current] = tuple(rows)
            block = line.strip("[]").split(",")
            if len(block) < 3:
                raise ValueError(f"{source}: malformed response section {line!r}")
            species = block[1].strip().upper()
            bec = block[3].strip().upper() if len(block) > 3 else ""
            try:
                site_index = int(float(block[2]))
            except ValueError as exc:
                raise ValueError(f"{source}: invalid site index in {line!r}") from exc
            current = (species, bec, site_index)
            rows = []
            continue
        if current is None:
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            age = int(float(parts[1]))
            pervol = float(parts[3])
        except ValueError:
            continue
        rows.append((age, pervol))
    if current is not None:
        tables[current] = tuple(rows)
    if not tables:
        raise ValueError(f"{source}: no response tables found")
    return TipsyFertilizationResponse(
        tables=tables,
        path=source,
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    )


def tipsy_response_percent(
    response: TipsyFertilizationResponse,
    *,
    species_code: str,
    site_index: int,
    response_age: int,
    bec: str = "",
) -> float:
    """Return the interpolated percent volume gain at a fertilization age.

    Parameters
    ----------
    response : TipsyFertilizationResponse
        Parsed response tables.
    species_code : str
        TIPSY species code (``FDC``, ``SS``, ``SW``, ``PLI``, ``FDI``).
    site_index : int
        Site index.
    response_age : int
        Fertilization age.
    bec : str, optional
        BEC zone for response tables that are zone-specific (``FDI``).

    Returns
    -------
    float
        Percent volume gain. Zero when no matching species table exists.
    """
    species = species_code.strip().upper()
    bec_value = bec.strip().upper()
    candidates = [
        key
        for key in response.tables
        if key[0] == species and (not bec_value or key[1] in {"", bec_value})
    ]
    if not candidates:
        return 0.0
    if any(key[1] == bec_value for key in candidates):
        candidates = [key for key in candidates if key[1] == bec_value]
    elif any(key[1] == "" for key in candidates):
        candidates = [key for key in candidates if key[1] == ""]
    by_si = sorted((key, response.tables[key]) for key in candidates)
    lower = max((item for item in by_si if item[0][2] <= site_index), default=by_si[0])
    upper = min((item for item in by_si if item[0][2] >= site_index), default=by_si[-1])
    lower_value = _response_at_age(lower[1], response_age)
    if upper[0][2] == lower[0][2]:
        return lower_value
    upper_value = _response_at_age(upper[1], response_age)
    weight = (site_index - lower[0][2]) / (upper[0][2] - lower[0][2])
    return lower_value + (upper_value - lower_value) * weight


def fertilized_curve(
    *,
    curve: tuple[tuple[float, float], ...],
    response_age: int,
    config: FertilizationConfig,
    species_code: str | None = None,
    site_index: int | None = None,
    bec: str = "",
) -> tuple[tuple[float, float], ...]:
    """Apply the public temporary growth-speedup response to a curve.

    This mirrors the patchworks fertilization curve: after ``response_age`` the
    curve is sampled ahead by ``speedup_fraction`` per year, up to
    ``speedup_fraction * response_years`` years.

    Parameters
    ----------
    curve : tuple of (float, float)
        Base age/volume curve.
    response_age : int
        Age at which the response begins.
    config : FertilizationConfig
        Response assumptions.
    species_code : str or None, optional
        TIPSY species code for the public MOF response table.
    site_index : int or None, optional
        Site index for the public MOF response table.
    bec : str, optional
        BEC zone for zone-specific response tables.

    Returns
    -------
    tuple of (float, float)
        Fertilized curve on the same age grid.
    """
    if not curve:
        raise ValueError("fertilized_curve requires a non-empty curve")
    if response_age < 0:
        raise ValueError("response_age must be non-negative")
    ordered = tuple(sorted((float(x), float(y)) for x, y in curve))
    if (
        config.response_method == "tipsy_mof_response"
        and config.response_file is not None
        and species_code
        and site_index is not None
    ):
        response = load_tipsy_fertilization_response(config.response_file)
        percent = tipsy_response_percent(
            response,
            species_code=species_code,
            site_index=site_index,
            response_age=response_age,
            bec=bec,
        )
        if percent <= 0:
            return ordered
        total_fraction = (percent / 100.0) * config.effectiveness
        result: list[tuple[float, float]] = []
        for x_value, y_value in ordered:
            if x_value >= response_age:
                elapsed = min(
                    float(config.response_years),
                    max(0.0, x_value - float(response_age)),
                )
                ramp = elapsed / float(config.response_years)
                y_value = y_value * (1.0 + total_fraction * ramp)
            result.append((x_value, y_value))
        return tuple(result)
    max_shift = config.speedup_fraction * config.response_years
    result = []
    for x_value, _ in ordered:
        sample_x = x_value
        if x_value >= response_age and max_shift > 0:
            elapsed = max(0.0, x_value - response_age)
            shift = min(max_shift, elapsed * config.speedup_fraction)
            sample_x = x_value + shift
        result.append((x_value, _interpolate(ordered, sample_x)))
    return tuple(result)


def fertilization_audit(
    *,
    schedule: pd.DataFrame,
    block_areas: pd.DataFrame,
    config: FertilizationConfig,
) -> FertilizationAuditResult:
    """Compute fertilization emissions from a schedule and block areas.

    Parameters
    ----------
    schedule : pandas.DataFrame
        Schedule with ``block_id``, ``treatment``, and ``offset``.
    block_areas : pandas.DataFrame
        Blocks with ``block_id`` and ``area_ha``.
    config : FertilizationConfig
        Emission assumptions.

    Returns
    -------
    FertilizationAuditResult
        Accounts and totals. Only ``f1``, ``f2``, and ``f3`` rows are audited;
        other treatments are ignored.
    """
    required = {"block_id", "treatment", "offset"}
    missing = sorted(required.difference(schedule.columns))
    if missing:
        raise ValueError(f"schedule is missing columns: {missing}")
    if not {"block_id", "area_ha"}.issubset(block_areas.columns):
        raise ValueError("block_areas must contain block_id and area_ha")
    areas = (
        block_areas.assign(
            block_id=pd.to_numeric(block_areas["block_id"], errors="raise").astype(int),
            area_ha=pd.to_numeric(block_areas["area_ha"], errors="raise").astype(float),
        )
        .groupby("block_id", as_index=True)["area_ha"]
        .sum()
    )
    frame = schedule.copy()
    frame["treatment"] = frame["treatment"].astype(str).str.strip().str.lower()
    frame = frame.loc[frame["treatment"].isin({"f1", "f2", "f3"})]
    if frame.empty:
        return FertilizationAuditResult(
            accounts=pd.DataFrame(columns=["offset", "account", "value"]),
            total_area_ha=0.0,
            total_co2e_t=0.0,
            source_schedule=Path("<memory>"),
        )
    frame["block_id"] = pd.to_numeric(frame["block_id"], errors="raise").astype(int)
    frame["offset"] = pd.to_numeric(frame["offset"], errors="raise").astype(int)
    missing_blocks = sorted(set(frame["block_id"]).difference(areas.index))
    if missing_blocks:
        raise ValueError(f"schedule blocks have no area: {missing_blocks[:5]}")
    frame["area_ha"] = frame["block_id"].map(areas)
    rows: list[dict[str, object]] = []
    for offset, group in frame.groupby(["offset", "treatment"], sort=True):
        offset_value = int(str(offset[0]))
        treatment = str(offset[1])
        area = float(group["area_ha"].sum())
        co2 = area * config.co2_kg_ha / 1000.0
        ch4 = area * config.ch4_kg_ha / 1000.0
        n2o = area * config.n2o_kg_ha[treatment] / 1000.0
        co2e = co2 + ch4 * config.gwp_ch4 + n2o * config.gwp_n2o
        values = {
            "fertilization.area_ha": area,
            "fertilization.dose_kg_n": area * config.dose_kg_n_ha,
            "fertilization.co2_t": co2,
            "fertilization.ch4_t": ch4,
            "fertilization.n2o_t": n2o,
            "fertilization.co2e_t": co2e,
        }
        for account, value in values.items():
            rows.append(
                {"offset": int(offset_value), "account": account, "value": value}
            )
    accounts = pd.DataFrame(rows)
    if not accounts.empty:
        accounts = pd.DataFrame(
            accounts.groupby(["offset", "account"], as_index=False)["value"].sum()
        )
    total_area = float(frame["area_ha"].sum())
    total_co2e = float(
        accounts.loc[accounts["account"] == "fertilization.co2e_t", "value"].sum()
    )
    return FertilizationAuditResult(
        accounts=accounts,
        total_area_ha=total_area,
        total_co2e_t=total_co2e,
        source_schedule=Path("<memory>"),
    )


def write_fertilization_audit(
    result: FertilizationAuditResult, output_dir: Path
) -> Path:
    """Write the audit accounts and a manifest.

    Parameters
    ----------
    result : FertilizationAuditResult
        Audit result.
    output_dir : Path
        Destination directory.

    Returns
    -------
    Path
        The accounts CSV.
    """
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    accounts_path = root / "fertilization_accounts.csv"
    result.accounts.to_csv(accounts_path, index=False)
    manifest = {
        "source_schedule": str(result.source_schedule),
        "total_area_ha": result.total_area_ha,
        "total_co2e_t": result.total_co2e_t,
        "note": (
            "Emissions audit only; growth response is a public curve speedup and "
            "is not added to CBM pools by this writer."
        ),
    }
    (root / "fertilization_manifest.json").write_text(
        pd.Series(manifest).to_json(indent=2), encoding="utf-8"
    )
    return accounts_path


def _response_at_age(rows: tuple[tuple[int, float], ...], age: int) -> float:
    """Interpolate percent response at an age."""
    if not rows:
        return 0.0
    ordered = sorted(rows)
    if age <= ordered[0][0]:
        return ordered[0][1]
    if age >= ordered[-1][0]:
        return ordered[-1][1]
    for (age0, value0), (age1, value1) in itertools.pairwise(ordered):
        if age0 <= age <= age1:
            if age1 == age0:
                return value1
            return value0 + (value1 - value0) * (age - age0) / (age1 - age0)
    return ordered[-1][1]


def _interpolate(curve: tuple[tuple[float, float], ...], x: float) -> float:
    """Linearly interpolate a curve at x, clamping outside the range."""
    if x <= curve[0][0]:
        return curve[0][1]
    if x >= curve[-1][0]:
        return curve[-1][1]
    for (x0, y0), (x1, y1) in itertools.pairwise(curve):
        if x0 <= x <= x1:
            if x1 == x0:
                return y1
            weight = (x - x0) / (x1 - x0)
            return y0 + (y1 - y0) * weight
    return curve[-1][1]
