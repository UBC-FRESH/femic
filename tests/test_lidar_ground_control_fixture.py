"""Public-control regression guard for the canonical ground classifier.

Fixtures are compact subsets of the P137 Squamish control patch:

- open estuarine mudflat labelled ground;
- first returns of multiple returns in closed canopy labelled non-ground.

Source data: District of Squamish 2024 7.5 cm orthophoto (OGL-Squamish) and LidarBC
2019 8 points/m2 point cloud (OGL-BC). Raw orthophoto and LAZ bytes are not tracked.

The thresholds guard against a classifier change that loses open-ground recall or starts
calling canopy first returns ground. They are not a general accuracy claim.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from femic.lidar.ground_classification import (
    classify_ground_ptd,
    statistical_outlier_mask,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "lidar" / "ground_control"


def _load_fixture(name: str) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(FIXTURE_DIR / name)
    xyz = np.column_stack([data["x"], data["y"], data["z"]]).astype(np.float64)
    labels = data["label"].astype(np.int8)
    return xyz, labels


def _predict(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    kept = ~statistical_outlier_mask(xyz, k=10, multiplier=2.0)
    result = classify_ground_ptd(
        xyz[kept],
        cell_size_m=1.0,
        max_angle_deg=15.0,
        max_distance_m=0.5,
        max_iterations=8,
    )
    predicted = np.zeros(len(xyz), dtype=bool)
    predicted[kept] = result.is_ground
    return predicted, kept


def test_public_control_ground_recall() -> None:
    """Open mudflat remains classified as ground."""
    xyz, labels = _load_fixture("squamish_ground_patch.npz")
    predicted, kept = _predict(xyz)
    labelled = kept & (labels == 1)
    assert int(labelled.sum()) == 5461
    recall = float(predicted[labelled].mean())
    assert recall >= 0.95, f"ground recall dropped to {recall:.4f}"


def test_public_control_canopy_false_ground() -> None:
    """Closed-canopy first returns stay out of the ground class."""
    xyz, labels = _load_fixture("squamish_canopy_patch.npz")
    predicted, kept = _predict(xyz)
    labelled = kept & (labels == 0)
    assert int(labelled.sum()) == 9234
    false_ground = float(predicted[labelled].mean())
    assert false_ground <= 0.005, f"canopy false ground rose to {false_ground:.4f}"
