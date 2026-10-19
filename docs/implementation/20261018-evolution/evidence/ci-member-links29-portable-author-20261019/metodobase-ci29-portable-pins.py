"""Anchor the exact accepted/browser boundary sources and prove bounded adaptations."""
import ast,hashlib,json,subprocess
from pathlib import Path
root=Path(r'F:\mb-r12-ci29-20261019')
path=root/'tests/verify_member_links_ci.py';text=path.read_text(encoding='utf-8-sig').replace('\r\n','\n')
tree=ast.parse(text)
node=next(item for item in tree.body if isinstance(item,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='PINNED_CURRENT_GATES' for target in item.targets))
pins=ast.literal_eval(node.value)
new=['tests/e2e/member_link_postgres_server.py','tests/e2e/member_link_browser.cjs','tests/e2e/normalize_member_link_report.py','tests/e2e/run_member_link_browser.py','tests/e2e/member_link_controls.cjs','tests/e2e/member_link_export.cjs']
for name in new:pins[name]=hashlib.sha256((root/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
lines=text.splitlines(keepends=True)
lines[node.lineno-1:node.end_lineno]=['PINNED_CURRENT_GATES = {\n']+["    "+repr(name)+": "+repr(digest)+",\n" for name,digest in pins.items()]+['}\n']
path.write_bytes(''.join(lines).encode())
original=Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/qa-r12-composition29-independent-20261019/afterec/portable')
server=(root/'tests/e2e/member_link_postgres_server.py').read_bytes().replace(b'\r\n',b'\n')
server_inverse=server.replace(b"['git','status','--porcelain','--untracked-files=no']",b"['git','status','--porcelain']").replace(b'import argparse,hashlib,json,os,re,subprocess,threading,uuid,tempfile',b'import argparse,hashlib,json,os,re,subprocess,threading,time,uuid,tempfile').replace(b'from sqlalchemy.orm import Session\n',b'from sqlalchemy.orm import Session,sessionmaker\n')
assert server_inverse==(original/'real29_server.py').read_bytes().replace(b'\r\n',b'\n')
assert (root/'tests/e2e/member_link_browser.cjs').read_bytes()==(original/'real29_browser.cjs').read_bytes()
assert (root/'tests/e2e/normalize_member_link_report.py').read_bytes()==(original/'normalize_browser_report.py').read_bytes()
export=(root/'tests/e2e/member_link_export.cjs').read_bytes().replace(b'\r\n',b'\n')
export_before=subprocess.check_output(['git','show','HEAD:tests/e2e/member_link_export.cjs'],cwd=root)
before_line=next(line for line in export_before.splitlines() if line.startswith(b'for(const bad of [{...linked(),status:'))
after_line=next(line for line in export.splitlines() if line.startswith(b'for(const [field,bad] of '))
assert export.replace(after_line,before_line)==export_before
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-ci29-portable-pins-20261019.json');assert not out.exists()
out.write_text(json.dumps({'pins':pins,'browser_accepted_byte_exact':True,'normalizer_accepted_byte_exact':True,'server_inverse_byte_exact':True,'server_changes':['Tracked-clean check allows generated untracked reports','Remove two unused imports; no criteria change'],'export_inverse_byte_exact':True,'export_changes':'One loop header distinguishes status/recipient_user_id/publication labels; identical three objects and assertion body'},indent=2)+'\n',encoding='utf8')
print(json.dumps({'pinned_executables':len(pins),'browser_and_normalizer_byte_exact':True,'server_and_export_inverse_exact':True}))
