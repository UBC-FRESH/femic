from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from femic.hydrology.surrogate import (
    DEFAULT_SURROGATE_TARGET,
    ApplicabilityDomain,
    DesignFactor,
    HydrologySurrogateError,
    SurrogateDataset,
    SurrogateSample,
    attach_targets,
    build_latin_hypercube_design,
    cross_validate_surrogate,
    evaluate_surrogate,
    fit_surrogate,
    load_surrogate,
    save_surrogate,
    train_validation_split,
)

GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _linear_dataset(size: int = 40, seed: int = 3) -> SurrogateDataset:
    rng = np.random.default_rng(seed)
    samples: list[SurrogateSample] = []
    for _ in range(size):
        x1 = float(rng.uniform(0.0, 1.0))
        x2 = float(rng.uniform(0.0, 1.0))
        target = 2.0 * x1 - 3.0 * x2 + 5.0
        samples.append(SurrogateSample({"x1": x1, "x2": x2}, target))
    return SurrogateDataset(("x1", "x2"), "target", tuple(samples), source="synthetic")


def _nonlinear_dataset(size: int = 40, seed: int = 4) -> SurrogateDataset:
    rng = np.random.default_rng(seed)
    samples: list[SurrogateSample] = []
    for _ in range(size):
        x1 = float(rng.uniform(0.0, 1.0))
        x2 = float(rng.uniform(0.0, 1.0))
        target = float(np.sin(3.0 * x1) + 0.5 * x2**2)
        samples.append(SurrogateSample({"x1": x1, "x2": x2}, target))
    return SurrogateDataset(("x1", "x2"), "target", tuple(samples), source="synthetic")


def test_latin_hypercube_design_and_split() -> None:
    design = build_latin_hypercube_design(
        (
            DesignFactor("harvest_fraction", 0.0, 0.6),
            DesignFactor("road_density", 0.0, 2.0),
        ),
        n_samples=20,
        seed=1,
        generated_utc=GENERATED_UTC,
    )
    assert design.design_id.startswith("hydro-design-")
    assert len(design.points) == 20
    assert all(
        0.0 <= point.features["harvest_fraction"] <= 0.6 for point in design.points
    )
    assert all(0.0 <= point.features["road_density"] <= 2.0 for point in design.points)
    assert design.to_dict()["summary"]["point_count"] == 20

    dataset = attach_targets(
        design,
        [point.features["harvest_fraction"] for point in design.points],
        source="design",
    )
    assert dataset.feature_names == ("harvest_fraction", "road_density")
    assert dataset.target_name == DEFAULT_SURROGATE_TARGET
    assert dataset.to_dict()["sample_count"] == 20

    train, validation = train_validation_split(
        dataset, validation_fraction=0.25, seed=2
    )
    assert len(train.samples) + len(validation.samples) == 20
    assert train.feature_names == dataset.feature_names

    same = build_latin_hypercube_design(
        (
            DesignFactor("harvest_fraction", 0.0, 0.6),
            DesignFactor("road_density", 0.0, 2.0),
        ),
        n_samples=20,
        seed=1,
        generated_utc=GENERATED_UTC,
    )
    assert same.design_id == design.design_id


def test_design_and_dataset_validation_errors() -> None:
    with pytest.raises(HydrologySurrogateError, match="At least one"):
        build_latin_hypercube_design((), n_samples=2)
    with pytest.raises(HydrologySurrogateError, match="positive"):
        build_latin_hypercube_design((DesignFactor("x", 0, 1),), n_samples=0)
    with pytest.raises(HydrologySurrogateError, match="unique"):
        build_latin_hypercube_design(
            (DesignFactor("x", 0, 1), DesignFactor("x", 0, 1)),
            n_samples=2,
        )
    with pytest.raises(HydrologySurrogateError, match="low < high"):
        DesignFactor("x", 1, 1)
    with pytest.raises(HydrologySurrogateError, match="finite"):
        DesignFactor("x", float("nan"), 1)
    with pytest.raises(HydrologySurrogateError, match="name"):
        DesignFactor(" ", 0, 1)

    dataset = _linear_dataset()
    with pytest.raises(HydrologySurrogateError, match="exactly"):
        SurrogateDataset(
            ("x1", "x2"),
            "target",
            (SurrogateSample({"x1": 1.0}, 1.0),),
        )
    with pytest.raises(HydrologySurrogateError, match="unique"):
        SurrogateDataset(
            ("x1", "x1"), "target", (SurrogateSample({"x1": 1.0, "x2": 2.0}, 1.0),)
        )
    with pytest.raises(HydrologySurrogateError, match="Target"):
        SurrogateDataset(
            ("x1",),
            "target",
            (SurrogateSample({"x1": 1.0}, float("nan")),),
        )
    with pytest.raises(HydrologySurrogateError, match="Targets"):
        attach_targets(
            build_latin_hypercube_design((DesignFactor("x", 0, 1),), n_samples=2),
            (1.0,),
        )
    with pytest.raises(HydrologySurrogateError, match="between 0 and 1"):
        train_validation_split(dataset, validation_fraction=0)
    with pytest.raises(HydrologySurrogateError, match="three"):
        train_validation_split(
            SurrogateDataset(("x",), "t", (SurrogateSample({"x": 1.0}, 1.0),))
        )


def test_linear_surrogate_fit_predict_and_persist(tmp_path: Path) -> None:
    dataset = _linear_dataset()
    model = fit_surrogate(dataset, family="linear")
    query = {"x1": 0.5, "x2": 0.5}
    prediction = model.predict(query)
    lower, upper = model.predict_interval(query)
    assert prediction == pytest.approx(4.5, abs=0.01)
    assert lower <= prediction <= upper
    assert model.warnings == ()

    validation = evaluate_surrogate(model, dataset)
    assert validation.is_valid
    assert validation.rmse is not None
    assert validation.rmse < 0.01
    assert validation.coverage_95 is not None
    assert validation.coverage_95 > 0.9
    assert validation.to_dict()["accepted_count"] == len(dataset.samples)

    path = save_surrogate(model, tmp_path / "linear.json")
    loaded = load_surrogate(path)
    assert loaded.predict(query) == pytest.approx(prediction)
    assert loaded.to_dict()["family"] == "linear"
    assert json.loads(path.read_text())["family"] == "linear"


def test_gaussian_process_fit_predict_and_persist(tmp_path: Path) -> None:
    dataset = _nonlinear_dataset()
    model = fit_surrogate(dataset, family="gp", length_scale=0.3)
    query = {"x1": 0.4, "x2": 0.7}
    prediction = model.predict(query)
    lower, upper = model.predict_interval(query)
    assert lower <= prediction <= upper
    validation = evaluate_surrogate(model, dataset)
    assert validation.is_valid
    assert validation.rmse is not None
    assert validation.rmse < 0.2

    path = save_surrogate(model, tmp_path / "gp.json")
    loaded = load_surrogate(path)
    assert loaded.predict(query) == pytest.approx(prediction)
    assert loaded.to_dict()["family"] == "gp"


def test_applicability_domain_refusal_and_extrapolation() -> None:
    dataset = _linear_dataset()
    model = fit_surrogate(dataset)
    outside = {"x1": 2.0, "x2": 0.5}
    result = model.applicability_domain.check(outside)
    assert not result.inside
    assert "x1" in result.outside_features
    with pytest.raises(HydrologySurrogateError, match="outside the applicability"):
        model.predict(outside)
    with pytest.raises(HydrologySurrogateError, match="outside the applicability"):
        model.predict_interval(outside)
    assert model.predict(outside, allow_extrapolation=True) is not None

    missing = model.applicability_domain.check({"x1": 0.5})
    assert not missing.inside
    assert missing.missing_features == ("x2",)

    domain = ApplicabilityDomain(
        feature_names=("x1",),
        min_values={"x1": 0.0},
        max_values={"x1": 1.0},
        mean_values={"x1": 0.5},
        scale_values={"x1": 1.0},
        max_distance=0.1,
    )
    far = domain.check({"x1": 1.0})
    assert not far.inside
    assert any("distance" in reason for reason in far.reasons)


def test_evaluate_refuses_out_of_domain_samples() -> None:
    model = fit_surrogate(_linear_dataset())
    evaluation = SurrogateDataset(
        ("x1", "x2"),
        "target",
        (
            SurrogateSample({"x1": 0.5, "x2": 0.5}, 4.5),
            SurrogateSample({"x1": 2.0, "x2": 0.5}, 7.0),
        ),
    )
    validation = evaluate_surrogate(model, evaluation)
    assert validation.accepted_count == 1
    assert validation.refused_count == 1
    assert any("refused" in warning for warning in validation.warnings)

    allow = evaluate_surrogate(model, evaluation, refuse_out_of_domain=False)
    assert allow.accepted_count == 2
    assert allow.refused_count == 1


def test_cross_validation_linear_and_gp() -> None:
    linear = cross_validate_surrogate(
        _linear_dataset(), family="linear", folds=4, seed=1
    )
    assert linear.is_valid
    assert linear.fold_count == 4
    assert linear.rmse is not None
    assert linear.rmse < 0.05

    gp = cross_validate_surrogate(
        _nonlinear_dataset(),
        family="gp",
        folds=3,
        seed=1,
        length_scale=0.3,
    )
    assert gp.is_valid
    assert gp.fold_count == 3
    assert gp.rmse is not None


def test_surrogate_errors_and_no_accepted() -> None:
    dataset = _linear_dataset()
    with pytest.raises(HydrologySurrogateError, match="Unsupported surrogate"):
        fit_surrogate(dataset, family="forest")
    with pytest.raises(HydrologySurrogateError, match="folds"):
        cross_validate_surrogate(dataset, folds=1)
    with pytest.raises(HydrologySurrogateError, match="folds"):
        cross_validate_surrogate(dataset, folds=len(dataset.samples) + 1)
    model = fit_surrogate(dataset)
    far = SurrogateDataset(
        ("x1", "x2"),
        "target",
        (SurrogateSample({"x1": 9.0, "x2": 9.0}, 1.0),),
    )
    validation = evaluate_surrogate(model, far)
    assert not validation.is_valid
    assert validation.accepted_count == 0
    assert validation.rmse is None
    assert any("No evaluation" in warning for warning in validation.warnings)

    path = Path("/tmp/opencode") / "bad-surrogate.json"
    path.write_text('{"family": "bad"}')
    with pytest.raises(HydrologySurrogateError, match="Unsupported"):
        load_surrogate(path)
    path.write_text("not-json")
    with pytest.raises(HydrologySurrogateError, match="Invalid JSON"):
        load_surrogate(path)
    path.write_text("[]")
    with pytest.raises(HydrologySurrogateError, match="JSON object"):
        load_surrogate(path)


def test_low_sample_linear_warning() -> None:
    dataset = SurrogateDataset(
        ("x1",),
        "target",
        tuple(
            SurrogateSample({"x1": float(index)}, float(index) * 2)
            for index in range(2)
        ),
    )
    model = fit_surrogate(dataset)
    assert any("Too few samples" in warning for warning in model.warnings)


def test_from_dict_helpers_errors() -> None:
    from femic.hydrology.surrogate import (
        ApplicabilityDomain,
        GaussianProcessSurrogate,
        LinearSurrogate,
    )

    domain = ApplicabilityDomain(
        ("x",),
        {"x": 0.0},
        {"x": 1.0},
        {"x": 0.5},
        {"x": 1.0},
        1.0,
    )
    linear = LinearSurrogate(
        ("x",),
        {"x": 0.5},
        {"x": 1.0},
        (0.0, 1.0),
        0.1,
        domain,
    )
    assert LinearSurrogate.from_dict(linear.to_dict()).predict(
        {"x": 0.5}
    ) == pytest.approx(0.0)
    gp = GaussianProcessSurrogate(
        ("x",),
        {"x": 0.5},
        {"x": 1.0},
        ((0.0,),),
        (1.0,),
        ((1.0,),),
        1.0,
        1.0,
        1.0,
        1e-6,
        domain,
    )
    assert GaussianProcessSurrogate.from_dict(gp.to_dict()).predict(
        {"x": 0.5}
    ) == pytest.approx(2.0)
    with pytest.raises(HydrologySurrogateError, match="must be a list"):
        ApplicabilityDomain.from_dict({"feature_names": "x"})
