from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shlex,subprocess,tempfile
WT=Path(r'F:\mb-container-runtime-tools-20261019');BASE='d038f1c3860296f42ba41ce9ee64a8a4e6300ebc'
OUT=Path(r'F:\MetodoBaseWeb-linux-lab-20261019/evidence/runtime-installer-removal-20261019');OUT.mkdir(exist_ok=False)
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(WT),*args])
assert git('rev-parse','HEAD').decode().strip()==BASE
before=git('show',BASE+':Dockerfile');current=(WT/'Dockerfile').read_bytes();s=current.decode('utf-8').replace('\r\n','\n')
def contract(text):
    runtime=text.split('FROM native-runtime AS runtime\n',1)[1]
    checks={
      'runtime cleanup after dependency copy':runtime.index('rm -rf -- /usr/local/lib/python3.12/site-packages/pip')>runtime.index('COPY --from=deps /usr/local/lib/python3.12/site-packages'),
      'pip module removed':'rm -rf -- /usr/local/lib/python3.12/site-packages/pip \\\n' in runtime,
      'pip metadata exact version removed':'/usr/local/lib/python3.12/site-packages/pip-26.2.1.dist-info \\\n' in runtime,
      'ensurepip entire subtree removed':'/usr/local/lib/python3.12/ensurepip;' in runtime,
      'all pip entry scripts removed':'rm -f -- /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.12;' in runtime,
      'stdlib and purelib path guards':"Path(sysconfig.get_path('stdlib'))==root and Path(sysconfig.get_path('purelib'))==site" in runtime,
      'resolved roots guards':'root.resolve()==root and site.resolve()==site' in runtime,
      'cleanup targets guarded against symlinks':'p.is_dir() and not p.is_symlink()' in runtime,
      'installed pip expected before removal':"m.version('pip')=='26.2.1'" in runtime,
      'pip and ensurepip import postconditions':"u.find_spec(n) is None for n in ('pip','ensurepip')" in runtime,
      'remaining wheels forbidden':"assert not any(root.rglob('*.whl'))" in runtime,
      'pip metadata remnants forbidden':"startswith(('pip-','pip.'))" in runtime,
      'entry symlink remnants forbidden':'p.exists() or p.is_symlink()' in runtime,
      'expected 54 only application distributions':'assert len(rows)==54' in runtime,
      'installer metadata absent':"not in ('pip','setuptools','wheel')" in runtime,
      'provenance inventory emitted':'runtime-python-metadata.json' in runtime,
      'build venv retained for SCA':"python -m venv /opt/psycopg-build-tools" in text and '/opt/psycopg-build-tools/bin/python -m pip --isolated freeze --all' in text,
      'dependency-stage pip check retained':'python -m pip check;' in text.split('FROM native-runtime AS runtime\n',1)[0],
      'cleanup before unprivileged runtime':runtime.index('rm -rf -- /usr/local/lib/python3.12/site-packages/pip')<runtime.index('USER appuser'),
    }
    return checks
checks=contract(s);assert all(checks.values()),checks
mutations={
 'ensurepip removal omitted':s.replace('/usr/local/lib/python3.12/ensurepip;','/usr/local/lib/python3.12/ensurepip-unrelated;'),
 'wheel postcondition omitted':s.replace("assert not any(root.rglob('*.whl'));",''),
 'old runtime count':s.replace('assert len(rows)==54','assert len(rows)==55'),
 'build venv silently omitted':s.replace('python -m venv /opt/psycopg-build-tools','true'),
 'pip import postcondition omitted':s.replace("u.find_spec(n) is None for n in ('pip','ensurepip')","True"),
 'path resolve guard omitted':s.replace('root.resolve()==root and site.resolve()==site','True'),
}
mutant_rows=[]
for name,mutant in mutations.items():
    failed=[k for k,v in contract(mutant).items() if not v];assert failed,name;mutant_rows.append({'name':name,'rejected_by':failed})
# Parse Docker RUN shell blocks; execute bash syntax checking only, never RUN bodies.
runs=[];lines=s.splitlines();i=0
while i<len(lines):
    if lines[i].startswith('RUN '):
        block=lines[i][4:]
        while block.endswith('\\'):
            i+=1;block=block[:-1]+'\n'+lines[i]
        runs.append(block)
    i+=1
shell_rows=[];python_snippets=[]
for index,block in enumerate(runs):
    file=OUT/('RUN-%02d.sh'%index);file.write_text(block+'\n',encoding='utf-8')
    cp=subprocess.run([r'C:\Program Files\Git\bin\bash.exe','--noprofile','--norc','-n',str(file)],capture_output=True,text=True);assert cp.returncode==0,cp.stderr
    shell_rows.append({'file':file.name,'sha256':sha(file.read_bytes()),'syntax_exit':cp.returncode})
    words=shlex.split(block)
    for n,word in enumerate(words[:-2]):
        if word.endswith('python') and words[n+1]=='-c':
            code=words[n+2];compile(code,'<Dockerfile static Python>','exec');python_snippets.append({'run':index,'code_sha256':sha(code.encode()),'bytes':len(code.encode()),'compiled_only':True})
changed=git('diff','--name-only').decode().splitlines();assert changed==['Dockerfile'],changed
lockpaths=git('ls-files','*lock').decode().splitlines();lockrows=[]
for rel in lockpaths:
    base=git('show',BASE+':'+rel);data=(WT/rel).read_bytes();assert data.replace(b'\r\n',b'\n')==base.replace(b'\r\n',b'\n'),rel
    lockrows.append({'path':rel,'git_blob':git('rev-parse',BASE+':'+rel).decode().strip(),'checkout_sha256':sha(data)})
diff=git('diff','--','Dockerfile');(OUT/'Dockerfile.diff').write_bytes(diff)
receipt={'captured_utc':datetime.now(timezone.utc).isoformat(),'base_head':BASE,'worktree':str(WT),'checks':[{'name':k,'pass':v} for k,v in checks.items()],'mutants':mutant_rows,'bash_syntax':shell_rows,'python_compiled_not_executed':python_snippets,'locks_unchanged':lockrows,'changed_files':changed,'dockerfile_lf_sha256':sha(s.encode()),'dockerfile_checkout_sha256':sha(current),'diff_sha256':sha(diff),'gates_pending':['Linux build; actual 54-distribution inventory and import/linkage/tests; actual filesystem absence of pip/ensurepip/wheels; runtime and build-stage SCA including vendors; full OS rescan; no SEC09/OS71 closure.'],'scope':'Static validation only. No Docker/QEMU, RUN-body execution or host cleanup performed.'}
(OUT/'static-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':len(checks),'mutants_rejected':len(mutant_rows),'shell_runs_syntax_checked':len(shell_rows),'python_snippets_compile_only':len(python_snippets),'locks_unchanged':len(lockrows),'dockerfile_lf_sha256':receipt['dockerfile_lf_sha256']},indent=2))
