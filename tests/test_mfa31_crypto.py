import base64
import pytest

from web.services.mfa_crypto import decrypt, encrypt, key_bytes, totp


@pytest.mark.parametrize("timestamp,expected", [(59,"94287082"),(1111111109,"07081804"),
    (1111111111,"14050471"),(1234567890,"89005924"),(2000000000,"69279037"),
    (20000000000,"65353130")])
def test_rfc6238_sha1_vectors(timestamp, expected):
    assert totp(b"12345678901234567890", timestamp // 30, digits=8) == expected


@pytest.mark.parametrize("counter,expected", list(enumerate(["755224","287082","359152","969429","338314","254676","287922","162583","399871","520489"])))
def test_rfc4226_vectors(counter, expected):
    assert totp(b"12345678901234567890", counter) == expected


def test_ciphertext_binds_owner_generation_and_separate_key():
    secret = b"synthetic-seed-20byte"
    key = key_bytes(base64.urlsafe_b64encode(b"x" * 32).decode())
    first = encrypt(secret, key, b"owner-a:1")
    assert first != encrypt(secret, key, b"owner-a:1")
    assert decrypt(first, key, b"owner-a:1") == secret
    for other_key, aad in [(b"y" * 32,b"owner-a:1"),(key,b"owner-b:1"),(key,b"owner-a:2")]:
        with pytest.raises(Exception): decrypt(first, other_key, aad)


@pytest.mark.parametrize("value", ["", "development", "x"*32, "!"*43, base64.urlsafe_b64encode(b"x"*31).decode()])
def test_no_default_or_malformed_encryption_key(value):
    with pytest.raises(ValueError): key_bytes(value)
