"""Reuse the frozen assertion runner with only the authenticated V7 capsule."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.ci_web37 import run_r05_history
from tests.ci_web37.r05_v7_history import load


if __name__ == "__main__":
    run_r05_history.load = load
    raise SystemExit(run_r05_history.main())
