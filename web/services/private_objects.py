"""Private document intents and transactional references.

Publication crosses a database/provider boundary. Persist the immutable intent
before PUT, then let the consumer mark it ready and attach it in one database
transaction. An uncertain PUT or failed attachment leaves a pending intent;
there is no automatic deletion, refund-by-timeout or alternate destination.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from web.database.tenant_context import tenant_task
from web.storage.objects import ObjectDescriptor, ObjectUnavailable, authorize, describe
from web.storage.runtime import get_object_store, storage_configuration


def _backend():
    from web.settings import get_settings
    return storage_configuration(get_settings()).backend


def _descriptor(row):
    return ObjectDescriptor(row.id, row.gym_id, row.kind, row.key,
        row.content_type, row.byte_size, row.sha256)


@tenant_task("gym_id")
def publish_pending_object(gym_id: str, kind: str, data: bytes, content_type: str) -> ObjectDescriptor:
    """Persist an intent before external I/O; caller is already authorized."""
    from web.database.engine import get_engine
    from web.database.models import StoredObject

    descriptor = describe(gym_id, kind, data, content_type)
    if kind == "gym_logo":
        from web.constants import UPLOAD_MAX_LOGO_SIZE_BYTES
        if descriptor.byte_size > UPLOAD_MAX_LOGO_SIZE_BYTES:
            raise ValueError("Invalid logo size")
    store = get_object_store()
    with Session(get_engine()) as db:
        db.add(StoredObject(id=descriptor.id, gym_id=gym_id, kind=kind,
            key=descriptor.key, content_type=content_type, byte_size=descriptor.byte_size,
            sha256=descriptor.sha256, storage_backend=_backend(), status="pending"))
        db.commit()
    store.put(descriptor, data, owner_id=gym_id)
    return descriptor


def mark_object_ready(db, gym_id: str, descriptor: ObjectDescriptor, kind: str) -> str:
    """Stage readiness in the SAME transaction as the plan/profile reference."""
    from web.database.models import StoredObject

    authorize(descriptor, gym_id)
    row = db.execute(select(StoredObject).where(StoredObject.id == descriptor.id,
        StoredObject.gym_id == gym_id).with_for_update()).scalar_one_or_none()
    if (row is None or row.kind != kind or descriptor.kind != kind
            or _descriptor(row) != descriptor or row.storage_backend != _backend()
            or row.status not in {"pending", "ready"}):
        raise ObjectUnavailable("Private object association unavailable")
    row.status = "ready"
    db.flush()
    return row.id


def require_ready_object(db, gym_id: str, object_id: str, kind: str):
    """Validate owner, state and document kind before attaching a reference."""
    from web.database.models import StoredObject

    row = db.execute(select(StoredObject).where(StoredObject.id == object_id,
        StoredObject.gym_id == gym_id, StoredObject.kind == kind,
        StoredObject.status == "ready")).scalar_one_or_none()
    if row is None:
        raise ObjectUnavailable("Private object association unavailable")
    descriptor = _descriptor(row)
    authorize(descriptor, gym_id)
    if kind == "gym_logo":
        from web.constants import UPLOAD_MAX_LOGO_SIZE_BYTES
        if descriptor.byte_size > UPLOAD_MAX_LOGO_SIZE_BYTES:
            raise ObjectUnavailable("Private logo size unavailable")
    return row


def read_private_object(db, gym_id: str, object_id: str, kind: str) -> tuple[bytes, str]:
    """Read only a ready, correctly associated object from its selected backend."""
    row = require_ready_object(db, gym_id, object_id, kind)
    if row.storage_backend != _backend():
        raise ObjectUnavailable("Private object destination unavailable")
    content = get_object_store().read(_descriptor(row), owner_id=gym_id)
    return content, row.content_type
