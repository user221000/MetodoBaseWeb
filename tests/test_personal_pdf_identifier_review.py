"""Independent regression: an invalid explicit personal plan never means latest."""
from datetime import datetime, timedelta
import importlib
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session


def test_invalid_explicit_identifier_is_rejected_and_only_omission_selects_latest(tmp_path,monkeypatch):
    from web.auth import crear_access_token,identity_from_user
    from web.database.engine import get_engine
    from web.database.models import Usuario,UserRole,Cliente,PlanGenerado
    from web.services import plan_documents
    root=tmp_path/'personal-pdfs'
    root.mkdir()
    monkeypatch.setattr(plan_documents,'CARPETA_PLANES',str(root))
    # The personal router belongs to SaaS; the standalone API has no such route.
    app=importlib.import_module('web.main_web').create_app()
    owner=str(uuid.uuid4())
    with Session(get_engine()) as db:
        user=Usuario(id=owner,email=owner+'@example.invalid',nombre='Synthetic',password_hash='unused',
            tipo='usuario',role=UserRole.VIEWER,activo=True)
        db.add(user)
        db.flush()
        db.add(Cliente(gym_id=owner,id_cliente=owner,nombre='Synthetic'))
        db.flush()
        plans=[]
        for number in (1,2):
            path=root/(str(number)+'.pdf')
            path.write_bytes(('%PDF-personal-review-'+str(number)).encode())
            plan=PlanGenerado(gym_id=owner,id_cliente=owner,ruta_pdf=str(path),
                fecha_generacion=datetime(2026,10,18)+timedelta(seconds=number))
            db.add(plan)
            db.flush()
            plans.append(plan.id)
        db.commit()
        token=crear_access_token(identity_from_user(user,db))
    headers={'Authorization':'Bearer '+token}
    with TestClient(app,raise_server_exceptions=False) as client:
        for invalid in (0,-1,2147483648):
            response=client.get('/api/usuario/descargar-pdf',params={'plan_id':invalid},headers=headers)
            assert response.status_code==422
            assert not response.content.startswith(b'%PDF-')
        exact=client.get('/api/usuario/descargar-pdf',params={'plan_id':plans[0]},headers=headers)
        latest=client.get('/api/usuario/descargar-pdf',headers=headers)
        assert exact.status_code==latest.status_code==200
        assert exact.content==b'%PDF-personal-review-1'
        assert latest.content==b'%PDF-personal-review-2'
