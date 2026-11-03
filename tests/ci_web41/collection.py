"""Six explicit source companions retain all historical collection identities.

The logging contract's revision literal and the release wiring now target41.
The old source and its plain historical RED remain reproducible unchanged.
Every original test name and parametrization remains in the current companion.
"""
import ast
import hashlib
import importlib
import os
import sys
from pathlib import Path
from types import CodeType, FunctionType, ModuleType

import pytest

from tests.ci_web41 import source_companion

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "tests/test_current40_migration_logging.py": "tests/current41_migration_logging.py",
    "tests/test_ci_web39_postgres_release.py": "tests/current41_postgres_release.py",
    "tests/test_stripe_refund_ledger_author.py": "tests/current41_stripe_refund_ledger_author.py",
    "tests/test_stripe_refund_ledger_peer.py": "tests/current41_stripe_refund_ledger_peer.py",
    "tests/test_stripe_webhook_version_contract.py": "tests/current41_stripe_webhook_version_contract.py",
    "tests/test_quality_web39.py": "tests/test_current41_quality_companion.py",
}
PARENT_FIXTURES = {"tests/test_current39_apt_transition.py": "actual_inputs"}
PARENT_PROVIDER = "tests/ci_web41/native_parent_fixtures.py"
PARENT_PROVIDER_PIN = (4493, "ca6979db2aeb5b411db44bfa62a5671f38bb99c6796f58d36de926f1de9506af")
LEGACY_UNIT = "tests/test_ci_web37_pg_legacy.py"
LEGACY_PROVIDER = "tests/ci_web41/legacy_pg_unit_capsule.py"
LEGACY_PROVIDER_PIN = (30448, 'b13f4baaa993ca3222108f79b99a8839211c0199f0ae79bd817c8b131040cd61')


def legacy_collector(module_path, parent):
    """Authenticate the finite helper before delegating any original unit ID."""
    from tests.ci_image57 import authority

    path = authority.regular_file(ROOT / LEGACY_PROVIDER)
    before = path.stat()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(LEGACY_PROVIDER_PIN[0] + 1)
        finished = os.fstat(stream.fileno())
    after = path.stat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if (len({identity(item) for item in (before, opened, finished, after)}) != 1
            or before.st_ctime_ns != after.st_ctime_ns or opened.st_ctime_ns != finished.st_ctime_ns
            or (len(raw), hashlib.sha256(raw).hexdigest()) != LEGACY_PROVIDER_PIN):
        raise pytest.UsageError("The finite legacy unit capsule helper differs")
    name = "tests.ci_web41.legacy_pg_unit_capsule"
    code = compile(raw, str(path), "exec", dont_inherit=True)
    provider = sys.modules.get(name)
    if provider is None:
        provider = ModuleType(name)
        provider.__file__, provider.__package__ = str(path), "tests.ci_web41"
        exec(code, vars(provider))  # noqa: S102 -- complete finite helper source authenticated above
        sys.modules[name] = provider
    if Path(provider.__file__) != path:
        raise pytest.UsageError("The legacy unit capsule provider path differs")
    references = {reference.co_name: reference for reference in code.co_consts if isinstance(reference, CodeType)}
    def authenticate(value, reference):
        def filenames(reference):
            return (reference.co_filename, *(name for item in reference.co_consts if isinstance(item, CodeType)
                                             for name in filenames(item)))
        if (not isinstance(value, FunctionType) or value.__code__ != reference
                or any(name != str(path) for name in filenames(value.__code__))
                or value.__globals__ is not vars(provider)):
            raise pytest.UsageError("A legacy capsule provider function differs")
    for node in ast.parse(raw).body:
        if isinstance(node, ast.FunctionDef):
            authenticate(getattr(provider, node.name, None), references[node.name])
        elif isinstance(node, ast.ClassDef):
            value = getattr(provider, node.name, None)
            if not isinstance(value, type):
                raise pytest.UsageError("A legacy capsule provider function differs")
            methods = {item.co_name: item for item in references[node.name].co_consts if isinstance(item, CodeType)}
            for name, method in methods.items():
                authenticate(vars(value).get(name), method)
    return provider.collector(module_path, parent)


def clone_parent_fixture(original):
    from tests.ci_image57 import authority

    path = authority.regular_file(ROOT / PARENT_PROVIDER)
    raw = path.read_bytes()
    if (len(raw), hashlib.sha256(raw).hexdigest()) != PARENT_PROVIDER_PIN:
        raise pytest.UsageError("The finite historical native fixture provider source differs")
    provider = importlib.import_module("tests.ci_web41.native_parent_fixtures")
    if Path(provider.__file__) != path or provider.ROOT != ROOT:
        raise pytest.UsageError("The historical native fixture provider path differs")
    code = compile(raw, str(path), "exec", dont_inherit=True)
    for reference in code.co_consts:
        if not isinstance(reference, CodeType):
            continue
        function = getattr(provider, reference.co_name, None)
        if hasattr(function, "_get_wrapped_function"):
            function = function._get_wrapped_function()
        if (not isinstance(function, FunctionType) or function.__code__ != reference
                or function.__globals__ is not vars(provider)):
            raise pytest.UsageError("A historical native fixture provider CodeType or globals differs")
    return provider.clone_fixture(original)


def clone_source(original, current_path):
    namespace = ModuleType(original.__name__)
    namespace.__dict__.update(original.__dict__)
    namespace.__file__ = str(ROOT / current_path)
    source_companion.populate(namespace.__dict__, namespace.__file__)
    original_names = {name for name in vars(original) if name.startswith(("test_", "Test"))}
    current_names = {name for name in vars(namespace) if name.startswith(("test_", "Test"))}
    if not original_names or current_names != original_names:
        raise pytest.UsageError("A current41 source companion omitted or added a historical identity")
    # Pytest reports the original file/identity; the binding receipt separately
    # names the exact current41 compiled source and its authenticated edits.
    namespace.__file__ = original.__file__
    return namespace, {"module": original.__name__, "historical_test_names_retained": len(original_names),
                       "original_source_unmodified": True, "source_companion": current_path,
                       "validation_scope": "explicit_current41_revision_and_release_wiring"}


def install(namespace):
    previous = namespace["pytest_pycollect_makemodule"]

    class SourceModule(pytest.Module):
        def _getobj(self):
            original = super()._getobj()
            relative = self.path.relative_to(ROOT).as_posix()
            if relative in PARENT_FIXTURES:
                companion, receipt = clone_parent_fixture(original)
            else:
                companion, receipt = clone_source(original, SOURCES[relative])
            self.config._web41_bindings.append(receipt)
            return companion

    def pytest_pycollect_makemodule(module_path, parent):
        if parent.config.getoption("--web41-current-fixtures"):
            try:
                relative = module_path.relative_to(ROOT).as_posix()
            except ValueError:
                relative = None
            if relative == LEGACY_UNIT:
                return legacy_collector(module_path, parent)
            if relative in SOURCES or relative in PARENT_FIXTURES:
                return SourceModule.from_parent(parent, path=module_path)
        return previous(module_path, parent)

    namespace["pytest_pycollect_makemodule"] = pytest_pycollect_makemodule
