"""Independent finite authority and actual no-repository portability review.

No compilation, installation, image, service or current runtime acceptance.
The isolated child deliberately has no application conftest, repository, Git
executable, network or subprocess transport; it runs the literal companion57.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import warnings
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from tests.ci_web37 import container_inputs, git_recipe

ROOT = Path(__file__).resolve().parents[1]
APPROVED = "34707350afcc810e546cbb668dd63089ec7982ae"
ORIGINAL_PEER = "23a5bb4637b7443c45342760914ce0887f98e4be"


def frame_records():
    with zipfile.ZipFile(git_recipe.FIXTURE) as archive:
        return [(row.filename, archive.read(row)) for row in archive.infolist()]


def zip_bytes(records, compression=zipfile.ZIP_STORED):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        for name, raw in records:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(name, raw)
    return output.getvalue()


def git_raw(kind, identifier):
    return subprocess.check_output(["git", "--no-replace-objects", "cat-file", kind,
                                    identifier], cwd=ROOT)


def test_all_twenty_one_object_frames_match_the_original_git_objects_without_import():
    raw = git_recipe.FIXTURE.read_bytes()
    assert len(raw) == 343384
    assert hashlib.sha256(raw).hexdigest() == (
        "62bf62f3dc5ec1be7d6abbe453b79b0004895d5df20943d3400be4aa24491d6b")
    records = frame_records()
    assert len(records) == 21
    for path, frame in records:
        header, separator, payload = frame.partition(b"\0")
        kind, space, size = header.partition(b" ")
        assert separator and space and size == str(len(payload)).encode()
        assert kind in {b"commit", b"tree", b"blob"}
        identifier = path.removeprefix("objects/")
        assert hashlib.sha1(frame, usedforsecurity=False).hexdigest() == identifier
        assert payload == git_raw(kind.decode(), identifier)


def test_original_peer_raw_is_the_complete_historical_source_with_declared_eol_only():
    raw = (ROOT/"tests/ci_web37/fixtures/container37-inputs-peer40.py.RAW").read_bytes()
    original = subprocess.check_output(["git", "show", ORIGINAL_PEER+
                                       ":tests/test_security_container37_inputs_peer.py"], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == (
        "1eb22aa94088334d12a202ca2376d7da0b5e566795b0cefd765be4b5b679f76e")
    assert raw.replace(b"\r\n", b"\n") == original.replace(b"\r\n", b"\n")


def test_all_twelve_candidate_inputs_remain_the_exact_approved_bytes():
    manifest = json.loads((ROOT/"tests/ci_web37/container-inputs.json").read_bytes())
    assert len(manifest["candidate_files"]) == 12
    for path, pin in manifest["candidate_files"].items():
        raw = (ROOT/path).read_bytes()
        approved = subprocess.check_output(["git", "show", APPROVED+":"+path], cwd=ROOT)
        assert raw == approved
        assert hashlib.sha256(raw).hexdigest() == pin["raw_sha256"]


@pytest.mark.parametrize("kind", ["deflated", "uppercase-oid", "signed-size", "many-records",
                                  "huge-object", "huge-fixture"])
def test_additional_unreviewed_archive_framing_is_rejected_before_authority(kind):
    records = frame_records()
    if kind == "uppercase-oid":
        path, frame = records[0]
        records[0] = (path.upper(), frame)
    elif kind == "signed-size":
        path, frame = records[0]
        header, _, payload = frame.partition(b"\0")
        records[0] = (path, header.replace(b" ", b" +", 1)+b"\0"+payload)
    elif kind == "many-records":
        records = [("objects/"+f"{i:040x}", b"blob 0\0") for i in range(101)]
    elif kind == "huge-object":
        payload = b"X"*(git_recipe.MAX_OBJECT+1)
        frame = b"blob "+str(len(payload)).encode()+b"\0"+payload
        records = [("objects/"+hashlib.sha1(frame, usedforsecurity=False).hexdigest(), frame)]
    raw = zip_bytes(records, zipfile.ZIP_DEFLATED if kind == "deflated" else zipfile.ZIP_STORED)
    if kind == "huge-fixture":
        raw += b"X"*(git_recipe.MAX_FIXTURE+1)
    with pytest.raises(ValueError):
        git_recipe.ObjectProof(raw).verify_routes()


@pytest.mark.parametrize("path", ["", "/Dockerfile", "Dockerfile/", "runtime-source\\expat-sec10",
                                  "runtime-source/./expat-sec10", "Dockerfile\0extra"])
def test_absolute_empty_backslash_and_ambiguous_declared_paths_are_not_authority(path):
    with pytest.raises(ValueError):
        git_recipe.load().resolve(git_recipe.NATIVE, path, "blob")


def copy_inputs(destination):
    manifest = json.loads((ROOT/"tests/ci_web37/container-inputs.json").read_bytes())
    for name in [*manifest["candidate_files"], "requirements_web.lock", "tests/ci_web37/container-inputs.json"]:
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    return manifest


@pytest.mark.parametrize("change", ["false-blob", "false-raw-sha", "missing-source", "extra-source"])
def test_source_pin_both_identities_and_finite_inventory_are_enforced(tmp_path, monkeypatch, change):
    manifest = copy_inputs(tmp_path)
    names = manifest["source_files"]
    if change == "false-blob":
        names["Dockerfile"]["blob"] = "0"*40
    elif change == "false-raw-sha":
        names["Dockerfile"]["raw_sha256"] = "0"*64
    elif change == "missing-source":
        names.pop("Dockerfile")
    else:
        names["unreviewed-native-file"] = names["Dockerfile"]
    (tmp_path/"tests/ci_web37/container-inputs.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(container_inputs, "ROOT", tmp_path)
    with pytest.raises(ValueError):
        container_inputs.verify()


@pytest.mark.parametrize("change", ["changed-byte", "missing-file", "added-file", "renamed-file"])
def test_historical33_tree_comparison_rejects_file_and_inventory_drift(tmp_path, change):
    shutil.copytree(ROOT/"tests/ci_google33", tmp_path/"tests/ci_google33",
                    ignore=shutil.ignore_patterns("__pycache__"))
    target = tmp_path/"tests/ci_google33/publish.py"
    if change == "changed-byte":
        target.write_bytes(target.read_bytes()+b"\n# unreviewed bytes\n")
    elif change == "missing-file":
        target.unlink()
    elif change == "renamed-file":
        target.rename(target.with_name("renamed.py"))
    else:
        target.with_name("unreviewed.py").write_bytes(b"unreviewed")
    with pytest.raises(ValueError):
        git_recipe.require_historical33_unchanged(tmp_path, git_recipe.load())


def test_historical33_bytecode_cache_is_not_mistaken_for_a_source_file(tmp_path):
    shutil.copytree(ROOT/"tests/ci_google33", tmp_path/"tests/ci_google33",
                    ignore=shutil.ignore_patterns("__pycache__"))
    cache = tmp_path/"tests/ci_google33/__pycache__/synthetic.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"declared non-source bytecode artifact")
    git_recipe.require_historical33_unchanged(tmp_path, git_recipe.load())


def test_literal_companion57_runs_in_a_new_tree_without_git_repository_or_child_transport(tmp_path):
    fresh = tmp_path/"portable-source"
    fresh.mkdir()
    manifest = copy_inputs(fresh)
    support = ["tests/__init__.py", "tests/ci_web37/__init__.py",
               "tests/ci_web37/git_recipe.py", "tests/ci_web37/container_inputs.py",
               "tests/ci_web37/container_peer_portable.py",
               "tests/ci_web37/fixtures/native-recipe72-objects.zip",
               "tests/ci_web37/fixtures/container37-inputs-peer40.py.RAW",
               "tests/test_security_container37_extras_peer.py",
               "tests/test_security_container37_portable_peer.py",
               "tests/test_ci_web37_git_recipe.py"]
    for name in support:
        target = fresh/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    shutil.copytree(ROOT/"tests/ci_google33", fresh/"tests/ci_google33",
                    ignore=shutil.ignore_patterns("__pycache__"))
    assert not list(fresh.rglob(".git")) and not (fresh/"conftest.py").exists()
    expected = {p.relative_to(fresh).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in fresh.rglob("*") if p.is_file()}
    archive = Path(os.environ["METODOBASE_TEST_PYTHON_SOURCE_ARCHIVE"])
    assert archive.is_absolute() and archive.is_file()
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ}
    environment.update({"PATH": str(tmp_path/"no-executables"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
                        "METODOBASE_TEST_PYTHON_SOURCE_ARCHIVE": str(archive)})
    journal = tmp_path/"child-junit.RAW.xml"
    bootstrap = '''import os, pathlib, shutil, sys
assert not pathlib.Path('.git').exists() and shutil.which('git') is None
blocked=[]
def guard(event,args):
    if event in {'subprocess.Popen','os.system','os.exec','os.posix_spawn','socket.connect','socket.bind','socket.getaddrinfo'}:
        blocked.append(event)
        raise RuntimeError('Forbidden portability review transport')
sys.addaudithook(guard)
import pytest
code=pytest.main(['-q','-p','no:cacheprovider','--tb=short','--junitxml='+sys.argv[1],
                 'tests/test_ci_web37_git_recipe.py','tests/test_security_container37_portable_peer.py'])
assert blocked==[], 'An undeclared transport was attempted'
sys.exit(code)
'''
    (tmp_path/"bootstrap.executed.RAW.py").write_text(bootstrap)
    process = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", bootstrap, str(journal)],
                             check=False, cwd=fresh, env=environment, capture_output=True, timeout=120)
    (tmp_path/"child-stdout.RAW").write_bytes(process.stdout)
    (tmp_path/"child-stderr.RAW").write_bytes(process.stderr)
    assert process.returncode == 0
    cases = ET.fromstring(journal.read_bytes()).findall(".//testcase")
    assert len(cases) == 57
    assert not any(row.find(tag) is not None for row in cases for tag in ("failure", "error", "skipped"))
    actual = {name: hashlib.sha256((fresh/name).read_bytes()).hexdigest() for name in expected}
    assert actual == expected
    assert len(manifest["candidate_files"]) == 12 and not list(fresh.rglob(".git"))
