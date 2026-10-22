"""Author finite test-only replay; all temp/cache settings are installed before Python startup."""
from pathlib import Path
import ast
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path('F:/mb-ci-image57-portable-20261022')
BASE='f766a09d1bad9ad74c1614a1d5232b18cf7d78e5'
OUT=Path('E:/MetodoBaseWorkspace/evidence/backend-ci57-pytest-bootstrap-20261022-v1')
PUBLIC=ROOT/'docs/implementation/20261018-evolution/evidence/backend-ci57-pytest-bootstrap-20261022'
sys.path.insert(0,str(ROOT))
from tests.ci_image57 import authority
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','--no-replace-objects',*a],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==BASE
assert Path(os.environ['TEMP']).resolve()==Path('E:/MetodoBaseWorkspace/tmp').resolve()
assert Path(os.environ['TMP']).resolve()==Path('E:/MetodoBaseWorkspace/tmp').resolve()
private=authority.private_directory(OUT,ROOT)
def write(name,value):
    blob=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    with (private/name).open('xb') as stream:stream.write(blob)
def source():
    names=git('ls-files','-z','--','tests/ci_image57','tests/run_current_image57.py','tests/test_ci_image57_offline.py',
        'tests/ci_web37','tests/run_isolated.py','tests/isolation.py').decode().split('\0')
    names += ['tests/test_ci_image57_pytest_bootstrap.py']
    return {name:sha((ROOT/name).read_bytes()) for name in sorted(set(names)) if name}
def packages():
    return {d.metadata['Name']:{'version':d.version,'metadata':sha((d.read_text('METADATA') or '').encode())}
            for d in importlib.metadata.distributions()}
before=source();deps=packages()
write('source.before.json',before);write('packages.before.json',deps)
original=git('show',BASE+':tests/test_ci_image57_offline.py')
with (private/'test_ci_image57_offline.before.py').open('xb') as stream:stream.write(original)
raw=(ROOT/'tests/test_ci_image57_offline.py').read_bytes()
def pieces(blob):
    tree=ast.parse(blob)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Offline57')
    methods={n.name:ast.get_source_segment(blob.decode(),n) for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
    directory=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='directory')
    main=tree.body[-1]
    return methods,ast.get_source_segment(blob.decode(),directory),ast.get_source_segment(blob.decode(),main)
oldmethods,olddirectory,oldmain=pieces(original)
methods,directory,main=pieces(raw)
assert len(methods)==18 and methods==oldmethods and directory==olddirectory and main==oldmain
assert set(before)-set(source())==set()
write('invariant.json',{'test_methods':18,'all_method_source_bytes_equal':methods==oldmethods,
    'all_method_AST_equal':{n:ast.dump(ast.parse(s),include_attributes=False) for n,s in methods.items()}==
                           {n:ast.dump(ast.parse(s),include_attributes=False) for n,s in oldmethods.items()},
    'directory_helper_literal_equal':directory==olddirectory,'explicit_CLI_main_literal_equal':main==oldmain,
    'before_file_sha256':sha(original),'after_file_sha256':sha(raw)})
with (private/'pip.before.private.log').open('xb') as log:
    pip_before=subprocess.run([sys.executable,'-B','-m','pip','check'],stdout=log,stderr=subprocess.STDOUT).returncode
commands=[('pytest18',[sys.executable,'-B','-X','utf8','tests/run_isolated.py','tests/test_ci_image57_offline.py',
        '-q','--tb=short','--basetemp='+str(private/'pytest18-data'),'--junitxml='+str(private/'pytest18.xml'),'-p','no:cacheprovider']),
    ('bootstrap3',[sys.executable,'-B','-X','utf8','tests/run_isolated.py','tests/test_ci_image57_pytest_bootstrap.py',
        '-q','--tb=short','--basetemp='+str(private/'bootstrap3-data'),'--junitxml='+str(private/'bootstrap3.xml'),'-p','no:cacheprovider'])]
results=[]
for label,command in commands:
    with (private/(label+'.private.log')).open('xb') as log:
        value=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    doc=ET.parse(private/(label+'.xml'))
    cases=doc.findall('.//testcase')
    results.append({'label':label,'exit':value.returncode,'tests':len(cases),'failures':len(doc.findall('.//failure')),
        'errors':len(doc.findall('.//error')),'skips':len(doc.findall('.//skipped')),
        'cases':[c.attrib['classname']+'::'+c.attrib['name'] for c in cases],
        'xml_sha256':sha((private/(label+'.xml')).read_bytes()),'log_sha256':sha((private/(label+'.private.log')).read_bytes()),
        'argv':command})
    write(label+'.result.json',results[-1])
cli_root=authority.private_directory(private/'explicit-cli',ROOT)
command=[sys.executable,'-I','-B','-X','utf8','tests/test_ci_image57_offline.py','--artifact-root',str(cli_root)]
with (private/'cli18.private.log').open('xb') as log:
    value=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
cli=json.loads((cli_root/'unit-result.json').read_bytes())
results.append({'label':'cli18','exit':value.returncode,**cli,'argv':command,
    'log_sha256':sha((private/'cli18.private.log').read_bytes())})
write('cli18.result.json',results[-1])
after=source();depsafter=packages()
write('source.after.json',after);write('packages.after.json',depsafter)
with (private/'pip.after.private.log').open('xb') as log:
    pip_after=subprocess.run([sys.executable,'-B','-m','pip','check'],stdout=log,stderr=subprocess.STDOUT).returncode
summary={'base':BASE,'source_quiet':before==after,'source_files':len(before),'packages_quiet':deps==depsafter,
    'packages':len(deps),'pip':[pip_before,pip_after],'results':results,'C_data_or_target_mutation_requested':False,
    'scope':'Test bootstrap only; no Docker/image/SQL/VM/service acceptance'}
write('summary.json',summary)
print(json.dumps(summary))
raise SystemExit(0 if before==after and deps==depsafter and pip_before==pip_after==0 and
    all(r['exit']==0 for r in results) else 1)
