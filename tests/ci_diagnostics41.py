"""Finite CI failure metadata; never format exception messages or arguments."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import types

SCHEMA = "metodobase-ci41-failure-metadata-v1"
PHASES = frozenset({"path_validation", "context_prepare", "build_probe", "seal", "pg_bootstrap", "unknown"})
KINDS = frozenset({"OSError", "FileNotFoundError", "PermissionError", "ValueError", "KeyError", "TypeError",
                   "AssertionError", "CalledProcessError", "RuntimeError", "TimeoutExpired", "ImportError",
                   "ModuleNotFoundError", "MemoryError", "SystemExit"})
# Names are finite; each admitted frame also requires exact Git blob bytes and
# an in-range line number. Synthetic compiler names and workflow stdin stay out.
PATHS = frozenset({
    "tests/run_current_image57.py", "tests/ci_diagnostics41.py",
    "tests/ci_image57/run.py", "tests/ci_image57/authority.py", "tests/ci_image57/context.py",
    "tests/ci_image57/source_proof.py", "tests/ci_image57/probe.py", "tests/ci_image57/production_child.py",
    "tests/ci_image57/technical_child.py", "tests/ci_image57/native_probe_20261103.py",
    "tests/ci_image57/check_report.py", "tests/ci_web41/ci_cluster.py", "tests/ci_web41/source_companion.py",
    "tests/ci_web41/current41_schema.py", "tests/ci_web39/ci_cluster.py", "tests/ci_web39/pg_contract.py",
    "tests/ci_web39/pg_control.py", "tests/ci_web39/pg_admission.py", "tests/ci_web39/pg_tools_linux.py",
    "tests/ci_web37/prepare_collection.py", "tests/ci_web37/pg_lease.py", "tests/ci_web37/pg53.py",
    "tests/ci_web37/pg_plan.py", "tests/ci_web37/pg_control.py",
    "tests/billing13_legacy_apply37_pg_contract.py",
})
SHA = re.compile(r"[0-9a-f]{40}\Z")
TRACE_FILE = re.compile(rb'^  File "([^"\x00\r\n]{1,2048})", line ([1-9][0-9]{0,6}), in [^\r\n]*$')
TRACE_KIND = re.compile(rb'^(?:[A-Za-z_][A-Za-z0-9_]*\.)*([A-Za-z_][A-Za-z0-9_]{0,80})(?=:|$)')
MAX_TRACE = 4 * 1024 * 1024
MAX_LINE = 65536

# One finite text-location companion. These pins authenticate the exact Git
# wrapper, complete catalogue, retained parent and rewritten source separately.
# This does not attest execution, subprocess arguments or a successful bootstrap.
PG_WRAPPER = "tests/ci_web41/ci_cluster.py"
PG_CATALOGUE = "tests/ci_web41/source-companions.json"
PG_PARENT = "tests/ci_web39/ci_cluster.py"
PG_INPUTS = {
    PG_WRAPPER: (339, "b191951d5531ed6a99975296104c2128736215d16cbfbcb6a544cf4015641e02"),
    PG_CATALOGUE: (51728, "882420c1bfa56e90542f8b7a73057b8e9a7ec760c97d75150777c4afcb0f936a"),
    PG_PARENT: (8510, "dcb624fbde74a74c0509422f271920a795b4fdbaa3a519b9137020c5302772f2"),
}
PG_COMPILED_SHA256 = "06efafacf474934fbbcd4655dbd751a19ee1ca57010d4159e6c85e073bde0241"
# Keys are exact starting callsites, never arbitrary lines in compiled source.
# The AST fingerprints contain no locations and are stable in Python3.11/3.12.
PG_CALLS = {
    49: ("version", "95ab763fb7d607a1794809cf0ecd2c556280a91d9bcd327a4245cc9637d45fd1"),
    63: ("initdb", "6df463b4d7bcabc38285d327d1d9b393a829b794251173622b49d12ff752bbab"),
    66: ("pg_ctl_start", "0435a51b1e740b01388dda98b6a4de7aabbc0c1d33c3bc8751f7f601b3d7bef7"),
    136: ("pg_ctl_stop", "dda9a742df192f52caa89e0270e6cf16d988cb55dab0d27b81b357f58ab8c17f"),
}


def empty(phase="unknown", kind="OTHER"):
    return {"schema": SCHEMA, "accepted": False, "phase": phase if phase in PHASES else "unknown",
            "exception_type": kind if kind in KINDS else "OTHER", "source": None, "frames": []}


def regular(path, *, directory=False):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path.absolute():
        raise ValueError("Invalid diagnostic path")
    for item in (path, *path.parents):
        value = item.lstat()
        if item == path and not directory:
            valid = stat.S_ISREG(value.st_mode) and value.st_nlink == 1
        else:
            valid = stat.S_ISDIR(value.st_mode)
        if not valid or item.is_symlink() or getattr(value, "st_file_attributes", 0) & 0x400:
            raise ValueError("Invalid diagnostic boundary")
    return path


def git(repository, *args):
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
                       GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    process = subprocess.run(["git", "--no-replace-objects", *args], cwd=repository, env=environment,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=False)
    if process.returncode:
        raise ValueError("Unavailable diagnostic Git proof")
    return process.stdout


class Binding:
    """Read-only source proof. No checkout, fetch, process/app import or config write."""

    def __init__(self, repository, source, helper_source=None):
        self.root = regular(Path(repository), directory=True)
        if not isinstance(source, str) or SHA.fullmatch(source) is None:
            raise ValueError("Invalid diagnostic source")
        if git(self.root, "cat-file", "-t", source) != b"commit\n":
            raise ValueError("Invalid diagnostic commit")
        if git(self.root, "rev-parse", "--verify", "HEAD").decode("ascii").strip() != source:
            raise ValueError("Diagnostic source is not the executing checkout")
        helper_source = helper_source or source
        if not isinstance(helper_source, str) or SHA.fullmatch(helper_source) is None:
            raise ValueError("Invalid diagnostic helper source")
        if git(self.root, "cat-file", "-t", helper_source) != b"commit\n":
            raise ValueError("Invalid diagnostic helper commit")
        own = regular(Path(__file__).absolute()).read_bytes()
        if own != git(self.root, "cat-file", "blob", helper_source + ":tests/ci_diagnostics41.py"):
            raise ValueError("Diagnostic helper differs from its event object")
        self.source = source
        self.cache = {}

    def record(self, name):
        if name not in PATHS or PurePosixPath(name).as_posix() != name:
            return None
        if name not in self.cache:
            try:
                path = regular(self.root / name)
                raw = path.read_bytes()
                original = git(self.root, "cat-file", "blob", self.source + ":" + name)
                if raw != original or len(raw) > 1024 * 1024:
                    raise ValueError("Unbound diagnostic source")
                self.cache[name] = {"raw": raw, "sha256": hashlib.sha256(raw).hexdigest(),
                                    "lines": len(raw.splitlines())}
            except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
                self.cache[name] = None
        return self.cache[name]

    def compiled_pg_frame(self, filename, line):
        """Project one catalogue-bound location only; no import, exec or live claim."""
        if type(line) is not int or line not in PG_CALLS:
            return None
        try:
            name = Path(filename).absolute().relative_to(self.root).as_posix()
            if name != PG_WRAPPER:
                return None
            inputs = {}
            for relative, (size, expected) in PG_INPUTS.items():
                path = regular(self.root / relative)
                raw = path.read_bytes()
                original = git(self.root, "cat-file", "blob", self.source + ":" + relative)
                if len(raw) != size or raw != original or hashlib.sha256(raw).hexdigest() != expected:
                    raise ValueError("The finite PG diagnostic source differs")
                inputs[relative] = raw
            catalogue = json.loads(inputs[PG_CATALOGUE])
            if (set(catalogue) != {"schema", "revision", "entries"}
                    or catalogue["schema"] != "finite-authenticated-current41-source-companions-v1"
                    or catalogue["revision"] != "20261102_payment_refund_facts"
                    or len(catalogue["entries"]) != 19):
                raise ValueError("The finite PG diagnostic catalogue differs")
            entry = catalogue["entries"][PG_WRAPPER]
            if (entry["original"] != PG_PARENT
                    or entry["original_sha256_LF"] != PG_INPUTS[PG_PARENT][1]
                    or entry["current_sha256_LF"] != PG_COMPILED_SHA256):
                raise ValueError("The single PG diagnostic entry differs")
            raw = inputs[PG_PARENT]
            if not any(type(frame["bytes"]) is int and len(raw) == frame["bytes"]
                       and hashlib.sha256(raw).hexdigest() == frame["sha256"]
                       for frame in entry["original_frames"]):
                raise ValueError("The retained PG parent frame differs")
            text = raw.decode("utf8")
            for edit in entry["literal_edits"]:
                old, new, count = edit["old"], edit["new"], edit["count"]
                if type(count) is not int or count <= 0 or not old or text.count(old) != count:
                    raise ValueError("The finite PG diagnostic edit count differs")
                text = text.replace(old, new)
            compiled = text.encode("utf8")
            if len(compiled.splitlines()) != 151 or hashlib.sha256(compiled).hexdigest() != PG_COMPILED_SHA256:
                raise ValueError("The complete PG diagnostic compiled source differs")
            calls = {}
            for node in ast.walk(ast.parse(compiled)):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"):
                    fingerprint = hashlib.sha256(ast.dump(node, include_attributes=False).encode("utf8")).hexdigest()
                    if node.lineno in calls:
                        raise ValueError("An ambiguous PG diagnostic callsite differs")
                    calls[node.lineno] = fingerprint
            if calls != {number: value[1] for number, value in PG_CALLS.items()}:
                raise ValueError("The finite PG diagnostic subprocess AST differs")
            if any(regular(self.root / relative).read_bytes() != raw for relative, raw in inputs.items()):
                raise ValueError("The PG diagnostic source changed during read")
            return {"path": PG_WRAPPER, "line": line, "source_sha256": PG_COMPILED_SHA256,
                    "binding": "catalogue_compiled/text_location_only", "operation": PG_CALLS[line][0],
                    "wrapper_sha256": PG_INPUTS[PG_WRAPPER][1],
                    "catalogue_sha256": PG_INPUTS[PG_CATALOGUE][1],
                    "parent_source_sha256": PG_INPUTS[PG_PARENT][1]}
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, SyntaxError, subprocess.SubprocessError):
            return None

    def frame(self, filename, line):
        if type(line) is not int or not 1 <= line <= 1000000:
            return None
        try:
            name = Path(filename).absolute().relative_to(self.root).as_posix()
        except (ValueError, OSError, TypeError):
            return None
        record = self.record(name)
        if record is None or line > record["lines"]:
            return None
        return {"path": name, "line": line, "source_sha256": record["sha256"]}

    def live_frame(self, live, line):
        """A filename alone is not proof of the executing code object."""
        result = self.frame(live.f_code.co_filename, line)
        if result is None:
            return None
        record = self.record(result["path"])
        try:
            original = compile(record["raw"], live.f_code.co_filename, "exec",
                               dont_inherit=True, optimize=sys.flags.optimize)
        except (SyntaxError, ValueError, TypeError):
            return None
        pending = [original]
        matches = False
        while pending:
            code = pending.pop()
            if live.f_code == code:
                matches = True
                break
            pending.extend(value for value in code.co_consts if isinstance(value, types.CodeType))
        if not matches:
            return None
        result["binding"] = "code_git_compile_match"
        return result


def image_phase(frames, binding):
    main = next((frame for frame in frames if frame["path"] == "tests/ci_image57/run.py"), None)
    record = binding.record("tests/ci_image57/run.py")
    if main is None or record is None:
        return "unknown"
    module = ast.parse(record["raw"])
    function = next((node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "main"), None)
    if function is None:
        return "unknown"
    points = {}
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "context" and target.attr == "prepare":
            points["context_prepare"] = node.lineno
        elif isinstance(target, ast.Name) and target.id == "build_probe":
            points["build_probe"] = node.lineno
        elif (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
              and target.value.id == "evidence" and isinstance(target.slice, ast.Constant) and target.slice.value == "seal"):
            points["seal"] = node.lineno
    if set(points) != {"context_prepare", "build_probe", "seal"} or not points["context_prepare"] < points["build_probe"] < points["seal"]:
        return "unknown"
    line = main["line"]
    if not function.lineno <= line <= function.end_lineno:
        return "build_probe"  # A real frame in build_probe, not main's callsite.
    if line >= points["seal"]:
        return "seal"
    if line >= points["build_probe"]:
        return "build_probe"
    if line >= points["context_prepare"]:
        return "context_prepare"
    return "path_validation"


def exception_metadata(error, binding):
    result = empty(kind=type(error).__name__)
    result["source"] = binding.source
    frames = []
    current = error.__traceback__
    while current is not None:
        frame = binding.live_frame(current.tb_frame, current.tb_lineno)
        if frame is not None:
            frames.append(frame)
        current = current.tb_next
    result["phase"] = image_phase(frames, binding)
    result["frames"] = frames[-2:]
    return result


def emit_image_failure(error, repository, argv):
    """The original caller remains responsible for its nonzero failure exit."""
    result = empty(kind=type(error).__name__)
    try:
        positions = [index for index, value in enumerate(argv) if value == "--source"]
        if len(positions) != 1 or positions[0] + 1 >= len(argv):
            raise ValueError("One explicit source required for diagnostics")
        binding = Binding(repository, argv[positions[0] + 1])
        result = exception_metadata(error, binding)
    except Exception:
        pass  # A diagnostic failure cannot replace the caller's original failure.
    print(json.dumps(result, sort_keys=True), file=sys.stderr)


def parse_traceback(lines, binding, phase):
    """Consume only structural file headers and an allowlisted class prefix."""
    result = empty(phase)
    result["source"] = binding.source
    frames = []
    for line in lines:
        if not isinstance(line, bytes) or len(line) > MAX_LINE:
            raise ValueError("Bounded private traceback required")
        line = line.rstrip(b"\r\n")
        match = TRACE_FILE.fullmatch(line)
        if match is not None:
            try:
                frame = binding.frame(match[1].decode("utf8", errors="strict"), int(match[2]))
            except UnicodeError:
                frame = None
            if frame is not None:
                frame["binding"] = "text_location_only/path_git_match"
            elif phase == "pg_bootstrap":
                try:
                    frame = binding.compiled_pg_frame(match[1].decode("utf8", errors="strict"), int(match[2]))
                except UnicodeError:
                    frame = None
            if frame is not None:
                frames.append(frame)
            continue
        kind = TRACE_KIND.match(line)
        if kind is not None:
            value = kind[1].decode("ascii")
            if value in KINDS:
                result["exception_type"] = value
    result["frames"] = frames[-2:]
    return result


def private_trace_lines(path):
    path = regular(Path(path))
    parent = path.parent.stat()
    if os.name != "posix" or parent.st_uid != os.geteuid() or stat.S_IMODE(parent.st_mode) != 0o700:
        raise ValueError("Private owned POSIX trace boundary required")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        before = os.fstat(stream.fileno())
        if (before.st_uid != os.geteuid() or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > MAX_TRACE or before.st_mode & 0o022):
            raise ValueError("Private traceback metadata rejected")
        total = 0
        while line := stream.readline(MAX_LINE + 1):
            total += len(line)
            if total > MAX_TRACE or len(line) > MAX_LINE:
                raise ValueError("Private traceback bound exceeded")
            yield line
        after = os.fstat(stream.fileno())
        if (before.st_ino, before.st_dev, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns):
            raise ValueError("Private traceback changed during diagnostic read")


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--helper-source", required=True)
    parser.add_argument("--private-trace", required=True)
    parser.add_argument("--phase", choices=("pg_bootstrap",), required=True)
    args = parser.parse_args(argv)
    result = empty(args.phase)
    code = 1
    try:
        binding = Binding(args.repository, args.source, args.helper_source)
        result = parse_traceback(private_trace_lines(args.private_trace), binding, args.phase)
        code = 0
    except Exception:
        pass
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
