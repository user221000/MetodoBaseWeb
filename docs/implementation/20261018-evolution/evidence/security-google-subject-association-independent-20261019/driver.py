from pathlib import Path
import ast
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(r'F:\mb-security-google-subject-peer-20261019')
MAIN=Path(r'F:\MetodoBaseWeb-execution-20261018')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-google-subject-association-independent-20261019'
PRIVATE=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-sec-google-subject-peer-private-20261019')
HEAD='345aa7ce16f65fec9481b48cfcd63c33ff3835fc'
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert not git('status','--porcelain','--untracked-files=no')
assert not OUT.exists() and {p.name for p in PRIVATE.iterdir()}=={'acl.private.raw.txt'}
author=MAIN/'docs/implementation/20261018-evolution/evidence/root-google-subject-contract-review-20261019'
assert sha((author/'manifest.json').read_bytes())=='47f479889f5ff5693894909767df971f930116c897e1a1342c4f39ebc6c5d330'
manifest=json.loads((author/'manifest.json').read_bytes())
for name,item in manifest.items():
    data=(author/name).read_bytes()
    assert len(data)==item['bytes'] and sha(data)==item['sha256']
frozen=json.loads((author/'source.json').read_bytes())
for name,item in frozen['files'].items():assert sha(git('show',HEAD+':'+name))==item['git_lf_sha256']
extra='tests/test_security_google_subject_peer.py'
ast.parse((ROOT/extra).read_bytes())
OUT.mkdir(parents=True);(OUT/'.gitattributes').write_bytes(b'* -text\n')
(OUT/'driver.py').write_bytes(Path(__file__).read_bytes())
(OUT/'test_security_google_subject_peer.py').write_bytes((ROOT/extra).read_bytes())
names=sorted(set(git('ls-files','-z').decode().split('\0')[:-1]+[extra]))
def acl():
    command="$reviewAcl = Get-Acl -LiteralPath '"+str(PRIVATE)+"'; [pscustomobject]@{sddl=$reviewAcl.Sddl; protected=$reviewAcl.AreAccessRulesProtected; rules=$reviewAcl.Access.Count} | ConvertTo-Json -Compress"
    value=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',command]))
    original=(PRIVATE/'acl.private.raw.txt').read_text(encoding='utf-8-sig').strip()
    assert value['sddl']==original and value['protected'] is True and value['rules']==2
    return {'protected':True,'explicit_allow_rules':2,'principals':'Current user and SYSTEM only',
        'sddl_sha256':sha(value['sddl'].encode()),'private_acl_receipt_sha256':sha((PRIVATE/'acl.private.raw.txt').read_bytes())}
def photo():
    return {'files':{n:sha((ROOT/n).read_bytes()) for n in names},
        'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),
        'python_sha256':sha(Path(sys.executable).read_bytes()),'raw_private_acl':acl()}
def dump(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
dump('provider-contract.json',{'reference':'https://developers.google.com/identity/gsi/web/guides/verify-google-id-token',
    'consulted_utc':datetime.now(timezone.utc).isoformat(),
    'facts':['Use stable Google sub to associate the local identity; email can change.',
        'For a third-party email without hd, email_verified can be historical, so another ownership challenge is recommended.',
        'A pre-existing local account can be explicitly linked after proving access to it.'],
    'limits':'This task models a structurally valid tokeninfo result. It does not bypass or test Google signature/issuer/expiry verification and makes no live Google exploit claim.'})
before=photo();dump('before.json',before)
pip0=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-before.raw.log').write_bytes(pip0.stdout+pip0.stderr);assert pip0.returncode==0
receipts=PRIVATE/'observations';receipts.mkdir()
cmd=[sys.executable,'-X','utf8','-B','tests/run_isolated.py',extra,'-q','--tb=short',
    '--basetemp='+str(PRIVATE/'pytest-run'),'--junitxml='+str(PRIVATE/'results.xml')]
run=subprocess.run(cmd,cwd=ROOT,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',
    SEC_GOOGLE_PRIVATE_RECEIPTS=str(receipts)),capture_output=True,timeout=480)
(PRIVATE/'stdout.raw.log').write_bytes(run.stdout);(PRIVATE/'stderr.raw.log').write_bytes(run.stderr)
cases=ET.parse(PRIVATE/'results.xml').findall('.//testcase')
projection=[{'case':c.get('classname')+'::'+c.get('name'),
    'outcome':next((kind for kind in ['failure','error','skipped'] if c.find(kind)is not None),'passed')} for c in cases]
dump('cases.STRUCTURAL.json',projection)
observed={p.stem:json.loads(p.read_bytes()) for p in sorted(receipts.glob('*.json'))}
dump('observations.json',observed)
after=photo();dump('after.json',after)
pip1=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(OUT/'pip-after.raw.log').write_bytes(pip1.stdout+pip1.stderr)
summary={'source_head':HEAD,'cases':len(cases),'outcomes':{k:sum(c['outcome']==k for c in projection) for k in ['passed','failure','error','skipped']},
    'exit':run.returncode,'source_count':len(names),'packages':len(before['packages']),
    'sources_packages_python_acl_exact':before==after,'pip_before':pip0.returncode,'pip_after':pip1.returncode,
    'author_primaries_authenticated':len(manifest),'own_receipts':len(observed),
    'scope':'Independent synthetic migrated32 SQLite HTTP with only Google HTTP transport substituted; delivery remains the inherited offline fixture. No identity override, live token, Google signature bypass, PG, browser, VM or production exploit claim.'}
dump('summary.json',summary)
dump('private-originals.json',{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(PRIVATE.iterdir()) if p.is_file()})
print(json.dumps(summary))
assert before==after and pip1.returncode==0
assert len(cases)==8 and summary['outcomes']=={'passed':4,'failure':4,'error':0,'skipped':0} and run.returncode==1
