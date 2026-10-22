"""Real CLI report gate; diagnostic successes require a complete typed report."""
import argparse,hashlib,json,sys
from pathlib import Path
from .context import json_object
from .probe import validate_report

def main(argv=None):
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--contract-sha256',required=True)
    parser.add_argument('--source',required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args(argv)
    raw=args.contract.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=args.contract_sha256:raise ValueError('Input contract hash differs')
    contract=json_object(raw)
    if contract['source']!=args.source or contract['schema']!='current-image57-input-v1':raise ValueError('Input source or schema differs')
    result=validate_report(json_object(args.report.read_bytes()),contract)
    print(json.dumps(result))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,KeyError,TypeError,AssertionError):
        print('Current57 report rejected; private diagnostics retained.',file=sys.stderr)
        raise SystemExit(1)
