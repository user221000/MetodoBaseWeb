"""Serial maintained phases with source/package photos and immutable origins."""
from support import *
import xml.etree.ElementTree as ET
mode=sys.argv[1];assert mode in ['full','units','collect']
phase=TEMP/mode;phase.mkdir(exist_ok=False);origin=phase/'origin';origin.mkdir()
before=photo(mode+'-before')
env=os.environ.copy()
for name in list(env):
    key=name.upper()
    if key=='DATABASE_URL' or key.endswith('_DATABASE_URL') or key.startswith(('PG','AWS_','S3_','METODOBASE_TEST_','_METODOBASE_TEST')) or any(word in key for word in ['STRIPE','MERCADOPAGO','RESEND','SMTP','SENTRY','OPENAI_API']):env.pop(name,None)
env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',PYTHONPATH=str(OUT),QA_HISTORY30_MODULE_ORIGIN_OUT=str(origin))
base=[str(PYTHON),'-X','utf8','-B']
if mode=='full':command=base+[str(OUT/'fenced_guard.py'),'--output',str(phase/'guard')]
elif mode=='units':command=base+['tests/run_isolated.py','-p','qa_ci30_origin','tests/test_member_ci_trust.py','tests/test_member_browser_gate.py','tests/test_reviewed_ci28_archive.py','tests/test_history_index_ci_trust.py','-q','--tb=short','--junitxml='+str(phase/'junit.xml')]
else:command=base+['tests/run_isolated.py','-p','qa_ci30_origin','tests/integration_personal_history_index_migrations.py','tests/integration_personal_history_ordered_query.py','-k','postgresql','--collect-only','-q']
with (phase/'stdout.log').open('xb') as stdout,(phase/'stderr.log').open('xb') as stderr:result=subprocess.run(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=420)
after=photo(mode+'-after');assert before==after
checks={}
if mode=='full' and result.returncode==0:
    value=json.loads((phase/'guard/review.json').read_bytes())
    checks={'reports':len(value['reports']),'workflow_mutants':len(value['unauthorized_delta_canaries']),'old_report_canaries':len(value['current_report_canaries']),'new_report_canaries':len(value['index_report_canaries']),'inert_Bash':len(value['current_inert_fixture_cases']),'Bash_blocks':value['bash_blocks'],'references':len(value['references'])}
    assert {k:checks[k] for k in ['reports','workflow_mutants','old_report_canaries','new_report_canaries','inert_Bash']}==dict(reports=28,workflow_mutants=27,old_report_canaries=55,new_report_canaries=24,inert_Bash=27)
elif mode=='units':
    cases=ET.parse(phase/'junit.xml').findall('.//testcase');assert len(cases)==74
    checks={'cases':74,'passed':sum(not any(c.find(tag)is not None for tag in ['failure','error','skipped']) for c in cases)}
    assert checks['passed']==74
outputs=[]
for path in sorted(phase.rglob('*')):
    rel=path.relative_to(phase)
    if path.is_file() and not {'source','owned-probes'}.intersection(rel.parts):outputs.append(publish(path,mode+'-'+rel.as_posix().replace('/','--')))
save(mode+'-result.json',{'head':HEAD,'exit':result.returncode,'checks':checks,'sources_helpers_packages_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'outputs':outputs,'scope':'Maintained local pure/unit/collection only. No PostgreSQL, Chrome, Actions, Linux-image or SLO execution.'})
print(json.dumps({'mode':mode,'exit':result.returncode,'checks':checks,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'stable':True}),flush=True)
assert result.returncode==0
