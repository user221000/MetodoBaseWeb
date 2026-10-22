"""Close private originals and publish only a scanner-checked finite summary."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import zipfile

from tests.ci_google33.publish import scan


def write(path, value):
    with path.open("x", encoding="utf8") as output:
        json.dump(value, output, indent=2)
        output.write("\n")


def boundary_before_payload(private):
    if os.name == "nt":
        acl = subprocess.check_output(["icacls", str(private)])
        (private / "dacl-before-payload.private.txt").write_bytes(acl)
        return acl
    if private.stat().st_mode & 0o777 != 0o700:
        raise ValueError("Private originals require an existing0700 boundary")
    return None


def seal(private, public, result, acl):
    write(private / "observation.json", result)
    archive = private / "originals.private.zip"
    members = []
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(private.rglob("*")):
            if path.is_symlink():
                raise ValueError("Private evidence contains an unexpected symlink")
            if path.is_file() and path != archive:
                raw = path.read_bytes()
                name = path.relative_to(private).as_posix()
                output.writestr(name, raw)
                members.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    with zipfile.ZipFile(archive) as closed:
        if closed.namelist() != [row["path"] for row in members]:
            raise ValueError("Private originals closed membership differs")
        for row in members:
            if hashlib.sha256(closed.read(row["path"])).hexdigest() != row["sha256"]:
                raise ValueError("Private originals closed readback differs")
    write(private / "closed-manifest.json", {"members": members, "all_members_readback": True})
    if os.name == "nt":
        after = subprocess.check_output(["icacls", str(private)])
        (private / "dacl-after-readback.private.txt").write_bytes(after)
        if after != acl:
            raise ValueError("Private originals boundary changed")
    result.update(private_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  private_archive_members=len(members), all_members_readback=True,
                  private_boundary_before_payload=True, raw_private=True)
    summary = (json.dumps(result, indent=2) + "\n").encode()
    scan(summary)
    public.mkdir(mode=0o700)
    (public / "summary.json").write_bytes(summary)
    return result
