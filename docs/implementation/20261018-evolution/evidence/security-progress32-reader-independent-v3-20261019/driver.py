from pathlib import Path
import ast
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(r'F:\mb-security-progress32-peer-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-progress32-reader-independent-v3-20261019'
PRIVATE=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-sec32-peer-private-v3-20261019')
PROFILE=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-qa-pg55483-private-ok6hrpyq\env.json')
HEAD='bd0501cdfbad1e48d483718b66e31bb65559f05e'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert not git('status','--porcelain','--untracked-files=no')
assert not OUT.exists() and not PRIVATE.exists()
extra=['tests/security_progress32_owned.py','tests/test_security_progress32_peer.py','tests/test_security_progress32_parent_boundary.py']
for p in extra:ast.parse((ROOT/p).read_text(encoding='utf8'))
freeze=ROOT/'docs/implementation/20261018-evolution/evidence/backend-r25-progress32-20261019/source-freeze.json'
frozen=json.loads(freeze.read_bytes())
for item in frozen['sources']:
    assert sha(git('show',HEAD+':'+item['path']))==item['LF_sha256'],item['path']
profile=json.loads(PROFILE.read_bytes())
assert set(profile)=={'METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN'}
pgexe=Path(profile['METODOBASE_TEST_PG_BIN'])/'postgres.exe'
OUT.mkdir(parents=True);PRIVATE.mkdir()
(OUT/'.gitattributes').write_bytes(b'* -text\n')
(OUT/'driver.py').write_bytes(Path(__file__).read_bytes())
for p in extra:(OUT/Path(p).name).write_bytes((ROOT/p).read_bytes())
names=sorted(git('ls-files','-z').decode().split('\0')[:-1]+extra)
def photo():
    return {'files':{n:sha((ROOT/n).read_bytes()) for n in names},
        'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
        'python_sha256':sha(Path(sys.executable).read_bytes()),'postgres_sha256':sha(pgexe.read_bytes()),
        'private_profile_sha256':sha(PROFILE.read_bytes())}
def dump(n,v):(OUT/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
before=photo();dump('before.json',before)
pip0=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-before.raw.log').write_bytes(pip0.stdout+pip0.stderr);assert pip0.returncode==0
launcher=PRIVATE/'pytest-launcher.py'
launcher.write_bytes(('''from pathlib import Path
import json,os,sys
ROOT=Path(r"F:\\mb-security-progress32-peer-20261019")
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
profile=json.loads(Path(r"C:\\Users\\Consu\\AppData\\Local\\Temp\\metodobase-qa-pg55483-private-ok6hrpyq\\env.json").read_bytes())
os.environ.update(profile)
os.environ['SEC32_PRIVATE_LEASES']=r"C:\\Users\\Consu\\AppData\\Local\\Temp\\metodobase-sec32-peer-private-v3-20261019\\leases"
os.environ['SEC32_BOUNDARY_RECEIPT']=r"C:\\Users\\Consu\\AppData\\Local\\Temp\\metodobase-sec32-peer-private-v3-20261019\\parent-boundary.json"
from tests import progress32_fixtures
from tests.security_progress32_owned import owned_database
progress32_fixtures.owned_database=owned_database
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
''').encode())
ast.parse(launcher.read_text())
(OUT/'pytest-launcher.py').write_bytes(launcher.read_bytes())
cmd=[sys.executable,'-X','utf8','-B',str(launcher),
    'tests/test_security_progress32_peer.py::test_authority_locks_block_updates_then_changed_source_and_reader_roles_deny_old_scope',
    'tests/test_security_progress32_parent_boundary.py','-q','--tb=short','--junitxml='+str(PRIVATE/'results.xml'),
    '-o','cache_dir='+str(PRIVATE/'cache')]
run=subprocess.run(cmd,cwd=ROOT,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),
    capture_output=True,timeout=600)
(PRIVATE/'stdout.raw.log').write_bytes(run.stdout);(PRIVATE/'stderr.raw.log').write_bytes(run.stderr)
cases=ET.parse(PRIVATE/'results.xml').findall('.//testcase')
projection=[{'case':c.get('classname')+'::'+c.get('name'),
    'outcome':next((k for k in ['failure','error','skipped'] if c.find(k)is not None),'passed')} for c in cases]
dump('cases.STRUCTURAL.json',projection)
after=photo();dump('after.json',after)
pip1=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-after.raw.log').write_bytes(pip1.stdout+pip1.stderr)
leases=[json.loads(p.read_bytes()) for p in sorted((PRIVATE/'leases').glob('lease-*.json'))]
dump('resource-closure.json',leases)
summary={'source_head':HEAD,'author_source_paths_git_lf_authenticated':len(frozen['sources']),
    'cases':len(cases),'own_cases':sum(c['case'].startswith(('tests.test_security_progress32_peer::','tests.test_security_progress32_parent_boundary::')) for c in projection),
    'exit':run.returncode,'outcomes':{k:sum(c['outcome']==k for c in projection) for k in ['passed','failure','error','skipped']},
    'source_count':len(names),'packages':len(before['packages']),'sources_packages_python_pg_profile_exact':before==after,
    'pip_before':pip0.returncode,'pip_after':pip1.returncode,'lease_count':len(leases),
    'all_own_leases_closed_absent':bool(leases) and all(l['state']=='closed_absent' and l['sessions_before_drop']==0 for l in leases),
    'ownership_harness':'Independent exclusive_xb before CREATE and CAS receipt updates replace only author owned_database fixture; no product/assertion changes',
    'scope':'Targeted replay of2 corrected typed-role fixtures plus1 diagnostic authentication-boundary case; PostgreSQL restricted role/pool1/real HTTP. No new retirement authentication policy or production/provider claim.'}
dump('summary.json',summary)
dump('private-originals.json',{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(PRIVATE.iterdir()) if p.is_file()})
print(json.dumps(summary))
assert before==after and pip1.returncode==0
assert summary['all_own_leases_closed_absent']
assert run.returncode==0 and len(cases)==3
