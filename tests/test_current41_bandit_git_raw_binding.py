"""The current complete Git frame preserves the historical -text publication RAW."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from tests.ci_web39 import bandit_review, quality

ROOT = Path(__file__).resolve().parents[1]
RAW = 'tests/ci_image57/fixtures/publication.py.RAW'
ATTR = 'tests/ci_image57/fixtures/.gitattributes'
RAW_SHA = 'ee0820ff6f4758ddf87af2202979a8ddba8c81e4a79a516fae0f42ede1221df9'
RAW_OID = '48666ec6af7d01916ee38189f3796db4c5e556ee'
OLD_VIRTUAL_SHA = 'c91a4d6ef3ebe3b0d1522f3415831a8c2def942c2abe8d0a2a46b49e9a4127db'
OLD_VIRTUAL_OID = '7184592235773201ab7d333143022f10970fc541'


@pytest.fixture(scope='module', autouse=True)
def database_schema():
    """These source/provenance controls use no database or application runtime."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw,
                        usedforsecurity=False).hexdigest()


@pytest.fixture(scope='module')
def proposal():
    return json.loads((ROOT / quality.PROPOSAL).read_bytes())


@pytest.fixture(scope='module')
def finite_report():
    source = ROOT / 'tests/ci_web39/fixtures/bandit32-current095-fixture.json'
    raw = source.read_bytes()
    assert len(raw) == 46259 and digest(raw) == '76470a29289912ea763237136bf9cc465822bedc14c0ee651e44ac0084e90336'
    report = json.loads(raw)['report']
    baseline = json.loads((ROOT / 'tests/bandit-reviewed-baseline.json').read_bytes())
    excluded = {row['fingerprint'] for row in baseline['exceptions']}
    findings = [row for row in report['results'] if quality.fingerprint(row) not in excluded]
    assert len(findings) == 26
    return {'errors': [], 'results': findings}


def exact_frame(source, pin, variant):
    # Fixture construction proves an entire declared frame before it copies
    # anything. Production admission never normalizes or edits a source byte.
    known = {pin['captured_main_raw_sha256'], pin['authenticated_git_objects_sha256']}
    assert digest(source) in known
    lf = source.replace(b'\r\n', b'\n')
    candidates = (source, lf, lf.replace(b'\n', b'\r\n'))
    expected = pin[variant + '_sha256']
    selected = next(raw for raw in candidates if digest(raw) == expected)
    length = pin['captured_bytes'] if variant == 'captured_main_raw' else pin['git_bytes']
    assert len(selected) == length
    if variant == 'authenticated_git_objects':
        assert blob(selected) == pin['git_blob']
    return selected


@pytest.fixture(scope='module')
def frames(tmp_path_factory, proposal):
    roots = {}
    assert len(proposal['bindings']) == 392
    for variant in ('captured_main_raw', 'authenticated_git_objects'):
        root = tmp_path_factory.mktemp('bandit392-' + variant)
        for name, pin in proposal['bindings'].items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(exact_frame((ROOT / name).read_bytes(), pin, variant))
        roots[variant] = root
    return roots


def validate(report, root, proposal):
    return bandit_review.validate_candidate(report, root, proposal,
        context=quality.REVIEW_CONTEXT, bandit_version='1.9.4')


@contextmanager
def changed(path, content):
    before = path.read_bytes() if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    try:
        yield
    finally:
        if before is None:
            path.unlink()
        else:
            path.write_bytes(before)


def test_publication_git_binding_is_its_actual_untouched_raw_object(proposal):
    actual = (ROOT / RAW).read_bytes()
    assert len(actual) == 12973 and digest(actual) == RAW_SHA and blob(actual) == RAW_OID
    assert actual.count(b'\r\n') == 230
    assert (ROOT / ATTR).read_bytes() == (
        b'* -text whitespace=cr-at-eol\n'
        b'runtime_probe57-69d49.py.RAW whitespace=-blank-at-eol,cr-at-eol\n')
    assert proposal['bindings'][RAW] == {
        'captured_main_raw_sha256': RAW_SHA, 'captured_bytes': 12973,
        'authenticated_git_objects_sha256': RAW_SHA, 'git_bytes': 12973, 'git_blob': RAW_OID}
    normalized = actual.replace(b'\r\n', b'\n')
    assert len(normalized) == 12743 and digest(normalized) == OLD_VIRTUAL_SHA
    assert blob(normalized) == OLD_VIRTUAL_OID != RAW_OID


@pytest.mark.parametrize('variant', ['captured_main_raw', 'authenticated_git_objects'])
def test_both_complete392_frames_keep_the_same26_exact_occurrences(frames, proposal, finite_report, variant):
    result = validate(finite_report, frames[variant], proposal)
    assert result['source_variant'] == variant
    assert result['reviewed_occurrences'] == 26
    assert result['approved'] is False and result['exceptions_applied'] == 0


def test_old_virtual_git_frame_is_not_the_actual_publication_object(frames, proposal, finite_report):
    root = frames['authenticated_git_objects']
    virtual = (root / RAW).read_bytes().replace(b'\r\n', b'\n')
    assert digest(virtual) == OLD_VIRTUAL_SHA
    with changed(root / RAW, virtual), pytest.raises(ValueError, match='entire reviewed RAW universe'):
        validate(finite_report, root, proposal)


@pytest.mark.parametrize('variant', ['captured_main_raw', 'authenticated_git_objects'])
def test_one_unapproved_mix_cannot_substitute_for_either_complete_universe(frames, proposal, finite_report, variant):
    name = next(name for name, pin in proposal['bindings'].items()
                if name != RAW and pin['captured_main_raw_sha256'] != pin['authenticated_git_objects_sha256'])
    other = 'authenticated_git_objects' if variant == 'captured_main_raw' else 'captured_main_raw'
    with changed(frames[variant] / name, (frames[other] / name).read_bytes()), pytest.raises(
            ValueError, match='entire reviewed RAW universe'):
        validate(finite_report, frames[variant], proposal)


@pytest.mark.parametrize('fault', ['byte', 'length', 'old-oid', 'old-size', 'old-digest'])
def test_no_changed_raw_byte_or_wrong_declared_git_identity_is_admitted(frames, proposal, finite_report, fault):
    root = frames['authenticated_git_objects']
    data = deepcopy(proposal)
    if fault in {'byte', 'length'}:
        actual = (root / RAW).read_bytes()
        altered = bytes([actual[0] ^ 1]) + actual[1:] if fault == 'byte' else actual + b'\n'
        with changed(root / RAW, altered), pytest.raises(ValueError):
            validate(finite_report, root, data)
        return
    if fault == 'old-oid':
        data['bindings'][RAW]['git_blob'] = OLD_VIRTUAL_OID
    elif fault == 'old-size':
        data['bindings'][RAW]['git_bytes'] = 12743
    else:
        data['bindings'][RAW]['authenticated_git_objects_sha256'] = OLD_VIRTUAL_SHA
    with pytest.raises(ValueError):
        validate(finite_report, root, data)


@pytest.mark.parametrize('fault', ['missing-finding', 'duplicate-finding', 'new-caller'])
def test_the_binding_correction_does_not_weaken_report_or_caller_inventory(frames, proposal, finite_report, fault):
    root = frames['authenticated_git_objects']
    report = deepcopy(finite_report)
    if fault == 'missing-finding':
        report['results'].pop()
    elif fault == 'duplicate-finding':
        report['results'].append(deepcopy(report['results'][0]))
    else:
        with changed(root / 'api/unreviewed_policy_caller.py', b'from web.database import followup_policy\n'):
            with pytest.raises(ValueError, match='source file inventory'):
                validate(report, root, proposal)
        return
    with pytest.raises(ValueError, match='finding multiset'):
        validate(report, root, proposal)
