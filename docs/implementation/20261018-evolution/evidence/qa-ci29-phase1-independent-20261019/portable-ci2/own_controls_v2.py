"""Independent filesystem/report/failure-order canaries; all process/HTTP seams synthetic."""
from support import *
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(ROOT))
from tests.e2e import run_member_link_browser as gate
before=photo('own-controls-v2-before')
phase=TEMP/'own-controls-v2';phase.mkdir(exist_ok=False);rows=[]
expected=('startup.json','browser-result.json','database-closure.json','http-trace.jsonl','final-identities.json','report.json','01-explicit-acceptance.png','02-real-recipient-publication.png','03-owner-own-external-contexts.png','04-account-switch-cleared.png')
assert gate.PUBLIC_FILES==expected
def artifacts(base):
    base.mkdir();private=base/'private';public=base/'public';private.mkdir();public.mkdir()
    (private/'mail.private.json').write_text(json.dumps([{'token':str(index)*43} for index in range(3)]))
    (private/'config.private.json').write_text('SYNTHETIC_PRIVATE_CONFIGURATION')
    (private/'deep-private').mkdir();(private/'deep-private/never-publish').write_text('private')
    for name in expected:(private/name).write_bytes(b'\x89PNG\r\n\x1a\nSYNTHETIC' if name.endswith('.png') else b'{}\n')
    return private,public
private,public=artifacts(phase/'allowlist-positive')
assert gate.publish(private,public)==list(expected) and sorted(p.name for p in public.iterdir())==sorted(expected)
rows.append({'case':'exact-independent-ten-file-allowlist-ignores-private-and-nested-files','passed':True})
for index,name in enumerate(expected):
    private,public=artifacts(phase/('missing-'+str(index)));(private/name).unlink()
    try:gate.publish(private,public)
    except AssertionError:rejected=True
    else:rejected=False
    rows.append({'case':'missing-'+name+'-publishes-nothing','passed':rejected and list(public.iterdir())==[]})
for mode in ['bearer-in-trace','invitation-in-identities','directory-in-allowlist']:
    private,public=artifacts(phase/mode)
    if mode=='bearer-in-trace':(private/'http-trace.jsonl').write_bytes(b'A'*40+b'.'+b'b'*64)
    elif mode=='invitation-in-identities':(private/'final-identities.json').write_text('0'*43)
    else:(private/'report.json').unlink();(private/'report.json').mkdir()
    try:gate.publish(private,public)
    except AssertionError:rejected=True
    else:rejected=False
    rows.append({'case':mode+'-publishes-nothing','passed':rejected and list(public.iterdir())==[]})
# Execute the actual normalizer and canonical parser against retained accepted output and altered copies.
retained=OUT.parent.parent/'qa-r12-composition29-independent-20261019/afterec/browser-v8-browser-result.json'
accepted=json.loads(retained.read_bytes());assert accepted['total']==accepted['passed']==16
normalizer=ROOT/'tests/e2e/normalize_member_link_report.py'
for mode in ['positive-retained','wrong-head','wrong-total','false-criterion','duplicate-label','missing-criterion-field','page-error','API-double','other-origin','external-expected-origin']:
    case=phase/('normalize-'+mode);case.mkdir();data=deepcopy(accepted)
    head=accepted['head'];origin=accepted['network']['first_party_origin']
    if mode=='wrong-head':data['head']='a'*40
    elif mode=='wrong-total':data['total']=17
    elif mode=='false-criterion':data['report'][0]['passed']=False
    elif mode=='duplicate-label':data['report'][1]['case']=data['report'][0]['case']
    elif mode=='missing-criterion-field':del data['report'][0]['passed']
    elif mode=='page-error':data['page_errors']=['SYNTHETIC_PAGE_ERROR']
    elif mode=='API-double':data['network']['API_doubles']=True
    elif mode=='other-origin':data['network']['first_party_origin']='http://127.0.0.1:18889'
    elif mode=='external-expected-origin':origin='https://example.invalid'
    raw=case/'input.json';raw.write_text(json.dumps(data));output=case/'report.json'
    result=subprocess.run([str(PYTHON),'-X','utf8','-B',str(normalizer),'--input',str(raw),'--output',str(output),'--expected-head',head,'--expected-origin',origin],cwd=ROOT,capture_output=True,timeout=15)
    (case/'stdout.log').write_bytes(result.stdout);(case/'stderr.log').write_bytes(result.stderr)
    positive=mode=='positive-retained'
    assert (result.returncode==0)==positive and output.exists()==positive
    if positive:
        parser=subprocess.run([str(PYTHON),str(ROOT/'scripts/check_frontend_report.py'),str(output),'--format','counts','--minimum','16'],cwd=ROOT,capture_output=True,timeout=15)
        assert parser.returncode==0
    rows.append({'case':'actual-normalizer-'+mode,'passed':True,'exit':result.returncode,'tests_rerun':0})
# Whole orchestrator sequencing with synthetic process/HTTP seams, never browser or PG acceptance.
modules=phase/'synthetic-node-modules'
for name in ['playwright-core/package.json','axe-core/axe.min.js']:
    p=modules/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
chrome=phase/'synthetic-chrome';chrome.write_text('never executed')
configuration={'METODOBASE_TEST_MIGRATOR_URL':'postgresql://metodobase_test_synthetic:synthetic-only@127.0.0.1:55483/metodobase_test_orchestration','METODOBASE_TEST_POSTGRES_URL':'postgresql://metodobase_test_synthetic:synthetic-only@127.0.0.1:55483/metodobase_test_orchestration','METODOBASE_TEST_PG_BIN':str(phase),'QA_NODE_MODULES':str(modules),'QA_CHROME':str(chrome)}
for mode in ['synthetic-positive','invalid-startup','browser-failure','database-remains']:
    private,_=artifacts(phase/('orchestration-'+mode));(private/'config.private.json').unlink();public=private.parent/'gate-output';calls=[]
    marker={'fixture':'r12-real-postgres29','head':HEAD,'pid':12345,'port':18889,'database_kind':'postgresql','executed_revision':gate.REVISION,'model_target_revision':gate.REVISION,'model_tables':29,'actual_tables':30,'application_role_restricted_nonowner':True,'runtime_pool_size':20,'runtime_max_overflow':10,'R12_API_doubles':False,'first_party_origin':'http://127.0.0.1:18889'}
    if mode=='invalid-startup':marker['model_target_revision']='20261019_account_recovery'
    class Process:
        returncode=None
        def __init__(self,*args,**kwargs):(private/'startup.json').write_text(json.dumps(marker));calls.append('start-owned-fixture')
        def poll(self):return self.returncode
        def wait(self,timeout):
            assert (private/'control.private.json').is_file();calls.append('cooperative-stop-before-publication');self.returncode=0
            name='metodobase_test_migrations_'+'a'*12
            (private/'database-closure.json').write_text(json.dumps({'exact_owned_names':[name],'count':1,'remaining':[name] if mode=='database-remains' else [],'all_owned_absent':mode!='database-remains','fixture_error_class':None}))
            return 0
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):return False
    def execute(command,*args,**kwargs):
        browser=any(str(item).endswith('member_link_browser.cjs') for item in command)
        calls.append('browser' if browser else 'normalizer-or-parser')
        return SimpleNamespace(returncode=1 if browser and mode=='browser-failure' else 0,stdout=b'',stderr=b'')
    def read_git(command,**kwargs):return HEAD+'\n' if 'rev-parse' in command else b''
    with patch.dict(os.environ,configuration),patch.object(gate.shutil,'which',return_value='synthetic-node'),patch.object(gate.tempfile,'mkdtemp',return_value=str(private)),patch.object(gate,'listener_closed',return_value=True),patch.object(gate,'urlopen',return_value=Response()),patch.object(gate.subprocess,'check_output',side_effect=read_git),patch.object(gate.subprocess,'Popen',Process),patch.object(gate.subprocess,'run',side_effect=execute):
        try:gate.run(public,18889)
        except RuntimeError:rejected=True
        else:rejected=False
    positive=mode=='synthetic-positive';receipt=json.loads((public/'receipt.json').read_bytes())
    assert rejected!=positive and receipt['completed']==positive
    assert sorted(p.name for p in public.iterdir())==sorted([*expected,'receipt.json'] if positive else ['receipt.json'])
    if mode=='invalid-startup':assert 'browser' not in calls
    if mode=='browser-failure':assert 'normalizer-or-parser' not in calls
    rows.append({'case':'synthetic-orchestration-'+mode,'passed':True,'calls':calls,'completed':receipt['completed'],'real_processes_HTTP_PG':False})
after=photo('own-controls-v2-after');assert before==after and all(row['passed'] for row in rows)
save('own-controls-v2-result.json',{'head':HEAD,'total':len(rows),'passed':sum(row['passed'] for row in rows),'results':rows,'source_helpers_packages_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'retained_browser_input_sha256':sha(retained.read_bytes()),'scope':'Local filesystem/actual report normalization and synthetic orchestrator process+HTTP seams. No new browser, real HTTP, PostgreSQL, Actions or provider execution. Retained16 are not counted as new tests.'})
print(json.dumps({'own_canaries':len(rows),'passed':sum(row['passed'] for row in rows),'sources':before['source_count'],'helpers':before['helper_count'],'packages':89}))
