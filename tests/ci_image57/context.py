"""Bind Docker COPY bytes to one explicit Git commit; no checkout filters."""
from pathlib import Path, PurePosixPath
from contextlib import contextmanager
import ast, hashlib, io, json, os, re, shlex, shutil, subprocess, sys, tarfile
from . import authority,source_proof

MAX_CONTEXT=64*1024**2
PREPARATION_RESERVE=4*MAX_CONTEXT+2*source_proof.MAX_PROOF+16*1024**2
APP_PREFIXES=('config/','core/','src/','api/','web/','utils/','static/','fonts/')
APP_FILES={'entrypoint.sh','alembic.ini','db_bootstrap.py'}
CORPUS=('web/data/password-blocklist/.gitattributes','web/data/password-blocklist/LICENSE.SecLists',
        'web/data/password-blocklist/manifest.json','web/data/password-blocklist/seclists-100k.sha256bin')
CORPUS_SHA256='d0d787734cd3ad38731ca3012e34532ff109e915feeb152cbf0fbd361c27c101'
CORPUS_LICENSE_SHA256='3dbdc93d5f8829de0941744841730a09c106d0732e5ae0e98ca1d77be7ded66c'

@contextmanager
def git_policy(git_dir=None,work_tree=None):
    old=dict(os.environ)
    try:
        for key in list(os.environ):
            if key.upper().startswith('GIT_'):os.environ.pop(key)
        os.environ.update(GIT_NO_REPLACE_OBJECTS='1',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,
            GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0')
        if git_dir is not None:os.environ['GIT_DIR']=str(git_dir)
        if work_tree is not None:os.environ['GIT_WORK_TREE']=str(work_tree)
        yield
    finally:
        os.environ.clear();os.environ.update(old)

def git(repository,*args):
    return subprocess.check_output(['git','--no-replace-objects',*args],cwd=repository)

def source(repository,revision,name):
    authority.canonical_name(name)
    return git(repository,'cat-file','blob',revision+':'+name)

def json_object(raw):
    def unique(pairs):
        value={}
        for name,item in pairs:
            if name in value:raise ValueError('Duplicate image57 JSON key')
            value[name]=item
        return value
    return json.loads(raw,object_pairs_hook=unique)

def check_source(repository,revision):
    authority.regular_directory(repository)
    if re.fullmatch('[0-9a-f]{40}',revision) is None:raise ValueError('Explicit full source commit required')
    if git(repository,'cat-file','-t',revision)!=b'commit\n':raise ValueError('Source must be original Git commit')

def validate_corpus(manifest,payload,license_raw,attributes):
    if (manifest.get('format')!='sorted-unique-sha256-digests-32-byte-records'
            or type(manifest.get('unique_digests')) is not int or manifest['unique_digests']<=0
            or type(manifest.get('payload_bytes')) is not int or len(payload)!=manifest['payload_bytes']
            or len(payload)!=32*manifest['unique_digests']
            or hashlib.sha256(payload).hexdigest()!=manifest.get('payload_sha256')
            or hashlib.sha256(license_raw).hexdigest()!=manifest.get('license_sha256')
            or b'*.sha256bin -text' not in attributes.replace(b'\r\n',b'\n').splitlines()):
        raise ValueError('Password corpus source metadata or RAW bytes differ')
    previous=None
    for offset in range(0,len(payload),32):
        item=payload[offset:offset+32]
        if previous is not None and item<=previous:raise ValueError('Password corpus records not strictly sorted and unique')
        previous=item
    return {'bytes':len(payload),'unique_digests':manifest['unique_digests'],'payload_sha256':manifest['payload_sha256']}

def require_current_corpus(manifest):
    if (manifest.get('payload_sha256')!=CORPUS_SHA256 or manifest.get('payload_bytes')!=3199968
            or type(manifest.get('payload_bytes')) is not int or manifest.get('unique_digests')!=99999
            or type(manifest.get('unique_digests')) is not int or manifest.get('license_sha256')!=CORPUS_LICENSE_SHA256):
        raise ValueError('Mandatory reviewed B19 corpus identity differs')

def validate_manifest(directory,revision,*,proof_required=True):
    directory=authority.regular_directory(directory)
    value=json_object(authority.regular_file(directory/'source-manifest.json').read_bytes())
    if (re.fullmatch('[0-9a-f]{40}',revision) is None or value['source_commit']!=revision
            or type(value['archive_bytes']) is not int or not 0<value['archive_bytes']<=MAX_CONTEXT
            or re.fullmatch('[0-9a-f]{40}',value['source_tree']) is None
            or value.get('all_members_readback') is not True or value.get('current57_critical_inputs_exact')!=12
            or value.get('runtime_distributions_expected')!=57):
        raise ValueError('Context source or size differs')
    archive=authority.regular_file(directory/'source-context.tar')
    if archive.stat().st_size!=value['archive_bytes'] or hashlib.sha256(archive.read_bytes()).hexdigest()!=value['archive_sha256']:
        raise ValueError('Closed context archive differs')
    records={row['path']:row for row in value['files']}
    if (not records or len(records)!=len(value['files']) or len({name.casefold() for name in records})!=len(records)
            or type(value.get('raw_bytes')) is not int or value['raw_bytes']!=sum(row['bytes'] for row in records.values())):
        raise ValueError('Ambiguous context membership')
    pins=json_object(authority.raw('container-inputs.json.RAW'))['candidate_files']
    if len(pins)!=12 or not pins.keys()<=records.keys():raise ValueError('Twelve critical native inputs absent')
    for name,pin in pins.items():
        if records[name]['raw_sha256']!=pin['raw_sha256'] or records[name]['bytes']!=pin['bytes']:
            raise ValueError('Closed context critical native input differs')
    docker=None;corpus_raw={}
    with tarfile.open(archive,'r:') as closed:
        if closed.getnames()!=list(records):raise ValueError('Context TAR order or membership differs')
        for member,row in zip(closed.getmembers(),records.values(),strict=True):
            name=authority.canonical_name(member.name);path=PurePosixPath(name)
            lowered=name.casefold()
            if (not member.isfile() or member.uid!=0 or member.gid!=0 or member.mtime!=0
                    or member.mode!=int(row['mode'],8)&0o777 or member.size!=row['bytes']
                    or row['mode'] not in {'100644','100755'} or type(row['bytes']) is not int or member.size>MAX_CONTEXT
                    or lowered.startswith(('docs/','tests/','assets/','ui_desktop/','web/static/uploads/'))
                    or any(part.casefold().startswith('.env') for part in path.parts)
                    or path.suffix.lower() in {'.db','.sqlite','.sqlite3','.pyc','.log'}):
                raise ValueError('Unsafe image context member')
            data=closed.extractfile(member).read()
            if (hashlib.sha256(data).hexdigest()!=row['raw_sha256']
                    or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data,usedforsecurity=False).hexdigest()!=row['git_blob']):
                raise ValueError('Context original blob bytes differ')
            if name=='Dockerfile':docker=data
            if name in CORPUS:corpus_raw[name]=data
    if set(corpus_raw)!=set(CORPUS):raise ValueError('Mandatory password blocklist corpus absent')
    corpus=json_object(corpus_raw[CORPUS[2]]);require_current_corpus(corpus)
    validate_corpus(corpus,corpus_raw[CORPUS[3]],corpus_raw[CORPUS[1]],corpus_raw[CORPUS[0]])
    if proof_required:
        checked=source_proof.verify(directory/'source-objects.zip',revision,records,docker)
        if checked['source_tree']!=value['source_tree']:raise ValueError('Source tree Merkle root differs')
    return value,records

def app_records(records):
    return {name:row for name,row in records.items() if name.startswith(APP_PREFIXES) or name in APP_FILES}

def validate_contract(directory,contract):
    """Verify a closed current context/contract without invoking Git."""
    if contract.get('schema')!='current-image57-input-v1':raise ValueError('Current57 contract schema differs')
    manifest,records=validate_manifest(directory,contract['source'])
    app=app_records(records)
    if (contract['context_sha256']!=manifest['archive_sha256'] or contract['context_bytes']!=manifest['archive_bytes']
            or type(contract['context_files']) is not int or contract['context_files']!=len(records)
            or contract['source_tree']!=manifest['source_tree']
            or contract['app_hashes']!={name:row['raw_sha256'] for name,row in app.items()}
            or contract['app_modes']!={name:row['mode'] for name,row in app.items()}
            or contract.get('native_input_count')!=12 or contract.get('native_merkle_objects')!=21
            or contract.get('required_password_corpus')!=list(CORPUS)):
        raise ValueError('Closed current57 contract/context identity differs')
    with tarfile.open(directory/'source-context.tar','r:') as archive:
        docker=archive.extractfile('Dockerfile').read()
        catalog=json_object(archive.extractfile('runtime-source/container37-contract.json').read())
    checked=source_proof.verify(directory/'source-objects.zip',contract['source'],records,docker)
    if checked!=contract.get('source_proof') or contract['distributions']!=catalog['distributions'] or len(catalog['distributions'])!=57:
        raise ValueError('Closed current57 proof or distribution inventory differs')
    corpus=contract.get('password_corpus_measured',{})
    if (corpus.get('bytes')!=3199968 or corpus.get('unique_digests')!=99999 or corpus.get('payload_sha256')!=CORPUS_SHA256):
        raise ValueError('Closed current57 corpus acknowledgement differs')
    return manifest,records

def prepare(repository,revision,private):
    repository=Path(repository);private=Path(private)
    with git_policy():
        check_source(repository,revision)
        # This ROOT/GIT_DIR transport is finite: original helper functions stay
        # unchanged; their only filesystem reads use explicit Git RAW copies.
        git_dir=Path(git(repository,'rev-parse','--absolute-git-dir').decode().strip())
        authority.private_directory(private,repository)
        if shutil.disk_usage(private).free<2*1024**3+PREPARATION_RESERVE:raise ValueError('Private context disk budget below floor')
        evidence=authority.evidence();acl=evidence['boundary_before_payload'](private)
        thin=private/'source-authority';thin.mkdir(mode=0o700)
        pins=json_object(authority.raw('container-inputs.json.RAW'))
        for name in [*pins['candidate_files'],'requirements_web.lock','tests/ci_web37/container-inputs.json']:
            path=thin/name;path.parent.mkdir(parents=True,exist_ok=True)
            data=source(repository,revision,name)
            if name=='tests/ci_web37/container-inputs.json' and data!=authority.raw('container-inputs.json.RAW'):
                raise ValueError('Current native critical pin authority differs')
            path.write_bytes(data)
        from packaging.requirements import Requirement,InvalidRequirement
        from packaging.utils import canonicalize_name
        from tests.ci_web37 import git_recipe
        proof=git_recipe.load()
        if len(proof.objects)!=21:raise ValueError('Original native Merkle inventory differs')
        namespace=dict(globals(),ROOT=thin,write=evidence['write'],Requirement=Requirement,
            InvalidRequirement=InvalidRequirement,canonicalize_name=canonicalize_name,
            NATIVE_FILES=git_recipe.NATIVE_FILES,load=git_recipe.load,object_id=git_recipe.object_id,RECIPE_SOURCE=git_recipe.NATIVE)
        native_ast=authority.functions(authority.raw('container_inputs.py.RAW'),{'lock_blocks','verify_current_lock','verify'},namespace)
        native=namespace['verify']()
        authority.functions(authority.raw('raw_git.py.RAW'),{'raw_blobs'},namespace)
        context_ast=authority.functions(authority.raw('image_context.py.RAW'),{'copy_inputs','select_inputs','prepare'},namespace)
        with git_policy(git_dir,thin):namespace['prepare'](revision,private)
        manifest,records=validate_manifest(private,revision,proof_required=False)
        source_checked=source_proof.prepare(repository,revision,records,source(repository,revision,'Dockerfile'),private,git)
        validate_manifest(private,revision)
        # Source manifest/hash/version are measured; no guessed line count.
        corpus=json_object(source(repository,revision,CORPUS[2]))
        require_current_corpus(corpus)
        corpus_checked=validate_corpus(corpus,source(repository,revision,CORPUS[3]),source(repository,revision,CORPUS[1]),source(repository,revision,CORPUS[0]))
        (private/'password-corpus-source-manifest.json').write_bytes(json.dumps(corpus,indent=2).encode()+b'\n')
        app={name:row['raw_sha256'] for name,row in app_records(records).items()}
        contract={'schema':'current-image57-input-v1','source':revision,'source_tree':manifest['source_tree'],
            'context_sha256':manifest['archive_sha256'],'context_bytes':manifest['archive_bytes'],
            'source_proof':source_checked,
            'context_files':len(records),'app_hashes':app,'app_modes':{name:records[name]['mode'] for name in app},
            'distributions':json_object(source(repository,revision,'runtime-source/container37-contract.json'))['distributions'],
            'native_input_count':12,'native_merkle_objects':21,'native_source_checks':native,
            'helper_function_AST':{'context':context_ast,'native':native_ast},
            'required_password_corpus':list(CORPUS),'password_corpus_measured':corpus_checked,
            'image_built':False,'runtime_probe_executed':False,'final_candidate_source_pin':False}
        if len(contract['distributions'])!=57:raise ValueError('Current57 catalog differs')
        evidence['write'](private/'runtime-input-contract.json',contract)
        validate_contract(private,contract)
        return contract,acl
