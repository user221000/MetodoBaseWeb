from pathlib import Path
import ast,contextlib,copy,hashlib,importlib.util,io,json,os,re,struct,sys,tarfile,tempfile
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).parent;ROOT=Path('F:/mb-expat-m2-sec');CODE=ROOT/'runtime-source/expat-sec10'
PROOF=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-expat-sec10-m2-prepared-20261019')
ARCHIVE=Path('F:/MetodoBaseWeb-linux-lab-20261019/evidence/sca-native-triage31-20261019/primary/Python-3.12.15.tar.xz')
def sha(b):return hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('reviewed_expat_builder',CODE/'rebuild_pyexpat.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
lock=m.pins();selected=m.source_files(ARCHIVE,lock);original=selected['Modules/expat/xmlparse.c'];diff=(CODE/'13c5f63.patch').read_bytes()
RESULTS=[];FACTS={};forbidden_calls=[]
def require(v,msg='criterion failed'):
    if not v:raise AssertionError(msg)
def test(name,fn):
    try:fn();RESULTS.append({'name':name,'passed':True})
    except Exception as e:RESULTS.append({'name':name,'passed':False,'error_class':type(e).__name__,'reason':str(e)[:200]})
def reject(fn,classes=(AssertionError,)):
    try:fn()
    except classes:return
    raise AssertionError('changed input unexpectedly accepted')
def forbidden(*args,**kwargs):forbidden_calls.append(True);raise RuntimeError('Compiler/network/subprocess path forbidden during pure probes')

def provenance():
    freeze=json.loads((PROOF/'freeze.json').read_bytes());receipts=[]
    for name,expected in {**freeze['source_hashes'],**freeze['unchanged_locks']}.items():
        raw=(Path(freeze['worktree'])/name).read_bytes();require(sha(raw)==expected,name)
        ours=(ROOT/name).read_bytes();require(raw.replace(b'\r\n',b'\n')==ours.replace(b'\r\n',b'\n'),name)
        receipts.append({'path':name,'author_raw_sha256':expected,'own_git_sha256':sha(ours),'raw_equal':raw==ours,'only_eol_difference':raw!=ours})
    require(set(freeze['changed_files'])==set(os.fsdecode(__import__('subprocess').check_output(['git','diff','--name-only','HEAD^','HEAD'],cwd=ROOT)).splitlines()))
    FACTS['source_receipts']=receipts
test('Six frozen product files and twelve unchanged locks authenticated, with explicit EOL receipts',provenance)

def patch_exact():
    up=json.loads((PROOF/'reused-primary/expat-fix-77214-commit.json').read_bytes());require(up['sha']==lock['upstream_fix_commit']=='13c5f63a7f1c52c2feee3b16a1134d4fb68e9ea0')
    patch_text=next(x['patch'] for x in up['files'] if x['filename']=='expat/lib/xmlparse.c')
    adds=lambda s:[l[1:] for l in s.splitlines() if l.startswith('+') and not l.startswith('+++')]
    require(adds(diff.decode())==adds(patch_text) and len(adds(patch_text))==5)
    fixed=m.backport(original,diff,lock);require(sha(fixed)==lock['source_after_sha256'])
    body=fixed.decode().split('\nXML_ParseBuffer(',1)[1].split('\nXML_GetBuffer(',1)[0];require(m.INSERT in body)
test('Exact upstream five-line hunk, no fuzzy patch, and expected patched ParseBuffer hash',patch_exact)
def prepared():
    out=HERE/'prepared-positive';record=m.prepare(ARCHIVE,out,lock)
    changed=[]
    for name,b in selected.items():
        actual=(out/'source'/name).read_bytes()
        if actual!=b:changed.append(name)
        if name!='Modules/expat/xmlparse.c':require(actual==b,name)
    require(len(selected)==30 and changed==['Modules/expat/xmlparse.c'])
    require(record['version']=='2.8.5' and record['changed_source_files']==changed)
    FACTS['prepared']={'files':len(selected),'changed':changed,'header_config_namespace_and_capi_unchanged':True,'record_sha256':sha((out/'source-preparation.json').read_bytes())}
test('Actual pure preparation writes thirty files and changes only xmlparse; headers/config/namespace/CAPI intact',prepared)
def macro_and_binding():
    p=selected['Modules/pyexpat.c'].decode();e=selected['Modules/_elementtree.c'].decode()
    require(re.search(r'#\s*define\s+Py_BUILD_CORE_MODULE\b',p[:500]) is not None)
    require(p.index('Py_BUILD_CORE_MODULE')<p.index('#include "Python.h"'))
    with tarfile.open(ARCHIVE,mode='r:xz') as t:port=t.extractfile('Python-3.12.15/Include/pyport.h').read().decode()
    require('Py_BUILD_CORE_MODULE' in port and re.search(r'#\s*define\s+Py_BUILD_CORE\b',port[:4000]))
    require('capi->Parse = XML_Parse;' in p and '"pyexpat", "expat_CAPI"' in e)
    require(all('st->expat_capi->'+n+'_VERSION != XML_'+n+'_VERSION' in e for n in ['MAJOR','MINOR','MICRO']))
    FACTS['macro_binding']={'Py_BUILD_CORE_MODULE_defined_in_source_before_Python_h':True,'Py_BUILD_CORE_derived_in_pyport':True,'ElementTree_capsule_and_version_checks_preserved':True,'no_extra_command_line_macro_required':True}
test('Source itself defines core-module macro before Python headers; pyport derives core; ElementTree shares unchanged capsule',macro_and_binding)
for name,source,patchbytes in [('mutated-source',b' '+original,diff),('already-patched',m.backport(original,diff,lock),diff),('changed-patch',original,diff+b'\n')]:
    test('Reject '+name+' before any output',lambda s=source,p=patchbytes:reject(lambda:m.backport(s,p,lock)))
for key,value in [('source_before_sha256',None),('source_after_sha256','0'*64),('patch_sha256',{'invalid':'type'})]:
    test('Reject inconsistent source-pin '+key,lambda k=key,v=value:reject(lambda:m.backport(original,diff,{**lock,k:v})))
class WrongArchive:
    def read_bytes(self):return b'wrong source archive'
test('Reject archive hash mismatch before TAR parsing',lambda:reject(lambda:m.source_files(WrongArchive(),lock)))
def synthetic_tar(case):
    target=HERE/(case+'.tar.xz');require(not target.exists())
    with tarfile.open(target,'w:xz') as t:
        for i in range(30):
            name=f'Python-3.12.15/Modules/expat/file{i:02}.c';data=b'x';kind=tarfile.REGTYPE
            if i==29:
                if case=='traversal':name='Python-3.12.15/Modules/expat/../outside.c'
                if case=='duplicate':name='Python-3.12.15/Modules/expat/file00.c'
                if case=='symlink':kind=tarfile.SYMTYPE
                if case=='hardlink':kind=tarfile.LNKTYPE
                if case=='oversized-member':data=b'x'*(1024*1024)
            if case=='total-bound' and i<5:data=b'x'*(900*1024)
            row=tarfile.TarInfo(name);row.type=kind;row.linkname='outside' if kind!=tarfile.REGTYPE else '';row.size=len(data) if kind==tarfile.REGTYPE else 0;t.addfile(row,io.BytesIO(data) if row.size else None)
    pinned={**lock,'psf_source_sha256':sha(target.read_bytes())}
    # Re-pin only synthetic bytes to reach inner TAR guards. This is not valid PSF provenance.
    reject(lambda:m.source_files(target,pinned))
for case in ['traversal','duplicate','symlink','hardlink','oversized-member','total-bound']:
    test('Re-pinned synthetic TAR rejects '+case,lambda c=case:synthetic_tar(c))
def existing_output():
    out=HERE/'existing-output';out.mkdir();(out/'marker').write_bytes(b'owned-marker')
    reject(lambda:m.prepare(ARCHIVE,out,lock),(FileExistsError,));require((out/'marker').read_bytes()==b'owned-marker')
test('Existing output is rejected before overwriting owned bytes',existing_output)

VALID_ABI={'SOABI':lock['expected_soabi'],'EXT_SUFFIX':lock['expected_ext_suffix'],'SIZEOF_VOID_P':8,'Py_DEBUG':0,'Py_ENABLE_SHARED':1,'CC':'gcc','CFLAGS':'-DNDEBUG -O3','CCSHARED':'-fPIC','LDSHARED':'gcc -shared','CONFIG_ARGS':'pinned-base'}
def guarded_build(change=None,environment=None,platform='linux',machine='x86_64',version=(3,12,15),ptr=8):
    abi={**VALID_ABI,**(change or {})};start=len(forbidden_calls)
    with patch.object(m.sys,'platform',platform),patch.object(m.platform,'machine',return_value=machine),patch.object(m.sys,'version_info',version),patch.object(m.struct,'calcsize',return_value=ptr),patch.object(m.sysconfig,'get_config_var',side_effect=abi.get),patch.dict(os.environ,environment or {},clear=True),patch.object(m.subprocess,'run',side_effect=forbidden),patch.object(m.urllib.request,'urlopen',side_effect=forbidden):
        reject(lambda:m.build(HERE/'never-built',lock,{}))
    require(len(forbidden_calls)==start,'probe entered forbidden subprocess/network path')
for label,kwargs in [('host-platform',{'platform':'win32'}),('architecture',{'machine':'aarch64'}),('Python-patch-version',{'version':(3,12,14)}),('pointer-width',{'ptr':4}),('SOABI',{'change':{'SOABI':'wrong'}}),('suffix',{'change':{'EXT_SUFFIX':'.so'}}),('debug-ABI',{'change':{'Py_DEBUG':1}}),('shared-ABI',{'change':{'Py_ENABLE_SHARED':0}})]:
    test('Original build precondition rejects '+label+' before compiler',lambda k=kwargs:guarded_build(**k))
for name in ['CC','CXX','CFLAGS','CPPFLAGS','LDFLAGS','LDSHARED','AR','ARFLAGS']:
    test('Compiler environment override rejected: '+name,lambda n=name:guarded_build(environment={n:'SYNTHETIC_UNREVIEWED'}))
def invalid_cli_output():
    with patch.object(m.sys,'argv',['rebuild_pyexpat.py','--build','--output','/expat-output/../outside']),patch.object(m.sys,'platform','linux'),patch.object(m.urllib.request,'urlopen',side_effect=forbidden):reject(m.main)
test('Build CLI rejects a different owned output before download/preparation',invalid_cli_output)
def elf_guard():
    tree=ast.parse((CODE/'rebuild_pyexpat.py').read_text(encoding='utf8'));build=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build')
    assertion=next(n for n in ast.walk(build) if isinstance(n,ast.Assert) and 'raw[:6]' in ast.unparse(n.test))
    code=compile(ast.fix_missing_locations(ast.Module(body=[assertion],type_ignores=[])),'<original ELF guard>','exec')
    valid=bytearray(64);valid[:6]=b'\x7fELF\x02\x01';valid[18:20]=(62).to_bytes(2,'little')
    exec(code,{'raw':bytes(valid)})
    for mutate in [b'',b'not ELF',bytes(valid[:4])+b'\x01'+bytes(valid[5:]),bytes(valid[:5])+b'\x02'+bytes(valid[6:]),bytes(valid[:18])+(183).to_bytes(2,'little')+bytes(valid[20:])]:reject(lambda b=mutate:exec(code,{'raw':b}))
test('Exact extracted ELF metadata guard rejects nonELF/32bit/big-endian/wrong-machine bytes without loading them',elf_guard)
def docker_contract():
    text=(ROOT/'Dockerfile').read_text(encoding='utf8');require('FROM psycopg-build AS expat-build' in text)
    require('RUN /opt/psycopg-build-tools/bin/python -I /tmp/metodobase-expat-sec10/rebuild_pyexpat.py --build --output /expat-output' in text)
    copies=[line for line in text.splitlines() if line.startswith('COPY --from=expat-build')];require(len(copies)==2)
    require('/expat-output/pyexpat.cpython-312-x86_64-linux-gnu.so /usr/local/lib/python3.12/lib-dynload/pyexpat.cpython-312-x86_64-linux-gnu.so' in copies[0])
    require(' /expat-output/source ' not in '\n'.join(copies) and '_elementtree' not in '\n'.join(copies))
    for required in ['build-provenance.json','sbom.json','source-pins.json','13c5f63.patch','COPYING.expat','small-binding-tests.log']:require(required in copies[1])
    source=(CODE/'rebuild_pyexpat.py').read_text(encoding='utf8');require("sys.executable,'-I','-S','-c',smoke" in source)
    require('base_before==base_after' in source and "identities+=sorted(include.rglob('*.h'))" in source)
    require("('pyexpat.c','expat/xmlparse.c','expat/xmlrole.c','expat/xmltok.c')" in source)
    FACTS['pending_actual_build']=['MODULE_PYEXPAT_CFLAGS and actual resolved compiler/argv','ELF/linkage/namespace and native imports','base preservation postconditions executed','small tests and wider bounded stdlib/application XML suite','actual runtime54 + build/runtime SCA, no ignores']
test('Docker isolates compilation and copies one extension plus provenance/license only; recorded build guards reviewed',docker_contract)
out=HERE/'own-results.json';require(not out.exists());out.write_text(json.dumps({'scope':'Offline pure source preparation, AST guards, tiny synthetic TAR/ELF byte inputs; no target C/native compile/import/application/VM','total':len(RESULTS),'passed':sum(r['passed'] for r in RESULTS),'results':RESULTS,'facts':FACTS,'forbidden_subprocess_or_network_calls':len(forbidden_calls)},indent=2)+'\n',encoding='utf8')
print(json.dumps({'total':len(RESULTS),'passed':sum(r['passed'] for r in RESULTS),'failed':[r for r in RESULTS if not r['passed']],'forbidden_calls':len(forbidden_calls)}))
raise SystemExit(0 if all(r['passed'] for r in RESULTS) else 1)
