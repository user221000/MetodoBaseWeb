from pathlib import Path
from collections import Counter
import hashlib,importlib.metadata,json,subprocess,sys,zipfile
ROOT=Path(r'F:/mb-security-r05-classifier-peer-20261019');sys.path.insert(0,str(ROOT))
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp');PRIVATE=TEMP/'metodobase-sec-r05-classifier-peer-private-20261019'
SOURCE=Path(r'F:/mb-progress-retirement-ui-20261019')
PREFIX='docs/implementation/20261018-evolution/evidence/security-r05-registry-independent-20261019';OUT=ROOT/PREFIX
OUT.mkdir();(OUT/'.gitattributes').write_bytes(b'* -text\n')
sha=lambda b:hashlib.sha256(b).hexdigest()
save=lambda n,v:(OUT/n).write_bytes((json.dumps(v,indent=2)+'\n').encode())
old=Path(r'F:/mb-security-gitleaks-triage-peer-20261019/tests')
for name in ['security_gitleaks_review.py','test_security_gitleaks_peer.py']:(ROOT/'tests'/name).write_bytes((old/name).read_bytes())
from scripts import reviewed_scan_locations as product
payload=(ROOT/product._REVIEW_DATA_PATH).read_bytes();assert sha(payload)==product._REVIEW_DATA_DIGEST=='813f66c2f414065200aff734bffe96ebce6673bd0f20b46f68821686b55c604e'
ledger_path=Path(r'F:/mb-security-gitleaks-triage-peer-20261019/docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019/finite-reviewed-location-ledger.json')
ledger_raw=ledger_path.read_bytes();assert sha(ledger_raw)=='2b42fdd68d828f9a7d0971326dcb76f650cd83028464b897e546dec2508a3233'
ledger=json.loads(ledger_raw);expected={(r['file'],r['file_sha256'],r['start_line'],r['rule_id'],r['physical_line_sha256']) for r in ledger['locations']}
with zipfile.ZipFile(ROOT/product._REVIEW_DATA_PATH) as z:
    assert z.namelist()==['reviewed-locations.json'];data=json.loads(z.read('reviewed-locations.json'))
actual={(f['path'],f['source_digest'],line['number'],rule,line['digest']) for f in data['files'] for line in f['lines'] for rule in line['rules']}
assert actual==expected and len(actual)==31394
snap=PRIVATE/'baseline-snapshot';snap.mkdir();hashes={}
for record in data['files']:
    name=record['path'];raw=(SOURCE/name).read_bytes();assert sha(raw)==record['source_digest']
    enc=ledger['encodings'][name];content=raw.decode(enc['source_encoding']).encode('utf8')
    assert sha(content)==record['scanner_digest']==enc['scanner_sha256']
    destination=snap/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(content)
    hashes[name]=sha(raw)
config=(ROOT/'.gitleaks.toml').read_bytes();assert sha(config)==data['config_digest']=='fade668c58cf3310a4bde299c32c051cd271bf2cf648634bf45e67d19a372099'
(snap/'.gitleaks.toml').write_bytes(config);hashes['.gitleaks.toml']=sha(config)
(snap/product._REVIEW_DATA_PATH).parent.mkdir(parents=True,exist_ok=True);(snap/product._REVIEW_DATA_PATH).write_bytes(payload)
registry=product.load_reviewed_locations(snap,hashes,'8.30.1');accepted=0
for name,digest,line,rule,linehash in expected:
    result=registry.classify({'StartLine':line,'EndLine':line,'RuleID':rule},name)
    assert result is not None and result['file_sha256']==digest and result['physical_line_sha256']==linehash
    accepted+=1
assert accepted==31394
save('dataset-ledger-binding.json',{'product_commit':'17c9b836776d8ebe51b619ab2b552fafab51f4de','dataset_zip_sha256':sha(payload),'dataset_files':len(data['files']),'ledger_sha256':sha(ledger_raw),'original_occurrences':31564,'unique_pins':len(expected),'exact_pin_set_equal':True,'all_unique_production_classifications_replayed':accepted,'original_source_bytes_from_fixed_UI_snapshot_match':True,'original_source_preimages_required':False,'encoding_bindings_exact':True,'source_hashes':hashes})
save('legacy83-test-copy-binding.json',{name:{'bytes':(ROOT/'tests'/name).stat().st_size,'sha256':sha((ROOT/'tests'/name).read_bytes()),'RAW_equal_previous_peer':(ROOT/'tests'/name).read_bytes()==(old/name).read_bytes()} for name in ['security_gitleaks_review.py','test_security_gitleaks_peer.py']})
photo={'sources':{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for stem in ['scripts','web','api','core','config','tests'] for p in (ROOT/stem).rglob('*.py') if '__pycache__' not in p.parts},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'python':sha(Path(sys.executable).read_bytes()),'base_python':sha(Path(sys._base_executable).read_bytes()),'data_zip':sha(payload)}
assert len(photo['packages'])==89
save('source17-before.json',photo)
print(json.dumps({'dataset_files':len(data['files']),'unique_pins':accepted,'source_Python_files':len(photo['sources']),'packages':89,'legacy_tests_RAW_unchanged':True}))
