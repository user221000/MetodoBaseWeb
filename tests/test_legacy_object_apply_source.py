"""Original source-provenance canary; synthetic Git namespace only."""
from scripts.apply_legacy_objects import source_check


def test_control_actual_HEAD_is_complete_hex():
    value = source_check()
    assert len(value['commit']) == 40 and len(value['files_sha256']) == 64


def test_inherited_GIT_DIR_cannot_substitute_source_HEAD(tmp_path, monkeypatch):
    baseline = source_check()
    foreign = tmp_path / 'synthetic-git'
    foreign.mkdir()
    (foreign / 'objects').mkdir()
    (foreign / 'refs').mkdir()
    (foreign / 'HEAD').write_text('a' * 40 + '\n', encoding='ascii')
    monkeypatch.setenv('GIT_DIR', str(foreign))
    assert source_check() == baseline
