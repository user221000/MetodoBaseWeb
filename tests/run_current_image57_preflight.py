"""Read one already leased owned guest against explicit current57 artifacts."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.ci_image57.preflight import main

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,KeyError,TypeError,AssertionError):
        print('Current57 read-only preflight rejected; private originals retained; no automatic retry.',file=sys.stderr)
        raise SystemExit(1)
