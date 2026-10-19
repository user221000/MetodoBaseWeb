"""Unchanged maintained full guard, fenced to this immutable own WT30."""
import os,runpy,sys
from pathlib import Path
ROOT=Path('F:/mb-r23-ci-qa-20261019')
sys.path.insert(0,str(ROOT))
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
from qa_r23_ci_origin import audit
audit('before-maintained-full-guard')
sys.argv=[str(ROOT/'tests/verify_history_index_ci.py'),*sys.argv[1:]]
try:runpy.run_path(sys.argv[0],run_name='__main__')
finally:audit('after-maintained-full-guard')
