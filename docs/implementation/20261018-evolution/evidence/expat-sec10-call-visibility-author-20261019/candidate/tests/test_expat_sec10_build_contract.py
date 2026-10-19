"""Offline OPS12/13 controls; no compiler, ELF loading, VM or native build."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import posixpath
import runpy
import subprocess
import textwrap
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = runpy.run_path(str(ROOT / 'runtime-source/expat-sec10/rebuild_pyexpat.py'))
FIXTURE_SHA256 = '6dffa081f5954295acb2494b767174041d10dfde5b8515c14c282c547f0c0013'


def installed_source():
    raw = (ROOT / 'tests/fixtures/expat_sec10/setuptools84-call-source.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    value = json.loads(raw)
    assert value['setuptools_version'] == '84.0.0'
    return value


def inert_compiler():
    """Run exact captured method bodies with process/file effects replaced."""
    observed = []
    def check_call(cmd, **kwargs):
        observed.append((list(cmd), kwargs))
    namespace = {'subprocess': SimpleNamespace(check_call=check_call, list2cmdline=subprocess.list2cmdline,
                    CalledProcessError=subprocess.CalledProcessError),
        'log': SimpleNamespace(info=lambda *_: None, debug=lambda *_: None),
        'macos': SimpleNamespace(inject_ver=lambda env: env), 'os': SimpleNamespace(path=posixpath),
        'compiler_fixup': lambda command, args: list(command),
        'CompileError': RuntimeError, 'LinkError': RuntimeError,
        'base': SimpleNamespace(Compiler=SimpleNamespace(EXECUTABLE='executable')),
        'gen_lib_options': lambda self, dirs, rdirs, libraries: ['-l' + name for name in libraries]}
    methods = installed_source()['methods']
    for key in ('Compiler.call', 'UnixCCompiler._compile', 'UnixCCompiler.link'):
        exec('from __future__ import annotations\n' + textwrap.dedent(methods[key]['source']), namespace)
    class Compiler:
        call = namespace['call']
        _compile = namespace['_compile']
        link = namespace['link']
        compiler_so = ['gcc', '-O3', '-fPIC']
        compiler_so_cxx = ['g++', '-O3', '-fPIC']
        linker_so = ['gcc', '-shared']
        linker_so_cxx = ['g++', '-shared']
        linker_exe = ['gcc']
        linker_exe_cxx = ['g++']
        objects = []
        detect_language = lambda self, src: 'c'
        _fix_object_args = lambda self, objects, output: (list(objects), output)
        _fix_lib_args = lambda self, libs, dirs, rdirs: (libs or [], dirs or [], rdirs or [])
        _need_link = lambda self, objects, output: True
        mkpath = lambda self, path: None
    return Compiler(), observed


def run_inert_methods(compiler):
    sources = ['/expat-output/source/Modules/' + name for name in
               ('pyexpat.c', 'expat/xmlparse.c', 'expat/xmlrole.c', 'expat/xmltok.c')]
    objects = ['/expat-output/objects/' + str(index) + '.o' for index in range(4)]
    artifact = '/expat-output/pyexpat.cpython-312-x86_64-linux-gnu.so'
    postargs = ['-g0', '-ffile-prefix-map=/expat-output=.'] + HELPER['module_visibility'](installed_source()['base_sysconfig'])
    for source, obj in zip(sources, objects):
        compiler._compile(obj, source, '.c', ['-c', '-DHAVE_EXPAT_CONFIG_H=1'], postargs, [])
    compiler.link('shared_object', objects, artifact, libraries=['m'])
    return sources, objects, artifact, postargs


def test_old_spawn_hook_misses_actual_setuptools84_method_path():
    compiler, observed = inert_compiler()
    missed = []
    compiler.spawn = lambda command, **kwargs: missed.append(list(command))
    run_inert_methods(compiler)
    assert missed == [] and len(observed) == 5


def test_call_hook_records_and_delegates_the_exact_four_compile_and_one_link_argv():
    compiler, observed = inert_compiler()
    commands = HELPER['record_compiler_calls'](compiler)
    sources, objects, artifact, postargs = run_inert_methods(compiler)
    assert len(commands) == 5 and commands == [command for command, kwargs in observed]
    assert all(kwargs == {'env': None} for command, kwargs in observed)
    HELPER['require_compiler_trace'](commands, sources, objects, artifact, compiler, postargs)


def test_call_hook_forwards_keywords_and_propagates_actual_delegate_failure():
    calls = []
    def failure(command, **kwargs):
        calls.append((command, kwargs))
        raise subprocess.CalledProcessError(7, command)
    compiler = SimpleNamespace(call=failure)
    commands = HELPER['record_compiler_calls'](compiler)
    argv, kwargs = ['gcc', '-c', 'synthetic.c'], {'env': {'SYNTHETIC_ONLY': '1'}, 'cwd': '/owned'}
    with pytest.raises(subprocess.CalledProcessError):
        compiler.call(argv, **kwargs)
    assert calls == [(argv, kwargs)] and calls[0][0] is argv and commands == [argv]


@pytest.mark.parametrize('argv', [[], 'gcc -c synthetic.c', ['gcc', ''], ['gcc', b'synthetic.c'], ['gcc\0']])
def test_call_hook_refuses_invalid_argv_before_delegating(argv):
    delegated = []
    compiler = SimpleNamespace(call=lambda command, **kwargs: delegated.append(command))
    commands = HELPER['record_compiler_calls'](compiler)
    with pytest.raises(AssertionError):
        compiler.call(argv)
    assert commands == delegated == []


@pytest.mark.parametrize('mode', ['empty', 'missing-compile', 'extra-link', 'shell-string', 'empty-arg',
    'nul', 'wrong-driver', 'wrong-source', 'wrong-object', 'missing-c', 'missing-visibility',
    'wrong-visibility', 'wrong-postargs', 'link-missing-object', 'link-wrong-output', 'link-not-shared'])
def test_five_command_gate_rejects_incomplete_or_substituted_traces(mode):
    compiler, _ = inert_compiler()
    commands = HELPER['record_compiler_calls'](compiler)
    sources, objects, artifact, postargs = run_inert_methods(compiler)
    commands = copy.deepcopy(commands)
    if mode == 'empty': commands.clear()
    elif mode == 'missing-compile': commands.pop(0)
    elif mode == 'extra-link': commands.append(commands[-1])
    elif mode == 'shell-string': commands[0] = 'gcc -c synthetic.c'
    elif mode == 'empty-arg': commands[0][0] = ''
    elif mode == 'nul': commands[0][0] = 'gcc\0'
    elif mode == 'wrong-driver': commands[0][0] = 'unreviewed'
    elif mode == 'wrong-source': commands[0][commands[0].index(sources[0])] = sources[1]
    elif mode == 'wrong-object': commands[0][commands[0].index('-o') + 1] = objects[1]
    elif mode == 'missing-c': commands[0].remove('-c')
    elif mode == 'missing-visibility': commands[0].remove('-fvisibility=hidden')
    elif mode == 'wrong-visibility': commands[0].append('-fvisibility=default')
    elif mode == 'wrong-postargs': commands[0][-2] = '-unreviewed'
    elif mode == 'link-missing-object': commands[-1].remove(objects[0])
    elif mode == 'link-wrong-output': commands[-1][-1] = 'other.so'
    elif mode == 'link-not-shared': commands[-1].remove('-shared')
    with pytest.raises((AssertionError, IndexError)):
        HELPER['require_compiler_trace'](commands, sources, objects, artifact, compiler, postargs)


def test_visibility_selects_only_hidden_from_the_measured_base_flags():
    abi = installed_source()['base_sysconfig']
    assert '-flto' in abi['PY_STDMODULE_CFLAGS'] and '-fprofile-use' in abi['PY_CFLAGS_NODIST']
    assert HELPER['module_visibility'](abi) == ['-fvisibility=hidden']


@pytest.mark.parametrize('key', ['PY_STDMODULE_CFLAGS', 'PY_CFLAGS_NODIST'])
@pytest.mark.parametrize('value', [None, '', '-fvisibility=default', '-fvisibility=hidden -fvisibility=default',
                                  '-fvisibility=hidden -fvisibility=hidden'])
def test_missing_or_ambiguous_base_visibility_fails_closed(key, value):
    abi = dict(installed_source()['base_sysconfig'], **{key: value})
    with pytest.raises(AssertionError):
        HELPER['module_visibility'](abi)


def test_export_gate_accepts_only_the_original_one_symbol_surface():
    parse, gate = HELPER['parse_defined_exports'], HELPER['require_base_exports']
    base = parse('0000000000010000 T PyInit_pyexpat\n')
    gate(base, base)
    with pytest.raises(AssertionError):
        gate(base, parse('0000000000010000 T PyInit_pyexpat\n0000000000020000 T XML_SetHashSalt16Bytes\n'))
    with pytest.raises(AssertionError):
        gate(['unreviewed'], ['unreviewed'])


@pytest.mark.parametrize('raw', ['', 'not-an-address T PyInit_pyexpat', '0000 U undefined',
                               '0000 T duplicate\n0001 T duplicate', '0000 T x extra'])
def test_export_parser_rejects_empty_malformed_or_duplicate_nm_output(raw):
    with pytest.raises(AssertionError):
        HELPER['parse_defined_exports'](raw)
