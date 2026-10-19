import hashlib,json,subprocess
from pathlib import Path
root=Path('F:/mb-r12-full29-20261019');relative='web/static/js/vinculos-ui.js'
raw=(root/relative).read_bytes();git=subprocess.check_output(['git','show','HEAD:'+relative],cwd=root)
sha=lambda value:hashlib.sha256(value).hexdigest()
print(json.dumps({'RAW':sha(raw),'LF':sha(raw.replace(b'\r\n',b'\n')),'Git':sha(git),'CRLF_representation':sha(git.replace(b'\n',b'\r\n')),'RAW_bytes':len(raw),'Git_bytes':len(git),'CRLF':raw.count(b'\r\n'),'CRCRLF':raw.count(b'\r\r\n'),'LF_equal_Git':raw.replace(b'\r\n',b'\n')==git,'UTF8_roundtrip':raw.decode('utf8').encode()==raw}))
