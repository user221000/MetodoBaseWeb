"""Author-only capture of three authenticated Git routes and two old RAW frames."""
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

from tests.ci_web37.git_recipe import object_id, tree_entries

ROOT = Path(__file__).resolve().parents[2]
ANCHOR = "b21b62c0711b3e277399bbe0a2686d1f89ab3249"
MANIFEST = "tests/e2e/native37_transitive_qa_v6.json"
PATHS = ("alembic.ini", "db_bootstrap.py")


def build(original_archive, destination):
    if hashlib.sha256(original_archive.read_bytes()).hexdigest() != (
            "186350fb9b33fdb19f85399914f82a5bb147f20fe8e71ba036ccbc93b3c3b3f2"):
        raise ValueError("The preserved before/after source archive differs")
    frames = {}

    def get(oid):
        result = subprocess.check_output(["git", "--no-replace-objects", "cat-file", "--batch"],
            input=(oid + "\n").encode(), cwd=ROOT)
        header, body = result.split(b"\n", 1)
        actual, kind, size = header.split()
        assert actual.decode() == oid and body.endswith(b"\n")
        raw = body[:-1]
        assert str(len(raw)).encode() == size and object_id(kind.decode(), raw) == oid
        frames[oid] = kind + b" " + size + b"\0" + raw
        return kind, raw

    kind, commit = get(ANCHOR)
    assert kind == b"commit"
    first = commit.split(b"\n", 1)[0]
    assert first.startswith(b"tree ")
    root_tree = first[5:].decode()

    def route(name):
        oid = root_tree
        parts = name.split("/")
        for index, part in enumerate(parts):
            kind, raw = get(oid)
            assert kind == b"tree"
            expected, oid = tree_entries(raw)[part]
            assert expected == ("blob" if index == len(parts) - 1 else "tree")
        kind, raw = get(oid)
        assert kind == b"blob"
        return raw

    data = {name: route(name) for name in (*PATHS, MANIFEST)}
    manifest = json.loads(data[MANIFEST])
    assert len(manifest["helper_union"]) == 22
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(original_archive) as sealed:
        before = sealed.read("before-RAW.zip")
    with zipfile.ZipFile(io.BytesIO(before)) as preserved:
        for name in PATHS:
            raw = preserved.read(name)
            assert hashlib.sha256(raw).hexdigest() == manifest["helper_union"][name]["raw_sha256"]
            assert b"\r\n" not in data[name] and raw == data[name].replace(b"\n", b"\r\n")
            (destination / ("native22-original-" + name + ".RAW")).write_bytes(raw)
    fixture = destination / "native22-original-objects.zip"
    with zipfile.ZipFile(fixture, "w", compression=zipfile.ZIP_STORED) as output:
        for oid, frame in sorted(frames.items()):
            entry = zipfile.ZipInfo("objects/" + oid, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            output.writestr(entry, frame)
    return {"fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
            "objects": len(frames), "routes": [*PATHS, MANIFEST], "anchor": ANCHOR,
            "original_v7_Git_LF_sha256": hashlib.sha256(subprocess.check_output(
                ["git", "show", ANCHOR + ":tests/test_security_native35_v7_peer.py"], cwd=ROOT)).hexdigest()}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-archive", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.original_archive, args.destination)))
