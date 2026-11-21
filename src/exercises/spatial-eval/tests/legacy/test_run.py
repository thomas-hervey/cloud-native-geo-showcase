import subprocess
import sys
from pathlib import Path

SPATIAL_EVAL_DIR = Path(__file__).resolve().parent.parent.parent


def test_run_help():
    """Smoke test: the pipeline runner's --help exits cleanly and lists its steps."""
    result = subprocess.run(
        [sys.executable, "run.py", "--help"],
        cwd=str(SPATIAL_EVAL_DIR),
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "batch-eval" in result.stdout
    assert "smoke" in result.stdout
