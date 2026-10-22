"""Preserve the literal 24 semantic witnesses using finite original Git RAW."""
from pathlib import Path

from tests.ci_web37.git_history import load


def export():
    proof = load()
    phase = "current-750-transport24"
    row = proof.manifest["phases"][phase]["files"]["tests/test_security_r05_753_peer.py"]
    raw = proof.blob(row["commit"], row["path"])
    namespace = {"__name__": "tests.ci_web37.r05_750_literal",
                 "__file__": str(Path(__file__).resolve().parents[2] / row["path"])}
    exec(compile(raw, namespace["__file__"], "exec"), namespace)  # noqa: S102 -- pinned original test blob, no reconstructed source
    namespace["git"] = lambda commit, name: proof.git(phase, commit, name)
    return {name: value for name, value in namespace.items() if not name.startswith("__")}
