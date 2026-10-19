"""Independent offline source review; never runs a Docker RUN or removal."""
import ast
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path,PurePosixPath
import re
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

WT=Path('F:/mb-container-runtime-tools-20261019')
OUT=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/backend-container-installer-static-review-20261019')
OUT.mkdir(exist_ok=False)
(OUT/'.gitattributes').write_bytes(b'* -text\n')
TEMP=Path(tempfile.mkdtemp(prefix='backend-container-installer-static-'))
HEAD='af548f71a8a763ba523853e85903a9ab8cf2b0a7'
BASE='d038f1c3860296f42ba41ce9ee64a8a4e6300ebc'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','--no-replace-objects',*args],cwd=WT)
def save(name,value):(OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert git('status','--porcelain')==b''
files=git('ls-files','-z').decode().split('\0')[:-1]
def photo():return {'files':{name:sha((WT/name).read_bytes()) for name in files if (WT/name).is_file()},
    'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}
before=photo();save('before.json',before)
raw=(WT/'Dockerfile').read_bytes();text=raw.decode('utf8').replace('\r\n','\n')
assert sha(text.encode())=='c923b779d7e6c97c5ac180c68a7373a2b3fc2f2854453c0bff6f4ce07e6a2ea1'
assert git('diff','--name-only',BASE,HEAD).decode().splitlines()==['Dockerfile']
lock_names=git('ls-files','*lock').decode().splitlines()
assert len(lock_names)==12
lock_rows=[]
for name in lock_names:
    previous=git('show',BASE+':'+name)
    current=git('show',HEAD+':'+name)
    assert previous==current
    assert (WT/name).read_bytes().replace(b'\r\n',b'\n')==current
    lock_rows.append({'name':name,'git_blob_sha256':sha(current)})
save('locks.json',lock_rows)
pins=lambda name:re.findall(r'^([A-Za-z0-9_.-]+)==([^\s\\]+)',(WT/name).read_text(encoding='utf8'),flags=re.M)
applications=pins('requirements-container.lock')+pins('requirements-container-psycopg.lock')
assert len(applications)==54 and len({name.lower() for name,version in applications})==54
assert all(name.lower() not in ('pip','setuptools','wheel') for name,version in applications)
assert pins('requirements-container-bootstrap.lock')==[('pip','26.2.1')]
save('expected-application-pins.json',applications)
lines=text.splitlines();runs=[];i=0
while i<len(lines):
    if lines[i].startswith('RUN '):
        block=lines[i][4:]
        while lines[i].endswith('\\'):
            i+=1;block+='\n'+lines[i]
        runs.append(block)
    i+=1
assert len(runs)==9
shell=[];snippets=[]
(OUT/'shell').mkdir();(OUT/'snippets').mkdir()
for number,block in enumerate(runs):
    path=OUT/'shell'/('RUN-%02d.sh'%number);path.write_bytes((block+'\n').encode())
    result=subprocess.run(['C:/Program Files/Git/bin/bash.exe','--noprofile','--norc','-n',str(path)],capture_output=True)
    assert result.returncode==0
    shell.append({'run':number,'exit':result.returncode,'stdout_sha256':sha(result.stdout),'stderr_sha256':sha(result.stderr)})
    words=shlex.split(block.replace('\\\n',''))
    for j,word in enumerate(words[:-2]):
        if word.endswith('python') and words[j+1]=='-c':
            script=words[j+2];compile(script,'<Dockerfile RUN-%02d>'%number,'exec')
            target=OUT/'snippets'/('RUN-%02d-%02d.py'%(number,j));target.write_bytes(script.encode())
            snippets.append({'run':number,'word':j,'sha256':sha(script.encode()),'compile_only':True})
assert len(snippets)==6
save('syntax.json',{'bash_parse_only':shell,'python_compile_only':snippets})
cleanup=runs[-1]
def commands(block):
    lex=shlex.shlex(block.replace('\\\n',''),posix=True,punctuation_chars=';|&')
    lex.whitespace_split=True
    values=list(lex);parts=[[]]
    for word in values:
        if word==';':parts.append([])
        else:parts[-1].append(word)
    return parts
parts=commands(cleanup)
assert len(parts)==5
assert parts[0]==['set','-eu']
assert parts[1][:2]==parts[4][:2]==['python','-c'] and len(parts[1])==len(parts[4])==3
expected_recursive=['rm','-rf','--','/usr/local/lib/python3.12/site-packages/pip',
    '/usr/local/lib/python3.12/site-packages/pip-26.2.1.dist-info','/usr/local/lib/python3.12/ensurepip']
expected_files=['rm','-f','--','/usr/local/bin/pip','/usr/local/bin/pip3','/usr/local/bin/pip3.12']
assert parts[2]==expected_recursive and parts[3]==expected_files
runtime=text.split('FROM native-runtime AS runtime\n',1)[1]
assert runtime.index(cleanup)<runtime.index('USER appuser')
assert runtime.rfind('COPY ')<runtime.index(cleanup)
assert not any(line.startswith(('COPY ','ADD ','RUN ')) for line in runtime.split('USER appuser',1)[1].splitlines())
contract_mutations={
    'remove_fail_closed_shell':cleanup.replace('set -eu','set +e'),
    'broaden_recursive_target':cleanup.replace('/usr/local/lib/python3.12/site-packages/pip \\', '/usr/local/lib/python3.12/site-packages \\'),
    'recursive_bin_cleanup':cleanup.replace('rm -f -- /usr/local/bin/pip ','rm -rf -- /usr/local/bin/pip '),
    'append_unreviewed_command':cleanup+'; echo unreviewed',
}
def structural(block):
    p=commands(block)
    return len(p)==5 and p[0]==['set','-eu'] and p[2]==expected_recursive and p[3]==expected_files
assert all(not structural(mutant) for mutant in contract_mutations.values())
pre,post=parts[1][2],parts[4][2]
def without_imports(code):
    tree=ast.parse(code)
    tree.body=[node for node in tree.body if not isinstance(node,(ast.Import,ast.ImportFrom))]
    return compile(tree,'<original guards; imports bound to controlled offline fakes>','exec')
pre_code,post_code=without_imports(pre),without_imports(post)
# Exercise the extracted guard ASTs with stdlib Path paths confined to Temp.
# Import metadata/specs and sysconfig are controlled; no shell/removal executes.
counter=0;results=[]
def probe(label,stage,change=None,expected=True):
    global counter
    counter+=1;sandbox=TEMP/('%02d'%counter);sandbox.mkdir()
    def mapped(value):
        path=PurePosixPath(str(value));assert path.is_absolute()
        return sandbox.joinpath(*path.parts[1:])
    root=mapped('/usr/local/lib/python3.12');site=root/'site-packages'
    site.mkdir(parents=True);(mapped('/usr/local/share/metodobase')).mkdir(parents=True)
    mapped('/usr/local/bin').mkdir(parents=True)
    state={'stdlib':'/usr/local/lib/python3.12','purelib':'/usr/local/lib/python3.12/site-packages',
           'pip_version':'26.2.1','rows':applications.copy(),'specs':set(),'symlink':None,'resolve_alias':None}
    if stage=='pre':
        for p in [site/'pip',site/'pip-26.2.1.dist-info',root/'ensurepip/_bundled']:p.mkdir(parents=True)
    if change:change(state,mapped,root,site)
    metadata=SimpleNamespace(version=lambda name:state['pip_version'],
        distributions=lambda:[SimpleNamespace(metadata={'Name':name},version=version) for name,version in state['rows']])
    util=SimpleNamespace(find_spec=lambda name:object() if name in state['specs'] else None)
    globals_={'Path':mapped,'m':metadata,'u':util,'json':json,
              'sysconfig':SimpleNamespace(get_path=lambda key:state[key])}
    original_symlink=Path.is_symlink;original_resolve=Path.resolve
    def symlink(path):return True if state['symlink'] is not None and path==mapped(state['symlink']) else original_symlink(path)
    def resolve(path,*args,**kwargs):
        if state['resolve_alias'] is not None and path==mapped(state['resolve_alias']):return sandbox/'alias'
        return original_resolve(path,*args,**kwargs)
    error=None
    with patch.object(Path,'is_symlink',symlink),patch.object(Path,'resolve',resolve):
        try:exec(pre_code if stage=='pre' else post_code,globals_)
        except (AssertionError,FileNotFoundError) as caught:error=type(caught).__name__
    passed=error is None
    assert passed==expected,(label,passed,error)
    results.append({'name':label,'stage':stage,'accepted':passed,'expected_accept':expected,'error_class':error,
                    'scope':'Extracted original guard AST with controlled offline imports and Temp-mapped literal paths; no Linux image or rm execution.'})
    return state,mapped,root,site

probe('expected guarded pre-removal shape','pre')
probe('closed expected 54 metadata rows','post')
for key,value in [('stdlib','/other/stdlib'),('purelib','/other/site'),('pip_version','25.0')]:
    probe('reject unexpected '+key,'pre',lambda s,p,r,t,k=key,v=value:s.__setitem__(k,v),False)
for path in ['/usr/local/lib/python3.12','/usr/local/lib/python3.12/site-packages']:
    probe('reject resolved root alias '+path,'pre',lambda s,p,r,t,path=path:s.__setitem__('resolve_alias',path),False)
for suffix in ['pip','pip-26.2.1.dist-info']:
    probe('reject target symlink '+suffix,'pre',lambda s,p,r,t,suffix=suffix:s.__setitem__('symlink','/usr/local/lib/python3.12/site-packages/'+suffix),False)
probe('reject ensurepip target symlink','pre',lambda s,p,r,t:s.__setitem__('symlink','/usr/local/lib/python3.12/ensurepip'),False)
probe('reject missing pip tree','pre',lambda s,p,r,t:(t/'pip').rmdir(),False)
probe('reject missing bundled directory','pre',lambda s,p,r,t:(r/'ensurepip/_bundled').rmdir(),False)
for name in ['pip','ensurepip']:
    probe('reject importable '+name,'post',lambda s,p,r,t,name=name:s['specs'].add(name),False)
probe('reject residual wheel anywhere below prefix','post',lambda s,p,r,t:(p('/usr/local/residue.whl')).write_bytes(b'not-a-real-wheel'),False)
probe('reject extra pip metadata','post',lambda s,p,r,t:(t/'pip-99.dist-info').mkdir(),False)
for name in ['pip','pip3','pip3.12']:
    probe('reject script '+name,'post',lambda s,p,r,t,name=name:p('/usr/local/bin/'+name).write_bytes(b'synthetic'),False)
probe('reject dangling script symlink witness','post',lambda s,p,r,t:s.__setitem__('symlink','/usr/local/bin/pip3'),False)
for length in [53,55]:
    probe('reject metadata count '+str(length),'post',lambda s,p,r,t,length=length:s.__setitem__('rows',applications[:length] if length<54 else applications+[('extra','1')]),False)
for name in ['pip','setuptools','wheel']:
    probe('reject installer metadata '+name,'post',lambda s,p,r,t,name=name:s.__setitem__('rows',applications[:-1]+[(name,'1')]),False)
# Explicit contract limits, not claimed adversarial rejections. The script-root
# alias remains unseen by pre-checks; no deletion is executed in this probe.
probe('scope witness: scripts root is not inspected by pre-guard','pre',lambda s,p,r,t:s.__setitem__('resolve_alias','/usr/local/bin'),True)
probe('scope witness: same-count changed app version not compared to lock','post',lambda s,p,r,t:s.__setitem__('rows',[(applications[0][0],'999')]+applications[1:]),True)
save('guard-semantics.json',results)
save('structural-contract.json',{'command_count':5,'recursive_targets':expected_recursive[3:],
    'script_targets':expected_files[3:],'guard_before_all_deletions':True,'after_all_copies':True,
    'before_unprivileged_user':True,'strict_command_mutants_rejected':list(contract_mutations)})
# Independently scan exactly the copied Python source families, without import.
copy_families=['config','core','src','api','web','utils']
source_names=sorted(name for name in files if (any(name.startswith(prefix+'/') for prefix in copy_families) and name.endswith('.py')) or name in ['db_bootstrap.py'])
imports=[];calls=[]
for name in source_names:
    tree=ast.parse((WT/name).read_bytes(),filename=name)
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] in {'pip','ensurepip','venv'}:imports.append({'path':name,'line':node.lineno,'module':alias.name})
        elif isinstance(node,ast.ImportFrom) and (node.module or '').split('.')[0] in {'pip','ensurepip','venv'}:
            imports.append({'path':name,'line':node.lineno,'module':node.module})
    for line_no,line in enumerate((WT/name).read_text(encoding='utf8').splitlines(),1):
        if re.search(r'\b(pip|ensurepip|venv)\b',line):calls.append({'path':name,'line':line_no,'code':line.strip()})
assert imports==[]
save('copied-source-installer-review.json',{'python_files':len(source_names),'direct_imports':imports,'word_occurrences':calls,
    'limitation':'Direct source inspection only; indirect dependency/dynamic imports and actual runtime startup remain build/functional gates.'})
after=photo();save('after.json',after);assert before==after
assert git('status','--porcelain')==b''
with zipfile.ZipFile(OUT/'source-exact.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name in ['Dockerfile','.dockerignore','entrypoint.sh',*lock_names]:archive.writestr(name,(WT/name).read_bytes())
(OUT/'Dockerfile.diff').write_bytes(git('diff',BASE,HEAD,'--','Dockerfile'))
save('summary.json',{'head':HEAD,'parent':BASE,'sources':len(before['files']),'packages':len(before['packages']),
    'sources_and_packages_stable':before==after,'locks_identical':len(lock_rows),'only_changed_file':'Dockerfile',
    'shell_parse_only':len(shell),'python_compile_only':len(snippets),'guard_semantic_probes':len(results),
    'expected_guard_rejections':sum(not r['accepted'] for r in results),'positive_guards':2,'scope_limits':2,
    'structural_mutants_rejected':len(contract_mutations),'expected_application_lock_rows':54,
    'docker_runs_executed':0,'container_builds':0,'qemu':0,'external_network':0,
    'verdict_pending_review_writeup':True})
print(json.dumps({'proof':str(OUT),'guard_probes':len(results),'expected_rejections':sum(not r['accepted'] for r in results),'syntax_shell':len(shell),'compiled_python':len(snippets),'sources_stable':before==after}))
