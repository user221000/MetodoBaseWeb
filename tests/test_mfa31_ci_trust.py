"""Offline CI31 trust/parser/publication canaries; no PG/browser/VM services."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

import pytest

from tests import check_mfa31_reports as checker
from tests import run_reviewed_ci30 as history
from tests.ci_mfa31 import publish
from tests.ci_mfa31 import run_current_browser as controller


def write_reports(directory):
    for name, required in checker.required_reports().items():
        root = ET.Element('testsuites')
        suite = ET.SubElement(root, 'testsuite', name='pytest', tests=str(len(required)),
                              failures='0', errors='0', skipped='0')
        for module, node in sorted(required):
            ET.SubElement(suite, 'testcase', classname=module, name=node)
        ET.ElementTree(root).write(directory / name, encoding='utf8', xml_declaration=True)


def test_all_exact_current31_nodes_are_required(tmp_path):
    write_reports(tmp_path)
    assert checker.validate(tmp_path) == 173


@pytest.mark.parametrize('report', tuple(checker.required_reports()))
@pytest.mark.parametrize('mode', ['absent', 'empty', 'missing', 'duplicate', 'substituted',
                                  'sqlite', 'failure', 'error', 'skipped', 'declared', 'dtd'])
def test_each_current31_boundary_rejects_reduction_or_substitution(tmp_path, report, mode):
    write_reports(tmp_path)
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
            case.set('name', case.get('name').replace('postgresql', 'sqlite') + '-not-the-required-node')
        elif mode in {'failure', 'error', 'skipped'}:
            ET.SubElement(case, mode)
        elif mode == 'declared':
            suite.set('tests', str(int(suite.get('tests')) + 1))
        ET.ElementTree(root).write(path, encoding='utf8', xml_declaration=True)
    with pytest.raises((ValueError, OSError, ET.ParseError)):
        checker.validate(tmp_path)


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'a//b', 'a/./b', 'a/../b', 'a\\b',
                                 'C:/drive', 'a:b', 'NUL', 'con.txt', 'COM1', 'lpt9.log',
                                 'a./b', 'a /b', 'a\x00b', 'a\nb', 'a\x7fb', 'a?b',
                                 'a*b', 'a<b', 'a>b', 'a|b', 'a"b', 'e\u0301/file'])
def test_historical_materializer_rejects_cross_platform_path_aliases(name):
    with pytest.raises(ValueError):
        history.canonical_name(name)


def test_historical_materializer_accepts_ordinary_git_spelling():
    assert history.canonical_name('tests/ci_mfa31/ci30-before.yml') == 'tests/ci_mfa31/ci30-before.yml'


def test_historical_baseline_cannot_self_update_its_digest(tmp_path, monkeypatch):
    folder = tmp_path / 'tests/ci_mfa31'
    folder.mkdir(parents=True)
    original = json.loads((history.ROOT / 'tests/ci_mfa31/baseline.json').read_bytes())
    original['workflow_sha256'] = '0' * 64
    (folder / 'baseline.json').write_text(json.dumps(original), encoding='utf8')
    monkeypatch.setattr(history, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='trust metadata'):
        history.trusted_baseline()


def test_historical_output_must_be_unused(tmp_path):
    with pytest.raises(ValueError, match='already exists'):
        history.new_directory(tmp_path)


@pytest.mark.parametrize('value', [b'A' * 43 + b'.' + b'b' * 64,
                                  b'A' * 43 + b'.' + b'B' * 43 + b'.' + b'C' * 43,
                                  b'otpauth://totp/synthetic', b'{"recovery_codes":["withheld"]}'],
                         ids=['signed-opaque-two-parts', 'jwt-three-parts', 'otp-uri', 'recovery-field'])
def test_publication_rejects_two_part_and_three_part_tokens_and_factors(value):
    with pytest.raises(ValueError):
        publish.scan(value)


def test_publication_scans_expanded_zip_members():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('report.txt', b'A' * 43 + b'.' + b'b' * 64)
    with pytest.raises(ValueError):
        publish.scan(stream.getvalue())


def test_publication_scans_zip_with_a_leading_preamble():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('report.txt', b'A' * 43 + b'.' + b'b' * 64)
    with pytest.raises(ValueError):
        publish.scan(b'approved-looking preamble\n' + stream.getvalue())


def test_publication_rejects_the_actual_product_csrf_three_part_function():
    from web.middleware.csrf import generate_csrf_token
    value = generate_csrf_token('synthetic-ci31-scanner-key-at-least-32-characters').encode('ascii')
    assert publish.CSRF.fullmatch(value)
    with pytest.raises(ValueError):
        publish.scan(value)


def test_public_junit_keeps_failure_status_and_withholds_private_diagnostics():
    raw = b'<testsuites><testsuite name="pytest" tests="1" failures="1" errors="0" skipped="0"><testcase classname="safe" name="safe"><failure message="private">withheld-sensitive-body</failure><system-out>private stdout</system-out></testcase></testsuite></testsuites>'
    projected = publish.xml_projection(raw)
    publish.scan(projected)
    assert b'withheld-sensitive-body' not in projected and b'private stdout' not in projected
    assert len(ET.fromstring(projected).findall('.//failure')) == 1


def test_public_junit_withholds_a_factor_embedded_in_a_parameter_identity():
    secret = 'A' * 43 + '.' + 'b' * 64
    root = ET.Element('testsuites')
    suite = ET.SubElement(root, 'testsuite', name='pytest', tests='1', failures='1', errors='0', skipped='0')
    case = ET.SubElement(suite, 'testcase', classname='safe', name='test_factor[' + secret + ']')
    ET.SubElement(case, 'failure', message=secret)
    result = publish.xml_projection(ET.tostring(root))
    publish.scan(result)
    assert secret.encode() not in result and len(ET.fromstring(result).findall('.//failure')) == 1


def test_json_publication_uses_only_structural_counters(tmp_path):
    private = tmp_path / 'private'
    private.mkdir()
    secret = 'A' * 43 + '.' + 'b' * 64
    (private / 'report.json').write_text(json.dumps({'total': 2, 'passed': 2,
        'private_factor': secret, 'checks': ['first', 'second']}), encoding='utf8')
    output = tmp_path / 'public'
    result = publish.publish(private, output, ['report.json'])
    assert len(result) == 1 and secret.encode() not in (output / 'report.json').read_bytes()
    assert json.loads((output / 'report.json').read_bytes())['checks_count'] == 2


def test_owned_inert_fixture_closes_after_a_gate_exception(tmp_path):
    stop = tmp_path / 'stop'
    code = 'from pathlib import Path\nimport time\np=Path(' + repr(str(stop)) + ')\nwhile not p.exists():time.sleep(.01)\n'
    with pytest.raises(ValueError, match='inert gate'):
        with controller.fixture([sys.executable, '-B', '-c', code], tmp_path, 'inert', dict(os.environ), stop) as process:
            raise ValueError('inert gate')
    assert stop.is_file() and process.poll() == 0


def test_owned_inert_fixture_unexpected_exit_cannot_be_accepted(tmp_path):
    with pytest.raises(AssertionError, match='finalizer failed'):
        with controller.fixture([sys.executable, '-B', '-c', 'raise SystemExit(7)'], tmp_path,
                                'nonzero', dict(os.environ), tmp_path / 'stop') as process:
            process.wait(timeout=10)
    assert process.returncode == 7


def test_current_fixture_wrong_real_marker_is_not_readiness(tmp_path):
    stop = tmp_path / 'stop'
    code = 'from pathlib import Path\nimport time\np=Path(' + repr(str(stop)) + ')\nwhile not p.exists():time.sleep(.01)\n'
    with controller.fixture([sys.executable, '-B', '-c', code], tmp_path, 'marker', dict(os.environ), stop) as process:
        with pytest.raises(TimeoutError):
            controller.wait_ready(process, 8765, lambda: {'pid': process.pid, 'runtime_revision': 'wrong'},
                                  controller.validate_pg_marker, timeout=.2)
    assert process.returncode == 0
