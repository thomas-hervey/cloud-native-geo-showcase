# Eval Pipeline Scripts

This directory contains the underlying python scripts used to drive the evaluation framework. 

Use the top-level `run.py` dispatcher to discover and run these scripts:
```bash
uv run python ../run.py --help
```

## Pipeline Steps
1. **Audit**: `audit_gt_coverage.py` - Audits ground truth sources for missing polygons.
2. **GT Compare**: `run_gt_comparison.py` - Pre-computes GT-vs-GT agreement metrics.
3. **Smoke Test**: `run_eval.py` - Evaluates a single LLM against a single place.
4. **Batch Eval**: `run_batch_eval.py` - Main runner predicting bounding boxes for all places across models and GT sources.
5. **Leaderboard**: `leaderboard.py` - Outputs model rankings based on composite score.
6. **Analysis**: `run_analysis.py` - Outputs place-by-source correlation matrices.
7. **Prompt Experiments**: `run_prompt_experiment.py` - CLI for running alternative prompt variations.
