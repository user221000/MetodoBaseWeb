"""Preserve the exact failed Bash harness case before fixing its missing setup."""
import importlib.util
import json
from pathlib import Path
import sys
import yaml
root=Path('F:/mb-r12-ci29-20261019');sys.path.insert(0,str(root))
out=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-inert-before-20261019');out.mkdir(exist_ok=False)
source=root/'tests/verify_member_links_ci.py';(out/'verifier-before.py').write_bytes(source.read_bytes())
spec=importlib.util.spec_from_file_location('ci29_author_probe',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
workflow=yaml.safe_load((root/'.github/workflows/ci.yml').read_text(encoding='utf8'))
browser=next(step['run'] for step in workflow['jobs']['image']['steps'] if 'run_browser_fixture() {' in step.get('run',''))
function=browser[browser.index('run_browser_fixture() {'):browser.index('\nbrowser_evidence=')]
call=next(line for line in browser.splitlines() if line.startswith('run_browser_fixture ') and line.endswith(' personal-diary-ui'))
try:module.inert_cases(function,[call],'C:/Program Files/Git/bin/bash.exe',out)
except AssertionError as error:
    (out/'expected-failure.json').write_bytes((json.dumps({'error_type':type(error).__name__,'case':list(error.args),'scope':'Inert author harness only, not product/server failure'},indent=2)+'\n').encode())
else:raise AssertionError('Expected exact before harness failure')
print(json.dumps({'expected_failure_preserved':True,'directory':str(out)}))
