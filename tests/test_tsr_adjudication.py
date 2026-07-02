from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from femic.tsr_catalog import adjudication


class _FixtureProvider:
    provider_id = "fixture"

    def classify_land_base_summary_row(self, *, label: str) -> None:
        _ = label
        return None

    def validate_checkpoint_path(
        self, *, instance_root: Path, checkpoint_path: Path
    ) -> None:
        _ = instance_root
        _ = checkpoint_path

    def is_strict_seam_checkpoint_path(
        self, *, instance_root: Path, checkpoint_path: Path
    ) -> bool:
        _ = instance_root
        _ = checkpoint_path
        return False

    def reconstruction_gap_interpretation(
        self, *, recipe_tsa_id: str, parent_step: dict[str, object]
    ) -> None:
        _ = recipe_tsa_id
        _ = parent_step
        return None

    def report_notes(self, *, recipe_tsa_id: str) -> tuple[str, ...]:
        _ = recipe_tsa_id
        return ()


def _reset_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adjudication, "_TSR_ADJUDICATION_OVERLAY_PROVIDERS", {})
    monkeypatch.setattr(adjudication, "_DISCOVERED_TSR_ADJUDICATION_OVERLAYS", True)


def test_register_tsr_adjudication_overlay_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_registry(monkeypatch)
    provider = _FixtureProvider()

    adjudication.register_tsr_adjudication_overlay_provider(provider)

    assert adjudication.get_tsr_adjudication_overlay_provider("fixture") is provider


def test_register_tsr_adjudication_overlay_provider_rejects_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_registry(monkeypatch)
    adjudication.register_tsr_adjudication_overlay_provider(_FixtureProvider())

    with pytest.raises(
        adjudication.TsrAdjudicationOverlayError, match="already registered"
    ):
        adjudication.register_tsr_adjudication_overlay_provider(_FixtureProvider())


def test_resolve_tsr_adjudication_overlay_provider_uses_instance_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _reset_registry(monkeypatch)
    provider = _FixtureProvider()
    adjudication.register_tsr_adjudication_overlay_provider(provider)
    config_path = tmp_path / "config" / "tsr" / "adjudication_overlay.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("provider_id: fixture\n", encoding="utf-8")

    resolved = adjudication.resolve_tsr_adjudication_overlay_provider(
        instance_root=tmp_path
    )

    assert resolved is provider


def test_resolve_tsr_adjudication_overlay_provider_returns_none_without_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _reset_registry(monkeypatch)

    assert (
        adjudication.resolve_tsr_adjudication_overlay_provider(instance_root=tmp_path)
        is None
    )


def test_resolve_tsr_adjudication_overlay_provider_reports_missing_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _reset_registry(monkeypatch)
    config_path = tmp_path / "config" / "tsr" / "adjudication_overlay.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("provider_id: missing\n", encoding="utf-8")

    with pytest.raises(adjudication.TsrAdjudicationOverlayError, match="not installed"):
        adjudication.resolve_tsr_adjudication_overlay_provider(instance_root=tmp_path)


def test_discover_tsr_adjudication_overlay_providers_loads_entry_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adjudication, "_TSR_ADJUDICATION_OVERLAY_PROVIDERS", {})
    monkeypatch.setattr(adjudication, "_DISCOVERED_TSR_ADJUDICATION_OVERLAYS", False)
    provider = _FixtureProvider()
    entry_point = SimpleNamespace(name="fixture", load=lambda: lambda: provider)

    class _EntryPoints:
        def select(self, *, group: str) -> tuple[object, ...]:
            assert group == adjudication.TSR_ADJUDICATION_OVERLAY_ENTRY_POINT_GROUP
            return (entry_point,)

    monkeypatch.setattr(
        adjudication.metadata,
        "entry_points",
        lambda: _EntryPoints(),
    )

    discovered = adjudication.discover_tsr_adjudication_overlay_providers()

    assert discovered == ("fixture",)
