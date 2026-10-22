from pathlib import Path
import ast
import hashlib
import json
import os
import subprocess
import sys
import zipfile

ROOT=Path('F:/mb-ci-image57-portable-20261022')
PRIVATE=Path('E:/MetodoBaseWorkspace/evidence/backend-ci57-pytest-bootstrap-20261022-v1')
BEFORE=Path('E:/MetodoBaseWorkspace/evidence/root-ci57-pytest-red-20261022-v1')
PUBLIC=ROOT/'docs/implementation/20261018-evolution/evidence/backend-ci57-pytest-bootstrap-20261022'
BASE='f766a09d1bad9ad74c1614a1d5232b18cf7d78e5'
sys.path.insert(0,str(ROOT))
from tests.ci_image57 import authority
scan=authority.publication()
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==BASE
assert (PUBLIC/'.gitattributes').read_bytes()==b'* -text\n'
def write(name,b):
    scan(b)
    with (PUBLIC/name).open('xb') as stream:stream.write(b)
def save(name,value):
    write(name,(json.dumps(value,indent=2,sort_keys=True)+'\n').encode())
original=git('show',BASE+':tests/test_ci_image57_offline.py')
assert original==git('show','d99c80bcdf5262f2ea63f1428fd0be5d1c00292d:tests/test_ci_image57_offline.py')
actual=(ROOT/'tests/test_ci_image57_offline.py').read_bytes()
tree=ast.parse(actual)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Offline57')
setup=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='setUpClass')
lines=actual.decode().splitlines(keepends=True)
start=min(n.lineno for n in setup.decorator_list)-1
end=setup.end_lineno
# One separator newline was added along with the class method.
assert lines[end]=='\n'
inverse=''.join(lines[:start]+lines[end+1:]).replace('import tempfile\n','',1).encode()
assert inverse==original
summary=json.loads((PRIVATE/'summary.json').read_bytes())
assert all(r['exit']==0 for r in summary['results'])
assert summary['source_quiet'] and summary['packages_quiet'] and summary['pip']==[0,0]
invariant=json.loads((PRIVATE/'invariant.json').read_bytes())
invariant['full_inverse_file_bytes_equal']=True
save('invariant.json',invariant)
save('summary.json',summary)
source={}
for name in ('tests/test_ci_image57_offline.py','tests/test_ci_image57_pytest_bootstrap.py'):
    blob=(ROOT/name).read_bytes()
    source[name]={'raw_sha256':sha(blob),'GitLF_sha256':sha(blob.replace(b'\r\n',b'\n')),'bytes':len(blob)}
    compile(blob,name,'exec')
save('source.json',{'base':BASE,'files':source,'python':sys.executable,'python_sha256':sha(Path(sys.executable).read_bytes()),
    'source_before_sha256':sha((PRIVATE/'source.before.json').read_bytes()),
    'source_after_sha256':sha((PRIVATE/'source.after.json').read_bytes()),
    'packages_before_sha256':sha((PRIVATE/'packages.before.json').read_bytes()),
    'packages_after_sha256':sha((PRIVATE/'packages.after.json').read_bytes()),
    'private_raw':str(PRIVATE),'scope':'Test-only bootstrap; not runtime CI/image/SQL/VM acceptance'})
before_result=json.loads((BEFORE/'result.json').read_bytes())
assert before_result['exit']==1 and before_result['expected_failure'] is True
save('before-reference.json',{'original_root':str(BEFORE),'original_source':before_result['source_HEAD'],
    'original_test_file_equal_to_author_base':True,'real_pytest_cases':1,'failure':'ARTIFACT NoneType in directory during test05',
    'files':{name:{'sha256':sha((BEFORE/name).read_bytes()),'bytes':(BEFORE/name).stat().st_size}
        for name in ('result.json','pytest.xml','pytest.private.log')}})
write('runner.py',(Path('E:/MetodoBaseWorkspace/evidence/backend-ci57-pytest-bootstrap-20261022-driver.py')).read_bytes())
write('seal.py',Path(__file__).read_bytes())
write('test_ci_image57_offline.before.py.RAW',original)
archives={}
members=[p for p in sorted(PRIVATE.iterdir()) if p.is_file()]
zip_path=PRIVATE/'originals.private.zip'
with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED) as archive:
    for path in members:archive.writestr(path.name,path.read_bytes())
with zipfile.ZipFile(zip_path) as archive:
    assert archive.testzip() is None
    assert len(archive.namelist())==len(members)
    assert all(archive.read(path.name)==path.read_bytes() for path in members)
save('private-archive.json',{'path':str(zip_path),'sha256':sha(zip_path.read_bytes()),'members':len(members),
    'full_readback':True,'private_boundary_preceded_payload':True,'public_RAW_zip':False})
for p in PUBLIC.iterdir():
    if p.is_file():scan(p.read_bytes())
save('scan.json',{'authority':'tests.ci_image57.authority.publication authenticated original',
    'status':'PASS','recursive_archive_checks':True,'private_error_payload_published':False})
files={p.name:{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(PUBLIC.iterdir()) if p.is_file()}
save('manifest.json',{'files':files,'raw_policy':'* -text existed before payload; index equality verified before commit'})
print(json.dumps({'source_sha256':sha((PUBLIC/'source.json').read_bytes()),
    'manifest_sha256':sha((PUBLIC/'manifest.json').read_bytes()),'files':len(files)+1,
    'private_archive_sha256':sha(zip_path.read_bytes())}))
