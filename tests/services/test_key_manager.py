import os

import pytest

from core.services.key_manager import KeyManager


def test_create_key_persists_file(tmp_path):
    km = KeyManager(key_path=tmp_path / "keys.json")
    info = km.create_key()
    assert info.key_b64
    assert (tmp_path / "keys.json").exists()


def test_load_key_missing_file(tmp_path):
    km = KeyManager(key_path=tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError):
        km.load_key()


def test_key_file_permissions_best_effort(tmp_path):
    km = KeyManager(key_path=tmp_path / "keys.json")
    km.create_key()
    try:
        mode = os.stat(tmp_path / "keys.json").st_mode & 0o777
        if os.name == "nt":
            # Windows chmod exposes only the read-only bit, not POSIX ACLs.
            # Verify usability here; this does not claim an ACL security test.
            assert os.access(tmp_path / "keys.json", os.R_OK)
            assert km.load_key().key_b64
        else:
            assert mode in {0o600, 0o644, 0o660}
    except OSError:
        pytest.skip("Permisos no disponibles en este entorno")
