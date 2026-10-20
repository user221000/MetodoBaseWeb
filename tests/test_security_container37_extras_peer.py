"""Independent packaging parser sees extras as distributions in the real locks."""
import json
import re

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from tests.ci_web37.container_inputs import ROOT, verify_current_lock


def parsed_requirements(raw):
    entries = {}
    for line in raw.decode().splitlines():
        if not re.match(r"^[A-Za-z0-9]", line):
            continue
        value = Requirement(line.removesuffix("\\").strip())
        name = canonicalize_name(value.name)
        assert name not in entries, "Duplicate canonical distribution"
        entries[name] = next(iter(value.specifier)).version
    return entries


def test_contract_covers_every_real_locked_distribution_including_extras():
    entries = parsed_requirements((ROOT / "requirements-container.lock").read_bytes())
    assert entries["google-auth"] == "2.62.0"
    expected = {**entries, "psycopg2": "2.9.13"}
    contract = json.loads((ROOT / "runtime-source/container37-contract.json").read_bytes())
    assert contract["distributions"] == expected
    assert type(contract["runtime_distribution_count"]) is int
    assert contract["runtime_distribution_count"] == len(expected)


def test_verifier_returns_the_complete_packaging_inventory_not_only_simple_names():
    web = (ROOT / "requirements_web.lock").read_bytes()
    container = (ROOT / "requirements-container.lock").read_bytes()
    contract = json.loads((ROOT / "runtime-source/container37-contract.json").read_bytes())
    versions = verify_current_lock(web, container, contract)
    expected = {**parsed_requirements(container), "psycopg2": "2.9.13"}
    assert versions == expected


def test_real_web_and_container_locks_keep_the_same_official_google_dependency():
    web = parsed_requirements((ROOT / "requirements_web.lock").read_bytes())
    container = parsed_requirements((ROOT / "requirements-container.lock").read_bytes())
    assert web["google-auth"] == container["google-auth"] == "2.62.0"
    assert {k: v for k, v in web.items() if k != "psycopg2-binary"} == container
