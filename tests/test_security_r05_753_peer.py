"""Independent finite proposal anchors and Git checksum witnesses; no new scan."""
import hashlib
import json
import subprocess
import zipfile
from functools import cache, lru_cache
from pathlib import Path

import pytest

from scripts import reviewed_scan_locations as review

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "8d6b18521c719ff789ebd32c493457b6810b2b48"
PROPOSAL = "docs/implementation/20261018-evolution/evidence/security-r05-753-independent-20261020/finite-proposal.zip"
DIGEST = "8bd7d163b5b8cd0fb2971d55c138daacc5603582ceaad5e5a8c4d6904922a15b"


def sha(value):
    return hashlib.sha256(value).hexdigest()


@lru_cache(maxsize=1)
def proposal():
    raw = (ROOT / PROPOSAL).read_bytes()
    assert sha(raw) == DIGEST
    with zipfile.ZipFile(ROOT / PROPOSAL) as archive:
        assert archive.namelist() == ["proposal.json", "producer.executed.RAW.py"]
        return json.loads(archive.read("proposal.json"))


@cache
def git(commit, name):
    return subprocess.check_output(["git", "--no-replace-objects", "show", commit + ":" + name], cwd=ROOT)


def physical(name):
    data = git(SOURCE, name)
    frame = next(row for row in proposal()["physical_file_frames"] if row["file"] == name)
    if frame["framing"] != "Git exact":
        assert "CRLF" in frame["framing"] and b"\r" not in data
        data = data.replace(b"\n", b"\r\n")
    assert sha(data) == frame["source_sha256"]
    return data


def prepared(tmp_path, names):
    records = {row["path"]: row for row in proposal()["files"] if row["path"] in names}
    hashes = {}
    mapped = {}
    for name, row in records.items():
        content = physical(name)
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        hashes[name] = sha(content)
        mapped[name] = {"source_digest": row["source_digest"], "scanner_digest": row["scanner_digest"],
                        "lines": {(pin["number"], rule): pin["digest"] for pin in row["lines"] for rule in pin["rules"]}}
    return hashes, mapped


def test_all753_proposed_physical_anchors_ignore_untrusted_scanner_payload(tmp_path):
    data = proposal()
    hashes, mapped = prepared(tmp_path, [row["path"] for row in data["files"]])
    # Exercise the unchanged physical anchor class directly. This does not load
    # the proposed dataset or claim the live v4 loader classified these rows.
    registry = review.ReviewedLocations(tmp_path, hashes, mapped)
    count = 0
    for record in data["files"]:
        for pin in record["lines"]:
            for rule in pin["rules"]:
                item = {"RuleID": rule, "StartLine": pin["number"], "EndLine": pin["number"],
                        "File": "untrusted-path", "Secret": object(), "Match": {"false": True}, "Line": None}
                result = registry.classify(item, record["path"])
                assert result is not None
                assert {k: result[k] for k in ["file", "line", "rule", "file_sha256", "physical_line_sha256"]} == {
                    "file": record["path"], "line": pin["number"], "rule": rule,
                    "file_sha256": record["source_digest"], "physical_line_sha256": pin["digest"]}
                count += 1
    assert count == 753


def test_every750_checksum_and_three_literals_have_exact_named_git_witnesses():
    checksums = literals = 0
    for row in proposal()["witnesses"]:
        blob = physical(row["file"])
        line = blob.split(b"\n")[row["line"] - 1]
        assert sha(blob) == row["file_sha256"] and sha(line) == row["physical_line_sha256"]
        witness = row["witness"]
        if row["kind"] == "recomputed_named_source_SHA256":
            parsed = json.loads(blob)
            for part in row["json_pointer"].split("/")[1:]:
                parsed = parsed[part.replace("~1", "/").replace("~0", "~")]
            source = git(witness["git_commit"], row["logical_source"])
            assert sha(source) == witness["git_blob_sha256"]
            if witness["framing"] != "Git exact":
                assert witness["framing"] == "Git LF to CRLF" and b"\r" not in source
                source = source.replace(b"\n", b"\r\n")
            assert sha(source) == witness["raw_sha256"] == row["checksum_sha256"] == parsed
            checksums += 1
        else:
            assert row["kind"] == "exact_VM_namespace_identity_assertion"
            assert row["line"] == 32 and row["rule"] == "generic-api-key"
            assert sha(git(witness["git_commit"], row["file"])) == witness["git_blob_sha256"]
            assert witness["node_syntax_check_exit"] == 0
            assert b"vm.runInContext" in line and b"Api.notifications36" in line
            literals += 1
    assert (checksums, literals) == (750, 3)


def test_proposal_is_disjoint_and_preserves_the_complete_v4_dataset_and_config():
    data = proposal()
    raw = (ROOT / "scripts/data/reviewed_scan_locations_v4.zip").read_bytes()
    assert sha(raw) == data["prior_registry_sha256"]
    with zipfile.ZipFile(ROOT / "scripts/data/reviewed_scan_locations_v4.zip") as archive:
        old = json.loads(archive.read("reviewed-locations.json"))
    assert len(old["files"]) == 877
    assert sum(len(p["rules"]) for row in old["files"] for p in row["lines"]) == 56285
    assert not {row["path"] for row in old["files"]} & {row["path"] for row in data["files"]}
    assert len(data["files"]) == 20 and sha((ROOT / ".gitleaks.toml").read_bytes()) == data["config_digest"] == old["config_digest"]


POINTS = [
    ("current_checksum", next(index for index, row in enumerate(proposal()["witnesses"])
                              if row["kind"] == "recomputed_named_source_SHA256" and row["witness"]["git_commit"] == SOURCE)),
    ("historical_checksum", next(index for index, row in enumerate(proposal()["witnesses"])
                                 if row["kind"] == "recomputed_named_source_SHA256" and row["witness"]["git_commit"] != SOURCE)),
    ("literal", next(index for index, row in enumerate(proposal()["witnesses"])
                     if row["kind"] == "exact_VM_namespace_identity_assertion")),
]


@pytest.mark.parametrize("category,point", POINTS)
@pytest.mark.parametrize("fault", ["missing_inventory", "false_inventory", "adjacent_byte", "physical_byte", "false_rule", "boolean_line", "wrong_path"])
def test_three_actual_categories_reject_each_independent_anchor_fault(tmp_path, category, point, fault):
    selected = proposal()["witnesses"][point]
    if category == "literal":
        assert selected["kind"] == "exact_VM_namespace_identity_assertion"
    else:
        assert selected["kind"] == "recomputed_named_source_SHA256"
        assert (selected["witness"]["git_commit"] == SOURCE) is (category == "current_checksum")
    name = selected["file"]
    hashes, mapped = prepared(tmp_path, [name])
    item = {"RuleID": selected["rule"], "StartLine": selected["line"], "EndLine": selected["line"],
            "Secret": selected["file_sha256"], "Match": "convincing reviewed data", "Line": "forged"}
    if fault == "missing_inventory":
        del hashes[name]
    elif fault == "false_inventory":
        hashes[name] = "0" * 64
    elif fault == "adjacent_byte":
        (tmp_path / name).write_bytes(physical(name) + b" ")
    elif fault == "physical_byte":
        parts = physical(name).split(b"\n")
        parts[selected["line"] - 1] += b" "
        (tmp_path / name).write_bytes(b"\n".join(parts))
    elif fault == "false_rule":
        item["RuleID"] = "unreviewed-rule"
    elif fault == "boolean_line":
        item["StartLine"] = True
    else:
        name = "unreviewed/source.json"
    registry = review.ReviewedLocations(tmp_path, hashes, mapped)
    assert registry.classify(item, name) is None
