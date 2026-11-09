"""Optional fresh-tipsy adapter contract."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_fresh_tipsy_adapter_envelope() -> None:
    """The optional adapter preserves provenance and version metadata."""
    pytest.importorskip("fresh_tipsy")
    from fresh_tipsy.integrations import FemicResult, query_growth

    result = FemicResult(
        status="ok",
        result={"value": 1.0},
        provenance={"sha256": "abc"},
        evidence="model_output",
        warnings=(),
        error=None,
        package_version="0.1.0",
        manifest_sha256="def",
    )
    payload = result.as_dict()
    assert payload["provenance"]["sha256"] == "abc"
    assert payload["fresh_tipsy_version"] == "0.1.0"
    assert payload["data_manifest_sha256"] == "def"

    missing = query_growth(
        Path("missing-manifest.json"),
        None,
        {"species_code": "PLI", "site_index": 20, "age": 80},
    )
    assert missing.status == "error"
    assert missing.error is not None
