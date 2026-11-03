"""Read-only typed locations from a failed, authenticated runtime probe.

This is a diagnostic projection. It never changes the original gate outcome,
executes the probe, calls Docker, or publishes child stderr/source text.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path

SCHEMA = "current57-private-runtime-failure-location-v1"
MAX_FILE = 4 * 1024 * 1024
MAX_STDERR = 1024 * 1024
MAX_BLOB = 8 * 1024 * 1024
MAX_APP = 64 * 1024 * 1024
KINDS = frozenset({"AssertionError", "ValueError", "TypeError", "KeyError", "IndexError",
                   "OSError", "FileNotFoundError", "PermissionError", "ImportError",
                   "ModuleNotFoundError", "RuntimeError", "MemoryError", "SystemExit",
                   "AttributeError", "UnicodeError", "SyntaxError", "NameError"})
PRODUCERS = ("__init__.py", "probe.py", "context.py", "authority.py", "authority_pins.py",
             "technical_child.py", "production_child.py", "native_probe_20261103.py", "source_proof.py")
FRAME = re.compile(rb'^  File "<stdin>", line ([1-9][0-9]{0,5}), in [^\r\n]{1,200}$')
KIND = re.compile(rb'^([A-Za-z_][A-Za-z0-9_]{0,80})(?=:|$)')


def reject():
    raise ValueError("Runtime diagnostic rejected; values withheld") from None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path, *, directory=False):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path.absolute():
        reject()
    for current in (path, *path.parents):
        info = current.lstat()
        folder = current != path or directory
        if (not (stat.S_ISDIR(info.st_mode) if folder else stat.S_ISREG(info.st_mode))
                or current.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400
                or (not folder and info.st_nlink != 1)):
            reject()
    return path


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read(path, limit=MAX_FILE):
    path = regular(path)
    before = path.stat()
    if not 0 <= before.st_size <= limit:
        reject()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(limit + 1)
        closed = os.fstat(stream.fileno())
    # Windows Python3.12 stat()/fstat() expose different ctime semantics. Match
    # their inode/device/size/mtime, and require ctime stability within each API.
    if (len(raw) > limit or len(raw) != before.st_size or opened.st_nlink != 1
            or identity(before)[:4] != identity(opened)[:4] or identity(opened) != identity(closed)
            or identity(before) != identity(path.stat())):
        reject()
    regular(path)
    return raw


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            reject()
        result[key] = value
    return result


def document(raw):
    return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _: reject())


def git(root, *args, limit=MAX_FILE):
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
               GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", "--no-replace-objects", *args], cwd=root, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=False)
    if result.returncode or len(result.stdout) > limit:
        reject()
    return result.stdout


def blob(root, source, name, limit=MAX_FILE):
    reference = source + ":" + name
    size = git(root, "cat-file", "-s", reference, limit=32).strip()
    if not re.fullmatch(rb"[0-9]{1,9}", size) or int(size) > limit:
        reject()
    raw = git(root, "cat-file", "blob", reference, limit=limit)
    if len(raw) != int(size):
        reject()
    return raw


def authenticate_contract(root, source, contract):
    """Recompute application identities from Git objects, without checkout filters."""
    if (type(source) is not str or re.fullmatch("[0-9a-f]{40}", source) is None
            or git(root, "cat-file", "-t", source) != b"commit\n"
            or git(root, "rev-parse", "HEAD").strip() != source.encode("ascii")):
        reject()
    for name in PRODUCERS:
        path = "tests/ci_image57/" + name
        actual = read(root / path)
        original = blob(root, source, path)
        if actual not in (original, original.replace(b"\n", b"\r\n")):
            reject()
    # Producer modules may execute imports at module scope. Admit all their
    # transitive project source bytes before importing any of those modules.
    from . import context, probe

    if type(contract) is not dict or contract.get("source") != source:
        reject()
    hashes, modes, total = {}, {}, 0
    rows = git(root, "ls-tree", "-r", "-l", "-z", "--full-tree", source)
    for row in rows.split(b"\0"):
        if not row:
            continue
        fields, path = row.split(b"\t", 1)
        name = path.decode("utf8", errors="strict")
        if not (name.startswith(context.APP_PREFIXES) or name in context.APP_FILES):
            continue
        mode, kind, _object, size = fields.split()
        if kind != b"blob" or mode not in {b"100644", b"100755"} or name in hashes:
            reject()
        total += int(size)
        if int(size) > MAX_BLOB or total > MAX_APP:
            reject()
        raw = blob(root, source, name, MAX_BLOB)
        hashes[name], modes[name] = digest(raw), mode.decode("ascii")
    if (contract.get("app_hashes") != hashes or contract.get("app_modes") != modes
            or contract.get("source_tree") != git(root, "rev-parse", source + "^{tree}").decode("ascii").strip()):
        reject()
    return probe.bind(contract)


def location(raw, number):
    if type(number) is not int or not 1 <= number <= len(raw.splitlines()):
        reject()
    nodes = [node for node in ast.walk(ast.parse(raw)) if isinstance(node, ast.stmt)
             and node.lineno <= number <= node.end_lineno]
    if not nodes:
        reject()
    node = min(nodes, key=lambda value: (value.end_lineno - value.lineno, -value.col_offset))
    return {"line": number, "statement_line": node.lineno, "statement_end_line": node.end_lineno,
            "statement_kind": type(node).__name__,
            "ast_sha256": digest(ast.dump(node, include_attributes=False).encode("utf8")),
            "line_sha256": digest(raw.splitlines(keepends=True)[number - 1])}


def project_trace(stderr, bound):
    frames, kind = [], "OTHER"
    if len(stderr) > MAX_STDERR:
        reject()
    for line in stderr.splitlines():
        if len(line) > 65536:
            reject()
        match = FRAME.fullmatch(line)
        if match is not None:
            frames.append(location(bound, int(match[1])))
        match = KIND.match(line)
        if match is not None:
            candidate = match[1].decode("ascii")
            kind = candidate if candidate in KINDS else "OTHER"
    return {"exception_type": kind, "frames": frames[-4:],
            "location_binding": "private_trace_text_only/recomputed_probe_equal"}


def state_projection(private, source, iid):
    owner = document(read(private / "runtime-ownership.private.json"))
    before = document(read(private / "container-before.private.json"))
    after = document(read(private / "container-after.private.json"))
    if (type(owner) is not dict or owner.get("source") != source or owner.get("image_id") != iid
            or type(owner.get("nonce")) is not str or re.fullmatch("[0-9a-f]{32}", owner["nonce"]) is None
            or type(before) is not list or len(before) != 1 or type(after) is not list or len(after) != 1):
        reject()
    from . import probe

    for row in (before[0], after[0]):
        probe.validate_container(row, iid, source, owner["nonce"])
    cid = read(private / "container-id.private.txt", 66).strip()
    if not re.fullmatch(rb"[0-9a-f]{64}", cid) or before[0]["Id"] != cid.decode("ascii") or after[0]["Id"] != before[0]["Id"]:
        reject()
    state = after[0].get("State")
    if (type(state) is not dict or type(state.get("ExitCode")) is not int
            or not -255 <= state["ExitCode"] <= 255 or type(state.get("Running")) is not bool
            or type(state.get("OOMKilled")) is not bool):
        reject()
    return {"container_id": cid.decode("ascii"), "running": state["Running"],
            "exit_code": state["ExitCode"], "oom_killed": state["OOMKilled"]}


def diagnose(private, source, repository):
    private = regular(Path(private), directory=True)
    repository = regular(Path(repository), directory=True)
    if private.is_relative_to(repository):
        reject()
    contract_raw = read(private / "runtime-input-contract.json")
    contract = document(contract_raw)
    expected = authenticate_contract(repository, source, contract)
    prepared = read(private / "prepared-runtime-probe57.raw.py")
    bound = read(private / "bound-runtime-probe57.raw.py")
    if prepared != expected or bound != expected:
        reject()
    iid = read(private / "runtime.iid", 72).decode("ascii").strip()
    if re.fullmatch("sha256:[0-9a-f]{64}", iid) is None:
        reject()
    state = state_projection(private, source, iid)
    stderr = read(private / "runtime-stderr.private.log", MAX_STDERR)
    return {"schema": SCHEMA, "accepted": False, "diagnostic_only": True, "source": source,
            "image_id": iid, "bound_probe_sha256": digest(bound), "stderr_sha256": digest(stderr),
            "stderr_bytes": len(stderr), "input_contract_sha256": digest(contract_raw),
            "state": state, **project_trace(stderr, bound)}


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    try:
        result = diagnose(args.private, args.source, args.repository)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, SyntaxError,
            UnicodeError, RecursionError, subprocess.SubprocessError):
        print(json.dumps({"schema": SCHEMA, "accepted": False, "diagnostic_only": True,
                          "diagnostic_status": "WITHHELD_INVALID_OR_UNAVAILABLE_BOUNDARY"}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
