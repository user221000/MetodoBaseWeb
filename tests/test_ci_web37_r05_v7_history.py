"""V7 has its own finite original authority, with no Git command at runtime."""
import hashlib
import json

import pytest

from tests.ci_web37 import r05_v7_history

SOURCE = "d568634be21fe0c745d21c110e344f161d3dd4b3"
PHASE = "frozen-v7-author15"


def test_all38_original_frames_and26_paths_are_required_by_the_V7_phase():
    proof = r05_v7_history.load()
    assert len(proof.objects) == 38 and len(proof.routes) == 26
    assert proof.used == proof.objects.keys()
    assert set(proof.manifest["phases"]) == {PHASE}
    row = proof.manifest["phases"][PHASE]
    assert row["required_cases"] == 15 and row["aliases"] == {"HEAD": SOURCE}
    assert row["tests"] == ["tests/test_secret_scan_finite_v7.py"]


def test_the_original_assertion_bytes_and_HEAD_reader_are_exact():
    proof = r05_v7_history.load()
    original = proof.blob(SOURCE, "tests/test_secret_scan_finite_v7.py")
    assert hashlib.sha256(original).hexdigest() == "12540b55f836df7104dc646cdb599b35b52735c937d107cae909d0b386ce75f3"
    reader = proof.git(PHASE, "HEAD", "scripts/reviewed_scan_locations.py")
    assert reader == proof.blob(SOURCE, "scripts/reviewed_scan_locations.py")
    assert b"registry v7" in reader and b"reviewed_scan_locations_v7.zip" in reader


def test_a_materialized_file_does_not_grant_an_additional_Git_read():
    proof = r05_v7_history.load()
    with pytest.raises(ValueError, match="another phase"):
        proof.git(PHASE, "HEAD", "tests/test_secret_scan_finite_v7.py")


@pytest.mark.parametrize("fault", ["manifest-byte", "HEAD-root", "archive-byte"])
def test_changed_manifest_authority_or_archive_is_refused(tmp_path, monkeypatch, fault):
    manifest = (r05_v7_history.FIXTURES / "r05-v7-history.json").read_bytes()
    archive = (r05_v7_history.FIXTURES / "r05-v7-history-objects.zip").read_bytes()
    if fault == "manifest-byte":
        manifest += b" "
    elif fault == "HEAD-root":
        row = json.loads(manifest)
        row["phases"][PHASE]["aliases"]["HEAD"] = "45eba8f1d50efebd7106106f8aa20bfda3c7b440"
        manifest = json.dumps(row).encode()
    else:
        archive += b" "
    (tmp_path / "r05-v7-history.json").write_bytes(manifest)
    (tmp_path / "r05-v7-history-objects.zip").write_bytes(archive)
    monkeypatch.setattr(r05_v7_history, "FIXTURES", tmp_path)
    with pytest.raises(ValueError):
        r05_v7_history.load()
