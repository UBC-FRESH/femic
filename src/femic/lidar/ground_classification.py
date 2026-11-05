"""Point-cloud conditioning primitives derived from published Arbor methods.

This module is a small, MIT-licensed Python reimplementation of four low-level ideas
described in the Arbor book and package. Arbor is GPL-3.0, so no Arbor source code was
copied. Each function records its own provenance and the clean-room statement.

The functions operate on an ``(N, 3)`` float array of point coordinates. They return
masks or labels aligned to that input order, which lets callers keep the original LAS/LAZ
attributes and apply the result with NumPy indexing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import Delaunay, QhullError, cKDTree  # type: ignore[import-untyped]

PointArray = NDArray[np.float64]
BoolMask = NDArray[np.bool_]
LabelArray = NDArray[np.int64]

# Keep kNN working sets bounded. A 50k-point chunk with k=20 needs about 25 MB for the
# neighbour coordinates alone, so a large tile does not allocate an N x k array at once.
_CHUNK_SIZE: int = 50_000
_MAX_TIN_SUPPORT: int = 200_000


def _as_points(points: PointArray) -> PointArray:
    """Validate a point array and return a float64 ``(N, 3)`` view.

    Parameters
    ----------
    points : ndarray
        Candidate point coordinates.

    Returns
    -------
    ndarray
        A contiguous float64 array with shape ``(N, 3)``.

    Raises
    ------
    ValueError
        When the input is not a finite ``(N, 3)`` array.
    """
    array = np.asarray(points, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")
    if not np.all(np.isfinite(array)):
        raise ValueError("points must contain only finite coordinates")
    return np.ascontiguousarray(array)


def _neighbour_offsets(connectivity: int) -> tuple[tuple[int, int, int], ...]:
    """Return the voxel offsets for a 6-, 18-, or 26-connected neighbourhood.

    Parameters
    ----------
    connectivity : int
        One of ``6``, ``18``, or ``26``.

    Returns
    -------
    tuple of tuple of int
        ``(di, dj, dk)`` offsets excluding the centre voxel.

    Raises
    ------
    ValueError
        When ``connectivity`` is not supported.
    """
    if connectivity not in (6, 18, 26):
        raise ValueError("connectivity must be 6, 18, or 26")
    offsets: list[tuple[int, int, int]] = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for dk in (-1, 0, 1):
                if di == 0 and dj == 0 and dk == 0:
                    continue
                distance = abs(di) + abs(dj) + abs(dk)
                if connectivity == 6 and distance != 1:
                    continue
                if connectivity == 18 and distance > 2:
                    continue
                offsets.append((di, dj, dk))
    return tuple(offsets)


def hybrid_homogenize(
    points: PointArray,
    resolution_m: float,
    *,
    reinjection_fraction: float = 0.1,
    seed: int = 42,
) -> BoolMask:
    """Select a density-preserving, voxel-homogenized subset of a point cloud.

    The method is the barycentric voxel decimation (BVD) and random-reinjection idea
    described in the Arbor book, chapter 3. Within each occupied 3D voxel it keeps the
    point closest to the voxel barycentre, then reinjects a deterministic random sample of
    discarded points to restore some of the local density variation that voxelization
    smooths away.

    Parameters
    ----------
    points : ndarray
        Point coordinates with shape ``(N, 3)``.
    resolution_m : float
        Voxel edge length in metres. Must be positive.
    reinjection_fraction : float, optional
        Fraction of the retained count to reinject from the discarded points. The default
        is ``0.1`` (about 10 percent). Must be between 0 and 1.
    seed : int, optional
        Seed for the deterministic reinjection sample. The default is ``42``.

    Returns
    -------
    ndarray of bool
        Boolean keep mask with shape ``(N,)``.

    Raises
    ------
    ValueError
        When ``resolution_m`` is not positive, ``reinjection_fraction`` is outside
        ``[0, 1]``, or the point array is invalid.

    Notes
    -----
    The BVD step is deterministic. The reinjection step is deterministic for a given
    NumPy version and ``seed``. When the cloud is empty or has one point, the mask is
    returned unchanged.

    Method provenance
    -----------------
    Idea and algorithm: Arbor 1.1.5 (r-lidar/arbor), commit
    ``a2b487f4a23236a42eec50cb6583a5eae15593ed``, book chapter 3
    (https://r-lidar.github.io/arbor_book/decimation.html).
    Source licence: GPL-3.0. This is an independent Python reimplementation; no Arbor
    source code was copied.
    """
    cloud = _as_points(points)
    if resolution_m <= 0:
        raise ValueError("resolution_m must be positive")
    if not 0 <= reinjection_fraction <= 1:
        raise ValueError("reinjection_fraction must be between 0 and 1")

    count = cloud.shape[0]
    if count == 0:
        return np.zeros(0, dtype=np.bool_)
    if count == 1:
        return np.ones(1, dtype=np.bool_)

    origin = np.min(cloud, axis=0)
    voxel = np.floor((cloud - origin) / resolution_m).astype(np.int64)
    _, inverse = np.unique(voxel, axis=0, return_inverse=True)

    order = np.argsort(inverse, kind="stable")
    sorted_groups = inverse[order]
    starts = np.flatnonzero(np.r_[True, sorted_groups[1:] != sorted_groups[:-1]])
    group_counts = np.diff(np.r_[starts, count])

    sums = np.add.reduceat(cloud[order], starts, axis=0)
    barycentres = sums / group_counts[:, None]
    distances = np.sum(
        (cloud[order] - barycentres[sorted_groups]) ** 2,
        axis=1,
    )

    minimum = np.minimum.reduceat(distances, starts)
    closest = distances == np.repeat(minimum, group_counts)
    candidate_positions = np.flatnonzero(closest)
    candidate_groups = sorted_groups[candidate_positions]
    _, first_positions = np.unique(candidate_groups, return_index=True)
    keep = np.zeros(count, dtype=np.bool_)
    keep[order[candidate_positions[first_positions]]] = True

    retained = int(np.count_nonzero(keep))
    reinjected = min(
        round(retained * reinjection_fraction),
        count - retained,
    )
    if reinjected > 0:
        discarded = np.flatnonzero(~keep)
        rng = np.random.default_rng(seed)
        chosen = rng.choice(discarded, size=reinjected, replace=False)
        keep[chosen] = True
    return keep


def statistical_outlier_mask(
    points: PointArray,
    *,
    k: int = 10,
    multiplier: float = 2.0,
) -> BoolMask:
    """Flag points whose mean k-nearest-neighbour distance is unusually large.

    This is the statistical outlier removal (SOR) rule used in the Arbor conditioning
    pipeline. It computes the mean distance to the ``k`` nearest neighbours for every
    point, then flags points above ``mean + multiplier * standard_deviation``.

    Parameters
    ----------
    points : ndarray
        Point coordinates with shape ``(N, 3)``.
    k : int, optional
        Number of neighbours used for the local distance. The default is ``10``. Must be
        at least 2.
    multiplier : float, optional
        Standard-deviation multiplier for the global threshold. The default is ``2.0``.
        Must be positive.

    Returns
    -------
    ndarray of bool
        Outlier mask with shape ``(N,)``. ``True`` means the point is flagged as an
        outlier.

    Raises
    ------
    ValueError
        When ``k < 2``, ``multiplier <= 0``, or the point array is invalid.

    Notes
    -----
    When the cloud has ``k`` or fewer points, or when the distance distribution has zero
    variance, no point is flagged. The function never mutates the input.

    Method provenance
    -----------------
    Idea and algorithm: Arbor 1.1.5 (r-lidar/arbor), commit
    ``a2b487f4a23236a42eec50cb6583a5eae15593ed``, ``src/utils/sor.cpp``.
    Source licence: GPL-3.0. This is an independent Python reimplementation; no Arbor
    source code was copied.
    """
    cloud = _as_points(points)
    if k < 2:
        raise ValueError("k must be at least 2")
    if multiplier <= 0:
        raise ValueError("multiplier must be positive")

    count = cloud.shape[0]
    if count <= k:
        return np.zeros(count, dtype=np.bool_)

    tree = cKDTree(cloud)
    distances, _ = tree.query(cloud, k=k + 1, workers=-1)
    # The first neighbour is the query point itself.
    mean_distance = np.asarray(distances[:, 1:], dtype=np.float64).mean(axis=1)
    centre = float(mean_distance.mean())
    spread = float(mean_distance.std(ddof=1))
    if spread <= 0:
        return np.zeros(count, dtype=np.bool_)
    threshold = centre + multiplier * spread
    return np.asarray(mean_distance > threshold, dtype=np.bool_)


def voxel_connected_components(
    points: PointArray,
    resolution_m: float,
    *,
    connectivity: int = 26,
) -> LabelArray:
    """Label 6-, 18-, or 26-connected occupied voxels in a point cloud.

    The function builds a sparse voxel occupancy set, then labels connected components
    without allocating a dense provincial-scale grid. Every input point receives the
    label of its voxel; labels start at 1.

    Parameters
    ----------
    points : ndarray
        Point coordinates with shape ``(N, 3)``.
    resolution_m : float
        Voxel edge length in metres. Must be positive.
    connectivity : int, optional
        Neighbourhood connectivity: ``6``, ``18``, or ``26``. The default is ``26``.

    Returns
    -------
    ndarray of int64
        Component label per input point, with shape ``(N,)``. An empty cloud returns an
        empty array.

    Raises
    ------
    ValueError
        When ``resolution_m`` is not positive, ``connectivity`` is unsupported, or the
        point array is invalid.

    Notes
    -----
    The sparse traversal is deterministic for a fixed input order. It is intended for
    bounded tiles and cluster cleaning, not for a dense mirror of a whole province.

    Method provenance
    -----------------
    Idea and algorithm: Arbor 1.1.5 (r-lidar/arbor), commit
    ``a2b487f4a23236a42eec50cb6583a5eae15593ed``, ``src/utils/Grid3D.cpp``.
    Source licence: GPL-3.0. This is an independent Python reimplementation; no Arbor
    source code was copied.
    """
    cloud = _as_points(points)
    if resolution_m <= 0:
        raise ValueError("resolution_m must be positive")
    offsets = _neighbour_offsets(connectivity)
    count = cloud.shape[0]
    if count == 0:
        return np.zeros(0, dtype=np.int64)

    origin = np.min(cloud, axis=0)
    voxel = np.floor((cloud - origin) / resolution_m).astype(np.int64)
    unique_voxels, inverse = np.unique(voxel, axis=0, return_inverse=True)
    lookup = {
        (int(row[0]), int(row[1]), int(row[2])): index
        for index, row in enumerate(unique_voxels)
    }

    labels = np.zeros(unique_voxels.shape[0], dtype=np.int64)
    current = 0
    for seed in range(unique_voxels.shape[0]):
        if labels[seed] != 0:
            continue
        current += 1
        labels[seed] = current
        stack = [seed]
        while stack:
            index = stack.pop()
            i, j, k = (int(value) for value in unique_voxels[index])
            for di, dj, dk in offsets:
                neighbour = lookup.get((i + di, j + dj, k + dk))
                if neighbour is not None and labels[neighbour] == 0:
                    labels[neighbour] = current
                    stack.append(neighbour)
    return np.asarray(labels[inverse], dtype=np.int64)


def local_anisotropy(
    points: PointArray,
    *,
    k: int = 20,
) -> NDArray[np.float64]:
    """Compute a local wood-likelihood proxy from kNN covariance anisotropy.

    For each point, the covariance of its ``k`` nearest-neighbour coordinates is
    decomposed into eigenvalues. The returned value is ``(lmax - lmin) / lmax``, which is
    near 1 for elongated or planar local structure and near 0 for an isotropic cluster.
    Arbor uses this as a wood-likelihood input before semantic segmentation.

    Parameters
    ----------
    points : ndarray
        Point coordinates with shape ``(N, 3)``.
    k : int, optional
        Number of neighbours used for the local covariance. The default is ``20``. Must be
        at least 3.

    Returns
    -------
    ndarray of float64
        Anisotropy values in ``[0, 1]`` with shape ``(N,)``. A cloud with fewer than four
        points returns zeros, because the covariance is not meaningful.

    Raises
    ------
    ValueError
        When ``k < 3`` or the point array is invalid.

    Notes
    -----
    The kNN query is chunked so a large tile does not allocate a full ``N x k x 3``
    neighbour array. This function is a descriptor only; it does not classify wood or
    foliage and does not claim point-wise accuracy.

    Method provenance
    -----------------
    Idea and algorithm: Arbor 1.1.5 (r-lidar/arbor), commit
    ``a2b487f4a23236a42eec50cb6583a5eae15593ed``, ``src/utils/anisotopy.cpp`` and
    book chapter 5 (https://r-lidar.github.io/arbor_book/semantic.html).
    Source licence: GPL-3.0. This is an independent Python reimplementation; no Arbor
    source code was copied.
    """
    cloud = _as_points(points)
    if k < 3:
        raise ValueError("k must be at least 3")

    count = cloud.shape[0]
    if count < 4:
        return np.zeros(count, dtype=np.float64)

    neighbours = min(k, count - 1)
    tree = cKDTree(cloud)
    result = np.zeros(count, dtype=np.float64)
    for start in range(0, count, _CHUNK_SIZE):
        stop = min(start + _CHUNK_SIZE, count)
        chunk = cloud[start:stop]
        _, indices = tree.query(chunk, k=neighbours + 1, workers=-1)
        # Drop the query point itself.
        local = cloud[np.asarray(indices[:, 1:], dtype=np.int64)]
        centred = local - local.mean(axis=1, keepdims=True)
        covariance = np.einsum("nki,nkj->nij", centred, centred) / max(
            neighbours - 1,
            1,
        )
        eigenvalues = np.linalg.eigvalsh(covariance)
        largest = eigenvalues[:, -1]
        smallest = eigenvalues[:, 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            values = np.where(largest > 1e-14, (largest - smallest) / largest, 0.0)
        result[start:stop] = np.clip(values, 0.0, 1.0)
    return result


@dataclass(frozen=True, slots=True)
class GroundClassification:
    """Ground labels and height above ground for one point cloud.

    Attributes
    ----------
    is_ground : ndarray of bool
        Ground mask with shape ``(N,)``.
    height_above_ground : ndarray of float64
        Height above the final ground surface, in metres, clipped at zero.
    ground_elevation : ndarray of float64
        Interpolated ground elevation at each point, in the input vertical units.
    iterations : int
        Number of TIN densification iterations that added at least one point.
    seed_count : int
        Number of lowest-per-cell seed points.
    warning : str or None
        A warning when the TIN was degenerate or too small; otherwise ``None``.
    """

    is_ground: BoolMask
    height_above_ground: NDArray[np.float64]
    ground_elevation: NDArray[np.float64]
    iterations: int
    seed_count: int
    warning: str | None = None


def _thin_support(indices: NDArray[np.int64]) -> NDArray[np.int64]:
    """Thin a TIN support set to a bounded number of points.

    Parameters
    ----------
    indices : ndarray of int64
        Candidate support-point indices.

    Returns
    -------
    ndarray of int64
        The input when it is small enough, otherwise an evenly spaced subset.
    """
    if indices.size <= _MAX_TIN_SUPPORT:
        return indices
    positions = np.linspace(
        0,
        indices.size - 1,
        num=_MAX_TIN_SUPPORT,
        dtype=np.int64,
    )
    return indices[positions]


def _tin_surface(
    points: PointArray,
    support: PointArray,
) -> tuple[NDArray[np.float64], BoolMask, NDArray[np.float64]]:
    """Interpolate a TIN surface and the point-to-vertex angle at each query point.

    Parameters
    ----------
    points : ndarray
        Query points with shape ``(N, 3)``.
    support : ndarray
        Support points with shape ``(M, 3)``. At least three non-collinear points are
        required.

    Returns
    -------
    ground_z : ndarray of float64
        Interpolated or nearest-support ground elevation.
    inside : ndarray of bool
        ``True`` where the query point falls inside the TIN hull.
    point_angle_deg : ndarray of float64
        Maximum angle between the point and the three triangle vertices, measured from
        the triangle plane. Outside the hull the angle is 90 degrees.

    Raises
    ------
    scipy.spatial.QhullError
        When the support points cannot form a triangulation.
    """
    xy = points[:, :2]
    triangulation = Delaunay(support[:, :2])
    simplex = triangulation.find_simplex(xy)
    inside = simplex >= 0
    ground_z = np.empty(points.shape[0], dtype=np.float64)
    point_angle_deg = np.full(points.shape[0], 90.0, dtype=np.float64)

    if np.any(inside):
        selected = simplex[inside]
        transform = triangulation.transform[selected]
        delta = xy[inside] - transform[:, 2, :2]
        bary = np.einsum("nij,nj->ni", transform[:, :2, :2], delta)
        bary = np.column_stack([bary, 1.0 - bary.sum(axis=1)])
        vertices = support[triangulation.simplices[selected]]
        ground_z[inside] = np.einsum("ni,ni->n", bary, vertices[:, :, 2])
        normal = np.cross(
            vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0]
        )
        norm = np.linalg.norm(normal, axis=1)
        unit_normal = normal / np.maximum(norm[:, None], 1e-12)
        vectors = points[inside, None, :] - vertices
        lengths = np.linalg.norm(vectors, axis=2)
        sines = np.abs(np.einsum("nvi,ni->nv", vectors, unit_normal))
        sines = np.divide(
            sines,
            np.maximum(lengths, 1e-12),
            out=np.zeros_like(sines),
            where=lengths > 0,
        )
        angles = np.degrees(np.arcsin(np.clip(sines, 0.0, 1.0)))
        point_angle_deg[inside] = angles.max(axis=1)

    if np.any(~inside):
        tree = cKDTree(support[:, :2])
        _, nearest = tree.query(xy[~inside], k=1, workers=-1)
        ground_z[~inside] = support[np.asarray(nearest, dtype=np.int64), 2]

    return ground_z, inside, point_angle_deg


def classify_ground_ptd(
    points: PointArray,
    *,
    cell_size_m: float = 1.0,
    max_angle_deg: float = 30.0,
    max_distance_m: float = 2.0,
    max_iterations: int = 8,
) -> GroundClassification:
    """Classify ALS ground points with a PTD-inspired progressive TIN.

    The method seeds a triangulated surface from the lowest point in each grid cell, then
    progressively adds points whose vertical residual from the TIN is within
    ``max_distance_m`` and whose point-to-vertex angle is within ``max_angle_deg``. The final TIN
    provides the ground elevation and height above ground.

    Parameters
    ----------
    points : ndarray
        Point coordinates with shape ``(N, 3)``. Coordinates must be finite.
    cell_size_m : float, optional
        Grid cell edge used to pick the lowest seed per cell. The default is ``1.0``.
        Must be positive.
    max_angle_deg : float, optional
        Maximum accepted point-to-vertex angle, in degrees. The default is ``30.0``. Must be
        between 0 and 90.
    max_distance_m : float, optional
        Maximum vertical residual from the TIN for a candidate ground point, in metres.
        The default is ``2.0``. Must be positive.
    max_iterations : int, optional
        Maximum densification iterations. The default is ``8``. Must be at least 1.

    Returns
    -------
    GroundClassification
        Ground mask, HAG, interpolated ground elevation, iteration count, seed count, and
        an optional warning.

    Raises
    ------
    ValueError
        When the point array is invalid or a parameter is outside its accepted range.

    Notes
    -----
    This is a simplified, PTD-inspired implementation, not a line-by-line port of Arbor,
    lidR, or the original PTD code. The angle test uses the maximum point-to-triangle-vertex
    angle measured from the triangle plane. The default vertical residual is deliberately
    permissive. A real LidarBC tile must be validated before this function is used as an
    operational ground classifier.

    Points outside the TIN hull are not classified as ground; their HAG uses the nearest
    support point. A degenerate or too-small TIN returns the seed-only classification with
    a warning instead of raising.

    Method provenance
    -----------------
    Idea and algorithm: progressive TIN densification (Axelsson 2000), as described in
    Arbor 1.1.5 (r-lidar/arbor), commit
    ``a2b487f4a23236a42eec50cb6583a5eae15593ed``, book chapter 4
    (https://r-lidar.github.io/arbor_book/ground.html) and
    ``src/segment/segment_ground_api.cpp``.
    Source licence: GPL-3.0. This is an independent Python reimplementation; no Arbor
    source code was copied.
    """
    cloud = _as_points(points)
    if cell_size_m <= 0:
        raise ValueError("cell_size_m must be positive")
    if not 0 < max_angle_deg < 90:
        raise ValueError("max_angle_deg must be between 0 and 90")
    if max_distance_m <= 0:
        raise ValueError("max_distance_m must be positive")
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")

    count = cloud.shape[0]
    if count == 0:
        return GroundClassification(
            is_ground=np.zeros(0, dtype=np.bool_),
            height_above_ground=np.zeros(0, dtype=np.float64),
            ground_elevation=np.zeros(0, dtype=np.float64),
            iterations=0,
            seed_count=0,
        )

    origin = np.min(cloud, axis=0)
    cells = np.floor((cloud[:, :2] - origin[:2]) / cell_size_m).astype(np.int64)
    _, inverse = np.unique(cells, axis=0, return_inverse=True)
    order = np.lexsort((cloud[:, 2], inverse))
    sorted_groups = inverse[order]
    starts = np.flatnonzero(np.r_[True, sorted_groups[1:] != sorted_groups[:-1]])
    seed_indices = np.asarray(order[starts], dtype=np.int64)

    ground = np.zeros(count, dtype=np.bool_)
    ground[seed_indices] = True
    warning: str | None = None
    iterations = 0

    support_indices = _thin_support(seed_indices)
    for _ in range(max_iterations):
        if support_indices.size < 3:
            warning = "fewer than three ground seeds; TIN densification skipped"
            break
        try:
            surface, inside, point_angle = _tin_surface(cloud, cloud[support_indices])
        except QhullError:
            warning = "degenerate ground seed TIN; TIN densification skipped"
            break
        residual = cloud[:, 2] - surface
        candidate = (
            inside
            & (np.abs(residual) <= max_distance_m)
            & (point_angle <= max_angle_deg)
        )
        new = candidate & ~ground
        if not np.any(new):
            break
        ground |= candidate
        support_indices = _thin_support(np.flatnonzero(ground))
        iterations += 1

    support_indices = _thin_support(np.flatnonzero(ground))
    if support_indices.size < 3:
        warning = warning or "fewer than three ground points; nearest-seed HAG used"
        tree = cKDTree(cloud[seed_indices, :2])
        _, nearest = tree.query(cloud[:, :2], k=1, workers=-1)
        ground_elevation = cloud[seed_indices, 2][np.asarray(nearest, dtype=np.int64)]
    else:
        try:
            ground_elevation, _, _ = _tin_surface(
                cloud,
                cloud[support_indices],
            )
        except QhullError:
            warning = warning or "degenerate final ground TIN; nearest-seed HAG used"
            tree = cKDTree(cloud[seed_indices, :2])
            _, nearest = tree.query(cloud[:, :2], k=1, workers=-1)
            ground_elevation = cloud[seed_indices, 2][
                np.asarray(nearest, dtype=np.int64)
            ]

    height_above_ground = np.maximum(cloud[:, 2] - ground_elevation, 0.0)
    return GroundClassification(
        is_ground=ground,
        height_above_ground=height_above_ground,
        ground_elevation=ground_elevation,
        iterations=iterations,
        seed_count=int(seed_indices.size),
        warning=warning,
    )


def low_point_mask(
    height_above_ground: NDArray[np.float64],
    *,
    cut_m: float = 0.15,
) -> BoolMask:
    """Flag points below a height-above-ground cut.

    The Arbor book recommends ignoring points a few centimetres above the ground during
    MLS/TLS segmentation, because the ground and low understory form a continuous surface
    that can confuse the pathfinder. This helper applies that policy to an existing HAG
    array without changing the ground labels.

    Parameters
    ----------
    height_above_ground : ndarray
        Height above ground in metres, with shape ``(N,)``.
    cut_m : float, optional
        Cut height in metres. The default is ``0.15``. Must be non-negative.

    Returns
    -------
    ndarray of bool
        ``True`` where ``height_above_ground < cut_m``.

    Raises
    ------
    ValueError
        When the HAG array is not one-dimensional or ``cut_m`` is negative.

    Notes
    -----
    This is a downstream segmentation flag, not a ground-classification label. A point
    flagged here can still be a valid ground point.

    Method provenance
    -----------------
    Idea: the low-point-removal policy described in Arbor 1.1.5 (r-lidar/arbor), commit
    ``a2b487f4a23236a42eec50cb6583a5eae15593ed``, book chapter 4
    (https://r-lidar.github.io/arbor_book/ground.html).
    Source licence: GPL-3.0. This is an independent Python implementation; no Arbor
    source code was copied.
    """
    values = np.asarray(height_above_ground, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("height_above_ground must be one-dimensional")
    if cut_m < 0:
        raise ValueError("cut_m must be non-negative")
    return np.asarray(values < cut_m, dtype=np.bool_)


__all__ = (
    "GroundClassification",
    "classify_ground_ptd",
    "hybrid_homogenize",
    "local_anisotropy",
    "low_point_mask",
    "statistical_outlier_mask",
    "voxel_connected_components",
)
