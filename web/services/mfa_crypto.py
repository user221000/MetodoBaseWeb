"""RFC6238 primitives and authenticated at-rest protection, without side effects."""
import base64
import hashlib
import hmac
import re
import secrets
import struct

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def key_bytes(value: str) -> bytes:
    """Require an explicit independent 256-bit key; never derive a fallback."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}=?", value):
        raise ValueError("MFA encryption key unavailable")
    result = base64.urlsafe_b64decode(value.rstrip("=") + "=")
    if len(result) != 32:
        raise ValueError("MFA encryption key unavailable")
    return result


def encrypt(secret: bytes, key: bytes, aad: bytes) -> str:
    nonce = secrets.token_bytes(12)
    return base64.urlsafe_b64encode(nonce + AESGCM(key).encrypt(nonce, secret, aad)).decode("ascii")


def decrypt(ciphertext: str, key: bytes, aad: bytes) -> bytes:
    raw = base64.b64decode(ciphertext, altchars=b"-_", validate=True)
    if len(raw) < 29:
        raise ValueError("Invalid encrypted factor")
    return AESGCM(key).decrypt(raw[:12], raw[12:], aad)


def totp(secret: bytes, counter: int, *, digits: int = 6, algorithm: str = "sha1") -> str:
    """HOTP dynamic truncation. Runtime fixes SHA1/6/30s; options test RFC vectors."""
    digest = hmac.new(secret, struct.pack(">Q", counter), algorithm).digest()
    offset = digest[-1] & 15
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff
    return str(value % 10 ** digits).zfill(digits)


def opaque_digest(purpose: str, token: str) -> str:
    return hashlib.sha256(("mfa31:" + purpose + ":" + token).encode("ascii")).hexdigest()


def access_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()
