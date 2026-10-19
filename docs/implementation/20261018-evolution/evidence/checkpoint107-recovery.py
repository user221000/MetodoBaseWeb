"""Correct a bookkeeping assertion: seven rows add nine evidence links."""
from pathlib import Path
import shutil

original=Path('C:/Users/Consu/AppData/Local/Temp/metodobase-checkpoint107-recovery-20261019.py')
preimage=Path('F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence/checkpoint107-recovery-first.py')
assert not preimage.exists()
shutil.copyfile(original,preimage)
source=original.read_text(encoding='utf-8')
assert source.count('assert corrected==11,corrected')==1
source=source.replace('assert corrected==11,corrected','assert corrected==9,corrected')
source=source.replace('Corrected only11new links','Corrected only9new links; the first recovery had an incorrect expected count11 and stopped before writing; its source is retained')
source=source.replace('raw.extend([driver,recovery,receipt])','raw.extend([driver,recovery,receipt,preimage])')
exec(compile(source,str(original)+'::nine-link-count', 'exec'),globals())
