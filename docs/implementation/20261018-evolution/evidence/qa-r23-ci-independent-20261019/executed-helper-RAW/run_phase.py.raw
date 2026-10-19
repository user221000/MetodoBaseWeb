"""Fresh full final guard and82+5 disjoint maintained cases, source fenced."""
from support import *
import xml.etree.ElementTree as ET
mode=sys.argv[1];assert mode in ['full','units82','process5']
phase=TEMP/mode;phase.mkdir(exist_ok=False);origin=phase/'origin';origin.mkdir();before=photo(mode+'-before')
env=os.environ.copy()
for name in list(env):
    key=name.upper()
    if key=='DATABASE_URL' or key.endswith('_DATABASE_URL') or key.startswith(('PG','AWS_','S3_','METODOBASE_TEST_','_METODOBASE_TEST')) or any(word in key for word in ['STRIPE','MERCADOPAGO','RESEND','SMTP','SENTRY','OPENAI_API']):env.pop(name,None)
env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',PYTHONPATH=str(ROOT)+os.pathsep+str(OUT),QA_HISTORY30_MODULE_ORIGIN_OUT=str(origin))
base=[str(PYTHON),'-X','utf8','-B']
if mode=='full':command=base+[str(OUT/'fenced_guard.py'),'--output',str(phase/'guard')]
else:
    names=['tests/test_member_ci_trust.py','tests/test_member_browser_gate.py','tests/test_reviewed_ci28_archive.py','tests/test_history_index_ci_trust.py','tests/test_followup_ci_trust.py'] if mode=='units82' else ['tests/test_followup_ci_process.py']
    env['METODOBASE_CI_PROCESS_EVIDENCE']=str(phase/'processes')
    command=base+['tests/run_isolated.py','-p','qa_r23_ci_origin',*names,'-q','--tb=short','--junitxml='+str(phase/'junit.xml')]
with (phase/'stdout.raw.log').open('xb') as stdout,(phase/'stderr.raw.log').open('xb') as stderr:result=subprocess.run(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=480)
after=photo(mode+'-after');assert before==after
checks={}
if mode=='full' and result.returncode==0:
    value=json.loads((phase/'guard/review.json').read_bytes())
    checks={'reports':len(value['reports']),'workflow':len(value['unauthorized_delta_canaries']),'old_parser':len(value['current_report_canaries']),'index_parser':len(value['index_report_canaries']),'followup_parser':len(value['followup_report_canaries']),'inert':len(value['current_inert_fixture_cases']),'Bash_blocks':value['bash_blocks'],'references':len(value['references'])}
    assert [checks[k] for k in ['reports','workflow','old_parser','index_parser','followup_parser','inert']]==[29,33,55,24,12,27]
elif mode!='full':
    cases=ET.parse(phase/'junit.xml').findall('.//testcase');expected=82 if mode=='units82' else 5
    checks={'expected':expected,'total':len(cases),'passed':sum(not any(c.find(tag)is not None for tag in ['failure','error','skipped']) for c in cases)}
    assert checks['total']==checks['passed']==expected
outputs=[]
for path in sorted(phase.rglob('*')):
    rel=path.relative_to(phase)
    if path.is_file() and not {'source','owned-probes'}.intersection(rel.parts):outputs.append(publish(path,mode+'-'+rel.as_posix().replace('/','--')))
save(mode+'-result.json',{'head':HEAD,'exit':result.returncode,'checks':checks,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'stable':True,'outputs':outputs,'scope':'Only local full/pure or inert Bash process checks, no actual HTTP/PostgreSQL/Chrome/Actions/Linux-image/SLO.'})
print(json.dumps({'mode':mode,'exit':result.returncode,'checks':checks,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'stable':True}),flush=True);assert result.returncode==0
