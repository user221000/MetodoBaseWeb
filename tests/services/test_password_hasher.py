import pytest

from core.services.password_hasher import PasswordHasher, PasswordPolicy


def test_hash_and_verify_strong_password():
    hasher = PasswordHasher()
    pw = "Str0ng!Passw0rd"
    h = hasher.hash_password(pw)
    assert hasher.verify_password(pw, h) is True


def test_rejects_weak_password():
    hasher = PasswordHasher(policy=PasswordPolicy(min_length=12))
    with pytest.raises(ValueError):
        hasher.hash_password("weakpass")


def test_rejects_double_hash():
    hasher = PasswordHasher()
    h = hasher.hash_password("Str0ng!Passw0rd")
    with pytest.raises(ValueError):
        hasher.hash_password(h)
