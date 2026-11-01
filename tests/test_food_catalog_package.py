"""Verify the shipped Git artifact, not only the Windows working copy."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from src.alimentos_catalogo_usda import USDA_DATA_SHA256, USDACatalogError, _read_records


def artifact():
    repo=Path(__file__).resolve().parents[1]
    return subprocess.check_output(['git','show',':src/data/food_catalog_usda_2018.json'],cwd=repo)


def test_git_artifact_retains_the_audited_reference_checksum():
    assert hashlib.sha256(artifact()).hexdigest()==USDA_DATA_SHA256


def test_exported_reference_loads_with_all_seventy_verified_profiles(tmp_path):
    path=tmp_path/'exported.json'
    path.write_bytes(artifact())
    rows=_read_records(path)
    assert len(rows)==70 and len({r['id'] for r in rows})==70


def test_line_ending_conversion_cannot_silently_change_the_reference(tmp_path):
    raw=artifact()
    changed=raw.replace(b'\r\n',b'\n') if b'\r\n' in raw else raw.replace(b'\n',b'\r\n')
    assert changed!=raw and json.loads(changed)==json.loads(raw)
    path=tmp_path/'changed.json';path.write_bytes(changed)
    with pytest.raises(USDACatalogError):_read_records(path)
