"""Admission and mutation canaries for the explicit current41 Node bridge."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from tests.ci_web41 import node_contracts as subject
from tests.ci_web38.reports import node_cases


def test_reviewed_manifest_and_all_historical_descriptors_are_admitted():
    value = subject.require_sources()
    assert len(value["input_files"]) == 322
    assert value["current_executed_additional_criteria"] == 96
    assert len(value["program_transitions"]) == 3


@pytest.mark.parametrize("raw", [b"a\rb", b"a\r\nb\n", b"a\nb\r\n"])
def test_mixed_or_lone_cr_source_is_rejected(raw):
    with pytest.raises(ValueError, match="uniform"):
        subject.canonical(raw)


def test_two_declared_uniform_text_transports_have_one_identity():
    assert subject.canonical(b"a\nb\n") == subject.canonical(b"a\r\nb\r\n")


@pytest.mark.parametrize("relative", [
    "web/static/js/api.js", "web/static/js/payment-history.js",
    "tests/e2e/mfa_api.cjs", "tests/ci_web41/node_adapter.cjs",
    "tests/ci_web41/node-adapters41.json",
    "tests/ci_web41/fixtures/routines_panel-878082.cjs.RAW",
    *[entry[0] for entry in subject.DESCRIPTORS.values()],
])
def test_changed_program_parser_adapter_or_historical_descriptor_rejects(monkeypatch, relative):
    original = Path.read_bytes
    target = (subject.ROOT / relative).resolve()
    def changed(path):
        raw = original(path)
        return raw + b"\nUNKNOWN_CURRENT41_CHANGE\n" if path.resolve() == target else raw
    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(ValueError):
        subject.require_sources()


def test_unknown_direct_transitive_source_rejects(monkeypatch):
    original = Path.glob
    def changed(path, pattern):
        values = list(original(path, pattern))
        if path == subject.ROOT and pattern == "web/static/js/*.js":
            values.append(subject.ROOT / "AGENTS.md")
        return iter(values)
    monkeypatch.setattr(Path, "glob", changed)
    with pytest.raises(ValueError, match="input set"):
        subject.require_sources()


@pytest.mark.parametrize("mutation", ["missing", "wrong-output", "historical-pass", "boolean-count", "wrong-copy"])
def test_adapter_receipt_requires_exact_output_parity_and_current_scope(mutation):
    adapter = json.loads((subject.ROOT / "tests/ci_web41/node-adapters41.json").read_bytes())["rules"][0]
    evidence = {key: copy.deepcopy(adapter[key]) for key in (
        "script", "original_canonical_lf_sha256", "input_compiled_canonical_lf_sha256",
        "output_compiled_canonical_lf_sha256", "criterion_renames", "allowed_assertion_changes")}
    evidence.update(historical_PASS_claim=False, assertions_preserved=adapter["assertion_count"])
    report = {"current41_adapter": evidence}
    subject._adapter_receipt(report, adapter)
    if mutation == "missing":
        report.clear()
    elif mutation == "wrong-output":
        evidence["output_compiled_canonical_lf_sha256"] = "0" * 64
    elif mutation == "historical-pass":
        evidence["historical_PASS_claim"] = True
    elif mutation == "boolean-count":
        evidence["assertions_preserved"] = True
    else:
        evidence["allowed_assertion_changes"] = [{"before": "unknown", "after": "arbitrary text"}]
    with pytest.raises(ValueError):
        subject._adapter_receipt(report, adapter)


@pytest.mark.parametrize("names", [["old"], ["required", "unknown"], ["required", "required"]])
def test_removed_new_duplicate_or_unknown_result_criterion_is_not_green(names):
    report = {"passed": len(names), "total": len(names),
              "results": [{"case": name, "passed": True} for name in names]}
    with pytest.raises(ValueError):
        node_cases(report, ["required"])


def test_real_node_adapter_rejects_unknown_compiled_code_copy_and_assertions(tmp_path):
    executable = shutil.which("node")
    assert executable, "Node is a required input; no silent skip"
    source = tmp_path / "before.cjs"
    environment = dict(os.environ, BROWSER31_DEBUG_SOURCE=str(source))
    result = subprocess.run([
        executable, "--require", "./tests/ci_web41/node_adapter.cjs",
        "tests/e2e/browser_compat31.cjs", "mfa_api"],
        cwd=subject.ROOT, env=environment, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode("utf8", errors="replace")
    report = json.loads(result.stdout)
    assert report["passed"] == report["total"] == 28
    assert report["current41_adapter"]["historical_PASS_claim"] is False
    script = r"""
const fs=require('node:fs'),assert=require('node:assert/strict');
const adapter=require('./tests/ci_web41/node_adapter.cjs');
const rules=JSON.parse(fs.readFileSync('./tests/ci_web41/node-adapters41.json','utf8')).rules;
const input=fs.readFileSync(process.argv[1],'utf8'),rule=rules[0];
assert.equal(typeof adapter.adapt(input,rule).text,'string');
let rejected=0;
for(const value of [input+'\nunknown();',input.replace('assert.equal','assert.notEqual'),input.replace('primaryGoogle','primaryGoogleUnrelated')]){
  assert.throws(()=>adapter.adapt(value,rule));rejected++;
}
const copyRule=rules.find(row=>row.script.endsWith('onboarding22_personal.cjs'));
const copy=fs.readFileSync(copyRule.script,'utf8');
assert.equal(typeof adapter.adapt(copy,copyRule).text,'string');
for(const value of [copy.replace('Configurar mi plan','arbitrary accepted copy'),copy.replace('assert.match','assert.ok')]){
  assert.throws(()=>adapter.adapt(value,copyRule));rejected++;
}
assert.throws(()=>require('node:net').createServer().listen(0));rejected++;
console.log(JSON.stringify({rejected,network_attempt_blocked:true}));
"""
    result = subprocess.run([executable, "-e", script, str(source)], cwd=subject.ROOT,
                            env=os.environ, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode("utf8", errors="replace")
    assert json.loads(result.stdout) == {"rejected": 6, "network_attempt_blocked": True}
