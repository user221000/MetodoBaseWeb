"""Actual v5 additions retain physical-file boundaries and immutable v4 history."""
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts import reviewed_scan_locations as review

ROOT = Path(__file__).resolve().parents[1]
POINTS = [('docs/implementation/20261018-evolution/evidence/mobile-nav-20261020/source.json', 56, 'generic-api-key'), ('docs/implementation/20261018-evolution/CUENTA_SEGURIDAD37_UI_IMPLEMENTACION.json', 316, 'generic-api-key'), ('docs/implementation/20261018-evolution/evidence/notifications36-bootstrap-20261020/bootstrap-initial-driver.cjs', 32, 'generic-api-key')]


def dataset(name):
    with zipfile.ZipFile(ROOT / name) as z:
        return json.loads(z.read("reviewed-locations.json"))


def test_all_v4_records_remain_exact_and_only_twenty_paths_are_added():
    old = dataset("scripts/data/reviewed_scan_locations_v4.zip")
    current = dataset(review._REVIEW_DATA_PATH)
    before = {r["path"]: r for r in old["files"]}
    after = {r["path"]: r for r in current["files"]}
    assert len(before) == 877 and len(after) == 897
    assert all(after[name] == record for name, record in before.items())
    assert len(set(after) - set(before)) == 20
    assert sum(len(p["rules"]) for r in current["files"] for p in r["lines"]) == 57038
    assert current["config_digest"] == old["config_digest"] == hashlib.sha256((ROOT / ".gitleaks.toml").read_bytes()).hexdigest()


@pytest.mark.parametrize("name,number,rule", POINTS)
@pytest.mark.parametrize("fault", [None, "adjacent_byte", "wrong_path", "wrong_rule", "false_inventory", "boolean_line"])
def test_actual_v5_categories_cannot_authorize_neighboring_or_untrusted_content(tmp_path, name, number, rule, fault):
    raw = (ROOT / name).read_bytes()
    target = tmp_path / name
    target.parent.mkdir(parents=True)
    target.write_bytes(raw)
    config = (ROOT / ".gitleaks.toml").read_bytes()
    (tmp_path / ".gitleaks.toml").write_bytes(config)
    registry_path = tmp_path / review._REVIEW_DATA_PATH
    registry_path.parent.mkdir(parents=True)
    registry_path.write_bytes((ROOT / review._REVIEW_DATA_PATH).read_bytes())
    hashes = {name: hashlib.sha256(raw).hexdigest(), ".gitleaks.toml": hashlib.sha256(config).hexdigest()}
    item = {"StartLine": number, "EndLine": number, "RuleID": rule, "Secret": object(), "Match": None, "Line": "untrusted"}
    if fault == "adjacent_byte":
        target.write_bytes(raw + b" ")
    elif fault == "wrong_path":
        name += ".unreviewed"
    elif fault == "wrong_rule":
        item["RuleID"] = "unreviewed-rule"
    elif fault == "false_inventory":
        hashes[name] = "0" * 64
    elif fault == "boolean_line":
        item["StartLine"] = True
    result = review.load_reviewed_locations(tmp_path, hashes, "8.30.1").classify(item, name)
    assert (result is not None) is (fault is None)
