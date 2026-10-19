"""Meaningful negative preflight checks after the missing-evidence setup error."""
import importlib.util,json,os
from pathlib import Path
from unittest.mock import patch
root=Path('F:/mb-r12-ci29-20261019')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-restore-preflight-20261019');out.mkdir(exist_ok=False)
directory=out/'evidence';directory.mkdir()
spec=importlib.util.spec_from_file_location('ci28_runner_preflight',root/'tests/run_reviewed_ci28.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
valid={name:'postgresql+psycopg2://metodobase_test_unused@127.0.0.1:55483/metodobase_test_unused' for name in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']}
valid['METODOBASE_TEST_EVIDENCE_DIR']=str(directory)
rows=[]
for name in ['positive','missing-evidence','missing-app','non-test-or-remote','absent-evidence-dir']:
    values=dict(valid)
    if name=='missing-evidence':values.pop('METODOBASE_TEST_EVIDENCE_DIR')
    elif name=='missing-app':values.pop('METODOBASE_TEST_POSTGRES_URL')
    elif name=='non-test-or-remote':values['METODOBASE_TEST_MIGRATOR_URL']='postgresql://unknown@external.example.invalid/business'
    elif name=='absent-evidence-dir':values['METODOBASE_TEST_EVIDENCE_DIR']=str(out/'not-created')
    with patch.dict(os.environ,values,clear=True):
        try:module.validate_restore_environment()
        except (KeyError,OSError,ValueError):accepted=False
        else:accepted=True
    assert accepted==(name=='positive')
    rows.append({'case':name,'accepted':accepted,'network_or_database_access':False})
(out/'review.json').write_bytes((json.dumps({'scope':'Preflight only; no archive, process, network or fixtures','cases':rows},indent=2)+'\n').encode())
print(json.dumps({'cases':len(rows),'all_matched':True}))
