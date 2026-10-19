"""Synthetic parser/CLI counterexamples; these never claim a PG execution."""
from __future__ import annotations

import ast
import copy
import io
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from tests import check_google33_reports as checker
from tests.ci_google33 import publish, witness

REPORTS = [('33', name) for name in checker.required_reports('33')] + [('32', name) for name in checker.required_reports('32')]


def measured(schema='33', *, pool=1, transition=False, previous=False):
    revision = witness.REVISION[str(int(schema) - 1) if previous else schema]
    tables = {'31': 33, '32': 34, '33': 36}[str(int(schema) - 1) if previous else schema]
    common = {'database_kind': 'postgresql', 'runtime_revision': revision, 'actual_tables': tables,
              'role_flags4': [False] * 4, 'owned_tables': 0, 'application_pool_size': pool, 'blank_GUCs': True}
    if transition:
        return {**common, 'database_nonowner': True, 'schema_sha256': 'a' * 64}
    model, _tables, functions, triggers = witness.COUNTS[schema]
    return {**common, 'model_tables': model, 'application_role_restricted_nonowner': True,
            'FORCE_RLS_tables': 26, 'signed_functions': functions, 'signed_triggers': triggers,
            'foreign_keys_validated': True, **{key: 'a' * 64 for key in witness.HASHES},
            'global_contract_sha256': witness.CONTRACT_HASHES[schema]}


def reports(directory, schema):
    directory.mkdir(exist_ok=True)
    for name, required in checker.required_reports(schema).items():
        root = ET.Element('testsuites')
        suite = ET.SubElement(root, 'testsuite', name='pytest', tests=str(len(required)), failures='0', errors='0', skipped='0')
        cases = []
        for module, node in sorted(required):
            ET.SubElement(suite, 'testcase', classname=module, name=node)
            migration = '_migrations' in module
            previous = migration and any(p in node for p in ('predecessor_drift', 'mid_migration_failure'))
            cases.append({'identity': [module, node], 'phase': 'after_business_before_teardown',
                'measurements': [measured(schema, pool=6 if module == 'tests.integration_current33_r24_race' else 1,
                    transition=migration, previous=previous)], 'measurement_sources': ['business_fixture_engine']})
        ET.ElementTree(root).write(directory / name, encoding='utf8', xml_declaration=True)
        (directory / name.replace('.xml', '.witnesses.json')).write_text(json.dumps({'schema': schema, 'cases': cases}), encoding='utf8')


def cli(directory, schema, path=None):
    return subprocess.run([sys.executable, '-X', 'utf8', '-B', str(path or checker.__file__),
        '--schema', schema, '--directory', str(directory)], capture_output=True, timeout=20, check=False)


@pytest.mark.parametrize('schema,total', [('33', 240), ('32', 38)])
def test_complete_synthetic_identity_and_measured_metadata_acceptance(schema, total, tmp_path):
    reports(tmp_path, schema)
    assert checker.validate(tmp_path, schema) == total
    result = cli(tmp_path, schema)
    assert result.returncode == 0 and json.loads(result.stdout)['passed_nodes'] == total


@pytest.mark.parametrize('schema,report', REPORTS)
@pytest.mark.parametrize('mode', ['absent', 'empty', 'missing', 'duplicate', 'substituted', 'sqlite',
                                  'failure', 'error', 'skipped', 'declared', 'dtd'])
def test_every_report_boundary_rejects_identity_state_and_dialect_reductions(schema, report, mode, tmp_path):
    reports(tmp_path, schema)
    path = tmp_path / report
    if mode == 'absent':
        path.unlink()
    elif mode == 'empty':
        path.write_bytes(b'')
    elif mode == 'dtd':
        path.write_bytes(b'<!DOCTYPE testsuites><testsuites/>')
    else:
        root = ET.parse(path).getroot()
        suite = root.find('testsuite')
        case = suite.find('testcase')
        if mode == 'missing':
            suite.remove(case)
        elif mode == 'duplicate':
            suite.append(ET.fromstring(ET.tostring(case)))
        elif mode == 'substituted':
            case.set('name', 'test_unrelated_smoke[postgresql]')
        elif mode == 'sqlite':
            case.set('name', case.get('name').replace('postgresql', 'sqlite') + '-wrong-dialect')
        elif mode in {'failure', 'error', 'skipped'}:
            ET.SubElement(case, mode)
        elif mode == 'declared':
            suite.set('tests', str(len(suite.findall('testcase')) + 1))
        ET.ElementTree(root).write(path, encoding='utf8')
    with pytest.raises((OSError, ValueError, ET.ParseError)):
        checker.validate(tmp_path, schema)
    result = cli(tmp_path, schema)
    assert result.returncode == 1 and not result.stdout


@pytest.mark.parametrize('schema,report', REPORTS)
@pytest.mark.parametrize('mode', ['absent', 'duplicate', 'wrong_revision', 'owner', 'bool_count', 'extra', 'unsigned', 'signature', 'foreign_case'])
def test_every_report_requires_closed_exact_runtime_observation(schema, report, mode, tmp_path):
    reports(tmp_path, schema)
    path = tmp_path / report.replace('.xml', '.witnesses.json')
    if mode == 'absent':
        path.unlink()
    else:
        value = json.loads(path.read_bytes())
        row = value['cases'][0]
        measurement = row['measurements'][0]
        if mode == 'duplicate':
            value['cases'].append(copy.deepcopy(row))
        elif mode == 'wrong_revision':
            measurement['runtime_revision'] = 'historical30-does-not-prove33'
        elif mode == 'owner':
            measurement['role_flags4'][0] = True
        elif mode == 'bool_count':
            measurement['application_pool_size'] = True
        elif mode == 'extra':
            measurement['unreviewed'] = 'synthetic-private-marker'
        elif mode == 'unsigned':
            key = 'schema_sha256' if '_migrations' in row['identity'][0] else 'functions_sha256'
            measurement[key] = ''
        elif mode == 'signature':
            key = 'schema_sha256' if '_migrations' in row['identity'][0] else 'global_contract_sha256'
            measurement[key] = '' if key == 'schema_sha256' else 'b' * 64
        elif mode == 'foreign_case':
            row['identity'][1] = 'test_wrong_case'
        path.write_text(json.dumps(value), encoding='utf8')
    with pytest.raises((OSError, ValueError, KeyError)):
        checker.validate(tmp_path, schema)
    result = cli(tmp_path, schema)
    assert result.returncode == 1 and not result.stdout


def test_false_success_main_is_reproduced_by_real_cli_then_rejected_by_source_pin(tmp_path):
    from tests.verify_google33_ci import verify_report_checker
    source = Path(checker.__file__).read_text(encoding='utf8')
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    lines = source.splitlines(keepends=True)
    mutant = ''.join(lines[:node.lineno - 1]) + 'def main():\n    return 0\n' + ''.join(lines[node.end_lineno:])
    path = tmp_path / 'false-success.py'
    path.write_text(mutant, encoding='utf8')
    result = cli(tmp_path, '33', path)
    assert result.returncode == 0 and not result.stdout
    with pytest.raises(ValueError, match='executable'):
        verify_report_checker(path)


@pytest.mark.parametrize('field', sorted(witness.FIELDS))
def test_browser_global_witness_cannot_omit_any_required_field(field):
    value = measured()
    del value[field]
    with pytest.raises(ValueError):
        witness.validate(value)


@pytest.mark.parametrize('private', [b'a' * 30 + b'.' + b'b' * 30,
                                  b'a' * 30 + b'.' + b'b' * 30 + b'.' + b'c' * 30,
                                  b'1234567890.' + b'a' * 64 + b'.' + b'b' * 64,
                                  b'otpauth://totp/Synthetic?secret=synthetic'])
def test_private_authentication_material_is_rejected_even_inside_expanded_zip(private):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('nested/private.txt', private)
    with pytest.raises(ValueError):
        publish.scan(buffer.getvalue())


def test_public_witness_preserves_closed_signatures_and_never_uploads_raw_log(tmp_path):
    raw = tmp_path / 'private'
    reports(raw, '33')
    name = next(iter(checker.required_reports('33'))).replace('.xml', '.witnesses.json')
    output = tmp_path / 'public'
    publish.publish(raw, output, [name])
    assert json.loads((output / name).read_bytes()) == json.loads((raw / name).read_bytes())
    (raw / 'unreviewed.raw.log').write_bytes(b'synthetic-private-log')
    with pytest.raises(ValueError):
        publish.publish(raw, tmp_path / 'public-bad', ['unreviewed.raw.log'])
