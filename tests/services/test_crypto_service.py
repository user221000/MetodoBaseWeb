import pytest

from core.services.crypto_service import CryptoService
from core.services.key_manager import KeyManager


def test_encrypt_decrypt_roundtrip(tmp_path):
    km = KeyManager(key_path=tmp_path / "keys.json")
    km.create_key()
    crypto = CryptoService(km)

    token = crypto.encrypt("email@dominio.com")
    assert crypto.decrypt(token) == "email@dominio.com"


def test_decrypt_with_wrong_key_fails(tmp_path):
    km_a = KeyManager(key_path=tmp_path / "a.json")
    km_b = KeyManager(key_path=tmp_path / "b.json")
    km_a.create_key()
    km_b.create_key()

    token = CryptoService(km_a).encrypt("secreto")
    with pytest.raises(ValueError):
        CryptoService(km_b).decrypt(token)


def test_rotation_allows_previous_key(tmp_path):
    km = KeyManager(key_path=tmp_path / "keys.json")
    km.create_key()
    crypto = CryptoService(km)

    token = crypto.encrypt("dato")
    km.rotate_key()

    assert crypto.decrypt(token) == "dato"
