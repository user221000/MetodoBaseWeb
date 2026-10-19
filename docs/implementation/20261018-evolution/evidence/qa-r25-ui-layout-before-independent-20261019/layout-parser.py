"""Validate independent real-browser mobile readability measurements.

Each page/viewport pair is one criterion. The historical before report must
stay red; after repair all four must be green using the same browser canary.
"""
import argparse
import json
from pathlib import Path


def criteria(report, source_head):
    assert report["source_head"] == source_head
    assert report["pageErrors"] == [] and report["browser_close_returned"] is True
    assert len(report["cases"]) == 4
    assert {(row["page"], row["width"]) for row in report["cases"]} == {
        ("personal", 320), ("personal", 390), ("professional", 320), ("professional", 390),
    }
    results = []
    for row in report["cases"]:
        region = row["region"]
        assert type(row["value"]["fragments"]) is int
        assert row["value"]["text"] == ("71.5 kg" if row["page"] == "personal" else "88.25 kg")
        if row["page"] == "personal":
            assert row["date"] is not None and type(row["date"]["fragments"]) is int
        passed = (
            row["pageOverflow"] is False
            and row["value"]["fragments"] == 1
            and (row["date"] is None or row["date"]["fragments"] == 1)
            and region["tabIndex"] == 0 and region["role"] == "region"
            and isinstance(region["label"], str) and bool(region["label"].strip())
            and region["scrollWidth"] > region["width"]
            and row["keyboardRegionFocused"] is True
            and row["horizontalArrowMoved"] is True
        )
        results.append({"page": row["page"], "width": row["width"], "passed": passed})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--expect", choices=("before-red", "after-green"), required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_bytes())
    results = criteria(report, args.source_head)
    passed = sum(row["passed"] for row in results)
    if args.expect == "before-red":
        assert passed == 0 and report["complete"] is False
    else:
        assert passed == 4 and report["complete"] is True
    print(json.dumps({"source_head": args.source_head, "expect": args.expect,
                      "passed_layout_criteria": passed, "total_layout_criteria": 4, "results": results}))


if __name__ == "__main__":
    main()
