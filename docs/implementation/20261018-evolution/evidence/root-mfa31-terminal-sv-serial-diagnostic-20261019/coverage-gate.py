"""Enforce risk-based line/branch coverage for the new nutrition contracts."""
import json
from pathlib import Path
import sys

GATES = {"core/nutrition_validation.py": (95, 90),
         "core/food_catalog.py": (95, 90),
         "web/profile_schemas.py": (95, 90)}


def main(path):
    """Fail on missing modules/branch data as well as below-threshold coverage."""
    files = {name.replace("\\", "/"): value for name, value in json.loads(Path(path).read_text(encoding="utf-8"))["files"].items()}
    failed = False
    for module, (lines_floor, branches_floor) in GATES.items():
        if module not in files:
            print(f"Missing critical coverage module: {module}")
            failed = True
            continue
        summary = files[module]["summary"]
        lines = 100 * summary["covered_lines"] / summary["num_statements"]
        branches = 100 * summary.get("covered_branches", 0) / summary.get("num_branches", 1)
        print(f"{module}: lines {lines:.2f}% >= {lines_floor}%; branches {branches:.2f}% >= {branches_floor}%")
        failed |= lines < lines_floor or branches < branches_floor or "num_branches" not in summary
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
