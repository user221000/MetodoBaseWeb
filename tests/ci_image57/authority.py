"""Authenticate original RAW helpers before selecting their unchanged functions."""
from pathlib import Path, PurePosixPath
import ast, csv, hashlib, io, json, os, re, stat, subprocess, tempfile, zipfile
from .authority_pins import PINS

FIXTURES=Path(__file__).with_name('fixtures')

def raw(name):
    data=(FIXTURES/name).read_bytes();pin=PINS[name]
    if (len(data)!=pin['bytes'] or hashlib.sha256(data).hexdigest()!=pin['sha256']
            or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data,usedforsecurity=False).hexdigest()!=pin['blob']):
        raise ValueError('Original image57 helper identity differs')
    return data

def functions(data,names,namespace):
    selected=[n for n in ast.parse(data).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    if {n.name for n in selected}!=set(names):raise ValueError('Original image57 function inventory differs')
    exec(compile(ast.Module(body=selected,type_ignores=[]),'authenticated-original-image57-functions','exec'),namespace)
    return {n.name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in selected}

def canonical_name(name):
    path=PurePosixPath(name)
    devices={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(10)),*(f'LPT{i}' for i in range(10))}
    if (not name or not path.parts or name!=path.as_posix() or path.is_absolute() or '..' in path.parts
            or ':' in name or '\\' in name or any(ord(c)<32 or ord(c)==127 for c in name)
            or any(p!=p.rstrip(' .') or p.split('.',1)[0].upper() in devices for p in path.parts)):
        raise ValueError('Noncanonical image57 path')
    return name

def regular_directory(path):
    path=Path(path)
    if not path.is_absolute() or path.resolve(strict=True)!=path.absolute():raise ValueError('Image57 directory alias')
    for item in (path,*path.parents):
        value=item.lstat()
        if (not stat.S_ISDIR(value.st_mode) or item.is_symlink()
                or getattr(value,'st_file_attributes',0)&0x400):raise ValueError('Image57 unsafe directory')
    return path

def regular_file(path):
    path=Path(path)
    regular_directory(path.parent)
    value=path.lstat()
    if not stat.S_ISREG(value.st_mode) or path.is_symlink() or getattr(value,'st_file_attributes',0)&0x400:
        raise ValueError('Image57 unsafe regular file')
    return path

def private_directory(path,repository):
    path=Path(path)
    if not path.is_absolute() or path.exists():raise ValueError('Fresh absolute private root required')
    regular_directory(path.parent)
    namespace=dict(globals(),ROOT=Path(repository))
    functions(raw('private_producer.py.RAW'),{'_assert_windows_acl','_set_windows_private_acl','_verify_private_boundary','_private_evidence'},namespace)
    return namespace['_private_evidence'](path)

def publication():
    namespace=dict(globals())
    data=raw('publication.py.RAW')
    for node in ast.parse(data).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'TOKEN','CSRF','FACTOR'} for t in node.targets):
            exec(compile(ast.Module(body=[node],type_ignores=[]),'original-image57-publication-pattern','exec'),namespace)
    functions(data,{'scan'},namespace)
    return namespace['scan']

def evidence():
    namespace=dict(globals(),scan=publication())
    functions(raw('evidence.py.RAW'),{'write','boundary_before_payload','seal'},namespace)
    return namespace
