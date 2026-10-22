"""Exact executed SEC31/QA9 source; only new37 fixtures establish ownership."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "tests/ci_web37/pg-originals37.json"
SPEC_SHA256_LF = "ad5889954e23d6aae940b3e50bb460f50dfd07d3cafb5c1be5f20999adc9ece5"


def raw(name):
    specification = SPEC.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(specification).hexdigest() != SPEC_SHA256_LF:
        raise ValueError("The executed SEC31/QA9 source authority differs")
    row = json.loads(specification)["files"][name]
    source = ROOT / row["path"]
    if source.is_symlink():
        raise ValueError("An executed original source cannot be a symlink")
    value = source.read_bytes()
    if len(value) != row["bytes"] or hashlib.sha256(value).hexdigest() != row["raw_sha256"]:
        raise ValueError("An executed original source differs physically")
    return value, source


def literal(name):
    value, path = raw(name)
    module = ModuleType("tests.ci_web37.original_" + name.removesuffix(".py"))
    module.__file__ = str(path)
    exec(compile(value, str(path), "exec"), module.__dict__)  # noqa: S102
    return module


def security31():
    from tests.ci_web37.fixtures import current37_witness, followup_db
    from tests.followup34_http import followup_http

    providers = {
        "capability": literal("test_security_notifications36_capability_peer.py"),
        "money": literal("test_security_notifications36_money_controls_peer.py"),
        "original": literal("test_security_notifications36_money_peer.py"),
        "sdk": literal("test_security_notifications36_sdk_objects_peer.py"),
    }
    wrapper, _path = raw("integration_current36_security_peer.py")
    namespace = {"followup_db": followup_db, "notification_http": followup_http,
                 "current37_witness": current37_witness}
    # The old wrapper's restricted_witness and imports are never executed.
    # Its exact fourteen alias assignments select the original assertion objects.
    for node in ast.parse(wrapper).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        if not name.startswith("test_"):
            continue
        if (not isinstance(node.value, ast.Attribute) or not isinstance(node.value.value, ast.Name)
                or node.value.value.id not in providers):
            raise ValueError("The original SEC31 alias frame differs")
        namespace[name] = getattr(providers[node.value.value.id], node.value.attr)
    if len([name for name in namespace if name.startswith("test_")]) != 14:
        raise ValueError("The fourteen SEC assertion object aliases differ")
    return namespace


def primary9(name):
    from tests.ci_web37.fixtures import current37_witness, followup_db
    from tests.followup34_http import followup_http

    original = literal(name)
    namespace = {key: value for key, value in vars(original).items() if not key.startswith("__")}
    namespace.update(followup_db=followup_db, current37_witness=current37_witness)
    namespace["notification_http" if name.endswith("canary.py") else "primary_http"] = followup_http
    # The existing synthetic outbound port is preserved for both real adapters.
    namespace["outbound_transport_is_synthetic"] = literal(
        "test_security_qa26_primary_peer.py").outbound_transport_is_synthetic
    return namespace
