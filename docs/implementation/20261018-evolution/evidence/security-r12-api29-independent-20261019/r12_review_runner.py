from pathlib import Path
import hashlib,json,os,subprocess,sys
import xml.etree.ElementTree as ET
HERE=Path(__file__).parent
ROOT=Path(os.environ.get('R12_REVIEW_SOURCE_ROOT','F:/mb-r12-api-s'))
if '--child' in sys.argv:
    sys.path.insert(0,str(ROOT))
    from tests.isolation import prepare_environment,block_external_sockets,validate_postgres_test_url
    prepare_environment(discard_inherited=True);block_external_sockets()
    private=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text())
    from urllib.parse import urlsplit
    for key in ('METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL'):
        value=private[key];validate_postgres_test_url(value);assert urlsplit(value).port==55483;os.environ[key]=value
    os.environ['METODOBASE_TEST_EVIDENCE_DIR']=str(HERE/'database-evidence')
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    import pytest
    label=sys.argv[sys.argv.index('--child')+1];extra=sys.argv[sys.argv.index('--child')+2:]
    raise SystemExit(pytest.main(['-q','--tb=short','--confcutdir='+str(HERE),'--junitxml='+str(HERE/(label+'.xml')),*extra]))
label=sys.argv[1];assert label.replace('-','').isalnum()
log=HERE/(label+'.log');assert not log.exists()
p=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__)),'--child',label,*sys.argv[2:]],cwd=ROOT,
    env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True)
log.write_bytes(p.stdout+p.stderr)
safe={'exit':p.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'raw_private':True}
if (HERE/(label+'.xml')).exists():
    t=ET.parse(HERE/(label+'.xml'))
    safe.update({k:sum(int(s.attrib.get(k,0)) for s in t.getroot().iter('testsuite')) for k in ('tests','failures','errors','skipped')})
    safe['cases']=[{'name':c.attrib['name'],'status':'failed' if c.find('failure') is not None else 'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed'} for c in t.getroot().iter('testcase')]
(HERE/(label+'-safe.json')).write_text(json.dumps(safe,indent=2)+'\n',encoding='utf8')
print(json.dumps(safe));raise SystemExit(p.returncode)
