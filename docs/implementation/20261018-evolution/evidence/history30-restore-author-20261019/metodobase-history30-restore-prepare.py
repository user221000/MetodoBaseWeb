"""Create a separate revision30 restore test without editing revision29."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

ROOT = Path('F:/mb-history30-restore-20261019')
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/history30-restore-author-20261019'
OUT.mkdir(exist_ok=False)
TEMP = Path(tempfile.mkdtemp(prefix='metodobase-history30-restore-author-'))
original_path = ROOT / 'tests/integration_client_link_restore.py'
raw = original_path.read_bytes()
original = raw.decode('utf8').replace('\r\n', '\n')
new = original
replacements = [
    ('"""Explicit29 restore derived separately; accepted26/27/28 fixtures stay immutable.\n\nPreserves the complete27 test body/assertions and reuses its unchanged diary\nservice/HTTP helpers; recovery additions are isolated in a separate helper.\n"""',
     '"""Explicit30 restore; accepted26/27/28/29 fixtures and assertions stay immutable.\n\nCopies the complete revision29 populated restore and its unchanged helpers.\nAdds exact physical index preservation and a post-restore ASC-only drift canary.\nNo business RPO/RTO, production recovery or query latency is accepted here.\n"""'),
    ('test_revision29_restore_preserves_member_links_and_all_revision26_27_28_contracts',
     'test_revision30_restore_preserves_history_index_and_all_revision26_27_28_29_contracts'),
    ('"""Explicit29; preserve26/27/28 criteria and add populated recipient capabilities."""',
     '"""Explicit30; preserve all26/27/28/29 criteria and physical index ordering."""'),
    ('client-link29', 'history-index30'),
    ('20261019_client_account_links', '20261019_personal_history_index'),
    ('synthetic PostgreSQL explicit revision29; preserved26/27/28 and explicit member relationships/publications',
     'synthetic PostgreSQL explicit revision30; preserved26/27/28/29 and physical history index'),
]
assert original.count('20261019_client_account_links') == 3
for old, replacement in replacements:
    assert old in new
    new = new.replace(old, replacement)
insertions = []
def add(anchor, block):
    global new
    assert new.count(anchor) == 1, anchor
    assert block not in new
    new = new.replace(anchor, anchor + block)
    insertions.append({'anchor': anchor, 'block': block})

add('    from web.database.alembic.member_link_security_v1 import member_link_security_signature\n',
    '    # BEGIN HISTORY30 INDEX IMPORTS\n'
    '    from web.database.alembic.history_index_contract_v1 import (\n'
    '        INDEX_NAME, create_history_index, expected_history_index, history_index_signature,\n'
    '    )\n'
    '    # END HISTORY30 INDEX IMPORTS\n')
add('            original_member_security = member_link_security_signature(connection)\n',
    '            # BEGIN HISTORY30 SOURCE INDEX\n'
    '            original_history_index = history_index_signature(connection)\n'
    '            assert original_history_index == expected_history_index("postgresql")\n'
    '            # END HISTORY30 SOURCE INDEX\n')
add('            restored_member_security = member_link_security_signature(connection)\n',
    '            # BEGIN HISTORY30 RESTORED INDEX\n'
    '            restored_history_index = history_index_signature(connection)\n'
    '            assert restored_history_index == expected_history_index("postgresql")\n'
    '            assert restored_history_index == original_history_index\n'
    '            # END HISTORY30 RESTORED INDEX\n')
add('        verify_runtime_schema(target, expected_revision="20261019_personal_history_index")\n',
    '        # BEGIN HISTORY30 ASC-ONLY RESTORED DRIFT\n'
    '        # Change only the timestamp sort direction; v1 deliberately omits it.\n'
    '        restored_revision = original_rows["alembic_version"][0]["version_num"]\n'
    '        with target.begin() as connection:\n'
    '            connection.exec_driver_sql("DROP INDEX " + INDEX_NAME)\n'
    '            connection.exec_driver_sql(\n'
    '                "CREATE INDEX ix_planes_gym_cliente_history ON planes_generados "\n'
    '                "(gym_id, id_cliente, fecha_generacion ASC NULLS LAST, id DESC NULLS LAST) "\n'
    '                "WHERE deleted_at IS NULL"\n'
    '            )\n'
    '            wrong_history_index = history_index_signature(connection)\n'
    '            assert wrong_history_index == {**original_history_index, "indoption": [0, 0, 0, 1]}\n'
    '            assert schema_signature(connection) == restored_signature == original_signature\n'
    '            assert tenant_security_signature(connection) == original_security\n'
    '            assert member_link_security_signature(connection) == original_member_security\n'
    '        assert snapshot(target) == original_rows\n'
    '        with pytest.raises(RuntimeError, match="history ordering"):\n'
    '            verify_runtime_schema(target, expected_revision=restored_revision)\n'
    '        with target.begin() as connection:\n'
    '            connection.exec_driver_sql("DROP INDEX " + INDEX_NAME)\n'
    '            create_history_index(connection)\n'
    '            assert history_index_signature(connection) == restored_history_index == original_history_index\n'
    '            assert schema_signature(connection) == restored_signature == original_signature\n'
    '            assert tenant_security_signature(connection) == original_security\n'
    '            assert member_link_security_signature(connection) == original_member_security\n'
    '        verify_runtime_schema(target, expected_revision=restored_revision)\n'
    '        assert snapshot(target) == original_rows\n'
    '        # END HISTORY30 ASC-ONLY RESTORED DRIFT\n')
add('            "restored_member_links": links_proof,\n',
    '            # BEGIN HISTORY30 MEASUREMENT\n'
    '            "source_history_index": original_history_index,\n'
    '            "restored_history_index": restored_history_index,\n'
    '            "wrong_asc_history_index": wrong_history_index,\n'
    '            "asc_only_drift_rejected_with_unchanged_v1_schema_and_rows": True,\n'
    '            "correct_index_recreated_and_runtime_rows_security_reverified": True,\n'
    '            # END HISTORY30 MEASUREMENT\n')
destination = ROOT / 'tests/integration_personal_history_index_restore.py'
with destination.open('xb') as stream:
    stream.write(new.encode('utf8'))
inverse = new
for entry in reversed(insertions):
    assert inverse.count(entry['block']) == 1
    inverse = inverse.replace(entry['block'], '')
for old, replacement in reversed(replacements):
    assert replacement in inverse
    inverse = inverse.replace(replacement, old)
assert inverse == original
assert ast.dump(ast.parse(inverse), include_attributes=False) == ast.dump(ast.parse(original), include_attributes=False)
assert original_path.read_bytes() == raw
sha = lambda data: hashlib.sha256(data).hexdigest()
preserve = [
    'tests/integration_client_link_restore.py', 'tests/client_link_restore_helpers.py',
    'tests/integration_backup_restore_postgres.py', 'tests/integration_diary_restore_review.py',
    'tests/recovery28_restore_helpers.py', 'scripts/backup_restore.py',
    'web/database/alembic/history_index_contract_v1.py', 'web/database/schema_control.py',
]
with zipfile.ZipFile(OUT / 'before29-exact.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
    for name in preserve:
        archive.writestr(name, (ROOT / name).read_bytes())
proof = {
    'base': 'ea66afbfe323cd5ac86e24705e2534b54c7bbe13',
    'original_sha256_raw': sha(raw), 'original_sha256_git_lf': sha(original.encode()),
    'new_sha256_raw': sha(destination.read_bytes()),
    'historical_assertions': sum(isinstance(node, ast.Assert) for node in ast.walk(ast.parse(original))),
    'new_assertions': sum(isinstance(node, ast.Assert) for node in ast.walk(ast.parse(new))),
    'inverse_text_exact_after_only_explicit_doc_name_revision_and_addition_reversal': inverse == original,
    'inverse_ast_exact_including_every_historical_assertion': True,
    'revision_literal_replacements': 3,
    'replacements': replacements, 'insertions': insertions,
    'historical_files_sha256_raw': {name: sha((ROOT / name).read_bytes()) for name in preserve},
}
(OUT / 'criteria-preservation.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf8')
(TEMP / 'location.json').write_text(json.dumps({'temp':str(TEMP),'evidence':str(OUT)},indent=2)+'\n', encoding='utf8')
print(json.dumps({'temp':str(TEMP),'evidence':str(OUT),'original_sha256':sha(raw),'new_sha256':sha(destination.read_bytes()),'original_assertions':proof['historical_assertions'],'new_assertions':proof['new_assertions']}))
