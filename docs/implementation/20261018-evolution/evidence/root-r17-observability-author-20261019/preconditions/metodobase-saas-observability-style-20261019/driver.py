from pathlib import Path
import ast
import hashlib
import json
import subprocess

root=Path(r'F:\mb-saas-observability-20261019')
names=['web/observability/routes.py','tests/test_saas_observability_contract.py','api/app.py','web/middleware/metrics.py']
before={n:(root/n).read_bytes() for n in names}
trees={n:ast.dump(ast.parse(b),include_attributes=False) for n,b in before.items()}
quality=r'C:\Users\Consu\AppData\Local\Temp\metodobase-qa-20261018\Scripts\python.exe'
result=subprocess.run([quality,'-m','ruff','format',*names[:2]],cwd=root,capture_output=True)
assert result.returncode==0
p=root/'api/app.py'
text=p.read_text(encoding='utf8')
lines=text.splitlines(keepends=True)
p.write_text(''.join(line for line in lines if not line.strip().startswith('# '+chr(0x2500)*2+' Metrics')),encoding='utf8',newline='\n')
p=root/'web/middleware/metrics.py'
p.write_bytes(p.read_bytes().rstrip(b'\r\n')+b'\n')
assert all(ast.dump(ast.parse((root/n).read_bytes()),include_attributes=False)==trees[n] for n in names)
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-saas-observability-style-20261019')
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'ruff.stdout.raw.log').write_bytes(result.stdout)
(out/'ruff.stderr.raw.log').write_bytes(result.stderr)
(out/'receipt.json').write_bytes((json.dumps({'AST_exact_all4':True,'before_RAW_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in before.items()},'after_RAW_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names}},indent=2)+'\n').encode())
baseline=Path(r'F:\mb-mfa31-compose-20261019\tests\_probe_saas_observability.py')
assert not baseline.exists()
baseline.write_bytes((root/'tests/test_saas_observability_contract.py').read_bytes())
print(json.dumps({'style_AST_exact':True,'baseline_probe_source_exact':True,'baseline_product_unchanged':True}))
