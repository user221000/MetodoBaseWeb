"""Portable opaque input for unchanged native35 controls; no services."""
from copy import deepcopy
import hashlib
import importlib
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests import test_security_native35_v7_peer as original
from tests.ci_web39 import composition
from tests.ci_web39 import native35_control_fixtures as provider


def test_three_catalogue_scopes_are_exact_and_original_test_objects_stay_identical():
    value = composition.specification()
    assert len(value["modules"]) == 75
    assert value["composition_scopes"] == {"current39_runtime_modules": 72,
        "historical37_operator_modules": 2, "synthetic_native35_control_modules": 1}
    assert sum("scope" not in item for item in value["modules"].values()) == 72
    before = dict(vars(original))
    companion, receipt = composition.clone_namespace(original, composition.native35_entry())
    assert companion.historical_profile_input is provider.historical_profile_input
    assert companion.historical_profile_input is not original.historical_profile_input
    assert vars(original) == before
    tests = {key: item for key, item in before.items() if key.startswith(("test_", "Test"))}
    assert tests and all(getattr(companion, key) is item for key, item in tests.items())
    assert receipt["validation_scope"] == provider.SCOPE
    assert receipt["fixture_bindings"][0]["service_admission"] is False


def test_normal_runtime_companion_keeps_its_scope_and_fixture_provider():
    name = "tests/test_account_security37_service.py"
    module = importlib.import_module(name.removesuffix(".py").replace("/", "."))
    companion, receipt = composition.clone_namespace(module, composition.specification()["modules"][name])
    assert receipt["validation_scope"] == "current39_runtime"
    assert companion.account37_engine is not module.account37_engine
    assert receipt["fixture_bindings"][0]["current_provider"] == "tests.ci_web39.sqlite_fixtures.account37_engine"


def test_without_explicit_plugin_flag_no_module_or_fixture_is_replaced():
    parent = SimpleNamespace(config=SimpleNamespace(getoption=lambda option: False))
    assert composition.pytest_pycollect_makemodule(composition.ROOT / composition.NATIVE35_MODULE, parent) is None


@pytest.mark.parametrize("fault", ["second-control", "different-provider", "different-fixture", "different-source", "removed", "wrong-split"])
def test_catalogue_refuses_an_unreviewed_native_control_contract(fault):
    value = deepcopy(composition.specification())
    entry = value["modules"][composition.NATIVE35_MODULE]
    if fault == "second-control":
        other = next(key for key, item in value["modules"].items() if "scope" not in item)
        value["modules"][other]["scope"] = provider.SCOPE
    elif fault == "different-provider":
        entry["replacements"]["historical_profile_input"]["module"] = "tests.ci_web39.sqlite_fixtures"
    elif fault == "different-fixture":
        entry["replacements"]["another_fixture"] = entry["replacements"].pop("historical_profile_input")
    elif fault == "different-source":
        entry["source_sha256_LF"] = "0" * 64
    elif fault == "removed":
        del value["modules"][composition.NATIVE35_MODULE]
    else:
        value["composition_scopes"]["synthetic_native35_control_modules"] = 2
    with pytest.raises(pytest.UsageError):
        composition.validate_specification(value)


@pytest.mark.parametrize("target", ["original-fixture", "provider-fixture", "provider-source-pin"])
def test_replaced_fixture_or_provider_cannot_enter_the_companion(monkeypatch, target):
    if target == "provider-source-pin":
        monkeypatch.setattr(composition, "NATIVE35_PROVIDER_SHA256_LF", "0" * 64)
    else:
        def counterfeit(request, monkeypatch):
            pytest.fail("A counterfeit fixture must never execute")
        counterfeit.__name__ = "historical_profile_input"
        counterfeit.__module__ = original.__name__ if target == "original-fixture" else provider.__name__
        fixture = pytest.fixture(autouse=True)(counterfeit)
        monkeypatch.setattr(original if target == "original-fixture" else provider, "historical_profile_input", fixture)
    with pytest.raises(pytest.UsageError, match="native35 control module, fixture or provider"):
        composition.clone_namespace(original, composition.native35_entry())


@pytest.mark.parametrize("function", sorted(provider.FUNCTIONS))
def test_targeted_profile_is_ephemeral_opaque_and_bound_before_original_assertions(tmp_path, monkeypatch, function):
    monkeypatch.delenv("METODOBASE_TEST_NATIVE35_V7_PROFILE", raising=False)
    monkeypatch.setattr(provider, "sys", SimpleNamespace(platform="win32"))
    request = SimpleNamespace(function=SimpleNamespace(__name__=function),
        getfixturevalue=lambda name: tmp_path if name == "tmp_path" else pytest.fail("Unexpected fixture"),
        node=SimpleNamespace(user_properties=[]))
    composition.fixture_function(provider.historical_profile_input)(request, monkeypatch)
    assert original.guard.PROFILE == tmp_path / "native35-control-profile.json"
    raw = original.guard.PROFILE.read_bytes()
    assert json.loads(raw) == {"scope": provider.SCOPE, "connection": None}
    assert original.guard.PROFILE_SHA == hashlib.sha256(raw).hexdigest() == provider.PROFILE_SHA256
    assert request.node.user_properties == [("native35_profile_scope", provider.SCOPE)]


def test_other_functions_do_not_read_inputs_create_profiles_or_rebind_guard(monkeypatch):
    monkeypatch.setenv("METODOBASE_TEST_NATIVE35_V7_PROFILE", "invalid-must-never-be-read")
    before = original.guard.PROFILE, original.guard.PROFILE_SHA
    def forbidden(name):
        pytest.fail("Unrelated controls must not request a profile directory")
    request = SimpleNamespace(function=SimpleNamespace(__name__="test_typed_finite_ACK_boundaries"), getfixturevalue=forbidden)
    composition.fixture_function(provider.historical_profile_input)(request, monkeypatch)
    assert (original.guard.PROFILE, original.guard.PROFILE_SHA) == before


@pytest.mark.parametrize("selected", ["relative.json", ""])
def test_explicit_historical_input_is_never_silently_replaced(tmp_path, selected):
    with pytest.raises(ValueError, match="historical V7 profile RAW"):
        provider.control_profile(tmp_path, {"METODOBASE_TEST_NATIVE35_V7_PROFILE": selected})
    assert list(tmp_path.iterdir()) == []


def test_real_profile_byte_drift_is_rejected_with_the_same_expected_hash_before_marker(tmp_path, monkeypatch):
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    profile, expected, _scope = provider.control_profile(profile_dir, {})
    monkeypatch.setattr(original.guard, "PROFILE", profile)
    monkeypatch.setattr(original.guard, "PROFILE_SHA", expected)
    task, _helpers = original.fixture_controls(tmp_path, monkeypatch)
    assert original.guard.require_ack(task, "chrome", original.NOW)
    profile.write_bytes(profile.read_bytes() + b" ")
    assert original.guard.PROFILE_SHA == expected
    starts = []
    with pytest.raises(ValueError, match="source/profile context"):
        original.guard.admitted_phase(lambda: original.guard.require_ack(task, "chrome", original.NOW),
                                    lambda: starts.append("forbidden child"))
    assert starts == []


@pytest.mark.parametrize("fault", ["PID", "address", "absent", "positive"])
def test_linux_proxy_runs_the_four_original_listener_assertions_and_restores_every_global(monkeypatch, fault):
    shared = subprocess.run, getattr(subprocess, "CREATE_NO_WINDOW", None)
    previous = original.guard.subprocess
    # The local input has no Windows constant and its real run must stay unused.
    without_windows_constant = SimpleNamespace(run=subprocess.run)
    function = getattr(original, provider.LISTENER_FUNCTION)
    request = SimpleNamespace(function=function, node=SimpleNamespace(user_properties=[]))
    with monkeypatch.context() as patch:
        patch.setattr(provider, "sys", SimpleNamespace(platform="linux"))
        patch.setattr(original.guard, "subprocess", without_windows_constant)
        composition.fixture_function(provider.historical_profile_input)(request, patch)
        proxy = original.guard.subprocess
        assert proxy is not without_windows_constant and proxy.CREATE_NO_WINDOW == 0
        with pytest.raises(ValueError, match="real listener observation process is forbidden"):
            proxy.run(["must-not-start"])
        function(patch, fault)
        assert request.node.user_properties == [
            ("native35_listener_scope", "synthetic listener observation; no processes")]
    assert original.guard.subprocess is previous
    assert (subprocess.run, getattr(subprocess, "CREATE_NO_WINDOW", None)) == shared
    with pytest.raises(ValueError, match="real listener observation process is forbidden"):
        proxy.run(["must-still-not-start-after-fake-restoration"])


@pytest.mark.parametrize("replacement", ["real", "wrapped-real", "other-lambda"])
def test_linux_proxy_rejects_real_or_wrapped_process_calls(monkeypatch, replacement):
    function = getattr(original, provider.LISTENER_FUNCTION)
    request = SimpleNamespace(function=function, node=SimpleNamespace(user_properties=[]))
    monkeypatch.setattr(provider, "sys", SimpleNamespace(platform="linux"))
    composition.fixture_function(provider.historical_profile_input)(request, monkeypatch)
    calls = []
    def wrapped(*args, **kwargs):
        calls.append("forbidden process")
        return subprocess.run(*args, **kwargs)
    candidate = {"real": subprocess.run, "wrapped-real": wrapped, "other-lambda": lambda *_a, **_k: None}[replacement]
    with pytest.raises(ValueError, match="pinned original listener fake"):
        original.guard.subprocess.run = candidate
    assert calls == []
    with pytest.raises(ValueError, match="real listener observation process is forbidden"):
        original.guard.subprocess.run(["must-not-start"])


def test_linux_listener_input_refuses_a_changed_function_before_rebinding_guard(monkeypatch):
    def changed(*_args):
        pytest.fail("A changed listener test must not execute")
    changed.__name__ = provider.LISTENER_FUNCTION
    request = SimpleNamespace(function=changed)
    previous = original.guard.subprocess
    monkeypatch.setattr(provider, "sys", SimpleNamespace(platform="linux"))
    with pytest.raises(ValueError, match="original pinned function"):
        composition.fixture_function(provider.historical_profile_input)(request, monkeypatch)
    assert original.guard.subprocess is previous


def test_windows_listener_input_changes_no_module_or_global(monkeypatch):
    function = getattr(original, provider.LISTENER_FUNCTION)
    request = SimpleNamespace(function=function)
    previous = original.guard.subprocess
    monkeypatch.setattr(provider, "sys", SimpleNamespace(platform="win32"))
    composition.fixture_function(provider.historical_profile_input)(request, monkeypatch)
    assert original.guard.subprocess is previous


@pytest.mark.parametrize("fault", ["PID", "address", "absent", "positive"])
def test_without_linux_listener_input_the_original_body_still_rejects_missing_Windows_constant(monkeypatch, fault):
    monkeypatch.setattr(original.guard, "subprocess", SimpleNamespace(run=lambda *_a, **_k: None))
    with pytest.raises(AttributeError, match="CREATE_NO_WINDOW"):
        getattr(original, provider.LISTENER_FUNCTION)(monkeypatch, fault)


@pytest.mark.parametrize("expired", [True, False])
def test_linux_launcher_input_runs_original_ACK_and_marker_assertions_and_restores_globals(tmp_path, monkeypatch, expired):
    real_import = original.importlib
    real_os = os.name, os.environ
    real_spec = importlib.util.spec_from_file_location
    function = getattr(original, provider.LAUNCHER_FUNCTION)
    request = SimpleNamespace(function=function, getfixturevalue=lambda name: tmp_path,
                              node=SimpleNamespace(user_properties=[]))
    with monkeypatch.context() as patch:
        patch.delenv("METODOBASE_TEST_NATIVE35_V7_PROFILE", raising=False)
        patch.setattr(provider, "sys", SimpleNamespace(platform="linux"))
        composition.fixture_function(provider.historical_profile_input)(request, patch)
        assert original.importlib is not real_import
        function(tmp_path, patch, expired)
    assert original.importlib is real_import
    assert (os.name, os.environ) == real_os and importlib.util.spec_from_file_location is real_spec


@pytest.mark.parametrize("fault", ["name", "different-path", "relative", "alias", "extra-positional", "loader-override"])
def test_private_launcher_import_refuses_any_other_load_before_real_loader(monkeypatch, fault):
    path = original.ROOT / "tests/e2e/run_native35_qa_v7.py"
    def forbidden(*_args, **_kwargs):
        pytest.fail("An unreviewed load reached the real spec factory")
    monkeypatch.setattr(provider, "importlib", SimpleNamespace(util=SimpleNamespace(
        spec_from_file_location=forbidden, module_from_spec=importlib.util.module_from_spec)))
    load = provider._launcher_import(path).util.spec_from_file_location
    name, location, args, kwargs = provider.LAUNCHER_NAME, path, (), {}
    if fault == "name": name = "other_module"
    elif fault == "different-path": location = path.with_name("other.py")
    elif fault == "relative": location = "tests/e2e/run_native35_qa_v7.py"
    elif fault == "alias": location = str(path.parent / ".." / "e2e" / path.name)
    elif fault == "extra-positional": args = (None,)
    else: kwargs = {"loader": object()}
    with pytest.raises(ValueError, match="exact pinned synthetic launcher load"):
        load(name, location, *args, **kwargs)


@pytest.mark.parametrize("fault", ["same-size-byte", "extra-byte", "relative-path"])
def test_private_launcher_source_refuses_tamper_before_execution(tmp_path, fault):
    path = tmp_path / "launcher.py"
    raw = (original.ROOT / "tests/e2e/run_native35_qa_v7.py").read_bytes()
    path.write_bytes((bytes([raw[0] ^ 1]) + raw[1:]) if fault == "same-size-byte" else raw + b" ")
    if fault == "relative-path":
        path = type(path)("relative.py")
    load = provider._launcher_import(path).util.spec_from_file_location
    with pytest.raises((ValueError, FileNotFoundError)):
        load(provider.LAUNCHER_NAME, path)


def test_private_launcher_rechecks_drift_at_exec_before_module_code_runs(tmp_path):
    path = tmp_path / "launcher.py"
    path.write_bytes((original.ROOT / "tests/e2e/run_native35_qa_v7.py").read_bytes())
    util = provider._launcher_import(path).util
    spec = util.spec_from_file_location(provider.LAUNCHER_NAME, path)
    module = util.module_from_spec(spec)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="pinned synthetic launcher source"):
        spec.loader.exec_module(module)
    assert not hasattr(module, "main")


def test_actual_loader_executes_authenticated_bytes_without_reopening_source_or_pyc(tmp_path, monkeypatch):
    path = tmp_path / "launcher.py"
    path.write_bytes((original.ROOT / "tests/e2e/run_native35_qa_v7.py").read_bytes())
    util = provider._launcher_import(path).util
    spec = util.spec_from_file_location(provider.LAUNCHER_NAME, path)
    module = util.module_from_spec(spec)
    def forbidden(*_args, **_kwargs):
        pytest.fail("The delegated loader reopened executable bytes after authentication")
    monkeypatch.setattr(spec.loader.loader, "get_data", forbidden)
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec.loader.exec_module(module)
    assert module.os is not os and module.os.name == "nt" and module.os.environ == {}
    assert callable(module.main) and not list(tmp_path.glob("__pycache__/*"))


@pytest.mark.parametrize("expired", [True, False])
def test_unadapted_posix_launcher_still_fails_the_original_Windows_platform_guard(tmp_path, monkeypatch, expired):
    function = getattr(original, provider.LAUNCHER_FUNCTION)
    request = SimpleNamespace(function=function, getfixturevalue=lambda name: tmp_path,
                              node=SimpleNamespace(user_properties=[]))
    monkeypatch.setattr(provider, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.delenv("METODOBASE_TEST_NATIVE35_V7_PROFILE", raising=False)
    composition.fixture_function(provider.historical_profile_input)(request, monkeypatch)
    path = original.ROOT / "tests/e2e/run_native35_qa_v7.py"
    util = original.importlib.util
    spec = util.spec_from_file_location(provider.LAUNCHER_NAME, path)
    execute = spec.loader.exec_module
    def posix(module):
        execute(module)
        module.os = SimpleNamespace(name="posix", environ={})
    spec.loader.exec_module = posix
    monkeypatch.setattr(original, "importlib", SimpleNamespace(util=SimpleNamespace(
        spec_from_file_location=lambda *_a, **_k: spec, module_from_spec=util.module_from_spec)))
    with pytest.raises(AssertionError):
        function(tmp_path, monkeypatch, expired)
