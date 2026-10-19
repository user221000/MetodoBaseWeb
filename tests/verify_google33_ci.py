"""Authenticate CI33 wiring and preserved versioned criteria, with CLI canaries.

Offline verification is not an execution of PostgreSQL, an image, Chromium,
Actions, deployment or a live identity provider.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPORT_CHECKER_SHA256 = '8e2a207bb859c1eb9d162cf74c58582a529c28346ee1f62b5561d440f7dbcd43'
TRUSTED_SOURCES = {
    "tests/check_google33_r05.py": "944d15f6e552531c8402b8fed4a367a515758ff81b397d5ab312183be59fad3d",
    "tests/check_google33_reports.py": "8e2a207bb859c1eb9d162cf74c58582a529c28346ee1f62b5561d440f7dbcd43",
    "tests/ci_google33/.gitattributes": "705fd4d6451a31d36b3df7de96f83f30ac976c9b4a6d1e51671d8e2f33e2d0da",
    "tests/ci_google33/SSR-framing-map.json": "07603381c0bd75e11345ae599c417cff133441378de8eba14b28f08ac628dfcd",
    "tests/ci_google33/adaptation-map.json": "89b1973014c4f76b35e9105c1d148991432c78400ddf070aac8acfab8adfc109",
    "tests/ci_google33/approved-composition.json": "48b31dc2527a60c8691c69252524be4c6e7b11263cd952712fb6090f9dac777d",
    "tests/ci_google33/autodiscovery-map.json": "7b95293b4c953f499e211e2a6fba8c3f879f23a25443f9c3207743313c399880",
    "tests/ci_google33/boot/sitecustomize.py": "36d961ad9f563ee9d9b92f572cec6e255493559796eedc02e39eb660e406a94c",
    "tests/ci_google33/browser-frame-map.json": "81b1f3b5811245fa69e539edbc1a5871468f5b11544b3eba4d98c969b0dc939a",
    "tests/ci_google33/collect.py": "2d049696360024d7b4d69bb8a1051dfb0631968ff1c1f6ca3f5c41b7ad74d2b2",
    "tests/ci_google33/compatibility-map.json": "ee1a6a090bfae8306b266a329bbc90478ac61e81d46f586f67895fe69603cad2",
    "tests/ci_google33/contract-body-map.json": "6d688c5026423862bd8f3a883bca9b722156165ed3e6840066ffbd0cd3ee40f8",
    "tests/ci_google33/current33-report-nodeids.json": "bfe56b94eb761db950ef1da66eba4e6e7c175af960ea117e0258256811a8fc0b",
    "tests/ci_google33/current_link_fixtures.py": "3f1a29d558ea25eb597a338f53eb8620da81f8ac6ae0fa583f4e444de74443cd",
    "tests/ci_google33/environment_photo.py": "a4ea5fbcde79ebd50d408408b873037c2950b6c6182b4fe75c2e87658de3b99d",
    "tests/ci_google33/historical-sources.json": "2be6cb886b85f10e031a97db3efa0d863832874c29b1615590f76c8424021af6",
    "tests/ci_google33/historical32-report-nodeids.json": "4bcfd2d3f323e6aaf8ab944d7de62c1872817b6e1a8e82d809a15528fb8bb5af",
    "tests/ci_google33/history.py": "678218bd35eef110d273d449d2febe158fcfe9533ceae146fe395db20a34387f",
    "tests/ci_google33/identity_fixtures.py": "0274b1ab5cee93c323e97aedb904515611378b426da91968594ad17ea1f7e561",
    "tests/ci_google33/image_inventory.py": "4c1ad0bde23999fed90fb1df6cf8e9d7ee64d8c6d8d64e31c9e174d36ae4da1c",
    "tests/ci_google33/image_roles.py": "0ebe69d1ff313c44d78b85651fcfdb9f875bde40d5f9ca8c57e73f488b10c5a2",
    "tests/ci_google33/normalize_vm.py": "c41cd0a1ad342cb6f98e8c865cfdce7724b8d54283fe54797c787c773e486a22",
    "tests/ci_google33/offline.py": "f0520679702491e80c01390af959f89cd3fd8a6a14b22d08a4973f39b0ba853d",
    "tests/ci_google33/owned.py": "820cb770fd572abed1026a8a8e2fcbb9f5cf5cbce8c9588b9daddd89bab20069",
    "tests/ci_google33/owned_portable.py": "f4443423041409d0652e34ac043d29a35a2f1c25b6e4167b14cf59a3b7eae407",
    "tests/ci_google33/pg_observer.py": "ca55e3fbb33b9fe35e7aa91cffa7e0cae6b413dd9c464dd4486812fe6cf9f634",
    "tests/ci_google33/physical.py": "56dad92e855162cd8d0e73f8b6e80ccb78e87d0d257b2e26a2300132972f62a1",
    "tests/ci_google33/publish.py": "c91a4d6ef3ebe3b0d1522f3415831a8c2def942c2abe8d0a2a46b49e9a4127db",
    "tests/ci_google33/r05-critical49.json": "945f2ba07ddd6c975c6194130c1ba3435e93bbc449d7b1a724fbac5a9d8638ee",
    "tests/ci_google33/r05-full110.json": "75f614af3405eae405b658fa385dd310b7de31ad46e31be33b1d852652a4f494",
    "tests/ci_google33/resource_guard.py": "0965fc747606e81b08e7a0c0979c6cdf3f641075e30e6ca077acceeecaa7c7b7",
    "tests/ci_google33/run_current_browser.py": "6664f87aab2db016772ebbeee0e234fb6aa2c2e4abbaf6ff014dc93777326ed4",
    "tests/ci_google33/run_postgres.py": "bf5d4cd95b8c2ab7442ae4355b62b97c22319050f90b0985e749c0672776f605",
    "tests/ci_google33/witness.py": "864ddeba22563c03afc1c39ec6f93472204f45aea28ba698155c4c11d2a3010e",
    "tests/ci_google33/workflow.py": "9110aebfdea0ea5f2ff6d6c8bc43825e153fb24bcb0c4507969167efed75bbc2",
    "tests/current_google33_publication_fixtures.py": "19b14730043c5a74c77c9713722fce2627e949f0fd28e52e12258dd39d7ae8a0",
    "tests/e2e/current33_export_context.cjs": "6bb404618bdef6a1df99c3d6c2f17c2517f8661b55f6b6f937a875d42af443e8",
    "tests/e2e/current33_export_controls.cjs": "c44458d6e914acc1d32fc624dfdca87d66a70071deebdfa47ef78170290622fb",
    "tests/e2e/current33_member_link_export.cjs": "d3c526d7d14b897b5ea7da02c570b0297519204789dff4feef3d2f360d4db5be",
    "tests/e2e/daily_plan33_browser.cjs": "317895b8cae48ac6d0f586f2fa3ccc2b05e1041837e6bbd7b71606d6a4ebed6e",
    "tests/e2e/daily_plan33_server.py": "cf9b7dd16a124b70acd20af530dd2632943a6da23664139494f0a9860b418469",
    "tests/e2e/dashboard_followup33_browser.cjs": "90847bdadc9f3277e9ac398b2db771749dfe01899c22c436425b7b06914eb531",
    "tests/e2e/followup33_server.py": "5610ae65898e245fb04949ed65ac4c1798f9296690a2f4cae23269e4c1a748e2",
    "tests/e2e/member_link33_postgres_server.py": "feb294dcb5c3563fc93813ed755a57714f7623fcd6dd916ad8742f49ebdb158a",
    "tests/e2e/mfa33_ui_server.py": "74a5ea580dcd2e13094c1ebac2d574d5df8995a2a0bf1ba6a5de573ba1ede8f0",
    "tests/e2e/mfa_personal33_browser.cjs": "645625e0272896ab1c7b2e038387166bd2d1371b52ceec24f21384565d779991",
    "tests/e2e/mfa_ui33_browser.cjs": "561176a8ee48f87cd0e1db343e28e82b9e793a96ae22cecdcc66ef4b30167c86",
    "tests/e2e/run_member_link33_browser.py": "0e886f0ac82cebd21664d6cd243e743e2c76f16708627b2153d5587f4f13b95d",
    "tests/google33_identity_contract.py": "394e4382e9e3b101e3c6f5a0e8db497e8e9aa0f908cdcd8aa2f52462502fee78",
    "tests/google33_mfa_reauth_contract.py": "f18e275a265bbb5e22a00078fa9055e16976837aadac6adcdba2ed202d3d5805",
    "tests/integration_current33_diary.py": "16e7761eada36d5b2d6e3f47212c3f466a413b33e3ad5b7b25dd24b9c2cbf7fd",
    "tests/integration_current33_followup.py": "a32a336f877abda8874fc1cd306930280d5e24964bc1fa119ddfc70b83846cb7",
    "tests/integration_current33_google_conflict_window.py": "409d453e7044c7ef9f634d18e41c93ab04cfa500eddda24c5abbd2837a9b045a",
    "tests/integration_current33_google_signup_races.py": "de85e39ac07fb46e5d297ca2c8117d7c6082723c27786a79021add517869938b",
    "tests/integration_current33_member_http.py": "7fa7916425eb7705d5d77f0d5d507076ecc5866cc6c0774b0e4d479517433264",
    "tests/integration_current33_member_races.py": "682bb19c231e7fa70f3080127eb965f100d62769473ab6671bbad42ff0a115ee",
    "tests/integration_current33_member_services.py": "35a207c62f81c980c8c0a36ada263ca6f8fbd48d0817f27a6768b08d197996a1",
    "tests/integration_current33_mfa_postgres.py": "7aef49e434ed1576aa607ce54df74efcb4c11baf2087d53149d6888613eec263",
    "tests/integration_current33_privacy.py": "f90b1102ab5732c06d13ccbfa05076f7d0725c051881f94193708dd335ac9277",
    "tests/integration_current33_progress_adversarial.py": "cec37d31422b17e5718af15695a1bead11adc7aeba14722ff228db4d330619ab",
    "tests/integration_current33_progress_postgres.py": "ea8e7c4e43c8b1f869b4ff010fde5acdd8af090a1c5f53fac662affb8c34a86f",
    "tests/integration_current33_progress_retirement.py": "6cc364aef66c7ccb77a0fdb09b9f7405356f1df9fe1192c8bb469017a9487e4d",
    "tests/integration_current33_r24_publication.py": "ddd83f3f9cdf1cfa869b69ec8ab843415a3c6146183145cd88d994fcfbbc3ce5",
    "tests/integration_current33_r24_race.py": "d25b5eca2cea8dd333a9df107e980b78a5bad095ea274d5a462acecc5a5ebb12",
    "tests/integration_current33_rls.py": "dbf9dccdc0592ee66827b7926f3fce99eb1736d12f530fafa22e9d02a7a6b714",
    "tests/test_ci33_autodiscovery.py": "6972fce474c9cf3f645f4ae07957976b64f2399731c0c3ba7f1e70ce1ba1c541",
    "tests/test_ci33_collection.py": "29a000169504105562b8bb4373a99d2323358b7be864a20714ddbb4d2e3d489d",
    "tests/test_ci33_offline_preparation.py": "7a652d3f588937c3b9ae99bedad15cf4c50bc33246232650c16ecb26f2014d5f",
    "tests/test_ci33_reports.py": "32a3a26d344e618d48a1274014d4e424c5f599806a1caa941d3ed7435b9b1dc7",
    "tests/test_ci33_resource_boundaries.py": "e3957a77b7b7df526ac963dfaab60c17fe6d2c5c12631fa8f93208f758138476",
    "tests/test_ci33_vm_normalization.py": "0887bb8607e60fac10e50f159b3468dd3447982bc4b4d5def4a9ff6230a71138",
    "tests/test_current_mfa31_fixture_clock.py": "3be72916544c7e4cf4a26f192bfbec65f2b71c79a80218a2e582064243d62c0f",
    "tests/test_current_publication_fixture_review.py": "bb8505e04e6fed5dfe7914120064f7f3dca5c66c4d8c54b628fa5a19ade8395c",
    "tests/test_google33_conflict_window.py": "47d066e94998c632952467507b4e7324a935f567978593ab6c99d787d15e0bf6",
    "tests/test_google33_headers.py": "f639ecf7d2ab2ee626edbf4cd230ce4eaf7be2207684d69a2dae733953f80882",
    "tests/test_identity_security.py": "cb183248563d60b27b35f4b067e2d9c625b9248171345e413e8c0f3a998cc01e",
    "tests/test_mfa31_google_reauth.py": "043bfc6bd434d591da411431afa76c5ec202e838e2c9edf84c9569e3da50bfcf",
    "tests/test_publication_diary_consumption.py": "f525cf54fbecdb4b6c15810464dda0581805da1117d66f437e9914f299e352a4",
    "web/services/google_link.py": "7eefa0329d6ff653199fe2f7c5af4d413bd6a5a9093c549c950970c915e659ab"
}


def normalized(path):
    return path.read_bytes().replace(b'\r\n', b'\n')


def require(value, message):
    if not value:
        raise ValueError(message)


def verify_report_checker(path):
    require(path.is_file() and not path.is_symlink() and path.resolve() == path.absolute(), 'Report checker executable is missing or aliased')
    require(hashlib.sha256(normalized(path)).hexdigest() == REPORT_CHECKER_SHA256,
            'Report checker executable differs from the frozen complete implementation')


def verify_workflow(actual):
    from tests.ci_google33.workflow import expected_workflow
    require(actual == expected_workflow(), 'CI33 differs from the complete versioned/current workflow')


def workflow_canaries(workflow):
    rows = []
    for job in workflow['jobs']:
        mutant = copy.deepcopy(workflow)
        del mutant['jobs'][job]
        try:
            verify_workflow(mutant)
        except ValueError:
            rows.append('missing-job-' + job)
        else:
            raise AssertionError('A required versioned/current job disappeared')
    for job, value in workflow['jobs'].items():
        for index, step in enumerate(value['steps']):
            if 'run' not in step and not step.get('uses', '').startswith('actions/upload-artifact@'):
                continue
            mutant = copy.deepcopy(workflow)
            del mutant['jobs'][job]['steps'][index]
            try:
                verify_workflow(mutant)
            except ValueError:
                rows.append('missing-gate-' + job + '-' + str(index))
            else:
                raise AssertionError('A run/upload gate disappeared')
    for job, key, replacement in [('current-postgres', 'path', '**/*'), ('historical32-postgres', 'path', '**/*.raw.log')]:
        mutant = copy.deepcopy(workflow)
        mutant['jobs'][job]['steps'][-1]['with'][key] = replacement
        try:
            verify_workflow(mutant)
        except ValueError:
            rows.append('reject-raw-publication-' + job)
        else:
            raise AssertionError('Unreviewed RAW upload passed')
    return rows


def git_source(revision, name):
    return subprocess.check_output(['git', '--no-replace-objects', 'show', revision + ':' + name], cwd=ROOT).replace(b'\r\n', b'\n')


def functions(raw):
    return {n.name: n for n in ast.parse(raw).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def verify_contract_mappings():
    body_map = json.loads((ROOT / 'tests/ci_google33/contract-body-map.json').read_bytes())
    assertion_counts = {}
    for label, group in body_map.items():
        before = git_source(group['base'], group['original_path']).decode()
        after = normalized(ROOT / group['provider_path']).decode()
        of, nf = functions(before), functions(after)
        assertions = 0
        for item in group['functions']:
            name = item['function']
            old = ast.get_source_segment(before, of[name])
            new = ast.get_source_segment(after, nf[name])
            require(old == item['original_function_source'] and new == item['current_function_source'], 'Complete Google contract body mapping differs')
            collect = lambda text: [ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Assert)]
            require(collect(old.replace('https://oauth2.googleapis.com/tokeninfo', 'https://www.googleapis.com/oauth2/v3/certs')) == collect(new), 'An original Google business assertion changed')
            assertions += len(collect(new))
        assertion_counts[label] = assertions
    require(assertion_counts == {'identity': 7, 'MFA': 8}, 'Original Google assertion scope differs')
    framing = json.loads((ROOT / 'tests/ci_google33/SSR-framing-map.json').read_bytes())
    original = git_source(framing['base'], framing['source'])
    current = normalized(ROOT / framing['source'])
    require(hashlib.sha256(original).hexdigest() == framing['before_normalized_sha256'], 'Original SSR framing differs')
    require(hashlib.sha256(current).hexdigest() == framing['after_normalized_sha256'], 'Current exact SSR framing differs')
    inverse = current.decode()
    for before, after in reversed(framing['pairs']):
        require(inverse.count(after) == 1, 'SSR inverse pair is ambiguous')
        inverse = inverse.replace(after, before)
    require(inverse.encode() == original, 'Complete SSR inverse differs')
    return assertion_counts


def verify_current_sources():
    from tests.ci_google33.history import specification, specifications
    from tests.ci_google33.offline import validate_frames
    from tests.run_reviewed_ci30 import trusted_baseline
    baseline = trusted_baseline()
    require(bool(TRUSTED_SOURCES), 'CI33 trust pins have not been frozen')
    for name, expected in TRUSTED_SOURCES.items():
        path = ROOT / name
        require(path.is_file() and not path.is_symlink() and hashlib.sha256(normalized(path)).hexdigest() == expected,
                'CI33 source or review mapping differs: ' + name)
    require(len(validate_frames()) == 35, 'Full adapter/browser frame inventory differs')
    for schema, spec in specifications().items():
        specification(ROOT, spec)
    composition = json.loads((ROOT / 'tests/ci_google33/approved-composition.json').read_bytes())
    imports = composition['ROOT_QA17_imports']
    require(set(imports) == {'web/services/google_link.py', 'tests/test_google33_conflict_window.py'}, 'Approved ROOT QA17 import scope differs')
    for name, receipt in imports.items():
        require(receipt['source_commit'] == '8a5e5dc235e96a47488befb743fc02a24b491939', 'Approved ROOT QA17 freeze differs')
        require(hashlib.sha256(normalized(ROOT / name)).hexdigest() == receipt['normalized_sha256']
                and hashlib.sha256(git_source(receipt['source_commit'], name)).hexdigest() == receipt['raw_git_sha256'],
                'An approved ROOT import changed')
    changed = subprocess.check_output(['git', 'diff', '--name-only', '3587b3b3eee3a58367624472d7c0683baa8f10e0'], cwd=ROOT).decode().splitlines()
    require(all(name.startswith(('tests/', 'docs/implementation/20261018-evolution/evidence/qa-ci33-'))
                or name == '.github/workflows/ci.yml' or name in imports for name in changed), 'CI33 delta changed product, dependencies or historical targets')
    assertions = verify_contract_mappings()
    from tests.isolation import block_external_sockets, prepare_environment
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    from web.database.models import Base
    from web.database.schema_control import expected_head
    require(expected_head() == '20261019_google_subjects' and len(Base.metadata.tables) == 35, 'Current33 source ORM/revision differs')
    return {'immutable_CI30_helpers': len(baseline['helpers23_sha256']), 'adapter_inverse_frames': 35,
            'current_source_revision': expected_head(), 'ORM_tables_source_only': 35,
            'Google_original_assertions': assertions, 'PostgreSQL_executed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--workflow', type=Path, default=ROOT / '.github/workflows/ci.yml')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    # Check the entire executable before importing any checker acceptance API.
    verify_report_checker(ROOT / 'tests/check_google33_reports.py')
    source = verify_current_sources()
    import yaml

    from tests.ci_google33.run_postgres import private_directory
    workflow = yaml.safe_load(args.workflow.read_bytes())
    verify_workflow(workflow)
    require(not args.output.absolute().is_relative_to(ROOT), 'Offline review must be outside source')
    output = private_directory(args.output)
    report = {'scope': 'Offline source/wiring/parser/CLI only; no PG/image/Chromium/Actions/provider claim',
        'source': source, 'workflow_canaries': workflow_canaries(workflow),
        'historical31_counted_as_current33': False, 'current33_required_PG_nodes': 240,
        'historical32_required_PG_nodes': 38}
    bash = os.environ.get('METODOBASE_CI_BASH') or ('C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash'))
    require(bool(bash), 'Bash is required for the complete workflow syntax gate')
    blocks = [step['run'] for job in workflow['jobs'].values() for step in job['steps'] if 'run' in step]
    for index, block in enumerate(blocks):
        # Actions expressions are evaluated by the runner before Bash sees them.
        rendered = re.sub(r'\$\{\{.*?\}\}', 'synthetic-actions-value', block)
        result = subprocess.run([bash, '-n'], input=rendered.encode(), capture_output=True, timeout=15, check=False)
        require(result.returncode == 0, 'CI33 Bash block does not parse: ' + str(index))
    refs = sorted(set(re.findall(r'(?:scripts|tests)/[A-Za-z0-9_./-]+\.(?:py|cjs)', args.workflow.read_text(encoding='utf8'))))
    require(all((ROOT / name).is_file() for name in refs), 'A workflow runner/helper reference is missing')
    report.update(bash_blocks=len(blocks), workflow_source_references=refs)
    if not args.verify_only:
        argv = [sys.executable, '-X', 'utf8', '-B', 'tests/run_isolated.py',
            'tests/test_mfa31_ci_trust.py', 'tests/test_ci33_offline_preparation.py',
            'tests/test_ci33_autodiscovery.py', 'tests/test_ci33_collection.py', 'tests/test_ci33_reports.py',
            'tests/test_ci33_resource_boundaries.py',
            'tests/test_ci33_vm_normalization.py',
            'tests/test_google33_conflict_window.py',
            'tests/test_secret_scan_reviewed_locations.py', 'tests/test_secret_scan_fragment_pins.py',
            'tests/test_secret_scan_safety.py',
            '-q', '--tb=short', '--junitxml=' + str(output / 'offline-canaries.xml')]
        with (output / 'offline-canaries.raw.log').open('xb') as raw:
            result = subprocess.run(argv, cwd=ROOT, stdout=raw, stderr=subprocess.STDOUT, timeout=420, check=False)
        require(result.returncode == 0, 'CI33 offline canary failed; first RAW is retained')
        report['offline_canaries_exit'] = 0
    (output / 'review.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
    print(json.dumps({'workflow_canaries': len(report['workflow_canaries']), 'bash_blocks': len(blocks),
        'current33_PG_nodeIDs_only': 240, 'historical32_PG_nodeIDs_only': 38, 'offline_only': True}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
