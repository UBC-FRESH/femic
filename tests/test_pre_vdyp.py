from __future__ import annotations

from pathlib import Path

from femic.pipeline.pre_vdyp import (
    build_vdyp_prep_signature,
    load_vdyp_prep_checkpoint,
    pre_vdyp_checkpoint_path,
    save_vdyp_prep_checkpoint,
    serialize_vdyp_prep_payload,
)


def test_serialize_vdyp_prep_payload_removes_fit_func() -> None:
    fit_func = lambda x: x  # noqa: E731
    results = [
        [
            0,
            "BWBS_SW",
            {
                "L": {
                    "species": {
                        "SW": {
                            "pct": 70,
                            "fit_func": fit_func,
                        }
                    }
                }
            },
        ]
    ]

    payload = serialize_vdyp_prep_payload(results)

    assert payload[0][2]["L"]["species"]["SW"]["pct"] == 70
    assert "fit_func" not in payload[0][2]["L"]["species"]["SW"]
    assert "fit_func" in results[0][2]["L"]["species"]["SW"]


def test_save_and_load_vdyp_prep_checkpoint_roundtrip(tmp_path: Path) -> None:
    checkpoint = tmp_path / "vdyp_prep.pkl"
    results = [[1, "BWBS_PL", {"M": {"species": {"PL": {"pct": 55}}}}]]

    count = save_vdyp_prep_checkpoint(checkpoint, results)
    loaded = load_vdyp_prep_checkpoint(checkpoint)

    assert count == 1
    assert loaded == [[1, "BWBS_PL", {"M": {"species": {"PL": {"pct": 55}}}}]]


def test_load_vdyp_prep_checkpoint_rejects_signature_mismatch(tmp_path: Path) -> None:
    checkpoint = tmp_path / "vdyp_prep.pkl"
    results = [[1, "BWBS_PL", {"M": {"species": {"PL": {"pct": 55}}}}]]
    signature_a = build_vdyp_prep_signature(
        selected_strata_codes=["BWBS_PL"],
        target_area_coverage=0.65,
        min_stands_per_si_bin=25,
    )
    signature_b = build_vdyp_prep_signature(
        selected_strata_codes=["BWBS_PL", "SBS_SW"],
        target_area_coverage=0.80,
        min_stands_per_si_bin=25,
    )
    save_vdyp_prep_checkpoint(checkpoint, results, signature=signature_a)

    try:
        load_vdyp_prep_checkpoint(checkpoint, expected_signature=signature_b)
        assert False, "expected signature mismatch to raise ValueError"
    except ValueError as exc:
        assert "signature mismatch" in str(exc)


def test_load_vdyp_prep_checkpoint_accepts_legacy_payload_list(tmp_path: Path) -> None:
    import pickle

    checkpoint = tmp_path / "vdyp_prep_legacy.pkl"
    legacy_payload = [[1, "BWBS_PL", {"M": {"species": {"PL": {"pct": 55}}}}]]
    with checkpoint.open("wb") as handle:
        pickle.dump(legacy_payload, handle)

    loaded = load_vdyp_prep_checkpoint(
        checkpoint,
        expected_signature={"selected_strata_codes": ["anything"]},
    )

    assert loaded == legacy_payload


def test_pre_vdyp_checkpoint_path_defaults_and_zero_padding() -> None:
    assert pre_vdyp_checkpoint_path(tsa_code="8") == Path("data/vdyp_prep-tsa08.pkl")
    assert pre_vdyp_checkpoint_path(tsa_code="24", base_dir=Path("/tmp")) == Path(
        "/tmp/vdyp_prep-tsa24.pkl"
    )
