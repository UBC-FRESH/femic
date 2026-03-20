"""Pre-VDYP stage helpers extracted from legacy TSA runner."""

from __future__ import annotations

import copy
from pathlib import Path
import pickle
from typing import Any, Mapping


def serialize_vdyp_prep_payload(results_tsa: list[list[Any]]) -> list[list[Any]]:
    """Copy and sanitize pre-VDYP fit payload for checkpoint persistence."""
    payload: list[list[Any]] = []
    for stratumi, sc, fit_out in results_tsa:
        fit_out_clean = copy.deepcopy(fit_out)
        for si_level_data in fit_out_clean.values():
            for species_data in si_level_data["species"].values():
                species_data.pop("fit_func", None)
        payload.append([stratumi, sc, fit_out_clean])
    return payload


def build_vdyp_prep_signature(
    *,
    selected_strata_codes: list[str],
    target_area_coverage: float | None,
    min_stands_per_si_bin: int,
) -> dict[str, Any]:
    """Build a deterministic signature for pre-VDYP checkpoint compatibility checks."""
    return {
        "selected_strata_codes": sorted(str(code) for code in selected_strata_codes),
        "target_area_coverage": (
            None if target_area_coverage is None else float(target_area_coverage)
        ),
        "min_stands_per_si_bin": int(min_stands_per_si_bin),
    }


def pre_vdyp_checkpoint_path(
    *,
    tsa_code: str,
    base_dir: str | Path = "data",
) -> Path:
    """Build per-TSA pre-VDYP checkpoint path."""
    tsa = str(tsa_code).zfill(2)
    return Path(base_dir) / f"vdyp_prep-tsa{tsa}.pkl"


def load_vdyp_prep_checkpoint(
    path: str | Path,
    *,
    expected_signature: Mapping[str, Any] | None = None,
) -> list[list[Any]]:
    """Load pre-VDYP checkpoint payload from pickle.

    Supports both legacy payload-only pickles and schema-v2 dictionaries carrying
    a compatibility signature. When `expected_signature` is provided and a stored
    signature exists, mismatches raise `ValueError`.
    """
    checkpoint_path = Path(path)
    with checkpoint_path.open("rb") as f:
        loaded = pickle.load(f)
    if isinstance(loaded, dict):
        payload = loaded.get("payload")
        signature = loaded.get("signature")
        if not isinstance(payload, list):
            raise TypeError("pre-VDYP checkpoint payload must be a list")
        if (
            expected_signature is not None
            and signature is not None
            and dict(signature) != dict(expected_signature)
        ):
            raise ValueError(
                "pre-VDYP checkpoint signature mismatch; expected "
                f"{dict(expected_signature)!r}, found {dict(signature)!r}"
            )
        return payload
    if isinstance(loaded, list):
        return loaded
    raise TypeError("pre-VDYP checkpoint payload must be a list")


def save_vdyp_prep_checkpoint(
    path: str | Path,
    results_tsa: list[list[Any]],
    *,
    signature: Mapping[str, Any] | None = None,
) -> int:
    """Persist sanitized pre-VDYP payload and return number of strata saved."""
    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    payload = serialize_vdyp_prep_payload(results_tsa)
    with checkpoint_path.open("wb") as f:
        pickle.dump(
            {
                "schema_version": 2,
                "signature": None if signature is None else dict(signature),
                "payload": payload,
            },
            f,
        )
    return len(payload)
