"""Preserve closed diagnostics, authenticated native inputs and the R25 contract."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET

root=Path(r'F:\MetodoBaseWeb-execution-20261018')
ev=root/'docs/implementation/20261018-evolution/evidence'
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
out=ev/'prepared-wave121-20261019'
sha=lambda b:hashlib.sha256(b).hexdigest()
files={'driver.py':Path(__file__).read_bytes()}
for directory,names in [
 ('metodobase-expat-clinic-inspection-20261019',['driver.py','header.raw.h','receipt.json']),
 ('metodobase-expat-clinic-verification-20261019',['driver.py','builder-before.GitLF.py','builder-after.RAW.py','receipt.json','prepared/source-preparation.json']),
]:
    for name in names:files[directory+'/'+name]=(tmp/directory/name).read_bytes()
contract=Path(r'F:\mb-r25-progress-20261019\docs\implementation\20261018-evolution\evidence\backend-r25-contract-20261019\contract.md').read_bytes()
assert sha(contract)=='879d093b45f40f519113c02638f2cbcd649d593708f7978cec1d4fb543099611'
files['R25/contract.RAW.md']=contract

diagnostic=tmp/'metodobase-mfa31-broad-diagnostic-20261019'
summary=json.loads((diagnostic/'summary.private.json').read_bytes())
assert summary['exit']==1 and not summary['timed_out'] and summary['cases']==2381
assert summary['source_packages_quiet'] and summary['pip_exit']==0
cases=ET.parse(diagnostic/'serial.xml').findall('.//testcase')
counts=Counter('error' if c.find('error') is not None else 'failure' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed' for c in cases)
assert dict(counts)=={'passed':2360,'failure':2,'skipped':1,'error':18},counts
private=tmp/'metodobase-mfa31-broad-diagnostic-raw-private-20261019.zip'
assert not private.exists()
with zipfile.ZipFile(private,'x',zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(diagnostic.iterdir()):
        if path.is_file():archive.write(path,path.name)
with zipfile.ZipFile(private) as archive:assert archive.testzip() is None
public={k:summary[k] for k in ['head','exit','timed_out','seconds','cases','source_packages_quiet','sources','packages','pip_exit','scope']}
public.update({'counts':dict(counts),'initial_maxfail':20,'whole_suite_accepted':False,
 'failed_modules':dict(Counter(c.get('classname') for c in cases if c.find('failure') is not None or c.find('error') is not None)),
 'case_ids':[{'module':r['module'],'case':r['case'],'kind':r['kind']} for r in summary['failures']],
 'private_originals':{'path':str(private),'bytes':private.stat().st_size,'sha256':sha(private.read_bytes())},
 'classification':'Two Google fixture assertions and eighteen publication fixture setup errors. Cause and legitimate adoption under review, not twenty demonstrated product defects.'})
files['broad31-diagnostic/summary.SANITIZED.json']=(json.dumps(public,indent=2)+'\n').encode()
for name in ['driver.py','before.json','after.json','before-pip.raw.log','after-pip.raw.log']:
    files['broad31-diagnostic/'+name]=(diagnostic/name).read_bytes()

# Root sensitive-value scan, not a substitute for the independently recorded scanners.
for name,blob in files.items():
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        p=match.start()
        assert not(p>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[p-30:p])),name
    assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+',blob),name
assert not out.exists()
out.mkdir()
(out/'.gitattributes').write_bytes(b'* -text\n')
for name,blob in files.items():
    path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
(out/'manifest.json').write_bytes((json.dumps({'files':{p.relative_to(out).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(out.rglob('*')) if p.is_file()}},indent=2)+'\n').encode())
print(json.dumps({'files':len(files)+1,'manifest_sha256':sha((out/'manifest.json').read_bytes()),'broad_counts':dict(counts)}))
