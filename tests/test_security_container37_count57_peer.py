"""Explicit QA-30 companion of count56: current57 plus typed adjacent controls."""
import json

import pytest

from tests.ci_web37.container_inputs import ROOT, verify_current_lock


@pytest.mark.parametrize("count", [57.0, "57", True, False, None, 55, 56, 58])
def test_current_runtime_count_requires_the_integer57_not_numeric_coercion(count):
    web = (ROOT / "requirements_web.lock").read_bytes()
    container = (ROOT / "requirements-container.lock").read_bytes()
    contract = json.loads((ROOT / "runtime-source/container37-contract.json").read_bytes())
    contract["runtime_distribution_count"] = count
    with pytest.raises(ValueError):
        verify_current_lock(web, container, contract)


def test_actual_current_integer57_and_exact_versions_are_accepted():
    contract = json.loads((ROOT / "runtime-source/container37-contract.json").read_bytes())
    assert type(contract["runtime_distribution_count"]) is int
    versions = verify_current_lock((ROOT / "requirements_web.lock").read_bytes(),
                                   (ROOT / "requirements-container.lock").read_bytes(), contract)
    assert len(versions) == 57
