"""Independent, bounded SQL review of frozen R12 revision29; no API claim.

Own UUID database, real migrations, actual restricted app role and real tenant
hook. Payload expectations are constructed from seeded source values, without
calling r12_project_plan to manufacture either accepted or rejected input.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import secrets
from threading import Event
import time
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine
from web.database.tenant_context import configure_tenant_engine, tenant_scope
from web.database.schema_control import verify_runtime_schema
from web.database.alembic.security_contract_v1 import tenant_security_signature

GA, GB, UA, UB = [str(uuid.UUID(int=x)) for x in (2001, 2002, 2003, 2004)]
CA, CA2, CA3, CB = 'qa-r12-a', 'qa-r12-a2', 'qa-r12-a3', 'qa-r12-b'
HEAD = '20261019_client_account_links'
NEW = {'client_account_links', 'client_link_invitations', 'client_plan_publications'}
MEALS = ('desayuno', 'almuerzo', 'comida', 'cena')
META = dict(tmb=1521.25, get_total=2312.75, kcal_objetivo=2140.5,
            kcal_real=2139.5, proteina_g=123.75, carbs_g=256.25, grasa_g=63.5,
            objetivo='synthetic-maintenance', nivel_actividad='synthetic-active', tipo_plan='menu_fijo')


def menu(kind='fixed'):
    if kind == 'fixed':
        return {name: {'kcal_objetivo': 300 + n, 'kcal_real': 299.5 + n,
                       'alimentos': {'Synthetic arroz ' + str(n): 73.25 + n,
                                     'Synthetic verdura ' + str(n): 18.5}}
                for n, name in enumerate(MEALS)}
    return {name: {'kcal_objetivo': 400 + n, 'tipo_plan': 'opciones',
                  **{category: {'cantidad_objetivo': 12.5 + n,
                                'opciones': [{'alimento': 'Synthetic ' + category + str(n),
                                              'gramos': 42.25 + n, 'equivalencia': 'Synthetic 1 portion',
                                              'macros': {'kcal': 34.5, 'proteina': 2.25, 'carbs': 4.5, 'grasa': 1.25}}]}
                     for category in ('proteinas', 'carbohidratos', 'grasas')},
                  'vegetales': [{'alimento': 'Synthetic veg ' + str(n), 'gramos': 17.25}]}
            for n, name in enumerate(MEALS)}


def digest(token):
    return hashlib.sha256(('client-account-invite-v1:' + token).encode('ascii')).hexdigest()


@pytest.fixture(scope='module')
def own_lab(tmp_path_factory):
    from web.database.models import Usuario, UserRole, Cliente, PlanGenerado, StoredObject
    from web.storage.objects import describe
    owner = migration_database.__wrapped__(SimpleNamespace(param='postgresql'), tmp_path_factory.mktemp('qa-r12-own'))
    url, admin = next(owner)
    app = None
    try:
        run_migration(url, 'db_bootstrap.py', '--revision', '20261019_account_recovery')
        with admin.connect() as db:
            previous = tenant_security_signature(db)
        run_migration(url, 'db_bootstrap.py', '--revision', HEAD)
        verify_runtime_schema(admin, expected_revision=HEAD)
        objects, plans = {}, {}
        with Session(admin) as db:
            for actor, kind, role in [(GA, 'gym', UserRole.OWNER), (GB, 'gym', UserRole.OWNER),
                                      (UA, 'usuario', UserRole.VIEWER), (UB, 'usuario', UserRole.VIEWER)]:
                db.add(Usuario(id=actor, email=actor+'@example.invalid', nombre='Synthetic QA',
                               password_hash='synthetic-qa-only', tipo=kind, role=role, activo=True))
            db.flush()
            for client, gym in [(CA, GA), (CA2, GA), (CA3, GA), (CB, GB)]:
                db.add(Cliente(id_cliente=client, gym_id=gym, nombre='Synthetic QA', activo=True))
                descriptor = describe(gym, 'plan_pdf', b'%PDF-1.7\nSynthetic QA ' + client.encode(), 'application/pdf')
                objects[client] = descriptor
                db.add(StoredObject(id=descriptor.id, gym_id=gym, kind=descriptor.kind, key=descriptor.key,
                                    content_type=descriptor.content_type, byte_size=descriptor.byte_size,
                                    sha256=descriptor.sha256, storage_backend='local', status='ready'))
                db.flush()
                plan = PlanGenerado(gym_id=gym, id_cliente=client, plan_json=json.dumps(menu()),
                                     pdf_object_id=descriptor.id, **META)
                db.add(plan); db.flush(); plans[client] = plan.id
            db.commit()
        base = application_engine(url, admin)
        app = configure_tenant_engine(create_engine(base.url, pool_size=5, max_overflow=0, hide_parameters=True))
        base.dispose()
        yield dict(admin=admin, app=app, objects=objects, plans=plans, previous=previous)
    finally:
        if app is not None:
            app.dispose()
        owner.close()


@pytest.fixture(autouse=True)
def restore_source(own_lab):
    with own_lab['admin'].begin() as db:
        db.exec_driver_sql('TRUNCATE public.client_plan_publications, public.client_link_invitations, public.client_account_links')
        db.exec_driver_sql('UPDATE public.usuarios SET activo=true, deleted_at=NULL, session_version=0')
        db.exec_driver_sql('UPDATE public.clientes SET activo=true, deleted_at=NULL')
        db.exec_driver_sql("UPDATE public.stored_objects SET status='ready'")
        db.execute(text('UPDATE public.planes_generados SET deleted_at=NULL,plan_json=:value,tmb=:tmb,get_total=:get_total,kcal_objetivo=:kcal_objetivo,kcal_real=:kcal_real,proteina_g=:proteina_g,carbs_g=:carbs_g,grasa_g=:grasa_g,objetivo=:objetivo,nivel_actividad=:nivel_actividad,tipo_plan=:tipo_plan'),
                   dict(value=json.dumps(menu()), **META))


@contextmanager
def transaction(lab, actor, token=None):
    with tenant_scope(actor), lab['app'].connect() as db:
        db.exec_driver_sql("SET LOCAL statement_timeout='7000ms'")
        if token is not None:
            db.execute(text("SELECT set_config('app.client_invitation_digest',:proof,true)"), {'proof': digest(token)})
        try:
            yield db
        finally:
            db.rollback()


def issue(lab, *, gym=GA, client=CA, recipient=UA, expiry='1 day'):
    token = secrets.token_urlsafe(32)
    values = dict(link=str(uuid.uuid4()), invitation=str(uuid.uuid4()), gym=gym, client=client,
                  actor=recipient, token=token, proof=digest(token), email=recipient+'@example.invalid', expiry=expiry)
    with transaction(lab, gym) as db:
        db.execute(text('SELECT id FROM public.usuarios WHERE id=:gym FOR UPDATE NOWAIT'), values).scalar_one()
        db.execute(text('SELECT id_cliente FROM public.clientes WHERE gym_id=:gym AND id_cliente=:client FOR UPDATE'), values).scalar_one()
        db.execute(text("INSERT INTO public.client_account_links(id,gym_id,client_id,status,gym_name,client_display_name) VALUES(:link,:gym,:client,'pending','Synthetic QA gym','Synthetic QA client')"), values)
        db.execute(text("INSERT INTO public.client_link_invitations(id,link_id,gym_id,client_id,recipient_email,token_hash,expires_at,status,issued_by,request_key,payload_hash) VALUES(:invitation,:link,:gym,:client,:email,:proof,(clock_timestamp() AT TIME ZONE 'UTC')+CAST(:expiry AS interval),'pending',:gym,:invitation,:proof)"), values)
        db.commit()
    return values


def consume(db, invitation):
    for actor in sorted({invitation['gym'], invitation['actor']}):
        db.execute(text('SELECT id FROM public.usuarios WHERE id=:id FOR UPDATE NOWAIT'), {'id': actor}).scalar_one()
    db.execute(text('SELECT id FROM public.client_account_links WHERE id=:link FOR UPDATE'), invitation).scalar_one()
    at = db.execute(text("UPDATE public.client_link_invitations SET status='consumed',consumed_by=:actor,version=version+1 WHERE id=:invitation RETURNING consumed_at"), invitation).scalar_one()
    db.execute(text("UPDATE public.client_account_links SET status='active',user_id=:actor,accepted_at=:at,version=version+1 WHERE id=:link RETURNING id"), dict(invitation, at=at)).scalar_one()


def accept(lab, invitation):
    with transaction(lab, invitation['actor'], invitation['token']) as db:
        consume(db, invitation); db.commit()


def expected(kind='fixed'):
    return {'plan': menu(kind), 'meta': dict(META, tipo_plan='opciones' if kind == 'options' else META['tipo_plan'])}


def publish(db, lab, invitation, payload=None, overrides=None):
    descriptor = lab['objects'][invitation['client']]
    serialized = json.dumps(payload if payload is not None else expected(), ensure_ascii=False, separators=(',', ':'))
    values = dict(id=str(uuid.uuid4()), gym=invitation['gym'], client=invitation['client'], link=invitation['link'],
                  source=lab['plans'][invitation['client']], source_object_id=descriptor.id,
                  object_key=descriptor.key, content_type=descriptor.content_type, byte_size=descriptor.byte_size,
                  sha256=descriptor.sha256, storage_backend='local', payload=serialized,
                  plan_sha=hashlib.sha256(serialized.encode('utf8')).hexdigest())
    values.update(overrides or {})
    return db.execute(text("""INSERT INTO public.client_plan_publications
      (id,gym_id,client_id,link_id,source_plan_id,source_object_id,object_key,content_type,byte_size,sha256,storage_backend,plan_json,plan_sha256,published_by,status)
      VALUES(:id,:gym,:client,:link,:source,:source_object_id,:object_key,:content_type,:byte_size,:sha256,:storage_backend,:payload,:plan_sha,:gym,'published') RETURNING id"""), values).scalar_one()


def make_publication(lab, invitation, payload=None):
    with transaction(lab, invitation['gym']) as db:
        publication = publish(db, lab, invitation, payload); db.commit(); return publication


@pytest.mark.parametrize('own_gym', [True, False])
def test_owner_identity_accepts_own_or_external_without_profile_or_role_adoption(own_lab, own_gym):
    invitation = issue(own_lab, gym=GA if own_gym else GB, client=CA if own_gym else CB, recipient=GA)
    with own_lab['admin'].connect() as db:
        before = db.execute(text('SELECT tipo,role,team_gym_id,session_version,email,password_hash FROM public.usuarios WHERE id=:actor'), {'actor': GA}).one()
    with transaction(own_lab, GA, secrets.token_urlsafe(32)) as db:
        assert db.scalar(text('SELECT count(*) FROM public.client_link_invitations i WHERE id=:invitation AND public.r12_proof(i)'), invitation) == 0
    accept(own_lab, invitation)
    publication = make_publication(own_lab, invitation)
    with transaction(own_lab, GA) as db:
        assert db.execute(text('SELECT p.id FROM public.client_plan_publications p JOIN public.client_account_links l ON l.id=p.link_id WHERE l.user_id=:actor AND p.id=:id'), {'actor': GA, 'id': publication}).scalar_one() == publication
    with own_lab['admin'].connect() as db:
        assert db.execute(text('SELECT tipo,role,team_gym_id,session_version,email,password_hash FROM public.usuarios WHERE id=:actor'), {'actor': GA}).one() == before


def test_owner_received_predicate_excludes_other_recipient_in_own_professional_scope(own_lab):
    other = issue(own_lab, recipient=UA); accept(own_lab, other); other_id = make_publication(own_lab, other)
    received = issue(own_lab, gym=GB, client=CB, recipient=GA); accept(own_lab, received); received_id = make_publication(own_lab, received)
    with transaction(own_lab, GA) as db:
        assert set(db.scalars(text('SELECT id FROM public.client_plan_publications'))) == {other_id, received_id}
        ids = set(db.scalars(text('SELECT p.id FROM public.client_plan_publications p JOIN public.client_account_links l ON l.id=p.link_id WHERE l.user_id=:actor'), {'actor': GA}))
        assert ids == {received_id}


@pytest.mark.parametrize('kind', ['fixed', 'options'])
def test_valid_four_meals_and_all_metadata_equal_independent_seed_exactly(own_lab, kind):
    source = expected(kind)
    with own_lab['admin'].begin() as db:
        db.execute(text('UPDATE public.planes_generados SET plan_json=:plan,tipo_plan=:kind WHERE id=:id'),
                   {'plan': json.dumps(source['plan']), 'kind': source['meta']['tipo_plan'], 'id': own_lab['plans'][CA]})
    invitation = issue(own_lab); accept(own_lab, invitation); identity = make_publication(own_lab, invitation, source)
    with transaction(own_lab, UA) as db:
        row = db.execute(text('SELECT plan_json,plan_sha256 FROM public.client_plan_publications WHERE id=:id'), {'id': identity}).one()
        assert json.loads(row.plan_json) == source
        assert len(source['plan']) == 4 and set(source['meta']) == set(META)
        assert row.plan_sha256 == hashlib.sha256(row.plan_json.encode('utf8')).hexdigest()


@pytest.mark.parametrize('change', ['valid_meal', 'valid_metadata'])
def test_valid_json_and_coherent_sha_cannot_forge_source_values(own_lab, change):
    invitation = issue(own_lab); accept(own_lab, invitation)
    forged = expected()
    if change == 'valid_meal':
        forged['plan']['comida']['alimentos']['Synthetic arroz 2'] = 81.125
    else:
        forged['meta']['proteina_g'] = 124.75
    with transaction(own_lab, GA) as db:
        with pytest.raises(DBAPIError) as rejected:
            publish(db, own_lab, invitation, forged)
        assert rejected.value.orig.pgcode == '23514'
        assert rejected.value.orig.diag.message_primary == 'R12 projection source mismatch'
    with own_lab['admin'].connect() as db:
        assert db.scalar(text('SELECT count(*) FROM public.client_plan_publications')) == 0


def wait_blocked(observer, pid, blocker_pid):
    deadline = time.monotonic() + 4
    while True:
        if blocker_pid in observer.scalar(text('SELECT pg_blocking_pids(:pid)'), {'pid': pid}):
            return
        assert time.monotonic() < deadline, 'Expected exact own wait edge did not occur'
        time.sleep(.01)


def test_expiration_is_rechecked_after_actual_invitation_row_wait(own_lab):
    invitation = issue(own_lab, expiry='1.2 seconds')
    ready, state = Event(), {}
    def worker():
        with transaction(own_lab, UA, invitation['token']) as db:
            state['pid'] = db.scalar(text('SELECT pg_backend_pid()')); ready.set()
            try:
                consume(db, invitation); db.commit()
            except DBAPIError as rejected:
                return rejected.orig.pgcode
            return 'unexpected-commit'
    with own_lab['admin'].begin() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        blocker_pid = blocker.scalar(text('SELECT pg_backend_pid()'))
        blocker.execute(text('SELECT id FROM public.client_link_invitations WHERE id=:invitation FOR UPDATE'), invitation).scalar_one()
        future = pool.submit(worker); assert ready.wait(3)
        with own_lab['admin'].connect() as observer:
            wait_blocked(observer, state['pid'], blocker_pid)
            deadline = time.monotonic()+4
            while not observer.scalar(text("SELECT (clock_timestamp() AT TIME ZONE 'UTC')>expires_at FROM public.client_link_invitations WHERE id=:invitation"), invitation):
                assert time.monotonic()<deadline; time.sleep(.02)
        blocker.commit()
        assert future.result(timeout=8) == '42501'
    with own_lab['admin'].connect() as db:
        assert db.execute(text('SELECT i.status,l.status FROM public.client_link_invitations i JOIN public.client_account_links l ON i.link_id=l.id')).one() == ('pending', 'pending')


@pytest.mark.parametrize('resource', ['client', 'plan', 'object'])
def test_inactive_owner_invalidation_survives_source_and_owner_reactivation(own_lab, resource):
    invitation = issue(own_lab); accept(own_lab, invitation); identity = make_publication(own_lab, invitation)
    with own_lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=false WHERE id=:actor'), {'actor': GA})
    mutate = {'client': ('UPDATE public.clientes SET activo=false WHERE id_cliente=:id', CA),
              'plan': ('UPDATE public.planes_generados SET kcal_real=kcal_real+1 WHERE id=:id', own_lab['plans'][CA]),
              'object': ("UPDATE public.stored_objects SET status='pending' WHERE id=:id", own_lab['objects'][CA].id)}
    sql, source_id = mutate[resource]
    with transaction(own_lab, GA) as db:
        assert db.execute(text(sql), {'id': source_id}).rowcount == 1; db.commit()
    with own_lab['admin'].begin() as db:
        assert db.scalar(text('SELECT status FROM public.client_plan_publications WHERE id=:id'), {'id': identity}) == 'withdrawn'
        db.execute(text('UPDATE public.usuarios SET activo=true WHERE id=:actor'), {'actor': GA})
        db.execute(text('UPDATE public.clientes SET activo=true WHERE id_cliente=:id'), {'id': CA})
        db.execute(text("UPDATE public.stored_objects SET status='ready' WHERE id=:id"), {'id': own_lab['objects'][CA].id})
        db.execute(text('UPDATE public.planes_generados SET kcal_real=:kcal WHERE id=:id'), {'kcal': META['kcal_real'], 'id': own_lab['plans'][CA]})
    with transaction(own_lab, UA) as db:
        assert db.scalar(text('SELECT count(*) FROM public.client_plan_publications WHERE id=:id'), {'id': identity}) == 0


def test_own_recipient_can_revoke_with_inactive_source_owner_but_other_actor_cannot(own_lab):
    invitation = issue(own_lab); accept(own_lab, invitation); identity = make_publication(own_lab, invitation)
    with own_lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=false WHERE id=:actor'), {'actor': GA})
    with transaction(own_lab, UB) as db:
        assert db.execute(text("UPDATE public.client_account_links SET status='revoked',version=version+1 WHERE id=:link"), invitation).rowcount == 0; db.commit()
    with transaction(own_lab, UA) as db:
        assert db.execute(text("UPDATE public.client_account_links SET status='revoked',version=version+1 WHERE id=:link RETURNING user_id"), invitation).scalar_one() == UA
        db.commit()
    with own_lab['admin'].begin() as db:
        assert db.scalar(text('SELECT status FROM public.client_account_links WHERE id=:link'), invitation) == 'revoked'
        db.execute(text('UPDATE public.usuarios SET activo=true WHERE id=:actor'), {'actor': GA})
    with transaction(own_lab, UA) as db:
        assert db.scalar(text('SELECT count(*) FROM public.client_plan_publications WHERE id=:id'), {'id': identity}) == 0


def test_direct_insert_retains_owner_lock_while_waiting_for_actual_plan_source(own_lab):
    invitation = issue(own_lab); accept(own_lab, invitation)
    ready, state = Event(), {}
    def worker():
        with transaction(own_lab, GA) as db:
            state['pid'] = db.scalar(text('SELECT pg_backend_pid()')); ready.set()
            identity = publish(db, own_lab, invitation); db.commit(); return identity
    with own_lab['admin'].begin() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        blocker_pid = blocker.scalar(text('SELECT pg_backend_pid()'))
        blocker.execute(text('SELECT id FROM public.planes_generados WHERE id=:id FOR UPDATE'), {'id': own_lab['plans'][CA]}).scalar_one()
        future = pool.submit(worker); assert ready.wait(3)
        with own_lab['admin'].connect() as observer:
            wait_blocked(observer, state['pid'], blocker_pid)
            with pytest.raises(DBAPIError) as rejected:
                observer.execute(text('SELECT id FROM public.usuarios WHERE id=:actor FOR UPDATE NOWAIT'), {'actor': GA})
            assert rejected.value.orig.pgcode == '55P03'; observer.rollback()
        blocker.commit(); identity = future.result(timeout=8)
    with own_lab['admin'].begin() as db:
        db.execute(text('UPDATE public.usuarios SET activo=false WHERE id=:actor'), {'actor': GA})
        assert db.scalar(text('SELECT status FROM public.client_plan_publications WHERE id=:id'), {'id': identity}) == 'published'
    with transaction(own_lab, UA) as db:
        assert db.scalar(text('SELECT count(*) FROM public.client_plan_publications WHERE id=:id'), {'id': identity}) == 0


@pytest.mark.parametrize('field', ['source_object_id', 'object_key', 'content_type', 'byte_size', 'sha256', 'storage_backend'])
def test_partial_pdf_descriptor_never_passes_sql_unknown(own_lab, field):
    invitation = issue(own_lab); accept(own_lab, invitation)
    with transaction(own_lab, GA) as db:
        with pytest.raises(DBAPIError) as rejected:
            publish(db, own_lab, invitation, overrides={field: None})
        assert rejected.value.orig.pgcode in {'23514', '42501'}
    with own_lab['admin'].connect() as db:
        assert db.scalar(text('SELECT count(*) FROM public.client_plan_publications')) == 0


def test_exact_twenty_historical_policy_families_preserved_and_new_three_forced(own_lab):
    with own_lab['admin'].connect() as db:
        current = tenant_security_signature(db)
        assert [row for row in current['tables'] if row[0] not in NEW] == own_lab['previous']['tables']
        assert [row for row in current['policies'] if row[0] not in NEW] == own_lab['previous']['policies']
        assert current['set_tenant'] == own_lab['previous']['set_tenant']
        assert len([row for row in own_lab['previous']['tables'] if row[1] and row[2]]) == 20
        assert len([row for row in current['tables'] if row[1] and row[2]]) == 23
        assert len(inspect(db).get_table_names()) == 30
    with own_lab['app'].connect() as db:
        assert tuple(db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()) == (False, False, False, False)


@pytest.mark.parametrize('mutation', ['disabled_trigger', 'definer_function'])
def test_startup_rejects_trigger_or_privilege_drift_and_accepts_exact_restoration(own_lab, mutation):
    change, restore = ('ALTER TABLE public.client_account_links DISABLE TRIGGER r12_guard_link',
                       'ALTER TABLE public.client_account_links ENABLE TRIGGER r12_guard_link') if mutation == 'disabled_trigger' else (
                       'ALTER FUNCTION public.r12_actor_valid() SECURITY DEFINER',
                       'ALTER FUNCTION public.r12_actor_valid() SECURITY INVOKER')
    try:
        with own_lab['admin'].begin() as db:
            db.exec_driver_sql(change)
        with pytest.raises(RuntimeError, match='guards'):
            verify_runtime_schema(own_lab['admin'], expected_revision=HEAD)
    finally:
        with own_lab['admin'].begin() as db:
            db.exec_driver_sql(restore)
    verify_runtime_schema(own_lab['admin'], expected_revision=HEAD)
