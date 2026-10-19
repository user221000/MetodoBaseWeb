from pathlib import Path
import hashlib,json,sys
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
RUN=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-expat-m2-native-validation-20261019')
sys.path.insert(0,str(LAB/'scripts'))
import guest_access
remote="""python3 - <<'PY'
from pathlib import Path
import io,json,hashlib,subprocess,tarfile
container='7cbc85823cba'
def copy(path):
 raw=subprocess.check_output(['sudo','-n','docker','cp',container+':'+path,'-'])
 with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
  members=tar.getmembers();assert len(members)==1 and members[0].isfile() and members[0].size<1000000
  return tar.extractfile(members[0]).read()
before=copy('/usr/local/share/metodobase/native-runtime/before.tsv')
status=copy('/var/lib/dpkg/status')
first={line.split('\\t')[0].split(':')[0]:line.split('\\t')[1] for line in before.decode().splitlines()}
last={}
for stanza in status.decode().split('\\n\\n'):
 fields={}
 for line in stanza.splitlines():
  if ': ' in line and not line.startswith(' '):k,v=line.split(': ',1);fields[k]=v
 if fields.get('Status')=='install ok installed':last[fields['Package']]=fields['Version']
assert first==last
state=json.loads(subprocess.check_output(['sudo','-n','docker','inspect',container]))[0]['State']
assert not state['Running'] and state['ExitCode']==1
result={'same_package_versions_before_after_failed_apt_update':True,'base_package_count':len(first),
        'before_tsv_sha256':hashlib.sha256(before).hexdigest(),'stopped_container_dpkg_status_sha256':hashlib.sha256(status).hexdigest(),
        'packages':last,'libssl3t64_version':last.get('libssl3t64'),'libpq5_installed': 'libpq5' in last,'gcc_installed':'gcc' in last,
        'compiler_and_libpq_install_reached':False,'scope':'Failed PREIMAGE only; confirms original base package invariance, no planned builder or final runtime acceptance.'}
out=Path('/var/tmp/metodobase-expat-m2-native-20261019/refresh-review')
(out/'base-dpkg-invariance.json').write_text(json.dumps(result,indent=2)+'\\n')
print(json.dumps(result))
PY
"""
r=guest_access.run(remote,timeout=45)
(RUN/'base-dpkg-invariance-raw.log').write_bytes(r.stdout+b'\nSTDERR\n'+r.stderr)
assert r.returncode==0,r.stderr.decode()
(RUN/'base-dpkg-invariance-source.json').write_bytes(r.stdout)
print(json.dumps({k:v for k,v in json.loads(r.stdout).items() if k!='packages'}))

