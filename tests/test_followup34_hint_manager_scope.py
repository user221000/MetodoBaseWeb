"""Canonical persisted tuples narrow lock discovery before final authority.

These are direct service/SQLite controls, not HTTP authentication or a claim
that inconsistent owner/team tuples are reachable through a supported API.
"""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests import followup34_http as http_fixtures
from web.database import followup_task_repository as repo
from web.database.models import (
    Cliente,
    FollowupTask,
    FollowupTaskEvent,
    UserRole,
    Usuario,
)
from web.database.tenant_context import tenant_scope
from web.followup_schemas import CreateTask
from web.services import followup_domain as domain
from web.services import followup_tasks as service

followup_db = http_fixtures.followup_db


@pytest.mark.parametrize("kind", ["personal_owner", "team_owner_gym", "team_owner_personal", "canonical_owner", "accepted_admin"])
def test_actual_persisted_tuple_controls_requested_assignee_lock(followup_db, monkeypatch, kind):
    engine = followup_db
    gym, actor, other, client = (str(uuid.uuid4()) for _ in range(4))
    if kind == "canonical_owner":
        actor = gym
    role = UserRole.ADMIN if kind == "accepted_admin" else UserRole.OWNER
    tipo = "gym" if kind in {"canonical_owner", "team_owner_gym"} else "usuario"
    team = gym if kind in {"accepted_admin", "team_owner_gym", "team_owner_personal"} else None
    with Session(engine) as db:
        db.add(Usuario(id=gym, email=uuid.uuid4().hex+"@example.invalid", password_hash="synthetic-unusable",
            nombre="Synthetic canonical owner", tipo="gym", role=UserRole.OWNER))
        if actor != gym:
            db.add(Usuario(id=actor, email=uuid.uuid4().hex+"@example.invalid", password_hash="synthetic-unusable",
                nombre="Synthetic tuple", tipo=tipo, role=role, team_gym_id=team))
        db.add(Usuario(id=other, email=uuid.uuid4().hex+"@example.invalid", password_hash="synthetic-unusable",
            nombre="Synthetic accepted responsible", tipo="usuario", role=UserRole.NUTRIOLOGO, team_gym_id=gym))
        db.flush()
        db.add(Cliente(id_cliente=client, gym_id=gym, nombre="Synthetic source"))
        db.commit()
        persisted = db.get(Usuario, actor)
        expected = {"id": persisted.id, "role": persisted.role.value, "tipo": persisted.tipo,
            "team_gym_id": persisted.team_gym_id, "session_version": persisted.session_version}
    observed = []
    original = service.authority
    def capture(db, principal, **kwargs):
        observed.append(tuple(kwargs.get("extra", ())))
        return original(db, principal, **kwargs)
    monkeypatch.setattr(service, "authority", capture)
    permitted = kind in {"canonical_owner", "accepted_admin"}
    with tenant_scope(team or actor), Session(engine) as db:
        source = repo.sources(db, gym, [client])[client]
        fact = domain.causes(source, gym, domain.instant())[0]
        command = CreateTask(client_id=client, cause=fact["cause"], cause_evidence_hash=fact["cause_evidence_hash"],
            next_step="review_plan_history", assignee_id=other, expected_active_task_id=None, confirm=True)
        if permitted:
            result = service.mutate(db, expected, "created", command, str(uuid.uuid4()), "/api/seguimiento/tareas")
            assert result["ack"] is True
        else:
            with pytest.raises(HTTPException) as denied:
                service.mutate(db, expected, "created", command, str(uuid.uuid4()), "/api/seguimiento/tareas")
            assert denied.value.status_code == 403
            db.rollback()
    assert observed == [(None, other)] if permitted else observed == [(None, None)]
    with Session(engine) as db:
        tasks = db.scalars(select(FollowupTask.id).where(FollowupTask.client_id == client)).all()
        events = db.scalars(select(FollowupTaskEvent.id).where(FollowupTaskEvent.client_id == client)).all()
        assert len(tasks) == len(events) == (1 if permitted else 0)
