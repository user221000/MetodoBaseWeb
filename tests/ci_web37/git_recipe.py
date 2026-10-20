"""Read a finite Merkle proof of the original Git recipes, without a repository.

The ZIP contains original Git object frames, not a reconstructed commit or a
replacement authority. Unrelated tree children and commit parents are not
materialized. Every included object must be reached by a declared path.
"""
from __future__ import annotations

import hashlib
import io
import re
import zipfile
from pathlib import Path

NATIVE = "72c44a1834d7bd9803b4b8846c6c87e85a53bfd3"
BASELINE = "cd423ab0961898ce94fd2574cb4d6452cf8338b3"
NATIVE_FILES = (
    "Dockerfile", "requirements-container-apt-metadata.lock",
    "requirements-container-bootstrap.lock", "requirements-container-build.lock",
    "requirements-container-psycopg.lock", "requirements-container.lock",
    "runtime-source/expat-sec10/.gitattributes", "runtime-source/expat-sec10/13c5f63.patch",
    "runtime-source/expat-sec10/CONTRATO.md", "runtime-source/expat-sec10/rebuild_pyexpat.py",
    "runtime-source/expat-sec10/source-pins.json",
)
FIXTURE = Path(__file__).with_name("fixtures") / "native-recipe72-objects.zip"
FIXTURE_SHA256 = "62bf62f3dc5ec1be7d6abbe453b79b0004895d5df20943d3400be4aa24491d6b"
OID = re.compile(r"[0-9a-f]{40}")
MAX_OBJECT = 2 * 1024 * 1024
MAX_FIXTURE = 4 * 1024 * 1024


def object_id(kind, payload):
    frame = kind.encode("ascii") + b" " + str(len(payload)).encode("ascii") + b"\0" + payload
    return hashlib.sha1(frame, usedforsecurity=False).hexdigest()


def tree_entries(payload):
    rows = {}
    remaining = payload
    while remaining:
        head, separator, body = remaining.partition(b"\0")
        mode, space, name = head.partition(b" ")
        if (not separator or not space or mode not in {b"40000", b"100644", b"100755"}
                or not name or b"/" in name or name in {b".", b".."} or len(body) < 20):
            raise ValueError("Original Git tree framing differs")
        try:
            decoded = name.decode("utf8")
        except UnicodeDecodeError as error:
            raise ValueError("Original Git path encoding differs") from error
        if decoded in rows:
            raise ValueError("Original Git tree has an ambiguous path")
        rows[decoded] = ("tree" if mode == b"40000" else "blob", body[:20].hex())
        remaining = body[20:]
    return rows


class ObjectProof:
    def __init__(self, raw):
        if len(raw) > MAX_FIXTURE:
            raise ValueError("Original Git fixture exceeds the reviewed bound")
        self.objects = {}
        self.used = set()
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                records = archive.infolist()
                if len(records) > 100 or sum(row.file_size for row in records) > MAX_FIXTURE:
                    raise ValueError("Original Git fixture object inventory exceeds its bound")
                for row in records:
                    name = row.filename.removeprefix("objects/")
                    if (row.filename != "objects/" + name or OID.fullmatch(name) is None
                            or name in self.objects or row.flag_bits & 1 or row.file_size > MAX_OBJECT
                            or row.compress_type != zipfile.ZIP_STORED):
                        raise ValueError("Original Git fixture member inventory differs")
                    frame = archive.read(row)
                    header, separator, payload = frame.partition(b"\0")
                    kind, space, size = header.partition(b" ")
                    if (not separator or not space or kind not in {b"commit", b"tree", b"blob"}
                            or size != str(len(payload)).encode("ascii")
                            or object_id(kind.decode("ascii"), payload) != name):
                        raise ValueError("Original Git object type, length or identity differs")
                    self.objects[name] = (kind.decode("ascii"), payload)
        except (zipfile.BadZipFile, RuntimeError) as error:
            raise ValueError("Original Git fixture ZIP differs") from error

    def get(self, oid, kind):
        record = self.objects.get(oid)
        if record is None or record[0] != kind:
            raise ValueError("A required original Git object is absent or has a different type")
        self.used.add(oid)
        return record[1]

    def root_tree(self, commit):
        if commit not in {NATIVE, BASELINE}:
            raise ValueError("Original Git commit authority differs")
        first = self.get(commit, "commit").split(b"\n", 1)[0]
        if not first.startswith(b"tree ") or OID.fullmatch(first[5:].decode("ascii")) is None:
            raise ValueError("Original Git commit root tree differs")
        return first[5:].decode("ascii")

    def resolve(self, commit, path, kind):
        parts = path.split("/")
        if any(part in {"", ".", ".."} for part in parts) or "\\" in path:
            raise ValueError("A declared original Git path differs")
        oid = self.root_tree(commit)
        for index, part in enumerate(parts):
            entry = tree_entries(self.get(oid, "tree")).get(part)
            expected = kind if index == len(parts) - 1 else "tree"
            if entry is None or entry[0] != expected:
                raise ValueError("Original Git Merkle path differs")
            oid = entry[1]
        return oid

    def blob(self, commit, path):
        return self.get(self.resolve(commit, path, "blob"), "blob")

    def subtree(self, commit, prefix):
        records = {}

        def visit(oid, path):
            for name, (kind, child) in tree_entries(self.get(oid, "tree")).items():
                full = path + "/" + name
                if kind == "tree":
                    visit(child, full)
                else:
                    records[full] = child

        visit(self.resolve(commit, prefix, "tree"), prefix)
        return records

    def verify_routes(self):
        for path in NATIVE_FILES:
            self.blob(NATIVE, path)
        self.blob(BASELINE, "requirements_web.lock")
        self.subtree(BASELINE, "tests/ci_google33")
        if self.used != self.objects.keys():
            raise ValueError("Original Git fixture contains undeclared or unreachable objects")


def load(path=FIXTURE):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise ValueError("Original Git fixture finite SHA256 differs")
    proof = ObjectProof(raw)
    proof.verify_routes()
    return proof


def require_historical33_unchanged(root, proof):
    expected = proof.subtree(BASELINE, "tests/ci_google33")
    actual = {path.relative_to(root).as_posix(): object_id("blob", path.read_bytes())
              for path in (root / "tests/ci_google33").rglob("*")
              if path.is_file() and "__pycache__" not in path.parts}
    if actual != expected:
        raise ValueError("Historical33 verifier file inventory or RAW bytes differ")
