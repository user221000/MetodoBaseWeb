"""Preserve original CRLF evidence while checking real whitespace unchanged."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R=Path('F:/MetodoBaseWeb-execution-20261018')
D=R/'docs/implementation/20261018-evolution'
C=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint134-20261020')
P=D/'evidence/checkpoint134-closure-20261020'
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def git(*a,check=True):return subprocess.run(['git',*a],cwd=R,capture_output=True,check=check)
assert git('rev-parse','HEAD').stdout.decode().strip()=='e006516fe99ec0da65c4a0f563b8c5736e541b50'
proc=git('diff','--cached','--check',check=False)
(C/'whitespace-before.stdout').write_bytes(proc.stdout);(C/'whitespace-before.stderr').write_bytes(proc.stderr)
assert proc.returncode==2
findings=[];contents={}
for line in proc.stdout.decode('utf-8').splitlines():
    match=re.fullmatch(r'(.+):(\d+): trailing whitespace\.',line)
    if not match:continue
    path,num=match.group(1),int(match.group(2))
    assert path.startswith('docs/implementation/20261018-evolution/evidence/')
    if path not in contents:contents[path]=git('show',':'+path).stdout
    physical=contents[path].split(b'\n')[num-1]
    assert physical.endswith(b'\r') and not physical[:-1].endswith((b' ',b'\t'))
    findings.append({'path':path,'line':num})
assert findings
attribute=D/'evidence/.gitattributes'
before=attribute.read_bytes()
paths=sorted(contents)
prefix='docs/implementation/20261018-evolution/evidence/'
rules=''.join(p.removeprefix(prefix)+' whitespace=cr-at-eol\n' for p in paths).encode()
attribute.write_bytes(before.rstrip()+b'\n'+rules)
git('-c','core.autocrlf=false','add','--',attribute.relative_to(R).as_posix())
after=git('diff','--cached','--check')
(C/'whitespace-after.stdout').write_bytes(after.stdout);(C/'whitespace-after.stderr').write_bytes(after.stderr)
assert all((R/p).read_bytes()==b and git('show',':'+p).stdout==b for p,b in contents.items())
receipt={'initial_diff_check_exit':2,'cause':'Original CRLF captures retained byte-identically; no horizontal trailing whitespace in reported source lines.','specific_paths':paths,'CR_only_observations':len(findings),'source_and_staged_hashes':{p:sha(b) for p,b in contents.items()},'after_diff_check_exit':0,'normalization_or_evidence_rewrite':False}
(P/'CRLF-preservation-receipt.json').write_bytes(enc(receipt))
(P/'finish-driver.py').write_bytes(Path(__file__).read_bytes())
git('-c','core.autocrlf=false','add','-f','--',P.relative_to(R).as_posix())
git('diff','--cached','--check')
preserved=json.loads((C/'untracked-before.json').read_bytes())
assert all(sha((R/p).read_bytes())==h for p,h in preserved.items())
proc=subprocess.run([sys.executable,'-B','-X','utf8','scripts/implementation_registry.py','--check'],cwd=R,capture_output=True,check=True)
(C/'registry-final.stdout').write_bytes(proc.stdout);(C/'registry-final.stderr').write_bytes(proc.stderr)
assert not any(not p.startswith('docs/') for p in git('diff','--cached','--name-only').stdout.decode().splitlines())
git('commit','-m','Preserve independent SQL conflict review and isolated nutrition35 evidence')
assert not git('status','--porcelain','-uno').stdout.strip()
result={'head':git('rev-parse','HEAD').stdout.decode().strip(),'registry':128,'previous_criteria_exact':128,'product_changes':[],'CRLF_evidence_preserved':True,'preexisting_untracked_preserved':len(preserved)}
(C/'result.json').write_bytes(enc(result));print(json.dumps(result))
