"""Reject ineffective mounts while retaining the real startup protections."""
import ast
import copy

import pytest

from tests.ci_image57 import owned_data_startup as gate
from tests.test_current39_image_startup import host_config, witness


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def current_witness():
    return witness() | {"revision": gate.REVISION, "data_uid": 999, "data_gid": 999,
                        "data_mode": 0o755, "data_write": True}


def container():
    host = host_config() | {"Tmpfs": {"/data": gate.DATA_OPTIONS,
                                     "/tmp": "rw,nosuid,nodev,mode=1777"}}
    return {"Id": "c" * 64, "Image": "sha256:" + "b" * 64,
            "Config": {"Labels": {gate.OWNER_LABEL: "d" * 32}},
            "HostConfig": host, "State": {"Running": False, "ExitCode": 0}}


def test_accepts_complete_owned_mount_and_real_startup_witness():
    value = container()
    gate.validate_container(value, value["Id"], value["Image"], "d" * 32)
    observed = current_witness()
    gate.validate_witness(observed, {"app_hashes": observed["source_hashes"]})


@pytest.mark.parametrize("key,value", [
    ("data_uid", 0), ("data_gid", 0), ("data_mode", 0o777), ("data_mode", 0o555),
    ("data_write", False), ("data_write", 1), ("uid", 0), ("effective_capabilities", 1),
    ("no_new_privileges", False), ("FORCE_RLS", 34), ("owned_ready_HTTP_200", False),
    ("source_hashes", {}),
])
def test_rejects_mount_privilege_schema_readiness_and_source_regressions(key, value):
    observed = current_witness()
    observed[key] = value
    with pytest.raises(ValueError):
        gate.validate_witness(observed, {"app_hashes": current_witness()["source_hashes"]})


@pytest.mark.parametrize("key,value", [
    ("Tmpfs", {}), ("Tmpfs", {"/data": "rw,nosuid,nodev,mode=1777"}),
    ("CapDrop", []), ("ReadonlyRootfs", False), ("SecurityOpt", []), ("Memory", 0),
])
def test_rejects_mount_and_container_control_substitution(key, value):
    observed = copy.deepcopy(container())
    observed["HostConfig"][key] = value
    with pytest.raises(ValueError):
        gate.validate_container(observed, observed["Id"], observed["Image"], "d" * 32)


def test_sql_ready_cleanup_and_runtime_configuration_are_unchanged():
    parent = ast.parse(gate.source_bytes("tests/ci_image57/current41_startup.py"))
    child = ast.parse(gate.source())
    functions = lambda tree: {node.name: ast.dump(node, include_attributes=False)
                              for node in tree.body if isinstance(node, ast.FunctionDef)}
    a, b = functions(parent), functions(child)
    assert set(a) == set(b)
    changed = {name for name in a if a[name] != b[name]}
    assert changed == {"container", "validate_container", "validate_witness"}
    compile(gate.WITNESS, "actual-owned-mount-witness", "exec")
