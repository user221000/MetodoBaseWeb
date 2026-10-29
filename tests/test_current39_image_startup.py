"""Negative inputs for the new real-image startup gate.

These controls execute no Docker daemon and make no claim of Linux startup.
"""
import ast
import copy
from types import CodeType, FunctionType, SimpleNamespace

import pytest

from tests.ci_image57 import current39_startup as gate

SOURCE = 'a' * 40
IMAGE = 'sha256:' + 'b' * 64
CONTAINER = 'c' * 64
OWNER = 'd' * 32


def configuration():
    return {
        'METODOBASE_TEST_MIGRATOR_URL':
            'postgresql+psycopg2://metodobase_test_admin:synthetic-admin@127.0.0.1:55483/metodobase_test_image',
        'METODOBASE_TEST_POSTGRES_URL':
            'postgresql+psycopg2://metodobase_test_app:synthetic-app@127.0.0.1:55483/metodobase_test_image',
    }


def image():
    return {'Id': IMAGE, 'Config': {'Labels': {'org.opencontainers.image.revision': SOURCE},
        'Cmd': ['/app/entrypoint.sh'], 'Entrypoint': None, 'User': 'appuser'}}


def witness():
    return {'revision': gate.REVISION, 'ORM_tables': 44, 'physical_tables': 45, 'FORCE_RLS': 35,
        'role_five_flags': [False] * 5, 'owned_tables': 0, 'uid': 999, 'pid1_main_web': True,
        'pid1_owns_ready_listener': True, 'owned_ready_HTTP_200': True,
        'migrator_absent': True, 'no_new_privileges': True, 'effective_capabilities': 0,
        'pool_size': 1, 'max_overflow': 0, 'source_hashes': {'entrypoint.sh': 'e' * 64}}


def host_config():
    return {'Memory': 512 * 1024**2, 'NanoCpus': 1000000000, 'PidsLimit': 128,
            'ReadonlyRootfs': True, 'NetworkMode': 'host', 'PidMode': '',
            'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges:true']}


def test_accepts_only_separate_explicit_synthetic_roles():
    assert gate.database_configuration(configuration()) == configuration()


@pytest.mark.parametrize('old,new', [
    ('127.0.0.1', 'example.com'), ('55483', '5432'),
    ('metodobase_test_image', 'metodobase_test_other'),
    ('metodobase_test_app:', 'metodobase_test_admin:'),
    ('synthetic-app', 'synthetic-app\nDATABASE_URL=postgresql://other'),
    ('metodobase_test_image', 'metodobase_test_image?options=-crole=owner'),
])
def test_rejects_remote_override_cross_target_and_role_alias(old, new):
    values = configuration()
    values['METODOBASE_TEST_POSTGRES_URL'] = values['METODOBASE_TEST_POSTGRES_URL'].replace(old, new)
    with pytest.raises(ValueError):
        gate.database_configuration(values)


def test_accepts_real_saas_image_configuration_by_id():
    gate.validate_image(image(), IMAGE, SOURCE)


@pytest.mark.parametrize('section,key,value', [
    ('root', 'Id', 'sha256:' + '0' * 64),
    ('Config', 'Cmd', ['python', 'api/app.py']),
    ('Config', 'User', '0'), ('Config', 'Entrypoint', ['/unexpected-wrapper']),
    ('Config', 'Labels', {'org.opencontainers.image.revision': '0' * 40}),
])
def test_rejects_source_tag_root_and_entrypoint_substitution(section, key, value):
    observed = image()
    (observed if section == 'root' else observed[section])[key] = value
    with pytest.raises(ValueError):
        gate.validate_image(observed, IMAGE, SOURCE)


def test_rejects_mutable_tag_even_if_inspect_echoes_it():
    with pytest.raises(ValueError):
        gate.validate_image(image(), 'metodobase:latest', SOURCE)


def test_accepts_container_with_exact_owner_and_image():
    value = {'Id': CONTAINER, 'Image': IMAGE, 'Config': {'Labels': {gate.OWNER_LABEL: OWNER}},
             'HostConfig': host_config(), 'State': {'Running': False, 'ExitCode': 0}}
    gate.validate_container(value, CONTAINER, IMAGE, OWNER)
    for key in ('Id', 'Image', 'Config'):
        other = copy.deepcopy(value)
        other[key] = {'Labels': {gate.OWNER_LABEL: 'wrong'}} if key == 'Config' else 'wrong'
        with pytest.raises(ValueError):
            gate.validate_container(other, CONTAINER, IMAGE, OWNER)


@pytest.mark.parametrize('key,bad', [('Memory', 0), ('NanoCpus', 0), ('PidsLimit', 0),
    ('ReadonlyRootfs', False), ('NetworkMode', 'bridge'), ('PidMode', 'host'),
    ('CapDrop', []), ('SecurityOpt', []), ('Memory', False)])
def test_rejects_missing_container_isolation_and_resource_limits(key, bad):
    value = {'Id': CONTAINER, 'Image': IMAGE, 'Config': {'Labels': {gate.OWNER_LABEL: OWNER}},
             'HostConfig': host_config(), 'State': {'Running': False, 'ExitCode': 0}}
    value['HostConfig'][key] = bad
    with pytest.raises(ValueError):
        gate.validate_container(value, CONTAINER, IMAGE, OWNER)


def test_accepts_complete_current39_schema_role_and_source_witness():
    gate.validate_witness(witness(), {'app_hashes': witness()['source_hashes']})


@pytest.mark.parametrize('key,value', [
    ('revision', '20261019_google_subjects'), ('ORM_tables', 35), ('physical_tables', 36),
    ('FORCE_RLS', 34), ('role_five_flags', [False, True, False, False, False]),
    ('role_five_flags', [0] * 5), ('owned_tables', 1), ('uid', 0),
    ('pid1_main_web', False), ('migrator_absent', False), ('no_new_privileges', False),
    ('pid1_owns_ready_listener', False), ('owned_ready_HTTP_200', False),
    ('effective_capabilities', 1), ('pool_size', 20), ('max_overflow', 10),
    ('owned_tables', False), ('source_hashes', {}),
])
def test_rejects_historical_schema_privilege_and_incomplete_source_claims(key, value):
    observed = witness()
    observed[key] = value
    with pytest.raises(ValueError):
        gate.validate_witness(observed, {'app_hashes': witness()['source_hashes']})


@pytest.mark.parametrize('change', ['missing', 'extra'])
def test_rejects_incomplete_or_expanded_witness(change):
    observed = witness()
    if change == 'missing':
        del observed['pid1_main_web']
    else:
        observed['invented_success'] = True
    with pytest.raises(ValueError):
        gate.validate_witness(observed, {'app_hashes': witness()['source_hashes']})


def test_database_readiness_requires_actual_json_true_without_redirect():
    gate.validate_ready(200, 'application/json; charset=utf-8', b'{"ready":true}',
                        'http://127.0.0.1:8765/health/ready')


@pytest.mark.parametrize('status,content_type,body,url', [
    (503, 'application/json', b'{"ready":true}', 'http://127.0.0.1:8765/health/ready'),
    (200, 'text/html', b'{"ready":true}', 'http://127.0.0.1:8765/health/ready'),
    (200, 'application/json', b'{"ready":false}', 'http://127.0.0.1:8765/health/ready'),
    (200, 'application/json', b'{"ready":1}', 'http://127.0.0.1:8765/health/ready'),
    (200, 'application/json', b'{"ready":true,"error":"ignored"}', 'http://127.0.0.1:8765/health/ready'),
    (200, 'application/json', b'{}', 'http://127.0.0.1:8765/health/ready'),
    (200, 'application/json', b'{"ready":true}', 'http://127.0.0.1:8765/login'),
    (200, 'application/json', b' ' * 1025, 'http://127.0.0.1:8765/health/ready'),
])
def test_rejects_false_malformed_redirected_or_unbounded_readiness(status, content_type, body, url):
    with pytest.raises(ValueError):
        gate.validate_ready(status, content_type, body, url)


@pytest.mark.parametrize('scenario', ['normal', 'payload_failure', 'foreign_cleanup', 'forced_exit', 'create_lost'])
def test_owned_container_cleanup_preserves_foreign_and_abnormal_evidence(tmp_path, monkeypatch, scenario):
    events = []
    inspections = 0
    monkeypatch.setattr(gate.uuid, 'uuid4', lambda: SimpleNamespace(hex=OWNER))

    def execute(argv, private, name, **kwargs):
        events.append(argv[1])
        if argv[1] == 'create':
            if scenario == 'create_lost':
                (private / 'modeled-cid.private.txt').write_text(CONTAINER, encoding='ascii')
                raise TimeoutError('inert lost create response')
            return CONTAINER.encode()
        return b''

    def inspect_one(docker, kind, target, private, name):
        nonlocal inspections
        inspections += 1
        value = {'Id': CONTAINER, 'Image': IMAGE, 'Config': {'Labels': {gate.OWNER_LABEL: OWNER}},
                 'HostConfig': host_config(),
                 'State': {'Running': inspections <= (1 if scenario == 'create_lost' else 2),
                           'ExitCode': 137 if scenario == 'forced_exit' and inspections == 3 else 0}}
        if scenario == 'foreign_cleanup' and inspections == 2:
            value['Config']['Labels'][gate.OWNER_LABEL] = 'someone-else'
        return value

    monkeypatch.setattr(gate, 'execute', execute)
    monkeypatch.setattr(gate, 'inspect_one', inspect_one)

    def attempt():
        with gate.container('inert-docker', IMAGE, tmp_path, 'modeled', tmp_path / 'inert.env') as actual:
            assert actual == CONTAINER
            if scenario == 'payload_failure':
                raise RuntimeError('inert startup failure')

    if scenario == 'normal':
        attempt()
    else:
        expected = RuntimeError if scenario == 'payload_failure' else (
            TimeoutError if scenario == 'create_lost' else ValueError)
        with pytest.raises(expected):
            attempt()
    if scenario == 'foreign_cleanup':
        assert events == ['create', 'start']
    elif scenario == 'forced_exit':
        assert events == ['create', 'start', 'stop', 'logs']
    else:
        assert events == (['create'] if scenario == 'create_lost' else ['create', 'start']) + ['stop', 'logs', 'rm']


@pytest.mark.parametrize('inode,port,state,ipv6,accepted', [
    ('12345', '223D', '0A', False, True), ('12345', '223D', '0A', True, True),
    ('99999', '223D', '0A', False, False), ('12345', '1F90', '0A', False, False),
    ('12345', '223D', '01', False, False),
])
def test_pid1_listener_requires_own_socket_inode_listening_on_ready_port(tmp_path, inode, port, state, ipv6, accepted):
    parent = tmp_path / 'pid1'
    (parent / 'fd').mkdir(parents=True)
    (parent / 'fd' / '7').touch()
    ipv4 = tmp_path / 'tcp'
    ipv6_table = tmp_path / 'tcp6'
    ipv4.write_text('header\n', encoding='ascii')
    ipv6_table.write_text('header\n', encoding='ascii')
    active = ipv6_table if ipv6 else ipv4
    active.write_text('header\n0: 00000000:' + port + ' 00000000:0000 ' + state
                      + ' 0:0 00:0 00000000 999 0 ' + inode + '\n', encoding='ascii')
    namespace = {'parent': parent, 'os': SimpleNamespace(readlink=lambda path: 'socket:[12345]'),
                 'Path': lambda name: ipv6_table if name.endswith('tcp6') else ipv4}
    node = next(node for node in ast.parse(gate.WITNESS).body
                if isinstance(node, ast.FunctionDef) and node.name == 'owned_listener')
    compiled = compile(ast.Module(body=[node], type_ignores=[]), 'literal-current39-listener', 'exec')
    literal = next(item for item in compiled.co_consts if isinstance(item, CodeType))
    listener = FunctionType(literal, namespace)
    if accepted:
        assert listener() == {'12345'}
    else:
        with pytest.raises(AssertionError):
            listener()
