"""A PG oracle must contain final selected items, never deselected SQLite cases."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('selector',['sqlite','postgresql','no_matching_case'])
def test_collector_records_only_final_keyword_selection(tmp_path_factory,selector):
    directory=tmp_path_factory.mktemp('selector')
    source=directory/'test_synthetic_dialect.py'
    source.write_text("import pytest\n@pytest.mark.parametrize('engine',['sqlite','postgresql'])\ndef test_case(engine): pass\n",encoding='utf8')
    output=directory/'identities.json'
    result=subprocess.run([sys.executable,'-X','utf8','-B','tests/ci_google33/collect.py','--output',str(output),str(source),'-k',selector],
        cwd=ROOT,capture_output=True,timeout=30,check=False)
    if selector=='no_matching_case':
        assert result.returncode==5 and not output.exists()
    else:
        assert result.returncode==0,'Collection child failed; diagnostics retained privately by runner'
        identities=json.loads(output.read_bytes())
        assert len(identities)==1 and identities[0][1]=='test_case['+selector+']'
