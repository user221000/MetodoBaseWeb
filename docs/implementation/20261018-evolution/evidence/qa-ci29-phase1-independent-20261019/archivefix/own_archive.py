"""Independent generic extraction adversaries using a tiny real owned Git repository."""
from support import *
import copy,io,tarfile
from unittest.mock import patch
sys.path.insert(0,str(ROOT))
from tests import run_reviewed_ci28 as runner
before=photo('own-archive-before')
phase=TEMP/'own-archive';phase.mkdir(exist_ok=False);repo=phase/'repository';repo.mkdir()
def owned_git(*args):return subprocess.check_output(['git','--no-replace-objects',*args],cwd=repo,stderr=subprocess.PIPE)
owned_git('init','--quiet')
contents={'a.txt':b'Alpha\n','dir/sub.py':b'print("SYNTHETIC_NEVER_EXECUTED")\n','format.txt':b'$Format:%H$\n'}
for name,raw in contents.items():
    path=repo/name;path.parent.mkdir(exist_ok=True,parents=True);path.write_bytes(raw)
owned_git('-c','core.autocrlf=false','add','--all')
owned_git('-c','core.autocrlf=false','-c','core.hooksPath='+str(phase/'no-hooks'),'-c','commit.gpgsign=false','-c','user.name=Synthetic QA','-c','user.email=qa@example.invalid','commit','--quiet','-m','Independent owned extraction fixture')
revision=owned_git('rev-parse','HEAD').decode().strip();owned_git('config','core.autocrlf','true')
metadata=lambda:{p.relative_to(repo/'.git').as_posix():sha(p.read_bytes()) for p in sorted((repo/'.git').rglob('*')) if p.is_file()}
rows=[];original=subprocess.check_output
with patch.object(runner,'REVISION',revision):
    prior=metadata();target=phase/'positive-CRLF-config'
    receipt=runner.materialize(repo,target)
    assert receipt['files']==3 and receipt['pinned_tree_blobs_verified'] is True and metadata()==prior
    assert all((target/name).read_bytes()==raw for name,raw in contents.items())
    rows.append({'case':'real-Git-blobs-stay-LF-despite-owned-autocrlf-true','passed':True})
    modes=['same-size-first-blob','LF-to-CRLF','directory-mode','PAX-parent-path','Windows-case-name','dot-alias-name','duplicate-first-file','wrong-tree-blob-OID','casefold-tree-alias']
    for mode in modes:
        saved=metadata();captured=[]
        def altered(command,*args,**kwargs):
            raw=original(command,*args,**kwargs)
            if 'ls-tree' in command and mode in ['wrong-tree-blob-OID','casefold-tree-alias']:
                first=raw.split(b'\0',1)[0]
                if mode=='wrong-tree-blob-OID':
                    fields=first.split(b'\t',1)[0].split();return raw.replace(fields[2],b'0'*40,1)
                return raw+first.rsplit(b'\t',1)[0]+b'\tA.TXT\0'
            if 'archive' not in command or mode in ['wrong-tree-blob-OID','casefold-tree-alias']:return raw
            output=io.BytesIO()
            with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as source,tarfile.open(fileobj=output,mode='w') as archive:
                for current in source:
                    entry=copy.copy(current);entry.pax_headers=dict(current.pax_headers)
                    data=source.extractfile(current).read() if current.isfile() else None
                    if entry.name=='a.txt':
                        if mode=='same-size-first-blob':data=b'X'+data[1:]
                        elif mode=='LF-to-CRLF':data=data.replace(b'\n',b'\r\n');entry.size=len(data)
                        elif mode=='PAX-parent-path':entry.pax_headers['path']='../outside-owned'
                        elif mode=='Windows-case-name':entry.name='A.TXT'
                        elif mode=='dot-alias-name':entry.name='./a.txt'
                    if entry.isdir() and mode=='directory-mode':entry.mode=0o700
                    archive.addfile(entry,io.BytesIO(data) if data is not None else None)
                    if entry.name=='a.txt' and mode=='duplicate-first-file':archive.addfile(entry,io.BytesIO(data))
            transformed=output.getvalue();captured.append(transformed);return transformed
        target=phase/mode
        with patch.object(runner.subprocess,'check_output',side_effect=altered):
            try:runner.materialize(repo,target)
            except AssertionError as error:rejected=True;message=str(error)
            else:rejected=False;message=''
        assert rejected and metadata()==saved
        if mode in ['same-size-first-blob','wrong-tree-blob-OID']:assert 'blob bytes differ' in message and not (target/'a.txt').exists()
        elif mode=='LF-to-CRLF':assert 'mode/size differs' in message and not (target/'a.txt').exists()
        elif mode=='directory-mode':assert 'directory mode differs' in message
        elif mode in ['Windows-case-name','duplicate-first-file']:assert 'Unexpected/duplicate historical file' in message
        elif mode=='casefold-tree-alias':assert 'aliased names' in message and not target.exists()
        assert not (phase/'outside-owned').exists()
        if captured:(phase/(mode+'.tar')).write_bytes(captured[0])
        rows.append({'case':mode,'passed':True,'assertion':message,'owned_Git_metadata_unchanged':True,'failed_tree_retained':target.is_dir()})
    (repo/'.git/info/attributes').write_text('format.txt export-subst\n',encoding='utf8');saved=metadata()
    try:runner.materialize(repo,phase/'real-export-subst')
    except AssertionError as error:rejected=True;message=str(error)
    else:rejected=False;message=''
    assert rejected and metadata()==saved and ('mode/size differs' in message or 'blob bytes differ' in message)
    rows.append({'case':'real-user-owned-export-subst-cannot-normalize-blob-authority','passed':True,'assertion':message,'owned_Git_metadata_unchanged':True})
after=photo('own-archive-after');assert before==after
save('own-archive-result.json',{'head':HEAD,'results':rows,'total':len(rows),'passed':sum(row['passed'] for row in rows),'fixture_owned_commit':revision,'source_helpers_packages_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'scope':'Generic extraction contract tested against tiny real owned Git fixture by process-local REVISION substitution; genuine fixed66 binding is exercised separately by immutable original10 and positive4433. No body execution, PG/browser/Actions.'})
print(json.dumps({'passed':len(rows),'total':len(rows),'sources':before['source_count'],'helpers':before['helper_count'],'packages':89}))
