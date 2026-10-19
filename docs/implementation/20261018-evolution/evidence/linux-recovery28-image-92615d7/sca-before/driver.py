import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

root=Path('F:/MetodoBaseWeb-linux-lab-20261019/evidence/recovery28-image-92615d7')
out=root/'sca'
out.mkdir(exist_ok=False)
inventory=(root/'runtime-inventory.json').read_bytes()
value=json.loads(inventory)
rows=value['runtime_inventory']['packages']
assert len(rows)==55 and len({p['name'].lower() for p in rows})==55
for package in rows:
    assert re.fullmatch(r'[A-Za-z0-9_.-]+',package['name']) and re.fullmatch(r'[A-Za-z0-9_.+!-]+',package['version'])
requirements=out/'actual-image-55.txt'
requirements.write_text(''.join(p['name']+'=='+p['version']+'\n' for p in rows),encoding='utf-8')
command=[sys.executable,'-m','pip_audit','--no-deps','--disable-pip','--vulnerability-service','osv',
         '--progress-spinner','off','--format','json','--output',str(out/'audit.json'),'-r',str(requirements)]
started=time.monotonic()
run=subprocess.run(command,capture_output=True,timeout=300)
(out/'audit.log').write_bytes(run.stdout+run.stderr)
summary={'image_id':value['image_id'],'image_source':'92615d74ee3a4bd82333c4606cca7898eb324a88',
         'runtime_inventory_sha256':hashlib.sha256(inventory).hexdigest(),'actual_distributions':55,
         'tool':'pip-audit2.10.1','service':'OSV','scope':'Python distributions actually installed in this Linux image; not Debian OS packages',
         'exit':run.returncode,'seconds':time.monotonic()-started,
         'requirements_sha256':hashlib.sha256(requirements.read_bytes()).hexdigest(),
         'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}}
if (out/'audit.json').is_file():
    audit=json.loads((out/'audit.json').read_text())
    summary['audited_dependencies']=len(audit['dependencies'])
    summary['vulnerability_count']=sum(len(p.get('vulns',[])) for p in audit['dependencies'])
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['exit','seconds','actual_distributions']}|{k:summary[k] for k in ['audited_dependencies','vulnerability_count'] if k in summary}))
