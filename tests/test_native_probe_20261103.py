"""Adversarial probe/parser controls; synthetic reports do not attest Linux."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from types import CodeType, FunctionType

import pytest

from tests.ci_image57 import authority, context, native_probe_20261103 as current, probe, production_child, technical_child as child
from tests.test_ci_image57_offline import cli, contract_and_report

LOCK = json.loads((Path(__file__).resolve().parents[1] / child.ACTIVE_SOURCE_PINS).read_bytes())
REPLACED = tuple('/usr/local/lib/python3.12/lib-dynload/' + name + LOCK['expected_ext_suffix']
                 for name in ('pyexpat', '_elementtree'))
PRESERVED = tuple(name for name in LOCK['base_file_sha256'] if name not in REPLACED)

# Independent metadata-derived fixture, not an executed Linux inventory.
DPKG_BASE_BINARY_PACKAGES = {'adduser': '3.152',
 'apt': '3.0.3',
 'base-files': '13.8+deb13u7',
 'base-passwd': '3.6.7',
 'bash': '5.2.37-2+b10',
 'bsdutils': '1:2.41.5-0+deb13u1',
 'ca-certificates': '20250419+deb13u1',
 'coreutils': '9.7-3',
 'dash': '0.5.12-12',
 'debconf': '1.5.91',
 'debian-archive-keyring': '2025.1',
 'debianutils': '5.23.2',
 'diffutils': '1:3.10-4',
 'dpkg': '1.22.22',
 'findutils': '4.10.0-3',
 'gcc-14-base:amd64': '14.2.0-19',
 'grep': '3.11-4',
 'gzip': '1.13-1+deb13u1',
 'hostname': '3.25',
 'init-system-helpers': '1.69~deb13u1',
 'libacl1:amd64': '2.3.2-2+b1',
 'libapt-pkg7.0:amd64': '3.0.3',
 'libattr1:amd64': '1:2.5.2-3',
 'libaudit-common': '1:4.0.2-2+deb13u1',
 'libaudit1:amd64': '1:4.0.2-2+deb13u1',
 'libblkid1:amd64': '2.41.5-0+deb13u1',
 'libbsd0:amd64': '0.12.2-2',
 'libbz2-1.0:amd64': '1.0.8-6',
 'libc-bin': '2.41-12+deb13u4',
 'libc6:amd64': '2.41-12+deb13u4',
 'libcap-ng0:amd64': '0.8.5-4+b1',
 'libcap2:amd64': '1:2.75-10+deb13u1+b3',
 'libcrypt1:amd64': '1:4.4.38-1',
 'libdb5.3t64:amd64': '5.3.28+dfsg2-9',
 'libdebconfclient0:amd64': '0.280',
 'libffi8:amd64': '3.4.8-2',
 'libgcc-s1:amd64': '14.2.0-19',
 'libgdbm6t64:amd64': '1.24-2',
 'libgmp10:amd64': '2:6.3.0+dfsg-3',
 'libhogweed6t64:amd64': '3.10.1-1',
 'liblastlog2-2:amd64': '2.41.5-0+deb13u1',
 'liblz4-1:amd64': '1.10.0-4',
 'liblzma5:amd64': '5.8.1-1+deb13u2',
 'libmd0:amd64': '1.1.0-2+b1',
 'libmount1:amd64': '2.41.5-0+deb13u1',
 'libncursesw6:amd64': '6.5+20250216-2',
 'libnettle8t64:amd64': '3.10.1-1',
 'libpam-modules-bin': '1.7.0-5',
 'libpam-modules:amd64': '1.7.0-5',
 'libpam-runtime': '1.7.0-5',
 'libpam0g:amd64': '1.7.0-5',
 'libpcre2-8-0:amd64': '10.46-1~deb13u3',
 'libreadline8t64:amd64': '8.2-6',
 'libseccomp2:amd64': '2.6.0-2',
 'libselinux1:amd64': '3.8.1-1',
 'libsemanage-common': '3.8.1-1',
 'libsemanage2:amd64': '3.8.1-1',
 'libsepol2:amd64': '3.8.1-1',
 'libsmartcols1:amd64': '2.41.5-0+deb13u1',
 'libsqlite3-0:amd64': '3.46.1-7+deb13u2',
 'libssl3t64:amd64': '3.5.7-1~deb13u3',
 'libstdc++6:amd64': '14.2.0-19',
 'libsystemd0:amd64': '257.13-1~deb13u1',
 'libtinfo6:amd64': '6.5+20250216-2',
 'libudev1:amd64': '257.13-1~deb13u1',
 'libuuid1:amd64': '2.41.5-0+deb13u1',
 'libxxhash0:amd64': '0.8.3-2',
 'libzstd1:amd64': '1.5.7+dfsg-1',
 'login': '1:4.16.0-2+really2.41.5-0+deb13u1',
 'login.defs': '1:4.17.4-2',
 'mawk': '1.3.4.20250131-1',
 'mount': '2.41.5-0+deb13u1',
 'ncurses-base': '6.5+20250216-2',
 'ncurses-bin': '6.5+20250216-2',
 'netbase': '6.5',
 'openssl': '3.5.7-1~deb13u3',
 'openssl-provider-legacy': '3.5.7-1~deb13u3',
 'passwd': '1:4.17.4-2',
 'perl-base': '5.40.1-6+deb13u1',
 'readline-common': '8.2-6',
 'sed': '4.9-2+deb13u1',
 'sqv': '1.3.0-3+b2',
 'sysvinit-utils': '3.14-4',
 'tar': '1.35+dfsg-3.1',
 'tzdata': '2026e-0+deb13u1',
 'util-linux': '2.41.5-0+deb13u1',
 'zlib1g:amd64': '1:1.3.dfsg+really1.3.1-1+b1'}


@pytest.fixture(scope='module', autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def structural_fixture():
    """Inert positive parser fixture, explicitly using synthetic ELF digests."""
    catalog, lock = child.details()
    prepared = child.expected_prepared(lock)
    contract, report = contract_and_report()
    contract['distributions'] = catalog['distributions']
    contract['native_input_transition'] = child.transition(production_child.transition(context.native_transition()))
    report['distributions'] = catalog['distributions'].copy()
    report['imports']['pyasn1']['version'] = '0.6.5'
    report['base_identity_files_unchanged'] = 217
    report['base_identity_files_measured'] = 219
    report['base_files_measured'] = lock['base_file_sha256'].copy()
    report['small_xml_cases'].append('dual_extension_elementtree_CAPI_binding')
    prepared_record = {'schema': 'metodobase-expat210-source-preparation-v1',
                       'psf_source_sha256': lock['psf_source_sha256'], 'expat_source_sha256': lock['expat_source_sha256'],
                       'psf_selected_sha256': lock['psf_selected_sha256'], 'upstream_expat_selected_sha256': lock['expat_selected_sha256'],
                       'prepared_source_sha256': prepared, 'only_expat_adaptation': lock['namespace_adaptation'],
                       'upstream_implementation_bytes_unchanged': True, 'python_config_namespace_and_binding_sources_unchanged': True,
                       'version': '2.10.0', 'binding_extensions_rebuilt': ['pyexpat', '_elementtree']}
    artifacts = {}
    report['native']['elementtree']['sha256'] = 'd' * 64
    report['native_binding_replacements'] = {}
    for module, key in (('pyexpat', 'pyexpat'), ('_elementtree', 'elementtree')):
        name = module + lock['expected_ext_suffix']
        commands = [['cc', '-c', '/native-output/source/' + source, '-o', str(index) + '.o', '-g0',
                     '-ffile-prefix-map=/native-output=.', '-fvisibility=hidden']
                    for index, source in enumerate(lock['compile_sources'][module])]
        commands.append(['cc', '-shared', '-lm', '-o', '/native-output/' + name])
        report['native'][key]['exports'] = ['PyInit_' + module]
        report['native'][key]['needed'] = ['libc.so.6']
        artifacts[module] = {'file': name, 'sha256': report['native'][key]['sha256'], 'bytes': 1024,
                             'exports': ['PyInit_' + module], 'compiler_commands': commands,
                             'dynamic_section': '0x0000000000000001 (NEEDED) Shared library: [libc.so.6]\n'}
        path = '/usr/local/lib/python3.12/lib-dynload/' + name
        report['base_files_measured'][path] = artifacts[module]['sha256']
        report['native_binding_replacements'][path] = {'original_sha256': lock['base_file_sha256'][path],
                                                      'runtime_sha256': artifacts[module]['sha256']}
    report['expat_attestation'] = {'schema': 'metodobase-expat210-dual-extension-build-v1',
        'base_files_before': lock['base_file_sha256'], 'base_files_after': lock['base_file_sha256'], 'base_quiet': True,
        'compiled_source': prepared_record, 'abi': {'SOABI': lock['expected_soabi'], 'EXT_SUFFIX': lock['expected_ext_suffix'],
            'Py_DEBUG': 0, 'Py_ENABLE_SHARED': 1, 'SIZEOF_VOID_P': 8,
            'PY_STDMODULE_CFLAGS': '-fvisibility=hidden', 'PY_CFLAGS_NODIST': '-fvisibility=hidden'},
        'artifacts': artifacts, 'build_tools': lock['build_tools'],
        'small_binding_tests': {'version': 'expat_2.10.0', 'small_cases': 12,
            'both_extensions_loaded_from_output': True, 'elementtree_CAPI_compatible': True}}
    additions = {'libcom-err2': '1.47.2-3+b12', 'libgssapi-krb5-2': '1.21.3-5+deb13u1',
        'libk5crypto3': '1.21.3-5+deb13u1', 'libkeyutils1': '1.6.3-6', 'libkrb5-3': '1.21.3-5+deb13u1',
        'libkrb5support0': '1.21.3-5+deb13u1', 'libldap2': '2.6.10+dfsg-1', 'libpq5': '17.11-0+deb13u1',
        'libsasl2-2': '2.1.28+dfsg1-9', 'libsasl2-modules-db': '2.1.28+dfsg1-9'}
    report['base_os_packages'] = DPKG_BASE_BINARY_PACKAGES.copy()
    additions = {name + ':amd64': version for name, version in additions.items()}
    report['os_packages'] = {**report['base_os_packages'], **additions}
    report['native_runtime_additions'] = additions
    report['native_components_measured'] = {'CPython': {'version': '3.12.16', 'SOABI': lock['expected_soabi'],
        'interpreter_path': '/usr/local/bin/python3.12', 'interpreter_sha256': lock['base_file_sha256']['/usr/local/bin/python3.12']},
        'Expat': {'reported_version': 'expat_2.10.0', 'source_release': '2.10.0', 'source_sha256': lock['expat_source_sha256'],
                  'artifact_sha256': report['native']['pyexpat']['sha256'], 'version_not_cosmetically_rewritten': True}}
    ca = lock['ca_trust']
    report['ca_trust'] = {'schema': 'metodobase-exact-os-ca-already-withdrawn-v2', 'base_image': ca['image'],
        'target_DER_sha256': '86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b',
        'target_SPKI_sha256': '8d417db2dd8bf5e3084d1e3f196d583849d81bdd4c00c70b9d39369e96b8c782',
        'target_source_config_DER_SPKI_absent': True, 'CApath_and_default_SSLContext_match': True, 'count': 148,
        'bundle_sha256': ca['ca_bundle_sha256'], 'configuration_sha256': ca['ca_conf_sha256'],
        'ca_set_sha256': ca['ca_set_sha256'], 'ca_der_sha256': ca['ca_der_sha256'], 'truststore_mutation': False}
    return contract, report


def test_positive_parser_fixture_uses_actual_current_versions_and_no_linux_execution_claim():
    contract, report = structural_fixture()
    result = probe.validate_report(report, contract)
    assert result['xml_cases'] == 12 and result['distributions'] == 57 and result['runtime_import_diagnostic_only'] is True
    assert report['complete_product_acceptance'] is False and report['SBOM_SCA_complete'] is False


def test_bound_current_probe_keeps_original_functions_eleven_cases_and_actual_versions():
    contract, _ = structural_fixture()
    bound = probe.bind(contract)
    original = authority.raw('runtime_probe57-69d49.py.RAW')
    assert all(probe.function_bytes(bound)[name] == raw for name, raw in probe.function_bytes(original).items())
    assert b"sys.version_info[:3]==(3,12,16)" in bound and b"pyexpat.EXPAT_VERSION=='expat_2.10.0'" in bound
    assert b"'dual_extension_elementtree_CAPI_binding'" in bound and b'len(cases)==12' in bound
    assert b"'pyasn1': '0.6.5'" in bound and b"'source_patch':'13c5f63'" not in bound
    assert b"ca_namespace['main']()" in bound and b'base_files_measured' in bound
    compile(bound, 'focal-native-probe-only.py', 'exec')


@pytest.mark.parametrize('fault', ['transition', 'pyasn1', 'other_dist'])
def test_no_unreviewed_source_transition_or_catalog_selects_new_probe(fault):
    contract, _ = structural_fixture()
    if fault == 'transition':
        contract['native_input_transition']['critical_input_count'] = 18
    elif fault == 'pyasn1':
        contract['distributions']['pyasn1'] = '0.6.4'
    else:
        contract['distributions']['stripe'] = '99.0.0'
    with pytest.raises(ValueError):
        probe.bind(contract)


@pytest.mark.parametrize('path,value', [
    (('base_files_measured', '/usr/local/bin/python3.12'), '0' * 64),
    (('base_identity_files_unchanged',), 218),
    (('expat_attestation', 'base_quiet'), False),
    (('expat_attestation', 'compiled_source', 'prepared_source_sha256', 'Modules/_elementtree.c'), '0' * 64),
    (('expat_attestation', 'compiled_source', 'only_expat_adaptation'), {}),
    (('expat_attestation', 'artifacts', '_elementtree', 'sha256'), '0' * 64),
    (('expat_attestation', 'artifacts', '_elementtree', 'exports'), ['PyInit__elementtree', 'XML_Parse']),
    (('expat_attestation', 'artifacts', 'pyexpat', 'compiler_commands'), []),
    (('expat_attestation', 'artifacts', '_elementtree', 'dynamic_section'), '(NEEDED) Shared library: [libexpat.so.1]'),
    (('expat_attestation', 'small_binding_tests', 'both_extensions_loaded_from_output'), False),
    (('expat_attestation', 'abi', 'Py_DEBUG'), False),
    (('native_components_measured', 'CPython', 'version'), '3.12.15'),
    (('native_components_measured', 'Expat', 'reported_version'), 'expat_2.8.5'),
    (('native_components_measured', 'Expat', 'source_sha256'), '0' * 64),
    (('os_packages', 'libpq5:amd64'), '17.10-0+deb13u1'),
    (('native_runtime_additions', 'libpq5:amd64'), '17.10-0+deb13u1'),
    (('base_os_packages', 'tzdata'), '2026c-0+deb13u1'),
    (('ca_trust', 'count'), 149),
    (('ca_trust', 'CApath_and_default_SSLContext_match'), False),
    (('ca_trust', 'truststore_mutation'), True),
    (('ca_trust', 'ca_set_sha256'), '0' * 64),
    (('uid',), True), (('source_modes',), {}), (('SBOM_SCA_complete',), True),
])
def test_meaningful_native_measurement_mutations_are_rejected(path, value):
    contract, report = structural_fixture()
    report = deepcopy(report)
    selected = report
    for name in path[:-1]:
        selected = selected[name]
    selected[path[-1]] = value
    with pytest.raises((ValueError, KeyError, TypeError)):
        probe.validate_report(report, contract)


def test_original_xml_case_algorithms_execute_on_host_without_claiming_new_linux_elfs():
    raw = current.source().decode('utf8')
    first = raw.index('import xml.etree.ElementTree as ET')
    last = raw.index('assert psycopg2.__libpq_version__', first)
    import io
    import pyexpat
    import _elementtree
    namespace = {'io': io, 'pyexpat': pyexpat, '_elementtree': _elementtree}
    exec(compile(raw[first:last], 'original-eleven-and-binding-case-only.py', 'exec'), namespace)
    assert len(namespace['cases']) == 12


@pytest.mark.parametrize('path', PRESERVED)
def test_every_one_of217_runtime_immutable_file_mutations_rejects(path):
    assert len(PRESERVED) == 217 and len(REPLACED) == 2
    contract, report = structural_fixture()
    report['base_files_measured'][path] = '0' * 64
    with pytest.raises(ValueError):
        probe.validate_report(report, contract)


@pytest.mark.parametrize('module,key,path', [('pyexpat', 'pyexpat', REPLACED[0]), ('_elementtree', 'elementtree', REPLACED[1])])
@pytest.mark.parametrize('fault', ['measured_mismatch', 'old_ELF_reused', 'missing_replacement', 'original_rebound'])
def test_each_runtime_replacement_requires_new_measured_elf_and_exact_build_provenance(module, key, path, fault):
    contract, report = structural_fixture()
    if fault == 'measured_mismatch':
        report['base_files_measured'][path] = '0' * 64
    elif fault == 'old_ELF_reused':
        old = LOCK['base_file_sha256'][path]
        report['base_files_measured'][path] = old
        report['native'][key]['sha256'] = old
        report['expat_attestation']['artifacts'][module]['sha256'] = old
        report['native_binding_replacements'][path]['runtime_sha256'] = old
    elif fault == 'missing_replacement':
        report['native_binding_replacements'].pop(path)
    else:
        report['native_binding_replacements'][path]['original_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        probe.validate_report(report, contract)


@pytest.mark.parametrize('fault', ['missing_measured', 'extra_measured', 'extra_replacement', 'count_bool'])
def test_runtime219_and_exactly_two_replacements_reject_missing_extra_or_untyped_values(fault):
    contract, report = structural_fixture()
    if fault == 'missing_measured':
        report['base_files_measured'].pop(PRESERVED[0])
    elif fault == 'extra_measured':
        report['base_files_measured']['/unreviewed'] = 'a' * 64
    elif fault == 'extra_replacement':
        report['native_binding_replacements']['/unreviewed'] = {'original_sha256': 'a' * 64, 'runtime_sha256': 'b' * 64}
    else:
        report['base_identity_files_measured'] = True
    with pytest.raises(ValueError):
        probe.validate_report(report, contract)


def test_actual_check_report_cli_accepts_only_current_complete_structural_measurements(tmp_path):
    root = Path(__file__).resolve().parents[1]
    folder = authority.private_directory(tmp_path / 'current-parser', root)
    contract, report = structural_fixture()
    entry = root / 'tests/run_current_image57.py'
    assert cli(entry, contract, report, folder, 'current-structural-positive') == 0
    changed = deepcopy(report)
    changed['base_files_measured'][PRESERVED[0]] = '0' * 64
    assert cli(entry, contract, changed, folder, 'current-immutable-negative') != 0
    _, previous = contract_and_report()
    assert cli(entry, contract, previous, folder, 'parent-report-negative') != 0


def test_debian_binary_names_are_exact_architecture_labels_without_runtime_relabeling():
    contract, report = structural_fixture()
    before = deepcopy(report)
    assert len(report['base_os_packages']) == 87 and len(report['os_packages']) == 97
    assert sum(':' in name for name in report['base_os_packages']) == 45
    assert sum(':' in name for name in report['os_packages']) == 55
    assert report['base_os_packages']['libc6:amd64'] == '2.41-12+deb13u4'
    assert 'libc6' not in report['base_os_packages'] and 'libpq5' not in report['os_packages']
    assert len(report['native_runtime_additions']) == 10
    probe.validate_report(report, contract)
    assert report == before


@pytest.mark.parametrize('target', ['base_os_packages', 'os_packages', 'native_runtime_additions'])
@pytest.mark.parametrize('fault', ['missing', 'extra', 'foreign_architecture', 'missing_qualifier',
                                 'different_case', 'canonical_collision', 'version', 'new_qualifier'])
def test_debian_exact_raw_names_reject_drift_even_at_unchanged_cardinality(target, fault):
    contract, report = structural_fixture()
    selected = report[target]
    key = 'libc6:amd64' if target == 'base_os_packages' else 'libpq5:amd64'
    if fault == 'missing':
        selected.pop(key)
    elif fault == 'extra':
        selected['unreviewed:amd64'] = '1'
    elif fault == 'foreign_architecture':
        selected[key.replace(':amd64', ':arm64')] = selected.pop(key)
    elif fault == 'missing_qualifier':
        selected[key.removesuffix(':amd64')] = selected.pop(key)
    elif fault == 'different_case':
        selected[key.upper()] = selected.pop(key)
    elif fault == 'canonical_collision':
        # Keep the cardinality while two labels refer to one canonical name.
        selected[key.removesuffix(':amd64')] = selected[key]
        other = next(name for name in selected if name not in {key, key.removesuffix(':amd64')})
        selected.pop(other)
    elif fault == 'version':
        selected[key] = '99.0-unreviewed'
    elif target == 'native_runtime_additions':
        selected[key + ':amd64'] = selected.pop(key)
    else:
        # A package without Multi-Arch:same cannot acquire an arbitrary suffix.
        selected['adduser:amd64'] = selected.pop('adduser')
    with pytest.raises(ValueError, match='Debian closure'):
        probe.validate_report(report, contract)


def test_debian_validator_embedded_in_bound_probe_has_no_extra_global_dependency():
    contract, report = structural_fixture()
    bound = probe.bind(contract)
    tree = ast.parse(bound)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'validate_native')
    compiled = compile(ast.Module(body=[function], type_ignores=[]), 'isolated-bound-validator-only.py', 'exec')
    code = next(value for value in compiled.co_consts if isinstance(value, CodeType) and value.co_name == 'validate_native')
    embedded = FunctionType(code, {})
    embedded(report, LOCK, child.expected_prepared(LOCK))
    report['os_packages']['libpq5:arm64'] = report['os_packages'].pop('libpq5:amd64')
    with pytest.raises(ValueError, match='Debian closure'):
        embedded(report, LOCK, child.expected_prepared(LOCK))


def test_debian_runtime_query_and_original_parsing_algorithms_remain_unchanged():
    contract, _report = structural_fixture()
    bound = probe.bind(contract)
    original = authority.raw('runtime_probe57-69d49.py.RAW')
    assert all(probe.function_bytes(bound)[name] == raw for name, raw in probe.function_bytes(original).items())
    assert b"fmt='${binary:Package}\\t${Version}\\n'" in bound
    assert b"packages=dict(line.split('\\t',1) for line in subprocess.check_output(['dpkg-query','-W','-f='+fmt],text=True).splitlines())" in bound
    assert b"'native_runtime_additions':{n:v for n,v in after.items() if n not in base}" in bound
