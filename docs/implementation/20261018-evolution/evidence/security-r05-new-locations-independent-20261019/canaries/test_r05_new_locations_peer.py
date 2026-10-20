"""Offline candidate evidence controls; installed v1 is never replaced."""
from pathlib import Path
from contextlib import contextmanager
import ast
import copy
import hashlib
import importlib.util
import json
import zipfile

import pytest

R=Path(r'F:/mb-security-r05-classifier-peer-20261019')
A=Path(r'F:/mb-r05-review-classifier-20261019')
T=Path(r'C:/Users/Consu/AppData/Local/Temp')
P=T/'metodobase-sec-r05-new-peer-private-20261019'
O=R/'docs/implementation/20261018-evolution/evidence/security-r05-new-locations-independent-20261019'
B=json.loads((O/'countercanary-input-binding.json').read_bytes())
S=Path(B['snapshot'])
SHA=lambda b:hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('independent_candidate_registry',R/'scripts/reviewed_scan_locations.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
# Isolated module constants point at an anchored private candidate copy only.
# No installed file/global scanner/configuration is changed.
M._REVIEW_DATA_PATH='candidate-reviewed-locations.zip'
M._REVIEW_DATA_DIGEST=B['candidate_digest']
source_hashes={n:v['RAW_SHA256'] for n,v in B['files'].items()}
source_hashes['.gitleaks.toml']=B['configuration_digest']
VALIDATED=M.load_reviewed_locations(S,source_hashes,'8.30.1')
COORDS=B['final15_coordinates']

def registry():
    return M.ReviewedLocations(S,dict(source_hashes),copy.deepcopy(VALIDATED.files))

def item(row):
    return {'StartLine':row['line'],'EndLine':row['line'],'RuleID':row['rule']}

@contextmanager
def changed(path,payload):
    original=path.read_bytes()
    try:
        path.write_bytes(payload)
        yield
    finally:path.write_bytes(original)

def test_all_14516_candidate_pins_replay_in_unchanged_runtime_parser():
    review=registry();count=0
    for name,record in review.files.items():
        for (line,rule),digest in record['lines'].items():
            result=review.classify({'StartLine':line,'EndLine':line,'RuleID':rule,
                'Secret':'ignored-untrusted-input','Match':'ignored-untrusted-input','Line':'ignored-untrusted-input'},name)
            assert result and result['physical_line_sha256']==digest
            count+=1
    assert count==14516 and len(review.files)==155

@pytest.mark.parametrize('index',range(15))
@pytest.mark.parametrize('attack',['neighbor_byte','RAW_hash','neighbor_path','rule','multiline','CR','forged_snapshot_digest'])
def test_each_final15_pin_rejects_changed_identity_or_physical_bytes(index,attack):
    row=COORDS[index];review=registry();finding=item(row);name=row['file'];target=S/name
    original=target.read_bytes()
    assert review.classify(finding,name)
    review=registry()
    if attack=='RAW_hash':
        review.source_hashes[name]='0'*64
        assert review.classify(finding,name) is None
    elif attack=='neighbor_path':assert review.classify(finding,name+'.neighbor') is None
    elif attack=='rule':
        finding['RuleID']='independent-unreviewed-rule'
        assert review.classify(finding,name) is None
    elif attack=='multiline':
        finding['EndLine']+=1
        assert review.classify(finding,name) is None
    else:
        parts=original.split(b'\n')
        if attack=='neighbor_byte':altered=original+b'\n'
        elif attack=='CR':
            part=parts[row['line']-1]
            parts[row['line']-1]=part[:-1] if part.endswith(b'\r') else part+b'\r'
            altered=b'\n'.join(parts)
        else:
            parts[row['line']-1]=b'X'+parts[row['line']-1]
            altered=b'\n'.join(parts)
            # Component control: even a forged scanner-digest input cannot
            # replace the independently pinned physical-line identity.
            review.files[name]['scanner_digest']=SHA(altered)
        assert altered!=original
        with changed(target,altered):assert review.classify(finding,name) is None
        assert target.read_bytes()==original

Q='docs/implementation/20261018-evolution/evidence/qa-mfa31-browser-v2-independent-20261019/'
PRODUCER=(T/'metodobase-mfa31-browser-v2-independent-20261019/server_adapter.py').read_bytes()
RECEIPTS=[(A/(Q+n)).read_bytes() for n in ['before.json','after.json','preflight-frozen.json']]
with zipfile.ZipFile(A/'docs/implementation/20261018-evolution/evidence/root-r05-new-locations-candidate-20261019/candidate-evidence.zip') as archive:
    config_proof=next(r['proof'] for r in json.loads(archive.read('phases/final15/classified.json')) if r['proof']['kind'].startswith('pinned pure'))
RECEIPT_DIGESTS={r['path']:r['digest'] for r in config_proof['producer_source_receipts']}
EXPECTED_RECEIPTS=[RECEIPT_DIGESTS[Q+n] for n in ['before.json','after.json','preflight-frozen.json']]
READY=json.loads((A/(Q+'owned-ready.json')).read_bytes())
CLOSED=json.loads((A/(Q+'resource-closure.json')).read_bytes())
LOG=json.loads((A/(Q+'server.stdout.raw.log')).read_bytes().split(b'\n')[1])

def provenance(raw,receipts,ready=READY,closed=CLOSED,log=LOG):
    """Offline semantic admission proof, distinct from runtime finite pins."""
    try:
        if raw is None or SHA(raw)!=B['producer_source_SHA256'] or len(receipts)!=3:return False
        if [SHA(r) for r in receipts]!=EXPECTED_RECEIPTS:return False
        functions=[n for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.FunctionDef) and n.name=='config_hashes']
        if len(functions)!=1 or SHA(ast.dump(functions[0]).encode())!=B['producer_AST_SHA256']:return False
        if any(json.loads(r)['helpers']['server_adapter.py']!=B['producer_source_SHA256'] for r in receipts):return False
        if ready!=closed['actual_server_ready'] or ready!=log:return False
        values=ready['config_hashes']
        if set(values)!={'SECRET_KEY','MFA_ENCRYPTION_KEY','DATABASE_URL','BASE_URL','GOOGLE_CLIENT_ID','STRIPE_SECRET_KEY','REDIS_URL'}:return False
        return all(isinstance(v,str) and len(v)==64 and set(v)<=set('0123456789abcdef') for v in values.values())
    except (KeyError,TypeError,ValueError,SyntaxError):return False

def test_verified_producer_accepts_equal_optional_setting_digests():
    assert provenance(PRODUCER,RECEIPTS)
    assert len(set(READY['config_hashes'].values()))<7

def test_missing_producer_cannot_admit_any_of_nine_configuration_locations():
    assert len([r for r in COORDS if '/qa-mfa31-browser-v2-independent-' in r['file']])==9
    assert not provenance(None,RECEIPTS)

def test_producer_neighbor_byte_rejects_even_with_identical_function_AST():
    assert not provenance(PRODUCER+b'\n',RECEIPTS)

def test_missing_producer_receipt_rejects():
    assert not provenance(PRODUCER,RECEIPTS[:-1])

def test_changed_producer_receipt_identity_rejects():
    bad=copy.deepcopy(RECEIPTS)
    entry=json.loads(bad[0]);entry['helpers']['server_adapter.py']='0'*64
    bad[0]=json.dumps(entry).encode()
    assert not provenance(PRODUCER,bad)

def test_producer_receipt_neighbor_byte_rejects():
    bad=list(RECEIPTS);bad[0]+=b'\n'
    assert not provenance(PRODUCER,bad)

def test_copied_setting_digest_change_rejects():
    ready=copy.deepcopy(READY);ready['config_hashes']['BASE_URL']='0'*64
    assert not provenance(PRODUCER,RECEIPTS,ready=ready)
