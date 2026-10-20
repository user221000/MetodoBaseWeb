from pathlib import Path, PurePosixPath
import ast
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile

T=Path('C:/Users/Consu/AppData/Local/Temp')
R=Path('F:/mb-google33-conflict-window-20261019')
C=T/'metodobase-google33-conflict-seal-20261019'
P=R/'docs/implementation/20261018-evolution/evidence/root-google33-conflict-author-20261019'
enc=lambda x:(json.dumps(x,indent=2)+'\n').encode()
sha=lambda x:hashlib.sha256(x).hexdigest()
def git(*args,check=True):return subprocess.run(['git',*args],cwd=R,capture_output=True,check=check)
assert git('rev-parse','HEAD').stdout.strip()==b'8a5e5dc235e96a47488befb743fc02a24b491939'
old_manifest=(P/'manifest.json').read_bytes();(C/'prepared-manifest-before-whitespace-attribute.json').write_bytes(old_manifest)
failure=git('diff','--cached','--check',check=False)
assert failure.returncode!=0
(C/'prepared-whitespace-failure.stdout').write_bytes(failure.stdout);(C/'prepared-whitespace-failure.stderr').write_bytes(failure.stderr)
names=re.findall(rb'^([^\n]+?):[0-9]+: trailing whitespace\.$',failure.stdout,re.MULTILINE)
assert names and set(names)=={b'docs/implementation/20261018-evolution/evidence/root-google33-conflict-author-20261019/archive-acl.ps1'}
attr=P/'.gitattributes';assert attr.read_bytes()==b'* -text\n'
attr.write_bytes(b'* -text\narchive-acl.ps1 whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n')
receipt={'initial_seal_stopped_before_commit':True,'reason':'RAW CRLF ACL helper required an explicit cr-at-eol whitespace attribute','RAW_ACL_helper_changed':False,'all_other_whitespace_checks_preserved':True,'product_and_tests_unchanged':True}
(P/'seal-finish-driver.py').write_bytes(Path(__file__).read_bytes())
(P/'seal-finish.json').write_bytes(enc(receipt))
definition=next(n for n in ast.parse((T/'metodobase-checkpoint119-prepare.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='scan')
exec(compile(ast.Module(body=[definition],type_ignores=[]),'scanner119','exec'))
for p in P.iterdir():
    if p.is_file():scan(p.read_bytes(),p.name)
manifest={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in P.iterdir() if p.is_file() and p.name!='manifest.json'}
(P/'manifest.json').write_bytes(enc(manifest))
prefix=P.relative_to(R).as_posix()
git('-c','core.autocrlf=false','add','-f','--',prefix)
git('diff','--cached','--check')
for p in P.iterdir():assert git('show',':'+p.relative_to(R).as_posix()).stdout==p.read_bytes()
git('commit','-m','Retain Google conflict regression baseline and fixed-source author evidence')
result={'head':git('rev-parse','HEAD').stdout.decode().strip(),'product_head':'8a5e5dc235e96a47488befb743fc02a24b491939','files':len(manifest)+1,'source_sha256':sha((P/'source.json').read_bytes()),'manifest_sha256':sha((P/'manifest.json').read_bytes()),'independent_peer_pending':True,'tracked_quiet':not git('status','--porcelain','-uno').stdout.strip()}
(C/'result.json').write_bytes(enc(result));print(json.dumps(result))
