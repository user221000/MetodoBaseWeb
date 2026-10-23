"""Five actual current metadata checksums, preserving the full V7 registry."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from tests.ci_web37.r05_v8_transport import original_source, review

ROOT = Path(__file__).resolve().parents[1]
OLD = "scripts/data/reviewed_scan_locations_v7.zip"
CURRENT = "scripts/data/reviewed_scan_locations_v8.zip"
OLD_DIGEST = "907501744833ca5c1ec1e8acaeff58659311f93ab56d7d8b184814dcf14ccb06"
CURRENT_DIGEST = "a6b0027ddbf2d651d26dd98d611e04729cefaf7508f0ff8a1ed5ac8c2d76d47f"
PROPOSAL = "tests/fixtures/r05-current5-proposal.zip"
PROPOSAL_DIGEST = "94db66c28ac5f235e2d3520286d570dc8411542f364ea0e1c48a3f37d6ccbcf0"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def document(name, expected, member):
    raw = (ROOT / name).read_bytes()
    assert digest(raw) == expected
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert archive.namelist() == [member]
        return json.loads(archive.read(member))


def proposal():
    return document(PROPOSAL, PROPOSAL_DIGEST, "proposal.json")


def test_v8_union_preserves904_original_records_and57262_pins_exactly():
    old = document(OLD, OLD_DIGEST, "reviewed-locations.json")
    new = document(CURRENT, CURRENT_DIGEST, "reviewed-locations.json")
    assert len(old["files"]) == 904 and len(new["files"]) == 907
    assert new["files"][:904] == old["files"]
    assert new["files"][904:] == proposal()["files"]
    assert {key: value for key, value in old.items() if key != "files"} == {
        key: value for key, value in new.items() if key != "files"}
    assert sum(len(line["rules"]) for row in old["files"] for line in row["lines"]) == 57262
    assert sum(len(line["rules"]) for row in new["files"] for line in row["lines"]) == 57267
    assert review._REVIEW_DATA_PATH == CURRENT and review._REVIEW_DATA_DIGEST == CURRENT_DIGEST


def test_only_three_loader_literals_change_from_the_authenticated_original_v7():
    original = (ROOT / "tests/fixtures/r05-v7-reader-original.py.RAW").read_bytes()
    assert digest(original) == "727c0a5e305a6d012523929ff86e59954488d32464ee44bda7bc8685e5a8add4"
    inverse = original_source()
    for before, after in [(CURRENT, OLD), (CURRENT_DIGEST, OLD_DIGEST), ("registry v8", "registry v7")]:
        assert inverse.count(before.encode()) == 1
        inverse = inverse.replace(before.encode(), after.encode())
    assert inverse == original


def snapshot(tmp_path):
    for name in [CURRENT, ".gitleaks.toml", *[row["path"] for row in proposal()["files"]]]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    return {path.relative_to(tmp_path).as_posix(): digest(path.read_bytes())
            for path in tmp_path.rglob("*") if path.is_file()}


@pytest.mark.parametrize("index", range(5))
def test_five_actual_json_checksums_are_bound_to_their_source_and_physical_line(tmp_path, index):
    row = proposal()["witnesses"][index]
    raw = (ROOT / row["file"]).read_bytes()
    assert digest(raw) == row["file_sha256"]
    assert digest(raw.split(b"\n")[row["line"] - 1]) == row["physical_line_sha256"]
    selected = json.loads(raw)
    for part in row["json_pointer"][1:].split("/"):
        selected = selected[part.replace("~1", "/").replace("~0", "~")]
    assert selected == row["checksum_sha256"] == row["witness"]["retained_actual_RAW_sha256"]
    hashes = snapshot(tmp_path)
    finding = {"StartLine": row["line"], "EndLine": row["line"], "RuleID": row["rule"],
               "Match": object(), "Secret": object(), "Line": False}
    actual = review.load_reviewed_locations(tmp_path, hashes, "8.30.1").classify(finding, row["file"])
    assert actual == {key: row[key] for key in ("file", "line", "rule", "file_sha256", "physical_line_sha256")} | {
        "reason": "finite independently reviewed non-credential evidence; registry v8"}


@pytest.mark.parametrize("index", range(5))
@pytest.mark.parametrize("fault", ["path", "unregistered-line", "rule", "file-byte", "inventory"])
def test_each_new_location_rejects_unreviewed_changes(tmp_path, index, fault):
    row = proposal()["witnesses"][index]
    hashes = snapshot(tmp_path)
    name = row["file"]
    finding = {"StartLine": row["line"], "EndLine": row["line"], "RuleID": row["rule"]}
    if fault == "path":
        name += ".unreviewed"
    elif fault == "unregistered-line":
        finding.update(StartLine=1, EndLine=1)
    elif fault == "rule":
        finding["RuleID"] = "unreviewed-new-rule"
    elif fault == "file-byte":
        target = tmp_path / name
        target.write_bytes(target.read_bytes() + b" ")
    else:
        hashes[name] = "0" * 64
    assert review.load_reviewed_locations(tmp_path, hashes, "8.30.1").classify(finding, name) is None


@pytest.mark.parametrize("fault", ["archive", "config", "version"])
def test_current_v8_registry_configuration_and_scanner_remain_exact(tmp_path, fault):
    hashes = snapshot(tmp_path)
    version = "8.30.1"
    if fault in {"archive", "config"}:
        target = tmp_path / (CURRENT if fault == "archive" else ".gitleaks.toml")
        target.write_bytes(target.read_bytes() + b" ")
    else:
        version = "8.30.2"
    with pytest.raises(RuntimeError):
        review.load_reviewed_locations(tmp_path, hashes, version)
