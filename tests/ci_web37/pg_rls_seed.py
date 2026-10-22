"""Original RLS fixture seed body, unchanged; CREATE/DROP are not imported."""
from sqlalchemy.orm import Session

from tests.integration_postgres import CLIENT_IDS, PERSONAL, TENANT_A, TENANT_B
from web.database import models as m


def seed_original_rls_rows(admin):
    with Session(admin) as db:
        for identity in (TENANT_A, TENANT_B):
            db.add(m.Usuario(id=identity, email=identity + "@example.test", password_hash="unused-synthetic",
                nombre="Synthetic", tipo="gym", role=m.UserRole.OWNER, activo=True, session_version=0))
        db.commit()
        db.add(m.Usuario(id=PERSONAL, email="pg-member@example.test", password_hash="unused-synthetic",
            nombre="Personal member", tipo="usuario", role=m.UserRole.NUTRIOLOGO,
            team_gym_id=TENANT_A, activo=True, session_version=0))
        db.commit()
        for identity in (TENANT_A, TENANT_B, PERSONAL):
            client = CLIENT_IDS[identity]
            db.add(m.Cliente(id_cliente=client, gym_id=identity, nombre="Synthetic " + identity,
                edad=30, peso_kg=70, estatura_cm=170, nivel_actividad="moderada", objetivo="mantenimiento"))
            db.flush()
            plan = m.PlanGenerado(id_cliente=client, gym_id=identity, ruta_pdf="synthetic.pdf")
            db.add(plan)
            db.flush()
            db.add_all([
                m.ClientProgress(id_cliente=client, gym_id=identity, peso_kg=70),
                m.Subscription(gym_id=identity, plan="free", status="active", max_clientes=10),
                m.Payment(gym_id=identity, amount_cents=100, status="succeeded", currency="mxn"),
                m.StripeCustomer(gym_id=identity, stripe_customer_id="cus_synthetic_" + identity),
                m.Invoice(gym_id=identity, stripe_invoice_id="in_synthetic_" + identity,
                    amount_due=100, total=100, status="paid"),
                m.CheckoutSession(id="cs_synthetic_" + identity, gym_id=identity, plan="standard",
                    email=identity + "@example.test"),
                m.GymProfile(gym_id=identity, nombre_negocio="Synthetic"),
                m.GymBranding(gym_id=identity, nombre_gym="Synthetic"),
                m.GymSettings(gym_id=identity),
                m.GymLicense(gym_id=identity, license_key="synthetic_" + identity,
                    plan_tier="free", max_clients=10),
                m.PlanSuscripcion(gym_id=identity, nombre="Synthetic", duracion_dias=30, precio=100, moneda="MXN"),
                m.AuditLog(gym_id=identity, accion="synthetic"),
                m.UserSubscription(user_id=identity, mes_actual="2026-10", plan="starter", status="active"),
                m.GenerationReservation(user_id=identity, request_key="synthetic-request",
                    period="2026-10", status="completed", plan_id=plan.id),
                m.LicenseActivation(gym_id=identity, hardware_id="hardware_" + identity,
                    clave_hash="a" * 64, email=identity + "@example.test", plan="free", expira=None),
            ])
        db.add(m.AuditLog(gym_id=None, accion="synthetic-control-plane-null"))
        db.add(m.LicenseActivation(gym_id=None, hardware_id="unassociated-synthetic-hardware",
            clave_hash="b" * 64, email="unassociated@example.test", plan="standard", expira=None))
        db.commit()
