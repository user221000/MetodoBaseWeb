"""Local audit reproductions. Uses an in-memory DB and blocks network sockets.

Run from the repository with the QA Python environment. No production writes.
These checks document observed defects; they are not passing security tests.
"""
import asyncio
import json
import os
from pathlib import Path
import socket
import ipaddress
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
os.environ.update({
    "METODOBASE_ENV": "testing",
    "WEB_SECRET_KEY": "audit-only-random-placeholder-key-32-characters",
    "DATABASE_URL": "sqlite://",
    "STRIPE_SECRET_KEY": "",
    "STRIPE_WEBHOOK_SECRET": "",
    "RESEND_API_KEY": "",
    "MERCADOPAGO_ACCESS_TOKEN": "",
    "SENTRY_DSN": "",
    "GOOGLE_CLIENT_ID": "",
    "REDIS_URL": "",
    "RATE_LIMIT_ENABLED": "false",
    "METODOBASE_DATA_DIR": tempfile.mkdtemp(prefix="metodobase-audit-security-"),
})

original_connect = socket.socket.connect
def deny_external_network(sock, address):
    if isinstance(address, tuple):
        host = address[0]
        try:
            if ipaddress.ip_address(host).is_loopback:
                return original_connect(sock, address)
        except ValueError:
            pass
    raise RuntimeError("External network disabled in local audit reproduction")

socket.socket.connect = deny_external_network

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from web.database import engine as engine_module
from web.database.models import Base, Cliente, UserRole, UserSubscription, Usuario
from web import auth
from web.routes import clientes, usuario
from web.services.permissions import has_permission

db_engine = create_engine("sqlite://", poolclass=StaticPool,
                          connect_args={"check_same_thread": False})
factory = sessionmaker(bind=db_engine, expire_on_commit=False)
engine_module._engine = db_engine
engine_module._SessionLocal = factory
Base.metadata.create_all(db_engine)
auth.init_auth()

owner = {"id": "audit-owner", "email": "owner@example.invalid", "nombre": "Audit Owner",
         "apellido": "", "tipo": "gym", "role": "owner"}
member = {"id": "audit-viewer", "email": "viewer@example.invalid", "nombre": "Audit Viewer",
          "apellido": "", "tipo": "usuario", "role": "viewer", "team_gym_id": owner["id"]}
individual = {"id": "audit-individual", "email": "person@example.invalid", "nombre": "Audit Person",
              "apellido": "", "tipo": "usuario", "role": "owner"}
with factory() as db:
    for record in (owner, member, individual):
        data = dict(record)
        data["role"] = UserRole(data["role"])
        db.add(Usuario(**data, password_hash=auth.hash_password("Audit-password-012345"), activo=True))
    db.commit()

app = FastAPI()
app.include_router(clientes.router, prefix="/api")
app.include_router(usuario.router, prefix="/api")
client = TestClient(app)
findings = {}

token = auth.crear_access_token(individual)
result = client.post("/api/usuario/suscripcion", json={"plan": "pro"},
                     headers={"Authorization": "Bearer " + token})
findings["pro_without_payment"] = {"status_code": result.status_code,
                                    "plan": result.json().get("plan"),
                                    "max_planes": result.json().get("max_planes")}
assert result.status_code == 200 and result.json()["plan"] == "pro"

viewer_token = auth.crear_access_token(member)
payload = {"nombre": "Audit Created By Viewer", "edad": 30, "sexo": "M",
           "peso_kg": 80, "estatura_cm": 175, "grasa_corporal_pct": 20,
           "nivel_actividad": "moderada", "objetivo": "mantenimiento"}
result = client.post("/api/clientes", json=payload,
                     headers={"Authorization": "Bearer " + viewer_token})
findings["viewer_creates_client"] = {
    "declared_permission": has_permission(member, "create", "cliente"),
    "status_code": result.status_code,
    "client_created": result.status_code == 201,
}
assert result.status_code == 201 and not has_permission(member, "create", "cliente")

credentials = auth.verificar_credenciales(member["email"], "Audit-password-012345")
findings["login_loses_membership"] = {"role": credentials.get("role"),
                                      "team_gym_id": credentials.get("team_gym_id")}
assert credentials.get("team_gym_id") is None
pair = auth.crear_token_pair(member)
new_pair = auth.rotar_refresh_token(pair["refresh_token"])
refreshed = auth.verificar_token(new_pair["access_token"])
findings["refresh_loses_membership"] = {"role": refreshed.get("role"),
                                        "team_gym_id": refreshed.get("team_gym_id")}
assert refreshed.get("team_gym_id") is None

remember_token = auth.crear_access_token(owner, remember_me=True)
auth.revocar_refresh_tokens_usuario(owner["id"])
with factory() as db:
    db.query(Usuario).filter(Usuario.id == owner["id"]).update({"activo": False})
    db.commit()
decoded = auth.verificar_token(remember_token)
findings["disabled_owner_access_token_still_valid"] = bool(decoded)
assert decoded is not None

# The service returns activated=False for an unpaid subscription. The user
# endpoint nevertheless persists Pro. Patch only the external provider call.
from unittest.mock import patch
from web.services import stripe_service
with factory() as db:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == individual["id"]).one()
    sub.plan = "starter"
    sub.max_planes_mes = 1
    db.commit()
with patch.object(stripe_service, "confirm_subscription",
                  return_value={"activated": False, "status": "incomplete"}):
    result = client.post("/api/usuario/confirm-subscription", json={"subscription_id": "sub_audit"},
                         headers={"Authorization": "Bearer " + token})
with factory() as db:
    persisted = db.query(UserSubscription).filter(UserSubscription.user_id == individual["id"]).one()
    findings["unpaid_confirmation_activates_pro"] = {
        "provider_result_activated": result.json().get("activated"),
        "persisted_plan": persisted.plan, "persisted_status": persisted.status,
    }
    assert result.json()["activated"] is False and persisted.plan == "pro"

result = client.put("/api/usuario/perfil", json={"edad": -5, "peso_kg": -80,
                    "estatura_cm": 0, "grasa_corporal_pct": 150},
                    headers={"Authorization": "Bearer " + token})
findings["invalid_body_measurements_accepted"] = {"status_code": result.status_code}
assert result.status_code == 200

# A provider stub avoids CPU/PDF work; the endpoint's entitlement enforcement
# still runs unmodified. An exhausted Starter quota must reject before calling it.
with factory() as db:
    profile = db.query(Cliente).filter(Cliente.gym_id == individual["id"]).one()
    profile.edad, profile.peso_kg, profile.estatura_cm = 30, 80, 175
    profile.objetivo, profile.nivel_actividad, profile.sexo = "mantenimiento", "moderada", "M"
    profile.grasa_corporal_pct = 20
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == individual["id"]).one()
    sub.plan, sub.max_planes_mes, sub.planes_usados_mes = "starter", 1, 1
    db.commit()
from web.routes import planes
with patch.object(planes, "_generar_plan_sync", return_value={"plan": {}, "ruta_pdf": ""}) as generation:
    result = client.post("/api/usuario/generar-plan", headers={"Authorization": "Bearer " + token})
    findings["exhausted_starter_still_generates"] = {"status_code": result.status_code,
                                                     "generation_called": generation.called}
    assert result.status_code == 200 and generation.called
with factory() as db:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == individual["id"]).one()
    findings["exhausted_starter_still_generates"]["usage_after"] = sub.planes_usados_mes
    assert sub.planes_usados_mes == 1

from sqlalchemy.exc import IntegrityError
from web.services.subscription_service import activate_subscription
with factory() as db:
    try:
        activate_subscription(db, individual["id"], "pro_usuario", stripe_subscription_id="sub_audit_paid")
    except IntegrityError:
        db.rollback()
        findings["paid_pro_identifier_rejected_by_schema"] = True
    else:
        raise AssertionError("Expected pro_usuario schema mismatch not reproduced")
with factory() as db:
    activate_subscription(db, owner["id"], "standard", provider="mercadopago")
    db.commit()
with factory() as db:
    try:
        activate_subscription(db, member["id"], "standard", provider="mercadopago")
    except IntegrityError:
        db.rollback()
        findings["second_mp_subscription_empty_stripe_id_collision"] = True
    else:
        raise AssertionError("Expected empty Stripe ID uniqueness collision not reproduced")

print(json.dumps(findings, indent=2))
