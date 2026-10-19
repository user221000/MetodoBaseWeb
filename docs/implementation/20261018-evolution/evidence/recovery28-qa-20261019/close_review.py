"""Close independent QA evidence; never modifies product or historical fixtures."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(r'F:\MetodoBaseWeb-recovery-compose-20261019')
OUT = Path(__file__).resolve().parent
BASE = '5c9e097'
FINAL = '453cb7e1a7de76ce991a17980c7a0921ff04c495'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(name, data):
    with (OUT / name).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def frozen(path):
    return subprocess.run(['git', 'show', BASE + ':' + path], cwd=ROOT,
                          capture_output=True, check=True).stdout.decode('utf8')


def main_function(text, prefix):
    return next(node for node in ast.parse(text).body
                if isinstance(node, ast.FunctionDef) and node.name.startswith(prefix))


def dump(node):
    return ast.dump(node, include_attributes=False)


class RevisionOnly(ast.NodeTransformer):
    def visit_Constant(self, node):
        if node.value == '20261019_personal_diary':
            return ast.copy_location(ast.Constant('20261019_account_recovery'), node)
        return node


historical_path = 'tests/integration_diary_restore_review.py'
historical = (ROOT / historical_path).read_text(encoding='utf8')
assert historical.replace('\r\n', '\n') == frozen(historical_path).replace('\r\n', '\n')
old = main_function(historical, 'test_revision27')
new_path = ROOT / 'tests/integration_recovery28_restore_review.py'
new = main_function(new_path.read_text(encoding='utf8'), 'test_revision28')
old_asserts = [dump(RevisionOnly().visit(copy.deepcopy(node))) for node in ast.walk(old) if isinstance(node, ast.Assert)]
new_asserts = [dump(node) for node in ast.walk(new) if isinstance(node, ast.Assert)]
assert len(old_asserts) == len(new_asserts) == 40 and old_asserts == new_asserts
functions = {node.name: node for node in ast.parse(new_path.read_text(encoding='utf8')).body
             if isinstance(node, ast.FunctionDef)}
assert '_populate_diary27' not in functions and '_verify_restored_diary27' not in functions

final_photo = json.loads((OUT / 'restore-453cb7-final/before.json').read_text())
assert final_photo['head'] == FINAL
own_paths = ['tests/test_recovery28_review.py', 'tests/integration_recovery28_restore_review.py',
             'tests/recovery28_restore_helpers.py']
own_sha = {path: sha(ROOT / path) for path in own_paths}
assert all(final_photo['sources'][path] == value for path, value in own_sha.items())
assert final_photo['sources'][historical_path] == sha(ROOT / historical_path)
source_copies = OUT / 'final-qa-source'
source_copies.mkdir(exist_ok=False)
for path in own_paths:
    (source_copies / (Path(path).name + '.txt')).write_bytes((ROOT / path).read_bytes())

proof = {
    'base_commit': BASE, 'runtime_freeze_commit': FINAL,
    'historical27_entire_source_unchanged': True,
    'historical27_current_sha256': sha(ROOT / historical_path),
    'historical27_main_assertions': 40, 'new28_main_assertions': 40,
    'assertion_ast_equal_after_only_target_revision_literal_delta': True,
    'frozen_helpers_imported_without_replacement': ['_populate_diary27', '_verify_restored_diary27'],
    'own_final_source_sha256': own_sha,
    'initial_proof_preserved': {'path': 'recovery28-qa-preservation-assertions.json',
                                'sha256': sha(OUT / 'recovery28-qa-preservation-assertions.json')},
    'initial_failed_restore_sources_preserved': {
        name: sha(OUT / name) for name in ['integration_recovery28_restore_review.first.txt',
                                         'recovery28_restore_helpers.first.txt']},
    'explicitly_approved_qa_lifecycle_correction': {
        'physical_before_factory': 'Full restored rows equal every backup row, including all 8 refresh rows and 4 revoked rows.',
        'after_existing_factory_cleanup': 'Full rows equal a deep copy of backup with only the exact 4 pre-seeded revoked jtis removed; expected is never derived from observed target.',
        'runtime_after_cleanup': 'Old access and refresh rejected even after revoked rows are gone; the exact other 4 live jtis survive until their own reset.',
        'auth_table_literal_guard': "AuthAuditLog.__tablename__ == 'auth_audit_log' and exact auth table names exist in reflected schema.",
        'business_projection_after_reset': 'Only usuarios, refresh_tokens and auth_audit_log mutate during actual credential/reset/login operations; all remaining tables exact.',
        'historical27_fixture_modified': False,
        'product_modified': False,
    },
}
emit('recovery28-qa-final-preservation.json', proof)

labels = ['directed-d9c8f80', 'own-453cb7-final', 'sqlite-453cb7', 'postgres-453cb7', 'restore-453cb7-final']
phases = []
for label in labels:
    data = json.loads((OUT / label / 'source.json').read_text())
    assert data['exit'] == 0 and data['source_stable'] and data['packages_stable']
    assert data['packages'] == 89 and data['pip_check_before_after'] == [0, 0]
    assert data['junit']['failure'] == data['junit']['error'] == data['junit']['skipped'] == 0
    xml = ET.parse(OUT / label / 'result.xml').getroot()
    suites = [xml] if xml.tag == 'testsuite' else list(xml.iter('testsuite'))
    parsed = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
              for key in ['tests', 'failures', 'errors', 'skipped']}
    assert parsed['tests'] == data['junit']['tests']
    assert parsed['failures'] == parsed['errors'] == parsed['skipped'] == 0
    phases.append({'label': label, **data, 'source_proof_sha256': sha(OUT / label / 'source.json'),
                   'junit_sha256': sha(OUT / label / 'result.xml')})
assert sum(phase['junit']['tests'] for phase in phases) == 211

measurement = json.loads((OUT / 'restore-453cb7-final/postgres-restore-recovery28-independent.json').read_text())
assert measurement['tables'] == 26 and measurement['rls_families_force'] == 20
assert measurement['private_objects'] == 5 and measurement['legacy_files'] == 2
assert measurement['diary_days'] == 5 and measurement['diary_subjects'] == 2
raw = measurement['restored_recovery_material_before_factory']
assert raw['restored_refresh_rows_before_factory'] == 8 and raw['restored_revoked_rows_before_factory'] == 4
assert raw['constraint_sqlstates'] == ['23514', '23514', '23514', '23505']
assert raw['utc_zones'] == ['UTC', 'America/Mexico_City']
assert raw['all_reset_states_persisted_exactly'] and raw['plain_bearer_absent_in_restored_accounts']
assert measurement['physical_backup_rows_by_table']['refresh_tokens'] == 8
assert measurement['rows_by_table']['refresh_tokens'] == 4
assert measurement['restored_recovery']['remaining_live_refresh_before_reset'] == 4
assert len(measurement['restored_recovery']['http']) == 2
for item in measurement['restored_recovery']['http']:
    assert all(item[key] for key in ['restored_pending_bearer_consumed_once', 'old_access_refresh_rejected',
                                    'normal_new_password_login', 'no_autologin'])
for label in ['restore-453cb7-first', 'restore-453cb7-final']:
    created = json.loads((OUT / label / 'recovery28-qa-owned-created.json').read_text())
    closed = json.loads((OUT / label / 'recovery28-qa-owned-closed.json').read_text())
    assert created['names'] == closed['names'] and closed['remaining'] == [] and closed['dropped_exactly_owned']

summary = {
    'decision': 'Accepted for scoped independent recovery28 QA on composition; no open product blocker from this review.',
    'phases': phases, 'positive_test_observations': 211,
    'directed_baseline_scope': '181 directed cases were run at d9c8f80 before the later header-only fix; the 6 own, 6 SQLite, 17 PostgreSQL and restore28 ran at453cb7. No claim that181 or broad2064 were rerun at453.',
    'preservation': '28 historical contracts unchanged; three approved historical function deltas retain all assertions; nine prior email functions, two login script blocks and entire restore27 source unchanged. New28 retains40 main asserts.',
    'restore': measurement,
    'owned_database_cleanup': 'Both first/final restore pairs were dropped by the accepted exact-name fixture and absence independently verified; no unrelated databases touched.',
    'retained_red_and_corrections': [
        {'label': 'own-453cb7-first', 'result': '4 pass/2 failed', 'classification': 'QA observer scope: actual startup rejected old schema during create_app before the expected-error context. Moved create_app into the observer; product unchanged, final6/6.'},
        {'label': 'restore-453cb7-first', 'result': 'Physical restore checks passed; post-startup full rows comparison failed.', 'classification': 'Existing factory startup legitimately deletes revoked refresh rows. Explicit parent-approved correction predicts only4 exact seeded revoked IDs from backup; preserves complete physical comparison and all40 assertions. Final1/1.'},
        {'classification': 'Private config inspection orchestration error', 'detail': 'A preliminary PowerShell linewise JSON parse produced errors containing local PostgreSQL URLs without passwords. No connection launched; corrected to load private config only in child Python memory. No URL or config content copied into this proof.'},
        {'classification': 'QA helper literal correction before first runtime reached helper', 'detail': 'Corrected auth audit table literal to actual singular auth_audit_log with reflection guard. No product or historical assertion changed.'},
    ],
    'pending_separate_integration_gates': ['CI28 author wiring/delta verifier and independent acceptance', 'Final composition freeze followed by separately authorized broad serial and shuffled gate'],
    'scope': 'Windows candidate Python, real isolated SQLite and loopback PostgreSQL, synthetic UUID-owned databases and local object files. No real provider, deployment, Actions or Linux execution claim. No product/CI edits or commits.',
    'final_preservation_proof_sha256': sha(OUT / 'recovery28-qa-final-preservation.json'),
}
emit('recovery28-qa-final-summary.json', summary)
manifest = {str(path.relative_to(OUT)).replace('\\', '/'): sha(path)
            for path in sorted(OUT.rglob('*')) if path.is_file()}
emit('recovery28-qa-evidence-manifest.json', {'files': manifest, 'count': len(manifest),
                                          'scope': 'All files under this new independent QA prefix except this self-referential manifest.'})
print(json.dumps({'positive_observations': 211, 'final_restore': '1/1',
                  'source_sha256': own_sha,
                  'preservation_sha256': sha(OUT / 'recovery28-qa-final-preservation.json'),
                  'summary_sha256': sha(OUT / 'recovery28-qa-final-summary.json'),
                  'manifest_sha256': sha(OUT / 'recovery28-qa-evidence-manifest.json'),
                  'evidence_files': len(manifest)}))
