"""Preserve distinct LF root and CRLF QA RAW sources with equal Git content."""
from pathlib import Path
import runpy
source=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r12-controls-author.py').read_text(encoding='utf8')
assert source.count('metodobase-r12-controls-author-20261019')==1
source=source.replace('metodobase-r12-controls-author-20261019','metodobase-r12-controls-author-v3-20261019')
needle="target=root/'tests/e2e/member_link_controls.cjs';assert not target.exists();target.write_bytes(driver)"
assert source.count(needle)==1;source=source.replace(needle,"target=root/'tests/e2e/member_link_controls.cjs';assert target.read_bytes()==driver")
needle="assert sha(old)=='b582e61feaa9753e6460e077d6387d4207a8cf33efea49dbb92ea720d23f7653'"
replacement="assert sha(old)=='fe109ac13ae8584530efc8c98ee1137031c7442fb9dfb7fa3efe49536625c5de'\nassert old==subprocess.check_output(['git','show','HEAD:web/static/js/vinculos-ui.js'],cwd=root)\nassert sha(old.replace(b'\\n',b'\\r\\n'))=='b582e61feaa9753e6460e077d6387d4207a8cf33efea49dbb92ea720d23f7653'"
assert source.count(needle)==1;source=source.replace(needle,replacement)
target=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-r12-controls-author-executed-v3.py');assert not target.exists();target.write_bytes(source.encode())
runpy.run_path(str(target),run_name='__main__')
