import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

root=Path('F:/MetodoBaseWeb-execution-20261018')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r29-final-composition-20261019')
out.mkdir(exist_ok=False)
ev=root/'docs/implementation/20261018-evolution/evidence'
sha=lambda b:hashlib.sha256(b).hexdigest()
dynamic=ev/'landing-independent-20261019/test_landing_dynamic_review.py.txt'
shutil.copyfile(dynamic,out/'test_landing_dynamic_review.py')
(out/'test_retired_page_urls.py').write_text('''import pytest
from tests.test_landing_commercial import landing

@pytest.mark.parametrize('path',['/checkout.html','/pages/checkout.html','/web/pages/checkout.html'])
def test_unused_checkout_file_has_no_public_route(landing,path):
    response=landing[0].get(path)
    assert response.status_code==404
    assert 'cdn.tailwindcss.com' not in response.text
''',encoding='utf-8')
def git(*args):
    return subprocess.run(['git',*args],cwd=root,capture_output=True,check=True).stdout
head=git('rev-parse','HEAD').decode().strip()
assert head=='1c24d3c529b6a08df7a31fe468186e38584ac186'
target=(root/'web/pages/checkout.html').resolve(strict=True)
assert target.is_relative_to(root.resolve()) and not target.is_symlink()
raw=target.read_bytes()
blob=git('show',head+':web/pages/checkout.html')
assert raw.replace(b'\r\n',b'\n')==blob
(out/'checkout-retired-original.html.raw').write_bytes(raw)
source_refs=subprocess.run(['rg','-n','--fixed-strings','checkout.html','--glob','!docs/**','--glob','!tests/**',
                            '--glob','!web/pages/checkout.html','.'],cwd=root,capture_output=True)
assert source_refs.returncode==1 and not source_refs.stdout
(out/'reference-scan.log').write_bytes(source_refs.stdout+source_refs.stderr)
paths=[p for p in git('ls-files','-z').decode().split('\0') if p and not p.startswith('docs/')
       and (root/p).suffix in {'.py','.js','.cjs','.html','.css','.sql','.json','.toml','.yml','.yaml','.lock','.sh'}]
photo=lambda:{p:sha((root/p).read_bytes()) for p in paths if (root/p).is_file()}
before=photo()
commands=[sys.executable,'tests/run_isolated.py','-p','conftest','--confcutdir='+str(out)]
run=subprocess.run([*commands,'tests/test_landing_commercial.py',str(out/'test_landing_dynamic_review.py'),
                    str(out/'test_retired_page_urls.py'),'-q','--junitxml='+str(out/'before-retirement.xml')],
                   cwd=root,capture_output=True,timeout=90)
(out/'before-retirement.log').write_bytes(run.stdout+run.stderr)
assert run.returncode==0 and photo()==before
assert target.read_bytes()==raw and sha((out/'checkout-retired-original.html.raw').read_bytes())==sha(raw)
target.unlink()
after_run=subprocess.run([*commands,str(out/'test_retired_page_urls.py'),'-q',
                          '--junitxml='+str(out/'after-retirement.xml')],cwd=root,capture_output=True,timeout=60)
(out/'after-retirement.log').write_bytes(after_run.stdout+after_run.stderr)
after=photo()
assert {p for p in before if p not in after}=={'web/pages/checkout.html'}
assert all(after[p]==digest for p,digest in before.items() if p in after)
def counts(name):
    document=ET.parse(out/name).getroot()
    suites=[document] if document.tag=='testsuite' else list(document)
    return {k:sum(int(s.get(k,'0')) for s in suites) for k in ['tests','errors','failures','skipped']}
value={'main_commit_before_retirement':head,'landing_source':'55f72149e7e05d032b5a865c664fb13070eb3df6',
       'retired_path':'web/pages/checkout.html','original_raw_sha256':sha(raw),'original_git_bytes_sha256':sha(blob),
       'raw_retained_outside_deliverable':str(out/'checkout-retired-original.html.raw'),
       'reference_scan_exit':source_refs.returncode,'no_runtime_filename_references':True,
       'mount_inventory':'Only /static mounted by both real factories; checkout file was outside web/static.',
       'source_count_before':len(before),'source_count_after':len(after),'only_retired_file_changed':True,
       'source_inventory_before_sha256':sha(json.dumps(before,sort_keys=True,separators=(',',':')).encode()),
       'source_inventory_after_sha256':sha(json.dumps(after,sort_keys=True,separators=(',',':')).encode()),
       'before_counts':counts('before-retirement.xml'),'after_counts':counts('after-retirement.xml'),
       'before_exit':run.returncode,'after_exit':after_run.returncode,
       'scope':'Composed R29 on schema28 plus retirement of the last unused commercial page; no billing/provider actions',
       'artifacts':{p.name:sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}}
(out/'summary.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:value[k] for k in ['main_commit_before_retirement','source_count_before','source_count_after','before_counts','after_counts']}))
assert after_run.returncode==0 and value['before_counts']=={'tests':20,'errors':0,'failures':0,'skipped':0}
assert value['after_counts']=={'tests':6,'errors':0,'failures':0,'skipped':0}
