"""Discovery helpers for FEMIC-adjacent FreshForge workflow documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class FreshForgeWorkflowDiscoveryError(RuntimeError):
    """Raised when FreshForge workflow discovery cannot proceed."""


@dataclass(frozen=True)
class FreshForgeWorkflowRecord:
    """Summary of a discovered FreshForge workflow document."""

    path: Path
    workflow_id: str | None
    name: str | None
    description: str | None
    provider_refs: tuple[str, ...]
    kind: str
    load_status: str
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-serializable representation."""

        return {
            "path": self.path.as_posix(),
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "provider_refs": list(self.provider_refs),
            "kind": self.kind,
            "load_status": self.load_status,
            "diagnostics": list(self.diagnostics),
        }


def discover_freshforge_workflows(
    root: str | Path = ".",
) -> tuple[FreshForgeWorkflowRecord, ...]:
    """Discover FreshForge workflow YAML files under a FEMIC checkout."""

    checkout_root = Path(root)
    records = [
        _record_for_workflow(path=path, root=checkout_root)
        for path in _iter_workflow_candidates(checkout_root)
    ]
    return tuple(sorted(records, key=lambda record: record.path.as_posix()))


def build_freshforge_command_block(
    workflow_path: str | Path,
    *,
    namespace: str | None = None,
    workdir: str | Path = "runtime/freshforge",
) -> tuple[str, ...]:
    """Build copy-paste FreshForge commands for a workflow document."""

    path = Path(workflow_path)
    if not path.exists():
        raise FreshForgeWorkflowDiscoveryError(f"FreshForge workflow not found: {path}")

    path_text = path.as_posix()
    namespace_text = namespace or suggest_freshforge_namespace(path)
    workdir_text = Path(workdir).as_posix()
    return (
        f"freshforge validate {path_text}",
        f"freshforge inspect {path_text}",
        f"freshforge plan {path_text}",
        (
            f"freshforge run {path_text} --workdir {workdir_text} "
            f"--namespace {namespace_text} --json"
        ),
    )


def suggest_freshforge_namespace(workflow_path: str | Path) -> str:
    """Suggest a generic namespace from a workflow filename."""

    stem = Path(workflow_path).stem
    tokens = [token for token in stem.replace("-", "_").split("_") if token]
    if tokens and tokens[-1] == "workflow":
        tokens = tokens[:-1]
    if not tokens:
        return "workflow"

    if len(tokens) >= 2 and tokens[-2:] == ["model", "build"]:
        prefix = tokens[:-2]
        suffix = "model-build"
    else:
        prefix = tokens[:-1]
        suffix = tokens[-1]

    prefix_text = "-".join(prefix)
    if prefix_text:
        return f"{prefix_text}/{suffix}"
    return suffix


def _iter_workflow_candidates(root: Path) -> tuple[Path, ...]:
    patterns = (
        root / "examples" / "freshforge",
        root / "external",
    )
    candidates: list[Path] = []
    examples_root = patterns[0]
    if examples_root.exists():
        candidates.extend(examples_root.glob("*workflow.yaml"))

    external_root = patterns[1]
    if external_root.exists():
        candidates.extend(external_root.glob("*/workflows/freshforge/*workflow.yaml"))

    return tuple(
        path.relative_to(root) if path.is_absolute() else path
        for path in sorted(candidates, key=lambda value: value.as_posix())
    )


def _record_for_workflow(*, path: Path, root: Path) -> FreshForgeWorkflowRecord:
    load_workflow = _freshforge_loader()
    load_path = root / path
    try:
        spec, diagnostics = load_workflow(load_path)
    except Exception as exc:  # pragma: no cover - defensive against parser changes.
        return FreshForgeWorkflowRecord(
            path=path,
            workflow_id=None,
            name=None,
            description=None,
            provider_refs=(),
            kind="unknown",
            load_status="error",
            diagnostics=(str(exc),),
        )

    diagnostic_messages = tuple(_diagnostic_message(item) for item in diagnostics)
    if spec is None:
        return FreshForgeWorkflowRecord(
            path=path,
            workflow_id=None,
            name=None,
            description=None,
            provider_refs=(),
            kind="unknown",
            load_status="error",
            diagnostics=diagnostic_messages,
        )

    provider_refs = tuple(sorted({node.provider for node in spec.nodes}))
    return FreshForgeWorkflowRecord(
        path=path,
        workflow_id=spec.id,
        name=spec.name,
        description=spec.description,
        provider_refs=provider_refs,
        kind=_classify_workflow(provider_refs),
        load_status="ok" if not diagnostic_messages else "warning",
        diagnostics=diagnostic_messages,
    )


def _freshforge_loader() -> Any:
    try:
        from freshforge.loading import load_workflow  # type: ignore[import-untyped]
    except ImportError as exc:
        raise FreshForgeWorkflowDiscoveryError(
            "FreshForge workflow discovery requires the optional "
            "`femic[freshforge]` dependency."
        ) from exc
    return load_workflow


def _classify_workflow(provider_refs: tuple[str, ...]) -> str:
    if any(ref.startswith("femic.materialization.") for ref in provider_refs):
        return "materialization"
    if any(ref.startswith("femic.") for ref in provider_refs):
        return "model-build"
    return "unknown"


def _diagnostic_message(value: Any) -> str:
    message = getattr(value, "message", None)
    code = getattr(value, "code", None)
    if code and message:
        return f"{code}: {message}"
    if message:
        return str(message)
    return str(value)
