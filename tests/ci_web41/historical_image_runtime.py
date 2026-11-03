"""Authenticate historical image runners and add a fresh TEST salt.

Invoke this standalone script directly, never with ``-m``: the original runner
must import its own historical tests/config. Ancestor files remain unchanged.
All original commands, checks, outcomes, roles, waits and cleanup are preserved.
An explicit optional member observer has a separate compiled source identity
and full inverse. Its metadata cannot turn an original failure into success.
"""
from __future__ import annotations

import argparse
import builtins
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath

OLD = b"        WEB_SECRET_KEY=base64.urlsafe_b64encode(os.urandom(48)).decode(),\n"
ADDITION = b"        METODO_BASE_SALT=base64.urlsafe_b64encode(os.urandom(32)).decode(),\n"
SOURCES = {
    "31": {
        "commit": "de506b6077ba055587f02e7d839387e7f5c56f84",
        "runner": "tests/ci_mfa31/run_current_browser.py",
        "bytes": 15278,
        "sha256": "1fe14e412f04f0c0e879950c3db6e8f246440b36ee7f168f47e3fd88025fe4e0",
        "compiled_sha256": "faa67d5dddd2cc90b5b61cc359f6aef5dfc4b60458f66d609770c2a9c2baf9e4",
        "tag_prefix": "metodobase-current31:",
    },
    "33": {
        "commit": "c86d1a25fcd0b0befcb4b473c4144917122109fb",
        "runner": "tests/ci_google33/run_current_browser.py",
        "bytes": 17278,
        "sha256": "6664f87aab2db016772ebbeee0e234fb6aa2c2e4abbaf6ff014dc93777326ed4",
        "compiled_sha256": "16bec0d3a9a70210c95c9eafc05aa123b0614dc6784836b110fcea5d2e1ec7eb",
        "tag_prefix": "metodobase-current33:",
    },
}
DIAGNOSTIC_COMPILED = {'31': {'bytes': 15454, 'sha256': '6ad7c696f564a5c824cf85eeeadb43d131d1f0668e0266d8019add3a979fe942'},
 '33': {'bytes': 17454, 'sha256': 'bb9461d966f2c9579eccdaca28d4e2bc085e2aba4b0ef3dcaea2e75856ff600b'}}
DIAGNOSTIC_SUPPORT = {'historical_failure_metadata.py': {'bytes': 31991, 'sha256': '7e689b1555edeb13fff469160a252a50b619dbbc40f9941c8c70309e9e424ba1'}, 'historical_member_diagnostic.py': {'bytes': 8773, 'sha256': '72968f95f1faa73f991441bbc08866131438a25ec835333ffdf736648f2a5cd4'}}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def specification(schema):
    if type(schema) is not str or schema not in SOURCES:
        raise ValueError("An explicit historical31 or33 source is required")
    return SOURCES[schema]


def adapted_bytes(raw, schema):
    spec = specification(schema)
    if len(raw) != spec["bytes"] or digest(raw) != spec["sha256"] or raw.count(OLD) != 1:
        raise ValueError("The complete historical runner differs")
    result = raw.replace(OLD, OLD + ADDITION)
    if result.count(ADDITION) != 1 or digest(result) != spec["compiled_sha256"]:
        raise ValueError("The finite TEST runtime companion differs")
    return result


def member_dispatch(schema):
    specification(schema)
    old = ("'tests/e2e/run_member_link" + schema + "_browser.py'").encode()
    new = ("_historical_member_diagnostic_path, '--schema', '" + schema
           + "', '--source', str(ROOT), '--failure-metadata', str(_historical_member_diagnostic_output)").encode()
    return old, new


def diagnostic_bytes(salt_source, schema):
    spec = specification(schema)
    if digest(salt_source) != spec["compiled_sha256"]:
        raise ValueError("The diagnostic predecessor must be the exact SALT companion")
    old, new = member_dispatch(schema)
    if salt_source.count(old) != 1:
        raise ValueError("The finite member dispatch count differs")
    result = salt_source.replace(old, new)
    pin = DIAGNOSTIC_COMPILED[schema]
    if (len(result), digest(result)) != (pin["bytes"], pin["sha256"]) or result.replace(new, old) != salt_source:
        raise ValueError("The complete member diagnostic source or inverse differs")
    return result


def diagnostic_support():
    parent = Path(__file__).absolute().parent
    plain_root(parent)
    for name, pin in DIAGNOSTIC_SUPPORT.items():
        path = parent / name
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or getattr(before, "st_file_attributes", 0) & 1024
                or path.resolve(strict=True) != path.absolute() or before.st_size != pin["bytes"]):
            raise ValueError("Member diagnostic support identity differs")
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or identity(opened)[:4] != identity(before)[:4]
                    or os.name != "nt" and identity(opened) != identity(before)):
                raise ValueError("Member diagnostic opened support identity differs")
            raw = stream.read(pin["bytes"] + 1)
            if identity(os.fstat(stream.fileno())) != identity(opened):
                raise ValueError("Member diagnostic opened support changed")
        after = path.lstat()
        if (identity(before) != identity(after) or after.st_nlink != 1
                or not stat.S_ISREG(after.st_mode) or getattr(after, "st_file_attributes", 0) & 1024
                or path.resolve(strict=True) != path.absolute()
                or (len(raw), digest(raw)) != (pin["bytes"], pin["sha256"])):
            raise ValueError("Member diagnostic support source differs")
    if set(DIAGNOSTIC_SUPPORT) != {"historical_failure_metadata.py", "historical_member_diagnostic.py"}:
        raise ValueError("The exact two member diagnostic supports are required")
    return parent / "historical_member_diagnostic.py"


def git(root, *args):
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
                       GIT_TERMINAL_PROMPT="0")
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(root), *args],
                                   env=environment, stderr=subprocess.PIPE, timeout=60)


def plain_root(root):
    root = Path(root)
    if not root.is_absolute() or root.resolve(strict=True) != root.absolute() or not root.is_dir():
        raise ValueError("An unaliased absolute historical source directory is required")
    return root


def snapshot(root, schema):
    """Authenticate every tracked file against the exact ancestor Git blobs."""
    root = plain_root(root)
    spec = specification(schema)
    if git(root, "rev-parse", "HEAD").decode().strip() != spec["commit"]:
        raise ValueError("The historical source HEAD differs")
    if Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve() != root:
        raise ValueError("The historical source boundary differs")
    listing = git(root, "ls-tree", "-r", "-z", "--long", spec["commit"])
    rows = []
    seen = set()
    total = 0
    for record in listing.split(b"\0"):
        if not record:
            continue
        metadata, name = record.split(b"\t", 1)
        match = re.fullmatch(rb"(100644|100755) blob ([0-9a-f]{40}) +([0-9]+)", metadata)
        name = name.decode("utf8")
        parts = PurePosixPath(name)
        if (match is None or parts.is_absolute() or parts.as_posix() != name
                or any(part in {"", ".", ".."} for part in parts.parts) or "\\" in name
                or name.casefold() in seen):
            raise ValueError("Unsupported historical Git inventory")
        seen.add(name.casefold())
        size = int(match[3])
        total += size
        if len(seen) > 25000 or total > 2 * 1024 ** 3:
            raise ValueError("Historical source inventory exceeds its boundary")
        path = root.joinpath(*parts.parts)
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or getattr(before, "st_file_attributes", 0) & 1024
                or before.st_size != size or path.resolve(strict=True) != path.absolute()):
            raise ValueError("A historical file is absent, changed or aliased")
        observed = hashlib.sha1(b"blob " + str(size).encode() + b"\0", usedforsecurity=False)
        with path.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                observed.update(block)
        after = path.lstat()
        identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        if identity(before) != identity(after) or observed.hexdigest() != match[2].decode():
            raise ValueError("A complete historical Git blob differs")
        rows.append([name, size, match[2].decode()])
    if not rows or spec["runner"] not in {row[0] for row in rows}:
        raise ValueError("The historical runner is absent")
    unexpected = [name for name in git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
                  if name and not name.startswith("docs/")]
    if unexpected:
        raise ValueError("Untracked historical runtime inputs are not admitted")
    if git(root, "rev-parse", "HEAD").decode().strip() != spec["commit"]:
        raise ValueError("Historical source changed during authentication")
    return {"source_commit": spec["commit"], "tracked_files": len(rows), "tracked_bytes": total,
            "inventory_sha256": digest(json.dumps(rows, separators=(",", ":")).encode())}


def execute(root, schema, output, image_tag, receipt, *, observe_member_failure=False, failure_metadata=None):
    """The original CLI is executed unchanged except the one literal addition."""
    if any(name in sys.modules for name in ("tests", "config", "web")):
        raise ValueError("Invoke the standalone script before historical package imports")
    root = plain_root(root)
    spec = specification(schema)
    if not re.fullmatch(re.escape(spec["tag_prefix"]) + "[0-9a-f]{40}", image_tag):
        raise ValueError("The original historical image tag contract differs")
    output, receipt = Path(output), Path(receipt)
    for target in (output, receipt):
        if (not target.is_absolute() or target.resolve(strict=False) != target.absolute()
                or target.is_relative_to(root) or target.exists()):
            raise ValueError("A new unaliased evidence path outside historical source is required")
    if not receipt.parent.is_dir():
        raise ValueError("The evidence parent must already exist")
    if type(observe_member_failure) is not bool or observe_member_failure != (failure_metadata is not None):
        raise ValueError("Member observation requires its separate diagnostic output")
    observer_path = None
    if observe_member_failure:
        observer_path = diagnostic_support()
        failure_metadata = Path(failure_metadata)
        if (not failure_metadata.is_absolute() or failure_metadata.resolve(strict=False) != failure_metadata.absolute()
                or failure_metadata.is_relative_to(root) or failure_metadata.exists()
                or failure_metadata in (output, receipt) or not failure_metadata.parent.is_dir()):
            raise ValueError("A fresh external member diagnostic output is required")
    before = snapshot(root, schema)
    original = (root / spec["runner"]).read_bytes()
    code = adapted_bytes(original, schema)
    if observe_member_failure:
        code = diagnostic_bytes(code, schema)
    previous_path, previous_argv, previous_cwd = list(sys.path), list(sys.argv), Path.cwd()
    result = {"schema": "finite-historical-image-test-runtime-v1", "original": before,
              "runner": spec["runner"], "original_sha256": digest(original), "compiled_sha256": digest(code),
              "only_delta": "Fresh32-byte METODO_BASE_SALT inside original synthetic runtime dictionary",
              "salt_value_recorded": False, "original_returned": False, "original_files_unchanged": False}
    if observe_member_failure:
        result["only_delta"] = "Fresh TEST salt plus one finite member diagnostic dispatch; complete two-stage inverse"
        result["salt_compiled_sha256"] = spec["compiled_sha256"]
        result["diagnostic_support"] = DIAGNOSTIC_SUPPORT
    try:
        os.chdir(root)
        sys.path.insert(0, str(root))
        sys.argv = [str(root / spec["runner"]), "--output", str(output), "--image-tag", image_tag]
        namespace = {"__file__": str(root / spec["runner"]), "__name__": "__main__", "__package__": None}
        if observe_member_failure:
            namespace.update(_historical_member_diagnostic_path=str(observer_path),
                             _historical_member_diagnostic_output=failure_metadata)
        exec(compile(code, str(root / spec["runner"]), "exec", dont_inherit=True), namespace)  # noqa: S102 -- exact pinned ancestral source
        result["original_returned"] = True
    except BaseException as error:
        if observe_member_failure:
            allowed = ("AssertionError", "ValueError", "TypeError", "KeyError", "IndexError", "OSError",
                       "FileNotFoundError", "PermissionError", "TimeoutError", "RuntimeError", "ImportError",
                       "ModuleNotFoundError", "MemoryError", "SystemExit", "KeyboardInterrupt")
            result["original_exception_class"] = next((name for name in allowed if type(error) is getattr(builtins, name)), "OTHER")
        else:
            result["original_exception_class"] = type(error).__name__
        raise
    finally:
        sys.path[:] = previous_path
        sys.argv[:] = previous_argv
        os.chdir(previous_cwd)
        try:
            after = snapshot(root, schema)
            result["original_files_unchanged"] = before == after
            if before != after:
                raise ValueError("Historical source changed during original execution")
            if observe_member_failure:
                diagnostic_support()
        finally:
            with receipt.open("x", encoding="utf8") as stream:
                json.dump(result, stream, indent=2)
                stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--schema", choices=tuple(SOURCES), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image-tag", required=True)
    parser.add_argument("--binding-receipt", type=Path, required=True)
    parser.add_argument("--observe-member-failure", action="store_true")
    parser.add_argument("--failure-metadata", type=Path)
    args = parser.parse_args()
    execute(args.source, args.schema, args.output, args.image_tag, args.binding_receipt,
            observe_member_failure=args.observe_member_failure, failure_metadata=args.failure_metadata)


if __name__ == "__main__":
    main()
