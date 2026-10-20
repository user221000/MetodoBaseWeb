"""Actual candidate V6 union and anchored new locations; no full secret scan."""
import ast
import hashlib
import io
import json
import subprocess
import zipfile
from collections import Counter
from functools import cache
from pathlib import Path

import pytest

from scripts import reviewed_scan_locations as review

ROOT = Path(__file__).resolve().parents[1]
BASE = "ab8bd90d65bde1a502f50c8ef0edd1d3dd417e1c"
SCAN = "ca09d2f803bcd1e2b977db7b708fa6559c9b5617"
PROPOSAL = "docs/implementation/20261018-evolution/evidence/root-r05-223-proposal-20261020/finite-proposal.zip"
V5 = "scripts/data/reviewed_scan_locations_v5.zip"
V6 = "scripts/data/reviewed_scan_locations_v6.zip"
V5_SHA = "5b847d2d632721d043199ec5658b48e96dc6796712b4692e1a79b68fa3b932f6"
V6_SHA = "6b10c621dca9e76b3bee4867caae5a33b70f2e81f3700807ebb9f9fb7731f092"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")


@cache
def git(commit, path):
    return subprocess.check_output(["git", "--no-replace-objects", "show", commit + ":" + path], cwd=ROOT)


@cache
def data(path):
    with zipfile.ZipFile(ROOT / path) as archive:
        assert archive.namelist() == ["reviewed-locations.json"]
        return json.loads(archive.read("reviewed-locations.json"))


@cache
def proposal():
    assert sha((ROOT / PROPOSAL).read_bytes()) == "0ee479cf5c4a886f706f7183c40c6c1126c6e8012276dfd5bf5e5728c3718909"
    with zipfile.ZipFile(ROOT / PROPOSAL) as archive:
        return json.loads(archive.read("proposal.json"))


def snapshot(tmp_path, names=None):
    hashes = {}
    for row in proposal()["files"]:
        name = row["path"]
        if names is not None and name not in names:
            continue
        raw = git(SCAN, name)
        assert sha(raw) == row["source_digest"] == row["scanner_digest"]
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        hashes[name] = sha(raw)
    config = (ROOT / ".gitleaks.toml").read_bytes()
    (tmp_path / ".gitleaks.toml").write_bytes(config)
    hashes[".gitleaks.toml"] = sha(config)
    target = tmp_path / V6
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((ROOT / V6).read_bytes())
    return hashes


def finding(row):
    return {"RuleID": row["rule"], "StartLine": row["line"], "EndLine": row["line"],
            "File": "untrusted/path", "Secret": object(), "Match": {"forged": True}, "Line": None}


def test_v6_is_exact_disjoint_six_file223_union_preserving897_v5_records():
    old, current, added = data(V5), data(V6), proposal()
    assert sha((ROOT / V5).read_bytes()) == V5_SHA and sha((ROOT / V6).read_bytes()) == V6_SHA
    assert review._REVIEW_DATA_PATH == V6 and review._REVIEW_DATA_DIGEST == V6_SHA
    assert len(old["files"]) == 897 and len(current["files"]) == 903 and len(added["files"]) == 6
    assert [canonical(row) for row in current["files"][:897]] == [canonical(row) for row in old["files"]]
    assert current["files"][897:] == added["files"]
    assert not {r["path"] for r in old["files"]} & {r["path"] for r in added["files"]}
    assert len({r["path"] for r in current["files"]}) == 903
    assert sum(len(p["rules"]) for r in old["files"] for p in r["lines"]) == 57038
    assert sum(len(p["rules"]) for r in current["files"] for p in r["lines"]) == 57261
    pins = Counter((r["path"], p["number"], rule, r["source_digest"], p["digest"])
                   for r in added["files"] for p in r["lines"] for rule in p["rules"])
    witnesses = Counter((r["file"], r["line"], r["rule"], r["file_sha256"], r["physical_line_sha256"])
                        for r in added["witnesses"])
    assert pins == witnesses and len(pins) == 223 and all(count == 1 for count in pins.values())
    assert Counter(r["rule"] for r in added["witnesses"]) == {
        "generic-api-key": 206, "sentry-access-token": 13, "sumologic-access-token": 4}
    config = sha((ROOT / ".gitleaks.toml").read_bytes())
    assert current["schema"] == old["schema"] == 1 and current["version"] == old["version"] == "8.30.1"
    assert current["config_digest"] == old["config_digest"] == added["config_digest"] == config


def test_loader_has_only_three_literal_changes_with_complete_inverse_and_identical_algorithm():
    path = "scripts/reviewed_scan_locations.py"
    old, current = git(BASE, path), git("HEAD", path)
    changes = {V6.encode(): V5.encode(), V6_SHA.encode(): V5_SHA.encode(),
               b"finite independently reviewed non-credential evidence; registry v6":
               b"finite independently reviewed non-credential evidence; registry v5"}
    restored = current
    for before, after in changes.items():
        assert restored.count(before) == 1
        restored = restored.replace(before, after)
    assert restored == old
    assert ast.dump(ast.parse(restored), include_attributes=False) == ast.dump(ast.parse(old), include_attributes=False)
    for name in [".gitleaks.toml", "scripts/scan_secrets.py", *[f"scripts/data/reviewed_scan_locations_v{number}.zip" for number in range(1, 6)]]:
        assert git("HEAD", name) == git(BASE, name)
        if name.endswith(".py"):
            assert ast.dump(ast.parse((ROOT / name).read_bytes())) == ast.dump(ast.parse(git(BASE, name)))
        else:
            assert (ROOT / name).read_bytes() == git(BASE, name)


def test_historical_v5_composition_changes_only_one_reader_argument_without_assert_changes():
    path = "tests/test_secret_scan_finite_v5.py"
    before, after = git(BASE, path), git("HEAD", path)
    old = b"current = dataset(review._REVIEW_DATA_PATH)"
    new = b'current = dataset("scripts/data/reviewed_scan_locations_v5.zip")'
    assert after.count(new) == before.count(old) == 1
    assert after.replace(new, old) == before


def test_all223_new_locations_are_classified_by_the_actual_byte_anchored_v6_loader(tmp_path):
    hashes = snapshot(tmp_path)
    registry = review.load_reviewed_locations(tmp_path, hashes, "8.30.1")
    results = []
    for row in proposal()["witnesses"]:
        result = registry.classify(finding(row), row["file"])
        assert result == {"file": row["file"], "line": row["line"], "rule": row["rule"],
                          "file_sha256": row["file_sha256"], "physical_line_sha256": row["physical_line_sha256"],
                          "reason": "finite independently reviewed non-credential evidence; registry v6"}
        results.append((result["file"], result["line"], result["rule"]))
    assert len(results) == len(set(results)) == 223


POINTS = [
    ("generic-source", next(i for i, r in enumerate(proposal()["witnesses"]) if r["rule"] == "generic-api-key")),
    ("sentry-source", next(i for i, r in enumerate(proposal()["witnesses"]) if r["rule"] == "sentry-access-token")),
    ("sumologic-source", next(i for i, r in enumerate(proposal()["witnesses"]) if r["rule"] == "sumologic-access-token")),
    ("exact-container-source", next(i for i, r in enumerate(proposal()["witnesses"]) if r["witness"]["git_commit"] == "34707350afcc810e546cbb668dd63089ec7982ae")),
    ("lock-block", next(i for i, r in enumerate(proposal()["witnesses"]) if r["kind"] == "recomputed_named_lock_block_SHA256")),
]


@pytest.mark.parametrize("category,index", POINTS)
@pytest.mark.parametrize("fault", ["neighbor-byte", "physical-line", "wrong-rule", "wrong-path", "inventory", "boolean-line", "multiline", "CRLF-added"])
def test_each_actual_rule_and_source_or_block_boundary_fails_closed(tmp_path, category, index, fault):
    row = proposal()["witnesses"][index]
    assert category
    name = row["file"]
    hashes = snapshot(tmp_path, {name})
    item = finding(row)
    path = tmp_path / name
    if fault == "neighbor-byte":
        path.write_bytes(path.read_bytes() + b" ")
    elif fault == "physical-line":
        lines = path.read_bytes().split(b"\n")
        lines[row["line"] - 1] += b" "
        path.write_bytes(b"\n".join(lines))
    elif fault == "wrong-rule":
        item["RuleID"] = "unreviewed-rule"
    elif fault == "wrong-path":
        name += ".unreviewed"
    elif fault == "inventory":
        hashes[name] = "0" * 64
    elif fault == "boolean-line":
        item["StartLine"] = True
    elif fault == "multiline":
        item["EndLine"] += 1
    else:
        raw = path.read_bytes()
        assert b"\r" not in raw
        path.write_bytes(raw.replace(b"\n", b"\r\n"))
        hashes[name] = sha(path.read_bytes())
    assert review.load_reviewed_locations(tmp_path, hashes, "8.30.1").classify(item, name) is None


@pytest.mark.parametrize("fault", ["archive-byte", "config-byte", "version", "repacked-identical-payload"])
def test_active_v6_requires_exact_zip_config_and_scanner_version(tmp_path, fault):
    hashes = snapshot(tmp_path, {proposal()["witnesses"][0]["file"]})
    version = "8.30.1"
    if fault == "archive-byte":
        target = tmp_path / V6
        target.write_bytes(target.read_bytes() + b" ")
    elif fault == "config-byte":
        (tmp_path / ".gitleaks.toml").write_bytes(b"[extend]\nuseDefault=true\n")
    elif fault == "version":
        version = "8.30.2"
    else:
        with zipfile.ZipFile(ROOT / V6) as archive:
            raw = archive.read("reviewed-locations.json")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("reviewed-locations.json", raw)
        assert sha(buffer.getvalue()) != V6_SHA
        (tmp_path / V6).write_bytes(buffer.getvalue())
    with pytest.raises(RuntimeError, match="registry is invalid; output withheld"):
        review.load_reviewed_locations(tmp_path, hashes, version)
