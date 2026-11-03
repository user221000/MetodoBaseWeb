"""Authenticated APT-stage fixture for unchanged historical assertions.

The complete current19 source is authenticated before its finite inverses.
Only the original module's actual_inputs fixture is replaced in a separate
namespace. No historical test object, global namespace or source is changed.
These source controls make no build, runtime, CA-store or SCA acceptance claim.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from types import CodeType, FunctionType, ModuleType

import pytest

from tests.ci_image57 import authority, context, production_child, technical_child

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = "tests/test_current39_apt_transition.py"
ORIGINAL_MODULE = "tests.test_current39_apt_transition"
SOURCE_FRAMES = {
    (19856, "e71c65f1af0db49067ad8ae0382d254d35574b966059d827619dc532e1620433"),
    (20239, "df4432a96351b68453837b216eb1b004c9b6150c9aa3766ad9bbe21c63caf0fd"),
}
SOURCE_BLOB = "d0a6f26f47655c475016e7d0181a12f7e9215866"


def apt_child_inputs(root):
    """Recover the exact twelve-input APT child from all19 current inputs."""
    actual = technical_child.read_payloads(root)
    production = technical_child.inverse(actual)
    original = context.json_object(authority.raw("container-inputs.json.RAW"))["candidate_files"]
    apt = {name: production[name] for name in original}
    apt["Dockerfile"] = production_child.inverse(apt["Dockerfile"])
    _parent, transition = context.native_parent_payloads(apt)
    if transition != context.native_transition():
        raise ValueError("The authenticated historical APT fixture transition differs")
    return apt


@pytest.fixture(scope="module")
def actual_inputs():
    return apt_child_inputs(ROOT)


def authenticate_original(original):
    """Authenticate whole source and every original function CodeType."""
    path = authority.regular_file(ROOT / ORIGINAL)
    if (original.__name__ != ORIGINAL_MODULE or Path(original.__file__) != path
            or original.ROOT != ROOT):
        raise ValueError("The historical APT fixture module or path differs")
    raw = path.read_bytes()
    if (len(raw), hashlib.sha256(raw).hexdigest()) not in SOURCE_FRAMES:
        raise ValueError("The historical APT source frame differs")
    lf = raw.replace(b"\r\n", b"\n")
    blob = hashlib.sha1(b"blob " + str(len(lf)).encode() + b"\0" + lf,
                        usedforsecurity=False).hexdigest()
    if blob != SOURCE_BLOB:
        raise ValueError("The historical APT Git source differs")
    tree = ast.parse(raw, filename=str(path))
    from _pytest.assertion.rewrite import AssertionRewritingHook, rewrite_asserts
    if isinstance(original.__loader__, AssertionRewritingHook):
        rewrite_asserts(tree, raw, str(path), original.__loader__.config)
    code = compile(tree, str(path), "exec", dont_inherit=True)
    expected = {value.co_name: value for value in code.co_consts if isinstance(value, CodeType)}
    for name, reference in expected.items():
        value = getattr(original, name, None)
        if hasattr(value, "_get_wrapped_function"):
            value = value._get_wrapped_function()
        if (not isinstance(value, FunctionType) or value.__code__ != reference
                or value.__globals__ is not vars(original)):
            raise ValueError("A historical APT function CodeType or globals differs")
    names = {name for name in vars(original) if name.startswith(("test_", "Test"))}
    if names != {name for name in expected if name.startswith(("test_", "Test"))}:
        raise ValueError("The historical APT test identity inventory differs")


def clone_fixture(original):
    authenticate_original(original)
    companion = ModuleType(original.__name__)
    companion.__dict__.update(vars(original))
    companion.actual_inputs = actual_inputs
    tests = {name: value for name, value in vars(original).items()
             if name.startswith(("test_", "Test"))}
    if not tests or any(vars(companion)[name] is not value for name, value in tests.items()):
        raise ValueError("A historical APT test object was changed or omitted")
    return companion, {
        "module": original.__name__, "historical_test_objects_identical": len(tests),
        "original_source_unmodified": True, "original_globals_unmodified": True,
        "fixture": "actual_inputs", "fixture_provider": __name__ + ".actual_inputs",
        "validation_scope": "authenticated_current19_to_historical_APT12_source_only",
    }
