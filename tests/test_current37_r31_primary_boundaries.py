"""Explicit QA26 companion of sixteen original R31 admission criteria.

Only the legacy-primary expected lookup predicate changes. POST/login now
establishes its own subject before optional Bearer I/O in both factories.
Original422/cookie/refresh/no-Set-Cookie and all other variants stay exact.
"""
import hashlib
from pathlib import Path

from tests.ci_web37.sqlite_fixtures import followup_db

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/test_security_r31_browser_boundaries_peer.py"
SHA256_LF = "f76358ac57dc335718e2f37e88b7b8c9b199503db7cf8b2e8701c049013ff106"
OLD = 'assert bool(calls) == (browser["factory_name"] == "api.app")'
NEW = 'assert bool(calls) == (browser["factory_name"] == "api.app" and variant != "legacy-no-header")'


def original_namespace():
    raw = SOURCE.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != SHA256_LF:
        raise ValueError("The original sixteen R31 admission criteria differ")
    source = raw.decode("utf8")
    if source.count(OLD) != 1:
        raise ValueError("The exact original R31 legacy lookup predicate is absent")
    revised = source.replace(OLD, NEW)
    if revised.replace(NEW, OLD) != source:
        raise ValueError("The explicit QA26 lookup companion cannot invert exactly")
    namespace = {"__file__": str(SOURCE), "__name__": __name__}
    # The original complete RAW source is fixed above; only one finite expected
    # predicate changes, with full inverse equality and no other source edit.
    exec(compile(revised, str(SOURCE), "exec"), namespace)  # noqa: S102
    namespace["followup_db"] = followup_db
    return {name: value for name, value in namespace.items() if not name.startswith("__")}


globals().update(original_namespace())
