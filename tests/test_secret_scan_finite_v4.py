"""Finite new provenance classes never authorize adjacent or copied content."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from scripts import reviewed_scan_locations as review

ROOT = Path(__file__).resolve().parents[1]
POINTS = [('tests/test_client_link_models.py', 23, 'generic-api-key'), ('docs/implementation/20261018-evolution/evidence/history-independent-20261019/browser57-own3/server.log', 1, 'generic-api-key'), ('docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_SNAPSHOT.json', 173, 'generic-api-key'), ('docs/implementation/20261018-evolution/evidence/qa-ci33-main-r05v2-composition-20261020/verifier-before.raw.txt', 73, 'generic-api-key'), ('docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_CI_MAP.json', 9641, 'generic-api-key'), ('docs/implementation/20261018-evolution/evidence/ux/team-freeze-source.json', 11, 'generic-api-key'), ('docs/implementation/20261018-evolution/evidence/backend-r12-api-cas-final-source.json', 16, 'generic-api-key')]


def source_bytes(name):
    if name == "docs/implementation/20261018-evolution/evidence/ux/team-freeze-source.json":
        with zipfile.ZipFile(ROOT/"tests/data/r05_v4_historical_team_manifest.zip") as archive:
            assert archive.namelist() == ["historical-team-freeze-source.RAW.json"]
            raw = archive.read("historical-team-freeze-source.RAW.json")
        assert hashlib.sha256(raw).hexdigest() == "6d09df84a1e84268b824d9f39f346b9a61f622647db6478b4839442bee964947"
        return raw
    return (ROOT/name).read_bytes()


def registry(name):
    with zipfile.ZipFile(io.BytesIO((ROOT/name).read_bytes())) as archive:
        return json.loads(archive.read("reviewed-locations.json"))


@pytest.mark.parametrize("name,number,rule", POINTS)
@pytest.mark.parametrize("mutation", [None, "adjacent_payload", "copied_path", "other_rule", "wrong_source_digest"])
def test_new_v4_categories_are_exact_file_and_physical_rule_pins(tmp_path, name, number, rule, mutation):
    original = source_bytes(name)
    target = tmp_path/name
    target.parent.mkdir(parents=True)
    target.write_bytes(original.decode("utf-8-sig").encode())
    config = (ROOT/".gitleaks.toml").read_bytes()
    (tmp_path/".gitleaks.toml").write_bytes(config)
    data = tmp_path/review._REVIEW_DATA_PATH
    data.parent.mkdir(parents=True)
    data.write_bytes((ROOT/review._REVIEW_DATA_PATH).read_bytes())
    hashes = {name: hashlib.sha256(original).hexdigest(), ".gitleaks.toml": hashlib.sha256(config).hexdigest()}
    item = {"StartLine": number, "EndLine": number, "RuleID": rule,
            "Match": "untrusted scanner field", "Secret": "untrusted scanner field"}
    if mutation == "adjacent_payload":
        target.write_bytes(target.read_bytes()+b'\n{"api_key":"synthetic-unreviewed-value"}\n')
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    elif mutation == "copied_path":
        name += ".unreviewed"
        (tmp_path/name).write_bytes(target.read_bytes())
        hashes[name] = hashes[target.relative_to(tmp_path).as_posix()]
    elif mutation == "other_rule":
        item["RuleID"] = "unreviewed-rule"
    elif mutation == "wrong_source_digest":
        hashes[name] = "0"*64
    value = review.load_reviewed_locations(tmp_path, hashes, "8.30.1").classify(item, name)
    if mutation is None:
        assert value is not None and (value["file"], value["line"], value["rule"]) == (name, number, rule)
        assert not {"Match", "Secret", "Line"} & value.keys()
    else:
        assert value is None


def test_v4_composition_preserves_641_records_and_85_replaced_versions_in_v3():
    old_raw = (ROOT/"scripts/data/reviewed_scan_locations_v3.zip").read_bytes()
    assert hashlib.sha256(old_raw).hexdigest() == "000a1c7afbc1847e7489459bef68b20bbaeaa387e227abe05c7b2073383fbaa4"
    old = {row["path"]: row for row in registry("scripts/data/reviewed_scan_locations_v3.zip")["files"]}
    current = {row["path"]: row for row in registry(review._REVIEW_DATA_PATH)["files"]}
    retained = {name for name in old if current[name] == old[name]}
    replaced = set(old)-retained
    assert len(retained) == 641 and len(replaced) == 85 and len(set(current)-set(old)) == 151
    assert all(current[name]["source_digest"] != old[name]["source_digest"] and
               current[name]["scanner_digest"] != old[name]["scanner_digest"] for name in replaced)


def test_v4_has_only_unique_finite_locations_and_the_same_scanner_config():
    data = registry(review._REVIEW_DATA_PATH)
    assert data["schema"] == 1 and data["version"] == "8.30.1"
    assert data["config_digest"] == hashlib.sha256((ROOT/".gitleaks.toml").read_bytes()).hexdigest()
    assert len(data["files"]) == len({row["path"] for row in data["files"]}) == 877
    pins = [(row["path"], line["number"], rule) for row in data["files"] for line in row["lines"] for rule in line["rules"]]
    assert len(pins) == len(set(pins)) == 56285
