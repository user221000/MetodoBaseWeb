"""Load only finite, whole-source-authenticated current41 companions.

The source39 bytes and their accepted LF/CRLF frames are explicit inputs. Each
literal edit has an exact count and the complete resulting source has a pin.
Neither historical modules nor their globals are patched in place.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = "tests/ci_web41/source-companions.json"
CATALOGUE_SHA256 = "3286b85b36440798fcd7e2e2ba8d00decbb363b2ab988d57bc9210dfb199eff3"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def specification():
    path = ROOT / CATALOGUE
    raw = path.read_bytes()
    if digest(raw) != CATALOGUE_SHA256:
        raise ValueError("The finite current41 source companion catalogue differs")
    result = json.loads(raw)
    if (set(result) != {"schema", "revision", "entries"}
            or result["schema"] != "finite-authenticated-current41-source-companions-v1"
            or result["revision"] != "20261102_payment_refund_facts"
            or not isinstance(result["entries"], dict)):
        raise ValueError("The current41 source companion contract differs")
    return result


def rewrite(raw, entry):
    """Reject any unreviewed byte, transport, count or resulting source."""
    frames = entry["original_frames"]
    if not any(type(frame["bytes"]) is int and len(raw) == frame["bytes"]
               and digest(raw) == frame["sha256"] for frame in frames):
        raise ValueError("A complete historical source frame differs")
    text = raw.replace(b"\r\n", b"\n").decode("utf8")
    if digest(text.encode("utf8")) != entry["original_sha256_LF"]:
        raise ValueError("The authenticated historical LF source differs")
    for edit in entry["literal_edits"]:
        old, new, count = edit["old"], edit["new"], edit["count"]
        if type(count) is not int or count <= 0 or not old or text.count(old) != count:
            raise ValueError("A finite current41 literal edit count differs")
        text = text.replace(old, new)
    result = text.encode("utf8")
    if digest(result) != entry["current_sha256_LF"]:
        raise ValueError("The complete resulting current41 source differs")
    return result


def source_bytes(name):
    """Expose exact compiled companion bytes for independent AST catalogues."""
    entry = specification()["entries"].get(name)
    if entry is None:
        raise ValueError("An explicit current41 source identity is required")
    path = ROOT / entry["original"]
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024
            or path.resolve(strict=True) != path.absolute()):
        raise ValueError("An authenticated historical input became an alias")
    return rewrite(path.read_bytes(), entry)


def populate(namespace, companion_file):
    """Populate this separate companion namespace, never the original module."""
    path = Path(companion_file)
    root = ROOT.resolve(strict=True)
    if path.resolve(strict=True) != path.absolute() or not path.is_relative_to(root):
        raise ValueError("An actual plain current41 wrapper path is required")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
        raise ValueError("A current41 companion wrapper became an alias")
    name = path.relative_to(root).as_posix()
    entry = specification()["entries"].get(name)
    if entry is None:
        raise ValueError("Only explicit current41 companions may load source")
    original = root / entry["original"]
    original_info = original.lstat()
    if (not stat.S_ISREG(original_info.st_mode)
            or getattr(original_info, "st_file_attributes", 0) & 1024
            or original.resolve(strict=True) != original.absolute()):
        raise ValueError("A historical source became an alias")
    code = rewrite(original.read_bytes(), entry)
    # The thin wrapper owns CLI dispatch so it can bind current41 Node gates
    # before calling the unchanged main. Importing either source never runs it.
    name_before = namespace["__name__"]
    if name_before == "__main__":
        namespace["__name__"] = name.removesuffix(".py").replace("/", ".")
    try:
        exec(compile(code, str(path), "exec", dont_inherit=True), namespace)
    finally:
        namespace["__name__"] = name_before
