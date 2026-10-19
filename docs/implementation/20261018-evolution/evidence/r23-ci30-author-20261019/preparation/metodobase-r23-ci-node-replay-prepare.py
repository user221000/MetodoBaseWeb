"""Correct only orchestration grouping; preserve the zero-execution attempt."""
from pathlib import Path
temp=Path(r'C:\Users\Consu\AppData\Local\Temp')
source=(temp/'metodobase-r23-ci-node-run.py').read_text(encoding='utf8')
source=source.replace('metodobase-r23-ci-node-first-20261019','metodobase-r23-ci-node-second-20261019')
source=source.replace('assert len(blocks)==3',"assert sum(sum(line.strip().startswith('node tests/e2e/') for line in block.splitlines()) for block in blocks)==23")
source=source.replace('assert len(rows)==3','assert len(rows)==len(blocks)')
target=temp/'metodobase-r23-ci-node-replay.py';assert not target.exists();target.write_bytes(source.encode())
print(str(target))
