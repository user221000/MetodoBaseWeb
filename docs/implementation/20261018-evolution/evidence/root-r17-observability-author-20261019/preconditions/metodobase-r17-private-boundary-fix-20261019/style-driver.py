from pathlib import Path
import ast
import json
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp')
root=Path(r'F:\mb-saas-observability-20261019')
file=root/'web/middleware/security_headers.py'
before=file.read_bytes();text=before.decode()
needle='            response.headers["Pragma"] = "no-cache"\r\n        \r\n'
assert text.count(needle)==1
after=text.replace(needle,'            response.headers["Pragma"] = "no-cache"\r\n\r\n').encode()
assert ast.dump(ast.parse(before))==ast.dump(ast.parse(after))
proof=tmp/'metodobase-r17-private-boundary-fix-20261019'
(proof/'before-trailing-blank-style.RAW.py').write_bytes(before)
file.write_bytes(after);(proof/'after-trailing-blank-style.RAW.py').write_bytes(after)
(proof/'style-driver.py').write_bytes(Path(__file__).read_bytes())
source=(tmp/'metodobase-saas-observability-freeze.py').read_text(encoding='utf8')
start=source.index('names=');end=source.index('subprocess.run([\'git\',\'diff\',\'--check\']')
source=source[:start]+'''names=['web/middleware/security_headers.py']
git=lambda *args:subprocess.check_output(['git',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()=='fee219929ac2c6a16cc8d8a6bec42cb757245a4e'
assert set(git('diff','--name-only','-z').decode().split('\\0')[:-1])==set(names)
'''+source[end:]
source=source.replace('metodobase-saas-observability-frozen-20261019','metodobase-r17-boundary-frozen-20261019')
source=source.replace('Mount private operational metrics in both application factories','Protect canonical operational method and error responses')
source=source.replace("'bd34893c4b6f806041b0cc6b7f156e9286886748'","'fee219929ac2c6a16cc8d8a6bec42cb757245a4e'")
source=source.replace("'tests/test_metrics_privacy_contract.py','tests/test_metrics_privacy_review.py','-q'","'tests/test_metrics_privacy_contract.py','tests/test_metrics_privacy_review.py','tests/test_security_hardening.py','-q'")
source=source.replace("'prior_directed':{'cases':103,'exit':0,'after_style_full_AST_exact':True},","'prior_directed':{'cases':103,'exit':0,'before_security_private_boundary_review':True},")
target=tmp/'metodobase-r17-boundary-freeze.py';assert not target.exists()
ast.parse(source);target.write_bytes(source.encode())
print(json.dumps({'prepared':str(target),'style_AST_exact':True}))
