from pathlib import Path
import hashlib
import json
import subprocess
import sys

root=Path(r'F:\mb-mfa31-reviewed-common-20261019')
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
serial=tmp/'metodobase-mfa31-reviewed-serial-20261019'
out=tmp/'metodobase-mfa31-reviewed-serial-coverage-check-20261019'
assert not out.exists()
sha=lambda data:hashlib.sha256(data).hexdigest()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()
assert head=='de506b6077ba055587f02e7d839387e7f5c56f84'
summary=json.loads((serial/'summary.private.json').read_bytes())
assert summary['exit']==0 and summary['cases']==3057 and not summary['failures']
assert summary['sources_packages_python_exact'] and summary['pip_before']==summary['pip_after']==0
assert json.loads((serial/'case-preservation.json').read_bytes())['baseline3047_preserved']
coverage=serial/'coverage.json';before=sha(coverage.read_bytes())
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
result=subprocess.run([sys.executable,'-X','utf8','-B','tests/check_coverage.py',str(coverage)],cwd=root,capture_output=True)
(out/'stdout.raw.log').write_bytes(result.stdout);(out/'stderr.raw.log').write_bytes(result.stderr)
assert result.returncode==0 and sha(coverage.read_bytes())==before
receipt={'head':head,'coverage_JSON_sha256':before,'coverage_gate_source_sha256':sha((root/'tests/check_coverage.py').read_bytes()),
 'exit':result.returncode,'prior_serial_source_and_package_quiet':True,'scope':'Actual canonical coverage gate over the closed3057 serial coverage JSON; no rerun or mutation of the serial result.'}
(out/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(result.stdout.decode())
print(json.dumps(receipt))
