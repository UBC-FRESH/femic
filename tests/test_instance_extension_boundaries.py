from __future__ import annotations

import re
from pathlib import Path


INSTANCE_REFERENCE_TERMS = (
    "mkrf",
    "k3z",
    "tsa29",
    "tsa_29",
    "tfl6",
    "femic-mkrf-instance",
    "femic-k3z-instance",
    "femic-tsa29-instance",
    "femic-tfl6-instance",
)


# P88 migration baseline. These counts are maximums, not required counts: later
# extraction phases are expected to drive them down to zero.
ALLOWED_INSTANCE_REFERENCE_COUNTS = {
    "src/femic/named_pipelines.py": {"tsa29": 21},
    "src/femic/patchworks_runtime.py": {"k3z": 2},
    "src/femic/cli/main.py": {"k3z": 3, "tsa29": 2},
    "src/femic/pipeline/vdyp_overrides.py": {"tsa29": 1},
    "src/femic/tsr_catalog/recipes.py": {
        "tsa29": 61,
        "tsa_29": 1,
        "femic-tsa29-instance": 4,
    },
    "src/femic/resources/builtins/instances.builtin.yaml": {
        "k3z": 4,
        "tsa29": 5,
        "femic-k3z-instance": 2,
        "femic-tsa29-instance": 2,
    },
    "src/femic/resources/patchworks/btc_indicator_bank_compile_recipes.yaml": {"k3z": 2},
    "src/femic/resources/patchworks/variants.builtin.yaml": {
        "mkrf": 19,
        "k3z": 117,
        "femic-mkrf-instance": 6,
        "femic-k3z-instance": 45,
    },
    "src/femic/resources/instance/config/patchworks.runtime.windows.yaml": {"k3z": 3},
    "src/femic/resources/instance/config/tipsy/template.case.yaml": {"k3z": 1},
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _count_instance_references(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {
        term: len(re.findall(re.escape(term), text, flags=re.IGNORECASE))
        for term in INSTANCE_REFERENCE_TERMS
        if re.search(re.escape(term), text, flags=re.IGNORECASE)
    }


def test_no_new_named_instance_references_enter_femic_core() -> None:
    root = _repo_root()
    actual: dict[str, dict[str, int]] = {}
    for path in (root / "src" / "femic").rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        counts = _count_instance_references(path)
        if counts:
            actual[path.relative_to(root).as_posix()] = counts

    violations: list[str] = []
    for path, counts in sorted(actual.items()):
        allowed_for_path = ALLOWED_INSTANCE_REFERENCE_COUNTS.get(path, {})
        for term, count in sorted(counts.items()):
            allowed = allowed_for_path.get(term, 0)
            if count > allowed:
                violations.append(f"{path}: {term} count {count} exceeds allowed {allowed}")

    assert not violations, (
        "Named example-instance references in src/femic are migration debt. "
        "Move new instance-specific behavior into an instance package or update "
        "the P88 migration allowlist with a roadmap-linked rationale.\n"
        + "\n".join(violations)
    )
