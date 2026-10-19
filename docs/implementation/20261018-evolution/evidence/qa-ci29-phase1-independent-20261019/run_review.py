"""Execute a frozen CI guard or one isolated primary mutation; never PG/browser."""
import time
from support import *
mode=sys.argv[1]
assert mode in {'baseline','checker-empty','runner-fake'}
phase=TEMP/mode;phase.mkdir(exist_ok=False)
source=ROOT if mode=='baseline' else TEMP/(mode+'-source')
before=photo(mode+'-before')
environment=os.environ.copy()
for name in list(environment):
    key=name.upper()
    if key=='DATABASE_URL' or key.endswith('_DATABASE_URL') or key.startswith(('PG','AWS_','S3_')) or any(word in key for word in ['STRIPE','MERCADOPAGO','RESEND','SMTP','SENTRY','OPENAI_API']):environment.pop(name,None)
environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',PYTHONPATH='')
started=time.monotonic()
with (phase/'driver.stdout.log').open('xb') as stdout,(phase/'driver.stderr.log').open('xb') as stderr:
    result=subprocess.run([str(PYTHON),'-X','utf8','-B',str(source/'tests/verify_member_links_ci.py'),
        '--output',str(phase/'review'),'--history-repository',str(ROOT)],cwd=source,env=environment,
        stdout=stdout,stderr=stderr,timeout=220)
after=photo(mode+'-after')
data=json.loads((phase/'review/review.json').read_bytes()) if (phase/'review/review.json').exists() else None
outputs=[]
names=['driver.stdout.log','driver.stderr.log','review/review.json','review/canaries-raw.zip','review/historical.log',
       'review/historical-ci28/receipt.json','review/historical-ci28/stdout.log','review/historical-ci28/stderr.log']
for name in names:
    if (phase/name).is_file():outputs.append(publish(phase/name,mode+'-'+name.replace('/','-')))
summary={'mode':mode,'head':HEAD,'CI_source_root':str(source),'exit':result.returncode,'runner_seconds':time.monotonic()-started,
         'current_guard_accepted':result.returncode==0,'historical_exit':data['historical_exit'] if data else None,
         'report_count':len(data['reports']) if data else None,'delta_canaries':len(data['unauthorized_delta_canaries']) if data else None,
         'report_canaries':len(data.get('current_report_canaries',[])) if data else None,
         'inert_cases':len(data.get('current_inert_fixture_cases',[])) if data else None,
         'source_helpers_packages_stable':before==after,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,
         'public_outputs':outputs,'scope':'Local guard only; no PG/browser/QEMU/Actions/provider execution.'}
save(mode+'-result.json',summary)
print(json.dumps({key:summary[key] for key in ['mode','exit','current_guard_accepted','report_count','delta_canaries','report_canaries','inert_cases','source_helpers_packages_stable','sources','packages']}))
assert before==after
if mode=='baseline':assert result.returncode==0 and summary['report_canaries']==55 and summary['inert_cases']==27
