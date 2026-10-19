from pathlib import Path, PurePosixPath
import ast, hashlib, io, json, lzma, os, re, socket, subprocess, sys, tarfile, tempfile, tomllib, urllib.request, zipfile
from unittest.mock import patch

HERE=Path(__file__).parent
ROOT=Path('F:/mb-pq-sec')
PROOF=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/linux-container-libpq-sec09-prepared-20261019')
LAB=Path('F:/MetodoBaseWeb-linux-lab-20261019/evidence/container-system-libpq-20261019')
RESULTS=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def readj(p):return json.loads(p.read_bytes())
def check(name,fn):
    try:
        fn();RESULTS.append({'name':name,'passed':True})
    except Exception as e:
        RESULTS.append({'name':name,'passed':False,'exception_class':type(e).__name__,'reason':str(e)[:250]})
def require(v,message='criterion failed'):
    if not v:raise AssertionError(message)
def reject(fn):
    try:fn()
    except (AssertionError,zipfile.BadZipFile):return
    raise AssertionError('unexpected acceptance of changed input')

docker=(ROOT/'Dockerfile').read_text(encoding='utf8')
baseline=git('show','HEAD^:Dockerfile').decode('utf8')
logical=re.sub(r'\\\r?\n[ \t]*',' ',docker)
base_logical=re.sub(r'\\\r?\n[ \t]*',' ',baseline)
instructions=[x for x in logical.splitlines() if x and not x.startswith('#')]
snippets=re.findall(r'python -c "([^"]*)"',logical)
guards=[x for x in snippets if x.startswith('from pathlib import Path;')]
require(len(guards)==4,'four original Python guards required')
manifest=readj(PROOF/'evidence-manifest.json')
freeze=readj(PROOF/'freeze.json')

def proof_authentication():
    require(sha((PROOF/'evidence-manifest.json').read_bytes())=='ecfd599f4d328bed856519fee8618f19643d97e66fbcd4c4c64540c470db00e6')
    require(len(manifest['files'])==manifest['file_count']==39)
    for r in manifest['files']:
        b=(PROOF/r['file']).read_bytes();require(len(b)==r['bytes'] and sha(b)==r['sha256'],r['file'])
check('authenticate 39 declared author proof files and manifest',proof_authentication)
def candidate_authentication():
    require(git('rev-parse','HEAD').decode().strip()=='d038f1c3860296f42ba41ce9ee64a8a4e6300ebc')
    changed=set(git('diff','--name-only','HEAD^','HEAD').decode().splitlines())
    require(changed==set(freeze['exclusive_git_blob_files']))
    for f,r in freeze['exclusive_git_blob_files'].items():
        b=git('show','HEAD:'+f)
        require(sha(b)==r['sha256'] and len(b)==r['bytes'],f)
        require((ROOT/f).read_bytes()==b and (PROOF/'candidate'/f).read_bytes()==b,f)
        original=(Path(freeze['worktree'])/f).read_bytes()
        require(sha(original)==r['worktree_sha256'],f)
        require(original.replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n'),f)
check('authenticate five Git blobs and explicitly verify author EOL normalization',candidate_authentication)
def blocks(text):
    lines=text.splitlines(keepends=True); found={};start=None;key=None
    for i,line in enumerate(lines):
        m=re.match(r'^([a-zA-Z0-9_-]+)==',line)
        if m:
            if start is not None:found[key]=''.join(lines[start:i])
            start=i;key=m[1]
    if start is not None:found[key]=''.join(lines[start:])
    return found
def app_conservation():
    old=blocks((ROOT/'requirements_web.lock').read_text(encoding='utf8'))
    new=blocks((ROOT/'requirements-container.lock').read_text(encoding='utf8'))
    require(len(old)==54 and len(new)==53)
    require(set(old)-set(new)=={'psycopg2-binary'} and all(old[k]==v for k,v in new.items()))
    changed=set(git('diff','--name-only','HEAD^','HEAD').decode().splitlines())
    require(not any(f in changed for f in ['requirements_web.lock','requirements_web.txt','requirements.txt','requirements-container-bootstrap.lock']))
check('all 53 other full application blocks exact; original web desktop bootstrap untouched',app_conservation)

assets=readj(PROOF/'primary-assets.json')
def source_asset():
    r=assets['packages']['psycopg2']['asset']; b=(LAB/r['filename']).read_bytes()
    require(len(b)==r['bytes']==378068 and sha(b)==r['sha256']=='d36784fc2dae69523ba4b79c7d1d1b4d6e83e87836874f111262f4db940b16a6')
    meta=readj(PROOF/'psycopg2.metadata.json')
    require(any(u['filename']==r['filename'] and u['digests']['sha256']==sha(b) and u['size']==len(b) and u['url']==r['url'] for u in meta['urls']))
    with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as t:
        pyproject=t.extractfile('psycopg2-2.9.13/pyproject.toml').read()
        cfg=t.extractfile('psycopg2-2.9.13/setup.cfg').read()
        require(pyproject==(PROOF/'psycopg2-pyproject.toml').read_bytes())
        require(cfg==(PROOF/'psycopg2-setup.cfg').read_bytes())
        require(tomllib.loads(pyproject.decode())['build-system']=={'requires':['setuptools>=70.1'],'build-backend':'setuptools.build_meta'})
        require(re.search(r'^static_libpq\s*=\s*0\s*$',cfg.decode(),re.M))
    require(r['sha256'] in (ROOT/'requirements-container-psycopg.lock').read_text())
check('source hash size and URL match PyPI; exact nonstatic-libpq source and declared backend',source_asset)
def backend_asset():
    name='setuptools-84.0.0-py3-none-any.whl';b=(LAB/name).read_bytes();meta=readj(PROOF/'setuptools.metadata.json')
    require(sha(b)=='51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670')
    require(any(u['filename']==name and u['digests']['sha256']==sha(b) and u['size']==len(b) for u in meta['urls']))
    with zipfile.ZipFile(io.BytesIO(b)) as z:require(z.testzip() is None)
    require(sha(b) in (ROOT/'requirements-container-build.lock').read_text())
check('pinned isolated build backend matches PyPI wheel and passes ZIP CRC',backend_asset)

def index_integrity():
    lock=(ROOT/'requirements-container-apt-metadata.lock').read_text()
    for suite in ['stable','updates','security']:
        release=(LAB/'apt-primary'/f'{suite}.InRelease').read_bytes()
        require(release==(PROOF/'apt-primary'/f'{suite}.InRelease').read_bytes())
        require(sha(release) in lock)
        data=(LAB/'apt-primary'/f'{suite}.Packages.xz').read_bytes()
        section=release.decode().split('SHA256:\n',1)[1].split('\nSHA512:',1)[0]
        require(re.search(r'^ '+sha(data)+r'\s+'+str(len(data))+r'\s+main/binary-amd64/Packages\.xz$',section,re.M))
check('three exact InRelease inputs bind retained amd64 Packages.xz bytes and lengths (not signatures)',index_integrity)
def records(raw):
    result=[]
    for paragraph in raw.split('\n\n'):
        fields={}
        for line in paragraph.splitlines():
            if line and not line[0].isspace() and ': ' in line:
                k,v=line.split(': ',1);fields[k]=v
        if fields:result.append(fields)
    return result
def runtime_prediction():
    predicted=readj(PROOF/'runtime-os-expected.json')['predicted_new_packages']
    require(len(predicted)==10)
    indices={k:records(lzma.decompress((LAB/'apt-primary'/f'{k}.Packages.xz').read_bytes()).decode()) for k in ['stable','updates','security']}
    for p in predicted:
        selected=[r for r in indices[p['metadata_source']] if r.get('Package')==p['package'] and r.get('Version')==p['version']]
        require(len(selected)==1,p['package']);r=selected[0]
        require(r['SHA256']==p['sha256'] and int(r['Size'])==p['bytes'] and r.get('Depends','')==p['depends'],p['package'])
        require(p['url'].endswith('/'+r['Filename']))
check('ten proposed runtime additions match pinned package records; no solver or closure claim',runtime_prediction)

def stage_contract():
    froms=[x for x in instructions if x.startswith('FROM ')]
    require(froms==['FROM python:3.12.15-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe AS base','FROM base AS native-runtime','FROM native-runtime AS psycopg-build','FROM native-runtime AS deps','FROM native-runtime AS runtime'])
    runtime=logical.split('FROM native-runtime AS runtime',1)[1]
    copyfrom=[x for x in runtime.splitlines() if x.startswith('COPY --from=')]
    require(all(x.startswith('COPY --from=deps /usr/local/') for x in copyfrom) and len(copyfrom)==3)
    require('/opt/psycopg-build-tools' not in runtime and '/usr/bin/gcc' not in runtime)
    require(runtime[runtime.index('# Asset version'):]==base_logical[base_logical.index('# Asset version'):])
check('stage inheritance and runtime copies isolate compiler/backend; nonroot and readiness tail unchanged',stage_contract)
def apt_contract():
    for stage in ['native-runtime','psycopg-build']:
        body=logical.split('AS '+stage+'\n',1)[1].split('\nFROM ',1)[0]
        require('Acquire::AllowInsecureRepositories=false update;' in body)
        require(body.index(' update;')<body.index('sha256sum --check')<body.index(' install -y --no-remove --no-install-recommends'))
        require('APT::Get::AllowUnauthenticated=false' in body)
        require(body.count('signed-by=/usr/share/keyrings/debian-archive-keyring.gpg')==3)
        require('Check-Valid-Until=false' not in body and 'allow-unauthenticated' not in body)
    require('Existing base packages changed' in logical and 'Existing native runtime packages changed' in logical)
check('APT signature update precedes pinned metadata and no-remove installs; preservation postconditions present',apt_contract)
def compile_install_contract():
    wheel=next(x for x in instructions if x.startswith('RUN set -eu;') and 'pip --isolated wheel' in x)
    cmd=wheel.split('pip --isolated wheel',1)[1].split(';',1)[0]
    for flag in ['--require-hashes','--no-deps','--no-build-isolation','--no-binary=:all:','--no-index','--find-links=/tmp/metodobase-native-source']:
        require(flag in cmd,flag)
    require('/opt/psycopg-build-tools/bin/python -m pip --isolated wheel' in wheel)
    install=next(x for x in instructions if x.startswith('RUN set -eu;') and '-r /tmp/psycopg-wheelhouse/built-wheel.lock' in x)
    for flag in ['--no-index','--no-deps','--require-hashes','--only-binary=:all:']:
        require(flag in install,flag)
    require('python -m pip check;' in install)
check('source compile and local install require hashes offline without implicit backend dependency build',compile_install_contract)
def syntax():
    for s in snippets:compile(s,'<original Docker inline Python>','exec')
    script='\n'.join(x[4:] for x in instructions if x.startswith('RUN '))+'\n'
    env=os.environ.copy();env.pop('BASH_ENV',None);env.pop('ENV',None)
    p=subprocess.run(['C:/Program Files/Git/bin/bash.exe','--noprofile','--norc','-n'],input=script.encode(),capture_output=True,env=env)
    require(p.returncode==0,p.stderr.decode(errors='replace')[:200])
check('all original Python snippets compile and shell RUN bodies pass nonexecuting bash syntax',syntax)

def original_code(index):
    tree=ast.parse(guards[index]);require(isinstance(tree.body[0],ast.ImportFrom) and tree.body[0].module=='pathlib')
    # Only injection point: remove the Path import and supply virtual Path. All original assertions remain.
    tree.body=tree.body[1:];return compile(tree,'<original guard with virtual Path>','exec')
def tsv_guard(index,after):
    content={'before.tsv':'libssl3t64\t3.5.7-1~deb13u3\nlibc6\t2.41-12+deb13u4\n','after.tsv':after,'native-before.tsv':'libssl3t64\t3.5.7-1~deb13u3\nlibc6\t2.41-12+deb13u4\n','builder-dpkg.tsv':after}
    class VP:
        def __init__(self,p):self.p=PurePosixPath(p)
        def __truediv__(self,n):return VP(str(self.p/n))
        def read_text(self):return content[self.p.name]
    exec(original_code(index),{'Path':VP})
for index,label in [(0,'base packages'),(1,'native runtime packages')]:
    good='libssl3t64\t3.5.7-1~deb13u3\nlibc6\t2.41-12+deb13u4\nlibpq5\t17.11-0+deb13u1\n'
    check(label+': original guard accepts unchanged baseline plus addition',lambda i=index,g=good:tsv_guard(i,g))
    check(label+': original guard rejects altered base version',lambda i=index,g=good:reject(lambda:tsv_guard(i,g.replace('3.5.7-1~deb13u3','3.5.8-1'))))
    check(label+': original guard rejects removed base package',lambda i=index,g=good:reject(lambda:tsv_guard(i,'\n'.join(x for x in g.splitlines() if not x.startswith('libc6'))+'\n')))

source=(LAB/'psycopg2-2.9.13.tar.gz').read_bytes()
def source_guard(payload,expect_write):
    writes=[]
    class VP:
        def __init__(self,p):require(p=='/tmp/metodobase-native-source/psycopg2-2.9.13.tar.gz')
        def write_bytes(self,b):writes.append(b)
    def open_memory(url,timeout):
        require(url==assets['packages']['psycopg2']['asset']['url'] and timeout==60);return io.BytesIO(payload)
    with patch.object(urllib.request,'urlopen',open_memory):
        if expect_write:exec(original_code(2),{'Path':VP});require(writes==[payload])
        else:reject(lambda:exec(original_code(2),{'Path':VP}));require(not writes)
check('source original guard accepts exact bytes and writes only after verification',lambda:source_guard(source,True))
check('source original guard rejects same-length digest mutation before write',lambda:source_guard(bytes([source[0]^1])+source[1:],False))
check('source original guard rejects truncation before write',lambda:source_guard(source[:-1],False))

def wheel_guard(kind):
    with tempfile.TemporaryDirectory(prefix='wheel-',dir=HERE) as tmp:
        directory=Path(tmp);name='psycopg2-2.9.13-cp312-cp312-linux_x86_64.whl'
        if kind=='name':name='psycopg2_binary-2.9.13-cp312-cp312-linux_x86_64.whl'
        names={'vendor':['psycopg2.libs/libssl-vendored.so'],'absolute':['/outside.so'],'traversal':['psycopg2/../outside.so']}.get(kind,['psycopg2/_psycopg.fake.so'])
        with zipfile.ZipFile(directory/name,'w',compression=zipfile.ZIP_STORED) as z:
            for n in names:z.writestr(n,b'SYNTHETIC_CONTENT_NOT_ELF')
        if kind=='two':(directory/name.replace('cp312','cp313')).write_bytes((directory/name).read_bytes())
        if kind=='crc':
            b=(directory/name).read_bytes();require(b.count(b'SYNTHETIC_CONTENT_NOT_ELF')==1)
            (directory/name).write_bytes(b.replace(b'SYNTHETIC_CONTENT_NOT_ELF',b'XYNTHETIC_CONTENT_NOT_ELF'))
        def vp(p):return directory if p=='/wheelhouse' else PurePosixPath(p)
        fn=lambda:exec(original_code(3),{'Path':vp})
        if kind=='valid':
            fn();require((directory/'built-wheel.lock').read_text()=='psycopg2==2.9.13 --hash=sha256:'+sha((directory/name).read_bytes())+'\n')
        else:reject(fn);require(not (directory/'built-wheel.lock').exists())
for kind in ['valid','name','two','vendor','absolute','traversal','crc']:
    check('wheel original guard '+('accepts exact local ZIP and records its SHA' if kind=='valid' else 'rejects '+kind),lambda k=kind:wheel_guard(k))

summary={'scope':'STATIC ONLY; no container build, compiler execution, package installation, provider request, database or runtime security acceptance','head':git('rev-parse','HEAD').decode().strip(),'total':len(RESULTS),'passed':sum(r['passed'] for r in RESULTS),'results':RESULTS,'original_guard_sha256':[sha(s.encode()) for s in guards],'network_transport':'source guard uses BytesIO and patched urlopen; no shell RUN executed','author_manifest_sha256':sha((PROOF/'evidence-manifest.json').read_bytes())}
out=HERE/'results.json';require(not out.exists(),'immutable result already exists');out.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
print(json.dumps({'total':summary['total'],'passed':summary['passed'],'failed':[r for r in RESULTS if not r['passed']]}))
sys.exit(0 if summary['total']==summary['passed'] else 1)
