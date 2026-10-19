"""Preserve CI29 source before adapting only its current runtime fixture."""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
ROOT=Path('F:/mb-member-browser30-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/member-browser30-author-20261019'
OUT.mkdir(exist_ok=False)
(OUT/'.gitattributes').write_bytes(b'* -text\n')
TEMP=Path(tempfile.mkdtemp(prefix='metodobase-member-browser30-author-'))
names=['tests/e2e/member_link_postgres_server.py','tests/e2e/run_member_link_browser.py',
       'tests/e2e/member_link_browser.cjs','tests/e2e/normalize_member_link_report.py',
       'tests/test_member_browser_gate.py']
sha=lambda data:hashlib.sha256(data).hexdigest()
with zipfile.ZipFile(OUT/'before29-exact.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name in names:archive.writestr(name,(ROOT/name).read_bytes())
(OUT/'before-source.json').write_text(json.dumps({name:{'raw_sha256':sha((ROOT/name).read_bytes()),
    'git_lf_sha256':sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))} for name in names},indent=2)+'\n',encoding='utf8')
(TEMP/'location.json').write_text(json.dumps({'temp':str(TEMP),'evidence':str(OUT)})+'\n',encoding='utf8')
print(json.dumps({'temp':str(TEMP),'evidence':str(OUT)}))
