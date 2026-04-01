"""Shared FMG core model dataclasses used by export adapters/writers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CurvePoint:
    """One curve point."""

    x: float
    y: float


@dataclass(frozen=True)
class CurveDefinition:
    """Curve payload with type and ordered points."""

    curve_id: int
    curve_type: str
    points: tuple[CurvePoint, ...]


@dataclass(frozen=True)
class AnalysisUnitDefinition:
    """Normalized AU row required for downstream exports."""

    au_id: int
    tsa: str
    stratum_code: str
    si_level: str
    managed_curve_id: int
    unmanaged_curve_id: int
    source_local_au_id: int | None = None
    source_managed_local_au_id: int | None = None
    source_unmanaged_local_au_id: int | None = None


@dataclass(frozen=True)
class QmdSupportDefinition:
    """Optional per-AU support inputs for approximate QMD reconstruction."""

    site_index: float | None = None
    unmanaged_stems_per_ha: float | None = None
    managed_stems_per_ha: float | None = None
    managed_height_points: tuple[CurvePoint, ...] = ()
    managed_tph_points: tuple[CurvePoint, ...] = ()


@dataclass(frozen=True)
class BundleModelContext:
    """Shared parsed context from FEMIC bundle tables."""

    tsa_list: list[str]
    analysis_units: tuple[AnalysisUnitDefinition, ...]
    curves_by_id: dict[int, CurveDefinition]
    managed_species_curve_ids: dict[int, dict[str, int]]
    unmanaged_species_curve_ids: dict[int, dict[str, int]]
    qmd_support_by_au: dict[int, QmdSupportDefinition]
    curve_row_count: int
    managed_indicator_curves_by_au: dict[int, dict[str, tuple[CurvePoint, ...]]] = (
        field(default_factory=dict)
    )


@dataclass(frozen=True)
class DefineFieldDefinition:
    """One `<define>` entry for ForestModel serialization."""

    field: str
    column: str | None = None


@dataclass(frozen=True)
class AttributeBinding:
    """Map one feature/product attribute label to a curve reference."""

    label: str
    curve_idref: str


@dataclass(frozen=True)
class TreatmentAssignment:
    """One assignment within a treatment produce block."""

    field: str
    value: str


@dataclass(frozen=True)
class TreatmentDefinition:
    """Treatment definition used in track blocks."""

    label: str
    min_age: int
    max_age: int
    adjust: str | None = None
    assignments: tuple[TreatmentAssignment, ...] = ()
    transition_assignments: tuple[TreatmentAssignment, ...] = ()


@dataclass(frozen=True)
class RetentionDefinition:
    """One retention definition applied within a select statement."""

    factor: str
    assignments: tuple[TreatmentAssignment, ...] = ()
    feature_attributes: tuple[AttributeBinding, ...] = ()


@dataclass(frozen=True)
class SelectDefinition:
    """One select statement plus optional features/products/track treatment."""

    statement: str
    feature_attributes: tuple[AttributeBinding, ...] = ()
    product_attributes: tuple[AttributeBinding, ...] = ()
    retention_definitions: tuple[RetentionDefinition, ...] = ()
    include_track: bool = False
    track_treatment: TreatmentDefinition | None = None
    track_treatments: tuple[TreatmentDefinition, ...] = ()


@dataclass(frozen=True)
class ForestModelDefinition:
    """Core ForestModel representation independent from XML serializer."""

    description: str
    horizon: int
    year: int
    match: str
    input_attributes: dict[str, str]
    output_attributes: dict[str, str]
    define_fields: tuple[DefineFieldDefinition, ...]
    curves: dict[str, tuple[CurvePoint, ...]]
    selects: tuple[SelectDefinition, ...]
