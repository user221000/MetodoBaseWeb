"""Exclusive public projection; private logs remain under their existing DACL."""
from pathlib import Path
import ast
from collections import Counter
import hashlib
import importlib.metadata
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path('F:/mb-product-analytics-r30-20261021')
PRIVATE = Path(os.environ['TEMP'])/'metodobase-r30-author-20261021'
OUT = ROOT/'docs/implementation/20261018-evolution/evidence/backend-r30-product-analytics-20261021'
BASE = '5efd3962ec9529e901273533d17ff1b19f0f1f39'
sha = lambda blob: hashlib.sha256(blob).hexdigest()
def git(*args):
    return subprocess.check_output(['git','--no-replace-objects',*args],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip() == BASE
assert (OUT/'.gitattributes').read_bytes() == b'* -text\n'
scanner_source = (Path(os.environ['TEMP'])/'metodobase-checkpoint119-prepare.py').read_bytes()
tree = ast.parse(scanner_source)
scanner_node = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == 'scan')
space = {}
exec('from pathlib import PurePosixPath\nimport re,io,tarfile,zipfile',space)
exec(compile(ast.Module(body=[scanner_node],type_ignores=[]),'scanner119','exec'),space)
def scan(blob,name):
    space['scan'](blob,name)
    assert not re.search(rb'[A-Za-z0-9_-]{30,}\.[0-9]{9,12}\.[a-f0-9]{64}',blob),name
    assert not re.search(rb'(?:postgres(?:ql)?|redis)://[^\s]+:[^\s]+@',blob),name
def raw(name,blob):
    scan(blob,name)
    path=OUT/name
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(blob)
def save(name,value):
    raw(name,(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())

os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
from web import product_analytics_domain as d
from web.product_analytics_baseline import build_baseline
from datetime import UTC,datetime
example=d.build_report('personal',{'profile_present':False,'plan_present':False},
    [datetime(2026,10,1,12,tzinfo=UTC),datetime(2026,10,8,12,tzinfo=UTC),datetime(2026,10,16,12,tzinfo=UTC)],[],[],
    now=datetime(2026,10,21,18,tzinfo=UTC),start='2026-09-28',through='2026-10-21',schema_revision='20261020_account_security')
save('example.synthetic.json',example)
save('baseline.synthetic.json',build_baseline(example))
save('dictionary.json',d.dictionary())
proposal=Path(os.environ['TEMP'])/'metodobase-r30-contract-20261021-_2jwa692/contract-v1-proposed.json'
assert sha(proposal.read_bytes()) == 'bc394f7c5ac01c57a669c867e36e4207995ae53991c710bb3e83de625a4220c8'
raw('contract.proposed.raw.json',proposal.read_bytes())
save('technical-approval.json',{'authority':'ROOT technical approval recorded in agent messages',
    'proposal_sha256':sha(proposal.read_bytes()),'implementation_base':BASE,
    'scope':'R30v1 private retained facts only; no full R30 completion',
    'amendments':['Build source is null/unavailable absent existing config, no hardcoded d568/no Git per request',
        'Invalid selectors: zero R30 reader/session/statistics calls, general auth middleware may read earlier',
        'Exact API/slash private middleware and real factory mounts owned only inside this isolated WT'],
    'human_external_approval_claimed':False})

phases=('phase2','phase3','http-error-before','final','rate-fixture-after')
case_sets={}
for phase in phases:
    parent=PRIVATE/phase
    summary=json.loads((parent/'summary.json').read_bytes())
    before=json.loads((parent/'sources.before.json').read_bytes())
    after=json.loads((parent/'sources.after.json').read_bytes())
    depsbefore=json.loads((parent/'packages.before.json').read_bytes())
    depsafter=json.loads((parent/'packages.after.json').read_bytes())
    assert before == after and depsbefore == depsafter and summary['pip'] == [0,0]
    xml=ET.parse(parent/'pytest.xml')
    cases=[{'id':c.attrib['classname']+'::'+c.attrib['name'],
            'status':'failure' if c.find('failure') is not None else 'error' if c.find('error') is not None else
                     'skip' if c.find('skipped') is not None else 'pass'} for c in xml.findall('.//testcase')]
    case_sets[phase]=cases
    save('runs/'+phase+'.json',{**summary,'cases':cases,
        'source_before_sha256':sha((parent/'sources.before.json').read_bytes()),
        'source_after_sha256':sha((parent/'sources.after.json').read_bytes()),
        'package_before_sha256':sha((parent/'packages.before.json').read_bytes()),
        'package_after_sha256':sha((parent/'packages.after.json').read_bytes()),
        'private_xml_sha256':sha((parent/'pytest.xml').read_bytes()),
        'private_log_sha256':sha((parent/'pytest.private.log').read_bytes())})

final={c['id']:c['status'] for c in case_sets['final']}
for c in case_sets['rate-fixture-after']:
    assert final[c['id']] == 'failure' and c['status'] == 'pass'
    final[c['id']]='pass'
assert len(final) == 113 and set(final.values()) == {'pass'}
latest=json.loads((PRIVATE/'rate-fixture-after/sources.after.json').read_bytes())
tested=json.loads((PRIVATE/'final/sources.after.json').read_bytes())
assert [p for p in latest if latest[p] != tested[p]] == ['tests/test_product_analytics_http.py']
save('final-cases.json',{'unique_ids':len(final),'pass':len(final),'fail':0,'errors':0,'skip':0,
    'composition':'111 pass final + exact2 fixture-only rate canaries repeated2/2; not a single113 final run',
    'cases':sorted(final),'between_runs_changed_only':['tests/test_product_analytics_http.py']})

inverses={}
for name in ('api/app.py','web/main_web.py','web/middleware/security_headers.py'):
    old=git('show',BASE+':'+name)
    actual=(ROOT/name).read_bytes()
    normalized=actual.replace(b'\r\n',b'\n')
    if name.endswith('security_headers.py'):
        back=normalized
        for fragment in (b'_PRODUCT_ANALYTICS_PATHS = frozenset({"/api/analytics/producto", "/api/analytics/producto/"})\n',
            b'        product_analytics_api = request.url.path in _PRODUCT_ANALYTICS_PATHS\n',
            b'                    and not product_analytics_api\n',b'                or product_analytics_api\n'):
            assert back.count(fragment)==1
            back=back.replace(fragment,b'')
        assert back.count(b'elif product_analytics_api or ')==1 and back.count(b'if product_analytics_api or ')==1
        back=back.replace(b'elif product_analytics_api or ',b'elif ').replace(b'if product_analytics_api or ',b'if ')
    else:
        fragment=b'    from web.routes import product_analytics\n    app.include_router(product_analytics.router, prefix="/api")\n'
        assert normalized.count(fragment)==1
        back=normalized.replace(fragment,b'')
    assert back==old,name
    raw('preimages/'+name,old)
    inverses[name]={'base_Git_sha256':sha(old),'current_RAW_sha256':sha(actual),'current_GitLF_sha256':sha(normalized),
                    'inverse_full_Git_bytes_equal':True,'base_RAW_claimed':False}
save('minimal-inverses.json',inverses)

old_test=(PRIVATE/'http-error-before/canary.before.py').read_bytes()
old_route=(PRIVATE/'http-error-before/route.before.py').read_bytes()
raw('preimages/http-error-canary.before.py',old_test)
raw('preimages/analytics-route.before.py',old_route)
def asserts(blob,name):
    parsed=ast.parse(blob)
    node=next(n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name==name)
    return Counter(ast.dump(n,include_attributes=False) for n in ast.walk(node) if isinstance(n,ast.Assert))
name='test_internal_and_outer_failures_use_opaque_factory_boundary'
assert asserts(old_test,name)==asserts((ROOT/'tests/test_product_analytics_http.py').read_bytes(),name)
save('failure-attribution.json',{'http_fault_injection':{'before':'2 failures +2 controls','after':'same4 pass in final',
    'same_assertion_AST':True,'assertion_count':sum(asserts(old_test,name).values()),
    'preimage_route_sha256':sha(old_route),'preimage_canary_sha256':sha(old_test),
    'scope':'Synthetic internal HTTPException500 detail forwarding; no SQL exploitation or observed real-user disclosure'},
    'own_harness_errors':[
      {'phase':'phase2','count':1,'cause':'SaaS unsafe POST without bearer reached existing CSRF403 on second loop; expected405 was incomplete'},
      {'phase':'phase3','count':1,'cause':'Bearer present first POST was exempt from CSRF and405; expected403 was incomplete'},
      {'phase':'final','count':2,'cause':'Isolated launcher disabled rate middleware; intentional429 required instance enabled=True'}],
    'historical_assertions_modified':0,'historical_helpers_targets_modified':0,
    'initial48':'48 pass, source/pip before-after not captured for that first run; no quiet claim retroactively added'})

newfiles=['web/product_analytics_domain.py','web/product_analytics_baseline.py','web/services/product_analytics.py',
    'web/routes/product_analytics.py','tests/product_analytics_fixtures.py','tests/test_product_analytics_domain.py',
    'tests/test_product_analytics_service.py','tests/test_product_analytics_http.py','tests/test_product_analytics_headers.py']
changed=['api/app.py','web/main_web.py','web/middleware/security_headers.py',*newfiles]
source={}
for name in changed:
    blob=(ROOT/name).read_bytes()
    scan(blob,name)
    source[name]={'raw_sha256':sha(blob),'GitLF_sha256':sha(blob.replace(b'\r\n',b'\n')),'bytes':len(blob)}
save('source.json',{'base':BASE,'files':source,'definition_version':d.VERSION,'definition_sha256':d.DEFINITION_HASH,
    'implementation_source_revision_not_attested':True,'dependencies':json.loads((PRIVATE/'rate-fixture-after/packages.after.json').read_bytes()),
    'python':{'executable':sys.executable,'version':sys.version,'sha256':sha(Path(sys.executable).read_bytes()),
              'base_executable_sha256':sha(Path(sys._base_executable).read_bytes())},
    'scope':'Author candidate only. SQLite37 and actual API/SaaS HTTP; no PG/Chrome/Redis/VM/n2/installations/live users/mail',
    'raw_proofs_preserved_private':str(PRIVATE),'private_dacl':'current user +SYSTEM only, inheritance disabled; checked by PowerShell',
    'limits':['Independent SEC/QA pending','PG REPEATABLE READ/READ ONLY and pool reset not runtime verified in this task',
              'Not full R30: no real-client baseline, interviews, global cohort population or experiment decision']})
raw('seal-driver.py',Path(__file__).read_bytes())
for phase in ('phase2','phase3','http-error-before','final','rate-fixture-after'):
    driver=Path(os.environ['TEMP'])/('metodobase-r30-'+{'phase2':'phase2','phase3':'phase3',
          'http-error-before':'http-error-before','final':'final','rate-fixture-after':'rate-fixture-after'}[phase]+'-run.py')
    raw('drivers/'+phase+'.py',driver.read_bytes())
save('scan.json',{'scanner119_source_sha256':sha(scanner_source),'scanner_AST_sha256':sha(ast.dump(scanner_node).encode()),
    'extra_checks':['3part CSRF token shape','credential-bearing PostgreSQL/Redis URL'],
    'result':'PASS','private_bodies_copied':False})
files={p.relative_to(OUT).as_posix():{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}
       for p in sorted(OUT.rglob('*')) if p.is_file()}
for name in files:scan((OUT/name).read_bytes(),name)
save('manifest.json',{'files':files,'raw_policy':'* -text created before proof bytes; exact Git equality checked after staging',
                     'public_projection_only':True})
print(json.dumps({'prefix':str(OUT),'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),
    'source_sha256':sha((OUT/'source.json').read_bytes()),'files':len(files)+1,'distinct_pass_ids':113}))
