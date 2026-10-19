"""Single-volume transition adapter; the deployment must mount/back up its root.

New objects publish atomically with an exclusive hard link on one filesystem.
No fallback writes to a container source tree or public static directory.
"""
import os
from pathlib import Path
import tempfile

from web.storage.objects import (
    ObjectAccessDenied, ObjectConflict, ObjectDescriptor, ObjectUnavailable,
    authorize, verify,
)


class LocalObjectStore:
    """An unavailable PUT may already be published; retain its descriptor.

    Retrying identical metadata/bytes is idempotent. A cleanup failure leaves a
    private .pending orphan for reconciliation; it never overwrites the final
    object or implies a successful database reference change.
    """
    def __init__(self, root: Path):
        if not Path(root).is_absolute():
            raise ValueError("Object storage requires an explicit absolute root")
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, descriptor: ObjectDescriptor, owner_id: str) -> Path:
        authorize(descriptor, owner_id)
        target = self.root / descriptor.key
        for parent in (*target.parents, target):
            if parent == self.root:
                continue
            if parent.is_symlink():
                raise ObjectAccessDenied("Object storage symlinks are forbidden")
        if not target.resolve().is_relative_to(self.root):
            raise ObjectAccessDenied("Object outside storage root")
        return target

    def put(self, descriptor: ObjectDescriptor, data: bytes, *, owner_id: str) -> None:
        target = self._path(descriptor, owner_id)
        verify(descriptor, data)
        temporary = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".pending-", delete=False) as output:
                temporary = Path(output.name)
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError:
                try:
                    self.read(descriptor, owner_id=owner_id)
                except ObjectUnavailable:
                    raise ObjectConflict("Immutable private object differs") from None
        except ObjectUnavailable:
            raise
        except OSError:
            raise ObjectUnavailable("Private object write unavailable") from None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    raise ObjectUnavailable("Private object cleanup unavailable") from None

    def read(self, descriptor: ObjectDescriptor, *, owner_id: str) -> bytes:
        target = self._path(descriptor, owner_id)
        try:
            with target.open("rb") as source:
                data = source.read(descriptor.byte_size + 1)
        except OSError:
            raise ObjectUnavailable("Private object read unavailable") from None
        return verify(descriptor, data)

    def delete(self, descriptor: ObjectDescriptor, *, owner_id: str) -> None:
        target = self._path(descriptor, owner_id)
        try:
            target.unlink(missing_ok=True)
        except OSError:
            raise ObjectUnavailable("Private object deletion unavailable") from None
