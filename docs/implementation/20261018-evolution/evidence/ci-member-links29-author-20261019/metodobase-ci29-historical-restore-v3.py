"""Supply the documented CI evidence directory; preserve earlier preparation/error."""
from pathlib import Path
import runpy
source=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-historical-restore-executed-v2.py').read_text(encoding='utf8')
assert source.count('metodobase-ci29-historical-restore-v2-20261019')==1
source=source.replace('metodobase-ci29-historical-restore-v2-20261019','metodobase-ci29-historical-restore-v3-20261019')
needle="for phase in ['before']:"
assert source.count(needle)==1
source=source.replace(needle,"(out/'evidence').mkdir()\nenvironment['METODOBASE_TEST_EVIDENCE_DIR']=str(out/'evidence')\n"+needle)
target=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-historical-restore-executed-v3.py')
assert not target.exists();target.write_bytes(source.encode())
runpy.run_path(str(target),run_name='__main__')
