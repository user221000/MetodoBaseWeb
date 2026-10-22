"""Finite original commit/tree proof; context blobs are verified from the TAR.

Only ``prepare`` invokes Git. ``verify`` authenticates the explicit commit and
the complete Docker COPY membership without a repository or Git executable.
"""
from pathlib import Path
import hashlib
import io
import re
import shlex
import zipfile
from . import authority

OID=re.compile(r'[0-9a-f]{40}')
MAX_OBJECT=2*1024**2
MAX_PROOF=16*1024**2
MAX_OBJECTS=2048

def frame(kind,payload):
    return kind.encode('ascii')+b' '+str(len(payload)).encode('ascii')+b'\0'+payload

def object_id(kind,payload):
    return hashlib.sha1(frame(kind,payload),usedforsecurity=False).hexdigest()

def entries(payload):
    result={};position=0
    while position<len(payload):
        end=payload.find(b'\0',position)
        if end<0 or end+21>len(payload):raise ValueError('Current source tree frame truncated')
        header=payload[position:end];mode,space,name=header.partition(b' ')
        if not space or mode not in {b'40000',b'100644',b'100755',b'120000',b'160000'}:
            raise ValueError('Current source tree mode differs')
        text=name.decode('utf8')
        if '/' in text or authority.canonical_name(text)!=text or text in result:
            raise ValueError('Current source tree component differs')
        result[text]=(mode.decode('ascii'),payload[end+1:end+21].hex())
        position=end+21
    return result

class Proof:
    def __init__(self,source,getter):
        if OID.fullmatch(source) is None:raise ValueError('Full source Git commit required')
        self.source=source;self.getter=getter;self.used=set()
        payload=self.get(source,'commit')
        first=payload.split(b'\n',1)[0]
        if not first.startswith(b'tree ') or OID.fullmatch(first[5:].decode('ascii')) is None:
            raise ValueError('Original source commit root differs')
        self.root=first[5:].decode('ascii')

    def get(self,oid,kind):
        payload=self.getter(oid,kind)
        if len(payload)>MAX_OBJECT or object_id(kind,payload)!=oid:
            raise ValueError('Current source Git object identity differs')
        self.used.add(oid)
        if len(self.used)>MAX_OBJECTS:raise ValueError('Current source proof inventory exceeds bound')
        return payload

    def resolve(self,name):
        authority.canonical_name(name)
        parts=name.rstrip('/').split('/');oid=self.root
        for index,part in enumerate(parts):
            row=entries(self.get(oid,'tree')).get(part)
            if row is None:raise ValueError('Required Docker source absent from original tree')
            mode,oid=row
            if index<len(parts)-1 and mode!='40000':raise ValueError('Source path parent is not original tree')
        return mode,oid

    def selected(self,sources):
        result={}
        def visit(name,mode,oid):
            if mode=='40000':
                for child,(child_mode,child_oid) in entries(self.get(oid,'tree')).items():
                    visit(name+'/'+child,child_mode,child_oid)
            elif mode in {'100644','100755'}:
                if name in result and result[name]!=(mode,oid):raise ValueError('Ambiguous COPY source')
                result[name]=(mode,oid)
            else:raise ValueError('Current COPY source is a symlink or submodule')
        for source in sorted(sources):
            normalized=source.rstrip('/')
            visit(normalized,*self.resolve(normalized))
        if len({name.casefold() for name in result})!=len(result):raise ValueError('Casefold source aliases')
        return result

def copy_sources(docker):
    namespace={'shlex':shlex}
    authority.functions(authority.raw('image_context.py.RAW'),{'copy_inputs'},namespace)
    return namespace['copy_inputs'](docker)

def checked_selection(proof,records,docker):
    expected=proof.selected(copy_sources(docker))
    actual={name:(row['mode'],row['git_blob']) for name,row in records.items()}
    if actual!=expected:raise ValueError('Complete original COPY Merkle membership differs')
    if object_id('blob',docker)!=expected['Dockerfile'][1]:raise ValueError('Docker COPY authority differs')
    return expected

def prepare(repository,source,records,docker,directory,git):
    objects={}
    def get(oid,kind):
        if oid in objects:
            saved_kind,payload=objects[oid]
            if saved_kind!=kind:raise ValueError('Conflicting source object kind')
            return payload
        payload=git(repository,'cat-file',kind,oid)
        objects[oid]=(kind,payload)
        if sum(len(frame(k,v)) for k,v in objects.values())>MAX_PROOF:
            raise ValueError('Current source proof exceeds byte bound')
        return payload
    proof=Proof(source,get);checked_selection(proof,records,docker)
    path=directory/'source-objects.zip'
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as output:
        for oid,(kind,payload) in sorted(objects.items()):
            item=zipfile.ZipInfo('objects/'+oid,date_time=(1980,1,1,0,0,0))
            item.external_attr=0o100600<<16
            output.writestr(item,frame(kind,payload))
    return verify(path,source,records,docker)

def verify(path,source,records,docker):
    raw=authority.regular_file(path).read_bytes()
    if len(raw)>MAX_PROOF:raise ValueError('Closed source proof exceeds byte bound')
    objects={}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as closed:
            members=closed.infolist()
            if len(members)>MAX_OBJECTS or sum(row.file_size for row in members)>MAX_PROOF:
                raise ValueError('Closed source proof inventory exceeds bound')
            for member in members:
                oid=member.filename.removeprefix('objects/')
                if (member.filename!='objects/'+oid or OID.fullmatch(oid) is None or oid in objects
                        or member.flag_bits&1 or member.compress_type!=zipfile.ZIP_STORED
                        or member.file_size>MAX_OBJECT+64 or member.is_dir()):
                    raise ValueError('Closed source proof member differs')
                value=closed.read(member);header,separator,payload=value.partition(b'\0')
                kind,space,size=header.partition(b' ')
                if (not separator or not space or kind not in {b'commit',b'tree'}
                        or size!=str(len(payload)).encode('ascii')):
                    raise ValueError('Closed source proof object frame differs')
                objects[oid]=(kind.decode('ascii'),payload)
    except (zipfile.BadZipFile,RuntimeError) as error:
        raise ValueError('Closed source proof ZIP differs') from error
    def get(oid,kind):
        saved=objects.get(oid)
        if saved is None or saved[0]!=kind:raise ValueError('Required original commit/tree is absent')
        return saved[1]
    proof=Proof(source,get);checked_selection(proof,records,docker)
    if proof.used!=set(objects):raise ValueError('Undeclared source proof objects')
    return {'source_commit':source,'source_tree':proof.root,'objects':len(objects),
            'sha256':hashlib.sha256(raw).hexdigest(),'consumer_Git_required':False}
