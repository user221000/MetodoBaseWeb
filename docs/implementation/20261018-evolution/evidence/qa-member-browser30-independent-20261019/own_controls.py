"""Current30 witness/report/failure-order controls; no actual Chrome, HTTP or PG."""
from support import *
import contextlib,io
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(ROOT))
from tests.e2e import run_member_link_browser as gate
from web.database.alembic.history_index_contract_v1 import expected_history_index
before=photo('own-before');phase=TEMP/'own-controls';phase.mkdir(exist_ok=False);rows=[]
canonical=json.loads((ROOT/'web/database/alembic/schema_targets/20261019_personal_history_index_postgresql.json').read_bytes())['history_order_index']
assert canonical==expected_history_index('postgresql')
def marker():return {'fixture':'r12-real-postgres30','head':HEAD,'pid':12345,'port':18898,'database_kind':'postgresql','executed_revision':gate.REVISION,'model_target_revision':gate.REVISION,'business_contract_revision':'20261019_client_account_links','history_order_index':deepcopy(canonical),'model_tables':29,'actual_tables':30,'application_role_restricted_nonowner':True,'runtime_pool_size':20,'runtime_max_overflow':10,'R12_API_doubles':False,'first_party_origin':'http://127.0.0.1:18898'}
positive=marker();positive['history_order_index']=dict(reversed(list(positive['history_order_index'].items())));gate.validate_startup(positive,HEAD,18898)
rows.append({'case':'literal-frozen-target-witness-accepts-reordered-object-keys','passed':True})
mutations=[('swapped-columns','columns',['id_cliente','gym_id','fecha_generacion','id']),('id-ascending','indoption',[0,0,1,0]),('timestamp-NULLS-FIRST','indoption',[0,0,3,1]),('included-extra-column','all_columns',5),('other-index-name','name','other-history-index'),('coerced-unique-zero','unique',0),('missing-id-key','columns',['gym_id','id_cliente','fecha_generacion']),('swapped-opclasses','operator_classes',['pg_catalog.text_ops','pg_catalog.text_ops','pg_catalog.int4_ops','pg_catalog.timestamp_ops']),('different-collation','collations',['pg_catalog.C','pg_catalog.default',None,None]),('string-sort-bits','indoption',['0','0','1','1'])]
for label,key,value in mutations:
    data=marker();data['history_order_index'][key]=value
    try:gate.validate_startup(data,HEAD,18898)
    except AssertionError:rejected=True
    else:rejected=False
    assert rejected;rows.append({'case':label+'-rejected','passed':True})
normalizer=ROOT/'tests/e2e/normalize_member_link_report.py'
author=ROOT/'docs/implementation/20261018-evolution/evidence/member-browser30-final-author-20261019/public/browser-result.json'
accepted=json.loads(author.read_bytes())
old=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/qa-r12-composition29-independent-20261019/afterec/browser-v8-browser-result.json')
for label in ['retained-current30-positive','actual-retained29-rejected','other-head-rejected','existing-output-preserved']:
    case=phase/label;case.mkdir();data=deepcopy(accepted);head=accepted['head'];output=case/'report.json'
    if label=='actual-retained29-rejected':data=json.loads(old.read_bytes());head=data['head']
    elif label=='other-head-rejected':head=HEAD
    elif label=='existing-output-preserved':output.write_bytes(b'OWN_EXISTING_UNCHANGED')
    source=case/'input.json';source.write_text(json.dumps(data))
    result=subprocess.run([str(PYTHON),'-X','utf8','-B',str(normalizer),'--input',str(source),'--output',str(output),'--expected-head',head,'--expected-origin',data['network']['first_party_origin'],'--expected-revision','20261019_personal_history_index'],cwd=ROOT,capture_output=True,timeout=15)
    (case/'stdout.log').write_bytes(result.stdout);(case/'stderr.log').write_bytes(result.stderr)
    positive=label=='retained-current30-positive';assert (result.returncode==0)==positive
    if label=='existing-output-preserved':assert output.read_bytes()==b'OWN_EXISTING_UNCHANGED'
    elif not positive:assert not output.exists()
    rows.append({'case':label,'passed':True,'normalizer_exit':result.returncode,'retained_browser_criteria_not_rerun':True})
modules=phase/'synthetic-node-modules'
for name in ['playwright-core/package.json','axe-core/axe.min.js']:
    path=modules/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}')
chrome=phase/'synthetic-chrome';chrome.write_text('never executed')
environment={'METODOBASE_TEST_MIGRATOR_URL':'postgresql://metodobase_test_synthetic:synthetic-only@127.0.0.1:55483/metodobase_test_orchestration','METODOBASE_TEST_POSTGRES_URL':'postgresql://metodobase_test_synthetic:synthetic-only@127.0.0.1:55483/metodobase_test_orchestration','METODOBASE_TEST_PG_BIN':str(phase),'QA_NODE_MODULES':str(modules),'QA_CHROME':str(chrome)}
for label in ['synthetic-positive','wrong-witness','missing-witness','business-physical-confusion','missing-JSON','malformed-JSON','normalizer-failure']:
    base=phase/('orchestrator-'+label);base.mkdir();private=base/'private';private.mkdir();public=base/'public';calls=[]
    (private/'mail.private.json').write_text(json.dumps([{'token':str(index)*43} for index in range(3)]))
    for name in gate.PUBLIC_FILES:(private/name).write_bytes(b'\x89PNG\r\n\x1a\nSYNTHETIC' if name.endswith('.png') else b'{}\n')
    startup=marker()
    if label=='wrong-witness':startup['history_order_index']['indoption']=[0,0,0,1]
    elif label=='missing-witness':del startup['history_order_index']
    elif label=='business-physical-confusion':startup['model_tables']=30
    class Process:
        returncode=None
        def __init__(self,*args,**kwargs):
            calls.append('start-synthetic-fixture')
            if label=='missing-JSON':(private/'startup.json').unlink()
            else:(private/'startup.json').write_bytes(b'{' if label=='malformed-JSON' else json.dumps(startup).encode())
        def poll(self):return self.returncode
        def wait(self,timeout):
            assert (private/'control.private.json').is_file();calls.append('cooperative-owned-stop');self.returncode=0
            (private/'database-closure.json').write_text(json.dumps({'exact_owned_names':['metodobase_test_migrations_'+'a'*12],'count':1,'remaining':[],'all_owned_absent':True,'fixture_error_class':None}));return 0
    class Response:
        status=200
        def __enter__(self):calls.append('health');return self
        def __exit__(self,*args):return False
    def execute(command,*args,**kwargs):
        normalize=any(str(value).endswith('normalize_member_link_report.py') for value in command)
        if normalize:assert command[command.index('--expected-revision')+1]=='20261019_personal_history_index'
        calls.append('normalizer' if normalize else 'browser' if any(str(value).endswith('member_link_browser.cjs') for value in command) else 'parser')
        return SimpleNamespace(returncode=1 if normalize and label=='normalizer-failure' else 0,stdout=b'',stderr=b'')
    read_git=lambda command,**kwargs:HEAD+'\n' if 'rev-parse' in command else b''
    clock=iter([0,0,100]);clock_fn=lambda:next(clock,100)
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ,environment));stack.enter_context(patch.object(gate.shutil,'which',return_value='synthetic-node'));stack.enter_context(patch.object(gate.tempfile,'mkdtemp',return_value=str(private)));stack.enter_context(patch.object(gate,'listener_closed',return_value=True));stack.enter_context(patch.object(gate,'urlopen',return_value=Response()));stack.enter_context(patch.object(gate.subprocess,'check_output',side_effect=read_git));stack.enter_context(patch.object(gate.subprocess,'Popen',Process));stack.enter_context(patch.object(gate.subprocess,'run',side_effect=execute))
        if label in ['missing-JSON','malformed-JSON']:stack.enter_context(patch.object(gate.time,'monotonic',side_effect=clock_fn));stack.enter_context(patch.object(gate.time,'sleep',return_value=None))
        capture=io.StringIO()
        with contextlib.redirect_stdout(capture):
            try:gate.run(public,18898)
            except RuntimeError:rejected=True
            else:rejected=False
    (base/'synthetic-orchestrator.stdout.log').write_text(capture.getvalue())
    positive=label=='synthetic-positive';receipt=json.loads((public/'receipt.json').read_bytes());assert rejected!=positive and receipt['completed']==positive
    assert sorted(path.name for path in public.iterdir())==sorted([*gate.PUBLIC_FILES,'receipt.json'] if positive else ['receipt.json'])
    if label in ['wrong-witness','missing-witness','business-physical-confusion','missing-JSON','malformed-JSON']:assert 'health' not in calls and 'browser' not in calls
    if label=='normalizer-failure':assert 'parser' not in calls
    rows.append({'case':'synthetic-orchestrator-'+label,'passed':True,'calls':calls,'completed':receipt['completed'],'real_Chrome_HTTP_PG':False})
after=photo('own-after');assert before==after
save('own-controls-result.json',{'head':HEAD,'passed':len(rows),'total':len(rows),'results':rows,'sources_helpers_packages_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'scope':'Physical-witness validation, actual normalization of retained reports, and synthetic orchestration sequencing only. Retained16 or synthetic positive stdout passed16 are not new browser criteria; no Chrome/HTTP/PG execution.'})
print(json.dumps({'passed':len(rows),'total':len(rows),'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'actual_Chrome_HTTP_PG':False}))
