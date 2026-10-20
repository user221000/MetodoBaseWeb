"""Reject counterfeit object authorities and unsafe fixture framing offline."""
import hashlib
import io
import warnings
import zipfile

import pytest

from tests.ci_web37 import git_recipe as subject


def members():
    with zipfile.ZipFile(subject.FIXTURE) as archive:
        return {row.filename: archive.read(row) for row in archive.infolist()}


def archive(records):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as result:
        for name, payload in records:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                result.writestr(name, payload)
    return output.getvalue()


def test_original_merkle_authority_is_self_contained_without_git_or_a_repository(monkeypatch):
    import subprocess

    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: pytest.fail("Git transport forbidden"))
    proof = subject.load()
    assert len(proof.objects) == len(proof.used) == 21
    assert len(proof.subtree(subject.BASELINE, "tests/ci_google33")) == 34
    assert hashlib.sha256(proof.blob(subject.NATIVE, "Dockerfile")).hexdigest() == (
        "0d94653622cb859039f5d2be0d67d5a02b82197ab954fe68dcb469ded0f53e94")


@pytest.mark.parametrize("change", [
    "wrong-kind", "noncanonical-length", "wrong-length", "changed-body", "missing-object",
    "duplicate-member", "unreachable-object", "member-traversal", "counterfeit-commit",
])
def test_rehashed_or_reframed_objects_cannot_replace_the_pinned_commit_authority(change):
    records = members()
    proof = subject.load()
    oid = proof.resolve(subject.NATIVE, "Dockerfile", "blob")
    key = "objects/" + oid
    frame = records[key]
    header, _, payload = frame.partition(b"\0")
    if change == "wrong-kind":
        records[key] = frame.replace(b"blob ", b"tree ", 1)
    elif change == "noncanonical-length":
        records[key] = b"blob 0" + str(len(payload)).encode() + b"\0" + payload
    elif change == "wrong-length":
        records[key] = b"blob " + str(len(payload) + 1).encode() + b"\0" + payload
    elif change == "changed-body":
        records[key] = header + b"\0" + bytes([payload[0] ^ 1]) + payload[1:]
    elif change == "missing-object":
        records.pop(key)
    elif change == "unreachable-object":
        extra = b"unreviewed authority"
        records["objects/" + subject.object_id("blob", extra)] = b"blob 20\0" + extra
    elif change == "member-traversal":
        records["../" + key] = records.pop(key)
    elif change == "counterfeit-commit":
        commit = records.pop("objects/" + subject.NATIVE)
        _kind, _, body = commit.partition(b"\0")
        body += b"\nunreviewed commit replacement\n"
        records["objects/" + subject.object_id("commit", body)] = b"commit " + str(len(body)).encode() + b"\0" + body
    values = list(records.items())
    if change == "duplicate-member":
        values.append((key, frame))
    with pytest.raises(ValueError):
        subject.ObjectProof(archive(values)).verify_routes()


@pytest.mark.parametrize("path,kind", [
    ("../Dockerfile", "blob"), ("runtime-source//expat-sec10/source-pins.json", "blob"),
    ("Dockerfile", "tree"), ("runtime-source/expat-sec10/unknown.py", "blob"),
])
def test_valid_objects_do_not_authorize_another_path_or_leaf_kind(path, kind):
    with pytest.raises(ValueError):
        subject.load().resolve(subject.NATIVE, path, kind)


@pytest.mark.parametrize("change", ["trailing-data", "different-container", "changed-pin"])
def test_finite_fixture_pin_cannot_be_substituted_even_with_internally_valid_objects(tmp_path, change):
    raw = subject.FIXTURE.read_bytes()
    if change == "trailing-data":
        raw += b"unreviewed trailing payload"
    elif change == "different-container":
        raw = archive(members().items())
    else:
        raw = raw.replace(b"objects/", b"OBJECTS/", 1)
    assert hashlib.sha256(raw).hexdigest() != subject.FIXTURE_SHA256
    target = tmp_path / "counterfeit.zip"
    target.write_bytes(raw)
    with pytest.raises(ValueError, match="finite SHA256"):
        subject.load(target)
