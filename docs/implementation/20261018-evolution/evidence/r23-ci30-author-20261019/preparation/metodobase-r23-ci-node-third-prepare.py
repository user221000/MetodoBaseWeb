from pathlib import Path
source=Path(__file__).with_name('metodobase-r23-ci-node-replay.py').read_text()
old=' local script="$1"; shift\n local args=()'
new=' if [[ "$1" == -* ]]; then "$CI_NODE" "$@"; return; fi\n local script="$1"; shift\n local args=()'
assert source.count(old)==1
source=source.replace(old,new).replace('metodobase-r23-ci-node-second-20261019','metodobase-r23-ci-node-third-20261019')
Path(__file__).with_name('metodobase-r23-ci-node-third.py').write_text(source)
