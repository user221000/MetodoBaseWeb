"""Read original regular Git blobs without archive/export or checkout filters."""
from __future__ import annotations

import hashlib
import re
import subprocess


def raw_blobs(repository, entries):
    """Yield (path, raw, oid, mode), checking each batch object frame and hash."""
    with subprocess.Popen(
        ["git", "--no-replace-objects", "cat-file", "--batch"], cwd=repository,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ) as child:
        try:
            for name, (oid, mode) in sorted(entries.items()):
                if re.fullmatch(r"[0-9a-f]{40}", oid) is None:
                    raise ValueError("Historical source Git object identity differs")
                child.stdin.write(oid.encode("ascii") + b"\n")
                child.stdin.flush()
                header = child.stdout.readline(256)
                fields = header.rstrip(b"\n").split(b" ")
                if (len(fields) != 3 or fields[0] != oid.encode("ascii")
                        or fields[1] != b"blob" or not fields[2].isdigit()
                        or header != b" ".join(fields) + b"\n"):
                    raise ValueError("Historical source Git batch frame differs")
                size = int(fields[2])
                if size > 100 * 1024 * 1024:
                    raise ValueError("Historical source blob exceeds the reviewed bound")
                raw = child.stdout.read(size)
                if len(raw) != size or child.stdout.read(1) != b"\n":
                    raise ValueError("Historical source Git batch body differs")
                digest = hashlib.sha1(b"blob " + str(size).encode() + b"\0" + raw,
                                      usedforsecurity=False).hexdigest()
                if digest != oid:
                    raise ValueError("Historical source Git blob differs")
                yield name, raw, oid, mode
            child.stdin.close()
            extra = child.stdout.read()
            diagnostics = child.stderr.read()
            code = child.wait(timeout=30)
            if code != 0 or extra or diagnostics:
                raise ValueError("Historical source Git batch completion differs")
        finally:
            # This is our direct Git child, never a Python redirector or service.
            if child.poll() is None:
                child.kill()
                child.wait(timeout=30)
