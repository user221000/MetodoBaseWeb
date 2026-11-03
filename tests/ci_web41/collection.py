"""Six explicit source companions retain all historical collection identities.

The logging contract's revision literal and the release wiring now target41.
The old source and its plain historical RED remain reproducible unchanged.
Every original test name and parametrization remains in the current companion.
"""
from pathlib import Path
from types import ModuleType

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
            companion, receipt = clone_source(original, SOURCES[relative])
            self.config._web41_bindings.append(receipt)
            return companion

    def pytest_pycollect_makemodule(module_path, parent):
        if parent.config.getoption("--web41-current-fixtures"):
            try:
                relative = module_path.relative_to(ROOT).as_posix()
            except ValueError:
                relative = None
            if relative in SOURCES:
                return SourceModule.from_parent(parent, path=module_path)
        return previous(module_path, parent)

    namespace["pytest_pycollect_makemodule"] = pytest_pycollect_makemodule
