"""Load private loopback config only in child; never print credentials or SQL values."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).parent
WT=Path(os.environ.get('R12_REVIEW_SOURCE_ROOT','F:/mb-r12-sec29'))
if '--child' in sys.argv:
    sys.path.insert(0,str(WT))
    os.environ.pop('DATABASE_URL',None)
    from tests.isolation import prepare_environment,block_external_sockets,validate_postgres_test_url
    prepare_environment(discard_inherited=True)
    block_external_sockets()
    config=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text())
    for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']:
        value=config[key];validate_postgres_test_url(value)
        from urllib.parse import urlsplit
        assert urlsplit(value).port==55483
        os.environ[key]=value
    os.environ['METODOBASE_TEST_EVIDENCE_DIR']=str(HERE/'pg-evidence')
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    import pytest
    suffix=sys.argv[sys.argv.index('--child')+1]
    extra=sys.argv[sys.argv.index('--child')+2:]
    raise SystemExit(pytest.main(['-q','--tb=short','--confcutdir='+str(HERE),
        '--junitxml='+str(HERE/(suffix+'.xml')),str(HERE/'test_r12_core29_security_review.py'),*extra]))

suffix=sys.argv[1]
assert suffix.replace('-','').isalnum()
log=HERE/(suffix+'.log');assert not log.exists()
result=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__)),'--child',suffix,*sys.argv[2:]],
    cwd=WT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'},capture_output=True)
log.write_bytes(result.stdout+result.stderr)
safe={'exit':result.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'database_values_printed':False}
if (HERE/(suffix+'.xml')).exists():
    tree=ET.parse(HERE/(suffix+'.xml'))
    suites=list(tree.getroot().iter('testsuite'))
    safe.update({k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']})
    safe['cases']=[{'name':case.attrib['name'],'status':'failed' if case.find('failure') is not None else 'error' if case.find('error') is not None else 'skipped' if case.find('skipped') is not None else 'passed'} for case in tree.getroot().iter('testcase')]
(HERE/(suffix+'-safe.json')).write_text(json.dumps(safe,indent=2)+'\n',encoding='utf8')
print(json.dumps(safe))
raise SystemExit(result.returncode)
