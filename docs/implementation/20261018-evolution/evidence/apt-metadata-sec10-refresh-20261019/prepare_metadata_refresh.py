"""Prepare one metadata-pin proposal from authenticated preserved primary inputs. No build."""
from pathlib import Path
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import difflib,hashlib,json,lzma,re,shutil,subprocess
WT=Path(r'F:\mb-container-apt-refresh-sec10-20261019')
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
PRIOR=LAB/'evidence/container-system-libpq-20261019/apt-primary'
MAIN=Path(r'F:\MetodoBaseWeb-execution-20261018')
PUB=MAIN/'docs/implementation/20261018-evolution/evidence/linux-container-libpq-sec09-prepared-20261019'
RUN=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-expat-m2-native-validation-20261019')
CURRENT=RUN/'public-apt-diagnostics'
PROOF=WT/'docs/implementation/20261018-evolution/evidence/apt-metadata-sec10-refresh-20261019'
BASE='7c013f12dd66b68dc15769e185756610eb2ca2e5'
def info(path):return {'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def git(*args):return subprocess.check_output(['git','--no-replace-objects','--no-optional-locks',*args],cwd=WT)
assert git('rev-parse','HEAD').decode().strip()==BASE and git('status','--porcelain')==b''
assert not PROOF.exists()
before_lock=(WT/'requirements-container-apt-metadata.lock').read_bytes()
assert before_lock==git('show',BASE+':requirements-container-apt-metadata.lock')
locks=git('ls-files','-z','--','requirements*.lock').decode().rstrip('\0').split('\0')
protected=[name for name in locks if name!='requirements-container-apt-metadata.lock']+['Dockerfile','runtime-source/expat-sec10/rebuild_pyexpat.py','runtime-source/expat-sec10/source-pins.json','runtime-source/expat-sec10/13c5f63.patch']
protected_before={name:info(WT/name) for name in protected}
diagnostics=json.loads((RUN/'failure-diagnostics-source.json').read_text())
old_signature=json.loads((RUN/'old-index-signature-source.json').read_text())
assert old_signature['gpgv_exit']==0
expected_signers={'4CB50190207B4758A3F73A796ED0E7B82643E131','B8E5F13176D2A7A75220028078DBA3BC47EF2265'}
assert set(old_signature['signers'])==expected_signers
old=(PUB/'apt-primary/updates.InRelease').read_bytes()
new_path=CURRENT/'deb.debian.org_debian_dists_trixie-updates_InRelease'
new=new_path.read_bytes()
old_hash=hashlib.sha256(old).hexdigest();new_hash=hashlib.sha256(new).hexdigest()
assert old_hash=='1ff5b5841ba7a91e3e4c1f43a5a0886d0a5987f1ab03c5fa3a04dbca0c6e7edf'
assert new_hash=='3ea800baec602255b1b450a0434052c05cf9eb72636eaf0b0144e0bd0a181080'
def payload(raw):return raw.decode('utf-8').split('\n\n',1)[1].split('-----BEGIN PGP SIGNATURE-----',1)[0]
def headers(raw):
 return {line.split(': ',1)[0]:line.split(': ',1)[1] for line in payload(raw).splitlines() if ': ' in line and not line.startswith(' ')}
def leaves(raw):
 section=payload(raw).split('SHA256:\n',1)[1].split('\n\n',1)[0]
 return {p:{'sha256':h,'bytes':int(n)} for h,n,p in
         (line.split() for line in section.splitlines() if re.fullmatch(r'\s+[a-f0-9]{64}\s+\d+\s+\S+',line))}
old_heads,new_heads=headers(old),headers(new)
old_leaves,new_leaves=leaves(old),leaves(new)
assert len(old_leaves)==409 and old_leaves==new_leaves
stripped=lambda raw:'\n'.join(line for line in payload(raw).splitlines() if not line.startswith(('Date:','Valid-Until:')))
assert stripped(old)==stripped(new)
now=datetime.now(timezone.utc)
assert parsedate_to_datetime(new_heads['Date'])<=now<parsedate_to_datetime(new_heads['Valid-Until'])
assert parsedate_to_datetime(old_heads['Date'])<=now<parsedate_to_datetime(old_heads['Valid-Until'])
assert new_heads['Codename']=='trixie-updates' and new_heads['Suite']=='stable-updates'
keyring=info(CURRENT/'debian-archive-keyring.gpg')
assert keyring['sha256']==old_signature['keyring_sha256']==diagnostics['keyring_sha256']
assert keyring['sha256']=='506b815cbb32d9b6066b4a2aa524071e071761e7e7f68c3ac74f3061ba852017'
for row in diagnostics['indices']:
 assert row['gpgv_exit']==0 and row['validsig_fingerprints']
 if row['signed_headers']['Codename']=='trixie-updates':
  assert set(row['validsig_fingerprints'])==expected_signers and row['actual_sha256']==new_hash
 else:assert row['matches_pin']
# The complete compressed binary indices are byte-identical authenticated leaves.
indices={};stanzas={}
prior_meta=json.loads((PUB/'apt-primary/metadata.json').read_text())
for name,current_name in (
 ('stable','deb.debian.org_debian_dists_trixie_InRelease'),
 ('updates','deb.debian.org_debian_dists_trixie-updates_InRelease'),
 ('security','security.debian.org_debian-security_dists_trixie-security_InRelease')):
 previous=PRIOR/(name+'.InRelease')
 current=CURRENT/current_name
 if name!='updates':assert previous.read_bytes()==current.read_bytes()
 old_map,new_map=leaves(previous.read_bytes()),leaves(current.read_bytes())
 assert old_map==new_map
 index=PRIOR/(name+'.Packages.xz');assert info(index)==new_map['main/binary-amd64/Packages.xz']
 record=next(row for row in prior_meta['downloads'] if row['file']==name+'.Packages.xz')
 assert info(index)=={k:record[k] for k in ('bytes','sha256')}
 indices[name]={'compressed_index':info(index),'all_signed_sha256_leaves_identical':True,
                'signed_sha256_leaf_count':len(new_map),'package_index_changed':False}
 parsed=[]
 for stanza in lzma.decompress(index.read_bytes()).decode().split('\n\n'):
  fields={}
  for line in stanza.splitlines():
   if line and not line[0].isspace() and ': ' in line:
    k,v=line.split(': ',1);fields[k]=v
  if 'Package' in fields:parsed.append(fields)
 stanzas[name]=parsed
# Verify every selected original compiler/libpq/openssl record against the
# authenticated complete index. Dependency constraints and filenames are retained.
selected=[]
suite_to_name={'trixie':'stable','trixie-updates':'updates','trixie-security':'security'}
keys=('Package','Version','Architecture','Depends','Pre-Depends','Filename','Size','SHA256')
for old_record in prior_meta['selected']:
 fields=old_record['fields'];name=suite_to_name[old_record['suite']]
 found=[row for row in stanzas[name] if row.get('Package')==fields['Package'] and row.get('Version')==fields['Version']]
 assert len(found)==1 and found[0]==fields
 selected.append({'suite':old_record['suite'],**{k:fields[k] for k in keys if k in fields}})
assert any(r['Package']=='libpq5' and r['Version']=='17.11-0+deb13u1' for r in selected)
assert any(r['Package']=='libssl3t64' and r['Version']=='3.5.7-1~deb13u3' for r in selected)
assert any(r['Package']=='gcc' and r['Version']=='4:14.2.0-1' for r in selected)
runtime_expected=json.loads((PUB/'runtime-os-expected.json').read_text())
closure=[]
for old_record in runtime_expected['predicted_new_packages']:
 rows=[row for row in stanzas[old_record['metadata_source']] if row.get('Package')==old_record['package'] and row.get('Version')==old_record['version']]
 assert len(rows)==1;row=rows[0]
 assert row['SHA256']==old_record['sha256'] and int(row['Size'])==old_record['bytes']
 assert row.get('Depends','')==old_record.get('depends','')
 closure.append(old_record)
# Literal one-line metadata pin replacement; no package or Dockerfile changes.
assert before_lock.count(old_hash.encode())==1
after_lock=before_lock.replace(old_hash.encode(),new_hash.encode())
assert before_lock!=after_lock and len(before_lock)==len(after_lock)
PROOF.mkdir(parents=True)
(WT/'requirements-container-apt-metadata.lock').write_bytes(after_lock)
protected_after={name:info(WT/name) for name in protected}
assert protected_before==protected_after
diff=''.join(difflib.unified_diff(before_lock.decode().splitlines(True),after_lock.decode().splitlines(True),fromfile='a/requirements-container-apt-metadata.lock',tofile='b/requirements-container-apt-metadata.lock'))
(PROOF/'lock-one-line.diff').write_text(diff,encoding='utf-8')
(PROOF/'signed-payload.diff').write_text(''.join(difflib.unified_diff(payload(old).splitlines(True),payload(new).splitlines(True),fromfile='old updates signed payload',tofile='current updates signed payload')),encoding='utf-8')
(PROOF/'old-updates.InRelease').write_bytes(old)
(PROOF/'current-updates.InRelease').write_bytes(new)
(PROOF/'debian-archive-keyring.gpg').write_bytes((CURRENT/'debian-archive-keyring.gpg').read_bytes())
(PROOF/'old-signature-source.json').write_bytes((RUN/'old-index-signature-source.json').read_bytes())
(PROOF/'current-signature-source.json').write_text(json.dumps(diagnostics['indices'],indent=2)+'\n',encoding='utf-8')
for ending in ('gpgv.stdout','gpgv.stderr'):
 shutil.copy2(CURRENT/('deb.debian.org_debian_dists_trixie-updates_InRelease.'+ending),PROOF/('current-updates.'+ending))
shutil.copy2(Path(__file__),PROOF/'prepare_metadata_refresh.py')
record={'status':'PREPARED_METADATA_ONLY_REQUIRES_INDEPENDENT_REVIEW','created_utc':now.isoformat(),'source_commit':BASE,
 'reason':'Native target failed closed before compiler stage because signed trixie-updates InRelease was republished.',
 'old_inrelease':{'bytes':len(old),'sha256':old_hash,'headers':old_heads},
 'new_inrelease':{'bytes':len(new),'sha256':new_hash,'headers':new_heads},
 'signatures':{'old_gpgv_exit':0,'new_gpgv_exit':0,'validated_fingerprints':sorted(expected_signers),'keyring':keyring},
 'all_409_signed_updates_sha256_leaves_identical':True,'signed_payload_changes_only':['Date','Valid-Until'],
 'authenticated_complete_indices':indices,'selected_packages_unchanged':selected,'predicted_runtime_closure_unchanged':closure,
 'package_or_dependency_download_change':False,'apt_solver_execution':'not repeated; no install/build in refresh proposal',
 'protected_files_before':protected_before,'protected_files_after':protected_after,
 'metadata_lock_before':{'bytes':len(before_lock),'sha256':hashlib.sha256(before_lock).hexdigest()},
 'metadata_lock_after':{'bytes':len(after_lock),'sha256':hashlib.sha256(after_lock).hexdigest()},
 'no_build_retry':True,'native_elf_or_linkage_validated':False,'runtime54_os71_product_accepted':False,
 'lease':'Owned QEMU idle retained by explicit root instruction; no new service or port.'}
(PROOF/'proposal-source.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
manifest={path.relative_to(PROOF).as_posix():info(path) for path in PROOF.rglob('*') if path.is_file()}
(PROOF/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':record['status'],'proof':str(PROOF),'lock_after':record['metadata_lock_after'],'selected_package_rows':len(selected),'unchanged_runtime_closure_rows':len(closure),'protected_files':len(protected_before),'updates_signed_sha256_leaves':409}))

