"""Current CI57 private unittest scope, failure cleanup and explicit CLI ownership."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE=Path(__file__).with_name('test_ci_image57_offline.py')


def fresh_module():
    # Isolate the helper's globals from the normal18 class collected by pytest.
    spec=importlib.util.spec_from_file_location('ci57_bootstrap_owned_probe',SOURCE)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_implicit_scope_is_private_before_payload_and_restores_globals():
    module=fresh_module()
    module.SERIAL=41
    class Owned(module.Offline57):
        pass
    Owned.setUpClass()
    artifact=module.ARTIFACT
    parent=artifact.parent
    try:
        assert artifact.is_relative_to(Path(tempfile.gettempdir()).resolve())
        assert module.authority.regular_directory(artifact)==artifact
        assert module.SERIAL==0
        if module.os.name=='nt':
            assert (artifact/'boundary-before-payload.private.txt').is_file()
        made=module.directory('first-payload')
        assert made.parent==artifact and made.name=='1-first-payload'
        (made/'bounded.txt').write_bytes(b'bounded synthetic payload')
    finally:
        Owned.doClassCleanups()
    assert module.ARTIFACT is None and module.SERIAL==41
    assert not parent.exists()


def test_explicit_cli_scope_is_not_replaced_or_cleaned(tmp_path,monkeypatch):
    module=fresh_module()
    owned=module.authority.private_directory(tmp_path/'cli-owned',module.ROOT)
    module.ARTIFACT,module.SERIAL=owned,7
    def forbidden(*args,**kwargs):
        raise AssertionError('Explicit CLI scope was replaced')
    monkeypatch.setattr(module.tempfile,'TemporaryDirectory',forbidden)
    class Owned(module.Offline57):
        pass
    Owned.setUpClass()
    Owned.doClassCleanups()
    assert module.ARTIFACT==owned and module.SERIAL==7 and owned.is_dir()


def test_unittest_failed_boundary_runs_cleanups_without_payload(monkeypatch):
    module=fresh_module()
    module.SERIAL=19
    created=[]
    original=module.tempfile.TemporaryDirectory
    def tracked(*args,**kwargs):
        value=original(*args,**kwargs)
        created.append(Path(value.name))
        return value
    def unavailable(*args,**kwargs):
        raise RuntimeError('Synthetic private boundary rejected')
    monkeypatch.setattr(module.tempfile,'TemporaryDirectory',tracked)
    monkeypatch.setattr(module.authority,'private_directory',unavailable)
    class Owned(module.Offline57):
        pass
    result=unittest.TestResult()
    # Actual unittest invokes inherited setUpClass and its failure cleanups.
    unittest.TestSuite([Owned('test_05_real_cli_positive_and_negatives')]).run(result)
    assert result.testsRun==0 and len(result.errors)==1 and not result.failures
    assert created and all(not path.exists() for path in created)
    assert module.ARTIFACT is None and module.SERIAL==19
