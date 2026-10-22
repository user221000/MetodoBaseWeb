"""The explicit offline transport cannot widen host I/O or accept fake reports."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.ci_web37.node_current import validate

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = {"format": "public-pass-lines", "expected_cases": ["first", "second"]}


def test_public_proof_footer_keeps_two_exact_named_executions():
    raw = b'PASS first\nPASS second\n{"passed":2,"failed":0,"runtime":"Node VM; no native browser"}\n'
    assert validate(raw, PUBLIC) == 2


@pytest.mark.parametrize("change", ["order", "duplicate", "Boolean-failed", "footer-extra", "count-only"])
def test_public_footer_cannot_replace_missing_names_or_counterfeit_typed_success(change):
    lines = ["PASS first", "PASS second"]
    footer = {"passed": 2, "failed": 0, "runtime": "Node VM; no native browser"}
    if change == "order":
        lines.reverse()
    elif change == "duplicate":
        lines[1] = lines[0]
    elif change == "Boolean-failed":
        footer["failed"] = False
    elif change == "footer-extra":
        footer["results"] = []
    else:
        lines = []
    with pytest.raises(ValueError):
        validate(("\n".join([*lines, json.dumps(footer)]) + "\n").encode(), PUBLIC)


@pytest.mark.parametrize("expression", [
    "cp.execFileSync('git',['version'],{encoding:'utf8'})",
    "cp.execFileSync('git',['show','6ee27e3c:tests/e2e/security_browser31_ui_peer.cjs'],{encoding:'utf8',shell:true})",
    "cp.spawnSync(process.execPath,['-e','process.exit(0)'])",
    "require('node:net').createServer().listen(0)",
])
def test_ui_git_read_adapter_never_permits_another_process_or_network_listener(expression):
    code = "const cp=require('node:child_process'),a=require('node:assert/strict');a.throws(()=>{" + expression + "});"
    completed = subprocess.run([shutil.which("node"), "--require", str(ROOT / "tests/e2e/ci_web37_offline.cjs"),
                                "-e", code], cwd=ROOT, capture_output=True, timeout=20, check=False)
    assert completed.returncode == 0
    assert completed.stdout == completed.stderr == b""
