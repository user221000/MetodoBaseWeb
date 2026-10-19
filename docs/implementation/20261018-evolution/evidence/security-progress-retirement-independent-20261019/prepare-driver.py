from pathlib import Path
import ast,hashlib,json,subprocess
ROOT=Path(r'F:/mb-security-retirement-peer-20261019')
BASE=Path(r'F:/mb-security-retirement-baseline-20261019')
AUTHOR=Path(r'F:/mb-progress32-retirement-20261019')
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-retirement-peer-private-20261019')
REL='docs/implementation/20261018-evolution/evidence/security-progress-retirement-independent-20261019'
OUT=ROOT/REL;OUT.mkdir();(OUT/'.gitattributes').write_bytes(b'* -text\n')
proof=AUTHOR/'docs/implementation/20261018-evolution/evidence/backend-progress32-retirement-20261019'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha((proof/'manifest.json').read_bytes())=='e89a6655d54bb3abd539884932ffb49dbbfaf9374d8fad9bb2e918cd622735eb'
assert sha((proof/'source.json').read_bytes())=='cbdc9bd6a68020d0f7a709b08355bec7e0fe92b31599f4074ef5348e18f6cedf'
manifest=json.loads((proof/'manifest.json').read_bytes())
for name,item in manifest['files'].items():
    blob=(proof/name).read_bytes();assert len(blob)==item['bytes'] and sha(blob)==item['sha256'],name
source=json.loads((proof/'source.json').read_bytes())
for name,item in source['sources'].items():
    blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
    assert sha(blob)==item['GitLF_sha256'],name
assert sha((proof/'wire-v1.md').read_bytes())=='5b6de9c0ecbb9bdf070a1ef6831d5f22f2ac11bddf32c54f3787b99d315bc706'
(OUT/'author-authentication.json').write_text(json.dumps({'commit':'fcfb55e5849e0e20b568be8729dcc1b8c6b1762e','proof_files_verified':len(manifest['files']),'GitLF_sources_verified':len(source['sources']),'manifest':sha((proof/'manifest.json').read_bytes()),'source':sha((proof/'source.json').read_bytes()),'wire':sha((proof/'wire-v1.md').read_bytes())},indent=2)+'\n',encoding='utf8')
lease=Path(r'F:/mb-security-progress32-peer-20261019/tests/security_progress32_owned.py').read_text(encoding='utf8')
lease=lease.replace('metodobase-sec32-peer-private-v3-20261019','metodobase-sec-retirement-peer-private-20261019').replace('metodobase_test_secprogress_','metodobase_test_secretirement_')
(ROOT/'tests/security_retirement_owned.py').write_text(lease,encoding='utf8')
(OUT/'independent-owned.py').write_bytes((ROOT/'tests/security_retirement_owned.py').read_bytes())
old=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec32-parent-boundary-test-20261019.py').read_text(encoding='utf8')
old=old.replace('from tests.integration_progress32_postgres import progress_db, progress_http','from tests.test_personal_progress_http import progress_db, progress_http')
old=old.replace('test_supported_team_member_parent_shutdown_boundary','test_supported_invited_member_can_retire_without_general_login')
old=old[:old.index('    metadata=client.get(own_path,headers=member_headers)')]+'''    assert client.get('/api/auth/me',headers=member_headers).status_code==401
    primary={'method':'password','email':member_email,'password':password}
    metadata=client.post('/api/auth/progress-retirement/metadata',json={'primary':primary})
    withdrawal=client.post('/api/auth/progress-retirement/withdraw',json={'primary':primary,'link_id':link,'expected_consent_id':consent['id'],'expected_version':1})
    receipt={'lineage':'real team invite, public accept, real password login, explicit grant','factory':c['factory'],
        'parent_off':'administrative SQL stimulus, actor remains active','general_login_after_parent_off':401,
        'metadata_http':metadata.status_code,'withdraw_http':withdrawal.status_code,
        'no_access_or_refresh_keys':all(k not in metadata.json() and k not in withdrawal.json() for k in ['token','access_token','refresh_token','challenge'])}
    target=Path(os.environ['SEC_RETIREMENT_LINEAGE_RECEIPT'])
    with target.open('x',encoding='utf8') as output:json.dump(receipt,output,indent=2);output.write('\\n')
    assert metadata.status_code==200 and withdrawal.status_code==200
    assert metadata.json()['items'][0]['link_id']==link
    assert withdrawal.json()['consent']['event']=='withdraw'
    assert receipt['no_access_or_refresh_keys']
    with Session(c['admin']) as db:
        assert [row.event for row in db.scalars(select(ProgressConsent).where(ProgressConsent.link_id==link).order_by(ProgressConsent.version))]==['grant','withdraw']
'''
old=old.replace('"""Diagnostic only: supported team creation, prior explicit grant, then administrative parent shutdown.\n\nThis records the existing authentication boundary. A401 is not a bypass failure\nor an independent approval of a new purpose-limited retirement authentication.\n"""','"""Independent supported invite lineage; same expected retirement contract before/after."""')
ast.parse(old)
for root in (ROOT,BASE):(root/'tests/test_security_retirement_lineage.py').write_text(old,encoding='utf8')
(OUT/'independent-lineage.py').write_bytes((ROOT/'tests/test_security_retirement_lineage.py').read_bytes())
print(json.dumps({'proofs':len(manifest['files']),'sources':len(source['sources']),'prepared':'lease and same lineage canary'}))
