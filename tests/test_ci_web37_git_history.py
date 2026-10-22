"""Adversarial finite Git transport checks; no Git command or network."""
import copy
import hashlib
import io
import zipfile

import pytest

from tests.ci_web37 import git_history


@pytest.fixture(scope="module")
def proof():
    return git_history.load()


def repack(proof, mutation):
    raw = (git_history.FIXTURES / "r05-history-objects.zip").read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = [(row.filename, archive.read(row)) for row in archive.infolist()]
    entries = mutation(entries)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        for name, value in entries:
            archive.writestr(name, value)
    raw = buffer.getvalue()
    manifest = copy.deepcopy(proof.manifest)
    manifest["archive_sha256"] = hashlib.sha256(raw).hexdigest()
    return raw, manifest


def test_all_original_objects_and_routes_are_reached_and_phase_counts_are_exact(proof):
    assert len(proof.objects) == 207 and len(proof.routes) == 132
    assert proof.used == proof.objects.keys()
    assert {name: row["required_cases"] for name, row in proof.manifest["phases"].items()} == {
        "frozen-v5-peer60": 60, "frozen-v6-author48": 48, "current-750-transport24": 24}


@pytest.mark.parametrize("fault", ["payload", "kind", "length", "missing", "duplicate", "path"])
def test_object_identity_type_length_inventory_and_member_paths_fail_closed(proof, fault):
    def mutation(entries):
        name, frame = entries[0]
        if fault == "payload":
            entries[0] = (name, frame + b" ")
        elif fault == "kind":
            entries[0] = (name, b"tag" + frame[frame.index(b" "):])
        elif fault == "length":
            head, payload = frame.split(b"\0", 1)
            kind, size = head.split(b" ", 1)
            entries[0] = (name, kind + b" 0" + size + b"\0" + payload)
        elif fault == "missing":
            entries.pop(0)
        elif fault == "duplicate":
            entries.append(entries[0])
        else:
            entries[0] = ("objects/../" + name.split("/")[-1], frame)
        return entries

    raw, manifest = repack(proof, mutation)
    with pytest.raises(ValueError):
        git_history.HistoryProof(raw, manifest)


def test_valid_but_undeclared_original_object_is_rejected(proof):
    payload = b"unreachable original object control\n"
    oid = git_history.object_id("blob", payload)
    raw, manifest = repack(proof, lambda rows: [*rows, ("objects/" + oid,
        b"blob " + str(len(payload)).encode() + b"\0" + payload)])
    manifest["objects"] += 1
    with pytest.raises(ValueError, match="unreachable"):
        git_history.HistoryProof(raw, manifest)


@pytest.mark.parametrize("fault", ["undeclared-root", "false-parent", "arbitrary-alias"])
def test_aliases_cannot_invent_a_HEAD_or_parent_authority(proof, fault):
    manifest = copy.deepcopy(proof.manifest)
    aliases = manifest["phases"]["frozen-v6-author48"]["aliases"]
    if fault == "undeclared-root":
        aliases["HEAD"] = "0" * 40
    elif fault == "false-parent":
        aliases["287a51865a9d346f7e45bb09d3a2e13a4922c636^"] = aliases["HEAD"]
    else:
        aliases["branch"] = aliases["HEAD"]
    with pytest.raises(ValueError):
        git_history.HistoryProof((git_history.FIXTURES / "r05-history-objects.zip").read_bytes(), manifest)


def test_a_phase_cannot_read_another_phase_HEAD_or_an_undeclared_path(proof):
    with pytest.raises(ValueError, match="another phase"):
        proof.git("frozen-v5-peer60", "HEAD", "scripts/reviewed_scan_locations.py")
    with pytest.raises(ValueError, match="finite inventory"):
        proof.blob("287a51865a9d346f7e45bb09d3a2e13a4922c636", "unreviewed/path")


@pytest.mark.parametrize("path", ["/absolute", "../parent", "a//b", "a/./b", "a\\b", "C:/drive"])
def test_materialized_paths_cannot_escape_the_fresh_phase_directory(path):
    with pytest.raises(ValueError, match="relative regular"):
        git_history.safe_path(path)


@pytest.mark.parametrize("fault", ["framing", "digest"])
def test_materialization_fails_on_unreviewed_framing_or_bytes(proof, tmp_path, fault):
    other = copy.copy(proof)
    other.manifest = copy.deepcopy(proof.manifest)
    row = next(iter(other.manifest["phases"]["frozen-v6-author48"]["files"].values()))
    row["framing" if fault == "framing" else "materialized_sha256"] = "unreviewed"
    with pytest.raises(ValueError):
        other.materialize("frozen-v6-author48", tmp_path / "new")
