"""Bind new37 PG fixtures while retaining the original234 domain test objects."""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECIFICATION = Path(__file__).with_name("pg-legacy37.json")


def specification():
    value = json.loads(SPECIFICATION.read_bytes())
    if len(value["groups"]) != 18 or sum(len(row["original_cases"]) for row in value["groups"].values()) != 234:
        raise ValueError("Legacy234 current37 PG domain inventory differs")
    for name, digest in value["original_source_sha256_LF"].items():
        if hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != digest:
            raise ValueError("A bound original legacy PG function/fixture source differs")
    return value


def export_group(group):
    from tests.ci_web37 import pg_legacy_fixtures as current

    entry = specification()["groups"][group]
    original = importlib.import_module(entry["module"])
    names = {row[1].split("[", 1)[0] for row in entry["original_cases"]}
    all_tests = {name for name in vars(original) if name.startswith("test_")}
    if names != all_tests:
        raise ValueError("An original legacy PG assertion object was omitted or added")
    for name, pin in entry["test_objects"].items():
        function = getattr(original, name)
        if ((function.__module__, function.__name__) != (pin["provider_module"], pin["function_name"])
                or hashlib.sha256(inspect.getsource(function).replace("\r\n", "\n").encode()).hexdigest()
                != pin["source_sha256_LF"]):
            raise ValueError("An original legacy PG domain assertion provider differs")
    namespace = {name: value for name, value in vars(original).items() if not name.startswith("__")}
    for name, function in entry["fixture_bindings"].items():
        namespace[name] = getattr(current, function)
    namespace["current37_legacy_pool_witness"] = current.current37_legacy_pool_witness
    if any(namespace[name] is not getattr(original, name) for name in names):
        raise ValueError("An original legacy PG domain assertion object was replaced")
    return namespace
