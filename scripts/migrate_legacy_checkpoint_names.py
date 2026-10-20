"""Rename instance artifacts that still carry the retired ``ria_`` prefix.

``ria_`` is leftover Western Boreal Initiative nomenclature. FEMIC no longer writes or
looks for it; this script renames existing artifacts so an older instance keeps working.

It is a migration, not a naming convention: this is the only file in the repository
permitted to contain the old prefix, and ``tests/test_no_ria_prefix.py`` enforces that.

Usage::

    python scripts/migrate_legacy_checkpoint_names.py --instance-root .
    python scripts/migrate_legacy_checkpoint_names.py --instance-root . --apply

The default is a dry run. With ``--apply`` the script uses ``git mv`` inside a git
working tree, which keeps git-annex keys intact; outside a work tree it falls back to
``Path.rename``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

OLD_TO_NEW = (
    ("ria_vri_vclr1p_checkpoint", "vri_vclr1p_checkpoint"),
    ("ria_maptiles.csv", "maptiles.csv"),
)


def _is_git_worktree(root: Path) -> bool:
    """Return True when ``root`` is inside a git working tree."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def plan(instance_root: Path) -> list[tuple[Path, Path]]:
    """Return the (source, destination) renames the instance needs."""
    renames: list[tuple[Path, Path]] = []
    for old_stem, new_stem in OLD_TO_NEW:
        for path in sorted(instance_root.rglob(f"{old_stem}*")):
            if not path.is_file() or ".git" in path.parts:
                continue
            renames.append((path, path.with_name(path.name.replace(old_stem, new_stem, 1))))
    return renames


def apply_renames(instance_root: Path, renames: list[tuple[Path, Path]]) -> None:
    """Rename each pair, preferring ``git mv`` so annex pointers survive."""
    use_git = _is_git_worktree(instance_root)
    for source, target in renames:
        if use_git:
            subprocess.run(  # noqa: S603
                ["git", "-C", str(instance_root), "mv", str(source), str(target)],
                check=True,
            )
        else:
            source.rename(target)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-root", type=Path, default=Path("."), dest="instance_root")
    parser.add_argument("--apply", action="store_true", help="perform the renames")
    args = parser.parse_args()

    renames = plan(args.instance_root.resolve())
    if not renames:
        print("No legacy names found.")
        return
    for source, target in renames:
        print(f"{'rename' if args.apply else 'would rename'}: {source.name} -> {target.name}")
    if not args.apply:
        print(f"\n{len(renames)} file(s) would be renamed. Re-run with --apply.")
        return
    apply_renames(args.instance_root.resolve(), renames)
    print(f"\nRenamed {len(renames)} file(s). Commit the change.")


if __name__ == "__main__":
    sys.exit(main())
