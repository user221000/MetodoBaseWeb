"""Portable new current57 entrypoint; historical image33 is unchanged."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.ci_image57.run import main

if __name__=='__main__':
    try:
        if len(sys.argv)>1 and sys.argv[1]=='check-report':
            from tests.ci_image57.check_report import main as check_main
            raise SystemExit(check_main(sys.argv[2:]))
        raise SystemExit(main())
    except (OSError,ValueError,KeyError,TypeError,AssertionError):
        print('Current57 gate rejected; private evidence retained; no automatic retry.',file=sys.stderr)
        raise SystemExit(1)
