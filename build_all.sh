#!/usr/bin/env bash
# Native build only: Linux/macOS need their own reviewed runtime/tooling locks.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON_EXE="${METODOBASE_BUILD_PYTHON:-python3}"
if [[ "${1:-}" == "macos" ]]; then
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "macOS artifacts must be built and validated on macOS." >&2
    exit 1
  fi
  shift
fi
# No source replacement, implicit installation, DMG creation or signing.
exec "$PYTHON_EXE" build.py --zip "$@"
