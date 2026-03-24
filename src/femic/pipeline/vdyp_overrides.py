"""Tracked VDYP fit-override policy loading for TSA/stratum/SI smoothing."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import yaml

CurveOverrideKey = tuple[str, str]
CurveOverrideKwargs = dict[str, Any]
CurveOverrideMap = dict[CurveOverrideKey, CurveOverrideKwargs]

DEFAULT_VDYP_FIT_POLICY_RELATIVE_PATH = Path("config/vdyp_fit_policy.yaml")
INSTANCE_VDYP_FIT_POLICY_RELATIVE_PATH = Path("config/vdyp_fit_policy.yaml")
_POLICY_VERSION = 1

# Narrow fallback seam used only if the tracked shared YAML defaults are missing
# or malformed in the active source checkout.
DEFAULT_VDYP_KWARG_OVERRIDES: dict[str, CurveOverrideMap] = {
    "08": {
        ("BWBS_SB", "H"): {"skip1": 30},
        ("BWBS_S", "L"): {"skip1": 50},
        ("SWB_S", "L"): {"skip1": 30},
        ("BWBS_AT", "H"): {"skip1": 30},
    },
    "16": {("SWB_SX", "L"): {"skip1": 30}},
    "24": {("ESSF_BL", "L"): {"skip1": 30}},
    "40": {
        ("BWBS_SX", "L"): {"skip1": 30},
        ("SWB_SX", "L"): {"skip1": 60, "dx_c1": 1.0, "dx_c2": 0.0},
    },
    "41": {("ESSF_BL", "L"): {"skip1": 60}, ("ESSF_SE", "M"): {"skip1": 30}},
    # TSA29: suppress pathological early-age spike for SBPS_PL low-SI curve.
    "29": {("SBPS_PL", "L"): {"skip1": 50}},
}


def _copy_override_map(
    source: Mapping[str, Mapping[CurveOverrideKey, Mapping[str, Any]]],
) -> dict[str, CurveOverrideMap]:
    return {
        str(tsa): {key: dict(kwargs) for key, kwargs in tsa_map.items()}
        for tsa, tsa_map in source.items()
    }


def _source_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _normalize_tsa_code(tsa_code: str) -> str:
    tsa = str(tsa_code).strip()
    return tsa if not tsa.isdigit() else tsa.zfill(2)


def _resolve_instance_root(instance_root: str | Path | None) -> Path | None:
    if instance_root is not None:
        return Path(instance_root).expanduser().resolve()
    env_value = os.environ.get("FEMIC_INSTANCE_ROOT", "").strip()
    if not env_value:
        return None
    return Path(env_value).expanduser().resolve()


def _validate_scalar(
    *,
    value: Any,
    field_name: str,
    policy_path: Path,
) -> Any:
    if isinstance(value, (bool, int, float, str)):
        return value
    raise ValueError(
        f"{field_name} in {policy_path} must be a scalar value, got {type(value)!r}"
    )


def _load_override_map_from_yaml(path: Path) -> dict[str, CurveOverrideMap]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise ValueError(f"VDYP fit policy root must be a mapping: {path}")
    version = payload.get("version", _POLICY_VERSION)
    if version != _POLICY_VERSION:
        raise ValueError(
            f"Unsupported VDYP fit policy version {version!r} in {path}; "
            f"expected {_POLICY_VERSION}"
        )

    tsa_overrides = payload.get("tsa_overrides", {})
    if tsa_overrides is None:
        return {}
    if not isinstance(tsa_overrides, Mapping):
        raise ValueError(f"tsa_overrides must be a mapping in {path}")

    merged: dict[str, CurveOverrideMap] = {}
    for raw_tsa, entries in tsa_overrides.items():
        tsa = _normalize_tsa_code(str(raw_tsa))
        if entries is None:
            continue
        if not isinstance(entries, list):
            raise ValueError(
                f"tsa_overrides.{raw_tsa} in {path} must be a list of entry mappings"
            )
        tsa_map = merged.setdefault(tsa, {})
        for idx, entry in enumerate(entries):
            entry_name = f"tsa_overrides.{raw_tsa}[{idx}]"
            if not isinstance(entry, Mapping):
                raise ValueError(f"{entry_name} in {path} must be a mapping")
            stratum = entry.get("stratum")
            si = entry.get("si")
            kwargs = entry.get("kwargs", {})
            if not isinstance(stratum, str) or not stratum.strip():
                raise ValueError(
                    f"{entry_name}.stratum in {path} must be a non-empty string"
                )
            if not isinstance(si, str) or not si.strip():
                raise ValueError(
                    f"{entry_name}.si in {path} must be a non-empty string"
                )
            if not isinstance(kwargs, Mapping):
                raise ValueError(f"{entry_name}.kwargs in {path} must be a mapping")
            tsa_map[(stratum.strip(), si.strip())] = {
                str(key): _validate_scalar(
                    value=value,
                    field_name=f"{entry_name}.kwargs.{key}",
                    policy_path=path,
                )
                for key, value in kwargs.items()
            }
    return merged


def _merge_override_sources(
    base: Mapping[str, Mapping[CurveOverrideKey, Mapping[str, Any]]],
    overlay: Mapping[str, Mapping[CurveOverrideKey, Mapping[str, Any]]],
) -> dict[str, CurveOverrideMap]:
    merged = _copy_override_map(base)
    for tsa, tsa_map in overlay.items():
        destination = merged.setdefault(str(tsa), {})
        for key, kwargs in tsa_map.items():
            destination[key] = {**destination.get(key, {}), **dict(kwargs)}
    return merged


def load_vdyp_override_policy(
    *,
    source_root: str | Path | None = None,
    instance_root: str | Path | None = None,
    default_policy_path: str | Path | None = None,
    instance_policy_path: str | Path | None = None,
) -> dict[str, CurveOverrideMap]:
    """Load merged FEMIC-level and instance-level VDYP fit-policy overrides."""
    resolved_source_root = (
        Path(source_root).expanduser().resolve()
        if source_root is not None
        else _source_root()
    )
    resolved_default_policy = (
        Path(default_policy_path).expanduser().resolve()
        if default_policy_path is not None
        else (resolved_source_root / DEFAULT_VDYP_FIT_POLICY_RELATIVE_PATH).resolve()
    )
    if resolved_default_policy.exists():
        try:
            merged = _load_override_map_from_yaml(resolved_default_policy)
        except ValueError:
            merged = _copy_override_map(DEFAULT_VDYP_KWARG_OVERRIDES)
    else:
        merged = _copy_override_map(DEFAULT_VDYP_KWARG_OVERRIDES)

    resolved_instance_policy: Path | None = None
    if instance_policy_path is not None:
        resolved_instance_policy = Path(instance_policy_path).expanduser().resolve()
    else:
        resolved_instance_root = _resolve_instance_root(instance_root)
        if resolved_instance_root is not None:
            candidate = (
                resolved_instance_root / INSTANCE_VDYP_FIT_POLICY_RELATIVE_PATH
            ).resolve()
            if candidate.exists():
                resolved_instance_policy = candidate

    if resolved_instance_policy is not None and resolved_instance_policy.exists():
        merged = _merge_override_sources(
            merged,
            _load_override_map_from_yaml(resolved_instance_policy),
        )
    return merged


def vdyp_kwarg_overrides_for_tsa(
    tsa_code: str,
    *,
    defaults: Mapping[str, Mapping[CurveOverrideKey, Mapping[str, Any]]] | None = None,
    source_root: str | Path | None = None,
    instance_root: str | Path | None = None,
    default_policy_path: str | Path | None = None,
    instance_policy_path: str | Path | None = None,
) -> CurveOverrideMap:
    """Return a defensive copy of configured smoothing-kwarg overrides for one TSA."""
    tsa = _normalize_tsa_code(tsa_code)
    source = defaults or load_vdyp_override_policy(
        source_root=source_root,
        instance_root=instance_root,
        default_policy_path=default_policy_path,
        instance_policy_path=instance_policy_path,
    )
    raw = source.get(tsa, {})
    return {key: dict(kwargs) for key, kwargs in raw.items()}
