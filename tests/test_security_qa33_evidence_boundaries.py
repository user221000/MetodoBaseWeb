"""Actual private-boundary refusal and bounded diagnostic retention controls."""
import hashlib
from pathlib import Path
import tempfile

import pytest

from scripts import scan_secrets as scanner
from tests import qa33_safety_transport as transport


def test_safety_transport_preserves_every_code_object_assertion_and_marker():
    rows = transport.export()
    for name, copied in rows.items():
        original = getattr(transport.original, name)
        assert copied.__code__ is original.__code__
        assert copied.__defaults__ == original.__defaults__
        assert copied.__dict__ == original.__dict__
        assert copied.__globals__["_scenario"] is transport.scenario
        assert original.__globals__["_scenario"] is transport.original._scenario


def test_unknown_original_safety_bytes_cannot_enter_the_companion(tmp_path, monkeypatch):
    source = tmp_path / "changed.py"
    source.write_bytes(Path(transport.original.__file__).read_bytes() + b"# altered\n")
    monkeypatch.setattr(transport.original, "__file__", str(source))
    with pytest.raises(ValueError, match="original scanner safety source"):
        transport.export()


@pytest.mark.parametrize("kind", ["relative", "existing", "inside"])
def test_evidence_requires_a_fresh_absolute_external_directory(tmp_path, monkeypatch, kind):
    root = tmp_path / "source"
    root.mkdir()
    monkeypatch.setattr(scanner, "ROOT", root)
    requested = {"relative": Path("relative-private"), "existing": tmp_path,
                 "inside": root / "new-evidence"}[kind]
    before = set(tmp_path.iterdir())
    with pytest.raises(ValueError, match="fresh absolute path outside"):
        scanner._private_evidence(requested)
    assert set(tmp_path.iterdir()) == before


def test_diagnostic_limit_preserves_bounded_prefix_and_refuses_complete_capture(tmp_path):
    path = tmp_path / "diagnostics.private.log"
    raw = b"synthetic-private" * (scanner._CAPTURE_LIMIT // 8)
    assert scanner._capture(path, raw) is False
    assert path.stat().st_size == scanner._CAPTURE_LIMIT
    assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(raw[:scanner._CAPTURE_LIMIT]).digest()


def test_default_boundary_is_outside_source_and_before_any_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(scanner, "ROOT", tmp_path)
    private = scanner._private_evidence(None)
    assert private.parent == Path(tempfile.gettempdir()).resolve()
    assert private.name.startswith("metodobase-secrets-evidence-")
    assert not private.is_relative_to(tmp_path)
    assert not (private / "scan.stdout.private.log").exists()


def test_only_protected_User_and_SYSTEM_full_control_is_private():
    scanner._assert_windows_acl(0x9004, [(0, 3, 0x1F01FF, "S-1-5-21-123"),
        (0, 3, 0x1F01FF, "S-1-5-18")], "S-1-5-21-123")


@pytest.mark.parametrize("fault", ["unprotected", "no-DACL", "extra-principal", "wrong-user", "inherited",
    "deny-ACE", "insufficient-rights", "duplicate-user", "Boolean-mask", "float-flags", "Boolean-control"])
def test_inherited_broad_or_untyped_DACL_never_establishes_privacy(fault):
    control = 0x9004
    entries = [(0, 3, 0x1F01FF, "S-1-5-21-123"), (0, 3, 0x1F01FF, "S-1-5-18")]
    if fault == "unprotected":
        control = 0x8004
    elif fault == "no-DACL":
        control = 0x9000
    elif fault == "extra-principal":
        entries.append((0, 3, 0x1F01FF, "S-1-1-0"))
    elif fault == "wrong-user":
        entries[0] = (0, 3, 0x1F01FF, "S-1-5-21-456")
    elif fault == "inherited":
        entries[0] = (0, 0x13, 0x1F01FF, entries[0][3])
    elif fault == "deny-ACE":
        entries[0] = (1, 3, 0x1F01FF, entries[0][3])
    elif fault == "insufficient-rights":
        entries[0] = (0, 3, 0x120089, entries[0][3])
    elif fault == "duplicate-user":
        entries[1] = entries[0]
    elif fault == "Boolean-mask":
        entries[0] = (0, 3, True, entries[0][3])
    elif fault == "float-flags":
        entries[0] = (0, 3.0, 0x1F01FF, entries[0][3])
    else:
        control = True
    with pytest.raises(OSError):
        scanner._assert_windows_acl(control, entries, "S-1-5-21-123")


def test_failed_semantic_boundary_verification_writes_no_payload(tmp_path, monkeypatch):
    root = tmp_path / "source"
    root.mkdir()
    requested = tmp_path / "new-private"
    monkeypatch.setattr(scanner, "ROOT", root)

    def fail_boundary(*args):
        raise OSError("synthetic semantic ACL refusal")

    monkeypatch.setattr(scanner, "_verify_private_boundary", fail_boundary)
    with pytest.raises(RuntimeError, match="boundary failed; output withheld"):
        scanner._private_evidence(requested)
    assert requested.is_dir() and list(requested.iterdir()) == []
