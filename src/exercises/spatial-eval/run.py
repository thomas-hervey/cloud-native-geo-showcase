"""Top-level runner/dispatcher for the 33-spatial-eval pipeline.

Usage:
    uv run python run.py --help
    uv run python run.py gt-compare
    uv run python run.py batch-eval --models gemini/gemini-2.0-flash
    uv run python run.py audit
    uv run python run.py leaderboard --gt-source sf_planning
    uv run python run.py analysis --metric iou --gt-source sf_planning
    uv run python run.py smoke --place "The Mission" --model claude-haiku-4-5
    uv run python run.py prompt-exp
    uv run python run.py compact-db

Each step passes unknown arguments through to the underlying script unchanged.
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent / "scripts"

STEPS: dict[str, dict] = {
    "gt-compare": {
        "script": "run_gt_comparison.py",
        "description": (
            "Run GT-vs-GT pairwise comparison across all active corpus places. "
            "Run once before first batch eval, and again when you add a new GT source."
        ),
    },
    "batch-eval": {
        "script": "run_batch_eval.py",
        "description": (
            "Run all models × all places × specified GT sources. "
            "This is your daily/weekly eval driver — idempotent; safe to re-run."
        ),
    },
    "audit": {
        "script": "audit_gt_coverage.py",
        "description": (
            "Pre-eval coverage audit: check which GT sources have polygons for each "
            "active corpus place. Run before batch-eval to catch missing aliases."
        ),
    },
    "leaderboard": {
        "script": "leaderboard.py",
        "description": "Print models ranked by composite score for a given GT source.",
    },
    "analysis": {
        "script": "run_analysis.py",
        "description": (
            "Print per-metric summary (iou, centroid_error_m, composite, gt-vs-gt). "
            "Use --metric iou, --metric composite, or --source-type gt."
        ),
    },
    "smoke": {
        "script": "run_eval.py",
        "description": (
            "Single-place smoke test. Use before a full batch-eval to verify "
            "your API keys and GT sources are working correctly."
        ),
        "default_args": ["--place", "The Mission", "--model", "claude-haiku-4-5"],
    },
    "prompt-exp": {
        "script": "run_prompt_experiment.py",
        "description": "CLI version of the Streamlit prompt experiment runner.",
    },
    "migrate-db": {
        "script": "migrate_db.py",
        "description": (
            "Build a variant-aware comparisons DB from existing cache and DB artifacts. "
            "Use this during prompt-variant schema migrations."
        ),
    },
}


def _compact_db() -> None:
    """Rebuild eval.duckdb from the canonical schema (flushes WAL, reclaims space)."""
    from db_duckdb import compact_database

    db_path = Path(__file__).parent / "data" / "eval.duckdb"
    if not db_path.exists():
        print(f"Error: {db_path} not found.", file=sys.stderr)
        sys.exit(1)

    size_before = db_path.stat().st_size / (1024 * 1024)
    rows_before, rows_after = compact_database(db_path)
    size_after = db_path.stat().st_size / (1024 * 1024)
    print(f"Size: {size_before:.1f} MB -> {size_after:.1f} MB")
    print(f"Rows: {rows_before} -> {rows_after}"
          + (f" ({rows_before - rows_after} duplicate(s) removed)" if rows_after != rows_before else ""))


def _print_help() -> None:
    print("SF Spatial Eval — pipeline runner\n")
    print(f"  Usage: uv run python run.py <step> [step-args]\n")
    print("Steps (run in this order for a full baseline):\n")
    for step_name, info in STEPS.items():
        print(f"  {step_name:<14} {info['description']}")
        default_args = info.get("default_args")
        if default_args:
            print(f"               Default args: {' '.join(default_args)}")
        print()
    print("Examples:")
    print("  uv run python run.py audit")
    print("  uv run python run.py gt-compare")
    print("  uv run python run.py batch-eval")
    print("  uv run python run.py leaderboard --gt-source sf_planning")
    print("  uv run python run.py smoke --place \"Visitacion Valley\" --model gpt-4o-mini")
    print("\nOther commands:")
    print("  compact-db     Flush WAL and compact eval.duckdb before committing to git.")
    print("                 Only needed after sessions with many deletes/rewrites.")
    print("\nTo launch the dashboard:")
    print("  uv run streamlit run app.py")


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in {"-h", "--help"}:
        _print_help()
        sys.exit(0)

    step_name = args[0]
    step_args = args[1:]

    if step_name == "compact-db":
        _compact_db()
        sys.exit(0)

    if step_name not in STEPS:
        print(f"Error: unknown step '{step_name}'.", file=sys.stderr)
        print(f"Known steps: {', '.join(STEPS)}", file=sys.stderr)
        sys.exit(1)

    info = STEPS[step_name]
    script = SCRIPTS_DIR / info["script"]
    default_args: list[str] = list(info.get("default_args", []))
    effective_args = step_args if step_args else default_args

    cmd = [sys.executable, str(script)] + effective_args
    print(f"[run.py] → running: {' '.join(cmd)}\n", flush=True)
    result = subprocess.run(cmd, cwd=str(Path(__file__).parent))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
