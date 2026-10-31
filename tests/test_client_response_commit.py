"""Client mutations are durable at HTTP headers, not a later request finalizer.

Real repository/SQLite and ASGI send timing. Identity and the daily registration
guard are supplied directly; the repository capacity guard remains real.
Authentication, production PostgreSQL and power-loss durability are not claimed.
"""
import asyncio

from fastapi import FastAPI
import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def mutation_case(tmp_path,monkeypatch):
    from web.auth_deps import get_usuario_actual
    from web.database import engine as database
    from web.database.models import Base, Cliente, Usuario, UserRole
    from web.routes.clientes import router
    from web.subscription_guard import check_daily_registration_limit

    engine=create_engine('sqlite:///'+(tmp_path/'owned-client-timing.db').as_posix(),
                         connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Usuario(id='timing-owner',email='timing-owner@example.invalid',
                       nombre='Synthetic owner',password_hash='not-authenticated-by-this-test',
                       tipo='gym',role=UserRole.OWNER))
        db.commit()
        db.add(Cliente(id_cliente='timing-existing',gym_id='timing-owner',
                       nombre='Existing client',notas='original',activo=True))
        db.commit()
    owner={'id':'timing-owner','tipo':'gym','role':'owner','team_gym_id':None}
    state={'fail_once':False,'commit_calls':0,'headers':[]}

    class RequestSession(Session):
        def commit(self):
            state['commit_calls']+=1
            if state['fail_once']:
                state['fail_once']=False
                raise RuntimeError('synthetic private commit diagnostic')
            return super().commit()

    factory=sessionmaker(bind=engine,class_=RequestSession,expire_on_commit=False,autoflush=False)
    monkeypatch.setattr(database,'_engine',engine)
    monkeypatch.setattr(database,'_SessionLocal',factory)
    assert factory.kw['bind'] is database._engine

    app=FastAPI()
    app.include_router(router,prefix='/api')
    app.dependency_overrides[get_usuario_actual]=lambda:owner
    app.dependency_overrides[check_daily_registration_limit]=lambda:owner

    def snapshot():
        with Session(engine) as db:
            return [{'id':x.id_cliente,'name':x.nombre,'notes':x.notas,'active':x.activo}
                    for x in db.scalars(select(Cliente).order_by(Cliente.id_cliente))]

    async def observed(scope,receive,send):
        async def capture(message):
            if message['type']=='http.response.start':
                state['headers'].append({'status':message['status'],'stored':snapshot()})
            await send(message)
        await app(scope,receive,capture)

    yield observed,state,snapshot
    engine.dispose()


def request(case,operation):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=case[0],raise_app_exceptions=False),
                                     base_url='http://testserver') as client:
            if operation=='create':
                return await client.post('/api/clientes',json={
                    'nombre':'New timing client','edad':30,'peso_kg':70,'estatura_cm':170,
                    'sexo':'M','nivel_actividad':'moderada','objetivo':'mantenimiento'})
            if operation=='update':
                return await client.put('/api/clientes/timing-existing',json={'notas':'updated'})
            return await client.delete('/api/clientes/timing-existing')
    return asyncio.run(run())


@pytest.mark.parametrize('operation',['create','update','delete'])
def test_next_connection_sees_change_before_success_headers(mutation_case,operation):
    _,state,snapshot=mutation_case
    response=request(mutation_case,operation)
    assert response.status_code==(201 if operation=='create' else 200)
    stored=state['headers'][0]['stored']
    assert stored==snapshot()
    if operation=='create':
        assert len(stored)==2 and any(x['name']=='New Timing Client' for x in stored)
    elif operation=='update':
        assert stored[0]['notes']=='updated'
    else:
        assert stored[0]['active'] is False


@pytest.mark.parametrize('operation',['create','update','delete'])
def test_one_failed_commit_never_becomes_success_or_later_finalizer_write(mutation_case,operation):
    _,state,snapshot=mutation_case
    before=snapshot()
    state['fail_once']=True
    response=request(mutation_case,operation)
    assert response.status_code==(500 if operation=='delete' else 400)
    assert state['headers'][0]['status']==response.status_code
    assert state['headers'][0]['stored']==before and snapshot()==before
    assert 'synthetic private commit diagnostic' not in response.text
    assert 'timing-existing' not in response.text
    assert state['commit_calls']==2  # the finalizer committed only an empty transaction
