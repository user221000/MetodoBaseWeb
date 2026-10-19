from pathlib import Path
import hashlib,json,re,subprocess
WT=Path(r'F:\mb-container-pq-20261019')
ROOT=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/container-system-libpq-20261019')
BASE='eb4ae1e5e6b9685b30a4330bea381a97df11ebb0'
assert subprocess.check_output(['git','-C',str(WT),'rev-parse','HEAD']).decode().strip()==BASE
assert not subprocess.check_output(['git','-C',str(WT),'status','--porcelain=v1','--untracked-files=all'])
def write(name,text):
    with (WT/name).open('x',encoding='utf-8',newline='\n') as f:f.write(text)
original=(WT/'requirements_web.lock').read_text(encoding='utf-8')
match=re.search(r'^psycopg2-binary==2\.9\.13 \\\n.*?(?=^[a-zA-Z0-9][a-zA-Z0-9_.-]*==|\Z)',original,re.M|re.S)
assert match
remaining=original[:match.start()]+original[match.end():]
remaining=remaining[remaining.index('alembic=='):]
write('requirements-container.lock','# Container-only dependency subset of requirements_web.lock at '+BASE+'\n# All 53 other application entries are unchanged. Native adapter source is locked separately.\n'+remaining)
write('requirements-container-psycopg.lock','# Native adapter source only; compiled in an isolated build stage.\npsycopg2==2.9.13 \\\n    --hash=sha256:d36784fc2dae69523ba4b79c7d1d1b4d6e83e87836874f111262f4db940b16a6\n')
write('requirements-container-build.lock','# PEP 517 backend only; /opt/psycopg-build-tools is excluded from runtime.\nsetuptools==84.0.0 \\\n    --hash=sha256:51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670\n')
metadata=json.loads((ROOT/'apt-primary/metadata.json').read_text())
paths={'stable.InRelease':'deb.debian.org_debian_dists_trixie_InRelease',
       'updates.InRelease':'deb.debian.org_debian_dists_trixie-updates_InRelease',
       'security.InRelease':'security.debian.org_debian-security_dists_trixie-security_InRelease'}
write('requirements-container-apt-metadata.lock','# Primary InRelease inputs captured 2026-10-19.\n# APT must first validate signatures and expiry using the immutable base keyring.\n'+''.join(r['sha256']+'  /var/lib/apt/lists/'+paths[r['file']]+'\n' for r in metadata['downloads'] if r['file'] in paths))
names=lambda text:dict(re.findall(r'^([\w.-]+)==([^\s\\]+)',text,re.M))
before=names(original);after=names(remaining)
assert len(before)==54 and len(after)==53
assert {k:v for k,v in before.items() if k!='psycopg2-binary'}==after
print(json.dumps({'original_packages':54,'unchanged_nonadapter_packages':53,'adapter':'psycopg2-binary 2.9.13 -> psycopg2 2.9.13 source','new_locks':4}))
