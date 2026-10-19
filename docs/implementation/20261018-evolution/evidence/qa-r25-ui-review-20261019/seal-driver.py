from pathlib import Path,PurePosixPath
import ast,hashlib,io,json,re,subprocess,tarfile,zipfile
ROOT=Path(r'F:\mb-r25-qa-ui-20261019');TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');EV=ROOT/'docs/implementation/20261018-evolution/evidence'
OUT=EV/'qa-r25-ui-review-20261019';SHA=lambda raw:hashlib.sha256(raw).hexdigest()
tree=ast.parse((TEMP/'metodobase-checkpoint119-prepare.py').read_text(encoding='utf8'))
fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='scan');exec(compile(ast.Module(body=[fn],type_ignores=[]),'<reviewed-token-scanner>','exec'))
def write(path,raw):
    scan(raw,path.name)
    with path.open('xb') as stream:stream.write(raw)
def dump(path,data):write(path,(json.dumps(data,indent=2)+'\n').encode())
OUT.mkdir(exist_ok=False);write(OUT/'.gitattributes',b'* -text\n')
frozen=(EV/'qa-r25-ui-http-replay-independent-20261019/independent-test.py').read_bytes();current=(ROOT/'tests/test_qa_progress32_independent.py').read_bytes()
def functions(raw):return [ast.dump(node,include_attributes=False) for node in ast.parse(raw).body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))]
assert functions(frozen)==functions(current)
layout=(TEMP/'metodobase-r25-qa-layout.cjs').read_bytes();write(ROOT/'tests/e2e/progress32_layout_qa.cjs',layout)
dump(OUT/'maintained-test-preservation.json',{'http_frozen_SHA256':SHA(frozen),'http_maintained_SHA256':SHA(current),'all7_function_ASTs_equal':True,'function_count':len(functions(current)),
    'only_change':'Imports sorted and fixture objects explicitly re-exported for pytest registration, with narrowly documented Ruff PLC0414 exceptions. No assertion or function body changed. The2 product-red export canaries remain intact.',
    'layout_driver_before_RAW_equals_maintained':True,'layout_driver_SHA256':SHA(layout),'layout_parser_SHA256':SHA((ROOT/'tests/check_progress32_layout_qa.py').read_bytes())})
ruff=subprocess.run([str(TEMP/'metodobase-qa-20261018/Scripts/ruff.exe'),'check','tests/check_progress32_layout_qa.py','tests/test_qa_progress32_independent.py'],cwd=ROOT,capture_output=True)
assert ruff.returncode==0;write(OUT/'owned-python-ruff.log',ruff.stdout+ruff.stderr)
write(OUT/'initial-browser-preflight-syntax-source.cjs',(TEMP/'metodobase-r25-qa-browser-initial-syntax-error.cjs').read_bytes())
for name in ('metodobase-r25-qa-browser-v2-prepare.py','metodobase-r25-qa-browser-v3-prepare.py','metodobase-r25-qa-browser-v2-harness-correction.json','metodobase-r25-qa-browser-v3-harness-correction.json','metodobase-r25-qa-ui-first.py','metodobase-r25-qa-ui-http-replay.py','metodobase-r25-qa-ui-prebrowser-seal.py','metodobase-r25-qa-browser-seal.py','metodobase-r25-qa-layout-prepare.py'):
    write(OUT/name,(TEMP/name).read_bytes())
links=[]
for name in ('qa-r25-ui-independent-20261019','qa-r25-ui-http-replay-independent-20261019','qa-r25-ui-browser-independent-20261019','qa-r25-ui-browser-v2-independent-20261019','qa-r25-ui-browser-v3-independent-20261019','qa-r25-ui-layout-before-independent-20261019'):
    raw=(EV/name/'manifest.json').read_bytes();manifest=json.loads(raw)
    assert set(manifest)=={'source_head','files'}
    for entry in manifest['files']:
        blob=(EV/name/entry['path']).read_bytes();assert len(blob)==entry['bytes'] and SHA(blob)==entry['SHA256']
    links.append({'prefix':name,'manifest_SHA256':SHA(raw),'files':len(manifest['files'])})
report=json.loads((EV/'qa-r25-ui-browser-v3-independent-20261019/browser-report.json').read_bytes())
assert report['complete'] and len(report['checks'])==14 and len(report['screens'])==12 and report['pageErrors']==[]
measure_puts=[row for row in report['requests'] if row['method']=='PUT' and row['path'].startswith('/api/usuario/progreso/mediciones/')]
assert len(measure_puts)==2 and measure_puts[0]['path']==measure_puts[1]['path']
dump(OUT/'review.json',{'source_head':'b7f8e129251dfd5216f811ba77d0b6183ca76735','status':'Scoped technical gates passed; two independent product findings remain open pending repairs and exact replay.',
    'VM':'152/152 maintained synthetic DOM/fetch cases across9 drivers. Replays overlap author scopes; not152 new independent business criteria.',
    'HTTP':'2 SSR+22 historical author HTTP passed on actual factories/migrated SQLite32.12 new independent HTTP:10 pass and2 export validation-header reds after correcting three own mistaken expectations. Initial36-case run30pass6red preserved; first cache-header equality masked the later real Referrer-Policy failure.',
    'browser':'14 actual groups and12 screenshots, zero scoped axe AA violations/reflow overflow. Real password login/link acceptance/measurement/CAS/consent/diary/projection/withdrawal/OWNER minimal withdrawal/account replacement/logout. Named dropped real measurement commit response then exact real HTTP readback; precisely2 measurement PUTs at the same key = initial write+explicit edit, no transport replay.',
    'UX':'Visual inspection found mobile tables collapse data into4-6 text fragments. Independent4-case layout report is0/4; labelled focusable region does not actually scroll. Existing axe/body-overflow green does not accept mobile table legibility.',
    'cleanup':'All four own browser/server runs closed cooperatively; exact observed9 Node/Chrome generations absent per run, no listener remains. VM never used by this QA agent; foreign processes/Chrome/8776 untouched. SQLite originals/private logs and command-line inventories remain private.',
    'preservation':'Full10297 tracked RAW files/89 installed name-version metadata/Python/Node/Chrome equal in first phase. Runtime337/89/binarios/drivers/3 Node metadata equal across each browser; pip0 before/after v2/v3/layout. This does not hash every installed Python byte.',
    'limits':'No PostgreSQL/RLS, provider, clinical, production, SLO or global R25 acceptance. Own harness failures and initial syntax source retained; no original preflight CLI log file was captured, and none is reconstructed.',
    'evidence':links})
write(OUT/'seal-driver.py',Path(__file__).read_bytes())
files=[]
for item in sorted(OUT.iterdir()):
    if item.is_file():files.append({'path':item.name,'bytes':item.stat().st_size,'SHA256':SHA(item.read_bytes())})
dump(OUT/'manifest.json',{'source_head':'b7f8e129251dfd5216f811ba77d0b6183ca76735','files':files})
print(json.dumps({'prefix':str(OUT),'files':len(files),'manifest_SHA256':SHA((OUT/'manifest.json').read_bytes()),'owned_test_function_count':len(functions(current))}))
