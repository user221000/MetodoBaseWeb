"""Execute maintained50 browser-gate unit cases only, fenced to exact WT30 source."""
from support import *
import xml.etree.ElementTree as ET
phase=TEMP/'unit50';phase.mkdir(exist_ok=False);evidence=phase/'evidence';evidence.mkdir()
before=photo('unit50-before')
env=os.environ.copy()
for name in list(env):
    key=name.upper()
    if key=='DATABASE_URL' or key.endswith('_DATABASE_URL') or key.startswith(('PG','AWS_','S3_','METODOBASE_TEST_','_METODOBASE_TEST')) or any(word in key for word in ['STRIPE','MERCADOPAGO','RESEND','SMTP','SENTRY','OPENAI_API']):env.pop(name,None)
env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',PYTHONPATH=str(OUT),QA_HISTORY30_MODULE_ORIGIN_OUT=str(evidence))
command=[str(PYTHON),'-X','utf8','-B','tests/run_isolated.py','-p','qa_browser30_origin','tests/test_member_browser_gate.py','-q','--tb=short','--junitxml='+str(phase/'junit.xml')]
with (phase/'stdout.log').open('xb') as stdout,(phase/'stderr.log').open('xb') as stderr:result=subprocess.run(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=180)
after=photo('unit50-after');assert before==after
cases=ET.parse(phase/'junit.xml').findall('.//testcase');assert len(cases)==50
passed=sum(not any(case.find(kind) is not None for kind in ['failure','error','skipped']) for case in cases)
outputs=[publish(path,'unit50-'+path.relative_to(phase).as_posix().replace('/','-')) for path in sorted(phase.rglob('*')) if path.is_file()]
save('unit50-result.json',{'head':HEAD,'exit':result.returncode,'passed':passed,'total':50,'all_source_modules_and_Base_aliases_fenced':True,'sources_helpers_packages_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'outputs':outputs,'scope':'Maintained metadata/publication-boundary/normalizer unit tests using isolated local SQLite only. No Chrome/HTTP/PG/provider execution.'})
print(json.dumps({'exit':result.returncode,'passed':passed,'total':50,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'stable':True}))
assert result.returncode==0 and passed==50
