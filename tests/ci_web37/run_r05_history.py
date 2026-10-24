"""Run literal frozen V5/V6 assertions with authenticated offline Git reads."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.scan_secrets import _private_evidence as private_directory
from tests.ci_web37.evidence import boundary_before_payload, write
from tests.ci_web37.git_history import load
from tests.ci_web37.reports import junit_identities


class Transport:
    def __init__(self, proof, phase):
        self.proof, self.phase = proof, phase
        self.identities = []

    def pytest_collection_modifyitems(self, items):
        expected = self.proof.manifest["phases"][self.phase]
        if len(items) != expected["required_cases"]:
            raise ValueError("The literal historical assertion collection differs")
        modules = {item.module for item in items}
        if {Path(module.__file__).name for module in modules} != {Path(name).name for name in expected["tests"]}:
            raise ValueError("An undeclared assertion module entered the historical phase")
        for module in modules:
            # Only the original Git read seam changes. The module, its fixture
            # inputs, complete test functions and all assertions stay literal.
            module.git = lambda commit, path: self.proof.git(self.phase, commit, path)
        self.identities = [item.nodeid for item in items]


def deny_external_actions():
    attempts = []

    def refused(*_args, **_kwargs):
        attempts.append("process_or_network")
        raise RuntimeError("The historical R05 phase prohibits processes and network access")

    subprocess.Popen = refused
    socket.create_connection = refused
    socket.socket.connect = refused
    socket.socket.connect_ex = refused
    socket.getaddrinfo = refused
    return attempts


def main():
    proof = load()
    choices = [name for name in proof.manifest["phases"] if name.startswith("frozen-")]
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--phase", choices=choices, required=True)
    parser.add_argument("--private", type=Path, required=True)
    args = parser.parse_args()
    private = private_directory(args.private)
    boundary_before_payload(private)
    source = proof.materialize(args.phase, private / "source")
    if (source / ".git").exists():
        raise ValueError("The historical phase must not contain a repository")
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ.pop("PYTHONPATH", None)
    sys.path = [str(source), *[entry for entry in sys.path if entry and Path(entry).resolve() != ROOT]]
    # Keep the authenticated proof and transport callables by reference, while
    # the frozen source supplies both package namespaces during collection.
    for module_name in tuple(sys.modules):
        if (module_name == "scripts" or module_name.startswith("scripts.")
                or module_name == "tests" or module_name.startswith("tests.")):
            del sys.modules[module_name]
    import pytest

    transport = Transport(proof, args.phase)
    attempts = deny_external_actions()
    original_stdout, original_stderr = sys.stdout, sys.stderr
    with (private / "pytest.private.log").open("x", encoding="utf8") as raw:
        try:
            sys.stdout = sys.stderr = raw
            code = pytest.main(["--noconftest", "--import-mode=importlib", "--rootdir=" + str(source),
                "-q", "--tb=short", "-p", "no:cacheprovider", "--basetemp=" + str(private / "data"),
                "--junitxml=" + str(private / "pytest.xml"),
                *[str(source / name) for name in proof.manifest["phases"][args.phase]["tests"]]], plugins=[transport])
        finally:
            sys.stdout, sys.stderr = original_stdout, original_stderr
    expected = proof.manifest["phases"][args.phase]["required_cases"]
    identities = junit_identities((private / "pytest.xml").read_bytes()) if code == 0 else set()
    accepted = code == 0 and len(identities) == expected and not attempts
    result = {"phase": args.phase, "accepted": accepted, "pytest_exit": code, "required_cases": expected,
              "passed_exact_unique_cases": len(identities), "process_or_network_attempts": len(attempts),
              "Git_repository_present": False, "current_runtime_claim": False, "Desktop": False,
              "PG": False, "Chrome": False, "VM": False, "source_materialization_files": len(proof.manifest["phases"][args.phase]["files"])}
    write(private / "result.json", result)
    print(json.dumps(result))
    return int(not accepted)


if __name__ == "__main__":
    raise SystemExit(main())
