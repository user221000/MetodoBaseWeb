"""Witness that old explicit revision29 assertions need an explicit target after head30."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(r'F:\mb-r12-history30-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-history30-historical29-before-20261019');out.mkdir(exist_ok=False)
source=root/'tests/integration_client_link_migrations.py';(out/'original.py').write_bytes(source.read_bytes())
result=subprocess.run([sys.executable,'-X','utf8','-B','tests/run_isolated.py','tests/integration_client_link_migrations.py','-k','sqlite','-q','--tb=short','--junitxml='+str(out/'tests.xml')],cwd=root,capture_output=True,timeout=120)
(out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr)
receipt={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'exit':result.returncode,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_unchanged':source.read_bytes()==(out/'original.py').read_bytes(),'scope':'Actual old revision29 SQLite migration tests under current model30. No PG or new production change.'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');print(json.dumps(receipt))
assert result.returncode!=0 and receipt['source_unchanged']
