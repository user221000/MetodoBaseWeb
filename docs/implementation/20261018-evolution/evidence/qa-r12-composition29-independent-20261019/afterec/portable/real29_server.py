"""Actual migrated29/restricted-PG/browser fixture. Only mail transport is doubled.

No fixture HTTP endpoints, API doubles or invitation proofs in public output.
The filesystem control channel is private to this process and the local driver.
"""
import sys
sys.dont_write_bytecode=True
import argparse,hashlib,json,os,re,subprocess,threading,time,uuid,tempfile
from html import unescape
from pathlib import Path
from types import SimpleNamespace

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--config',required=True);parser.add_argument('--head',required=True)
    parser.add_argument('--port',required=True,type=int)
    args=parser.parse_args();root=Path(args.root).resolve();out=Path(args.out).resolve()
    assert out.is_relative_to(Path(tempfile.gettempdir()).resolve()) and out.is_dir()
    assert 1024<args.port<65536
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==args.head
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=root).strip()
    os.chdir(root);sys.path.insert(0,str(root))
    from tests.isolation import prepare_environment,block_external_sockets,validate_postgres_test_url
    own=prepare_environment(discard_inherited=True).resolve();block_external_sockets()
    configuration=json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
    for name in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:
        os.environ[name]=configuration[name]
    for name in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']:
        validate_postgres_test_url(os.environ[name])
    origin='http://127.0.0.1:'+str(args.port)
    os.environ.update(BASE_URL=origin,CORS_ORIGINS=origin,RATE_LIMIT_ENABLED='true')
    from sqlalchemy import inspect,select,text
    from sqlalchemy.orm import Session,sessionmaker
    from tests import integration_schema_migrations as migrations
    from tests import integration_client_link_services as shared
    from web.database import engine as database
    from web.database.models import Base,Cliente,ClientAccountLink,ClientLinkInvitation,Usuario
    from web.database.schema_control import expected_head,verify_runtime_schema
    from web.database.tenant_context import current_tenant
    from web import auth
    from web.services import email_service
    from web.settings import get_settings
    original=migrations.migration_database.__wrapped__;owned=[]
    def observed(request,tmp_path):
        generator=original(request,tmp_path)
        try:
            value=next(generator);owned.append(value[1].url.database)
            (out/'owned-database.json').write_text(json.dumps({'names':owned,'fixture_pid':os.getpid()})+'\n',encoding='utf8')
            yield value
        finally:generator.close()
    migrations.migration_database.__wrapped__=observed
    class TempFactory:
        def mktemp(self,label):
            target=own/(label+'-'+uuid.uuid4().hex);target.mkdir();return target
    generator=shared.link_db.__wrapped__(SimpleNamespace(param='postgresql'),TempFactory())
    admin=app=None;server=None;control=None;stop=threading.Event();error=None
    write_lock=threading.Lock()
    try:
        admin,app=next(generator)
        # Shared functional fixture pool1 cannot serve dashboard's concurrent reads.
        # Use actual runtime construction with exactly the same restricted URL.
        os.environ['DATABASE_URL']=app.url.render_as_string(hide_password=False)
        os.environ.pop('DB_POOL_SIZE',None);os.environ.pop('DB_MAX_OVERFLOW',None)
        database._engine=None;database._SessionLocal=None
        app=database.get_engine()
        from web.database.tenant_policy import verify_application_database_role
        verify_application_database_role(app)
        assert app.pool.size()==20 and app.pool._max_overflow==10
        assert database._SessionLocal.kw['bind'] is app
        settings=get_settings();settings.BASE_URL=origin;settings.RESEND_API_KEY='synthetic-local-transport-only'
        settings.CORS_ORIGINS=[origin]
        verify_runtime_schema(app,require_revision=True)
        assert expected_head()=='20261019_client_account_links'
        with app.connect() as connection:
            flags=connection.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()
            assert tuple(flags)==(False,False,False,False)
            assert connection.execute(text('SELECT pg_get_userbyid(datdba)<>current_user FROM pg_database WHERE datname=current_database()')).scalar_one()
            actual_revision=connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
        assert actual_revision==expected_head()
        case=shared.case.__wrapped__((admin,app));password='Synthetic browser password 42!'
        personal=str(uuid.uuid4())
        with Session(admin) as db:
            for key,label in [('gym','Synthetic owner A'),('othergym','Synthetic owner B'),('person','Synthetic recipient'),('other','Synthetic other account')]:
                row=db.get(Usuario,case[key]);row.password_hash=auth.hash_password(password);row.nombre=label
            db.add(Cliente(id_cliente=personal,gym_id=case['person'],nombre='Preserved personal profile',notas='PRIVATE_PERSONAL_PROFILE'))
            db.commit()
        plan_a,descriptor_a,content_a=shared.source(case,marker='SYNTHETIC_BROWSER_A')
        external=dict(case,gym=case['othergym'],client=case['otherclient'])
        plan_b,descriptor_b,content_b=shared.source(external,marker='SYNTHETIC_BROWSER_B')
        def identity_snapshot():
            with Session(admin) as db:
                return {key:{'id':case[key],'tipo':(u:=db.get(Usuario,case[key])).tipo,'role':u.role.value,'team_gym_id':u.team_gym_id,
                     'session_version':u.session_version,'profiles':list(db.scalars(select(Cliente.id_cliente).where(Cliente.gym_id==case[key]).order_by(Cliente.id_cliente)))}
                     for key in ['gym','othergym','person','other']}
        baseline=identity_snapshot()
        metadata={'origin':origin,'head':args.head,'ids':{key:case[key] for key in ['gym','othergym','person','other','client','otherclient']},
                  'emails':{key:(case['email'] if key=='person' else case[key]+'@example.invalid') for key in ['gym','othergym','person','other']},
                  'password':password,'plans':{'gym':plan_a,'othergym':plan_b},'private_personal_profile_id':personal,
                  'pdfs':{'gym':{'sha256':hashlib.sha256(content_a).hexdigest(),'bytes':len(content_a)},
                          'othergym':{'sha256':hashlib.sha256(content_b).hexdigest(),'bytes':len(content_b)}},'baseline':baseline}
        (out/'metadata.private.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf8')
        (out/'mail.private.json').write_text('[]\n',encoding='utf8')
        def local_mail(recipient,subject,html,**kwargs):
            assert current_tenant.get()==''
            found=re.search(re.escape(origin)+r'/auth/accept-client-link#token=([A-Za-z0-9_-]{43})',unescape(html))
            if found:
                token=found.group(1);digest=hashlib.sha256(('client-account-invite-v1:'+token).encode()).hexdigest()
                with Session(admin) as db:
                    row=db.scalar(select(ClientLinkInvitation).where(ClientLinkInvitation.token_hash==digest,ClientLinkInvitation.recipient_email==recipient))
                    assert row is not None and row.status=='pending'
                    invitation_id=row.id;link_id=row.link_id
                with write_lock:
                    messages=json.loads((out/'mail.private.json').read_bytes())
                    messages.append({'recipient':recipient,'token':token,'url':found.group(0),'invitation_id':invitation_id,'link_id':link_id,
                                     'committed_pending_witness':True,'tenant_context_empty':True})
                    temporary=out/'mail.pending.private.json';temporary.write_text(json.dumps(messages,indent=2)+'\n',encoding='utf8')
                    temporary.replace(out/'mail.private.json')
            return True
        email_service._send=local_mail
        from web.main_web import create_app
        actual=create_app()
        class Trace:
            def __init__(self,application):self.application=application
            async def __call__(self,scope,receive,send):
                async def recorded(message):
                    if scope['type']=='http' and message['type']=='http.response.start':
                        headers={k.decode().lower():v.decode() for k,v in message.get('headers',[])}
                        row={'method':scope['method'],'path':scope['path'],'status':message['status'],
                             'cache_control':headers.get('cache-control'),'referrer_policy':headers.get('referrer-policy'),
                             'request_id_present':bool(headers.get('x-request-id'))}
                        with write_lock:
                            with (out/'http-trace.jsonl').open('a',encoding='utf8') as stream:stream.write(json.dumps(row)+'\n')
                    await send(message)
                await self.application(scope,receive,recorded)
        import uvicorn
        server=uvicorn.Server(uvicorn.Config(Trace(actual),host='127.0.0.1',port=args.port,log_level='warning',access_log=False))
        def controller():
            seen=set()
            while not stop.wait(.05):
                command=out/'control.private.json'
                if not command.exists():continue
                try:value=json.loads(command.read_bytes())
                except json.JSONDecodeError:continue
                if value.get('id') in seen:continue
                assert set(value)<= {'id','action','actor'} and value['action'] in {'snapshot','bump_sv','stop'}
                seen.add(value['id'])
                if value['action']=='bump_sv':
                    assert value['actor']=='person'
                    with Session(admin) as db:
                        user=db.get(Usuario,case['person']);user.session_version+=1;db.commit()
                if value['action']=='stop':server.should_exit=True
                state=identity_snapshot()
                with Session(admin) as db:
                    links=[{'id':v.id,'status':v.status,'user_id':v.user_id} for v in db.scalars(select(ClientAccountLink))]
                temporary=out/'control-ack.pending.private.json'
                temporary.write_text(json.dumps({'id':value['id'],'identities':state,'links':links})+'\n',encoding='utf8')
                temporary.replace(out/'control-ack.private.json')
        control=threading.Thread(target=controller,daemon=True);control.start()
        marker={'fixture':'r12-real-postgres29','head':args.head,'pid':os.getpid(),'port':args.port,
                'database_kind':'postgresql','executed_revision':actual_revision,'model_target_revision':expected_head(),
                'model_tables':len(Base.metadata.tables),'actual_tables':len(inspect(admin).get_table_names()),
                'application_role_restricted_nonowner':True,'runtime_pool_size':app.pool.size(),'runtime_max_overflow':app.pool._max_overflow,'mail_transport':'private-filesystem-after-commit-witness',
                'R12_API_doubles':False,'source_plan_pdf':'Synthetic four-meal JSON and labelled local bytes; not a generation/provider demonstration',
                'outbound_socket_guard':'loopback-only in-process','first_party_origin':origin}
        (out/'startup.json').write_text(json.dumps(marker,indent=2)+'\n',encoding='utf8')
        print(json.dumps(marker),flush=True)
        server.run()
        final=identity_snapshot()
        for key in ['gym','othergym','other']:assert final[key]==baseline[key]
        assert {k:v for k,v in final['person'].items() if k!='session_version'}=={k:v for k,v in baseline['person'].items() if k!='session_version'}
        assert final['person']['session_version'] in {0,1}
        (out/'final-identities.json').write_text(json.dumps({'baseline':baseline,'final':final,'preserved':True},indent=2)+'\n',encoding='utf8')
    except BaseException as caught:
        error=type(caught).__name__
        raise
    finally:
        stop.set()
        if control:control.join(timeout=3)
        if app is not None:app.dispose()
        generator.close()
        import psycopg2
        with psycopg2.connect(configuration['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1)) as db,db.cursor() as cursor:
            cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)',(owned,));remaining=[row[0] for row in cursor.fetchall()]
        (out/'database-closure.json').write_text(json.dumps({'exact_owned_names':owned,'count':len(owned),'remaining':remaining,'all_owned_absent':not remaining,'fixture_error_class':error},indent=2)+'\n',encoding='utf8')
        assert len(owned)==1 and not remaining

if __name__=='__main__':main()
