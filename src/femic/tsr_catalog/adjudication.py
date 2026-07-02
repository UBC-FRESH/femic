"""TSR adjudication overlay extension points."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Protocol, cast

import yaml


TSR_ADJUDICATION_OVERLAY_ENTRY_POINT_GROUP = "femic.tsr_adjudication_overlays"
TSR_ADJUDICATION_OVERLAY_CONFIG_RELATIVE_PATH = Path(
    "config/tsr/adjudication_overlay.yaml"
)


class TsrAdjudicationOverlayError(RuntimeError):
    """Raised when TSR adjudication overlay configuration is invalid."""


@dataclass(frozen=True)
class TsrLandBaseSummaryRowClassification:
    """Classification for one TSR land-base summary row."""

    land_base_stage: str
    execution_class: str
    benchmark_role: str


@dataclass(frozen=True)
class TsrReconstructionGapInterpretation:
    """Instance-specific interpretation for one reconstruction comparison row."""

    problem_ownership: str
    difference_nature: str
    engineering_interpretation: str
    recommended_next_move: str


class TsrAdjudicationOverlayProvider(Protocol):
    """Provider hook for instance-owned TSR adjudication policy."""

    provider_id: str

    def classify_land_base_summary_row(
        self, *, label: str
    ) -> TsrLandBaseSummaryRowClassification | None:
        """Return an instance-specific row classification, when known."""
        ...

    def validate_checkpoint_path(
        self, *, instance_root: Path, checkpoint_path: Path
    ) -> None:
        """Reject checkpoint paths that violate instance adjudication policy."""
        ...

    def is_strict_seam_checkpoint_path(
        self, *, instance_root: Path, checkpoint_path: Path
    ) -> bool:
        """Return whether a checkpoint is an instance-approved strict seam."""
        ...

    def reconstruction_gap_interpretation(
        self, *, recipe_tsa_id: str, parent_step: dict[str, Any]
    ) -> TsrReconstructionGapInterpretation | None:
        """Return an instance-specific reconstruction-gap interpretation."""
        ...

    def report_notes(self, *, recipe_tsa_id: str) -> tuple[str, ...]:
        """Return instance-specific plain-language report notes."""
        ...


_TSR_ADJUDICATION_OVERLAY_PROVIDERS: dict[str, TsrAdjudicationOverlayProvider] = {}
_DISCOVERED_TSR_ADJUDICATION_OVERLAYS = False


def register_tsr_adjudication_overlay_provider(
    provider: TsrAdjudicationOverlayProvider,
) -> None:
    """Register one TSR adjudication overlay provider in-process."""

    provider_id = str(getattr(provider, "provider_id", "")).strip()
    if not provider_id:
        raise TsrAdjudicationOverlayError(
            "TSR adjudication overlay provider is missing `provider_id`."
        )
    if provider_id in _TSR_ADJUDICATION_OVERLAY_PROVIDERS:
        raise TsrAdjudicationOverlayError(
            f"TSR adjudication overlay provider already registered: {provider_id}"
        )
    _TSR_ADJUDICATION_OVERLAY_PROVIDERS[provider_id] = provider


def _load_adjudication_entry_point(
    entry_point: metadata.EntryPoint,
) -> TsrAdjudicationOverlayProvider:
    loaded = entry_point.load()
    candidate = loaded() if callable(loaded) else loaded
    provider_id = str(getattr(candidate, "provider_id", "")).strip()
    if not provider_id:
        raise TsrAdjudicationOverlayError(
            "TSR adjudication overlay entry point "
            f"`{entry_point.name}` did not provide an object with `provider_id`."
        )
    return cast(TsrAdjudicationOverlayProvider, candidate)


def discover_tsr_adjudication_overlay_providers() -> tuple[str, ...]:
    """Discover installed TSR adjudication overlay providers from entry points."""

    global _DISCOVERED_TSR_ADJUDICATION_OVERLAYS
    discovered: list[str] = []
    selected = metadata.entry_points().select(
        group=TSR_ADJUDICATION_OVERLAY_ENTRY_POINT_GROUP
    )
    for entry_point in selected:
        provider = _load_adjudication_entry_point(entry_point)
        register_tsr_adjudication_overlay_provider(provider)
        discovered.append(provider.provider_id)
    _DISCOVERED_TSR_ADJUDICATION_OVERLAYS = True
    return tuple(discovered)


def _ensure_tsr_adjudication_overlay_providers_discovered() -> None:
    global _DISCOVERED_TSR_ADJUDICATION_OVERLAYS
    if _DISCOVERED_TSR_ADJUDICATION_OVERLAYS:
        return
    discover_tsr_adjudication_overlay_providers()
    _DISCOVERED_TSR_ADJUDICATION_OVERLAYS = True


def get_tsr_adjudication_overlay_provider(
    provider_id: str,
) -> TsrAdjudicationOverlayProvider:
    """Return one registered TSR adjudication overlay provider."""

    _ensure_tsr_adjudication_overlay_providers_discovered()
    normalized = provider_id.strip()
    provider = _TSR_ADJUDICATION_OVERLAY_PROVIDERS.get(normalized)
    if provider is None:
        raise TsrAdjudicationOverlayError(
            "TSR adjudication overlay provider is not installed or registered: "
            f"{normalized}"
        )
    return provider


def _load_overlay_config_provider_id(config_path: Path) -> str | None:
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TsrAdjudicationOverlayError(
            f"Invalid TSR adjudication overlay config: {config_path}"
        ) from exc
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise TsrAdjudicationOverlayError(
            f"TSR adjudication overlay config must be a mapping: {config_path}"
        )
    provider_id = str(payload.get("provider_id", "")).strip()
    if not provider_id:
        raise TsrAdjudicationOverlayError(
            f"TSR adjudication overlay config is missing `provider_id`: {config_path}"
        )
    return provider_id


def resolve_tsr_adjudication_overlay_provider(
    *, instance_root: Path
) -> TsrAdjudicationOverlayProvider | None:
    """Resolve the instance-selected TSR adjudication overlay provider, if any."""

    config_path = (
        instance_root.expanduser().resolve()
        / TSR_ADJUDICATION_OVERLAY_CONFIG_RELATIVE_PATH
    )
    if not config_path.exists():
        return None
    provider_id = _load_overlay_config_provider_id(config_path)
    if provider_id is None:
        return None
    return get_tsr_adjudication_overlay_provider(provider_id)
