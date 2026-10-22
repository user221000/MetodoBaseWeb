"""Counterexamples for explicit current fixtures without rewriting test bodies."""
import hashlib
from types import ModuleType

import pytest

from tests.ci_web37.composition import clone_namespace


def old_database():
    raise AssertionError("An old database fixture executed during inert composition")


def original_test():
    assert 1 + 1 == 2


def sample(tmp_path):
    path = tmp_path / "test_source.py"
    raw = b"# immutable original test module\n"
    path.write_bytes(raw)
    module = ModuleType("tests.example_companion")
    module.__file__ = str(path)
    module.followup_db = old_database
    module.test_business = original_test
    entry = {"source_sha256_LF": hashlib.sha256(raw).hexdigest(), "replacements": {
        "followup_db": {"module": __name__, "function": "old_database"}}}
    return module, entry


def test_companion_keeps_original_test_object_and_original_module_untouched(tmp_path):
    from tests.ci_web37.sqlite_fixtures import followup_db
    original, entry = sample(tmp_path)
    companion, receipt = clone_namespace(original, entry)
    assert companion is not original
    assert companion.test_business is original.test_business is original_test
    assert original.followup_db is old_database
    assert companion.followup_db is followup_db
    assert receipt["test_objects_identical"] == 1 and receipt["original_module_unmodified"] is True


def test_companion_authenticates_original_module_bytes_before_fixture_change(tmp_path):
    original, entry = sample(tmp_path)
    entry["source_sha256_LF"] = "0" * 64
    with pytest.raises(pytest.UsageError, match="original current37 companion"):
        clone_namespace(original, entry)
    assert original.followup_db is old_database


@pytest.mark.parametrize("key", ["module", "function"])
def test_companion_rejects_unreviewed_fixture_binding(tmp_path, key):
    original, entry = sample(tmp_path)
    entry["replacements"]["followup_db"][key] = "unexpected_provider"
    with pytest.raises(pytest.UsageError, match="historical fixture binding"):
        clone_namespace(original, entry)
    assert original.followup_db is old_database


def test_companion_never_approves_empty_original_test_module(tmp_path):
    original, entry = sample(tmp_path)
    del original.test_business
    with pytest.raises(pytest.UsageError, match="business test object"):
        clone_namespace(original, entry)


def test_selected_alias_name_is_separate_from_original_provider_function(tmp_path):
    from tests.ci_web37.sqlite_fixtures import google_db
    original, entry = sample(tmp_path)
    original.google_db = original.followup_db
    del original.followup_db
    entry["replacements"]["google_db"] = entry["replacements"].pop("followup_db")
    companion, receipt = clone_namespace(original, entry)
    assert companion.google_db is google_db
    assert original.google_db is old_database
    assert receipt["fixture_bindings"][0]["name"] == "google_db"
