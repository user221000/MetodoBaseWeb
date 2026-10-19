"""Repair pre-DB encoding typo; retain the original preparation attempt."""
from pathlib import Path
import runpy
source=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-historical-restore.py').read_text(encoding='utf8')
assert source.count("encoding='utf8-sig'")==1
assert source.count('metodobase-ci29-historical-restore-20261019')==1
source=source.replace("encoding='utf8-sig'","encoding='utf-8-sig'").replace('metodobase-ci29-historical-restore-20261019','metodobase-ci29-historical-restore-v2-20261019')
target=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-ci29-historical-restore-executed-v2.py')
assert not target.exists();target.write_bytes(source.encode())
runpy.run_path(str(target),run_name='__main__')
