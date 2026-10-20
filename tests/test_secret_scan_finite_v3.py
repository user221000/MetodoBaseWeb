"""Real anchored additions remain finite even when adjacent data looks alike."""
import hashlib
from pathlib import Path

import pytest

from scripts import reviewed_scan_locations as review

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "docs/implementation/20261018-evolution/evidence/"
POINTS = [
    ("google-link-ui/invariants.json", 3),
    ("security-gitleaks-triage-independent-20261019/additional-classified-locations.STRUCTURAL.json", 423),
    ("security-gitleaks-triage-independent-20261019/attempt-initial/source-before.json", 497),
]


@pytest.mark.parametrize("relative,number", POINTS)
@pytest.mark.parametrize("mutation", [None, "whole_file", "adjacent", "copied_path", "other_rule"])
def test_actual_v3_additions_have_no_shape_or_prefix_authority(tmp_path, relative, number, mutation):
    digest = lambda raw: hashlib.sha256(raw).hexdigest()
    name = PREFIX + relative
    original = (ROOT/name).read_bytes()
    target = tmp_path/name
    target.parent.mkdir(parents=True)
    target.write_bytes(original)
    config = (ROOT/".gitleaks.toml").read_bytes()
    (tmp_path/".gitleaks.toml").write_bytes(config)
    data = tmp_path/review._REVIEW_DATA_PATH
    data.parent.mkdir(parents=True)
    data.write_bytes((ROOT/review._REVIEW_DATA_PATH).read_bytes())
    hashes = {name:digest(original), ".gitleaks.toml":digest(config)}
    item = {"StartLine":number, "EndLine":number, "RuleID":"generic-api-key",
            "Match":"untrusted scanner data", "Secret":"untrusted scanner data"}
    if mutation == "whole_file":
        target.write_bytes(original+b" ")
        hashes[name] = digest(target.read_bytes())
    elif mutation == "adjacent":
        target.write_bytes(original+b'\n{"api_key":"synthetic unreviewed credential"}\n')
        hashes[name] = digest(target.read_bytes())
    elif mutation == "copied_path":
        name = PREFIX+"unreviewed-copy.json"
        (tmp_path/name).write_bytes(original)
        hashes[name] = digest(original)
    elif mutation == "other_rule":
        item["RuleID"] = "unreviewed-rule"
    result = review.load_reviewed_locations(tmp_path, hashes, "8.30.1").classify(item, name)
    if mutation is None:
        assert result is not None
        assert result["file"] == name and result["line"] == number
        assert result["file_sha256"] == digest(original)
        assert not {"Match", "Secret", "Line"} & result.keys()
    else:
        assert result is None
