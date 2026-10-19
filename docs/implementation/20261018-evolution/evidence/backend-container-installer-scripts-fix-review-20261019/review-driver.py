"""Read-only scoped replay for c02 scripts-root guards; no Docker/RUN/removal."""
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

WT=Path('F:/mb-container-runtime-tools-20261019')
MAIN=Path('F:/MetodoBaseWeb-execution-20261018')
OUT=MAIN/'docs/implementation/20261018-evolution/evidence/backend-container-installer-scripts-fix-review-20261019'
OUT.mkdir(exist_ok=False);(OUT/'.gitattributes').write_bytes(b'* -text\n')
TEMP=Path(tempfile.mkdtemp(prefix='backend-installer-scripts-fix-review-'))
HEAD='c02e3a1e1c10e0c6102d9a240697013f7246cfa5'
BASE='af548f71a8a763ba523853e85903a9ab8cf2b0a7'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','--no-replace-objects',*args],cwd=WT)
def save(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain')
assert git('diff','--name-only',BASE,HEAD).decode().splitlines()==['Dockerfile']
files=git('ls-files','-z').decode().split('\0')[:-1]
def photo():return {'files':{name:sha((WT/name).read_bytes()) for name in files if (WT/name).is_file()},
    'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();save('before.json',before)
raw=(WT/'Dockerfile').read_bytes();current=raw.decode().replace('\r\n','\n')
previous=git('show',BASE+':Dockerfile').decode().replace('\r\n','\n')
inverse=current
for old,new in [
    ("site=root/'site-packages';", "site=root/'site-packages'; scripts=Path('/usr/local/bin');"),
    ("Path(sysconfig.get_path('purelib'))==site;", "Path(sysconfig.get_path('purelib'))==site and Path(sysconfig.get_path('scripts'))==scripts;"),
    ("assert root.resolve()==root and site.resolve()==site;", "assert root.resolve()==root and site.resolve()==site; assert scripts.is_dir() and not scripts.is_symlink() and scripts.resolve()==scripts;"),
]:
    assert inverse.count(new)==1
    inverse=inverse.replace(new,old)
assert inverse==previous
lock_names=git('ls-files','*lock').decode().splitlines();assert len(lock_names)==12
locks=[]
for name in lock_names:
    a,b=git('show',BASE+':'+name),git('show',HEAD+':'+name);assert a==b
    locks.append({'path':name,'blob_sha256':sha(a)})
save('locks.json',locks)
runtime=current.split('FROM native-runtime AS runtime\n',1)[1]
block=runtime.split('RUN set -eu;',1)[1].split('\n\n',1)[0]
block='set -eu;'+block
path=OUT/'changed-RUN.sh';path.write_bytes((block+'\n').encode())
syntax=subprocess.run(['C:/Program Files/Git/bin/bash.exe','--noprofile','--norc','-n',str(path)],capture_output=True)
(OUT/'syntax.stdout.log').write_bytes(syntax.stdout);(OUT/'syntax.stderr.log').write_bytes(syntax.stderr)
assert syntax.returncode==0
tokens=shlex.split(block.replace('\\\n',''));code=tokens[tokens.index('-c')+1]
compile(code,'<exact changed pre-removal guard>','exec')
(OUT/'changed-precondition.py').write_bytes(code.encode())
driver=MAIN/'docs/implementation/20261018-evolution/evidence/backend-container-installer-static-review-20261019/test_runtime_installer_paths.py'
frozen=driver.read_bytes();assert sha(frozen)=='67388a1948844492550986f63fb9eab776c8b86a92a94ccf5be26adc81e630f4'
test=TEMP/'test_runtime_installer_paths.py';test.write_bytes(frozen)
related=TEMP/'test_runtime_installer_paths_related.py'
related.write_bytes(Path('C:/Users/Consu/AppData/Local/Temp/test_runtime_installer_paths_related.py').read_bytes())
environment=dict(os.environ,CONTAINER_REVIEW_SOURCE_ROOT=str(WT),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHON_DOTENV_DISABLED='1')
for label,args in [('original-three',[str(test)]),('related-six',[str(related)])]:
    result=subprocess.run([sys.executable,'-X','utf8','-B','-m','pytest',*args,
        '--rootdir='+str(TEMP),'--confcutdir='+str(TEMP),'-q','--tb=short','--junitxml='+str(OUT/(label+'.xml'))],
        cwd=TEMP,env=environment,capture_output=True,timeout=60)
    (OUT/(label+'.stdout.raw.log')).write_bytes(result.stdout)
    (OUT/(label+'.stderr.raw.log')).write_bytes(result.stderr)
    cases=list(ET.parse(OUT/(label+'.xml')).iter('testcase'))
    assert result.returncode==0 and len(cases)==(3 if label=='original-three' else 6)
    assert all(case.find(tag) is None for case in cases for tag in ['failure','error','skipped'])
assert test.read_bytes()==driver.read_bytes()==frozen
after=photo();save('after.json',after);assert before==after and not git('status','--porcelain')
with zipfile.ZipFile(OUT/'source-and-drivers-exact.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('Dockerfile',raw)
    archive.writestr('Dockerfile-before-af548',git('show',BASE+':Dockerfile'))
    archive.writestr('test_runtime_installer_paths.py',frozen)
    archive.writestr('test_runtime_installer_paths_related.py',related.read_bytes())
(OUT/'test_runtime_installer_paths.py').write_bytes(frozen)
(OUT/'test_runtime_installer_paths_related.py').write_bytes(related.read_bytes())
(OUT/'Dockerfile.diff').write_bytes(git('diff',BASE,HEAD,'--','Dockerfile'))
(OUT/'review-driver.py').write_bytes(Path(__file__).read_bytes())
save('summary.json',{'head':HEAD,'parent':BASE,'verdict':'accept_scripts_parent_guard_static_scope',
    'original_frozen_driver_sha256':sha(frozen),'unchanged_original_tests_passed':3,'additional_path_controls_passed':6,
    'failures':0,'errors':0,'skipped':0,'before_original_driver_result':{'passed':1,'failed':2},
    'inverse_full_dockerfile_text_exact_except_three_added_scripts_guard_fragments':True,
    'locks_identical':len(locks),'source_files':len(before['files']),'host_packages':len(before['packages']),
    'source_and_packages_stable':before==after,'changed_run_bash_parse_only':1,'changed_precondition_compile':1,
    'scope':'Static source plus exact guard AST under controlled imports/Temp paths. No Docker/RUN/rm/build/QEMU/PG/Chrome/network/ELF/SCA or actual image inventory claim.',
    'main_staged_or_committed_by_reviewer':False})
print(json.dumps({'original_three':3,'related_six':6,'sources_stable':before==after,'head':HEAD,'proof':str(OUT)}))
