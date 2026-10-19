from pathlib import Path
import ast
import hashlib
import json
import subprocess

root=Path(r'F:\mb-saas-observability-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r17-private-boundary-fix-20261019')
assert not out.exists()
git=lambda *args:subprocess.check_output(['git',*args],cwd=root)
assert git('rev-parse','HEAD').decode().strip()=='fee219929ac2c6a16cc8d8a6bec42cb757245a4e'
assert not git('status','--porcelain','--untracked-files=no')
path=root/'web/middleware/security_headers.py';before=path.read_bytes()
text=before.decode();newline='\r\n' if '\r\n' in text else '\n'
text=text.replace('\r\n','\n')
changes=[
 ('        primary_api = request.url.path in _PRIMARY_API_PATHS\n',
  '        primary_api = request.url.path in _PRIMARY_API_PATHS\n        operations = request.url.path in {"/metrics", "/alerts", "/health/circuits"}\n'),
 ('                    and not primary_api):','                    and not primary_api\n                    and not operations):'),
 ('                or primary_api\n','                or primary_api\n                or operations\n'),
 ('        if primary_api or is_member_link_private(request.url.path) or diary_api or request.url.path.startswith("/api/auth/mfa/"):\n',
  '        if operations or primary_api or is_member_link_private(request.url.path) or diary_api or request.url.path.startswith("/api/auth/mfa/"):\n'),
 ('        # ─── Cache control para APIs',
  '        if operations:\n            response.headers["Pragma"] = "no-cache"\n        \n        # ─── Cache control para APIs'),
]
for old,new in changes:
    assert text.count(old)==1,old
    text=text.replace(old,new)
ast.parse(text)
out.mkdir();(out/'driver.py').write_bytes(Path(__file__).read_bytes())
(out/'security_headers.before.RAW.py').write_bytes(before)
(out/'security_headers.before.GitLF.py').write_bytes(git('show','HEAD:web/middleware/security_headers.py'))
after=text.replace('\n',newline).encode();path.write_bytes(after)
(out/'security_headers.after.RAW.py').write_bytes(after)
inverse=text
for old,new in reversed(changes):
    assert inverse.count(new)==1
    inverse=inverse.replace(new,old)
assert inverse==before.decode().replace('\r\n','\n')
(out/'receipt.json').write_bytes((json.dumps({'base':'fee219929ac2c6a16cc8d8a6bec42cb757245a4e',
 'exact_canonical_paths':['/metrics','/alerts','/health/circuits'],
 'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest(),
 'inverse_preserves_full_original_text_normalized_LF':True,
 'new_private_exception_scope':'Only three canonical operational routes; existing opaque factory error handler remains unchanged.'},indent=2)+'\n').encode())
print(json.dumps({'changed':'web/middleware/security_headers.py','before_preserved':True,'inverse_exact':True}))
