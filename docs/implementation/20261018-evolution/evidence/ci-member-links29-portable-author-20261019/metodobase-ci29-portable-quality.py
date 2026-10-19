"""Capture the required quality tools without changing source or packages."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
root=Path('F:/mb-r12-ci29-20261019')
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-portable-quality-20261019');out.mkdir(exist_ok=False)
def packages():return sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())
before=packages()
commands={name:[sys.executable,'tests/check_quality.py',name] for name in ['lint','syntax','security']}
commands['new-harness-lint']=[sys.executable,'-m','ruff','check','tests/run_reviewed_ci28.py','tests/check_member_link_reports.py','tests/verify_member_links_ci.py','tests/e2e/run_member_link_browser.py','tests/e2e/member_link_postgres_server.py','tests/e2e/normalize_member_link_report.py','tests/test_member_browser_gate.py','tests/test_member_ci_trust.py','--select','F821,F401']
def run(item):
    name,command=item;result=subprocess.run(command,cwd=root,capture_output=True,timeout=120)
    (out/(name+'.stdout.log')).write_bytes(result.stdout);(out/(name+'.stderr.log')).write_bytes(result.stderr)
    return {'name':name,'exit_code':result.returncode,'command':command}
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,commands.items()))
after=packages();assert before==after
(out/'review.json').write_bytes((json.dumps({'results':rows,'tool_packages_before_after':before,'tool_packages_stable':True},indent=2)+'\n').encode())
print(json.dumps({'quality':rows,'packages_stable':True}))
assert all(row['exit_code']==0 for row in rows)
