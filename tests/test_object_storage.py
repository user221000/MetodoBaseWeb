"""Private volume objects survive adapter replacement and reject wrong owners."""
from dataclasses import replace
from pathlib import Path

import pytest

from web.storage.local import LocalObjectStore
from web.storage.objects import (
    MAX_OBJECT_BYTES, ObjectAccessDenied, ObjectConflict, ObjectUnavailable, describe,
)


@pytest.fixture
def artifact(tmp_path):
    data = b"%PDF-1.7\nsynthetic-private-plan\n%%EOF"
    return LocalObjectStore(tmp_path / "private-volume"), describe("gym-a", "plan_pdf", data, "application/pdf"), data


def test_object_survives_new_adapter_and_identical_retry_does_not_overwrite(artifact):
    store, descriptor, data = artifact
    store.put(descriptor, data, owner_id="gym-a")
    before = (store.root / descriptor.key).stat().st_mtime_ns
    store = LocalObjectStore(store.root)
    assert store.read(descriptor, owner_id="gym-a") == data
    store.put(descriptor, data, owner_id="gym-a")
    assert (store.root / descriptor.key).stat().st_mtime_ns == before
    assert not list(store.root.rglob(".pending-*"))


@pytest.mark.parametrize("operation", ["put", "read", "delete"])
def test_other_owner_cannot_access_or_delete_even_with_known_key(artifact, operation):
    store, descriptor, data = artifact
    store.put(descriptor, data, owner_id="gym-a")
    with pytest.raises(ObjectAccessDenied):
        if operation == "put":
            store.put(descriptor, data, owner_id="gym-b")
        else:
            getattr(store, operation)(descriptor, owner_id="gym-b")
    assert store.read(descriptor, owner_id="gym-a") == data


@pytest.mark.parametrize("key", ["../outside.pdf", "/absolute.pdf", "C:/outside.pdf", "v1/../../outside.pdf", "v1\\..\\outside.pdf"])
def test_database_key_tampering_never_becomes_a_local_path(artifact, key):
    store, descriptor, data = artifact
    with pytest.raises(ObjectAccessDenied):
        store.put(replace(descriptor, key=key), data, owner_id="gym-a")
    assert not list(store.root.rglob("*.pdf"))


def test_integrity_failure_never_returns_corrupted_document(artifact):
    store, descriptor, data = artifact
    store.put(descriptor, data, owner_id="gym-a")
    (store.root / descriptor.key).write_bytes(data.replace(b"synthetic", b"altered--"))
    with pytest.raises(ObjectUnavailable):
        store.read(descriptor, owner_id="gym-a")
    with pytest.raises(ObjectConflict):
        store.put(descriptor, data, owner_id="gym-a")


def test_atomic_publication_failure_leaves_no_document_or_tempfile(artifact, monkeypatch):
    store, descriptor, data = artifact
    def fail(*args):
        raise OSError("untrusted transport detail")
    monkeypatch.setattr("web.storage.local.os.link", fail)
    with pytest.raises(ObjectUnavailable) as error:
        store.put(descriptor, data, owner_id="gym-a")
    assert "untrusted" not in str(error.value)
    assert not (store.root / descriptor.key).exists()
    assert not list(store.root.rglob(".pending-*"))


def test_cleanup_failure_after_publication_preserves_idempotent_descriptor(artifact, monkeypatch):
    store, descriptor, data = artifact
    original_unlink = Path.unlink
    def fail_pending(path, *args, **kwargs):
        if path.name.startswith(".pending-"):
            raise OSError("synthetic-cleanup-unavailable")
        return original_unlink(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", fail_pending)
        with pytest.raises(ObjectUnavailable):
            store.put(descriptor, data, owner_id="gym-a")
    assert store.read(descriptor, owner_id="gym-a") == data
    store.put(descriptor, data, owner_id="gym-a")
    assert store.read(descriptor, owner_id="gym-a") == data
    assert len(list(store.root.rglob(".pending-*"))) == 1


@pytest.mark.parametrize("field,value", [("id", None), ("sha256", None), ("kind", []),
                                        ("content_type", []), ("key", None), ("byte_size", True)])
def test_corrupted_database_metadata_is_a_typed_access_denial(artifact, field, value):
    store, descriptor, _ = artifact
    with pytest.raises(ObjectAccessDenied):
        store.read(replace(descriptor, **{field: value}), owner_id="gym-a")


def test_delete_is_owner_scoped_and_idempotent(artifact):
    store, descriptor, data = artifact
    store.put(descriptor, data, owner_id="gym-a")
    store.delete(descriptor, owner_id="gym-a")
    store.delete(descriptor, owner_id="gym-a")
    with pytest.raises(ObjectUnavailable):
        store.read(descriptor, owner_id="gym-a")


def test_relative_storage_root_is_rejected():
    with pytest.raises(ValueError):
        LocalObjectStore(Path("web/static/uploads"))


@pytest.mark.parametrize("kind,content_type", [("plan_pdf", "text/html"), ("gym_logo", "image/svg+xml"), ("unknown", "image/png")])
def test_unsupported_types_do_not_create_metadata(kind, content_type):
    with pytest.raises(ValueError):
        describe("gym-a", kind, b"not-an-object", content_type)


@pytest.mark.parametrize("data", [b"", b"x" * (MAX_OBJECT_BYTES + 1)], ids=["empty", "oversized"])
def test_empty_or_oversized_data_is_rejected(data):
    with pytest.raises(ValueError):
        describe("gym-a", "plan_pdf", data, "application/pdf")


def test_symlink_cannot_redirect_a_private_document(artifact, tmp_path):
    store, descriptor, data = artifact
    destination = tmp_path / "outside"
    destination.mkdir()
    redirected = store.root / "v1"
    try:
        redirected.symlink_to(destination, target_is_directory=True)
    except OSError:
        pytest.skip("Host does not grant symlink creation; Linux CI must exercise this boundary")
    with pytest.raises(ObjectAccessDenied):
        store.put(descriptor, data, owner_id="gym-a")
    assert not list(destination.rglob("*.pdf"))
