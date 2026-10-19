"""Exact CI31 workflow composition from authenticated CI30, no product edits."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import shlex

import yaml

ROOT = Path(__file__).resolve().parents[2]
CURRENT_REPORT_COMMANDS = (
    ('member-services', ['tests/integration_current31_member_services.py'], ''),
    ('member-http', ['tests/integration_current31_member_http.py'], ''),
    ('member-races', ['tests/integration_current31_member_races.py'], ''),
    ('r24-publication', ['tests/integration_current31_r24_publication.py'], ''),
    ('r24-race', ['tests/integration_current31_r24_race.py'], ''),
    ('mfa-migrations', ['tests/integration_mfa31_migrations.py'], ' -k postgresql'),
    ('mfa-services', ['tests/integration_mfa31_postgres.py'], ''),
    ('mfa-restore', ['tests/integration_mfa31_restore.py'], ''),
    ('followup', ['tests/integration_followup_postgres.py'], ''),
    ('rls-worker', ['tests/integration_postgres.py'], ''),
    ('privacy-export', ['tests/integration_privacy_composition_postgres.py'], ''),
    ('diary', ['tests/integration_personal_diary_postgres.py', 'tests/integration_personal_diary_security_review.py'], ''),
)
CURRENT_VM = {'mfa_api': 28, 'mfa_state': 30, 'mfa_consumers': 8, 'mfa_prompt': 8,
              'daily_plan_data': 23, 'daily_plan_controls': 17,
              'personal_export_context': 17, 'personal_export_url_contract': 15}


def projection(name, directory, output, files):
    return {'name': name, 'if': 'always()', 'working-directory': '${{ github.workspace }}',
            'run': 'python -X utf8 tests/ci_mfa31/publish.py --directory "' + directory +
                   '" --output "' + output + '" --files ' + ' '.join('"' + path + '"' for path in files)}


def upload(name, directory, files):
    return {'uses': 'actions/upload-artifact@v4', 'if': 'always()', 'with': {
        'name': name, 'path': '\n'.join(directory + '/' + name for name in [*files, 'publication.json']),
        'if-no-files-found': 'error'}}


def materializer(name):
    return {'name': 'Materialize exact accepted CI30 Git blobs; no archive filters or replace refs',
        'working-directory': '${{ github.workspace }}',
        'run': 'python -X utf8 tests/run_reviewed_ci30.py --materialize-only --history-repository "$GITHUB_WORKSPACE" --output "$RUNNER_TEMP/ci30-' + name + '"'}


def capture(block, folder, index):
    return ('install -d -m 700 "$RUNNER_TEMP/' + folder + '"\n(\n' + block.rstrip() +
            '\n) > "$RUNNER_TEMP/' + folder + '/step-' + str(index) + '.raw.log" 2>&1\n')


def expected_workflow():
    raw = (ROOT / 'tests/ci_mfa31/ci30-before.yml').read_bytes()
    if hashlib.sha256(raw).hexdigest() != '5f74662c11611e3041d87a8cbd4a6a8c6828606da7c46e1d2446af6b1e36ab9b':
        raise ValueError('Historical workflow snapshot differs before composition')
    old = yaml.safe_load(raw)
    expected = copy.deepcopy(old)
    # PyYAML's YAML1.1 treats unquoted `on` as a boolean; emit it quoted as the
    # literal Actions event key. No event or permission is otherwise changed.
    expected['on'] = expected.pop(True)
    jobs = expected['jobs']
    test_web = jobs['test-web']['steps']
    step = next(s for s in test_web if 'tests/verify_history_index_ci.py' in s.get('run', ''))
    step.update(name='Current MFA31 wiring, exact report nodes and offline trust canaries',
                run='python -X utf8 tests/verify_mfa31_ci.py --output "$RUNNER_TEMP/mfa31-ci-wiring"')
    for index, item in enumerate(test_web):
        if 'tests/run_isolated.py ' in item.get('run', ''):
            item['run'] = capture(item['run'], 'web-private', index)
    # Keep serial coverage, coverage threshold, SDK checks, n2 shuffle and both
    # no-skip gates unchanged. Upload structural projections, never raw traces.
    web_upload = next(s for s in test_web if s.get('with', {}).get('name', '').startswith('web-tests-'))
    web_files = web_upload['with']['path'].splitlines()
    test_web.remove(web_upload)
    test_web.extend([projection('Project current web reports without assertion bodies', '$GITHUB_WORKSPACE',
                               '$RUNNER_TEMP/web-public', web_files),
                     upload('web-tests-${{ matrix.python }}', '${{ runner.temp }}/web-public', web_files)])
    desktop = jobs['test-desktop']['steps']
    for index, item in enumerate(desktop):
        if 'tests/run_isolated.py ' in item.get('run', ''):
            item['shell'] = 'bash'
            item['run'] = capture(item['run'], 'desktop-private', index)
    desktop_upload = next(s for s in desktop if s.get('with', {}).get('name', '').startswith('desktop-tests-'))
    desktop.remove(desktop_upload)
    files = desktop_upload['with']['path'].splitlines()
    projected = projection('Project desktop reports without assertion bodies', '$GITHUB_WORKSPACE',
                           '$RUNNER_TEMP/desktop-public', files)
    # Portable shell quoting is explicit on both supported desktop runners.
    projected['shell'] = 'bash'
    desktop.extend([projected, upload('desktop-tests-${{ matrix.os }}', '${{ runner.temp }}/desktop-public', files)])
    frontend = jobs['frontend-contracts']['steps']
    previous = next(s for s in frontend if 'Member link API' in s.get('name', ''))
    previous['run'] = previous['run'].replace('node tests/e2e/member_link_consumers.cjs',
                                             'node tests/e2e/member_link_consumers31.cjs')
    previous['name'] += '; current31 uses real R24 companions with all16 original callbacks'
    frontend_upload = next(s for s in frontend if s.get('with', {}).get('name') == 'frontend-session-contracts')
    frontend.remove(frontend_upload)
    vm_lines = []
    for module, minimum in CURRENT_VM.items():
        filename = module.replace('_', '-') + '-current31.json'
        if module == 'daily_plan_data':
            raw = filename.replace('.json', '.raw.json')
            vm_lines += ['node tests/e2e/' + module + '.cjs > ' + raw,
                         'python tests/e2e/normalize_followup_report.py ' + raw + ' ' + filename + ' --kind counts --minimum ' + str(minimum)]
        else:
            vm_lines += ['node tests/e2e/' + module + '.cjs > ' + filename]
        vm_lines.append('python scripts/check_frontend_report.py ' + filename + ' --format counts --minimum ' + str(minimum))
    frontend.append({'name': 'MFA31 transport/state/consumer/prompt and current R24/export VM contracts', 'run': '\n'.join(vm_lines) + '\n'})
    frontend_files = []
    for step in frontend:
        for line in step.get('run', '').splitlines():
            if line.startswith('node tests/') and ' > ' in line:
                frontend_files.append(line.split(' > ')[1])
            if line.startswith('python tests/e2e/normalize_followup_report.py '):
                frontend_files.append(shlex.split(line)[3])
    assert len(frontend_files) == len(set(frontend_files))
    for index, item in enumerate(frontend):
        if 'run' in item:
            item['run'] = capture(item['run'], 'frontend-private', index)
    frontend.extend([projection('Project frontend counters only; raw RAM harness diagnostics remain private',
                                '$GITHUB_WORKSPACE', '$RUNNER_TEMP/frontend-public', frontend_files),
                     upload('frontend-session-contracts', '${{ runner.temp }}/frontend-public', frontend_files)])
    # The historical job runs the unchanged FULL verifier (33+55+24+12+27) and
    # the23 original VM modules/348 executions on genuine source30, not Base31.
    jobs['historical-ci30'] = {'runs-on': 'ubuntu-latest', 'needs': 'quality', 'steps': [
        {'uses': 'actions/checkout@v4', 'with': {'fetch-depth': 0}},
        {'uses': 'actions/setup-python@v5', 'with': {'python-version': '3.12'}},
        {'uses': 'actions/setup-node@v4', 'with': {'node-version': '24'}},
        {'run': 'python -m pip install --require-hashes -r requirements-test.lock'},
        {'name': 'Unchanged full CI30 and original VM348 on authenticated ancestor30',
         'run': 'python -X utf8 tests/run_reviewed_ci30.py --history-repository "$GITHUB_WORKSPACE" --output "$RUNNER_TEMP/ci30-full" --include-vm'}]}
    historical_pg = jobs.pop('postgres')
    historical_pg['defaults'] = {'run': {'shell': 'bash', 'working-directory': '${{ runner.temp }}/ci30-postgres/source'}}
    historical_pg['env']['METODOBASE_TEST_EVIDENCE_DIR'] = '${{ runner.temp }}/ci30-postgres-private/evidence'
    pg_steps = historical_pg['steps']
    pg_steps.insert(2, materializer('postgres'))
    pg_steps.insert(3, {'name': 'Keep historical raw restore evidence private',
                        'run': 'install -d -m 700 "$METODOBASE_TEST_EVIDENCE_DIR"'})
    for step in pg_steps:
        block = step.get('run', '')
        if 'tests/run_reviewed_ci28.py' in block or 'tests/run_reviewed_ci29.py' in block:
            step['run'] = block + ' --history-repository "$GITHUB_WORKSPACE"'
    pg_upload = next(s for s in pg_steps if s.get('with', {}).get('name') == 'postgres-integration')
    pg_files = re.findall(r'--junitxml=(pytest-postgres-[A-Za-z0-9-]+\.xml)',
                          '\n'.join(s.get('run', '') for s in pg_steps))
    assert len(pg_files) == len(set(pg_files)) == 29
    pg_steps.remove(pg_upload)
    for index, item in enumerate(pg_steps):
        if 'run' in item:
            item['run'] = capture(item['run'], 'ci30-postgres-private', index)
    pg_steps.extend([projection('Project all29 historical reports; retain exact old acceptance checks',
                               '$RUNNER_TEMP/ci30-postgres/source', '$RUNNER_TEMP/ci30-postgres-public', pg_files),
                     upload('historical30-postgres-tests', '${{ runner.temp }}/ci30-postgres-public', pg_files)])
    jobs['historical-postgres'] = historical_pg
    historical_image = jobs.pop('image')
    historical_image['needs'] = ['test-web', 'historical-postgres']
    historical_image['defaults'] = {'run': {'shell': 'bash', 'working-directory': '${{ runner.temp }}/ci30-image/source'}}
    steps = historical_image['steps']
    steps[0]['with'] = {'fetch-depth': 0}
    steps[1:1] = [{'uses': 'actions/setup-python@v5', 'with': {'python-version': '3.12'}}, materializer('image')]
    browser_files = []
    for step in steps:
        if 'run' in step:
            step['run'] = step['run'].replace('metodobase-candidate', 'metodobase-ci30').replace(
                '$GITHUB_WORKSPACE/tests/e2e/node_modules', '$RUNNER_TEMP/ci30-image/source/tests/e2e/node_modules')
            for line in step['run'].splitlines():
                if line.startswith('run_browser_fixture '):
                    args = shlex.split(line)
                    browser_files.append(args[4].replace('${browser_evidence}', 'docs/implementation/20261018-evolution/evidence/ux'))
                    if len(args) > 9 and args[8]:
                        browser_files.append(args[9].replace('${browser_evidence}', 'docs/implementation/20261018-evolution/evidence/ux'))
    steps[:] = [s for s in steps if not s.get('uses', '').startswith('actions/upload-artifact@')]
    for index, item in enumerate(steps):
        if 'run' in item:
            item['run'] = capture(item['run'], 'ci30-image-private', index)
    for name, directory, output, files in [
        ('Historical30 labelled browser reports', '$RUNNER_TEMP/ci30-image/source', '$RUNNER_TEMP/ci30-image-public', browser_files),
        ('Historical30 R12 and followup browser reports', '$RUNNER_TEMP', '$RUNNER_TEMP/ci30-host-public',
         ['member-link-public/report.json', 'followup-public/report.json'])]:
        step = projection(name, directory, output, files)
        if browser_files == files:
            step['run'] = 'export METODOBASE_EVIDENCE_BATCH="ci-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"\n' + step['run']
        steps.extend([step, upload(name.replace(' ', '-'), output.replace('$RUNNER_TEMP', '${{ runner.temp }}'), files)])
    steps.append({'uses': 'actions/upload-artifact@v4', 'with': {'name': 'historical30-candidate-identity',
        'path': '${{ runner.temp }}/ci30-image/source/candidate-image-id.txt', 'if-no-files-found': 'error'}})
    jobs['historical-image'] = historical_image
    # Current31 has its own fresh service and runs each full identity set. It
    # never reuses an archive's29 reports to stand in for the new schema.
    current_pg = copy.deepcopy(old['jobs']['postgres'])
    current_pg['env'].update(METODOBASE_TEST_EVIDENCE_DIR='${{ runner.temp }}/current31-private/evidence',
                            R24_PG_OUTPUT='${{ runner.temp }}/current31-private/r24')
    current_pg['steps'] = copy.deepcopy(old['jobs']['postgres']['steps'][:4])
    current_pg['steps'].append({'name': 'Create private current31 evidence locations',
        'run': 'install -d -m 700 "$RUNNER_TEMP/current31-private" "$METODOBASE_TEST_EVIDENCE_DIR" "$R24_PG_OUTPUT"'})
    current_pg['steps'].append({'name': 'Current31 real migrations and restricted runtime role',
                               'run': 'python -X utf8 tests/prepare_postgres.py'})
    current_files = []
    for label, modules, selection in CURRENT_REPORT_COMMANDS:
        report = 'pytest-current31-' + label + '.xml'
        current_files.append(report)
        current_pg['steps'].append({'name': 'Current31 ' + label + '; original full business assertions',
            'run': 'python -X utf8 tests/run_isolated.py ' + ' '.join(modules) + selection +
                   ' -q --tb=short --junitxml=' + report +
                   ' > "$RUNNER_TEMP/current31-private/' + label + '.raw.log" 2>&1'})
    current_pg['steps'].extend([
        {'name': 'Every exact current31 PG identity passes; no skips/errors/substitutions/duplicates',
         'run': 'python -X utf8 tests/check_mfa31_reports.py'},
        projection('Project all12 current31 reports without authentication diagnostics', '$GITHUB_WORKSPACE',
                   '$RUNNER_TEMP/current31-postgres-public', current_files),
        upload('current31-postgres-tests', '${{ runner.temp }}/current31-postgres-public', current_files)])
    jobs['current-postgres'] = current_pg
    image_service = copy.deepcopy(old['jobs']['image']['services'])
    current_image = {'runs-on': 'ubuntu-latest', 'needs': 'quality', 'services': image_service,
        'env': {'METODOBASE_TEST_MIGRATOR_URL': 'postgresql+psycopg2://metodobase_test_admin:synthetic-ci-only@127.0.0.1:55483/metodobase_test_image',
                'METODOBASE_TEST_POSTGRES_URL': 'postgresql+psycopg2://metodobase_test_app:synthetic-app-only@127.0.0.1:55483/metodobase_test_image',
                'METODOBASE_TEST_PG_BIN': '/usr/lib/postgresql/17/bin'},
        'steps': [{'uses': 'actions/checkout@v4', 'with': {'fetch-depth': 0}},
                  {'uses': 'actions/setup-python@v5', 'with': {'python-version': '3.12'}},
                  {'uses': 'actions/setup-node@v4', 'with': {'node-version': '24', 'cache': 'npm',
                                                           'cache-dependency-path': 'tests/e2e/package-lock.json'}},
                  {'run': 'python -m pip install --require-hashes -r requirements-test.lock'},
                  copy.deepcopy(old['jobs']['postgres']['steps'][3]),
                  {'name': 'Current31 locked browser dependencies and Chromium', 'run': 'npm ci --prefix tests/e2e --ignore-scripts\nnode tests/e2e/node_modules/playwright-core/cli.js install --with-deps chromium'},
                  {'name': 'Build current31 production Dockerfile from this exact checkout',
                   'run': 'docker build --tag metodobase-current31:${{ github.sha }} .'},
                  {'name': 'Current31 actual entrypoint, image MFA and R12/R24/followup/MFA browsers; owned cleanup',
                   'run': 'export CHROME_PATH=$(node -e "process.stdout.write(require(\'./tests/e2e/node_modules/playwright-core\').chromium.executablePath())")\npython -X utf8 tests/ci_mfa31/run_current_browser.py --image-tag metodobase-current31:${{ github.sha }} --output "$RUNNER_TEMP/current31-browser-public"'},
                  upload('current31-real-image-and-browser', '${{ runner.temp }}/current31-browser-public',
                      ['image-inventory.json', 'image-identity.json', 'image-browser.json', 'member-report.json',
                       'followup-report.json', 'daily-report.json', 'mfa-ui-report.json', 'mfa-personal-report.json'])]}
    jobs['current-image'] = current_image
    jobs['ci-success']['needs'] = [name for name in jobs if name != 'ci-success']
    return expected


def write(path: Path):
    class LiteralDumper(yaml.SafeDumper):
        pass
    def string(dumper, value):
        return dumper.represent_scalar('tag:yaml.org,2002:str', value, style='|' if '\n' in value else None)
    LiteralDumper.add_representer(str, string)
    path.write_bytes(yaml.dump(expected_workflow(), Dumper=LiteralDumper, sort_keys=False, width=120).encode('utf8'))


if __name__ == '__main__':
    write(ROOT / '.github/workflows/ci.yml')
