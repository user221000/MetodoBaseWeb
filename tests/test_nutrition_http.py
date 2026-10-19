"""Independent HTTP/persistence and whole-plan restriction acceptance."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import uuid

import pytest


@pytest.fixture
def individual_client():
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from web.auth import crear_access_token, hash_password
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole
    from web.main_web import create_app

    app = create_app()
    user = {"id": str(uuid.uuid4()), "email": "nutrition@example.test", "nombre": "Synthetic", "tipo": "usuario", "role": "viewer", "session_version": 0}
    with Session(get_engine()) as db:
        db.add(Usuario(id=user["id"], email=user["email"], nombre=user["nombre"], tipo="usuario",
                       password_hash=hash_password("SyntheticTestPassword123!"), role=UserRole.VIEWER,
                       session_version=0, activo=True))
        db.commit()
    with TestClient(app, headers={"Authorization": "Bearer " + crear_access_token(user)}) as client:
        valid = {"edad": 30, "peso_kg": 75, "estatura_cm": 175, "grasa_corporal_pct": 20,
                 "nivel_actividad": "moderada", "objetivo": "mantenimiento", "sexo": "M"}
        assert client.put("/api/usuario/perfil", json=valid).status_code == 200
        yield client, user


@pytest.mark.parametrize("change", [
    {"edad": -5}, {"peso_kg": -80}, {"estatura_cm": 0}, {"grasa_corporal_pct": 150},
    {"peso_kg": "NaN"}, {"peso_kg": "Infinity"}, {"nivel_actividad": "unsafe"},
    {"objetivo": "unknown"}, {"sexo": "unknown"}, {"gym_id": "other-gym"},
    {"role": "owner"}, {"alimentos_excluidos": ["outside_catalog"]},
])
def test_rejected_profile_cannot_modify_persisted_data(individual_client, change):
    client, _ = individual_client
    before = client.get("/api/usuario/perfil").json()
    response = client.put("/api/usuario/perfil", json=change)
    assert response.status_code == 422
    assert client.get("/api/usuario/perfil").json() == before


def test_partial_normalized_profile_preserves_other_fields(individual_client):
    client, _ = individual_client
    response = client.put("/api/usuario/perfil", json={"sexo": "femenino", "nivel_actividad": "sedentario"})
    assert response.status_code == 200
    profile = client.get("/api/usuario/perfil").json()
    assert profile["sexo"] == "F"
    assert profile["nivel_actividad"] == "nula"
    assert profile["peso_kg"] == 75


def test_explicit_null_optional_fields_preserve_existing_profile(individual_client):
    client, _ = individual_client
    before = client.get("/api/usuario/perfil").json()
    update = {key: None for key in ("edad", "peso_kg", "estatura_cm", "grasa_corporal_pct",
                                   "sexo", "nivel_actividad", "objetivo", "alimentos_excluidos")}
    assert client.put("/api/usuario/perfil", json=update).status_code == 200
    assert client.get("/api/usuario/perfil").json() == before


def test_unavailable_food_id_or_only_forbidden_fallback_fails_closed():
    from core.food_catalog import FoodCatalog, FoodRestrictionError
    from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS
    with pytest.raises(FoodRestrictionError):
        FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, ["outside_catalog"])
    catalog = FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, ["huevo"])
    with pytest.raises(FoodRestrictionError):
        catalog.require_candidates(["huevo"])


def test_total_exclusion_does_not_publish_and_refunds_the_credit(individual_client):
    from sqlalchemy.orm import Session
    from src.alimentos_base import CATEGORIAS
    from web.database.engine import get_engine
    from web.database.models import PlanGenerado, UserSubscription

    client, user = individual_client
    assert client.put("/api/usuario/perfil", json={"alimentos_excluidos": list(CATEGORIAS["proteina"])}).status_code == 200
    response = client.post("/api/usuario/generar-plan", headers={"Idempotency-Key": "all-proteins-excluded"})
    assert response.status_code == 400
    with Session(get_engine()) as db:
        assert db.query(PlanGenerado).filter_by(gym_id=user["id"]).count() == 0
        assert db.query(UserSubscription).filter_by(user_id=user["id"]).one().planes_usados_mes == 0


def test_whole_plans_with_distinct_restrictions_are_independent(tmp_path):
    from core.food_catalog import FoodCatalog
    from core.generador_opciones import ConstructorPlanConOpciones
    from core.modelos import ClienteEvaluacion
    from core.motor_nutricional import MotorNutricional
    from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS

    snapshot = {name: tuple(items) for name, items in CATEGORIAS.items()}
    groups = (("huevo", "avena", "papa"), ("arroz_blanco", "granola", "nueces"))

    def generate(case):
        index, exclusions = case
        catalog = FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, exclusions)
        client = MotorNutricional.calcular_motor(ClienteEvaluacion(nombre="Synthetic", id_cliente=f"QA_PARALLEL_{index}",
            edad=30, peso_kg=80, estatura_cm=175, grasa_corporal_pct=20,
            nivel_actividad="moderada", objetivo="mantenimiento"))
        output = Path(tmp_path) / str(index)
        output.mkdir()
        plan = ConstructorPlanConOpciones.construir(client, directorio_planes=str(output), catalogo=catalog)
        catalog.validate_plan(plan)
        assert all(plan[meal]["proteinas"]["opciones"] for meal in ("desayuno", "almuerzo", "comida", "cena"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(generate, enumerate(groups)))
    assert {name: tuple(items) for name, items in CATEGORIAS.items()} == snapshot
