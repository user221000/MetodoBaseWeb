"""Reject incomplete, escaping or nonregular Docker source contexts offline."""
import pytest

from tests.ci_web37.image_context import copy_inputs, select_inputs


@pytest.mark.parametrize("source", ["runtime-source/expat-sec10", "runtime-source/expat-sec10/"])
def test_directory_copy_keeps_nested_inputs_without_accepting_a_neighbor_prefix(source):
    entries = {
        "runtime-source/expat-sec10/source-pins.json": ("a" * 40, "100644", b"blob"),
        "runtime-source/expat-sec10/nested/patch": ("b" * 40, "100755", b"blob"),
        "runtime-source/expat-sec10-other/injected": ("c" * 40, "100644", b"blob"),
    }
    assert set(select_inputs(entries, {source})) == {
        "runtime-source/expat-sec10/source-pins.json", "runtime-source/expat-sec10/nested/patch"}


@pytest.mark.parametrize("source", ["../authority", "/authority", "a/../authority", "a//authority",
                                    "a/./authority", "*.py", "--chown=someone"])
def test_unreviewed_context_paths_and_copy_options_are_rejected(source):
    with pytest.raises(ValueError):
        copy_inputs(f"COPY {source} /app/\n".encode())


def test_a_missing_source_cannot_be_replaced_with_a_similarly_named_directory():
    with pytest.raises(ValueError, match="absent"):
        select_inputs({"web-old/file.py": ("a" * 40, "100644", b"blob")}, {"web"})


@pytest.mark.parametrize("mode", ["120000", "160000"])
def test_context_cannot_follow_a_git_symlink_or_submodule(mode):
    with pytest.raises(ValueError, match="regular"):
        select_inputs({"web/file": ("a" * 40, mode, b"blob")}, {"web"})
