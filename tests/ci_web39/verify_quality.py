"""Real Ruff/Bandit controls over an isolated copy of the current web sources."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.ci_image57 import authority, context
from tests.ci_web37 import git_recipe
from tests.ci_web37.raw_git import raw_blobs
from tests.ci_web39 import quality

SUPPORT = (
    "requirements_web.lock", "entrypoint.sh", "tests/bandit-reviewed-baseline.json",
    "tests/ci_web37/container-inputs.json", "tests/ci_web37/fixtures/native-recipe72-objects.zip",
    "tests/ci_image57/fixtures/container-inputs.json.RAW", quality.PROPOSAL, quality.APPROVAL,
)


def copy_source(repository, target):
    """Copy public source/authority files only, never runtime data or dotenv."""
    names = set(SUPPORT)
    for directory in (*quality.RUNTIME, "scripts", "tests"):
        names.update(path.relative_to(repository).as_posix()
                     for path in (repository / directory).rglob("*.py"))
    names.update(quality.OPERATIONAL)
    names.update(context.json_object(authority.raw("container-inputs.json.RAW"))["candidate_files"])
    proposal = context.json_object((repository / quality.PROPOSAL).read_bytes())

    def dependency_paths(value):
        if isinstance(value, str):
            try:
                name = authority.canonical_name(value)
            except ValueError:
                return
            prefixes = tuple(part + "/" for part in quality.RUNTIME) + ("scripts/", "tests/", ".github/")
            if ("/" in name and name.startswith(prefixes)
                    and (repository / name).is_file()):
                names.add(name)
        elif type(value) is dict:
            for key, item in value.items():
                dependency_paths(key)
                dependency_paths(item)
        elif type(value) is list:
            for item in value:
                dependency_paths(item)

    dependency_paths(proposal)
    records = {}
    for name in sorted(names):
        authority.canonical_name(name)
        if any(part.startswith(".env") for part in Path(name).parts):
            raise ValueError("Dotenv is outside static quality controls")
        raw = authority.regular_file(repository / name).read_bytes()
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        records[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    # Source-only control copies can lack Git metadata. Preserve a complete physical approved
    # universe without consulting Git or changing a source byte.
    variants = {"captured_main_raw", "authenticated_git_objects"}
    for name, pin in proposal["bindings"].items():
        raw = (target / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        matches = set()
        if digest == pin["captured_main_raw_sha256"] and len(raw) == pin["captured_bytes"]:
            matches.add("captured_main_raw")
        if (digest == pin["authenticated_git_objects_sha256"] and len(raw) == pin["git_bytes"]
                and git_recipe.object_id("blob", raw) == pin["git_blob"]):
            matches.add("authenticated_git_objects")
        variants.intersection_update(matches)
        # This permits a finite transport to reviewed HEAD objects only. It
        # does not admit a mixed checkout to quality.classify. Reject body or
        # irregular framing before Git can replace any unreviewed bytes.
        lf = raw.replace(b"\r\n", b"\n")
        uniform = b"\r" not in lf and not (b"\r\n" in raw and b"\n" in raw.replace(b"\r\n", b""))
        git_frame = (uniform and len(lf) == pin["git_bytes"]
                     and hashlib.sha256(lf).hexdigest() == pin["authenticated_git_objects_sha256"]
                     and git_recipe.object_id("blob", lf) == pin["git_blob"])
        if not matches and not git_frame:
            raise ValueError("Physical source drift cannot be replaced by a Git transport")
    if variants:
        selected_variant = next(name for name in ("captured_main_raw", "authenticated_git_objects") if name in variants)
        for name in proposal["bindings"]:
            records[name]["transport"] = "authenticated_physical_whole_universe"
            records[name]["source_variant"] = selected_variant
        return records
    if not (repository / ".git").exists():
        raise ValueError("Mixed physical source frames require an authenticated current HEAD Git transport")
    # Materialize the entire approved Git-object universe, not an arbitrary EOL
    # normalization. Read the current HEAD so a shallow CI checkout is enough;
    # every object must still equal the explicit source-review pin. This is an
    # explicit Git snapshot for tool controls, not admission of checkout bytes.
    # The actual quality gate still requires one whole approved source universe.
    with context.git_policy():
        revision = context.git(repository, "rev-parse", "HEAD").decode().strip()
        context.check_source(repository, revision)
        listing = context.git(repository, "ls-tree", "-r", "-z", revision)
        entries = {}
        for row in listing.split(b"\0"):
            if row:
                head, name = row.split(b"\t", 1)
                mode, kind, oid = head.decode().split()
                entries[name.decode("utf8")] = (mode, kind, oid)
        selected = {}
        for name, pin in proposal["bindings"].items():
            mode, kind, oid = entries[name]
            if kind != "blob" or mode not in {"100644", "100755"} or oid != pin["git_blob"]:
                raise ValueError("Current HEAD is not the exact reviewed Git source")
            selected[name] = (oid, mode)
        for name, raw, oid, _mode in raw_blobs(repository, selected):
            pin = proposal["bindings"][name]
            if len(raw) != pin["git_bytes"] or hashlib.sha256(raw).hexdigest() != pin["authenticated_git_objects_sha256"]:
                raise ValueError("Current HEAD is not the reviewed Git-object universe")
            (target / name).write_bytes(raw)
            records[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                             "checkout_sha256": records[name]["sha256"], "git_blob": oid,
                             "source_commit": revision, "transport": "authenticated_current_HEAD_Git_object"}
    return records


def verify(repository, evidence, *, approval_control=None):
    """An optional approval is confined to this temporary test copy.

    The actual quality CLI always reads its own repository approval file. This
    control grants no approval to Main or to any other source directory.
    """
    repository = authority.regular_directory(Path(repository))
    evidence = authority.regular_directory(Path(evidence))
    observations = []
    with tempfile.TemporaryDirectory(prefix="metodobase-quality39-") as temporary:
        base = Path(temporary).resolve()
        if base.parent != Path(tempfile.gettempdir()).resolve():
            raise ValueError("Quality control temporary root differs")
        target = authority.private_directory(base / "source", repository)
        records = copy_source(repository, target)
        if approval_control is not None:
            (target / quality.APPROVAL).write_text(json.dumps(approval_control, indent=2) + "\n", encoding="utf8")
        (evidence / "source-copy.json").write_text(json.dumps({
            "scope": "temporary static tool controls only", "files": records,
            "temporary_test_approval": approval_control is not None}, indent=2) + "\n", encoding="utf8")
        command = [sys.executable, "-B", "-X", "utf8", str(target / "tests/ci_web39/quality.py")]

        def run(mode, filename, expected, marker=None):
            process = subprocess.run([*command, mode], cwd=target, capture_output=True,
                                     timeout=60, check=False)
            index = len(observations) + 1
            (evidence / f"tool-{index}.stdout.private.log").write_bytes(process.stdout)
            (evidence / f"tool-{index}.stderr.private.log").write_bytes(process.stderr)
            stdout = process.stdout.decode("utf8", errors="replace")
            stderr = process.stderr.decode("utf8", errors="replace")
            row = {"mode": mode, "file": filename, "exit": process.returncode,
                   "positive_control": expected == 0, "required_marker": marker}
            observations.append(row)
            if (expected == 0 and process.returncode != 0) or (expected != 0 and process.returncode == 0):
                raise ValueError("A real quality control returned the wrong status; originals retained")
            if marker is not None and marker not in stdout + stderr:
                raise ValueError("A rejection did not include the actual tool finding; originals retained")
            if marker == "B602":
                observed = {line.removeprefix("Observed B602 ").rsplit(":", 1)[0]
                            .replace("\\", "/").removeprefix("./")
                            for line in stdout.splitlines() if line.startswith("Observed B602 ")}
                if filename not in observed:
                    raise ValueError("The real new B602 was not bound to the changed source")

        files = ("api_server.py", "scripts/backup_daily.py", "web/quality39_control.py",
                 "runtime-source/quality39_control.py")
        for name in files:
            source = target / name
            previous = source.read_bytes() if source.exists() else None
            try:
                # An intact, fully admitted source is required before each
                # mutation, so a missing fixture/authority cannot mimic success.
                for mode in ("lint", "syntax", "security"):
                    run(mode, name, 0)
                source.write_text("def probe():\n    return undefined_quality39_canary\n", encoding="utf8")
                run("lint", name, 1, "F821")
                source.write_text("def broken(:\n", encoding="utf8")
                run("syntax", name, 1, "SyntaxError")
                source.write_text("import subprocess\ndef dangerous(command):\n    subprocess.run(command, shell=True)\n", encoding="utf8")
                run("security", name, 1, "B602")
            finally:
                if previous is None:
                    source.unlink(missing_ok=True)
                else:
                    source.write_bytes(previous)
        result = {"scope": "static quality tools only; generated code never imported or executed",
                  "failure_probes": 12, "positive_controls": 12,
                  "temporary_test_approval": approval_control is not None, "observations": observations}
        (evidence / "controls.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    result = verify(ROOT, args.evidence)
    print(json.dumps({key: value for key, value in result.items() if key != "observations"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
