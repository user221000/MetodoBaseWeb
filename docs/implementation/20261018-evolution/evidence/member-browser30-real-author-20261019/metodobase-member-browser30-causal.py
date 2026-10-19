"""One owned route probe isolates the missing personal-profile precondition."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
import uuid
import zipfile

ROOT=Path('F:/mb-member-browser30-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/member-browser30-real-author-20261019'
TEMP=Path('C:/Users/Consu/AppData/Local/Temp')
RUN=TEMP/'metodobase-member-browser30-author-8x89ac13/real30'
phase=Path(json.loads((RUN/'diagnostic-phase.private.json').read_bytes())['phase'])
private=json.loads((TEMP/'metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
sha=lambda raw:hashlib.sha256(raw).hexdigest()
tokens=[row['token'].encode() for row in json.loads((phase/'mail.private.json').read_bytes())]
secrets=tokens+[private[k].encode() for k in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']]
raw_names=['startup.json','browser-result.json','database-closure.json','fixture.private.log',
           'http-trace.jsonl','report.json','01-explicit-acceptance.png','02-real-recipient-publication.png',
           '03-owner-own-external-contexts.png','04-account-switch-cleared.png']
raw_records=[]
with zipfile.ZipFile(OUT/'failed-run-exact-nonsecret.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name in raw_names:
        if not (phase/name).is_file():continue
        raw=(phase/name).read_bytes()
        assert not any(secret in raw for secret in secrets)
        archive.writestr(name,raw)
        raw_records.append({'path':name,'sha256_raw':sha(raw),'secret_filter_matches':0})
    for name in ['manager.stdout.raw.log','manager.stderr.raw.log']:
        raw=(RUN/name).read_bytes();assert not any(secret in raw for secret in secrets)
        archive.writestr(name,raw)
    archive.writestr('receipt.json',(RUN/'public/receipt.json').read_bytes())
    archive.writestr('driver-original.py',(TEMP/'metodobase-member-browser30-real.py').read_bytes())
(OUT/'failed-raw-classification.json').write_text(json.dumps(raw_records,indent=2)+'\n',encoding='utf8')
assert json.loads((OUT/'before.json').read_bytes())==json.loads((OUT/'after.json').read_bytes())
current=(ROOT/'web/routes/usuario.py').read_bytes()
historical=subprocess.check_output(['git','--no-replace-objects','show','67ae4664ed091f05568f49e366a67d6846d8a728:web/routes/usuario.py'],cwd=ROOT)
def function(raw,name):
    return next(node for node in ast.parse(raw.decode('utf8')).body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name)
for name in ['_get_or_create_self_cliente','get_perfil']:
    assert ast.dump(function(current,name),include_attributes=False)==ast.dump(function(historical,name),include_attributes=False)
accepted=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/ci-member-links29-browser-author-20261019/public')
accepted_identity=json.loads((accepted/'final-identities.json').read_bytes())
accepted_trace=[json.loads(line) for line in (accepted/'http-trace.jsonl').read_text(encoding='utf8').splitlines()]
assert accepted_identity['baseline']['other']['profiles']==accepted_identity['final']['other']['profiles']==[]
before_comparison={'route_helpers_ast_exact_vs_accepted67':True,
    'accepted29_final_other_profile_empty':True,
    'accepted29_trace_profile_get_count':sum(row['path']=='/api/usuario/perfil' for row in accepted_trace),
    'failed30_trace_profile_get_count':sum(json.loads(line)['path']=='/api/usuario/perfil' for line in (phase/'http-trace.jsonl').read_text(encoding='utf8').splitlines()),
    'accepted29_identity_raw_sha256':sha((accepted/'final-identities.json').read_bytes()),
    'accepted29_trace_raw_sha256':sha((accepted/'http-trace.jsonl').read_bytes()),
    'classification':'16 browser criteria passed; existing fixture final-identity assertion rejected teardown. No business/index regression is inferred from that alone.'}
(OUT/'comparison-before-causal-probe.json').write_text(json.dumps(before_comparison,indent=2)+'\n',encoding='utf8')
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from tests.isolation import prepare_environment,block_external_sockets
own=prepare_environment(discard_inherited=True);block_external_sockets()
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:os.environ[key]=private[key]
from tests import integration_schema_migrations as migrations
from tests import integration_client_link_services as shared
from sqlalchemy import select
from sqlalchemy.orm import Session,sessionmaker
from web.database import engine as database
from web.database.models import Cliente,Usuario
from web import auth
from web.main_web import create_app
from fastapi.testclient import TestClient
from unittest.mock import patch
class Factory:
    def mktemp(self,label):
        path=own/(label+'-'+uuid.uuid4().hex);path.mkdir();return path
generator=shared.link_db.__wrapped__(SimpleNamespace(param='postgresql'),Factory())
admin=app=None;name=None;proof=None
try:
    admin,app=next(generator)
    name=admin.url.database
    assert re.fullmatch(r'metodobase_test_migrations_[0-9a-f]{12}',name)
    migrations.run_migration(admin.url.render_as_string(hide_password=False),'db_bootstrap.py','--revision','20261019_personal_history_index')
    case=shared.case.__wrapped__((admin,app))
    password='Synthetic browser profile precondition 42!'
    with Session(admin) as db:
        row=db.get(Usuario,case['other']);row.password_hash=auth.hash_password(password);db.commit()
    def snapshot():
        with Session(admin) as db:
            user=db.get(Usuario,case['other'])
            return {'user':{'id':user.id,'tipo':user.tipo,'role':user.role.value,'team_gym_id':user.team_gym_id,'session_version':user.session_version},
                'profiles':[{'id':row.id_cliente,'gym_id':row.gym_id} for row in db.scalars(select(Cliente).where(Cliente.gym_id==case['other']))],
                'professional_clients':[(row.id_cliente,row.gym_id) for row in db.scalars(select(Cliente).where(Cliente.gym_id.in_([case['gym'],case['othergym']])).order_by(Cliente.id_cliente))]}
    initial=snapshot();assert initial['profiles']==[]
    with patch.object(database,'_engine',app),patch.object(database,'_SessionLocal',sessionmaker(bind=app,autoflush=False,expire_on_commit=False)):
        actual=create_app()
        with TestClient(actual,raise_server_exceptions=False) as client:
            login=client.post('/api/auth/login',json={'email':case['other']+'@example.invalid','password':password})
            assert login.status_code==200
            headers={'Authorization':'Bearer '+login.json()['token']}
            logged_in=snapshot();assert logged_in==initial
            response=client.get('/api/usuario/perfil',headers=headers)
            assert response.status_code==200
            after=snapshot()
            assert len(after['profiles'])==1 and after['profiles'][0]['gym_id']==case['other']
            assert after['user']==initial['user'] and after['professional_clients']==initial['professional_clients']
            repeated=client.get('/api/usuario/perfil',headers=headers)
            assert repeated.status_code==200 and snapshot()==after
    proof={'database_name':name,'login_status':200,'profile_status':200,'repeat_profile_status':200,
           'before_profile_count':0,'after_profile_count':1,'repeat_profile_count':1,
           'same_active_viewer_subject':initial['user'],'before':initial,'after':after,
           'professional_clients_unchanged':True,'account_role_team_sv_unchanged':True,
           'cause':'Login alone does not create a profile. Subsequent ordinary GET /api/usuario/perfil creates its own missing profile once; it never adopts a professional client.',
           'scope':'One new owned real PostgreSQL30 UUID, actual web factory/auth/route and app RLS role; no browser, API mock or production source edit.'}
finally:
    generator.close()
    import psycopg2
    names=[name,'metodobase_test_migrations_1c1d356de44e'] if name else ['metodobase_test_migrations_1c1d356de44e']
    with psycopg2.connect(private['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1),connect_timeout=5) as db,db.cursor() as cursor:
        cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)',(names,));remaining=[row[0] for row in cursor.fetchall()]
    (OUT/'causal-probe-database-closure.json').write_text(json.dumps({'exact_own_names':names,'remaining':remaining},indent=2)+'\n',encoding='utf8')
    assert remaining==[]
if proof:
    (OUT/'causal-profile-bootstrap.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'owned_uuid':name,'login200':True,'profile200':True,'before':0,'after':1,'repeat':1,'identity_and_professional_clients_unchanged':True,'two_own_uuids_absent':True}))
