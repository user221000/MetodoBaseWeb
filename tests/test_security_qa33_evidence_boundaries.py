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
