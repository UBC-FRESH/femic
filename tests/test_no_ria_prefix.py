"""Guard against reintroducing the retired ``ria_`` filename prefix.

The prefix is leftover nomenclature from the Western Boreal Initiative project and has
no meaning in FEMIC. It was purged once and reintroduced several times because it read
like a data convention, so this test makes a reintroduction fail loudly.

The only permitted occurrence is the migration script, which has to name the old prefix
in order to find and rename it.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = (REPO_ROOT / "src" / "femic", REPO_ROOT / "scripts")
ALLOWED_FILES = {
    # Names the retired prefix on purpose: it exists to rename those files.
    REPO_ROOT / "scripts" / "migrate_legacy_checkpoint_names.py",
}

# A prefix at the start of an identifier or filename stem. Deliberately does not match
# ``wbi_ria_yield`` or ``Armillaria_OAF``: the lookbehind requires a non-word character.
PATTERN = re.compile(r"(?<![A-Za-z0-9_])ria_[A-Za-z0-9_]+")


def _offenders() -> list[str]:
    found: list[str] = []
    for root in SEARCH_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if path in ALLOWED_FILES:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                match = PATTERN.search(line)
                if match:
                    found.append(
                        f"{path.relative_to(REPO_ROOT)}:{number}: {match.group(0)}"
                    )
    return found


def test_no_ria_prefix_in_filenames_or_identifiers() -> None:
    offenders = _offenders()
    assert not offenders, (
        "The retired 'ria_' prefix is back. It is leftover Western Boreal Initiative "
        "nomenclature and means nothing in FEMIC; use the plain name. Offenders:\n  "
        + "\n  ".join(offenders)
    )
