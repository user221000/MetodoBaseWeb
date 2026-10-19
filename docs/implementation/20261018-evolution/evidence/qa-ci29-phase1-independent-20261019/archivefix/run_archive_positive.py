"""Replay immutable ten canaries or execute genuine pinned historical source. No services."""
from support import *
import re
mode=sys.argv[1];assert mode in {'original10','positive4433'}
phase=TEMP/mode;phase.mkdir(exist_ok=False)
before=photo(mode+'-before')
env=os.environ.copy()
for name in list(env):
    key=name.upper()
    if key=='DATABASE_URL' or key.endswith('_DATABASE_URL') or key.startswith(('PG','AWS_','S3_','METODOBASE_TEST_')) or any(word in key for word in ['STRIPE','MERCADOPAGO','RESEND','SMTP','SENTRY','OPENAI_API']):env.pop(name,None)
env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',PYTHONPATH='')
if mode=='original10':
    driver=OUT.parent/'archive-reproduction-driver.py';assert sha(driver.read_bytes())=='02b7ef0643f6a58c1fd0c617523f6940098c4204bf22e41007ba63a9e1d3fbb7'
    clone=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-phase1-independent-20261019/owned-history-clone/.git')
    metadata=lambda:{p.relative_to(clone).as_posix():sha(p.read_bytes()) for p in sorted(clone.rglob('*')) if p.is_file()}
    original=metadata();save('original10-owned-clone-before.json',original)
    command=[str(PYTHON),'-X','utf8','-B',str(driver),'--runner',str(ROOT/'tests/run_reviewed_ci28.py'),'--label','qa-independent98']
else:command=[str(PYTHON),'-X','utf8','-B',str(ROOT/'tests/run_reviewed_ci28.py'),'--output',str(phase/'historical'),'--history-repository',str(ROOT)]
with (phase/'stdout.log').open('xb') as stdout,(phase/'stderr.log').open('xb') as stderr:
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=160)
assert result.returncode==0
if mode=='original10':
    report=OUT.parent/'archive-qa-independent98-review.json';data=json.loads(report.read_bytes())
    assert data['total']==data['passed']==10
    current=metadata();save('original10-owned-clone-after.json',current);assert current==original
    details={'passed':10,'total':10,'exact_original_driver_sha256':sha(driver.read_bytes()),'same_owned_clone_metadata_unchanged':True,'before_accepted_controls':7,'after_accepted_controls':10}
    outputs=[publish(report,'original10-report.json')]
else:
    receipt=json.loads((phase/'historical/receipt.json').read_bytes());assert receipt['exit_code']==0 and receipt['files']==4433 and receipt['pinned_tree_blobs_verified'] is True and receipt['replacement_objects_disabled'] is True and 'no restore/browser/services' in receipt['scope'] and json.loads((phase/'stdout.log').read_bytes())['restore'] is False
    source=Path(receipt['source_directory']);listing=subprocess.check_output(['git','--no-replace-objects','ls-tree','-r','-z','--long','66d9dec0e15dd873038bd248d3883daeeb27d4ca'],cwd=ROOT)
    expected={}
    for record in listing.rstrip(b'\0').split(b'\0'):
        meta,name=record.split(b'\t',1);mode,kind,oid,size=meta.split();assert kind==b'blob'
        path=name.decode();raw=(source/path).read_bytes();size=int(size)
        assert len(raw)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw,usedforsecurity=False).hexdigest()==oid.decode()
        expected[path]=sha(raw)
    assert len(expected)==4433 and {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}==set(expected)
    save('independently-rehashed-pinned-source4433.json',expected)
    details={'exit':0,'pinned_files':4433,'independent_complete_blob_rehash':True,'historical_verifier_executed':True,'restore_executed':False,'source_commit':'66d9dec0e15dd873038bd248d3883daeeb27d4ca'}
    outputs=[publish(path,'positive4433-'+path.relative_to(phase).as_posix().replace('/','-')) for path in sorted(phase.rglob('*')) if path.is_file() and 'source' not in path.relative_to(phase).parts]
after=photo(mode+'-after');assert before==after
outputs += [publish(phase/name,mode+'-'+name) for name in ['stdout.log','stderr.log']] if mode=='original10' else []
save(mode+'-result.json',{'head':HEAD,'results':details,'source_helpers_packages_stable':True,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,'outputs':outputs,'scope':'Owned local Git/archive and historical pure guard. No PG/browser/restore/Actions.'})
print(json.dumps({'mode':mode,'sources':before['source_count'],'helpers':before['helper_count'],'packages':89,**details}))
