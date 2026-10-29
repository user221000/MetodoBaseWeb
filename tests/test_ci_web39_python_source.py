"""Broad39 source-input controls: real files, no download, compiler or process."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from tests.ci_web39 import run_web as runner


def test_explicit_actual_psf_source_matches_the_reviewed_native_recipe_and_is_quiet():
    # CI downloads this public input in an earlier hash-checking step. Local
    # invocations provide the same existing explicit E/F file, outside source.
    supplied = os.environ.get(runner.PYTHON_SOURCE_ENV)
    assert supplied, "Provide the explicit pinned PSF archive before source-input controls"
    environment = {runner.PYTHON_SOURCE_ENV: supplied}
    first = runner.python_source_archive(environment)
    second = runner.python_source_archive(environment)
    assert first == second
    assert first["sha256"] == runner.PYTHON_SOURCE_SHA256
    assert first["version"] == "3.12.15" and first["external_input"] is True
    assert first["bytes"] == Path(supplied).stat().st_size == 20829824


@pytest.mark.parametrize("environment", [{}, {runner.PYTHON_SOURCE_ENV: ""},
    {runner.PYTHON_SOURCE_ENV: "relative/Python-3.12.15.tar.xz"}])
def test_missing_or_relative_psf_source_never_falls_back_to_a_host_path(environment):
    with pytest.raises(ValueError):
        runner.python_source_archive(environment)


def test_missing_external_source_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        runner.python_source_archive({runner.PYTHON_SOURCE_ENV: str(tmp_path / "absent.tar.xz")})


def test_source_inside_deliverable_is_rejected_before_opening_or_hashing(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    root.mkdir()
    archive = root / "Python-3.12.15.tar.xz"
    archive.write_bytes(b"synthetic input must never become deliverable")
    monkeypatch.setattr(runner, "ROOT", root)
    with pytest.raises(ValueError, match="absolute external input"):
        runner.python_source_archive({runner.PYTHON_SOURCE_ENV: str(archive)})


def test_wrong_actual_archive_bytes_fail_the_literal_source_hash(tmp_path):
    archive = tmp_path / "wrong.tar.xz"
    archive.write_bytes(b"unreviewed PSF source")
    with pytest.raises(ValueError, match="SHA differs"):
        runner.python_source_archive({runner.PYTHON_SOURCE_ENV: str(archive)})


def test_directory_and_hardlinked_source_are_rejected_before_hashing(tmp_path):
    with pytest.raises(ValueError, match="plain unaliased"):
        runner.python_source_archive({runner.PYTHON_SOURCE_ENV: str(tmp_path)})
    original = tmp_path / "original.tar.xz"
    original.write_bytes(b"synthetic untrusted source")
    alias = tmp_path / "alias.tar.xz"
    os.link(original, alias)
    assert original.stat().st_nlink == alias.stat().st_nlink == 2
    with pytest.raises(ValueError, match="plain unaliased"):
        runner.python_source_archive({runner.PYTHON_SOURCE_ENV: str(alias)})


def test_input_change_during_stream_hashing_is_rejected(tmp_path, monkeypatch):
    archive = tmp_path / "changing.tar.xz"
    archive.write_bytes(b"synthetic initial source")
    original = hashlib.file_digest
    def changed(stream, algorithm):
        result = original(stream, algorithm)
        # Mutate only this synthetic fixture after its real stream read.
        with archive.open("ab") as output:
            output.write(b"unreviewed extension")
        return result
    monkeypatch.setattr(runner.hashlib, "file_digest", changed)
    with pytest.raises(ValueError, match="changed during validation"):
        runner.python_source_archive({runner.PYTHON_SOURCE_ENV: str(archive)})


def test_changed_recipe_cannot_authorize_an_arbitrary_input_hash(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    recipe = root / "runtime-source/expat-sec10/source-pins.json"
    recipe.parent.mkdir(parents=True)
    recipe.write_text(json.dumps({"python_version": "3.12.15", "psf_source_sha256": "0" * 64}), encoding="utf8")
    archive = tmp_path / "untrusted.tar.xz"
    archive.write_bytes(b"arbitrary source")
    monkeypatch.setattr(runner, "ROOT", root)
    with pytest.raises(ValueError, match="reviewed PSF source recipe differs"):
        runner.python_source_archive({runner.PYTHON_SOURCE_ENV: str(archive)})


@pytest.mark.parametrize("suite", ["serial", "parallel"])
def test_broad_gate_rejects_missing_input_before_collection_or_child_admission(tmp_path, monkeypatch, suite):
    def forbidden(*args, **kwargs):
        pytest.fail("Collection or a runtime child must not start with missing source input")
    monkeypatch.setattr(runner, "execute", forbidden)
    private = tmp_path / "no-payload"
    with pytest.raises(ValueError, match="explicit PSF source archive"):
        runner.pytest_gate(private, {}, suite)
    assert not private.exists()
