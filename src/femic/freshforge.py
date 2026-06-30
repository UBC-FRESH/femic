"""FreshForge provider integration for FEMIC model-build workflows.

This module is intentionally non-executing. It describes FEMIC workflow stages
for FreshForge validation and planning, but it does not call FEMIC runtime
commands, inspect artifacts, or touch model inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FEMIC_PROVIDER_ID = "femic"
FEMIC_PROVIDER_VERSION = "0.1.0a1"


@dataclass(frozen=True)
class _NodeContract:
    id: str
    name: str
    description: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    parameters: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()


_NODE_CONTRACTS: tuple[_NodeContract, ...] = (
    _NodeContract(
        id="validate_case",
        name="Validate FEMIC case",
        description="Declare the FEMIC case-aware preflight seam.",
        outputs=("case_validation",),
        parameters=("instance_root", "run_config"),
    ),
    _NodeContract(
        id="geospatial_preflight",
        name="Geospatial preflight",
        description="Declare the generic geospatial runtime preflight seam.",
        inputs=("case_validation",),
        outputs=("geospatial_runtime",),
        parameters=("instance_root",),
    ),
    _NodeContract(
        id="compile_upstream",
        name="Compile upstream model inputs",
        description="Declare FEMIC Stage 00 and Stage 01a upstream compilation.",
        inputs=("geospatial_runtime",),
        outputs=("btc_handoff",),
        parameters=("instance_root", "run_config", "run_id"),
        artifacts=("run_manifest",),
    ),
    _NodeContract(
        id="btc_post_tipsy",
        name="BTC and post-TIPSY bundle",
        description="Declare the unattended BTC and Stage 01b bundle seam.",
        inputs=("btc_handoff",),
        outputs=("model_input_bundle",),
        parameters=("instance_root", "run_config", "tsa", "run_id"),
        artifacts=("btc_manifest", "post_tipsy_manifest"),
    ),
    _NodeContract(
        id="export_patchworks",
        name="Export Patchworks package",
        description="Declare the FEMIC Patchworks model-package export seam.",
        inputs=("model_input_bundle",),
        outputs=("patchworks_package",),
        parameters=("instance_root", "run_config", "tsa"),
        artifacts=("forestmodel_xml", "fragments"),
    ),
    _NodeContract(
        id="patchworks_preflight",
        name="Patchworks preflight",
        description="Declare Patchworks runtime/config preflight.",
        inputs=("patchworks_package",),
        outputs=("patchworks_runtime",),
        parameters=("instance_root", "patchworks_config"),
    ),
    _NodeContract(
        id="matrix_build",
        name="Patchworks matrix build",
        description="Declare Patchworks matrix-builder compilation.",
        inputs=("patchworks_runtime",),
        outputs=("compiled_patchworks_model",),
        parameters=("instance_root", "patchworks_config", "run_id"),
        artifacts=("matrix_build_manifest",),
    ),
)


class FemicFreshForgeProvider:
    """Non-executing FreshForge provider for FEMIC workflow stages."""

    def metadata(self) -> Any:
        """Return FreshForge provider metadata."""
        node_type_metadata, provider_metadata = _freshforge_metadata_types()
        return provider_metadata(
            id=FEMIC_PROVIDER_ID,
            version=FEMIC_PROVIDER_VERSION,
            name="FEMIC model-build provider",
            description=(
                "Non-executing provider for FEMIC model-build workflow "
                "validation, inspection, and planning."
            ),
            node_types=tuple(
                node_type_metadata(
                    id=contract.id,
                    name=contract.name,
                    description=contract.description,
                    inputs=contract.inputs,
                    outputs=contract.outputs,
                    parameters=contract.parameters,
                    artifacts=contract.artifacts,
                )
                for contract in _NODE_CONTRACTS
            ),
        )

    def validate_node(
        self, node: Any, node_type: Any, *, location: str
    ) -> tuple[Any, ...]:
        """Validate broad FEMIC node shape without executing FEMIC."""
        diagnostic, severity = _freshforge_diagnostic_types()
        diagnostics: list[Any] = []
        diagnostics.extend(
            _missing_key_diagnostics(
                diagnostic=diagnostic,
                severity=severity,
                required=tuple(node_type.inputs),
                actual=node.inputs,
                field_name="inputs",
                location=location,
            )
        )
        diagnostics.extend(
            _missing_key_diagnostics(
                diagnostic=diagnostic,
                severity=severity,
                required=tuple(node_type.outputs),
                actual=node.outputs,
                field_name="outputs",
                location=location,
            )
        )
        diagnostics.extend(
            _missing_key_diagnostics(
                diagnostic=diagnostic,
                severity=severity,
                required=tuple(node_type.parameters),
                actual=node.parameters,
                field_name="parameters",
                location=location,
            )
        )
        artifacts = node.artifacts if isinstance(node.artifacts, dict) else {}
        diagnostics.extend(
            _missing_key_diagnostics(
                diagnostic=diagnostic,
                severity=severity,
                required=tuple(node_type.artifacts),
                actual=artifacts,
                field_name="artifacts",
                location=location,
            )
        )
        diagnostics.extend(
            _empty_parameter_diagnostics(
                diagnostic=diagnostic,
                severity=severity,
                parameters=node.parameters,
                required=tuple(node_type.parameters),
                location=location,
            )
        )
        return tuple(diagnostics)


def provider_factory() -> FemicFreshForgeProvider:
    """Return the FEMIC FreshForge provider for entry-point discovery."""
    return FemicFreshForgeProvider()


def _freshforge_metadata_types() -> tuple[Any, Any]:
    try:
        from freshforge.providers import (  # type: ignore[import-untyped]
            NodeTypeMetadata,
            ProviderMetadata,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The FEMIC FreshForge integration requires the optional "
            "`femic[freshforge]` dependency."
        ) from exc
    return NodeTypeMetadata, ProviderMetadata


def _freshforge_diagnostic_types() -> tuple[Any, Any]:
    try:
        from freshforge.records import (  # type: ignore[import-untyped]
            Diagnostic,
            DiagnosticSeverity,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The FEMIC FreshForge integration requires the optional "
            "`femic[freshforge]` dependency."
        ) from exc
    return Diagnostic, DiagnosticSeverity


def _missing_key_diagnostics(
    *,
    diagnostic: Any,
    severity: Any,
    required: tuple[str, ...],
    actual: dict[str, Any],
    field_name: str,
    location: str,
) -> tuple[Any, ...]:
    return tuple(
        diagnostic(
            severity=severity.ERROR,
            code=f"femic.{field_name}.missing",
            message=(
                f"FEMIC node requires {field_name} key '{key}' for "
                "non-executing workflow planning."
            ),
            location=f"{location}.{field_name}.{key}",
        )
        for key in required
        if key not in actual
    )


def _empty_parameter_diagnostics(
    *,
    diagnostic: Any,
    severity: Any,
    parameters: dict[str, Any],
    required: tuple[str, ...],
    location: str,
) -> tuple[Any, ...]:
    diagnostics: list[Any] = []
    for key in required:
        value = parameters.get(key)
        if isinstance(value, str) and not value.strip():
            diagnostics.append(
                diagnostic(
                    severity=severity.ERROR,
                    code="femic.parameters.empty",
                    message=f"FEMIC node parameter '{key}' must be nonempty.",
                    location=f"{location}.parameters.{key}",
                )
            )
    return tuple(diagnostics)
