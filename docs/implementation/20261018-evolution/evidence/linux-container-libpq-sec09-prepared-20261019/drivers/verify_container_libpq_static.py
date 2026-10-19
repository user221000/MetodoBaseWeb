from pathlib import Path
from datetime import datetime,timezone
import hashlib,io,json,lzma,re,shlex,subprocess,tarfile,zipfile
WT=Path(r'F:\mb-container-pq-20261019')
ROOT=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/container-system-libpq-20261019')
BASE='eb4ae1e5e6b9685b30a4330bea381a97df11ebb0'
checks=[]
def check(name,value):
    assert value,name
    checks.append(name)
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-c','core.hooksPath=NUL','-C',str(WT),*args])
check('base_head',git('rev-parse','HEAD').decode().strip()==BASE)
for rel in ['requirements_web.lock','requirements_web.txt','requirements_web-windows.lock','requirements-container-bootstrap.lock','requirements_build.lock','requirements-test-desktop.lock']:
    check('unchanged_'+rel,(WT/rel).read_bytes().replace(b'\r\n',b'\n')==git('show',BASE+':'+rel))
def blocks(text):
    matches=list(re.finditer(r'^([\w.-]+)==([^\s\\]+).*?(?=^[\w.-]+==|\Z)',text,re.M|re.S))
    return {m.group(1):m.group(0) for m in matches}
old=blocks((WT/'requirements_web.lock').read_text());new=blocks((WT/'requirements-container.lock').read_text())
check('53_original_nonadapter_blocks_preserved_exactly',len(new)==53 and new=={k:v for k,v in old.items() if k!='psycopg2-binary'})
check('source_adapter_only',set(blocks((WT/'requirements-container-psycopg.lock').read_text()))=={'psycopg2'})
check('backend_only',set(blocks((WT/'requirements-container-build.lock').read_text()))=={'setuptools'})
sdist=ROOT/'psycopg2-2.9.13.tar.gz'
check('source_sha256',hashlib.sha256(sdist.read_bytes()).hexdigest()=='d36784fc2dae69523ba4b79c7d1d1b4d6e83e87836874f111262f4db940b16a6')
with tarfile.open(fileobj=io.BytesIO(sdist.read_bytes()),mode='r:gz') as tf:
    pyproject=tf.extractfile('psycopg2-2.9.13/pyproject.toml').read().decode()
    check('source_backend_declaration',pyproject=='[build-system]\nrequires = ["setuptools>=70.1"]\nbuild-backend = "setuptools.build_meta"\n')
backend=ROOT/'setuptools-84.0.0-py3-none-any.whl'
check('backend_sha256',hashlib.sha256(backend.read_bytes()).hexdigest()=='51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670')
with zipfile.ZipFile(backend) as z:check('backend_zip_crc',z.testzip() is None)
apt=json.loads((ROOT/'apt-primary/metadata.json').read_text())
for row in apt['downloads']:
    check('primary_'+row['file'],hashlib.sha256((ROOT/'apt-primary'/row['file']).read_bytes()).hexdigest()==row['sha256'])
docker=(WT/'Dockerfile').read_text()
instructions=[];buffer=''
for line in docker.splitlines():
    if not buffer and (not line.strip() or line.lstrip().startswith('#')):continue
    buffer+=line.rstrip()[:-1]+' ' if line.rstrip().endswith('\\') else line
    if line.rstrip().endswith('\\'):continue
    instructions.append(buffer);buffer=''
check('docker_continuations_closed',not buffer)
froms=[line for line in instructions if line.startswith('FROM ')]
check('single_immutable_external_base',froms==[
 'FROM python:3.12.15-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe AS base',
 'FROM base AS native-runtime','FROM native-runtime AS psycopg-build','FROM native-runtime AS deps','FROM native-runtime AS runtime'])
runs=[line[4:] for line in instructions if line.startswith('RUN ')]
syntax=ROOT/'docker-runs.syntax-only.sh'
syntax.write_text('#!/bin/sh\n'+ '\n'.join(runs)+'\n',newline='\n')
result=subprocess.run([r'C:\Program Files\Git\bin\bash.exe','--noprofile','--norc','-n',str(syntax)],capture_output=True)
check('all_docker_run_shell_syntax',result.returncode==0)
for line in runs:
    for token in shlex.split(line,posix=True):
        if token.startswith('from pathlib import Path;'):
            compile(token,'docker-python-fragment','exec')
check('python_build_fragments_parse',True)
check('no_backend_directory_copy','COPY --from=psycopg-build /opt/' not in docker and 'COPY --from=psycopg-build /usr/local' not in docker)
check('source_wheel_local_hashed_no_dependency_resolution','--no-build-isolation --no-binary=:all: --no-index --find-links=/tmp/metodobase-native-source' in docker)
check('runtime_inherits_native_packages','FROM native-runtime AS runtime' in docker)
check('entrypoint_unchanged',docker[docker.index('# Asset version used by existing templates.'):].replace('COPY --from=deps /usr/local/share/metodobase/psycopg2-build /usr/local/share/metodobase/psycopg2-build\n','')==git('show',BASE+':Dockerfile').decode().split('# Asset version used by existing templates.',1)[1].join(['# Asset version used by existing templates.','']))
changed=git('diff','--name-only').decode().splitlines()
untracked=git('ls-files','--others','--exclude-standard').decode().splitlines()
allowed=['Dockerfile','requirements-container-apt-metadata.lock','requirements-container-build.lock','requirements-container-psycopg.lock','requirements-container.lock']
check('only_five_candidate_files',set(changed+untracked)==set(allowed))
files={rel:{'bytes':(WT/rel).stat().st_size,'sha256':hashlib.sha256((WT/rel).read_bytes()).hexdigest()} for rel in allowed}
receipt={'finished_utc':datetime.now(timezone.utc).isoformat(),'base_head':BASE,'check_count':len(checks),'checks':checks,'candidate_files':files,
         'original_packages':54,'unchanged_application_entries':53,'candidate_runtime_expected_packages_including_pip':55,
         'adapter_distribution_change':'psycopg2-binary==2.9.13 -> psycopg2==2.9.13',
         'scope':'Static validation only; no Linux build, source execution, APT signature verification or runtime acceptance.',
         'pending':['Independent SEC review','Linux APT signatures and simulated package closure','Build after coordinated resource window','Actual ELF/version/linkage/SBOM and Python+OS SCA','Real application migration/startup under separately accepted product candidate']}
(ROOT/'static-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'files':files,'linux_build_or_source_execution':False},indent=2))
