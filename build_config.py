"""Read-only compatibility metadata; the sole recipe is MetodoBase.spec."""
from pathlib import Path

from build import APP_NAME, BASE_DIR, HIDDEN_IMPORTS, collect_resources, read_version

APP_VERSION = read_version(BASE_DIR)
APP_AUTHOR = "MetodoBase"
SPEC_FILE = BASE_DIR / "MetodoBase.spec"
PYINSTALLER_CONFIG = {
    "name": APP_NAME, "onefile": False, "windowed": True,
    "entry_point": "main.py", "spec_file": str(SPEC_FILE),
}


def resource_data(root: Path = BASE_DIR) -> list[tuple[str, str]]:
    """Use the same tracked, per-file resource inventory as the spec."""
    return collect_resources(root)
