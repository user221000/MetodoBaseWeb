"""New R30 companions on actual schema37; historical fixtures stay unchanged."""
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from tests import account_security37_http as original
from web.database.models import (
    Cliente,
    GenerationReservation,
    GymGenerationReservation,
    PlanGenerado,
    UserRole,
    Usuario,
)

account37_engine = original.account37_engine
followup_db = original.followup_db
analytics_http = original.account_http
NOW = datetime(2026, 10, 21, 18, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def analytics_engine(account37_engine):
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
    event.listen(account37_engine, "connect", foreign_keys)
    account37_engine.dispose()
    return account37_engine


@pytest.fixture
def analytics_case(analytics_engine):
    class Case:
        engine = analytics_engine
        factory = sessionmaker(bind=analytics_engine, autoflush=False, expire_on_commit=True)

        def user(self, *, role=UserRole.OWNER, tipo="gym", parent=None, **fields):
            identity = str(uuid.uuid4())
            with self.factory() as db:
                db.add(Usuario(id=identity, email=uuid.uuid4().hex + "@example.invalid",
                    nombre="Synthetic analytics fixture", password_hash="service-fixture-not-a-login-credential",
                    tipo=tipo, role=role, team_gym_id=parent, **fields))
                db.commit()
            return {"id": identity, "tipo": tipo, "role": role.value,
                    "team_gym_id": parent, "session_version": fields.get("session_version", 0)}

        def profile(self, owner):
            identity = str(uuid.uuid4())
            with self.factory() as db:
                db.add(Cliente(gym_id=owner["id"], id_cliente=identity, nombre="Synthetic unselected profile"))
                db.commit()
            return identity

        def plan(self, owner, profile):
            with self.factory() as db:
                row = PlanGenerado(gym_id=owner["id"], id_cliente=profile,
                    fecha_generacion=NOW, plan_json='{"private":"must never be selected"}', kcal_objetivo=1234)
                db.add(row)
                db.flush()
                identity = row.id
                db.commit()
            return identity

        def saved(self, owner, stamp, *, context="gym", **fields):
            identity = str(uuid.uuid4())
            data = {"id": identity, "request_key": uuid.uuid4().hex, "created_at": stamp or NOW,
                    "updated_at": stamp or NOW, "status": "completed", "persisted_at": stamp}
            if context == "gym":
                data.update(gym_id=owner["id"], request_hash="a" * 64, period="2026-10",
                    local_date=NOW.date(), timezone="America/Mexico_City", catalog_plan="free", result_json="{}")
                model = GymGenerationReservation
            else:
                data.update(user_id=owner["id"], period="2026-10", publication_protocol=1)
                model = GenerationReservation
            data.update(fields)
            with self.factory() as db:
                db.add(model(**data))
                db.commit()
            return identity
    return Case()
