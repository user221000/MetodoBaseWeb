import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

root=Path('F:/MetodoBaseWeb-execution-20261018')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-history-recovery28-composition-20261019')
out.mkdir(exist_ok=False)
ev=root/'docs/implementation/20261018-evolution/evidence'
sha=lambda b:hashlib.sha256(b).hexdigest()
copies={
 'test_history_headers.py':ev/'history-headers-root-independent-20261019/test_history_headers.py',
 'test_history_failure_headers_review.py':ev/'history-security-independent-20261019/test_history_failure_headers_frozen.py',
 'test_recovery_security.py':ev/'recovery-security-headers-fix-20261019/test_recovery_security.py',
 'test_recovery_headers_semantic_security.py':ev/'recovery-security-headers-fix-20261019/test_recovery_headers_semantic_security.py',
 'test_recovery_method_edges.py':ev/'recovery-security-headers-fix-20261019/test_recovery_method_edges.py',
}
for name,source in copies.items():
    shutil.copyfile(source,out/name)
assert sha((out/'test_history_headers.py').read_bytes())=='e2cc888f0919aa890003e040b093d0f672db633c009fb3b769e2e403f5058755'
assert sha((out/'test_history_failure_headers_review.py').read_bytes())=='56acd85a2d72d55dbcf0c564aba263945ecba28ad2b6235c15e8c04e996baac7'
def git(*args):
    return subprocess.run(['git',*args],cwd=root,capture_output=True,check=True).stdout
head=git('rev-parse','HEAD').decode().strip()
assert head=='fdfc9cb98c7cdb437ac70e422e517a0ca4ae04f2'
suffixes={'.py','.js','.cjs','.html','.css','.sql','.json','.toml','.yml','.yaml','.lock','.sh'}
paths=[p for p in git('ls-files','-z').decode().split('\0') if p and not p.startswith('docs/') and (root/p).suffix in suffixes]
photo=lambda:{p:sha((root/p).read_bytes()) for p in paths}
before=photo()
(out/'before-private.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
selected=['test_history_headers.py','test_history_failure_headers_review.py',
          'test_recovery_headers_semantic_security.py','test_recovery_method_edges.py']
command=[sys.executable,'tests/run_isolated.py','-p','conftest','--confcutdir='+str(out),
         *[str(out/name) for name in selected],'tests/test_recovery28_review.py','-q','--junitxml='+str(out/'composition.xml')]
result=subprocess.run(command,cwd=root,capture_output=True,timeout=120)
(out/'composition.log').write_bytes(result.stdout+result.stderr)
after=photo()
(out/'after-private.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
document=ET.parse(out/'composition.xml').getroot()
suites=[document] if document.tag=='testsuite' else list(document)
counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ['tests','errors','failures','skipped']}
value={'main_commit':head,'history_source':'57cdc0d51848203bdd89c0b9f0f3c426f1b285d8',
       'recovery_source':'92615d74ee3a4bd82333c4606cca7898eb324a88',
       'scope':'composed three exact private paths, recovery page CSP and history query-failure boundary; no broad or browser rerun',
       'source_count':len(before),'sources_stable':before==after,'exit':result.returncode,'junit_counts':counts,
       'before_inventory_sha256':sha(json.dumps(before,sort_keys=True,separators=(',',':')).encode()),
       'after_inventory_sha256':sha(json.dumps(after,sort_keys=True,separators=(',',':')).encode()),
       'unchanged_driver_sha256':{name:sha((out/name).read_bytes()) for name in copies},
       'raw_retained_directory':str(out),'artifacts':{p.name:sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}}
(out/'summary.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:value[k] for k in ['main_commit','source_count','sources_stable','exit','junit_counts']}))
assert result.returncode==0 and before==after and counts=={'tests':36,'errors':0,'failures':0,'skipped':0}
