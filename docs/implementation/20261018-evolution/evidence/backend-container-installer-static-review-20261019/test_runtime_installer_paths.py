"""Frozen independent path preconditions; no rm, Docker or real prefix access."""
import ast
import os
from pathlib import Path,PurePosixPath
import shlex
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT=Path(os.environ.get('CONTAINER_REVIEW_SOURCE_ROOT','F:/mb-container-runtime-tools-20261019'))


def precondition():
    text=(ROOT/'Dockerfile').read_text(encoding='utf8')
    runtime=text.split('FROM native-runtime AS runtime\n',1)[1]
    code=runtime.split('RUN set -eu;',1)[1].split('python -c ',1)[1]
    code=shlex.split(code.replace('\\\n',''))[0]
    tree=ast.parse(code)
    tree.body=[node for node in tree.body if not isinstance(node,(ast.Import,ast.ImportFrom))]
    return compile(tree,'<exact preguard AST with controlled imports>','exec')


def bindings(tmp_path,*,scripts='/usr/local/bin'):
    def mapped(value):
        value=PurePosixPath(str(value))
        assert value.is_absolute()
        return tmp_path.joinpath(*value.parts[1:])
    root=mapped('/usr/local/lib/python3.12')
    for name in ['site-packages/pip','site-packages/pip-26.2.1.dist-info','ensurepip/_bundled']:
        (root/name).mkdir(parents=True,exist_ok=True)
    mapped('/usr/local/bin').mkdir(parents=True)
    values={'stdlib':'/usr/local/lib/python3.12','purelib':'/usr/local/lib/python3.12/site-packages','scripts':scripts}
    return {'Path':mapped,'m':SimpleNamespace(version=lambda name:'26.2.1'),
            'sysconfig':SimpleNamespace(get_path=lambda name:values[name])},mapped


def test_expected_owned_paths_pass_the_precondition(tmp_path):
    environment,_mapped=bindings(tmp_path)
    exec(precondition(),environment)


def test_cleanup_rejects_aliased_scripts_parent(tmp_path):
    environment,mapped=bindings(tmp_path)
    scripts=mapped('/usr/local/bin')
    alias=tmp_path/'other-owned-directory'
    alias.mkdir()
    original_resolve=Path.resolve
    def resolved(path,*args,**kwargs):
        return alias if path==scripts else original_resolve(path,*args,**kwargs)
    with patch.object(Path,'resolve',resolved):
        assert scripts.resolve()!=scripts
        with pytest.raises(AssertionError):
            exec(precondition(),environment)


def test_cleanup_rejects_unexpected_sysconfig_scripts(tmp_path):
    environment,_mapped=bindings(tmp_path,scripts='/different/scripts')
    with pytest.raises(AssertionError):
        exec(precondition(),environment)
