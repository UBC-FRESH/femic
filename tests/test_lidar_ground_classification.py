"""Tests for the clean-room point-cloud conditioning primitives."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pytest

from femic.lidar.ground_classification import (
    classify_ground_ptd,
    hybrid_homogenize,
    local_anisotropy,
    low_point_mask,
    statistical_outlier_mask,
    voxel_connected_components,
)


def test_hybrid_homogenize_keeps_the_barycentre_nearest_point() -> None:
    """BVD keeps one point per occupied voxel before reinjection."""
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.1, 0.1, 0.1],
            [0.9, 0.9, 0.9],
            [2.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    keep = hybrid_homogenize(points, 1.0, reinjection_fraction=0.0)
    assert keep.dtype == np.bool_
    assert keep.shape == (4,)
    assert int(keep.sum()) == 2
    assert keep[1]
    assert keep[3]


def test_hybrid_homogenize_reinjection_is_deterministic() -> None:
    """The reinjection step is reproducible for a fixed seed."""
    rng = np.random.default_rng(7)
    points = rng.normal(size=(100, 3))
    first = hybrid_homogenize(points, 0.5, reinjection_fraction=0.2, seed=11)
    second = hybrid_homogenize(points, 0.5, reinjection_fraction=0.2, seed=11)
    assert np.array_equal(first, second)
    assert int(first.sum()) > 0


def test_hybrid_homogenize_handles_empty_and_single_points() -> None:
    """Empty and singleton clouds return an aligned mask."""
    assert hybrid_homogenize(np.zeros((0, 3)), 1.0).shape == (0,)
    keep = hybrid_homogenize(np.array([[1.0, 2.0, 3.0]]), 1.0)
    assert np.array_equal(keep, np.array([True]))


def test_statistical_outlier_mask_flags_a_far_point() -> None:
    """A point far from a dense cluster is flagged and the cluster is kept."""
    axis = np.linspace(0.0, 0.4, 5)
    grid = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1).reshape(-1, 3)
    points = np.vstack([grid, np.array([[100.0, 100.0, 100.0]])])
    mask = statistical_outlier_mask(points, k=5, multiplier=2.0)
    assert mask.dtype == np.bool_
    assert mask[-1]
    assert not mask[:-1].any()


def test_statistical_outlier_mask_handles_small_clouds() -> None:
    """A cloud with k or fewer points has no estimable outlier."""
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float64)
    mask = statistical_outlier_mask(points, k=5)
    assert not mask.any()


def test_statistical_outlier_mask_handles_zero_variance() -> None:
    """Identical points have no spread, so none are flagged."""
    points = np.zeros((10, 3), dtype=np.float64)
    mask = statistical_outlier_mask(points, k=5)
    assert not mask.any()


def test_point_validation_rejects_bad_shapes_and_nonfinite() -> None:
    """The shared validator rejects malformed and non-finite clouds."""
    with pytest.raises(ValueError, match="shape"):
        hybrid_homogenize(np.zeros((4, 2)), 1.0)
    with pytest.raises(ValueError, match="finite"):
        hybrid_homogenize(np.array([[0.0, 0.0, np.nan]]), 1.0)


def test_invalid_connectivity_raises() -> None:
    """Voxel connectivity must be one of the three supported values."""
    with pytest.raises(ValueError, match="connectivity"):
        voxel_connected_components(np.zeros((2, 3)), 1.0, connectivity=8)


def test_reinjection_fraction_must_be_bounded() -> None:
    """Reinjection cannot exceed the discarded population."""
    with pytest.raises(ValueError, match="reinjection_fraction"):
        hybrid_homogenize(np.zeros((2, 3)), 1.0, reinjection_fraction=1.5)


def test_multiplier_must_be_positive() -> None:
    """A non-positive SOR multiplier is rejected."""
    with pytest.raises(ValueError, match="multiplier"):
        statistical_outlier_mask(np.zeros((10, 3)), multiplier=0.0)


def test_voxel_connected_components_handles_empty_cloud() -> None:
    """An empty cloud returns an empty label array."""
    labels = voxel_connected_components(np.zeros((0, 3)), 1.0)
    assert labels.shape == (0,)


def test_voxel_connected_components_separates_clusters() -> None:
    """Occupied voxels in two separated blobs get different labels."""
    first = np.array(
        [[0.0, 0.0, 0.0], [0.1, 0.1, 0.1], [0.2, 0.0, 0.0]],
        dtype=np.float64,
    )
    second = np.array(
        [[10.0, 0.0, 0.0], [10.1, 0.1, 0.1], [10.2, 0.0, 0.0]],
        dtype=np.float64,
    )
    labels = voxel_connected_components(np.vstack([first, second]), 0.5)
    assert labels.shape == (6,)
    assert labels[0] == labels[1] == labels[2]
    assert labels[3] == labels[4] == labels[5]
    assert labels[0] != labels[3]
    assert int(np.min(labels)) == 1


def test_voxel_connected_components_connectivity_changes_labels() -> None:
    """A corner touch is connected at 26 but not at 6 or 18."""
    points = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], dtype=np.float64)
    six = voxel_connected_components(points, 1.0, connectivity=6)
    eighteen = voxel_connected_components(points, 1.0, connectivity=18)
    twenty_six = voxel_connected_components(points, 1.0, connectivity=26)
    assert six[0] != six[1]
    assert eighteen[0] != eighteen[1]
    assert twenty_six[0] == twenty_six[1]


def test_local_anisotropy_planar_is_high_and_isotropic_is_low() -> None:
    """A plane is strongly anisotropic; a 3D Gaussian blob is close to isotropic."""
    axis = np.linspace(0.0, 1.0, 10)
    plane = np.stack(np.meshgrid(axis, axis, indexing="ij"), axis=-1).reshape(-1, 2)
    plane = np.column_stack([plane, np.zeros(plane.shape[0])])

    rng = np.random.default_rng(3)
    blob = rng.normal(size=(500, 3))

    plane_values = local_anisotropy(plane, k=8)
    blob_values = local_anisotropy(blob, k=20)

    assert plane_values.shape == (plane.shape[0],)
    assert blob_values.shape == (blob.shape[0],)
    assert np.all((plane_values >= 0.0) & (plane_values <= 1.0))
    assert np.all((blob_values >= 0.0) & (blob_values <= 1.0))
    assert float(np.mean(plane_values)) > 0.8
    assert float(np.mean(blob_values)) < 0.6


def test_local_anisotropy_handles_tiny_clouds() -> None:
    """Fewer than four points cannot support a local covariance."""
    values = local_anisotropy(np.zeros((3, 3)), k=10)
    assert np.array_equal(values, np.zeros(3))


@pytest.mark.parametrize(
    ("function", "kwargs", "match"),
    [
        (hybrid_homogenize, {"resolution_m": 0.0}, "resolution_m must be positive"),
        (statistical_outlier_mask, {"k": 1}, "k must be at least 2"),
        (
            voxel_connected_components,
            {"resolution_m": -1.0},
            "resolution_m must be positive",
        ),
        (local_anisotropy, {"k": 2}, "k must be at least 3"),
    ],
)
def test_invalid_parameters_raise(
    function: Callable[..., object],
    kwargs: dict[str, object],
    match: str,
) -> None:
    """Invalid resolutions, neighbour counts, and multipliers fail loudly."""
    points = np.zeros((5, 3), dtype=np.float64)
    with pytest.raises(ValueError, match=match):
        function(points, **kwargs)


def test_classify_ground_ptd_flat_plane_with_outlier() -> None:
    """A flat plane is ground and a high building-like point is not."""
    axis = np.linspace(0.0, 9.0, 10)
    xx, yy = np.meshgrid(axis, axis)
    plane = np.column_stack([xx.ravel(), yy.ravel(), np.zeros(xx.size)])
    points = np.vstack([plane, np.array([[5.0, 5.0, 5.0]])])
    result = classify_ground_ptd(
        points,
        cell_size_m=1.0,
        max_distance_m=0.5,
    )
    assert result.is_ground.shape == (points.shape[0],)
    assert bool(np.all(result.is_ground[:-1]))
    assert not bool(result.is_ground[-1])
    assert float(np.max(result.height_above_ground[:-1])) < 1e-6
    assert float(result.height_above_ground[-1]) == pytest.approx(5.0)
    assert result.seed_count > 0


def test_classify_ground_ptd_sloped_plane() -> None:
    """A gentle slope is ground with near-zero HAG."""
    axis = np.linspace(0.0, 9.0, 10)
    xx, yy = np.meshgrid(axis, axis)
    z = 0.1 * xx + 0.05 * yy
    points = np.column_stack([xx.ravel(), yy.ravel(), z.ravel()])
    result = classify_ground_ptd(
        points,
        cell_size_m=1.0,
        max_angle_deg=30.0,
        max_distance_m=0.5,
    )
    assert bool(np.all(result.is_ground))
    assert float(np.max(result.height_above_ground)) < 1e-6


def test_classify_ground_ptd_high_vegetation_stays_above_ground() -> None:
    """High points above a flat plane are not ground and keep positive HAG."""
    axis = np.linspace(0.0, 4.0, 5)
    xx, yy = np.meshgrid(axis, axis)
    plane = np.column_stack([xx.ravel(), yy.ravel(), np.zeros(xx.size)])
    tall = np.array([[2.0, 2.0, 3.0], [2.0, 2.0, 4.0]])
    points = np.vstack([plane, tall])
    result = classify_ground_ptd(points, cell_size_m=1.0, max_distance_m=0.5)
    assert not bool(np.any(result.is_ground[-2:]))
    assert float(result.height_above_ground[-2]) == pytest.approx(3.0)
    assert float(result.height_above_ground[-1]) == pytest.approx(4.0)


def test_classify_ground_ptd_degenerate_tin_returns_warning() -> None:
    """A collinear seed set does not crash and reports a warning."""
    points = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    result = classify_ground_ptd(points, cell_size_m=0.5)
    assert result.warning is not None
    assert bool(np.all(result.is_ground))
    assert float(np.max(result.height_above_ground)) == pytest.approx(0.0)


def test_classify_ground_ptd_empty_cloud() -> None:
    """An empty cloud returns empty arrays and zero counters."""
    result = classify_ground_ptd(np.zeros((0, 3)), cell_size_m=1.0)
    assert result.is_ground.shape == (0,)
    assert result.height_above_ground.shape == (0,)
    assert result.ground_elevation.shape == (0,)
    assert result.iterations == 0
    assert result.seed_count == 0
    assert result.warning is None


def test_classify_ground_ptd_invalid_parameters() -> None:
    """Invalid PTD parameters fail with a clear error."""
    points = np.zeros((5, 3), dtype=np.float64)
    with pytest.raises(ValueError, match="cell_size_m"):
        classify_ground_ptd(points, cell_size_m=0.0)
    with pytest.raises(ValueError, match="max_angle_deg"):
        classify_ground_ptd(points, max_angle_deg=0.0)
    with pytest.raises(ValueError, match="max_angle_deg"):
        classify_ground_ptd(points, max_angle_deg=90.0)
    with pytest.raises(ValueError, match="max_distance_m"):
        classify_ground_ptd(points, max_distance_m=0.0)
    with pytest.raises(ValueError, match="max_iterations"):
        classify_ground_ptd(points, max_iterations=0)


def test_low_point_mask_flags_points_below_the_cut() -> None:
    """The low-point flag uses a strict HAG cut."""
    hag = np.array([0.0, 0.1, 0.15, 0.2], dtype=np.float64)
    mask = low_point_mask(hag, cut_m=0.15)
    assert mask.dtype == np.bool_
    assert np.array_equal(mask, np.array([True, True, False, False]))


def test_low_point_mask_validates_inputs() -> None:
    """Negative cuts and non-vector HAG arrays fail."""
    with pytest.raises(ValueError, match="one-dimensional"):
        low_point_mask(np.zeros((2, 2)), cut_m=0.15)
    with pytest.raises(ValueError, match="non-negative"):
        low_point_mask(np.zeros(3), cut_m=-0.1)
