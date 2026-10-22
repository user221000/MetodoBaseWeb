"""Literal current companions for two finite obsolete helper/DTO seams."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PINS = {
    "tests/test_mfa31_primary_privacy.py": "2c33d96a49e96c75892f175e4b3d7418fe100bb7be0cf38bcbdd59242ac28937",
    "tests/test_retention_followup.py": "10d3e5a8529974e72425ec8d821bfd3a78994d0b4da61a60021b4b525ed9dec4",
}
RETENTION_REPLACEMENTS = (
    ("monkeypatch.setattr(route, 'get_followup',", "monkeypatch.setattr(route, 'dashboard',"),
    ("monkeypatch.setattr(route,'get_followup',", "monkeypatch.setattr(route,'dashboard',"),
    ("assert body['responsibility'] == 'not_recorded'", "assert body['responsibility'] == 'per_cause_tasks'"),
)


def namespace(name, module):
    original = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(original).hexdigest() != PINS[name]:
        raise ValueError("An original current37 helper/DTO companion source differs")
    source = original.decode("utf8")
    if name.endswith("test_retention_followup.py"):
        for before, after in RETENTION_REPLACEMENTS:
            if source.count(before) != 1 or after in source:
                raise ValueError("The reviewed retention seam/DTO expression differs")
            source = source.replace(before, after)
        inverse = source
        for before, after in reversed(RETENTION_REPLACEMENTS):
            inverse = inverse.replace(after, before)
        if inverse.encode() != original:
            raise ValueError("The finite retention seam/DTO companion cannot invert exactly")
    result = {"__file__": str(ROOT / name), "__name__": module}
    exec(compile(source, str(ROOT / name), "exec"), result)  # noqa: S102
    return result
