"""Authenticate finite historical Git routes without Git or a repository.

Only original object frames are accepted. Named commit roots, declared paths,
finite framing and a pinned complete inventory establish each test phase.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from tests.ci_web37.git_recipe import object_id, tree_entries

OID = re.compile(r"[0-9a-f]{40}")
FIXTURES = Path(__file__).with_name("fixtures")
MANIFEST_SHA256 = "e8feba38f41b8146f4358ac559d773adf87e6f69810ad912c7bd0b31ab0f342f"
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_OBJECT = 8 * 1024 * 1024
MAX_OBJECTS = 2048


def safe_path(value):
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError("A historical Git route is not a finite relative regular path")
    return value


class HistoryProof:
    def __init__(self, raw, manifest):
        if len(raw) > MAX_ARCHIVE or hashlib.sha256(raw).hexdigest() != manifest["archive_sha256"]:
            raise ValueError("The finite historical ZIP differs")
        self.manifest = manifest
        self.routes = {(row["commit"], safe_path(row["path"])) for row in manifest["routes"]}
        self.roots = {commit for commit, _path in self.routes}
        if len(self.routes) != len(manifest["routes"]) or any(OID.fullmatch(root) is None for root in self.roots):
            raise ValueError("The historical route/root inventory is ambiguous")
        self.objects = {}
        self.used = set()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > MAX_OBJECTS or sum(row.file_size for row in entries) > MAX_ARCHIVE:
                raise ValueError("The finite historical object inventory exceeds its bound")
            for row in entries:
                oid = row.filename.removeprefix("objects/")
                if (row.filename != "objects/" + oid or OID.fullmatch(oid) is None or oid in self.objects
                        or row.flag_bits & 1 or row.compress_type != zipfile.ZIP_STORED or row.file_size > MAX_OBJECT):
                    raise ValueError("A historical ZIP member is undeclared, duplicated or oversized")
                frame = archive.read(row)
                head, separator, payload = frame.partition(b"\0")
                kind, space, size = head.partition(b" ")
                if (not separator or not space or kind not in {b"commit", b"tree", b"blob"}
                        or size != str(len(payload)).encode("ascii")
                        or object_id(kind.decode("ascii"), payload) != oid):
                    raise ValueError("An original Git object type, length or SHA1 differs")
                self.objects[oid] = (kind.decode("ascii"), payload)
        if len(self.objects) != manifest["objects"]:
            raise ValueError("The pinned historical object count differs")
        for commit, path in sorted(self.routes):
            self.blob(commit, path)
        for phase in manifest["phases"].values():
            for alias, target in phase["aliases"].items():
                if target not in self.roots:
                    raise ValueError("A historical alias has no authenticated root")
                if alias != "HEAD":
                    if not alias.endswith("^") or alias[:-1] not in self.roots:
                        raise ValueError("Only explicit HEAD/first-parent historical aliases are permitted")
                    parents = [line[7:].decode("ascii") for line in self.get(alias[:-1], "commit").split(b"\n")
                               if line.startswith(b"parent ")]
                    if not parents or parents[0] != target:
                        raise ValueError("The historical parent alias differs from its original commit frame")
        if self.used != self.objects.keys():
            raise ValueError("The historical ZIP contains unreachable or undeclared objects")

    def get(self, oid, kind):
        row = self.objects.get(oid)
        if row is None or row[0] != kind:
            raise ValueError("An authenticated historical Git object is absent or mistyped")
        self.used.add(oid)
        return row[1]

    def blob(self, commit, path):
        if (commit, safe_path(path)) not in self.routes:
            raise ValueError("The historical Git read is outside its explicit finite inventory")
        first = self.get(commit, "commit").split(b"\n", 1)[0]
        if not first.startswith(b"tree ") or OID.fullmatch(first[5:].decode("ascii")) is None:
            raise ValueError("The original historical commit root-tree framing differs")
        oid = first[5:].decode("ascii")
        parts = path.split("/")
        for index, part in enumerate(parts):
            entry = tree_entries(self.get(oid, "tree")).get(part)
            expected = "blob" if index == len(parts) - 1 else "tree"
            if entry is None or entry[0] != expected:
                raise ValueError("The original historical Merkle route differs")
            oid = entry[1]
        return self.get(oid, "blob")

    def git(self, phase, commit, path):
        selection = self.manifest["phases"][phase]
        if [commit, path] not in selection["git_reads"]:
            raise ValueError("This historical phase cannot read another phase's Git authority")
        return self.blob(selection["aliases"].get(commit, commit), path)

    def materialize(self, phase, destination):
        destination = Path(destination)
        if destination.exists():
            raise ValueError("Historical phase materialization requires a fresh directory")
        destination.mkdir()
        for name, row in self.manifest["phases"][phase]["files"].items():
            safe_path(name)
            raw = self.blob(row["commit"], row["path"])
            if row["framing"] == "Git LF to CRLF":
                if b"\r" in raw:
                    raise ValueError("A finite CRLF materialization has non-LF Git bytes")
                raw = raw.replace(b"\n", b"\r\n")
            elif row["framing"] != "Git exact":
                raise ValueError("An undeclared historical byte framing was requested")
            if hashlib.sha256(raw).hexdigest() != row["materialized_sha256"]:
                raise ValueError("A source-bound historical materialization differs")
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        return destination


def load():
    raw = (FIXTURES / "r05-history.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("The immutable historical manifest differs")
    manifest = json.loads(raw)
    return HistoryProof((FIXTURES / "r05-history-objects.zip").read_bytes(), manifest)
