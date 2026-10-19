"""Verify a desktop manifest; explicitly opt in to the isolated Qt diagnostic."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

from build import APP_NAME, BASE_DIR, BuildError, validate_bundle, verify_manifest


def gui_smoke(bundle: Path, timeout: float = 30) -> dict:
    if not math.isfinite(timeout) or timeout <= 0:
        raise BuildError("Diagnostic timeout must be finite and positive")
    verify_manifest(bundle)
    executable = validate_bundle(bundle)
    with tempfile.TemporaryDirectory(prefix="metodobase-desktop-smoke-") as temporary:
        root = Path(temporary).resolve()
        nonce = secrets.token_hex(32)
        (root / ".desktop-smoke-marker").write_text(nonce, encoding="ascii")
        allowed = {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATH", "PATHEXT", "TMP", "TEMP", "LANG", "LC_ALL"}
        env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        env.update({"METODOBASE_DESKTOP_SMOKE_DIR": str(root), "METODOBASE_DESKTOP_SMOKE_NONCE": nonce,
                    "METODOBASE_DATA_DIR": str(root / "data"), "APPDATA": str(root / "appdata"),
                    "LOCALAPPDATA": str(root / "localappdata"), "USERPROFILE": str(root / "home"),
                    "HOME": str(root / "home"), "XDG_DATA_HOME": str(root / "home"),
                    "PYTHON_DOTENV_DISABLED": "1", "QT_QPA_PLATFORM": "offscreen",
                    "METODOBASE_ENV": "testing", "SENTRY_DSN": "", "AWS_EC2_METADATA_DISABLED": "true"})
        for name in ("data", "home", "appdata", "localappdata"):
            (root / name).mkdir()
        try:
            result = subprocess.run([str(executable)], cwd=root, env=env, capture_output=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BuildError("Desktop offscreen diagnostic did not complete") from exc
        if result.returncode != 0:
            raise BuildError("Desktop offscreen diagnostic failed")
        try:
            receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
            if not (isinstance(receipt, dict) and receipt.get("nonce") == nonce and receipt.get("ok") is True and
                    receipt.get("qt_platform") == "offscreen" and receipt.get("python_network_blocked") is True):
                raise BuildError("Desktop diagnostic receipt is invalid")
        except (OSError, ValueError, TypeError) as exc:
            raise BuildError("Desktop diagnostic receipt is missing or invalid") from exc
        return {key: value for key, value in receipt.items() if key != "nonce"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=BASE_DIR / "dist" / APP_NAME)
    parser.add_argument("--gui-smoke", action="store_true", help="Explicitly launch isolated offscreen diagnostic")
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    try:
        verify_manifest(args.bundle)
        print(json.dumps(gui_smoke(args.bundle, args.timeout) if args.gui_smoke else
                         {"manifest_verified": True, "gui_executed": False}, sort_keys=True))
        return 0
    except BuildError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
