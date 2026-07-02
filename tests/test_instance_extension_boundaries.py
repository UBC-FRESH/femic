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


ALLOWED_INSTANCE_REFERENCE_COUNTS: dict[str, dict[str, int]] = {}


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
                violations.append(
                    f"{path}: {term} count {count} exceeds allowed {allowed}"
                )

    assert not violations, (
        "Named example-instance references are not allowed in src/femic. Move "
        "instance-specific behavior into an instance package or explicit user "
        "configuration.\n" + "\n".join(violations)
    )
