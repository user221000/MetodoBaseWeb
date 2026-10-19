"""Verify HIST30/CURRENT31 separation, trusted source pins and strict parsers.

Local static/offline execution is not Actions, PG, Chromium or image evidence.
Historical full execution has its own runner; current services have their own
jobs and exact node IDs, and cannot be satisfied by historical report files.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Authenticate the executable checker before importing its API. API-only
# canaries cannot detect a replacement main() that unconditionally returns 0.
REPORT_CHECKER_SHA256 = 'b375cfda1eedefa1716af5150a9d7935c27f7e3b4e4f1fe21548aeead8e04484'


def verify_report_checker(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or path.resolve() != path.absolute():
        raise ValueError('Current31 report checker is missing or aliased')
    if hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != REPORT_CHECKER_SHA256:
        raise ValueError('Current31 report checker executable differs from its reviewed source')


verify_report_checker(ROOT / 'tests/check_mfa31_reports.py')

import yaml
from tests.check_mfa31_reports import required_reports
from tests.ci_mfa31.workflow import expected_workflow, CURRENT_VM
from tests.run_reviewed_ci30 import new_directory, require, trusted_baseline, REVISION

MEMBER31_SHA256 = '4b8db35bfac09bef72b32940dab81245a316385d7a78a05a1c725b67b4167be6'
SNAPSHOT_SHA256 = 'e61033118012fb2357ae978ab28171a9f0b41f54a9f559b18a487ffcfd275fa0'
DIARY_CONTROLLER_SHA256 = 'e6b407d7b68a8536a14e4b195a4728f5f79edc1f7b5d24529b76715666bd5e10'
MAPPING_SHA256 = '16b09c49bd3a84eb4849586465664ac5f86e85ea77dcb5d940c4e5c54889d6a7'
BROWSER_MAPPING_SHA256 = 'f7c779a99e18f59a36b42f96cf223bc0f9e94e7e6b1b67c9bcb896ff8bdb854a'


def verify_workflow(actual: dict) -> None:
    require(CURRENT_VM == {'mfa_api': 28, 'mfa_state': 30, 'mfa_consumers': 8, 'mfa_prompt': 8,
            'daily_plan_data': 23, 'daily_plan_controls': 17, 'daily_plan_snapshot': 25,
            'personal_export_context': 17, 'personal_export_url_contract': 15},
            'Current31 must retain all snapshot25 executions: 7 new and18 replayed criteria')
    require(actual == expected_workflow(), 'CI31 differs from the exact reviewed historical/current composition')


def workflow_canaries(workflow: dict) -> list[dict]:
    results = []
    # Deleting any job, run gate or upload is a concrete unauthorized reduction,
    # including historical FULL,29 old reports and every current31 frontier.
    for job in workflow['jobs']:
        mutant = copy.deepcopy(workflow)
        del mutant['jobs'][job]
        try:
            verify_workflow(mutant)
        except ValueError:
            results.append({'case': 'missing-job-' + job, 'rejected': True})
        else:
            raise AssertionError('A required CI31 job could be removed')
    for job, value in workflow['jobs'].items():
        for index, step in enumerate(value['steps']):
            if 'run' not in step and not step.get('uses', '').startswith('actions/upload-artifact@'):
                continue
            mutant = copy.deepcopy(workflow)
            del mutant['jobs'][job]['steps'][index]
            try:
                verify_workflow(mutant)
            except ValueError:
                results.append({'case': 'missing-step-' + job + '-' + str(index), 'rejected': True})
            else:
                raise AssertionError('A required run/publication gate could be removed')
    for label, change in [
        ('history-cwd-current-source', lambda w: w['jobs']['historical-postgres']['defaults']['run'].update({'working-directory': '${{ github.workspace }}'})),
        ('history-repository-omitted', lambda w: w['jobs']['historical-ci30']['steps'][-1].update({'run': 'python tests/run_reviewed_ci30.py --output "$RUNNER_TEMP/not-authenticated"'})),
        ('raw-current-artifact', lambda w: w['jobs']['current-postgres']['steps'][-1]['with'].update({'path': '**/*'})),
        ('current-restored-as-history', lambda w: w['jobs']['current-postgres']['steps'][-3].update({'run': 'python tests/check_history_index_reports.py'})),
        ('current-uses-archived-image', lambda w: w['jobs']['current-image']['steps'][-2].update({'run': 'echo historical30-is-enough'})),
        ('weaken-frontend', lambda w: next(s for s in w['jobs']['frontend-contracts']['steps'] if 'MFA31 transport' in s.get('name', '')).update({'run': 'echo no-op'})),
        ('success-omits-current', lambda w: w['jobs']['ci-success']['needs'].remove('current-postgres')),
    ]:
        mutant = copy.deepcopy(workflow)
        change(mutant)
        try:
            verify_workflow(mutant)
        except ValueError:
            results.append({'case': label, 'rejected': True})
        else:
            raise AssertionError('An unauthorized CI31 substitution passed')
    return results


def verify_current_sources() -> dict:
    raw = (ROOT / 'tests/ci_mfa31/current-business-mapping.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == MAPPING_SHA256, 'Current business mapping trust metadata differs')
    mapping = json.loads(raw)
    browser_raw = (ROOT / 'tests/ci_mfa31/current-browser-mapping.json').read_bytes()
    require(hashlib.sha256(browser_raw).hexdigest() == BROWSER_MAPPING_SHA256, 'Current browser mapping trust metadata differs')
    for item in json.loads(browser_raw):
        for key, digest_key in [('historical_file', 'historical_normalized_sha256'), ('current_file', 'current_sha256')]:
            raw = (ROOT / item[key]).read_bytes().replace(b'\r\n', b'\n')
            require(hashlib.sha256(raw).hexdigest() == item[digest_key], 'Historical/current browser source differs from its attributed mapping')
    original_functions = 0
    for group in ('member_services', 'member_http', 'member_races', 'r24_publication'):
        item = mapping[group]
        wrapper = ast.parse((ROOT / ('tests/integration_current31_' + group + '.py')).read_text(encoding='utf8'))
        imports = {node.module: {alias.name for alias in node.names} for node in wrapper.body if isinstance(node, ast.ImportFrom)}
        require(not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in wrapper.body),
                'A business wrapper replaced an original test body')
        for module, digest in item['source_modules'].items():
            raw = (ROOT / ('tests/' + module + '.py')).read_bytes().replace(b'\r\n', b'\n')
            require(hashlib.sha256(raw).hexdigest() == digest, 'Original current business assertions changed')
            names = {node.name for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}
            require(imports['tests.' + module] == names, 'A current31 wrapper omitted original test functions')
            original_functions += len(names)
    race = mapping['r24_race']
    path = ROOT / 'tests/integration_current31_r24_race.py'
    source = path.read_text(encoding='utf8')
    node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == race['function'])
    first = min([node.lineno] + [decorator.lineno for decorator in node.decorator_list]) - 1
    body = ('\n'.join(source.splitlines()[first:node.end_lineno]) + '\n').encode()
    require(hashlib.sha256(body).hexdigest() == race['original_function_sha256'], 'The accepted R24 physical-lock assertions changed')
    helper = (ROOT / 'tests/ci_mfa31/current_link_fixtures.py').read_text(encoding='utf8')
    require('crear_access_token' not in helper and 'dependency_overrides' not in helper,
            'Current31 HTTP fixture bypasses actual authentication')
    for endpoint in ('/api/auth/login', '/api/auth/mfa/reauth', '/api/auth/mfa/enroll',
                     '/api/auth/mfa/enroll/confirm', '/api/auth/mfa/login/verify'):
        require(endpoint in helper, 'Current31 fixture omitted a real MFA protocol stage')
    member = (ROOT / 'tests/e2e/member_link_consumers31.cjs').read_bytes().replace(b'\r\n', b'\n')
    require(hashlib.sha256(member).hexdigest() == MEMBER31_SHA256, 'Current31 companion/DOM fixture differs from reviewed root freeze')
    for name, digest in [('daily_plan_snapshot.cjs', SNAPSHOT_SHA256),
                         ('personal_diary_controller.cjs', DIARY_CONTROLLER_SHA256)]:
        raw = (ROOT / 'tests/e2e' / name).read_bytes().replace(b'\r\n', b'\n')
        require(hashlib.sha256(raw).hexdigest() == digest,
                'Current31 snapshot25 or its18 original diary criteria changed')
    reports = required_reports()
    # Import actual ORM/revision only after process-local test isolation. This
    # reads model metadata and version files, never connects to PostgreSQL.
    from tests.isolation import prepare_environment, block_external_sockets
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    from web.database.models import Base
    from web.database.schema_control import expected_head
    require(len(Base.metadata.tables) == 32 and expected_head() == '20261019_mfa',
            'Current31 actual ORM/revision differs')
    return {'original_business_functions_reused': original_functions, 'original_R24_race_body_identical': True,
            'reports': len(reports), 'required_full_current_PG_nodeids': sum(map(len, reports.values())),
            'actual_model_tables': len(Base.metadata.tables), 'actual_expected_head': expected_head(),
            'physical33_and_service_execution': 'Pending explicit current PG/image/browser jobs; no static acceptance'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--workflow', type=Path, default=ROOT / '.github/workflows/ci.yml')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    baseline = trusted_baseline()
    workflow = yaml.safe_load(args.workflow.read_bytes())
    verify_workflow(workflow)
    require(not args.output.absolute().is_relative_to(ROOT), 'Review output must be outside source')
    output = new_directory(args.output)
    report = {'scope': 'Local offline wiring/AST/parser/owned inert checks only; not Actions/PG/browser/image',
              'historical30_commit': REVISION, 'historical_files': baseline['files'],
              'historical_regular_bytes': baseline['regular_bytes'], 'immutable_helpers': 23,
              'current': verify_current_sources(), 'workflow_canaries': workflow_canaries(workflow),
              'current_VM_minima': CURRENT_VM}
    if not args.verify_only:
        bash = os.environ.get('METODOBASE_CI_BASH') or ('C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash'))
        require(bool(bash), 'Reviewed Bash is required for syntax checks')
        blocks = [step['run'] for job in workflow['jobs'].values() for step in job['steps'] if 'run' in step]
        for index, block in enumerate(blocks):
            result = subprocess.run([bash, '-n'], input=block.encode('utf8'), capture_output=True, timeout=15)
            require(result.returncode == 0, 'CI31 Bash block does not parse: ' + str(index))
        refs = sorted(set(re.findall(r'(?:scripts|tests)/[A-Za-z0-9_./-]+\.(?:py|cjs)', args.workflow.read_text(encoding='utf8'))))
        require(all((ROOT / name).is_file() for name in refs), 'CI31 references a missing maintained source')
        result = subprocess.run([sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py',
            'tests/test_mfa31_ci_trust.py', '-q', '--tb=short', '--junitxml=' + str(output / 'parser-canaries.xml')],
            cwd=ROOT, capture_output=True, timeout=90)
        (output / 'parser-canaries.stdout.log').write_bytes(result.stdout)
        (output / 'parser-canaries.stderr.log').write_bytes(result.stderr)
        require(result.returncode == 0, 'Current31 parser/trust/publication canaries failed')
        report.update(bash_blocks=len(blocks), references=refs, parser_canaries_exit=0)
    (output / 'review.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
    print(json.dumps({'historical30': REVISION, 'current_report_nodes': 173,
                      'workflow_canaries': len(report['workflow_canaries']), 'static_only': True}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
