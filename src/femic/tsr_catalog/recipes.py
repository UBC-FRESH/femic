"""Instance-local TSR recipe scaffold helpers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources as importlib_resources
import json
from pathlib import Path
from typing import Any

import yaml

from .overlay import TsrOverlayTsaRecord


class TsrRecipeError(RuntimeError):
    """Raised when TSR recipe initialization or loading fails."""


_TSR_RECIPE_RESOURCE_PACKAGE = "femic.resources.tsr_recipes"
_SOURCE_LAYERS_RECIPE_RESOURCE = "source_layers.recipe.yaml"
_THLB_NETDOWN_RECIPE_RESOURCE = "thlb_netdown.recipe.yaml"


@dataclass(frozen=True)
class TsrRecipeCanonicalInputs:
    """Canonical shared inputs referenced by TSR recipes."""

    registry_path: str
    documents_path: str
    candidate_facts_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "registry_path": self.registry_path,
            "documents_path": self.documents_path,
            "candidate_facts_path": self.candidate_facts_path,
        }


@dataclass(frozen=True)
class TsrSourceLayersRecipeInstanceInputs:
    """Instance-local inputs referenced by the source-layer recipe."""

    overlay_path: str
    source_layer_overrides_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "overlay_path": self.overlay_path,
            "source_layer_overrides_path": self.source_layer_overrides_path,
        }


@dataclass(frozen=True)
class TsrThlbNetdownRecipeInstanceInputs:
    """Instance-local inputs referenced by the THLB netdown recipe."""

    overlay_path: str
    source_layer_recipe_path: str
    source_layer_overrides_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "overlay_path": self.overlay_path,
            "source_layer_recipe_path": self.source_layer_recipe_path,
            "source_layer_overrides_path": self.source_layer_overrides_path,
        }


@dataclass(frozen=True)
class TsrSourceLayersRecipeRecord:
    """One instance-local source-layer recipe scaffold."""

    schema_version: int
    recipe_kind: str
    tsa: TsrOverlayTsaRecord
    canonical_inputs: TsrRecipeCanonicalInputs
    instance_inputs: TsrSourceLayersRecipeInstanceInputs
    recipe_contract: dict[str, Any]
    entries: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "recipe_kind": self.recipe_kind,
            "tsa": self.tsa.to_dict(),
            "canonical_inputs": self.canonical_inputs.to_dict(),
            "instance_inputs": self.instance_inputs.to_dict(),
            "recipe_contract": dict(self.recipe_contract),
            "entries": [dict(entry) for entry in self.entries],
        }


@dataclass(frozen=True)
class TsrThlbNetdownRecipeRecord:
    """One instance-local THLB netdown recipe scaffold."""

    schema_version: int
    recipe_kind: str
    tsa: TsrOverlayTsaRecord
    canonical_inputs: TsrRecipeCanonicalInputs
    instance_inputs: TsrThlbNetdownRecipeInstanceInputs
    recipe_contract: dict[str, Any]
    steps: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "recipe_kind": self.recipe_kind,
            "tsa": self.tsa.to_dict(),
            "canonical_inputs": self.canonical_inputs.to_dict(),
            "instance_inputs": self.instance_inputs.to_dict(),
            "recipe_contract": dict(self.recipe_contract),
            "steps": [dict(step) for step in self.steps],
        }


@dataclass(frozen=True)
class TsrRecipeInitResult:
    """Result payload for recipe scaffold initialization."""

    tsa: TsrOverlayTsaRecord
    source_layers_recipe_path: Path
    thlb_netdown_recipe_path: Path
    created_source_layers_recipe: bool
    created_thlb_netdown_recipe: bool


def _read_json_object(path: Path, *, description: str) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrRecipeError(f"{description} not found: {resolved}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid {description.lower()} payload: {resolved}")
    return payload


def _normalize_tsa_token(value: str) -> str:
    return value.strip().replace("_", " ").casefold()


def _resolve_tsa_record(*, tsa: str, registry_path: Path) -> TsrOverlayTsaRecord:
    payload = _read_json_object(registry_path, description="TSR registry JSON")
    records = payload.get("tsas")
    if not isinstance(records, list):
        raise TsrRecipeError("TSR registry JSON is missing a valid `tsas` list.")
    normalized = _normalize_tsa_token(tsa)
    matches: list[TsrOverlayTsaRecord] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        record = TsrOverlayTsaRecord(
            tsa_id=str(item.get("tsa_id", "")),
            tsa_code=str(item.get("tsa_code", "")),
            tsa_name=str(item.get("tsa_name", "")),
        )
        if normalized in {
            _normalize_tsa_token(record.tsa_id),
            _normalize_tsa_token(record.tsa_code),
            _normalize_tsa_token(record.tsa_code.lstrip("0") or record.tsa_code),
            _normalize_tsa_token(record.tsa_name),
        }:
            matches.append(record)
    if not matches:
        raise TsrRecipeError(f"No canonical TSR TSA match found for `{tsa}`.")
    if len(matches) > 1:
        labels = ", ".join(f"{record.tsa_code}:{record.tsa_name}" for record in matches)
        raise TsrRecipeError(f"Ambiguous TSR TSA match for `{tsa}`: {labels}")
    return matches[0]


def _load_resource_yaml(resource_name: str) -> dict[str, Any]:
    resource = importlib_resources.files(_TSR_RECIPE_RESOURCE_PACKAGE).joinpath(
        resource_name
    )
    payload = yaml.safe_load(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid packaged TSR recipe template: {resource_name}")
    return payload


def _repo_relative(path: Path, *, source_root: Path) -> str:
    return path.expanduser().resolve().relative_to(source_root.resolve()).as_posix()


def default_tsr_source_layers_recipe_path(*, instance_root: Path) -> Path:
    """Return the default per-instance source-layer recipe path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml"
    )


def default_tsr_thlb_netdown_recipe_path(*, instance_root: Path) -> Path:
    """Return the default per-instance THLB netdown recipe path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml"
    )


def _write_recipe_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def init_tsr_recipe_scaffolds(
    *,
    instance_root: Path,
    tsa: str,
    registry_path: Path,
    documents_path: Path,
    candidate_facts_path: Path,
    source_root: Path,
    overlay_path: Path,
    overrides_path: Path,
    source_layers_recipe_path: Path,
    thlb_netdown_recipe_path: Path,
    overwrite: bool = False,
) -> TsrRecipeInitResult:
    """Initialize per-instance TSR recipe scaffold YAML files."""

    resolved_instance_root = instance_root.expanduser().resolve()
    resolved_registry_path = registry_path.expanduser().resolve()
    resolved_documents_path = documents_path.expanduser().resolve()
    resolved_candidate_facts_path = candidate_facts_path.expanduser().resolve()
    resolved_overlay_path = overlay_path.expanduser().resolve()
    resolved_overrides_path = overrides_path.expanduser().resolve()
    resolved_source_layers_recipe_path = (
        source_layers_recipe_path.expanduser().resolve()
    )
    resolved_thlb_netdown_recipe_path = thlb_netdown_recipe_path.expanduser().resolve()

    for candidate_path in (
        resolved_overlay_path,
        resolved_overrides_path,
        resolved_source_layers_recipe_path,
        resolved_thlb_netdown_recipe_path,
    ):
        try:
            candidate_path.relative_to(resolved_instance_root)
        except ValueError as exc:
            raise TsrRecipeError(
                "TSR recipe paths must live under the instance root."
            ) from exc

    if not overwrite:
        existing = [
            path
            for path in (
                resolved_source_layers_recipe_path,
                resolved_thlb_netdown_recipe_path,
            )
            if path.exists()
        ]
        if existing:
            joined = ", ".join(str(path) for path in existing)
            raise TsrRecipeError(
                "TSR recipe scaffold(s) already exist: "
                f"{joined}. Use `--overwrite` to replace them."
            )

    tsa_record = _resolve_tsa_record(tsa=tsa, registry_path=resolved_registry_path)
    canonical_inputs = TsrRecipeCanonicalInputs(
        registry_path=_repo_relative(resolved_registry_path, source_root=source_root),
        documents_path=_repo_relative(resolved_documents_path, source_root=source_root),
        candidate_facts_path=_repo_relative(
            resolved_candidate_facts_path, source_root=source_root
        ),
    )
    source_layers_instance_inputs = TsrSourceLayersRecipeInstanceInputs(
        overlay_path=str(
            resolved_overlay_path.relative_to(resolved_instance_root).as_posix()
        ),
        source_layer_overrides_path=str(
            resolved_overrides_path.relative_to(resolved_instance_root).as_posix()
        ),
    )
    thlb_instance_inputs = TsrThlbNetdownRecipeInstanceInputs(
        overlay_path=str(
            resolved_overlay_path.relative_to(resolved_instance_root).as_posix()
        ),
        source_layer_recipe_path=str(
            resolved_source_layers_recipe_path.relative_to(
                resolved_instance_root
            ).as_posix()
        ),
        source_layer_overrides_path=str(
            resolved_overrides_path.relative_to(resolved_instance_root).as_posix()
        ),
    )

    source_layers_template = _load_resource_yaml(_SOURCE_LAYERS_RECIPE_RESOURCE)
    thlb_template = _load_resource_yaml(_THLB_NETDOWN_RECIPE_RESOURCE)

    source_layers_record = TsrSourceLayersRecipeRecord(
        schema_version=int(source_layers_template.get("schema_version", 1)),
        recipe_kind=str(source_layers_template.get("recipe_kind", "source_layers")),
        tsa=tsa_record,
        canonical_inputs=canonical_inputs,
        instance_inputs=source_layers_instance_inputs,
        recipe_contract=dict(source_layers_template.get("recipe_contract", {})),
        entries=(),
    )
    thlb_record = TsrThlbNetdownRecipeRecord(
        schema_version=int(thlb_template.get("schema_version", 1)),
        recipe_kind=str(thlb_template.get("recipe_kind", "thlb_netdown")),
        tsa=tsa_record,
        canonical_inputs=canonical_inputs,
        instance_inputs=thlb_instance_inputs,
        recipe_contract=dict(thlb_template.get("recipe_contract", {})),
        steps=(),
    )

    _write_recipe_yaml(
        resolved_source_layers_recipe_path,
        source_layers_record.to_dict(),
    )
    _write_recipe_yaml(
        resolved_thlb_netdown_recipe_path,
        thlb_record.to_dict(),
    )
    return TsrRecipeInitResult(
        tsa=tsa_record,
        source_layers_recipe_path=resolved_source_layers_recipe_path,
        thlb_netdown_recipe_path=resolved_thlb_netdown_recipe_path,
        created_source_layers_recipe=True,
        created_thlb_netdown_recipe=True,
    )


def load_tsr_source_layers_recipe(path: Path) -> TsrSourceLayersRecipeRecord:
    """Load one per-instance source-layer recipe scaffold YAML file."""

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrRecipeError(f"TSR source-layer recipe not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid TSR source-layer recipe payload: {resolved}")
    if str(payload.get("recipe_kind", "")) != "source_layers":
        raise TsrRecipeError(f"Invalid TSR source-layer recipe kind: {resolved}")
    tsa_payload = payload.get("tsa")
    canonical_payload = payload.get("canonical_inputs")
    instance_payload = payload.get("instance_inputs")
    if (
        not isinstance(tsa_payload, dict)
        or not isinstance(canonical_payload, dict)
        or not isinstance(instance_payload, dict)
    ):
        raise TsrRecipeError(f"Invalid TSR source-layer recipe structure: {resolved}")
    return TsrSourceLayersRecipeRecord(
        schema_version=int(payload.get("schema_version", 1)),
        recipe_kind="source_layers",
        tsa=TsrOverlayTsaRecord(
            tsa_id=str(tsa_payload.get("tsa_id", "")),
            tsa_code=str(tsa_payload.get("tsa_code", "")),
            tsa_name=str(tsa_payload.get("tsa_name", "")),
        ),
        canonical_inputs=TsrRecipeCanonicalInputs(
            registry_path=str(canonical_payload.get("registry_path", "")),
            documents_path=str(canonical_payload.get("documents_path", "")),
            candidate_facts_path=str(canonical_payload.get("candidate_facts_path", "")),
        ),
        instance_inputs=TsrSourceLayersRecipeInstanceInputs(
            overlay_path=str(instance_payload.get("overlay_path", "")),
            source_layer_overrides_path=str(
                instance_payload.get("source_layer_overrides_path", "")
            ),
        ),
        recipe_contract=dict(payload.get("recipe_contract", {})),
        entries=tuple(
            item for item in payload.get("entries", []) if isinstance(item, dict)
        ),
    )


def load_tsr_thlb_netdown_recipe(path: Path) -> TsrThlbNetdownRecipeRecord:
    """Load one per-instance THLB netdown recipe scaffold YAML file."""

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrRecipeError(f"TSR THLB netdown recipe not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid TSR THLB netdown recipe payload: {resolved}")
    if str(payload.get("recipe_kind", "")) != "thlb_netdown":
        raise TsrRecipeError(f"Invalid TSR THLB netdown recipe kind: {resolved}")
    tsa_payload = payload.get("tsa")
    canonical_payload = payload.get("canonical_inputs")
    instance_payload = payload.get("instance_inputs")
    if (
        not isinstance(tsa_payload, dict)
        or not isinstance(canonical_payload, dict)
        or not isinstance(instance_payload, dict)
    ):
        raise TsrRecipeError(f"Invalid TSR THLB netdown recipe structure: {resolved}")
    return TsrThlbNetdownRecipeRecord(
        schema_version=int(payload.get("schema_version", 1)),
        recipe_kind="thlb_netdown",
        tsa=TsrOverlayTsaRecord(
            tsa_id=str(tsa_payload.get("tsa_id", "")),
            tsa_code=str(tsa_payload.get("tsa_code", "")),
            tsa_name=str(tsa_payload.get("tsa_name", "")),
        ),
        canonical_inputs=TsrRecipeCanonicalInputs(
            registry_path=str(canonical_payload.get("registry_path", "")),
            documents_path=str(canonical_payload.get("documents_path", "")),
            candidate_facts_path=str(canonical_payload.get("candidate_facts_path", "")),
        ),
        instance_inputs=TsrThlbNetdownRecipeInstanceInputs(
            overlay_path=str(instance_payload.get("overlay_path", "")),
            source_layer_recipe_path=str(
                instance_payload.get("source_layer_recipe_path", "")
            ),
            source_layer_overrides_path=str(
                instance_payload.get("source_layer_overrides_path", "")
            ),
        ),
        recipe_contract=dict(payload.get("recipe_contract", {})),
        steps=tuple(
            item for item in payload.get("steps", []) if isinstance(item, dict)
        ),
    )
