"""Compile Expat 2.10 into both CPython XML extensions, preserving the base ABI.

The interpreter, libpython, installed headers and sysconfig are never rebuilt.
Source archives and every selected source/base file are authenticated separately.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import shlex
import struct
import subprocess
import ssl
import sys
import sysconfig
import tarfile
import tempfile
from urllib.parse import urljoin, urlsplit

HERE = Path(__file__).resolve().parent
ABI_KEYS = ('SOABI', 'EXT_SUFFIX', 'SIZEOF_VOID_P', 'Py_DEBUG', 'Py_ENABLE_SHARED',
            'CC', 'CFLAGS', 'CCSHARED', 'LDSHARED', 'CONFIG_ARGS',
            'PY_STDMODULE_CFLAGS', 'PY_CFLAGS_NODIST')
NAMESPACE_ANCHOR = b'#  define Expat_External_INCLUDED 1\n'
NAMESPACE_INCLUDE = b'/* Preserve CPython\'s private Expat symbol namespace. */\n#include "pyexpatns.h"\n'
SOURCE_HOSTS = {
    'https://www.python.org/ftp/python/3.12.16/Python-3.12.16.tar.xz': {'www.python.org'},
    'https://github.com/libexpat/libexpat/releases/download/R_2_10_0/expat-2.10.0.tar.xz':
        {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_archive(path, prefix, expected, archive_sha, archive_bytes):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size == archive_bytes,
            'Unexpected regular source archive or size')
    require(hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() == archive_sha,
            'Source archive hash differs')
    selected = {}
    with tarfile.open(path, 'r:xz') as archive:
        for member in archive:
            if not member.name.startswith(prefix):
                continue
            relative = member.name[len(prefix):]
            if relative not in expected:
                continue
            require(member.isfile() and not member.issym() and not member.islnk()
                    and 0 < member.size < 1024**2 and relative not in selected,
                    'Invalid selected source member')
            require(all(part not in {'', '.', '..'} for part in relative.split('/')),
                    'Invalid selected source path')
            raw = archive.extractfile(member).read(1024**2)
            require(len(raw) == member.size and digest(raw) == expected[relative],
                    'Selected source hash differs: ' + relative)
            selected[relative] = raw
    require(set(selected) == set(expected) and sum(map(len, selected.values())) < 4 * 1024**2,
            'Selected source universe differs')
    return selected


def prepare(psf_archive, expat_archive, output, lock):
    psf = read_archive(psf_archive, 'Python-3.12.16/', lock['psf_selected_sha256'],
                       lock['psf_source_sha256'], lock['psf_source_bytes'])
    expat = read_archive(expat_archive, 'expat-2.10.0/', lock['expat_selected_sha256'],
                         lock['expat_source_sha256'], lock['expat_source_bytes'])
    require(len(psf) == 7 and len(expat) == 38, 'Unexpected finite source counts')
    original = expat['lib/expat_external.h']
    require(original.count(NAMESPACE_ANCHOR) == 1, 'Namespace insertion anchor differs')
    modified = original.replace(NAMESPACE_ANCHOR, NAMESPACE_ANCHOR + NAMESPACE_INCLUDE, 1)
    require(digest(original) == lock['namespace_adaptation']['before_sha256']
            and digest(modified) == lock['namespace_adaptation']['after_sha256'],
            'Finite namespace adaptation differs')
    expat['lib/expat_external.h'] = modified
    selected = dict(psf)
    for relative, raw in expat.items():
        target = 'Modules/expat/' + (relative[len('lib/'):] if relative.startswith('lib/') else relative)
        require(target not in selected, 'Conflicting source origins')
        selected[target] = raw
    require(len(selected) == 45, 'Unexpected combined source universe')
    output.mkdir(parents=True, exist_ok=False)
    for relative, raw in selected.items():
        path = output / 'source' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as target:
            target.write(raw)
    record = {'schema': 'metodobase-expat210-source-preparation-v1',
              'psf_source_sha256': lock['psf_source_sha256'],
              'expat_source_sha256': lock['expat_source_sha256'],
              'psf_selected_sha256': lock['psf_selected_sha256'],
              'upstream_expat_selected_sha256': lock['expat_selected_sha256'],
              'prepared_source_sha256': {name: digest(raw) for name, raw in sorted(selected.items())},
              'upstream_implementation_bytes_unchanged': True,
              'only_expat_adaptation': lock['namespace_adaptation'],
              'python_config_namespace_and_binding_sources_unchanged': True,
              'version': '2.10.0', 'binding_extensions_rebuilt': ['pyexpat', '_elementtree']}
    (output / 'source-preparation.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
    return record


def base_snapshot(lock):
    expected = lock['base_file_sha256']
    require(len(expected) == 219, 'Unexpected base-file universe')
    actual = {}
    for name, value in expected.items():
        path = Path(name)
        require(name.startswith('/usr/local/') and path.is_file() and not path.is_symlink()
                and path.resolve() == path, 'Unexpected immutable base file')
        actual[name] = digest(path.read_bytes())
        require(actual[name] == value, 'Pinned base file differs: ' + name)
    return actual


def visibility_flags(abi):
    for key in ('PY_STDMODULE_CFLAGS', 'PY_CFLAGS_NODIST'):
        require(isinstance(abi[key], str), 'Missing base module flags')
        require([v for v in shlex.split(abi[key]) if v.startswith('-fvisibility=')]
                == ['-fvisibility=hidden'], 'Unexpected module visibility')
    return ['-fvisibility=hidden']


def record_compiler_calls(compiler):
    commands = []
    call = compiler.call

    def recorded(command, **kwargs):
        require(isinstance(command, (list, tuple)) and command
                and all(type(arg) is str and arg and '\0' not in arg for arg in command),
                'Invalid compiler command')
        commands.append(list(command))
        return call(command, **kwargs)
    compiler.call = recorded
    return commands


def require_trace(commands, sources, objects, artifact, compiler, postargs):
    require(len(commands) == len(sources) + 1 and len(sources) == len(objects)
            and len(set(objects)) == len(objects), 'Compiler trace count differs')
    for command, source, obj in zip(commands[:-1], sources, objects):
        require(command[:len(compiler.compiler_so)] == list(compiler.compiler_so)
                and compiler.compiler_so and command.count('-c') == command.count('-o') == 1
                and command.count(str(source)) == command.count(obj) == 1
                and command[command.index('-o') + 1] == obj
                and [arg for arg in command if arg.startswith('-fvisibility=')] == ['-fvisibility=hidden']
                and command[-len(postargs):] == postargs, 'Compile command differs')
    link = commands[-1]
    require(compiler.linker_so and link[:len(compiler.linker_so)] == list(compiler.linker_so)
            and '-c' not in link and '-shared' in link and '-lm' in link
            and link.count('-o') == 1 and link[link.index('-o') + 1] == str(artifact)
            and link.count(str(artifact)) == 1
            and all(link.count(obj) == 1 for obj in objects), 'Link command differs')


def exports(path):
    result = subprocess.run(['/usr/bin/nm', '-D', '--defined-only', str(path)],
                            capture_output=True, text=True, check=True, timeout=15)
    require(len(result.stdout) < 1024**2, 'ELF exports exceed limit')
    names = []
    for line in result.stdout.splitlines():
        fields = line.split()
        require(len(fields) == 3 and all(c in '0123456789abcdefABCDEF' for c in fields[0])
                and len(fields[1]) == 1 and fields[1] not in {'U', 'u'}, 'Unexpected ELF exports')
        names.append(fields[2])
    require(names and len(names) == len(set(names)), 'Missing or duplicate ELF exports')
    return sorted(names)


def build(output, lock, prepared):
    require(sys.platform == 'linux' and platform.machine() == 'x86_64'
            and sys.version_info[:3] == (3, 12, 16) and struct.calcsize('P') == 8,
            'Only pinned Linux/amd64 CPython3.12.16 build is supported')
    abi = {key: sysconfig.get_config_var(key) for key in ABI_KEYS}
    require(abi['SOABI'] == lock['expected_soabi'] and abi['EXT_SUFFIX'] == lock['expected_ext_suffix']
            and abi['Py_DEBUG'] == 0 and abi['Py_ENABLE_SHARED'] == 1, 'Base ABI differs')
    for name in ('CC', 'CXX', 'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'LDSHARED', 'AR', 'ARFLAGS'):
        require(not os.environ.get(name), 'Unreviewed compiler override: ' + name)
    from importlib import metadata
    require({name: metadata.version(name) for name in lock['build_tools']} == lock['build_tools'],
            'Build tools differ')
    include = Path(sysconfig.get_path('include'))
    require(include == Path('/usr/local/include/python3.12') and include.resolve() == include,
            'Installed header root differs')
    require(digest((include / 'pyexpat.h').read_bytes()) == prepared['psf_selected_sha256']['Include/pyexpat.h'],
            'Installed Python CAPI header differs')
    before = base_snapshot(lock)
    nm = Path('/usr/bin/nm').resolve(strict=True)
    readelf = Path('/usr/bin/readelf').resolve(strict=True)
    tools_before = {str(p): digest(p.read_bytes()) for p in (nm, readelf)}
    from setuptools._distutils.ccompiler import new_compiler
    from setuptools._distutils.sysconfig import customize_compiler
    artifacts = {}
    compile_counts = {'pyexpat': 5, '_elementtree': 1}
    for module in ('pyexpat', '_elementtree'):
        compiler = new_compiler()
        customize_compiler(compiler)
        commands = record_compiler_calls(compiler)
        sources = [output / 'source' / relative for relative in lock['compile_sources'][module]]
        require(len(sources) == compile_counts[module], 'Finite module source count differs')
        postargs = ['-g0', '-ffile-prefix-map=' + str(output) + '=.'] + visibility_flags(abi)
        objects = compiler.compile([str(p) for p in sources], output_dir=str(output / ('objects-' + module)),
                                   include_dirs=[str(include), str(include / 'internal'),
                                                 str(output / 'source/Modules/expat')],
                                   macros=[('HAVE_EXPAT_CONFIG_H', '1')], extra_postargs=postargs)
        require(all(Path(p).is_file() for p in objects), 'Compiled object is missing')
        artifact = output / (module + lock['expected_ext_suffix'])
        compiler.link_shared_object(objects, str(artifact), libraries=['m'])
        require_trace(commands, sources, objects, artifact, compiler, postargs)
        raw = artifact.read_bytes()
        require(raw[:6] == b'\x7fELF\x02\x01' and int.from_bytes(raw[18:20], 'little') == 62,
                'Extension is not amd64 ELF64')
        original = Path('/usr/local/lib/python3.12/lib-dynload') / artifact.name
        require(exports(original) == exports(artifact) == ['PyInit_' + module],
                'Extension public ELF export surface differs')
        dynamic = subprocess.run(['/usr/bin/readelf', '-d', str(artifact)],
                                 capture_output=True, text=True, check=True, timeout=15).stdout
        require('libexpat' not in dynamic.lower(), 'Unexpected external Expat dependency')
        artifacts[module] = {'file': artifact.name, 'sha256': digest(raw), 'bytes': len(raw),
                             'exports': exports(artifact), 'compiler_commands': commands,
                             'dynamic_section': dynamic}
    after = base_snapshot(lock)
    require(before == after and tools_before == {str(p): digest(p.read_bytes()) for p in (nm, readelf)},
            'Base or inspection tools changed during build')
    smoke = '''import io,json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import pyexpat,_elementtree,xml.etree.ElementTree as ET
root=Path(sys.argv[1])
assert Path(pyexpat.__file__).resolve()==root/('pyexpat'+sys.argv[2])
assert Path(_elementtree.__file__).resolve()==root/('_elementtree'+sys.argv[2])
assert pyexpat.EXPAT_VERSION=='expat_2.10.0' and pyexpat.version_info==(2,10,0)
assert ET.Element is _elementtree.Element and ET.XMLParser is _elementtree.XMLParser
xml=b'<root><child>safe</child></root>'
p=pyexpat.ParserCreate();p.Parse(xml[:10],False);p.Parse(xml[10:],True)
p=pyexpat.ParserCreate();p.ParseFile(io.BytesIO(xml))
assert ET.fromstring(xml).find('child').text=='safe'
assert ET.parse(io.BytesIO(xml)).getroot().tag=='root'
assert len(list(ET.iterparse(io.BytesIO(xml))))==2
parser=ET.XMLPullParser(['start','end']);parser.feed(xml[:10]);parser.feed(xml[10:]);parser.close()
assert len(list(parser.read_events()))==4
assert ET.fromstring(b'<r xmlns="urn:test"><c/></r>').tag=='{urn:test}r'
assert ET.fromstring('<r>\\u00f1\\U0001f600</r>').text=='\\u00f1\\U0001f600'
p=pyexpat.ParserCreate();p.SetReparseDeferralEnabled(True);assert p.GetReparseDeferralEnabled()
p=pyexpat.ParserCreate();p.Parse(b'',False);p.Parse(b'<r/>',True)
class Oversize:
 def read(self,n):return b'x'*(n+1)
try:pyexpat.ParserCreate().ParseFile(Oversize())
except ValueError:pass
else:raise AssertionError('Oversized ParseFile read accepted')
try:ET.fromstring(b'<root>')
except ET.ParseError:pass
else:raise AssertionError('Malformed XML accepted')
print(json.dumps({'pyexpat':pyexpat.__file__,'elementtree':_elementtree.__file__,'version':pyexpat.EXPAT_VERSION,'small_cases':12,'both_extensions_loaded_from_output':True,'elementtree_CAPI_compatible':True}))
'''
    checked = subprocess.run([sys.executable, '-I', '-S', '-c', smoke, str(output), lock['expected_ext_suffix']],
                             capture_output=True, text=True, timeout=30)
    (output / 'small-binding-tests.log').write_text(checked.stdout + '\nSTDERR\n' + checked.stderr, encoding='utf8')
    require(checked.returncode == 0, 'Compiled XML binding smoke tests failed; inspect retained log')
    result = {'schema': 'metodobase-expat210-dual-extension-build-v1', 'compiled_source': prepared,
              'abi': abi, 'artifacts': artifacts, 'base_files_before': before, 'base_files_after': after,
              'base_quiet': True, 'inspection_tools_sha256': tools_before,
              'compiler_trace_method': 'setuptools84 Compiler.call delegates unchanged;5+1compiles and2links',
              'build_tools': lock['build_tools'], 'small_binding_tests': json.loads(checked.stdout),
              'limits': 'No product startup, vulnerability scan, Debian High waiver or full security acceptance.'}
    (output / 'build-provenance.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    components = [{'type': 'library', 'name': 'libexpat', 'version': '2.10.0',
                   'cpe': 'cpe:2.3:a:libexpat_project:libexpat:2.10.0:*:*:*:*:*:*:*',
                   'properties': [{'name': 'metodobase:observed-binding-version', 'value': 'expat_2.10.0'},
                                  {'name': 'metodobase:CPE-identity-provenance', 'value': 'Canonical NVD vendor/product;version derived from authenticated upstream source and measured build,not a claim of exact dictionary entry'},
                                  {'name': 'metodobase:upstream-source-sha256', 'value': lock['expat_source_sha256']}]
                   + [{'name': 'metodobase:' + module + '-ELF-sha256', 'value': item['sha256']}
                      for module, item in artifacts.items()]}]
    (output / 'sbom.json').write_text(json.dumps({'bomFormat': 'CycloneDX', 'specVersion': '1.6',
                                                'version': 1, 'components': components}, indent=2) + '\n', encoding='utf8')
    (output / 'source-pins.json').write_bytes((HERE / 'source-pins.json').read_bytes())
    (output / 'COPYING.expat').write_bytes((output / 'source/Modules/expat/COPYING').read_bytes())


def download_source(url, path, size, expected):
    require(not path.exists(), 'Download destination already exists')
    require(url in SOURCE_HOSTS, 'Only the two pinned upstream source URLs are permitted')
    require(not os.environ.get('SSL_CERT_FILE') and not os.environ.get('SSL_CERT_DIR'),
            'Ambient source-download trust overrides rejected')
    context = ssl.create_default_context()
    require(context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED,
            'Verified TLS hostname and certificate checks required')
    allowed_hosts, current = SOURCE_HOSTS[url], url
    for hop in range(4):
        require(type(current) is str and len(current) <= 8192 and current.isascii()
                and not any(ord(char) < 33 or ord(char) == 127 for char in current),
                'Unsupported source-download URL framing')
        parsed = urlsplit(current)
        require(parsed.scheme == 'https' and parsed.hostname in allowed_hosts
                and parsed.port in {None, 443} and not parsed.username and not parsed.password
                and not parsed.fragment, 'Source redirect escaped the pinned HTTPS hosts')
        connection = http.client.HTTPSConnection(parsed.hostname, 443, timeout=90, context=context)
        response = None
        try:
            target = (parsed.path or '/') + ('?' + parsed.query if parsed.query else '')
            connection.request('GET', target, headers={'User-Agent': 'MetodoBase-native-source/20261103'})
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader('Location')
                require(hop < 3 and type(location) is str and 0 < len(location) <= 8192,
                        'Source redirect count or target differs')
                current = urljoin(current, location)
                continue
            require(response.status == 200, 'Pinned source download did not succeed')
            length = response.getheader('Content-Length')
            require(length is None or length == str(size), 'Pinned source response length differs')
            raw = response.read(size + 1)
            require(len(raw) == size and digest(raw) == expected, 'Downloaded source differs')
            with path.open('xb') as stream:
                stream.write(raw)
            return path
        finally:
            if response is not None:
                response.close()
            connection.close()
    raise ValueError('Pinned source redirect limit exceeded')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--expat-archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    lock = json.loads((HERE / 'source-pins.json').read_bytes())
    require(lock['python_version'] == '3.12.16' and lock['expat_version'] == '2.10.0', 'Finite runtime versions differ')
    if args.build:
        require(sys.platform == 'linux' and args.output == Path('/native-output'), 'Unexpected Linux build destination')
    else:
        require(args.archive is not None and args.expat_archive is not None, 'Preparation requires both explicit archives')
    with tempfile.TemporaryDirectory(prefix='metodobase-native-sources-') as temporary:
        private = Path(temporary)
        psf = args.archive or download_source(lock['psf_source_url'], private / 'python.tar.xz',
                                              lock['psf_source_bytes'], lock['psf_source_sha256'])
        expat = args.expat_archive or download_source(lock['expat_source_url'], private / 'expat.tar.xz',
                                                    lock['expat_source_bytes'], lock['expat_source_sha256'])
        os.environ['SOURCE_DATE_EPOCH'] = str(lock['source_date_epoch'])
        os.environ['PYTHONHASHSEED'] = '0'
        prepared = prepare(psf, expat, args.output, lock)
        if args.build:
            build(args.output, lock, prepared)


if __name__ == '__main__':
    main()
