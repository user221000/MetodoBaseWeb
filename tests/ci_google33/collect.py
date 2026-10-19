"""Collect exact maintained identities only; never executes fixtures or SQL."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


class Collector:
    def __init__(self,output):self.output=output;self.identities=[]

    def pytest_collection_finish(self,session):
        # -k and other selectors finish in collection_modifyitems. Capturing
        # there could silently include deselected SQLite nodes in a PG oracle.
        for item in session.items:
            path,name=item.nodeid.split('::',1)
            assert '::' not in name,'Class-based collection requires explicit JUnit mapping'
            module=path.removesuffix('.py').replace('/','.').replace('\\','.')
            self.identities.append([module,name])

    def pytest_sessionfinish(self,session,exitstatus):
        if exitstatus==0:
            assert len(self.identities)==len({tuple(row) for row in self.identities})
            with self.output.open('x',encoding='utf8') as out:json.dump(self.identities,out,indent=2);out.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args,modules=parser.parse_known_args();assert modules and not args.output.exists()
    from tests.isolation import block_external_sockets, prepare_environment
    prepare_environment(discard_inherited=True);block_external_sockets()
    import pytest
    return pytest.main(['--collect-only','-q',*modules],plugins=[Collector(args.output)])


if __name__=='__main__':raise SystemExit(main())
