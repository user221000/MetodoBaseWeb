"""Exactly two reviewed public build fingerprints after all prior authorities.

The PSF OpenPGP fingerprint identifies the public Python3.12 signing key.
The second reviewed value authenticates a CPython header, not an API credential.
No historical decision, scanner rule, report field, or scan scope is changed.
"""
from __future__ import annotations

import hashlib
import os
import stat
import types
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 1024 * 1024
REASON = "finite technical-close review: two exact public build fingerprints, not credentials"
PINS = {'Dockerfile': [{'line_sha256': 'cab8904917dab7fce2b0f6f25ec6c6de3bb84ebcb660e07eed62b7fd3d89c328',
                 'source_bytes': 19328,
                 'source_sha256': 'eeac19a8ddd5ac2a3e118a83581484ae34e7e3c8d10324015439f94a02b0a8b3',
                 'span': [223, 223, 6, 54, 'generic-api-key']},
                {'line_sha256': 'b0965925b78a30cd9ec4d2910a8f67a31da2b6f0b3781aede4653e5243791855',
                 'source_bytes': 19567,
                 'source_sha256': 'bbb1b44642b230ad97816369f7de2c5f703b98700bc1524fd73a5c2696f04d98',
                 'span': [223, 223, 6, 54, 'generic-api-key']}],
 'runtime-source/technical-close-20261103/source-pins.json': [{'line_sha256': '8d8ad86bc63a3694264bc0a80054fd2ffb2b879402a8c9c81e1ba8bf309e3833',
                                                               'source_bytes': 48425,
                                                               'source_sha256': '9a1d7bd6be0c171c9b263963381afc3f61b29c8dd04d3dd8142e6bb780983d97',
                                                               'span': [156,
                                                                        156,
                                                                        46,
                                                                        128,
                                                                        'generic-api-key']},
                                                              {'line_sha256': '8cd7869c18c79375ee343e38361625f0df7a6417755a671f5343c18f97f0ccb3',
                                                               'source_bytes': 48990,
                                                               'source_sha256': 'dde4df4afcd6c2da6104af3cc16f66f8963001f815faa45050f9b30a2db62dc3',
                                                               'span': [156,
                                                                        156,
                                                                        46,
                                                                        128,
                                                                        'generic-api-key']}]}
PARENTS = {'scripts/reviewed_scan_locations.py': ((7391,
                                         'f28ff600da75ced76d05a198718993d53e6f4c72bd244ac5cd89f764026c1d11'),
                                        (7552,
                                         '366e5847e2808c05817fc9194e6713a05e60289b6c42426dd8065bc935e856da')),
 'scripts/scan_secrets.py': ((19748, 'b74c882e0b44b377fe72ef043a21409e1326c9475e6e534ae938d42403933613'),
                             (20120, '435b29cdb085f557ec81d38f5260ff0523801422d3528505e9766ac0e543f494')),
 'tests/ci_web39/__init__.py': ((70, 'ddc11faa4dfaa04bda501c17f9b56fbdfb078f39521fdd58836639e2762e1b22'),
                                (71, '8d349c2309966105e71a7ffb1fa7bcc4401e7f6fb95c9e4567c996d385a928b3')),
 'tests/ci_web39/current_secret_locations.py': ((27226,
                                                 'd15ac76a9510c590ef82a16f6d74a820f780b6ea2a1f6f982e66952d9761acb7'),
                                                (27790,
                                                 '39a9bbc0d2bd83185c080c73d14a9453b418e14ed1e4733e2f992890cf56eca2')),
 'tests/ci_web39/scan_secrets.py': ((1778,
                                     '3a96ff9f3572311235526266f8a22101771cc0a22db66a469b29660211fd347b'),
                                    (1820,
                                     '83d08c604b435474e7b96ee94854e9721c155ee809e8e2f948383ea296c1cc2e'))}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def invalid():
    raise RuntimeError("Technical reviewed scanner bootstrap invalid; output withheld") from None


def bounded(root, name, limit=LIMIT):
    root = Path(root)
    if (type(name) is not str or not name or ":" in name or "\\" in name
            or PurePosixPath(name).is_absolute() or any(part in {"", ".", ".."} for part in name.split("/"))
            or not root.is_absolute()):
        invalid()
    path = root / name
    if path.resolve(strict=True) != path.absolute():
        invalid()
    for value in (path, *path.parents):
        info = value.lstat()
        if (value.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400
                or not (stat.S_ISREG(info.st_mode) if value == path else stat.S_ISDIR(info.st_mode))):
            invalid()
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 <= before.st_size <= limit:
        invalid()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(limit + 1)
        closed = os.fstat(stream.fileno())
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    identity = lambda value: tuple(getattr(value, field) for field in fields)
    after = path.stat()
    if (len(raw) > limit or len(raw) != before.st_size or opened.st_nlink != 1
            or identity(before) != identity(opened) or identity(opened) != identity(closed)
            or identity(before) != identity(after) or before.st_ctime_ns != after.st_ctime_ns
            or opened.st_ctime_ns != closed.st_ctime_ns):
        invalid()
    if path.resolve(strict=True) != path.absolute() or path.is_symlink():
        invalid()
    return raw


def authenticate_parents(root):
    # Authenticate all project modules reachable through the historical CLI
    # before importing any of them. The bootstrap uses only standard library.
    payloads = {}
    if (Path(root) / "scripts/__init__.py").exists() or (Path(root) / "scripts/__init__.py").is_symlink():
        invalid()
    for name, frames in PARENTS.items():
        raw = bounded(root, name)
        if (len(raw), digest(raw)) not in frames:
            invalid()
        payloads[name] = raw
    from tests.ci_web39 import current_secret_locations as current
    from tests.ci_web39 import scan_secrets as prior_cli

    for name, module in (("tests/ci_web39/current_secret_locations.py", current),
                         ("tests/ci_web39/scan_secrets.py", prior_cli)):
        current.authenticate_module(module, ROOT / name, payloads[name])
    return current, prior_cli


class TechnicalLocations:
    def __init__(self, previous, snapshot, source_hashes):
        self.previous = previous
        self.snapshot = Path(snapshot)
        self.source_hashes = source_hashes
        self.used = set()

    def classify(self, item, name):
        prior = self.previous.classify(item, name)
        if prior is not None:
            return prior
        if type(name) is not str or name not in PINS:
            return None
        fields = ("StartLine", "EndLine", "StartColumn", "EndColumn", "RuleID")
        span = tuple(item.get(field) for field in fields)
        if any(type(value) is not int for value in span[:4]) or type(span[4]) is not str:
            return None
        chosen = next((frame for frame in PINS[name]
                       if self.source_hashes.get(name) == frame["source_sha256"]), None)
        if (chosen is None or span != tuple(chosen["span"]) or (name, span) in self.used):
            return None
        try:
            raw = bounded(self.snapshot, name)
            if (len(raw) != chosen["source_bytes"] or digest(raw) != chosen["source_sha256"]
                    or digest(raw.split(b"\n")[span[0] - 1]) != chosen["line_sha256"]):
                return None
            raw.decode("utf8", errors="strict")
        except (OSError, ValueError, TypeError, RuntimeError, UnicodeError, IndexError):
            return None
        self.used.add((name, span))
        return {"file": name, "line": span[0], "rule": span[4],
                "file_sha256": chosen["source_sha256"], "physical_line_sha256": chosen["line_sha256"],
                "start_column": span[2], "end_column": span[3], "reason": REASON}


def delegated_main(root=ROOT):
    _current, prior_cli = authenticate_parents(root)
    original = prior_cli.delegated_main(root)
    prior_loader = original.__globals__["load_reviewed_locations"]

    def loader(snapshot, source_hashes, version):
        authenticate_parents(snapshot)
        previous = prior_loader(snapshot, source_hashes, version)
        return TechnicalLocations(previous, snapshot, source_hashes)

    namespace = dict(original.__globals__, load_reviewed_locations=loader)
    result = types.FunctionType(original.__code__, namespace, original.__name__,
                                original.__defaults__, original.__closure__)
    if (result.__code__ is not original.__code__ or result.__globals__ is original.__globals__
            or [key for key in namespace if namespace[key] is not original.__globals__[key]]
            != ["load_reviewed_locations"]):
        invalid()
    return result


def main():
    return delegated_main()()


if __name__ == "__main__":
    raise SystemExit(main())
