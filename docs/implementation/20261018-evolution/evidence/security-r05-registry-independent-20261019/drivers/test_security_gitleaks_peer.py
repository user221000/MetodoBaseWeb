"""Adversarial proof controls against actual fixed-report checksum examples."""
from pathlib import Path
import copy,hashlib,json,subprocess
import pytest
from tests.security_gitleaks_review import verify,historical
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp')
SOURCE=Path(r'F:/mb-progress-retirement-ui-20261019')

@pytest.fixture(scope='module')
def example():
    report=json.loads((TEMP/'metodobase-retirement-ui-scan-7c_07ul3/secret-scan-full.json').read_bytes())
    data=json.loads((TEMP/'metodobase-gitleaks-fingerprint-triage-20261019/classified.json').read_bytes())
    # The source-fingerprint phase has no actual UTF16 example. Derive an
    # explicitly synthetic UTF16 boundary fixture; never label this as RAW.
    row=copy.deepcopy(data[0]);original=(SOURCE/row['file']).read_bytes()
    decoded=original.decode('utf8');derived=decoded.encode('utf-16')
    row['file']='docs/implementation/20261018-evolution/evidence/synthetic-encoding-case.json'
    row['file_sha256']=hashlib.sha256(derived).hexdigest();row['fingerprint']='synthetic-encoding-test-only'
    expected={k:row[k] for k in ['file','line','rule','fingerprint','file_sha256']}
    transform={'source_encoding':'utf-16','scanner_encoding':'utf-8','scanner_sha256':hashlib.sha256(decoded.encode()).hexdigest()}
    return row,derived,(SOURCE/row['source_path']).read_bytes(),expected,transform

def check(example,row=None,proof=None,raw=None,target=None,transform=None):
    p,b,t,e,x=example
    return verify(row or p,proof or p,b if raw is None else raw,t if target is None else target,e,e['file_sha256'],x if transform is None else transform)

def test_derived_UTF16_fixture_keeps_whole_file_and_line_validation(example):assert check(example)

def test_real_fixed_UTF8_source_checksum_is_verified_separately():
    row=json.loads((TEMP/'metodobase-gitleaks-fingerprint-triage-20261019/classified.json').read_bytes())[0]
    expected={k:row[k] for k in ['file','line','rule','fingerprint','file_sha256']}
    assert verify(row,row,(SOURCE/row['file']).read_bytes(),(SOURCE/row['source_path']).read_bytes(),expected,row['file_sha256'])

@pytest.mark.parametrize('field,value',[('line',True),('line',0),('line',-1),('file','../outside.json'),('file','C:/outside.json'),('file','docs/implementation/20261018-evolution/evidence/other.json'),('file_sha256','0'*64),('rule','other-rule'),('fingerprint','forged')])
def test_forged_finding_metadata_cannot_adopt_checksum_classification(example,field,value):
    row=copy.deepcopy(example[0]);row[field]=value
    assert check(example,row=row) is False

@pytest.mark.parametrize('field,value',[('source_path','../outside.py'),('source_path','web/other.py'),('source_sha256','0'*64),('physical_line_sha256','0'*64)])
def test_substituted_target_path_digest_or_physical_line_hash_is_rejected(example,field,value):
    proof=copy.deepcopy(example[0]);proof[field]=value
    assert check(example,proof=proof) is False

def test_one_raw_byte_change_is_rejected(example):assert check(example,raw=example[1]+b' ') is False
def test_unchanged_metadata_does_not_accept_a_fragment_only(example):assert check(example,raw=example[1][:128]) is False
def test_target_bytes_must_actually_hash_to_claimed_digest(example):assert check(example,target=example[2]+b' ') is False

@pytest.mark.parametrize('change',['encoding','scanner_hash','scanner_encoding'])
def test_encoding_metadata_cannot_hide_changed_scanner_bytes(example,change):
    x=copy.deepcopy(example[4])
    if change=='encoding':x['source_encoding']='utf8'
    elif change=='scanner_hash':x['scanner_sha256']='0'*64
    else:x['scanner_encoding']='utf16'
    assert check(example,transform=x) is False

def test_derived_newline_checksum_is_not_historical_raw_or_an_unbound_oid():
    rows=json.loads((TEMP/'metodobase-gitleaks-historical-fingerprint-triage-20261019/classified.json').read_bytes())
    row=next(r for r in rows if r['derivation']=='DERIVED_GitLF_to_CRLF_checksum_not_historical_RAW')
    blob=subprocess.check_output(['git','--no-replace-objects','cat-file','blob',row['Git_blob_oid']],cwd=SOURCE)
    oid=row['Git_blob_oid'];path=row['public_source_path'];pairs={(oid,path)}
    assert historical(blob,oid,path,pairs,row['sha256'],row['derivation'])
    assert not historical(blob,oid,path,pairs,row['sha256'],'Git_blob_bytes')
    assert not historical(blob,oid,path,pairs,row['sha256'],'execution_RAW_reconstructed')
    assert not historical(blob+b' ',oid,path,pairs,row['sha256'],row['derivation'])
    assert not historical(blob,'0'*40,path,pairs,row['sha256'],row['derivation'])
    assert not historical(blob,oid,'web/other.py',pairs,row['sha256'],row['derivation'])
