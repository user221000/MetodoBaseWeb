"""Git objects, external attributes and adversarial tar streams, in owned Temp."""
import copy
import io
import os
import stat
import subprocess
import tarfile

import pytest

from tests import run_reviewed_ci28 as runner


def git(repository,*args):
    return subprocess.check_output(['git','--no-replace-objects',*args],cwd=repository)


@pytest.fixture
def history(tmp_path,monkeypatch):
    repository=tmp_path/'repository';repository.mkdir()
    git(repository,'init','--quiet')
    contents={'a.txt':b'Exact first blob\n','notes.txt':b'$Format:%H$\n','scripts/tool.sh':b'#!/bin/sh\nexit 0\n'}
    for name,content in contents.items():
        path=repository/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    git(repository,'-c','core.autocrlf=false','add','--all')
    git(repository,'update-index','--chmod=+x','scripts/tool.sh')
    git(repository,'-c','user.name=Synthetic QA','-c','user.email=qa@example.invalid',
        '-c','commit.gpgsign=false','commit','--quiet','-m','Owned archive fixture')
    git(repository,'config','core.autocrlf','true')
    commit=git(repository,'rev-parse','HEAD').decode().strip()
    monkeypatch.setattr(runner,'REVISION',commit)
    return repository,contents


def metadata(repository):
    paths=[repository/'.git/config',repository/'.git/HEAD',*sorted((repository/'.git/refs').rglob('*'))]
    return {path.relative_to(repository).as_posix():path.read_bytes() for path in paths if path.is_file()}


def test_exact_object_bytes_and_execute_mode_survive_windows_autocrlf_without_metadata_mutation(history,tmp_path):
    repository,contents=history;before=metadata(repository)
    target=tmp_path/'source'
    receipt=runner.materialize(repository,target)
    assert receipt['files']==len(contents) and receipt['pinned_tree_blobs_verified']
    assert receipt['replacement_objects_disabled']
    assert {name:(target/name).read_bytes() for name in contents}==contents
    if os.name!='nt':assert stat.S_IMODE((target/'scripts/tool.sh').stat().st_mode)==0o755
    assert metadata(repository)==before


@pytest.mark.parametrize('attribute',['export-ignore','export-subst'])
def test_external_archive_attributes_cannot_remove_or_rewrite_a_committed_blob(history,tmp_path,attribute):
    repository,_=history
    (repository/'.git/info/attributes').write_text('notes.txt '+attribute+'\n',encoding='utf8')
    before=metadata(repository);target=tmp_path/'rejected'
    with pytest.raises(AssertionError):runner.materialize(repository,target)
    assert target.is_dir() and (target/'a.txt').read_bytes()==b'Exact first blob\n'
    assert metadata(repository)==before


@pytest.mark.parametrize('mutation',[
    'bytes','size','mode','duplicate-file','missing-file','extra-file','extra-directory','duplicate-directory',
])
def test_tar_cannot_change_the_tree_contract_and_keeps_its_failed_partial_tree(history,tmp_path,monkeypatch,mutation):
    repository,contents=history;original=subprocess.check_output
    def altered(command,*args,**kwargs):
        data=original(command,*args,**kwargs)
        if 'archive' not in command:return data
        output=io.BytesIO()
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as source,tarfile.open(fileobj=output,mode='w') as target:
            saved=[]
            for current in source:
                entry=copy.copy(current)
                payload=source.extractfile(current).read() if current.isfile() else None
                saved.append((copy.copy(entry),payload))
                if entry.name=='notes.txt':
                    if mutation=='missing-file':continue
                    if mutation=='bytes':payload=b'X'+payload[1:]
                    if mutation=='size':payload+=b'X';entry.size=len(payload)
                    if mutation=='mode':entry.mode=0o755
                target.addfile(entry,io.BytesIO(payload) if payload is not None else None)
            if mutation.startswith('duplicate-'):
                entry,payload=next(row for row in saved if row[0].isdir()==(mutation=='duplicate-directory'))
                target.addfile(entry,io.BytesIO(payload) if payload is not None else None)
            if mutation in {'extra-file','extra-directory'}:
                entry=tarfile.TarInfo('not-in-tree')
                entry.mode=0o755 if mutation=='extra-directory' else 0o644
                entry.type=tarfile.DIRTYPE if mutation=='extra-directory' else tarfile.REGTYPE
                target.addfile(entry,io.BytesIO(b'') if entry.isfile() else None)
        return output.getvalue()
    monkeypatch.setattr(runner.subprocess,'check_output',altered)
    target=tmp_path/'rejected'
    with pytest.raises(AssertionError):runner.materialize(repository,target)
    assert target.is_dir() and (target/'a.txt').read_bytes()==contents['a.txt']


@pytest.mark.parametrize('mutation',['symlink-object','gitlink','incomplete-listing'])
def test_non_blob_or_incomplete_git_tree_never_becomes_an_accepted_specification(history,tmp_path,monkeypatch,mutation):
    repository,_=history;original=subprocess.check_output
    def altered(command,*args,**kwargs):
        data=original(command,*args,**kwargs)
        if 'ls-tree' not in command:return data
        if mutation=='incomplete-listing':return data[:-1]
        if mutation=='symlink-object':return data.replace(b'100644 blob',b'120000 blob',1)
        return data.replace(b'100644 blob',b'160000 commit',1)
    monkeypatch.setattr(runner.subprocess,'check_output',altered)
    with pytest.raises(AssertionError):runner.materialize(repository,tmp_path/'not-created')
    assert not (tmp_path/'not-created').exists()
