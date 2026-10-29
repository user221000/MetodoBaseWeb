"""Current39 CLI: unchanged complete scanner plus three finite public locations."""
from __future__ import annotations

import types
from pathlib import Path

from scripts import reviewed_scan_locations as review
from scripts import scan_secrets as scanner
from tests.ci_web39 import current_secret_locations as current

ROOT = Path(__file__).resolve().parents[2]


def delegated_main(root=ROOT):
    document = current.read_registry(root)
    sources = current.authenticate_sources(root, document)
    current.authenticate_module(review, root / 'scripts/reviewed_scan_locations.py',
                                sources['scripts/reviewed_scan_locations.py'])
    current.authenticate_module(scanner, root / 'scripts/scan_secrets.py',
                                sources['scripts/scan_secrets.py'])
    original = scanner.main
    if (scanner.ROOT.resolve() != root.resolve() or original.__globals__ is not vars(scanner)
            or scanner.load_reviewed_locations is not review.load_reviewed_locations):
        current.invalid()
    private = dict(original.__globals__)
    private['load_reviewed_locations'] = current.adapted_loader(root, document, review)
    result = types.FunctionType(original.__code__, private, original.__name__,
                                original.__defaults__, original.__closure__)
    if (result.__code__ is not original.__code__ or result.__globals__ is original.__globals__
            or [k for k in private if private[k] is not original.__globals__[k]]
            != ['load_reviewed_locations']):
        current.invalid()
    return result


def main():
    return delegated_main()()


if __name__ == '__main__':
    raise SystemExit(main())
