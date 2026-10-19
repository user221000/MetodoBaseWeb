from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,tempfile,sys
WT=Path(r'F:\mb-container-runtime-tools-20261019')
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
OUT=LAB/'evidence/runtime-installer-scripts-parent-fix32-20261019'
DRIVER=Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/backend-container-installer-static-review-20261019/test_runtime_installer_paths.py')
EXPECTED='67388a1948844492550986f63fb9eab776c8b86a92a94ccf5be26adc81e630f4'
PYTHON=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-candidate-web-20261018\Scripts\python.exe')
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(WT),*args])
assert sys.argv[1] in ['before','after'];phase=sys.argv[1]
assert sha(DRIVER.read_bytes())==EXPECTED
if phase=='before':
    OUT.mkdir(exist_ok=False);assert git('rev-parse','HEAD').decode().strip()=='af548f71a8a763ba523853e85903a9ab8cf2b0a7';assert not git('status','--porcelain')
else:assert OUT.is_dir()
for root in [WT,LAB,OUT,PYTHON.parent,DRIVER.parent]:
    for path in [root,*root.parents]:assert not path.is_symlink(),path
temp=Path(tempfile.mkdtemp(prefix='metodobase-runtime-installer-path-fix32-20261019-'));copied=temp/'test_runtime_installer_paths.py';copied.write_bytes(DRIVER.read_bytes());assert sha(copied.read_bytes())==EXPECTED
env=os.environ.copy()
for name in ['PYTHONPATH','PYTHONHOME','PYTEST_ADDOPTS','PYTEST_PLUGINS']:env.pop(name,None)
env.update({'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','CONTAINER_REVIEW_SOURCE_ROOT':str(WT)})
locks={rel:{'checkout_sha256':sha((WT/rel).read_bytes()),'git_blob':git('rev-parse','HEAD:'+rel).decode().strip()} for rel in git('ls-files','*lock').decode().splitlines()}
argv=[str(PYTHON),'-B','-m','pytest','-q','-p','no:cacheprovider','--rootdir='+str(temp),'--confcutdir='+str(temp),'--basetemp='+str(temp/'cases'),'--junitxml='+str(OUT/(phase+'.xml')),str(copied)]
run=subprocess.run(argv,cwd=temp,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
log=run.stdout+'\nSTDERR\n'+run.stderr;(OUT/(phase+'.log')).write_text(log,encoding='utf-8')
expected_exit=1 if phase=='before' else 0;assert run.returncode==expected_exit,(run.returncode,log)
if phase=='before':assert '2 failed, 1 passed' in run.stdout
else:assert '3 passed' in run.stdout
locks_after={rel:sha((WT/rel).read_bytes()) for rel in locks};assert all(locks_after[rel]==row['checkout_sha256'] for rel,row in locks.items())
receipt={'captured_utc':datetime.now(timezone.utc).isoformat(),'phase':phase,'source_head_before_commit':git('rev-parse','HEAD').decode().strip(),'worktree':str(WT),'driver_original':str(DRIVER),'driver_sha256':EXPECTED,'driver_copy':str(copied),'python_exe':str(PYTHON),'python_exe_sha256':sha(PYTHON.read_bytes()),'argv':argv,'cwd':str(temp),'exit':run.returncode,'expected_result':'1 positive pass, 2 negatives fail' if phase=='before' else '3 pass','log_sha256':sha((OUT/(phase+'.log')).read_bytes()),'junit_sha256':sha((OUT/(phase+'.xml')).read_bytes()),'dockerfile_checkout_sha256':sha((WT/'Dockerfile').read_bytes()),'lock_count':len(locks),'locks_before':locks,'locks_after':locks_after,'locks_quiet':True,'safe_environment_keys':{k:env[k] for k in ['PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTHONNOUSERSITE','PYTHONDONTWRITEBYTECODE','CONTAINER_REVIEW_SOURCE_ROOT']},'scope':'Exact independent driver, temp copies outside MAIN, pytest plugin autoload disabled and no project conftest. Controlled AST preguard only; no rm, installers, network, Docker/QEMU or real /usr/local access.'}
path=OUT/(phase+'-receipt.json');assert not path.exists();path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({'phase':phase,'exit':run.returncode,'result':receipt['expected_result'],'locks_quiet':True,'driver_sha256':EXPECTED,'receipt':str(path)},indent=2))
