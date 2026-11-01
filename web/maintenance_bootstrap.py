"""Install the private maintenance seed before starting a web worker."""
from __future__ import annotations

import os
from pathlib import Path
import stat
import sys
import tempfile

SEED_ENV = "METODOBASE_MAINTENANCE_BOOTSTRAP"
FILE_ENV = "METODOBASE_MAINTENANCE_FILE"


def install_control() -> bool:
    seed = os.environ.get(SEED_ENV, "")
    configured_path = os.environ.get(FILE_ENV, "")
    if not seed and not configured_path:
        return False
    if not seed or not configured_path:
        raise ValueError("Incomplete maintenance bootstrap configuration")

    from web.middleware.maintenance import MAX_CONTROL_BYTES, _read_control

    raw = seed.encode("utf8")
    if len(raw) > MAX_CONTROL_BYTES:
        raise ValueError("Invalid maintenance bootstrap document")
    target = Path(configured_path)
    if not target.is_absolute() or target.name != "maintenance.json":
        raise ValueError("Invalid maintenance control location")
    directory = target.parent
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or directory.is_symlink():
        raise ValueError("Unsafe maintenance control directory")
    if os.name == "posix" and (info.st_uid != os.getuid()
                                or stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError("Unsafe maintenance control directory permissions")
    if target.exists() or target.is_symlink():
        info = target.lstat()
        if not stat.S_ISREG(info.st_mode) or target.is_symlink():
            raise ValueError("Unsafe existing maintenance control")
        if os.name == "posix" and (info.st_uid != os.getuid()
                                    or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError("Unsafe existing maintenance control permissions")

    descriptor, temporary = tempfile.mkstemp(prefix=".control-", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            if os.name == "posix":
                os.fchmod(stream.fileno(), 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if not _read_control(temporary).valid:
            raise ValueError("Invalid maintenance bootstrap document")
        os.replace(temporary, target)
        if os.name == "posix":
            descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        # Remove only this invocation's unpublished temporary, never the control.
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def main() -> int:
    try:
        install_control()
    except Exception:
        # Provider output must never contain the seed, token or file contents.
        print("Maintenance bootstrap failed; web worker was not started.", file=sys.stderr)
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
