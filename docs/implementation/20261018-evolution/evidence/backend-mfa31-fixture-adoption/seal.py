"""Freeze current31 test-only fixture adoption and private/public proof split."""
import ast
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path('F:/mb-mfa31-fixtures-20261019')
HERE = Path(__file__).parent
OUT = ROOT / 'docs/implementation/20261018-evolution/evidence/backend-mfa31-fixture-adoption'
BASE = '913cb66061ac754ad09344fc24e8f769b5722997'
SOURCE_COMMIT = 'dab090679a48cb8b064804a13622c415db0a170b'
SOURCES = ['tests/mfa31_contract_client.py', 'tests/test_mfa31_contract_fixture_review.py',
    'tests/test_personal_diary_security_review.py', 'tests/test_team_entitlement_review.py',
    'tests/test_team_invitation_contract.py']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)


def original_tests(raw):
    return {item.name: item for item in ast.parse(raw).body
            if isinstance(item, ast.FunctionDef) and item.name.startswith('test_')}


def assertions(node):
    return [item for item in ast.walk(node) if isinstance(item, ast.Assert)]


def dumped(node):
    return ast.dump(node, include_attributes=False)


def main():
    assert git('rev-parse', 'HEAD').decode().strip() == SOURCE_COMMIT
    assert git('diff', '--name-only').decode().strip() == ''
    assert sorted(git('diff', '--name-only', BASE, SOURCE_COMMIT).decode().splitlines()) == sorted(SOURCES)
    assert (OUT / 'conftest.py.before-RAW').read_bytes() == (ROOT / 'conftest.py').read_bytes()
    assert_maps = []
    changed_nodes = []
    for filename in ['tests/test_team_invitation_contract.py', 'tests/test_team_entitlement_review.py',
                     'tests/test_personal_diary_security_review.py']:
        before = git('show', BASE + ':' + filename)
        old, new = original_tests(before), original_tests((ROOT / filename).read_bytes())
        assert set(old) == set(new)
        total, preserved, added = 0, 0, 0
        for name in old:
            old_asserts, new_asserts = assertions(old[name]), assertions(new[name])
            expected = copy.deepcopy(old_asserts)
            if name == 'test_team_mutations_never_cross_to_another_gym':
                status = expected[0]
                assert isinstance(status.test, ast.Compare)
                assert len(status.test.comparators) == 1 and status.test.comparators[0].value == 404
                status.test.comparators[0].value = 403
                changed_nodes.append({'file': filename, 'function': name, 'assert_source_node': 0,
                    'old_status': 404, 'current_status': 403,
                    'exact_parameterized_cases': ['role', 'remove', 'resend']})
            candidates = iter(new_asserts)
            for target in expected:
                assert any(dumped(candidate) == dumped(target) for candidate in candidates), (filename, name)
            total += len(old_asserts)
            preserved += sum(dumped(a) == dumped(b) for a, b in zip(old_asserts, expected))
            added += len(new_asserts) - len(old_asserts)
        assert_maps.append({'file': filename, 'original_test_functions': len(old), 'original_assert_nodes': total,
            'original_assert_nodes_AST_identical': preserved, 'added_assert_nodes': added,
            'test_function_names_unchanged': True})
    assert len(changed_nodes) == 1
    team_maps = [item for item in assert_maps if 'diary' not in item['file']]
    assert sum(item['original_assert_nodes'] for item in team_maps) == 110
    assert sum(item['original_assert_nodes_AST_identical'] for item in team_maps) == 109
    assert_maps_data = {'source_commit': SOURCE_COMMIT, 'files': assert_maps,
        'approved_status_change': changed_nodes,
        'counting': 'One source Assert node expands to exactly3 parameterized expectations.109/110 original team/entitlement nodes remain exact; all original diary Assert nodes remain exact. New checks are additional.'}
    (OUT / 'assert-adoption-map.json').write_text(json.dumps(assert_maps_data, indent=2) + '\n', encoding='utf-8', newline='\n')
    labels = {'first-adoption': (2, 0), 'adopted-team-contracts': (44, 3), 'current31-opacity-matrix': (10, 0),
        'diary-revoke-before': (2, 1), 'final-adopted-contracts': (56, 0), 'diary-security-module': (27, 0), 'final-directed-eight': (174, 0)}
    reports = {}
    for label, (count, failed) in labels.items():
        report = json.loads((OUT / (label + '-summary.json')).read_bytes())
        assert (report['cases'], report['counts']['failure'], report['counts']['error'], report['counts']['skipped']) == (count, failed, 0, 0)
        assert report['source_quiet'] and report['packages'] == 89
        assert report['redactions'] == {'log': [0, 0, 0, 0], 'xml': [0, 0, 0, 0]}
        assert sha((HERE / (label + '.private.log')).read_bytes()) == report['raw_log_private_sha256']
        assert sha((HERE / (label + '.private.xml')).read_bytes()) == report['raw_xml_private_sha256']
        assert sha((OUT / (label + '-projected.log')).read_bytes()) == report['projected_log_sha256']
        assert sha((OUT / (label + '-projected.xml')).read_bytes()) == report['projected_xml_sha256']
        reports[label] = report
    final = ET.fromstring((HERE / 'final-directed-eight.private.xml').read_bytes())
    cases = list(final.iter('testcase'))
    breakdown = Counter(item.attrib['classname'] for item in cases)
    final_ids = {(item.attrib['classname'], item.attrib['name']) for item in cases}
    assert len(final_ids) == 174
    original_root = json.loads((HERE / 'root-summary.private.json').read_bytes())
    assert original_root['head'] == BASE and original_root['cases'] == 92
    assert original_root['counts'] == {'passed': 72, 'failure': 20, 'error': 0, 'skipped': 0}
    root_ids = {(item['module'], item['case']) for item in original_root['rows']}
    assert root_ids <= final_ids
    assert {item['case'] for item in reports['adopted-team-contracts']['rows']} <= {item[1] for item in final_ids}
    source_hashes = {}
    for filename in SOURCES:
        raw = (ROOT / filename).read_bytes()
        blob = git('show', SOURCE_COMMIT + ':' + filename)
        assert raw.replace(b'\r\n', b'\n') == blob
        source_hashes[filename] = {'raw_sha256': sha(raw), 'git_lf_sha256': sha(blob), 'raw_bytes': len(raw)}
    shutil.copyfile(HERE / 'run.py', OUT / 'scanned-replay-runner.py')
    shutil.copyfile(Path(__file__), OUT / 'seal.py')
    original_driver = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-mfa31-legacy-contract-diagnostic.py')
    shutil.copyfile(original_driver, OUT / 'coordinator-diagnostic-driver-original.py')
    (OUT / 'test-only.diff').write_bytes(git('diff', BASE, SOURCE_COMMIT, '--', *SOURCES))
    (OUT / 'ruff.txt').write_bytes(b'ruff check --select F821,E9 (all5changedtestsourcefiles)\nAll checks passed!\n')
    private = {item.name: {'sha256': sha(item.read_bytes()), 'bytes': item.stat().st_size}
        for item in sorted(HERE.iterdir()) if item.is_file() and ('.private.' in item.name or item.name.startswith('root-'))}
    (OUT / 'private-artifact-receipt.json').write_text(json.dumps({'private_dir': str(HERE), 'artifacts': private,
        'disposition': 'Private exact raw outputs retained; only scanned public projection was published.'}, indent=2) + '\n', encoding='utf-8', newline='\n')
    summary = {'base': BASE, 'source_commit_tested_by_final_directed_run': SOURCE_COMMIT,
        'scope': 'Current31 opt-in test fixture adoption only; no application changes.',
        'coordinator_original_bounded_before': {'cases':92, 'passed':72, 'failures':20, 'maxfail':20,
            'all_original_92_case_ids_present_in_final': True, 'driver_sha256': sha(original_driver.read_bytes())},
        'final_directed': reports['final-directed-eight'], 'final_module_counts': dict(breakdown),
        'assertion_map': assert_maps_data,
        'causality': 'Original missing-bearer401 resolved by real auth/enrollment/grants; approved3target403 precedences after preserved404reds and9opaque-state-negativecases. Diary Web enrollment403 resolved by setup only; APIbranch unchanged.',
        'stages': {label: {key: report[key] for key in ('cases','counts','source_quiet','packages')} for label, report in reports.items()},
        'overlap': 'First2,44,10,2,56,27 andfinal174 overlap; they are not additive unique criteria. Final174 includes all92 initial coordinator case IDs and all new10causal/controlcases.',
        'historical': 'Historical30 preserves404. No conftest, helpers22-30, schema targets, migration, application, CI or browser source changed.',
        'publication': 'All private raw log/XML files retained and hashed. Published projections scanned for2-part HMAC/CSRF3-part/otpauth/labeledopaquevalues; zero matches in these runs. This is not a general DLP guarantee.',
        'source_hashes': source_hashes,
        'limitations': 'SQLite/ASGI author evidence only. Independent fixture QA pending. No PG/browser/operational MFA/AAL2/provider claims. Old team browser adoption is assigned separately.',
        'stability': 'Source and89installed packages photographed identical before/after everyrun; finalrun on committed dab0906 without later test-source edits.',
        'encoding': 'Evidence prefix * -text fromcreation; normal testsource GitLF. RAW andGitLF source hashes recorded separately.'}
    (OUT / 'review-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    rows = {item.name: {'sha256': sha(item.read_bytes()), 'bytes': item.stat().st_size}
        for item in sorted(OUT.iterdir()) if item.is_file() and item.name != 'freeze.json'}
    freeze = {'base':BASE, 'source_commit_tested':SOURCE_COMMIT, 'proof_files':rows, 'source_hashes':source_hashes}
    (OUT / 'freeze.json').write_text(json.dumps(freeze, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'freeze_sha256':sha((OUT/'freeze.json').read_bytes()),'summary_sha256':sha((OUT/'review-summary.json').read_bytes()),'proof_files':len(rows)+1,'assertion_map':assert_maps,'final_module_counts':dict(breakdown)}))


if __name__ == '__main__':
    main()
