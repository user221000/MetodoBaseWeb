from pathlib import Path
import ast,hashlib,json
R=Path(r'F:/mb-security-google33-conflict-peer-20261019');T=Path(r'C:/Users/Consu/AppData/Local/Temp')
O=R/'docs/implementation/20261018-evolution/evidence/security-followup34-qa18-author-20261019'
O.mkdir();(O/'.gitattributes').write_bytes(b'* -text\n')
original=(R/'tests/test_security_followup34_sql_errors_peer.py').read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest();assert sha(original)=='c3a4aa36cf432a32898c93f4c4fef6a8a0d63f479ff8ac883f48eba9379073ce'
suffix=b'''\n\n@pytest.fixture(autouse=True)\ndef isolated_SQL_error_receipts(tmp_path, monkeypatch):\n    """Keep structural observations in each pytest-owned private test directory."""\n    monkeypatch.setenv('SEC_FOLLOWUP34_RECEIPTS', str(tmp_path))\n'''
maintained=R/'tests/test_followup34_sql_error_classification.py';assert not maintained.exists()
maintained.write_bytes(original+suffix)
assert maintained.read_bytes().removesuffix(suffix)==original
old_tests={n.name:ast.dump(n)for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)and n.name.startswith('test_')}
new_tests={n.name:ast.dump(n)for n in ast.parse(maintained.read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name.startswith('test_')}
assert old_tests==new_tests
(O/'maintained-canary-binding.json').write_bytes((json.dumps({'immutable_RED_commit':'e318ae52df86e0119dc8e4bbc1f793a3bbc7b1ee','original_canary_SHA256':sha(original),
    'maintained_copy_SHA256':sha(maintained.read_bytes()),'all_original_test_functions_AST_exact':True,
    'full_byte_inverse_after_removing_only_CI_private_receipt_fixture':True,'new_business_assertions':False},indent=2)+'\n').encode())
prior=T/'metodobase-sec-followup34-peer-run-own-errors-20261019.py';raw=prior.read_bytes();assert sha(raw)=='cdb1a5049920dbebac11f0e1b3bfd1d1909aeefc17a91081f7cc9af67f783eac'
source=raw.decode();replacements=[
    ("metodobase-sec-followup34-peer-private-20261019", "metodobase-sec-followup34-qa18-author-private-20261019"),
    ("security-followup34-independent-20261019", "security-followup34-qa18-author-20261019"),
    ("target=R/'tests/test_security_followup34_sql_errors_peer.py';assert not target.exists();target.write_bytes(original.read_bytes())", "target=R/'tests/test_security_followup34_sql_errors_peer.py';assert sha(target.read_bytes())=='c3a4aa36cf432a32898c93f4c4fef6a8a0d63f479ff8ac883f48eba9379073ce'"),
    ("'80b9a44adf4daae160673b4d86a58cb06f809071'", "'e318ae52df86e0119dc8e4bbc1f793a3bbc7b1ee'"),
    ("+['tests/'+target.name]", "+['tests/'+target.name,'tests/test_followup34_sql_error_classification.py']"),
]
revised=source
for old,new in replacements:assert revised.count(old)==1;revised=revised.replace(old,new,1)
inverse=revised
for old,new in reversed(replacements):inverse=inverse.replace(new,old,1)
assert inverse==source
executed=T/'metodobase-sec-followup34-qa18-run-executed-20261019.py';executed.write_bytes(revised.encode())
(O/'replay-driver-binding.json').write_bytes((json.dumps({'original_driver_SHA256':sha(raw),'executed_revision_SHA256':sha(revised.encode()),
    'full_inverse_exact':True,'changes':'Only author capture coordinates, immutable RED HEAD, existing original canary integrity instead of copying it, and maintained CI copy in source photo. Same12cases and assertions.'},indent=2)+'\n').encode())
exec(compile(revised,str(executed),'exec'),{'__name__':'__main__'})
