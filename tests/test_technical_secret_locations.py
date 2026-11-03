"""Exact two fingerprints; historical classifications and scanner stay intact."""
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import scan_secrets as original
from tests.ci_web39 import scan_secrets as prior_cli
from tests.ci_web41 import technical_secret_locations as subject

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def setup(tmp_path, name, frame):
    source = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
    if frame == subject.PINS[name][1]:
        source = source.replace(b"\n", b"\r\n")
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source)
    hashes = {name: hashlib.sha256(source).hexdigest()}
    span = frame["span"]
    item = dict(zip(("StartLine", "EndLine", "StartColumn", "EndColumn", "RuleID"), span, strict=True))
    item.update(Secret=object(), Match=object(), Line=object())
    adapter = subject.TechnicalLocations(SimpleNamespace(classify=lambda *_: None), tmp_path, hashes)
    return adapter, item, path, hashes


CASES = [(name, frame) for name, frames in subject.PINS.items() for frame in frames]


@pytest.mark.parametrize("name,frame", CASES)
def test_exact_measured_four_frames_classify_once_without_using_scanner_values(tmp_path, name, frame):
    adapter, item, _path, _hashes = setup(tmp_path, name, frame)
    result = adapter.classify(item, name)
    assert result == {"file": name, "line": frame["span"][0], "rule": frame["span"][4],
                      "file_sha256": frame["source_sha256"], "physical_line_sha256": frame["line_sha256"],
                      "start_column": frame["span"][2], "end_column": frame["span"][3], "reason": subject.REASON}
    assert adapter.classify(item, name) is None


@pytest.mark.parametrize("name,frame", CASES)
@pytest.mark.parametrize("fault", ["source", "inventory", "moved", "neighbor", "rule", "start", "end",
                                  "column", "bool", "multiline", "bom", "utf16", "mixed", "hardlink"])
def test_new_or_changed_locations_stay_blocking(tmp_path, name, frame, fault):
    adapter, item, path, hashes = setup(tmp_path, name, frame)
    if fault == "source":
        path.write_bytes(path.read_bytes() + b"# drift\n")
        hashes[name] = subject.digest(path.read_bytes())
    elif fault == "inventory":
        hashes[name] = "0" * 64
    elif fault == "moved":
        name = "unreviewed/" + name
        new = tmp_path / name
        new.parent.mkdir(parents=True, exist_ok=True)
        new.write_bytes(path.read_bytes())
        hashes[name] = subject.digest(new.read_bytes())
    elif fault == "neighbor":
        item["StartLine"] += 1
        item["EndLine"] += 1
    elif fault == "rule":
        item["RuleID"] = "unknown-rule"
    elif fault == "start":
        item["StartColumn"] -= 1
    elif fault == "end":
        item["EndColumn"] += 1
    elif fault == "column":
        item["StartColumn"] += 1
    elif fault == "bool":
        item["StartLine"] = True
    elif fault == "multiline":
        item["EndLine"] += 1
    elif fault == "hardlink":
        (tmp_path / "alias").hardlink_to(path)
    else:
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        if fault == "bom":
            raw = b"\xef\xbb\xbf" + raw
        elif fault == "utf16":
            raw = raw.decode().encode("utf16")
        else:
            raw = raw.replace(b"\n", b"\r\n", 1)
        path.write_bytes(raw)
        hashes[name] = subject.digest(raw)
    assert adapter.classify(item, name) is None


@pytest.mark.parametrize("name", ["Dockerfile", "runtime-source/technical-close-20261103/source-pins.json", "historical.py"])
def test_previous_result_and_identity_are_unchanged_even_at_owned_paths(name):
    result = {"unchanged": object()}
    calls = []
    previous = SimpleNamespace(classify=lambda item, path: calls.append((item, path)) or result)
    adapter = subject.TechnicalLocations(previous, ROOT, {})
    item = {"hostile": object()}
    assert adapter.classify(item, name) is result
    assert calls == [(item, name)]


def test_cli_retains_original_full_scan_code_and_only_private_loader_changes():
    before = dict(vars(original))
    previous = prior_cli.delegated_main()
    result = subject.delegated_main()
    assert result.__code__ is previous.__code__ is original.main.__code__
    assert result.__globals__ is not previous.__globals__
    assert [name for name in result.__globals__ if result.__globals__[name] is not previous.__globals__[name]] == [
        "load_reviewed_locations"]
    assert vars(original) == before


@pytest.mark.parametrize("name", list(subject.PARENTS))
def test_parent_source_tampering_rejects(tmp_path, name):
    for source in subject.PARENTS:
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / source).read_bytes())
    path = tmp_path / name
    path.write_bytes(path.read_bytes() + b"# unreviewed source\n")
    with pytest.raises(RuntimeError, match="output withheld"):
        subject.authenticate_parents(tmp_path)


def test_bounded_read_rejects_excess_before_open(tmp_path, monkeypatch):
    path = tmp_path / "large"
    path.write_bytes(b"12345")
    calls = []
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(RuntimeError, match="output withheld"):
        subject.bounded(tmp_path, "large", 4)
    assert calls == []


def test_source_frames_are_exactly_two_paths_with_both_measured_transports():
    assert set(subject.PINS) == {"Dockerfile", "runtime-source/technical-close-20261103/source-pins.json"}
    assert all(len(frames) == 2 and frames[0]["span"] == frames[1]["span"] for frames in subject.PINS.values())


def test_changed_parent_is_rejected_before_import_in_fresh_process(tmp_path):
    root = tmp_path / "isolated-source"
    names = [*subject.PARENTS, "tests/__init__.py", "tests/ci_web41/__init__.py",
             "tests/ci_web41/technical_secret_locations.py"]
    for name in names:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    sentinel = root / "IMPORT_EXECUTED"
    parent = root / "tests/ci_web39/current_secret_locations.py"
    parent.write_text("from pathlib import Path\nPath(" + repr(str(sentinel))
                      + ").write_text('unsafe import executed')\n", encoding="utf8")
    program = ("import sys\nfrom pathlib import Path\nsys.path.insert(0," + repr(str(root)) + ")\n"
               "from tests.ci_web41 import technical_secret_locations as s\n"
               "try:\n s.authenticate_parents(Path(" + repr(str(root)) + "))\n"
               "except RuntimeError:\n print('REJECTED_BEFORE_IMPORT')\n")
    result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", "-c", program],
                            cwd=root, env=os.environ.copy(), capture_output=True, timeout=15, check=False)
    assert result.returncode == 0 and result.stdout.strip() == b"REJECTED_BEFORE_IMPORT"
    assert result.stderr == b"" and not sentinel.exists()
