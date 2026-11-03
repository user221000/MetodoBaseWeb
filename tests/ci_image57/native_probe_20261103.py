"""Finite dual-XML successor to the immutable57 runtime probe.

Only the complete authenticated19-input source transition selects this probe.
Original native parsing functions and eleven XML cases remain byte-identical.
The build supplies ELF hashes; no unbuilt artifact hash is invented here.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path
from . import authority, technical_child


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_native(report, lock, prepared):
    """Validate measured current values without translating them to the parent."""
    import re

    def check(condition, message):
        if not condition:
            raise ValueError(message)

    def sha(value):
        return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None

    check(type(report.get('base_identity_files_unchanged')) is int
          and report['base_identity_files_unchanged'] == 217
          and type(report.get('base_identity_files_measured')) is int
          and report['base_identity_files_measured'] == 219, 'Technical base-file count differs')
    expected_base = lock['base_file_sha256']
    prov = report.get('expat_attestation', {})
    check(prov.get('schema') == 'metodobase-expat210-dual-extension-build-v1'
          and prov.get('base_files_before') == prov.get('base_files_after') == expected_base
          and len(expected_base) == 219 and prov.get('base_quiet') is True,
          'Technical complete219 immutable base identity differs')
    compiled = prov.get('compiled_source', {})
    check(compiled.get('schema') == 'metodobase-expat210-source-preparation-v1'
          and compiled.get('psf_source_sha256') == lock['psf_source_sha256']
          and compiled.get('expat_source_sha256') == lock['expat_source_sha256']
          and compiled.get('psf_selected_sha256') == lock['psf_selected_sha256']
          and compiled.get('upstream_expat_selected_sha256') == lock['expat_selected_sha256']
          and compiled.get('prepared_source_sha256') == prepared and len(prepared) == 45
          and compiled.get('only_expat_adaptation') == lock['namespace_adaptation']
          and compiled.get('upstream_implementation_bytes_unchanged') is True
          and compiled.get('python_config_namespace_and_binding_sources_unchanged') is True
          and compiled.get('version') == '2.10.0'
          and compiled.get('binding_extensions_rebuilt') == ['pyexpat', '_elementtree'],
          'Technical exact45 source origins or namespace adaptation differ')
    abi = prov.get('abi', {})
    check(abi.get('SOABI') == lock['expected_soabi']
          and abi.get('EXT_SUFFIX') == lock['expected_ext_suffix']
          and type(abi.get('Py_DEBUG')) is int and abi['Py_DEBUG'] == 0
          and type(abi.get('Py_ENABLE_SHARED')) is int and abi['Py_ENABLE_SHARED'] == 1
          and abi.get('SIZEOF_VOID_P') == 8 and prov.get('build_tools') == lock['build_tools'],
          'Technical pinned ABI/build tools differ')
    for key in ('PY_STDMODULE_CFLAGS', 'PY_CFLAGS_NODIST'):
        check(type(abi.get(key)) is str and [v for v in abi[key].split() if v.startswith('-fvisibility=')]
              == ['-fvisibility=hidden'], 'Technical base module visibility differs')
    artifacts = prov.get('artifacts', {})
    check(set(artifacts) == {'pyexpat', '_elementtree'}, 'Technical dual artifact universe differs')
    native = report.get('native', {})
    expected_runtime = dict(expected_base)
    replacements = {}
    for module, count, key in (('pyexpat', 5, 'pyexpat'), ('_elementtree', 1, 'elementtree')):
        artifact = artifacts[module]
        measured = native[key]
        path = '/usr/local/lib/python3.12/lib-dynload/' + module + lock['expected_ext_suffix']
        check(artifact.get('file') == module + lock['expected_ext_suffix']
              and sha(artifact.get('sha256')) and artifact['sha256'] == measured['sha256']
              and type(artifact.get('bytes')) is int and artifact['bytes'] > 0
              and artifact.get('exports') == measured.get('exports') == ['PyInit_' + module]
              and artifact['sha256'] != expected_base[path],
              'Technical real dual ELF digest/export differs')
        expected_runtime[path] = artifact['sha256']
        replacements[path] = {'original_sha256': expected_base[path], 'runtime_sha256': artifact['sha256']}
        commands = artifact.get('compiler_commands', [])
        check(type(commands) is list and len(commands) == count + 1
              and all(type(c) is list and c and all(type(a) is str and a and '\0' not in a for a in c)
                      for c in commands), 'Technical finite compiler argv absent')
        for command, source in zip(commands[:-1], lock['compile_sources'][module]):
            check(command.count('-c') == command.count('-o') == 1
                  and command.count('/native-output/source/' + source) == 1
                  and [a for a in command if a.startswith('-fvisibility=')] == ['-fvisibility=hidden']
                  and [a for a in command if a.startswith('-ffile-prefix-map=')]
                  == ['-ffile-prefix-map=/native-output=.']
                  and command[-3:] == ['-g0', '-ffile-prefix-map=/native-output=.', '-fvisibility=hidden'],
                  'Technical exact module compile source/flags differ')
        link = commands[-1]
        check('-c' not in link and '-shared' in link and '-lm' in link and link.count('-o') == 1
              and link[link.index('-o') + 1] == '/native-output/' + artifact['file'],
              'Technical finite module link differs')
        dynamic = artifact.get('dynamic_section')
        check(type(dynamic) is str and 'libexpat' not in dynamic.lower(),
              'Technical external Expat dependency differs')
        needed = re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', dynamic)
        check(needed == measured.get('needed') and 'libc.so.6' in needed
              and len(needed) == len(set(needed)) and set(needed) <= {'libc.so.6', 'libm.so.6'},
              'Technical measured/readelf dynamic dependencies differ')
    check(artifacts['pyexpat']['sha256'] != artifacts['_elementtree']['sha256']
          and report.get('base_files_measured') == expected_runtime
          and report.get('native_binding_replacements') == replacements,
          'Technical exact217 preserved files and2 measured replacements differ')
    smoke = prov.get('small_binding_tests', {})
    check(smoke.get('version') == 'expat_2.10.0' and type(smoke.get('small_cases')) is int
          and smoke['small_cases'] == 12 and smoke.get('both_extensions_loaded_from_output') is True
          and smoke.get('elementtree_CAPI_compatible') is True,
          'Technical dual-binding build smoke differs')
    check(report.get('capi_capsule_name') == 'pyexpat.expat_CAPI'
          and report.get('libpq_compile') == report.get('libpq_runtime') == 170011,
          'Technical actual native API differs')
    components = report.get('native_components_measured', {})
    cpython = components.get('CPython', {})
    expat = components.get('Expat', {})
    check(cpython.get('version') == '3.12.16' and cpython.get('SOABI') == lock['expected_soabi']
          and cpython.get('interpreter_path') == '/usr/local/bin/python3.12'
          and cpython.get('interpreter_sha256') == expected_base['/usr/local/bin/python3.12'],
          'Technical real CPython identity differs')
    check(expat.get('reported_version') == 'expat_2.10.0'
          and expat.get('source_release') == '2.10.0'
          and expat.get('source_sha256') == lock['expat_source_sha256']
          and expat.get('artifact_sha256') == native['pyexpat']['sha256']
          and expat.get('version_not_cosmetically_rewritten') is True,
          'Technical real upstream Expat identity differs')
    before = report.get('base_os_packages')
    packages = report.get('os_packages', {})
    additions = report.get('native_runtime_additions', {})
    # dpkg-query binary:Package emits an architecture qualifier for these
    # exact Multi-Arch identities. Keep every measured key verbatim; never
    # strip a suffix or infer an expected key from the runtime inventory.
    expected_binary_names = {'adduser': 'adduser',
     'apt': 'apt',
     'base-files': 'base-files',
     'base-passwd': 'base-passwd',
     'bash': 'bash',
     'bsdutils': 'bsdutils',
     'ca-certificates': 'ca-certificates',
     'coreutils': 'coreutils',
     'dash': 'dash',
     'debconf': 'debconf',
     'debian-archive-keyring': 'debian-archive-keyring',
     'debianutils': 'debianutils',
     'diffutils': 'diffutils',
     'dpkg': 'dpkg',
     'findutils': 'findutils',
     'gcc-14-base': 'gcc-14-base:amd64',
     'grep': 'grep',
     'gzip': 'gzip',
     'hostname': 'hostname',
     'init-system-helpers': 'init-system-helpers',
     'libacl1': 'libacl1:amd64',
     'libapt-pkg7.0': 'libapt-pkg7.0:amd64',
     'libattr1': 'libattr1:amd64',
     'libaudit-common': 'libaudit-common',
     'libaudit1': 'libaudit1:amd64',
     'libblkid1': 'libblkid1:amd64',
     'libbsd0': 'libbsd0:amd64',
     'libbz2-1.0': 'libbz2-1.0:amd64',
     'libc-bin': 'libc-bin',
     'libc6': 'libc6:amd64',
     'libcap-ng0': 'libcap-ng0:amd64',
     'libcap2': 'libcap2:amd64',
     'libcrypt1': 'libcrypt1:amd64',
     'libdb5.3t64': 'libdb5.3t64:amd64',
     'libdebconfclient0': 'libdebconfclient0:amd64',
     'libffi8': 'libffi8:amd64',
     'libgcc-s1': 'libgcc-s1:amd64',
     'libgdbm6t64': 'libgdbm6t64:amd64',
     'libgmp10': 'libgmp10:amd64',
     'libhogweed6t64': 'libhogweed6t64:amd64',
     'liblastlog2-2': 'liblastlog2-2:amd64',
     'liblz4-1': 'liblz4-1:amd64',
     'liblzma5': 'liblzma5:amd64',
     'libmd0': 'libmd0:amd64',
     'libmount1': 'libmount1:amd64',
     'libncursesw6': 'libncursesw6:amd64',
     'libnettle8t64': 'libnettle8t64:amd64',
     'libpam-modules': 'libpam-modules:amd64',
     'libpam-modules-bin': 'libpam-modules-bin',
     'libpam-runtime': 'libpam-runtime',
     'libpam0g': 'libpam0g:amd64',
     'libpcre2-8-0': 'libpcre2-8-0:amd64',
     'libreadline8t64': 'libreadline8t64:amd64',
     'libseccomp2': 'libseccomp2:amd64',
     'libselinux1': 'libselinux1:amd64',
     'libsemanage-common': 'libsemanage-common',
     'libsemanage2': 'libsemanage2:amd64',
     'libsepol2': 'libsepol2:amd64',
     'libsmartcols1': 'libsmartcols1:amd64',
     'libsqlite3-0': 'libsqlite3-0:amd64',
     'libssl3t64': 'libssl3t64:amd64',
     'libstdc++6': 'libstdc++6:amd64',
     'libsystemd0': 'libsystemd0:amd64',
     'libtinfo6': 'libtinfo6:amd64',
     'libudev1': 'libudev1:amd64',
     'libuuid1': 'libuuid1:amd64',
     'libxxhash0': 'libxxhash0:amd64',
     'libzstd1': 'libzstd1:amd64',
     'login': 'login',
     'login.defs': 'login.defs',
     'mawk': 'mawk',
     'mount': 'mount',
     'ncurses-base': 'ncurses-base',
     'ncurses-bin': 'ncurses-bin',
     'netbase': 'netbase',
     'openssl': 'openssl',
     'openssl-provider-legacy': 'openssl-provider-legacy',
     'passwd': 'passwd',
     'perl-base': 'perl-base',
     'readline-common': 'readline-common',
     'sed': 'sed',
     'sqv': 'sqv',
     'sysvinit-utils': 'sysvinit-utils',
     'tar': 'tar',
     'tzdata': 'tzdata',
     'util-linux': 'util-linux',
     'zlib1g': 'zlib1g:amd64'}
    source_os = lock['ca_trust']['installed_debian_packages']
    check(type(source_os) is dict and set(source_os) == set(expected_binary_names)
          and len(expected_binary_names) == len(set(expected_binary_names.values())) == 87,
          'Technical exact base package name authority differs')
    expected_os_base = {expected_binary_names[name]: version for name, version in source_os.items()}
    expected_os_additions = {'libcom-err2:amd64': '1.47.2-3+b12',
     'libgssapi-krb5-2:amd64': '1.21.3-5+deb13u1',
     'libk5crypto3:amd64': '1.21.3-5+deb13u1',
     'libkeyutils1:amd64': '1.6.3-6',
     'libkrb5-3:amd64': '1.21.3-5+deb13u1',
     'libkrb5support0:amd64': '1.21.3-5+deb13u1',
     'libldap2:amd64': '2.6.10+dfsg-1',
     'libpq5:amd64': '17.11-0+deb13u1',
     'libsasl2-2:amd64': '2.1.28+dfsg1-9',
     'libsasl2-modules-db:amd64': '2.1.28+dfsg1-9'}
    check(before == expected_os_base and len(before) == 87
          and type(packages) is dict and len(packages) == 97
          and packages == {**expected_os_base, **expected_os_additions}
          and all(packages.get(n) == v for n, v in before.items())
          and additions == {n: v for n, v in packages.items() if n not in before}
          and additions == expected_os_additions
          and report.get('os_package_counts') == {'before_native': 87, 'after_native': 97, 'runtime': 97},
          'Technical measured Debian closure differs')
    trust = report.get('ca_trust', {})
    ca = lock['ca_trust']
    check(trust.get('schema') == 'metodobase-exact-os-ca-already-withdrawn-v2'
          and trust.get('base_image') == ca['image']
          and trust.get('target_DER_sha256') == '86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b'
          and trust.get('target_SPKI_sha256') == '8d417db2dd8bf5e3084d1e3f196d583849d81bdd4c00c70b9d39369e96b8c782'
          and trust.get('target_source_config_DER_SPKI_absent') is True
          and trust.get('CApath_and_default_SSLContext_match') is True
          and type(trust.get('count')) is int and trust['count'] == 148
          and trust.get('bundle_sha256') == ca['ca_bundle_sha256']
          and trust.get('configuration_sha256') == ca['ca_conf_sha256']
          and trust.get('ca_set_sha256') == ca['ca_set_sha256']
          and trust.get('ca_der_sha256') == ca['ca_der_sha256']
          and trust.get('truststore_mutation') is False,
          'Technical exact148 default trust identity differs')


def source():
    """Bind finite source changes after authenticating every current native input."""
    _, lock = technical_child.details()
    prepared = technical_child.expected_prepared(lock)
    original = authority.raw('runtime_probe57-69d49.py.RAW')
    text = original.decode('utf8')
    start = text.index('artifact=Path(pyexpat.__file__)')
    end = text.index('import xml.etree.ElementTree as ET', start)
    replacement = '''artifact=Path(pyexpat.__file__);elementtree=Path(_elementtree.__file__)
assert str(artifact)=='/usr/local/lib/python3.12/lib-dynload/pyexpat'+TECHNICAL_LOCK['expected_ext_suffix']
assert str(elementtree)=='/usr/local/lib/python3.12/lib-dynload/_elementtree'+TECHNICAL_LOCK['expected_ext_suffix']
att=Path('/usr/local/share/metodobase/native-20261103')
prov=json.loads((att/'build-provenance.json').read_text())
base_measured={name:sha(name) for name in TECHNICAL_LOCK['base_file_sha256']}
base_checks={name:base_measured[name]==digest for name,digest in TECHNICAL_LOCK['base_file_sha256'].items()}
assert len(base_checks)==219 and sum(base_checks.values())==217
assert type(pyexpat.expat_CAPI).__name__=='PyCapsule' and repr(pyexpat.expat_CAPI).startswith('<capsule object "pyexpat.expat_CAPI"')
assert sha('/usr/local/include/python3.12/pyexpat.h')==TECHNICAL_LOCK['psf_selected_sha256']['Include/pyexpat.h']
assert pyexpat.EXPAT_VERSION=='expat_2.10.0' and pyexpat.version_info==(2,10,0)

'''
    text = text[:start] + replacement + text[end:]
    edits = [
        ("'pyasn1': '0.6.4'", "'pyasn1': '0.6.5'"),
        ('assert len(cases)==11', "assert ET.Element is _elementtree.Element and ET.XMLParser is _elementtree.XMLParser\ncases.append('dual_extension_elementtree_CAPI_binding')\nassert len(cases)==12"),
        ("assert native['pyexpat']['needed']==['libc.so.6'] and 'libpq.so.5' in native['psycopg2']['needed']", "assert 'libpq.so.5' in native['psycopg2']['needed']"),
        ("assert sha(artifact)==prov['artifact_sha256'] and actual_app==", "assert sha(artifact)==prov['artifacts']['pyexpat']['sha256'] and actual_app=="),
        ('sys.version_info[:3]==(3,12,15)', 'sys.version_info[:3]==(3,12,16)'),
        ("'source_patch':'13c5f63'", "'source_release':'2.10.0','source_sha256':TECHNICAL_LOCK['expat_source_sha256']"),
        ("'base_identity_files_unchanged':len(base_checks)", "'base_identity_files_unchanged':sum(base_checks.values())"),
    ]
    for old, new in edits:
        require(text.count(old) == 1, 'Technical finite probe anchor differs')
        text = text.replace(old, new, 1)
    # The already authenticated verifier is executed in a separate namespace:
    # its digest helper never changes the original probe sha(path) function.
    ca_source = (Path(__file__).resolve().parents[2] / technical_child.NATIVE_PREFIX / 'verify_ca.py').read_text(encoding='utf8')
    ca_start = ca_source.index('    output = Path(')
    ca_end = ca_source.index("\n\nif __name__ == '__main__':", ca_start)
    ca_source = ca_source[:ca_start] + '    return result\n' + ca_source[ca_end:]
    tail = ("report['base_files_measured']=base_measured\nreport['base_identity_files_measured']=len(base_measured)\nreport['base_os_packages']=base\n"
            + "report['native_binding_replacements']={str(path):{'original_sha256':TECHNICAL_LOCK['base_file_sha256'][str(path)],'runtime_sha256':sha(path)} for path in (artifact,elementtree)}\n"
            + "ca_namespace={'__name__':'finite_ca_runtime','__file__':'/usr/local/share/metodobase/technical-close-20261103/verify_ca.py'}\n"
            + 'exec(compile(' + repr(ca_source) + ",'finite-ca-runtime.py','exec'),ca_namespace)\n"
            + "report['ca_trust']=ca_namespace['main']()\n"
            + "assert report['ca_trust']==json.loads(Path('/usr/local/share/metodobase/ca-root-g3-20261103.json').read_bytes())\n"
            + 'validate_native(report,TECHNICAL_LOCK,TECHNICAL_PREPARED)\n')
    require(text.count('print(json.dumps(report))') == 1, 'Technical probe report framing differs')
    text = text.replace('print(json.dumps(report))', tail + 'print(json.dumps(report))', 1)
    prefix = ('TECHNICAL_LOCK=' + repr(lock) + '\nTECHNICAL_PREPARED=' + repr(prepared) + '\n'
              + inspect.getsource(validate_native) + '\n')
    result = (prefix + text).encode('utf8')
    from .probe import function_bytes
    require(all(function_bytes(result).get(name) == raw for name, raw in function_bytes(original).items()),
            'Technical successor changed an original native parsing function')
    compile(result, 'technical-native-probe.py', 'exec')
    return result
