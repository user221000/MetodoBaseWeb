"""Shared content version for the static files served by either web factory."""
import hashlib
from pathlib import Path


def compute_static_version(directory: Path) -> str:
    """Preserve the Web JS/CSS byte-order cache key; not a security digest."""
    digest = hashlib.md5(usedforsecurity=False)
    if directory.exists():
        for file in sorted(directory.rglob("*")):
            if file.is_file() and file.suffix in (".js", ".css"):
                digest.update(file.read_bytes())
    return digest.hexdigest()[:10]
