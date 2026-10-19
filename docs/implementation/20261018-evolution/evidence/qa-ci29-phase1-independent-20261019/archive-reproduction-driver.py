"""Independent archive guards and local Git metadata trust canaries; no services."""
import sys
sys.dont_write_bytecode=True
import argparse,hashlib,importlib.util,io,json,os,subprocess,tarfile
from pathlib import Path
from unittest.mock import patch
parser=argparse.ArgumentParser();parser.add_argument('--runner',required=True);parser.add_argument('--label',required=True);parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
root=Path(r'F:/mb-r12-ci29-qa-20261019')
out=Path(r'F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/qa-ci29-phase1-independent-20261019')
temp=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-phase1-independent-20261019')
phase=temp/('archive-'+args.label);phase.mkdir(exist_ok=False)
spec=importlib.util.spec_from_file_location('reviewed_runner',args.runner);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
rows=[];original=subprocess.check_output
for name,member,kind in [('parent','../escape',tarfile.REGTYPE),('absolute','/escape',tarfile.REGTYPE),('backslash','dir\\escape',tarfile.REGTYPE),('drive','C:/escape',tarfile.REGTYPE),('symlink','link',tarfile.SYMTYPE),('hardlink','link',tarfile.LNKTYPE),('fifo','fifo',tarfile.FIFOTYPE)]:
    payload=io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w') as archive:
        entry=tarfile.TarInfo(member);entry.type=kind
        if kind in [tarfile.SYMTYPE,tarfile.LNKTYPE]:entry.linkname='../../escape'
        archive.addfile(entry)
    def fake(command,*a,**kw):
        return payload.getvalue() if command[0]=='git' and 'archive' in command else original(command,*a,**kw)
    target=phase/name
    try:
        with patch.object(module.subprocess,'check_output',fake):module.materialize(root,target)
    except (AssertionError,ValueError,OSError):rejected=True
    else:rejected=False
    rows.append({'case':'unsafe-archive-'+name,'passed':rejected,'owned_files_created':len(list(target.rglob('*'))) if target.exists() else 0})
existing=phase/'existing';existing.mkdir();sentinel=existing/'sentinel';sentinel.write_bytes(b'OWN_UNCHANGED')
try:module.materialize(root,existing)
except FileExistsError:rejected=True
else:rejected=False
rows.append({'case':'existing-destination-never-overwritten','passed':rejected and sentinel.read_bytes()==b'OWN_UNCHANGED'})
# A local clone owns its metadata and new objects; alternates only read source objects.
clone=temp/'owned-history-clone'
if args.prepare:
    subprocess.run(['git','clone','--shared','--no-checkout','--no-hardlinks',str(root),str(clone)],check=True,capture_output=True)
    env=dict(os.environ,GIT_AUTHOR_NAME='Synthetic QA',GIT_AUTHOR_EMAIL='qa@example.invalid',GIT_COMMITTER_NAME='Synthetic QA',GIT_COMMITTER_EMAIL='qa@example.invalid',GIT_INDEX_FILE=str(temp/'owned-index'))
    subprocess.run(['git','read-tree',module.REVISION],cwd=clone,env=env,check=True,capture_output=True)
    stub=b'"""Synthetic QA replacement; historical assertions were NOT executed."""\nprint("QA_REPLACED_HISTORICAL_ASSERTIONS")\n'
    blob=subprocess.check_output(['git','hash-object','-w','--stdin'],cwd=clone,env=env,input=stub).decode().strip()
    subprocess.run(['git','update-index','--add','--cacheinfo','100644,'+blob+',tests/verify_history_landing_ci.py'],cwd=clone,env=env,check=True,capture_output=True)
    tree=subprocess.check_output(['git','write-tree'],cwd=clone,env=env).decode().strip()
    parent=subprocess.check_output(['git','rev-parse',module.REVISION+'^'],cwd=clone,env=env).decode().strip()
    replacement=subprocess.check_output(['git','-c','commit.gpgsign=false','commit-tree',tree,'-p',parent],cwd=clone,env=env,input=b'Synthetic QA replacement commit\n').decode().strip()
    subprocess.run(['git','replace',module.REVISION,replacement],cwd=clone,env=env,check=True,capture_output=True)
    (out/'archive-owned-replacement-setup.json').write_text(json.dumps({'clone':str(clone),'pinned_original':module.REVISION,'replacement':replacement,'stub_sha256':sha(stub),'source_repository_mutated':False},indent=2)+'\n',encoding='utf8')
target=phase/'replaced-source'
try:
    receipt=module.materialize(clone,target)
    actual=(target/'tests/verify_history_landing_ci.py').read_bytes()
    expected=subprocess.check_output(['git','--no-replace-objects','show',module.REVISION+':tests/verify_history_landing_ci.py'],cwd=root)
    protected=actual==expected
    detail={'receipt':receipt,'actual_historical_verifier_sha256':sha(actual),'true_pinned_verifier_sha256':sha(expected),'stub_present':b'QA_REPLACED_HISTORICAL_ASSERTIONS' in actual}
except (AssertionError,subprocess.CalledProcessError,ValueError):protected=True;detail={'rejected':True}
rows.append({'case':'local-replace-ref-cannot-substitute-pinned-historical-assertions','passed':protected,'detail':detail})
# Normal Git user attributes can omit a committed historical assertion source.
attributes=phase/'owned-export-attributes';attributes.write_text('tests/integration_recovery28_restore_review.py export-ignore\n',encoding='utf8')
keys=['GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0'];saved={key:os.environ.get(key) for key in keys}
try:
    os.environ.update(GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.attributesFile',GIT_CONFIG_VALUE_0=str(attributes))
    target=phase/'attributes-source'
    try:
        receipt=module.materialize(root,target);present=(target/'tests/integration_recovery28_restore_review.py').is_file()
        detail={'receipt':receipt,'pinned_restore_fixture_present':present};protected=present
    except (AssertionError,subprocess.CalledProcessError,ValueError):protected=True;detail={'rejected':True}
finally:
    for key,value in saved.items():
        if value is None:os.environ.pop(key,None)
        else:os.environ[key]=value
rows.append({'case':'user-export-attributes-cannot-omit-pinned-restore-assertions','passed':protected,'detail':detail})
report={'runner':args.runner,'runner_sha256':sha(Path(args.runner).read_bytes()),'results':rows,'passed':sum(row['passed'] for row in rows),'total':len(rows),'scope':'Only local archive extraction/Git metadata in owned Temp. No PG/browser/Actions; no original Git metadata changed.'}
with (out/('archive-'+args.label+'-review.json')).open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps({'passed':report['passed'],'total':report['total'],'failed_cases':[row['case'] for row in rows if not row['passed']]}))
