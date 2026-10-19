"""Database/provider boundary failures retain intents without false references."""
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from web.services import private_objects as service
from web.storage.local import LocalObjectStore
from web.storage.objects import ObjectAccessDenied, ObjectUnavailable, describe


@pytest.fixture
def storage(test_gym_user, tmp_path, monkeypatch):
    store = LocalObjectStore(tmp_path / "objects")
    monkeypatch.setattr(service, "get_object_store", lambda: store)
    return test_gym_user["id"], store


@pytest.mark.parametrize("published", [False, True])
def test_uncertain_put_keeps_committed_pending_intent_without_reference(storage, monkeypatch, published):
    from web.database.engine import get_engine
    from web.database.models import StoredObject, PlanGenerado
    owner, store = storage
    original = store.put
    observed = []
    def fail(descriptor, data, *, owner_id):
        # Another session sees the committed intent before provider I/O.
        with Session(get_engine()) as db:
            row = db.get(StoredObject, descriptor.id)
            assert row.status == "pending" and row.gym_id == owner
        observed.append(descriptor)
        if published:
            original(descriptor, data, owner_id=owner_id)
        raise ObjectUnavailable("Synthetic publication uncertainty")
    monkeypatch.setattr(store, "put", fail)
    with pytest.raises(ObjectUnavailable):
        service.publish_pending_object(owner, "plan_pdf", b"%PDF-synthetic", "application/pdf")
    with Session(get_engine()) as db:
        assert db.query(StoredObject).one().status == "pending"
        assert db.query(PlanGenerado).count() == 0
        with pytest.raises(ObjectUnavailable):
            service.read_private_object(db, owner, observed[0].id, "plan_pdf")
    if published:
        assert store.read(observed[0], owner_id=owner) == b"%PDF-synthetic"


def test_readiness_and_consumer_reference_rollback_together(storage):
    from web.database.engine import get_engine
    from web.database.models import Cliente, StoredObject, PlanGenerado
    from web.database import repository
    owner, store = storage
    descriptor = service.publish_pending_object(owner, "plan_pdf", b"%PDF-atomic", "application/pdf")
    with Session(get_engine()) as db:
        db.add(Cliente(id_cliente="synthetic-object-client", gym_id=owner, nombre="Synthetic"))
        db.commit()
        service.mark_object_ready(db, owner, descriptor, "plan_pdf")
        repository.registrar_plan(db, owner, "synthetic-object-client", {"pdf_object_id": descriptor.id})
        db.rollback()
    with Session(get_engine()) as db:
        assert db.get(StoredObject, descriptor.id).status == "pending"
        assert db.query(PlanGenerado).count() == 0
        assert db.query(Cliente).one().total_planes_generados == 0
        service.mark_object_ready(db, owner, descriptor, "plan_pdf")
        repository.registrar_plan(db, owner, "synthetic-object-client", {"pdf_object_id": descriptor.id})
        db.commit()
    # A reconstructed adapter reads the same verified bytes after process-local
    # state is discarded; this is not evidence of a mounted/container volume.
    reopened = LocalObjectStore(store.root)
    assert reopened.read(descriptor, owner_id=owner) == b"%PDF-atomic"
    with Session(get_engine()) as db:
        assert db.get(StoredObject, descriptor.id).status == "ready"
        assert db.query(PlanGenerado).one().pdf_object_id == descriptor.id


@pytest.mark.parametrize("change", ["owner", "kind", "digest", "backend"])
def test_invalid_association_never_reads_provider(storage, monkeypatch, change):
    from web.database.engine import get_engine
    from web.database.models import StoredObject
    owner, store = storage
    descriptor = service.publish_pending_object(owner, "plan_pdf", b"%PDF-owned", "application/pdf")
    with Session(get_engine()) as db:
        if change == "digest":
            with pytest.raises(ObjectUnavailable):
                service.mark_object_ready(db, owner, replace(descriptor, sha256="0" * 64), "plan_pdf")
            return
        service.mark_object_ready(db, owner, descriptor, "plan_pdf")
        if change == "backend":
            db.get(StoredObject, descriptor.id).storage_backend = "s3"
        db.commit()
        monkeypatch.setattr(store, "read", lambda *args, **kwargs: pytest.fail("Unauthorized provider read"))
        with pytest.raises((ObjectUnavailable, ObjectAccessDenied)):
            service.read_private_object(db, "other-owner" if change == "owner" else owner,
                descriptor.id, "gym_logo" if change == "kind" else "plan_pdf")


def test_private_reference_does_not_fall_back_to_legacy_pdf(storage, tmp_path, monkeypatch):
    from web.database.engine import get_engine
    from web.database.models import Cliente, PlanGenerado
    from web.services import plan_documents
    from fastapi import HTTPException
    owner, store = storage
    descriptor = service.publish_pending_object(owner, "plan_pdf", b"%PDF-original", "application/pdf")
    legacy = tmp_path / "legacy.pdf"
    legacy.write_bytes(b"%PDF-different-legacy")
    monkeypatch.setattr(plan_documents, "CARPETA_PLANES", str(tmp_path))
    with Session(get_engine()) as db:
        db.add(Cliente(id_cliente="object-owned-client", gym_id=owner, nombre="Synthetic"))
        db.flush()
        service.mark_object_ready(db, owner, descriptor, "plan_pdf")
        row = PlanGenerado(gym_id=owner, id_cliente="object-owned-client", pdf_object_id=descriptor.id, ruta_pdf=str(legacy))
        db.add(row)
        db.commit()
        assert plan_documents.read_plan_pdf(db, owner, row.id) == b"%PDF-original"
        (store.root / descriptor.key).write_bytes(b"%PDF-corrupted")
        with pytest.raises(HTTPException) as error:
            plan_documents.read_plan_pdf(db, owner, row.id)
        assert error.value.status_code == 404
