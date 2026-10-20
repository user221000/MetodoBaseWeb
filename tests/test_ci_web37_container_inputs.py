"""The runtime contract must preserve dependencies beyond the old native image."""
import json

import pytest

from tests.ci_web37.container_inputs import ROOT, lock_blocks, verify_current_lock


def inputs():
    return ((ROOT / "requirements_web.lock").read_bytes(),
            (ROOT / "requirements-container.lock").read_bytes(),
            json.loads((ROOT / "runtime-source/container37-contract.json").read_bytes()))


@pytest.mark.parametrize("package", ["pyasn1", "pyasn1-modules", "cryptography"])
def test_missing_current_dependency_or_hash_block_cannot_reuse_the_old_native_inventory(package):
    web, container, contract = inputs()
    blocks, _ = lock_blocks(container)
    reduced = container.replace(b"\r\n", b"\n").replace(blocks[package], b"")
    with pytest.raises(ValueError, match="must be preserved"):
        verify_current_lock(web, reduced, contract)


def test_count56_cannot_hide_a_different_runtime_package_version():
    web, container, contract = inputs()
    contract["distributions"]["pyasn1"] = "0.0.0"
    with pytest.raises(ValueError, match="exact name/version"):
        verify_current_lock(web, container, contract)


def test_installer_or_binary_adapter_cannot_be_added_to_runtime_even_if_count_is_adjusted():
    web, container, contract = inputs()
    contract["distributions"]["pip"] = "26.2.1"
    contract["runtime_distribution_count"] = 58
    with pytest.raises(ValueError, match="exact name/version"):
        verify_current_lock(web, container, contract)


@pytest.mark.parametrize("count", [
    [57], {"value": 57}, {"count": 57}, 57.00000000000001,
    float("inf"), float("nan"), 0, -57, [],
])
def test_structured_nonfinite_or_wrong_count_cannot_satisfy_the_typed_contract(count):
    web, container, contract = inputs()
    contract["runtime_distribution_count"] = count
    with pytest.raises(ValueError, match="exact name/version"):
        verify_current_lock(web, container, contract)


def test_an_extras_requirement_is_a_separate_preserved_canonical_distribution():
    web, container, _ = inputs()
    blocks, versions = lock_blocks(web)
    assert versions["google-auth"] == "2.62.0"
    assert blocks["google-auth"].startswith(b"google-auth[pyjwt]==2.62.0")
    assert lock_blocks(container)[0]["google-auth"] == blocks["google-auth"]


@pytest.mark.parametrize("second", ["example_pkg", "EXAMPLE-PKG", "example.pkg[one]"])
def test_duplicate_canonical_names_cannot_be_hidden_by_spelling_or_extras(second):
    digest = b"0" * 64
    raw = b"example-pkg==1.0 \\\n    --hash=sha256:" + digest + b"\n"
    raw += second.encode() + b"==1.0 \\\n    --hash=sha256:" + digest + b"\n"
    with pytest.raises(ValueError, match="Duplicate canonical"):
        lock_blocks(raw)


@pytest.mark.parametrize("line", [
    b"--extra-index-url https://example.invalid/simple",
    b"example==1.0; python_version>'3.0'", b"example>=1.0", b"example==1.*",
])
def test_unsupported_active_lock_lines_cannot_be_silently_omitted(line):
    with pytest.raises(ValueError):
        lock_blocks(line + b"\n")


def test_a_comment_cannot_supply_a_missing_active_requirement_hash():
    with pytest.raises(ValueError, match="no authenticated hash"):
        lock_blocks(b"example[feature]==1.0\n    # --hash=sha256:" + b"0" * 64 + b"\n")
