from pathlib import Path
import ast,hashlib,json,subprocess
ROOT=Path(r'F:/mb-security-retirement-cleanup-peer-20261019')
OLD=Path(r'F:/mb-security-retirement-peer-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-retirement-owned-cleanup-independent-20261019'
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-retirement-cleanup-peer-private-20261019')
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git',*a],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()=='2273616eb218adfdd30680e111da50a4599a8c53'
assert not git('status','--porcelain','--untracked-files=no')
proof=ROOT/'docs/implementation/20261018-evolution/evidence/root-retirement32-owned-cleanup-20261019'
assert sha((proof/'source.json').read_bytes())=='7df1d371ee033eb988d8a8e35cd9ef7204e20438995a55952a841c21ac3e3f62'
assert sha((proof/'manifest.json').read_bytes())=='44df142f8dd1524aeb4d4b4db96841d2242737526684c732e960a3feeebabb37'
manifest=json.loads((proof/'manifest.json').read_bytes())
for name,item in manifest.items():
    blob=(proof/name).read_bytes();assert len(blob)==item['bytes'] and sha(blob)==item['sha256']
source=json.loads((proof/'source.json').read_bytes())
for field in ['product','maintained_test']:
    for name,expected in source[field].items():assert sha(git('show','HEAD:'+name))==expected and sha((ROOT/name).read_bytes())==expected
assert git('show','219f89a5ee0196061fea5b67e36ae07daf7f4316:web/routes/progress_retirement.py')==(proof/'route-before.GitLF.py').read_bytes()
OUT.mkdir();(OUT/'.gitattributes').write_bytes(b'* -text\n')
oldproof=OLD/'docs/implementation/20261018-evolution/evidence/security-progress-retirement-independent-20261019'
assert sha((oldproof/'manifest.json').read_bytes())=='fe37709f7e1a81aff1d89e84505050fcd9b023401a0d86e17d6fc14c7d0d8b7a'
oldmanifest=json.loads((oldproof/'manifest.json').read_bytes())
for name,item in oldmanifest.items():
    blob=(oldproof/name).read_bytes();assert len(blob)==item['bytes'] and sha(blob)==item['sha256']
copies={'independent-faults.py':'test_security_retirement_peer.py','independent-lineage.py':'test_security_retirement_lineage.py','independent-postgres.py':'integration_security_retirement_peer.py'}
for old,new in copies.items():
    blob=(oldproof/old).read_bytes();ast.parse(blob);(ROOT/'tests'/new).write_bytes(blob);(OUT/old).write_bytes(blob)
assert (ROOT/'tests/test_security_retirement_peer.py').read_bytes()==(ROOT/'tests/test_progress_retirement_cleanup.py').read_bytes()
for name in ['test_security_retirement_invalidation.py','integration_security_retirement_invalidation.py']:
    blob=(ROOT/'tests'/name).read_bytes();ast.parse(blob);(OUT/name).write_bytes(blob)
lease=(oldproof/'independent-owned.py').read_text(encoding='utf8').replace('metodobase-sec-retirement-peer-private-20261019','metodobase-sec-retirement-cleanup-peer-private-20261019').replace('metodobase_test_secretirement_','metodobase_test_seccleanup_')
(ROOT/'tests/security_retirement_owned.py').write_text(lease,encoding='utf8');(OUT/'independent-owned.py').write_bytes((ROOT/'tests/security_retirement_owned.py').read_bytes())
runner=(oldproof/'runner.py').read_text(encoding='utf8').replace('metodobase-sec-retirement-peer-private-20261019','metodobase-sec-retirement-cleanup-peer-private-20261019').replace('F:/mb-security-retirement-peer-20261019','F:/mb-security-retirement-cleanup-peer-20261019').replace('security-progress-retirement-independent-20261019','security-retirement-owned-cleanup-independent-20261019').replace('metodobase-sec-retirement-peer-child-20261019.py','metodobase-sec-retirement-cleanup-peer-child-20261019.py')
runner=runner.replace("SEC_RETIREMENT_LINEAGE_RECEIPT=str(raw/'lineage.json'))","SEC_RETIREMENT_LINEAGE_RECEIPT=str(raw/'lineage.json'),SEC_RETIREMENT_INVALIDATION_RECEIPTS=str(raw/'observations'))\n(raw/'observations').mkdir()")
runner=runner.replace("if (raw/'lineage.json').exists():dump('lineage.json',json.loads((raw/'lineage.json').read_bytes()))","if (raw/'lineage.json').exists():dump('lineage.json',json.loads((raw/'lineage.json').read_bytes()))\ndump('invalidation-observations.json',{p.stem:json.loads(p.read_bytes()) for p in sorted((raw/'observations').glob('*.json'))})")
child=(oldproof/'child.py').read_text(encoding='utf8')
for text,name in [(runner,'runner'),(child,'child')]:
    ast.parse(text);target=Path(__file__).with_name('metodobase-sec-retirement-cleanup-peer-'+name+'-20261019.py');target.write_text(text,encoding='utf8');(OUT/(name+'.py')).write_bytes(target.read_bytes())
receipt=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-retirement32-cleanup-commit-receipt.json').read_bytes()
assert json.loads(receipt)['head']=='2273616eb218adfdd30680e111da50a4599a8c53'
(OUT/'author-commit-erratum.json').write_bytes(receipt)
(OUT/'author-authentication.json').write_text(json.dumps({'source_sha256':sha((proof/'source.json').read_bytes()),'manifest_sha256':sha((proof/'manifest.json').read_bytes()),'proof_files_verified':len(manifest),'previous_peer_manifest_sha256':sha((oldproof/'manifest.json').read_bytes()),'previous_peer_files_verified':len(oldmanifest),'original_faults_RAW_sha256':sha((ROOT/'tests/test_security_retirement_peer.py').read_bytes()),'maintained_duplicate_excluded_from_explicit_replay':True,'worktree_checkout':'core.autocrlf=false; product and maintained test RAW equal Git LF','inverse_route_exact_to_composition_parent':True},indent=2)+'\n',encoding='utf8')
print(json.dumps({'author_files':len(manifest),'previous_peer_files':len(oldmanifest),'prepared':'same canaries and separate invalidation-failure observations'}))
