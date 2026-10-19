"""Preserve the existing closed proof's declared RAW bytes across every checkout."""
from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path(r'F:\mb-r12-history30-20261019');author=Path(r'F:\mb-history30-restore-20261019')
prefix='docs/implementation/20261018-evolution/evidence/history30-restore-author-20261019'
sha=lambda value:hashlib.sha256(value).hexdigest()
freeze=(author/prefix/'freeze.json').read_bytes();assert sha(freeze)=='83fb548ffbd92ba99e02fba675c5b097150d413a85af62de34749c31a3ea7da3'
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
before_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();rows=[]
for entry in json.loads(freeze)['files']:
    name=entry['path']
    if not name.startswith(prefix+'/'):continue
    raw=(author/name).read_bytes();assert sha(raw)==entry['sha256_raw'],name
    prior=subprocess.check_output(['git','show','HEAD:'+name],cwd=root)
    assert prior.replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n'),name
    (root/name).write_bytes(raw)
    rows.append({'path':name,'previous_Git_blob_sha256':sha(prior),'preserved_RAW_sha256':sha(raw),'only_newline_representation_changed':prior!=raw})
(root/prefix/'freeze.json').write_bytes(freeze)
(root/prefix/'.gitattributes').write_bytes(b'* -text\n')
ev=root/'docs/implementation/20261018-evolution/evidence/history30-restore-raw-preservation-20261019';ev.mkdir(exist_ok=False);(ev/'.gitattributes').write_bytes(b'* -text\n')
shutil.copyfile(__file__,ev/'preserve.py')
receipt={'parent':before_head,'original_freeze_RAW_sha256':sha(freeze),'scope':'Representation repair only: frozen source RAW bytes authenticated against original manifest; no source/test/assertion/runtime changes or retests. Prior Git LF derivatives remain in parent objects.','files':rows}
(ev/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
raw=sorted(path.relative_to(root).as_posix() for directory in [root/prefix,ev] for path in directory.rglob('*') if path.is_file())
for index in range(0,len(raw),25):
    subprocess.run(['git','-c','core.autocrlf=false','add','-f','--',*raw[index:index+25]],cwd=root,check=True,capture_output=True)
    subprocess.run(['git','-c','core.autocrlf=false','add','--renormalize','--',*raw[index:index+25]],cwd=root,check=True,capture_output=True)
for name in raw:assert subprocess.check_output(['git','show',':'+name],cwd=root)==(root/name).read_bytes(),name
assert set(subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=root).decode().split('\0')[:-1]).issubset(set(raw))
subprocess.run(['git','commit','-m','Preserve declared RAW restore30 evidence across checkout platforms'],cwd=root,check=True,stdout=subprocess.DEVNULL)
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root)
print(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'RAW_files_authenticated':len(raw),'previous_LF_derivatives_preserved_in_parent':True,'representation_changes':sum(row['only_newline_representation_changed'] for row in rows)}))
