"""Immutable private objects with explicit owner and integrity metadata.

The application persists ObjectDescriptor in PostgreSQL and authorizes the
principal before reading an object. Neither a key nor a local filename is an
authorization credential. Adapters never return public URLs or accept paths.
"""
from dataclasses import dataclass
import hashlib
import re
from typing import Protocol
from uuid import uuid4

MAX_OBJECT_BYTES = 64 * 1024 * 1024
CONTENT_TYPES = {
    "plan_pdf": {"application/pdf": "pdf"},
    "gym_logo": {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"},
}


class ObjectUnavailable(Exception):
    """Object missing, inaccessible or not verifiable; never exposes SDK detail."""


class ObjectConflict(ObjectUnavailable):
    """An immutable key already contains different bytes."""


class ObjectAccessDenied(ObjectUnavailable):
    """Descriptor or key does not belong to the explicitly authorized owner."""


@dataclass(frozen=True)
class ObjectDescriptor:
    id: str
    owner_id: str
    kind: str
    key: str
    content_type: str
    byte_size: int
    sha256: str


def owner_prefix(owner_id: str) -> str:
    if not isinstance(owner_id, str) or not owner_id or len(owner_id) > 36:
        raise ObjectAccessDenied("Invalid object owner")
    return "v1/" + hashlib.sha256(owner_id.encode("utf-8")).hexdigest() + "/"


def describe(owner_id: str, kind: str, data: bytes, content_type: str) -> ObjectDescriptor:
    prefix = owner_prefix(owner_id)
    if (not isinstance(kind, str) or not isinstance(content_type, str)
            or content_type not in CONTENT_TYPES.get(kind, {})):
        raise ValueError("Unsupported object content type")
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_OBJECT_BYTES:
        raise ValueError("Invalid object size")
    identity = uuid4().hex
    return ObjectDescriptor(identity, owner_id, kind,
        prefix + kind + "/" + identity + "." + CONTENT_TYPES[kind][content_type],
        content_type, len(data), hashlib.sha256(data).hexdigest())


def authorize(descriptor: ObjectDescriptor, owner_id: str) -> None:
    prefix = owner_prefix(owner_id)
    if (not isinstance(descriptor, ObjectDescriptor)
            or any(not isinstance(value, str) for value in (
                descriptor.id, descriptor.owner_id, descriptor.kind, descriptor.key,
                descriptor.content_type, descriptor.sha256))):
        raise ObjectAccessDenied("Invalid private object metadata")
    extension = CONTENT_TYPES.get(descriptor.kind, {}).get(descriptor.content_type)
    if (descriptor.owner_id != owner_id or extension is None
            or not re.fullmatch(r"[a-f0-9]{32}", descriptor.id)
            or descriptor.key != prefix + descriptor.kind + "/" + descriptor.id + "." + extension
            or type(descriptor.byte_size) is not int or not 0 < descriptor.byte_size <= MAX_OBJECT_BYTES
            or not re.fullmatch(r"[a-f0-9]{64}", descriptor.sha256)):
        raise ObjectAccessDenied("Invalid private object association")


def verify(descriptor: ObjectDescriptor, data: bytes) -> bytes:
    if len(data) != descriptor.byte_size or hashlib.sha256(data).hexdigest() != descriptor.sha256:
        raise ObjectUnavailable("Private object integrity check failed")
    return data


class ObjectStore(Protocol):
    """Only an already-authorized application case invokes these operations."""
    def put(self, descriptor: ObjectDescriptor, data: bytes, *, owner_id: str) -> None: ...
    def read(self, descriptor: ObjectDescriptor, *, owner_id: str) -> bytes: ...
    def delete(self, descriptor: ObjectDescriptor, *, owner_id: str) -> None: ...
