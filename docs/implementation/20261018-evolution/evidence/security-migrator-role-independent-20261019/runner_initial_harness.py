from pathlib import Path
import hashlib,json,os,subprocess,sys
import xml.etree.ElementTree as ET
HERE=Path(__file__).parent
ROOT=Path(os.environ.get('MIGRATOR_REVIEW_SOURCE_ROOT','F:/mb-mig-sec'))
if '--child' in sys.argv:
    label=sys.argv[sys.argv.index('--child')+1];mode=sys.argv[sys.argv.index('--child')+2];args=sys.argv[sys.argv.index('--child')+3:]
    sys.path.insert(0,str(ROOT))
    from tests.isolation import prepare_environment,block_external_sockets
    prepare_environment(discard_inherited=True);block_external_sockets()
    assert mode in ('absent','present')
    evidence=HERE/label;evidence.mkdir(exist_ok=False)
    os.environ.update(METODOBASE_TEST_ROLE_CLUSTER='handoff55484' if mode=='absent' else 'qa55483',
        METODOBASE_TEST_ROLE_HANDOFF_POINTER='F:/MetodoBaseWeb-linux-lab-20261019/evidence/runtime28-native-20261019/pg55484-instance-pointer.json',
        METODOBASE_TEST_ROLE_QA_CONFIG='C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json',
        METODOBASE_TEST_ROLE_EVIDENCE=str(evidence),PYTHONDONTWRITEBYTECODE='1')
    import pytest
    code=pytest.main(['-q','--tb=short','--confcutdir='+str(HERE),'--junitxml='+str(HERE/(label+'.xml')),*args])
    origins=[]
    for name in ('web.database.schema_control','web.database.tenant_policy','web.database.alembic.schema_contract_v1','web.settings'):
        path=Path(sys.modules[name].__file__).resolve();assert path.is_relative_to(ROOT.resolve())
        origins.append({'module':name,'relative_path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (HERE/(label+'-module-origins.json')).write_text(json.dumps(origins,indent=2)+'\n',encoding='utf8')
    raise SystemExit(code)
label,mode=sys.argv[1:3];assert label.replace('-','').isalnum()
target=HERE/(label+'.log');assert not target.exists()
p=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__)),'--child',label,mode,*sys.argv[3:]],cwd=ROOT,
    env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True)
target.write_bytes(p.stdout+p.stderr)
safe={'exit':p.returncode,'log_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'cluster_port':55484 if mode=='absent' else 55483,'raw_private':True}
if (HERE/(label+'.xml')).exists():
    t=ET.parse(HERE/(label+'.xml'));safe.update({k:sum(int(s.attrib.get(k,0)) for s in t.getroot().iter('testsuite')) for k in ('tests','failures','errors','skipped')})
    safe['cases']=[{'name':c.attrib['name'],'status':'failed' if c.find('failure') is not None else 'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed'} for c in t.getroot().iter('testcase')]
(HERE/(label+'-safe.json')).write_text(json.dumps(safe,indent=2)+'\n',encoding='utf8')
print(json.dumps(safe));raise SystemExit(p.returncode)
