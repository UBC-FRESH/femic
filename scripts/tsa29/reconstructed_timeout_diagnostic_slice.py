from __future__ import annotations

import argparse
import json
from pathlib import Path

from femic.tsr_catalog.recipes import (
    load_tsr_thlb_netdown_recipe,
    run_tsr_thlb_reconstructed_diagnostic_slice,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one reconstructed THLB diagnostic slice without mutating live recipe surfaces."
    )
    parser.add_argument("--recipe-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--audit-path", type=Path, required=True)
    parser.add_argument("--diagnostic-path", type=Path, required=True)
    parser.add_argument("--checkpoint-path", type=Path, default=None)
    parser.add_argument("--resume-checkpoint-path", type=Path, default=None)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--end-index", type=int, default=None)
    parser.add_argument(
        "--allow-stand-binary-fallback",
        action="store_true",
        help="Enable the explicit debug stand-binary fallback.",
    )
    parser.add_argument(
        "--list-executable-steps",
        action="store_true",
        help="Print the reconstructed executable-step inventory and exit.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    recipe = load_tsr_thlb_netdown_recipe(args.recipe_path.expanduser().resolve())
    if args.list_executable_steps:
        steps = [
            {
                "index": index,
                "step_id": str(step.get("step_id", "")).strip(),
                "label": str(step.get("label", "")).strip(),
                "normalized_action": str(step.get("normalized_action", "")).strip(),
            }
            for index, step in enumerate(recipe.steps)
            if str(step.get("normalized_action", "")).strip()
            in {"use_land_base", "no_deduction", "exclude"}
        ]
        print(json.dumps({"executable_steps": steps}, indent=2))
        return

    result = run_tsr_thlb_reconstructed_diagnostic_slice(
        recipe_path=args.recipe_path,
        checkpoint_path=args.checkpoint_path,
        resume_checkpoint_path=args.resume_checkpoint_path,
        output_path=args.output_path,
        audit_path=args.audit_path,
        diagnostic_path=args.diagnostic_path,
        start_index=args.start_index,
        end_index=args.end_index,
        allow_stand_binary_fallback=args.allow_stand_binary_fallback,
    )
    print(
        json.dumps(
            {
                "output_path": str(result.output_path),
                "audit_path": str(result.audit_path),
                "diagnostic_path": str(result.diagnostic_path),
                "executed_step_ids": list(result.executed_step_ids),
                "start_index": result.start_index,
                "end_index": result.end_index,
                "step_count": result.step_count,
                "outcome_counts": result.outcome_counts,
                "baseline_managed_area_ha": result.baseline_managed_area_ha,
                "final_managed_area_ha": result.final_managed_area_ha,
                "total_seconds": result.total_seconds,
                "resumed_from_checkpoint": result.resumed_from_checkpoint,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
