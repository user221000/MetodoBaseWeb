import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

root = Path('F:/MetodoBaseWeb-execution-20261018')
ev = root / 'docs/implementation/20261018-evolution/evidence'
out = Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history-landing-main-ci-review-20261019')
out.mkdir(exist_ok=False)
sha = lambda raw: hashlib.sha256(raw).hexdigest()
head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert head.startswith('52af400')
qa = ev / 'history-landing-ci-independent-20261019'
assert sha((qa/'final-summary.json').read_bytes()) == 'f24d465456bcf0f33f0d3c1aef116b207dfadca001b56d3bf7563569b005fd00'
assert sha((qa/'final-manifest.json').read_bytes()) == '6128847cb3384252e3f8fe3310a1df6a0050403004ec8a71d245d0f8b6967205'
files = json.loads((qa/'final-manifest.json').read_text(encoding='utf-8'))['files']
for name,value in files.items():
    assert sha((qa/name).read_bytes()) == (value if isinstance(value,str) else value['sha256']), name
gitfiles = subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1]
suffixes = {'.py','.js','.cjs','.html','.css','.sql','.json','.toml','.yml','.yaml','.lock','.sh'}
selected = [n for n in gitfiles if not n.startswith('docs/') and (root/n).suffix in suffixes]
photo = lambda: {n:sha((root/n).read_bytes()) for n in selected}
packages = lambda: subprocess.check_output([sys.executable,'-m','pip','list','--format=json','--disable-pip-version-check'])
before = photo()
before_packages = packages()
command = [sys.executable,'-X','utf8','tests/verify_history_landing_ci.py','--verify-only','--output',str(out/'verify-only')]
result = subprocess.run(command,cwd=root,capture_output=True,timeout=90)
(out/'verify-only.log').write_bytes(result.stdout+result.stderr)
after = photo()
after_packages = packages()
pip = subprocess.run([sys.executable,'-m','pip','check'],capture_output=True)
(out/'pip-check.log').write_bytes(pip.stdout+pip.stderr)
assert result.returncode == pip.returncode == 0
assert before == after and before_packages == after_packages
report = json.loads((out/'verify-only/review.json').read_text(encoding='utf-8'))
assert report['historical_ci28_exit'] == 0 and len(report['unauthorized_delta_canaries']) == 13
(out/'source-photos-private.json').write_text(json.dumps({'before':before,'after':after},indent=2)+'\n',encoding='utf-8')
summary = {'head':head,'accepted_qa_head':'57dba41a87de4f7a743e6b68c0378f1629b7bb72','independent_manifest_rehashed':len(files),'independent_final_summary_sha256':sha((qa/'final-summary.json').read_bytes()),'composition_verify_only_exit':result.returncode,'delta_canaries':13,'source_count':len(before),'sources_stable':True,'source_aggregate_sha256':sha(json.dumps(before,sort_keys=True,separators=(',',':')).encode()),'packages':len(json.loads(before_packages)),'packages_stable':True,'pip_check_exit':pip.returncode,'scope':'MAIN composed CI extension and pinned historical verifier only. Independent full verifier,30 own cases,23VM and10+8browser already accepted; no repeated broad/PG/browser/Actions/image.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
dest = ev / 'history-landing-main-ci-review-20261019'
dest.mkdir(exist_ok=False)
for p in out.rglob('*'):
    if p.is_file() and p.name != 'source-photos-private.json':
        target = dest / p.relative_to(out)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,target)
shutil.copyfile(__file__,dest/'driver.py')
(dest/'manifest.json').write_text(json.dumps({'files':{p.relative_to(dest).as_posix():sha(p.read_bytes()) for p in sorted(dest.rglob('*')) if p.is_file()}},indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary))
