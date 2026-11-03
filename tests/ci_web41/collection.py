"""Six explicit source companions retain all historical collection identities.

The logging contract's revision literal and the release wiring now target41.
The old source and its plain historical RED remain reproducible unchanged.
Every original test name and parametrization remains in the current companion.
"""
import ast
import builtins
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
LEGACY_PROVIDER_PIN = (34313, 'd39464a30a56cc2b1b26164820b348de4e7fe95c7a1a4e9c35f9f1bd173172f0')
PG_CONSUMERS = {
    "tests/test_ci_web37_pg_lease.py", "tests/test_ci_web37_pg_qa_uuid_budget.py",
    "tests/test_ci_web37_pg_r24_witness.py",
}
PG_CONSUMER_PROVIDER = "tests/ci_web41/pg_legacy_consumer_inputs.py"
PG_CONSUMER_PROVIDER_PIN = (23603, '6dda20bcc5d3831b3143a54ef8d2acce725e3397df4dfffc6289a43a4f23ae52')


def finite_provider(relative, pin, name):
    """Authenticate the complete finite provider before dispatching originals."""
    from tests.ci_image57 import authority

    path = authority.regular_file(ROOT / relative)
    before = path.stat()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(pin[0] + 1)
        finished = os.fstat(stream.fileno())
    after = path.stat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if (len({identity(item) for item in (before, opened, finished, after)}) != 1
            or before.st_ctime_ns != after.st_ctime_ns or opened.st_ctime_ns != finished.st_ctime_ns
            or (len(raw), hashlib.sha256(raw).hexdigest()) != pin):
        raise pytest.UsageError("The finite legacy unit capsule helper differs")
    code = compile(raw, str(path), "exec", dont_inherit=True)
    provider = sys.modules.get(name)
    if provider is None:
        provider = ModuleType(name)
        provider.__file__, provider.__package__ = str(path), "tests.ci_web41"
        exec(code, vars(provider))  # noqa: S102 -- complete finite helper source authenticated above
        sys.modules[name] = provider
    if Path(provider.__file__) != path:
        raise pytest.UsageError("The legacy unit capsule provider path differs")
    if vars(provider).get("__builtins__") is not builtins and vars(provider).get("__builtins__") is not vars(builtins):
        raise pytest.UsageError("A finite provider builtins binding differs")
    for node in ast.parse(raw).body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)) or isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue
        for alias in node.names:
            if isinstance(node, ast.Import):
                key = alias.asname or alias.name.split(".")[0]
                expected = importlib.import_module(alias.name if alias.asname else key)
            else:
                key = alias.asname or alias.name
                package = importlib.import_module(node.module)
                expected = getattr(package, alias.name, None)
                if expected is None:
                    expected = importlib.import_module(node.module + "." + alias.name)
            if vars(provider).get(key) is not expected:
                raise pytest.UsageError("A finite provider canonical import binding differs")
    references = {reference.co_name: reference for reference in code.co_consts if isinstance(reference, CodeType)}
    def authenticate(value, reference):
        def filenames(reference):
            return (reference.co_filename, *(name for item in reference.co_consts if isinstance(item, CodeType)
                                             for name in filenames(item)))
        if (not isinstance(value, FunctionType) or value.__code__ != reference
                or any(name != str(path) for name in filenames(value.__code__))
                or value.__globals__ is not vars(provider) or value.__builtins__ is not vars(builtins)):
            raise pytest.UsageError("A legacy capsule provider function differs")
    for node in ast.parse(raw).body:
        if isinstance(node, ast.FunctionDef):
            authenticate(getattr(provider, node.name, None), references[node.name])
        elif isinstance(node, ast.ClassDef):
            value = getattr(provider, node.name, None)
            if not isinstance(value, type):
                raise pytest.UsageError("A legacy capsule provider function differs")
            methods = {item.co_name: item for item in references[node.name].co_consts if isinstance(item, CodeType)}
            for method_name, method in methods.items():
                authenticate(vars(value).get(method_name), method)
    return provider, raw


def legacy_collector(module_path, parent):
    provider, _raw = finite_provider(LEGACY_PROVIDER, LEGACY_PROVIDER_PIN, "tests.ci_web41.legacy_pg_unit_capsule")
    return provider.collector(module_path, parent)


def clone_pg_consumer(original):
    capsule, _raw = finite_provider(LEGACY_PROVIDER, LEGACY_PROVIDER_PIN, "tests.ci_web41.legacy_pg_unit_capsule")
    provider, raw = finite_provider(PG_CONSUMER_PROVIDER, PG_CONSUMER_PROVIDER_PIN, "tests.ci_web41.pg_legacy_consumer_inputs")
    assignments = {node.targets[0].id: ast.literal_eval(node.value) for node in ast.parse(raw).body
                   if isinstance(node, ast.Assign) and len(node.targets) == 1
                   and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"PINS", "CONSUMERS", "PYTEST_REWRITE_PIN"}}
    if (provider.ROOT != ROOT or provider.capsule is not capsule
            or provider.PINS != assignments["PINS"] or provider.CONSUMERS != assignments["CONSUMERS"]
            or provider.PYTEST_REWRITE_PIN != assignments["PYTEST_REWRITE_PIN"]):
        raise pytest.UsageError("The finite historical PG consumer provider constants differ")
    return provider.clone_inputs(original)


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
            if relative in PG_CONSUMERS:
                companion, receipt = clone_pg_consumer(original)
            elif relative in PARENT_FIXTURES:
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
            if relative in SOURCES or relative in PARENT_FIXTURES or relative in PG_CONSUMERS:
                return SourceModule.from_parent(parent, path=module_path)
        return previous(module_path, parent)

    namespace["pytest_pycollect_makemodule"] = pytest_pycollect_makemodule
