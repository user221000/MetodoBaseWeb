from pathlib import Path
import ast
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(r'F:\mb-security-export-headers-peer-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-export-private-headers-independent-20261019'
PRIVATE=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-sec-export-headers-peer-private-20261019')
HEAD='2002959122f142162192a122fad7ba2cafbb12b1'
BASE='b7f8e129251dfd5216f811ba77d0b6183ca76735'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert not git('status','--porcelain','--untracked-files=no')
assert not OUT.exists() and not PRIVATE.exists()
author=ROOT/'docs/implementation/20261018-evolution/evidence/backend-r25-export-private-headers-20261019'
assert sha((author/'source.json').read_bytes())=='8bb645d7b00373eb031b25f516ac0a7824c14e82752cb131adcb55a3be9b18bb'
source=json.loads((author/'source.json').read_bytes())
for item in source['proof_files']:
    b=(author/item['path']).read_bytes()
    assert len(b)==item['bytes'] and sha(b)==item['RAW_sha256'],item['path']
for item in source['sources']:assert sha(git('show',HEAD+':'+item['path']))==item['GitLF_sha256']
extra=['tests/security_export_headers_qa_original.py','tests/test_security_export_headers_peer.py']
for name in extra:ast.parse((ROOT/name).read_bytes())
assert sha((ROOT/extra[0]).read_bytes())=='44941ef6403aa7ef628d50bb551019c9cce3412d97c00d9d4cf3f5f28866df2b'
current=git('show',HEAD+':web/middleware/security_headers.py')
block=b'''# Validation/authentication/method/redirect failures precede exporter headers.
# Exactly the mounted exporter and its slash redirect, never nearby prefixes.
_PRIVATE_EXPORT_PATHS = frozenset({
    "/api/usuario/privacidad/exportar", "/api/usuario/privacidad/exportar/",
})
'''
assert current.count(block)==1
inverse=current.replace(block,b'')
for old,new in [(b'        export_api = request.url.path in _PRIVATE_EXPORT_PATHS\n',b''),
    (b'                    and not export_api\n',b''),(b'                or export_api\n',b''),
    (b'progress_api or export_api or',b'progress_api or')]:
    assert inverse.count(old)==1
    inverse=inverse.replace(old,new)
prior=git('show',BASE+':web/middleware/security_headers.py')
assert inverse==prior and ast.dump(ast.parse(inverse))==ast.dump(ast.parse(prior))
changed=git('diff','--name-only',BASE,HEAD).decode().splitlines()
assert len(changed)==15
assert [n for n in changed if not n.startswith('docs/')]==['tests/test_progress32_export_privacy_headers.py','web/middleware/security_headers.py']

OUT.mkdir(parents=True);PRIVATE.mkdir()
(OUT/'.gitattributes').write_bytes(b'* -text\n')
(OUT/'driver.py').write_bytes(Path(__file__).read_bytes())
for name in extra:(OUT/Path(name).name).write_bytes((ROOT/name).read_bytes())
names=sorted(set(git('ls-files','-z').decode().split('\0')[:-1]+extra))
def photo():
    return {'files':{n:sha((ROOT/n).read_bytes()) for n in names},
        'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
        'python_sha256':sha(Path(sys.executable).read_bytes())}
def dump(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
dump('inverse-proof.json',{'source_head':HEAD,'parent':BASE,'exact_gitlf_full_file_inverse':True,
    'entire_ast_equal_after_inverse':True,'parent_sha256':sha(prior),'current_sha256':sha(current),
    'author_primary_files_authenticated':len(source['proof_files'])+1,'changed_paths':changed})
before=photo();dump('before.json',before)
pip0=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-before.raw.log').write_bytes(pip0.stdout+pip0.stderr);assert pip0.returncode==0
cmd=[sys.executable,'-X','utf8','-B','tests/run_isolated.py',
    'tests/security_export_headers_qa_original.py::test_eighth_export_cursor_is_lowercase_only_and_does_not_authorize_other_actor',
    'tests/test_security_export_headers_peer.py','-q','--tb=short','--junitxml='+str(PRIVATE/'results.xml')]
run=subprocess.run(cmd,cwd=ROOT,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=360)
(PRIVATE/'stdout.raw.log').write_bytes(run.stdout);(PRIVATE/'stderr.raw.log').write_bytes(run.stderr)
cases=ET.parse(PRIVATE/'results.xml').findall('.//testcase')
structural=[{'case':c.get('classname')+'::'+c.get('name'),
    'outcome':next((kind for kind in ['failure','error','skipped'] if c.find(kind)is not None),'passed')} for c in cases]
dump('cases.STRUCTURAL.json',structural)
after=photo();dump('after.json',after)
pip1=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-after.raw.log').write_bytes(pip1.stdout+pip1.stderr)
summary={'source_head':HEAD,'case_count':len(cases),'same_QA_cases':2,'own_cases':len(cases)-2,
    'outcomes':{k:sum(c['outcome']==k for c in structural) for k in ['passed','failure','error','skipped']},
    'exit':run.returncode,'source_count':len(names),'packages':len(before['packages']),
    'sources_packages_python_exact':before==after,'pip_before':pip0.returncode,'pip_after':pip1.returncode,
    'scope':'Independent focal middleware policy and actual migrated32 SQLite factories/HTTP. Exact QA source; no auth override. No PG, Chrome, VM, provider, data disclosure or global R25 acceptance claim.'}
dump('summary.json',summary)
dump('private-originals.json',{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(PRIVATE.iterdir()) if p.is_file()})
print(json.dumps(summary))
assert before==after and pip1.returncode==0
assert run.returncode==0 and len(cases)==20
