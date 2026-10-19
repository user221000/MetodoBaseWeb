from pathlib import Path
import ast
import json
import subprocess

root=Path(r'F:\mb-mfa31-compose-20261019');tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
base='809eab28c40c112cb6e3c9d8caceebae28683abd';fix='6a75d096ea3d63d9e78c76d33b7e243160b23364'
out=tmp/'metodobase-terminal-sv-compose-20261019';assert not out.exists()
git=lambda *args:subprocess.check_output(['git','--no-replace-objects',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain','--untracked-files=no')
names=set(git('diff','--name-only','-z',base,fix).decode().split('\0')[:-1])
assert names=={'web/services/mfa_service.py','web/static/js/mfa-ui.js','tests/test_mfa31_terminal_session_version.py'}
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
result=subprocess.run(['git','merge','--ff-only',fix],cwd=root,capture_output=True)
(out/'merge.stdout.raw.log').write_bytes(result.stdout);(out/'merge.stderr.raw.log').write_bytes(result.stderr)
assert result.returncode==0
assert git('rev-parse','HEAD').decode().strip()==fix and not git('status','--porcelain','--untracked-files=no')
preserved=[]
for name in ['tests/ci_mfa31/current-report-nodeids.json','tests/ci_mfa31/current-business-mapping.json','tests/verify_mfa31_ci.py']:
    assert git('show',base+':'+name)==git('show',fix+':'+name);preserved.append(name)
old=tmp/'metodobase-mfa31-composed-regression.py';new=tmp/'metodobase-mfa31-composed-terminal-sv-regression.py'
source=old.read_text(encoding='utf8')
needle="out=tmp/('metodobase-mfa31-composed-'+mode+'-20261019')"
replacement="out=tmp/('metodobase-mfa31-composed-'+mode+'-terminal-sv-20261019')"
assert source.count(needle)==1
source=source.replace(needle,replacement);ast.parse(source);assert not new.exists();new.write_bytes(source.encode())
old_check=tmp/'metodobase-mfa31-broad-result-check.py';new_check=tmp/'metodobase-mfa31-terminal-sv-result-check.py'
source=old_check.read_text(encoding='utf8').replace(base,fix)
for previous,current in [
 ("'metodobase-mfa31-composed-'+mode+'-20261019'","'metodobase-mfa31-composed-'+mode+'-terminal-sv-20261019'"),
 ("'metodobase-mfa31-composed-'+mode+'-checks-20261019'","'metodobase-mfa31-composed-'+mode+'-terminal-sv-checks-20261019'"),
 ('metodobase-mfa31-composed-serial-checks-20261019','metodobase-mfa31-composed-serial-terminal-sv-checks-20261019'),
 ('metodobase-mfa31-composed-serial-20261019','metodobase-mfa31-composed-serial-terminal-sv-20261019')]:
    assert previous in source;source=source.replace(previous,current)
ast.parse(source);assert not new_check.exists();new_check.write_bytes(source.encode())
receipt={'head':fix,'base':base,'changed':sorted(names),'preserved_CI':preserved,
 'scope':'Prepared isolated candidate and fresh driver paths. Independent security and full matrix still pending. No MAIN changes.',
 'regression_driver':str(new),'result_check_driver':str(new_check)}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps(receipt))
