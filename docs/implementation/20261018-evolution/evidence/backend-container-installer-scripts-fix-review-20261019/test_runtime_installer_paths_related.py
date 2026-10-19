"""Additional independent path-shape controls; same offline Temp-only bindings."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from test_runtime_installer_paths import bindings,precondition


@pytest.mark.parametrize('shape',['missing','regular-file','symlink-witness'])
def test_scripts_root_must_be_an_actual_unaliased_directory(tmp_path,shape):
    environment,mapped=bindings(tmp_path)
    scripts=mapped('/usr/local/bin')
    if shape in {'missing','regular-file'}:
        scripts.rmdir()  # This test owns the empty Temp directory it created.
        if shape=='regular-file':scripts.write_bytes(b'synthetic test file')
        with pytest.raises(AssertionError):exec(precondition(),environment)
    else:
        original=Path.is_symlink
        def symlink(path):return path==scripts or original(path)
        with patch.object(Path,'is_symlink',symlink):
            with pytest.raises(AssertionError):exec(precondition(),environment)


@pytest.mark.parametrize('target',['stdlib','purelib'])
def test_existing_canonical_prefix_guards_remain_active(tmp_path,target):
    environment,mapped=bindings(tmp_path)
    root=mapped('/usr/local/lib/python3.12')
    aliased=root if target=='stdlib' else root/'site-packages'
    original=Path.resolve
    def resolved(path,*args,**kwargs):
        return tmp_path/'elsewhere' if path==aliased else original(path,*args,**kwargs)
    with patch.object(Path,'resolve',resolved):
        with pytest.raises(AssertionError):exec(precondition(),environment)


def test_expected_installer_version_guard_remains_active(tmp_path):
    environment,_mapped=bindings(tmp_path)
    environment['m']=SimpleNamespace(version=lambda name:'25.0')
    with pytest.raises(AssertionError):exec(precondition(),environment)
