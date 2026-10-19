"""Canonical, account/profile-bound history positions. A cursor grants no authority."""
import base64
from datetime import datetime
import hashlib
import hmac
import json
import re

MAX_CURSOR_LENGTH = 180


def _pack(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _signature(payload: bytes, secret: str, subject: str, profile: str) -> bytes:
    if not isinstance(secret, str) or not secret:
        raise RuntimeError('History signing configuration is unavailable')
    binding = json.dumps(['personal-history:v1', subject, profile], separators=(',', ':')).encode('utf8')
    return hmac.new(secret.encode('utf8'), binding + b'\0' + payload, hashlib.sha256).digest()


def encode_position(stamp: datetime | None, identity: int, *, secret: str, subject: str, profile: str) -> str:
    if stamp is not None and stamp.tzinfo is not None:
        raise ValueError('Expected the stored UTC-naive timestamp')
    payload = json.dumps([1, stamp.isoformat(timespec='microseconds') if stamp is not None else None, identity], separators=(',', ':')).encode('ascii')
    return _pack(payload) + '.' + _pack(_signature(payload, secret, subject, profile))


def decode_position(cursor: str, *, secret: str, subject: str, profile: str) -> tuple[datetime | None, int]:
    # Bound the input before splitting, decoding, signing or parsing it.
    if not isinstance(cursor, str) or not 1 <= len(cursor) <= MAX_CURSOR_LENGTH:
        raise ValueError('Invalid history cursor')
    parts = cursor.split('.')
    if len(parts) != 2 or any(not re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in parts):
        raise ValueError('Invalid history cursor')
    try:
        decoded = [base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True) for value in parts]
        payload, signature = decoded
        if any(_pack(raw) != value for raw, value in zip(decoded, parts)) or not hmac.compare_digest(signature, _signature(payload, secret, subject, profile)):
            raise ValueError('Invalid history cursor')
        value = json.loads(payload)
        if not isinstance(value, list) or len(value) != 3 or type(value[0]) is not int or value[0] != 1:
            raise ValueError('Invalid history cursor')
        stamp, identity = value[1:]
        if type(identity) is not int or not 1 <= identity <= 2147483647:
            raise ValueError('Invalid history cursor')
        if stamp is not None:
            if not isinstance(stamp, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}', stamp):
                raise ValueError('Invalid history cursor')
            stamp = datetime.fromisoformat(stamp)
        canonical = json.dumps([1, stamp.isoformat(timespec='microseconds') if stamp is not None else None, identity], separators=(',', ':')).encode('ascii')
        if canonical != payload:
            raise ValueError('Invalid history cursor')
        return stamp, identity
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise ValueError('Invalid history cursor') from error
