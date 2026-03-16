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
        assert mode in {0o600, 0o644, 0o660}
    except OSError:
        pytest.skip("Permisos no disponibles en este entorno")
