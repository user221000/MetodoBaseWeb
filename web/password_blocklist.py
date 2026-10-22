"""Pinned offline blocklist for newly selected passwords, never for login.

The distributed file contains sorted full SHA-256 digests of public SecLists
entries, not hashes of this service's users. No network or normalization is
involved. Read and authenticate the bounded artifact for every validation so a
missing or changed file fails closed even after an earlier successful use.
"""
from hashlib import sha256
from pathlib import Path

_CORPUS_PATH = Path(__file__).parent / "data" / "password-blocklist" / "seclists-100k.sha256bin"
_CORPUS_BYTES = 3_199_968
_CORPUS_SHA256 = "d0d787734cd3ad38731ca3012e34532ff109e915feeb152cbf0fbd361c27c101"
_DIGEST_BYTES = 32


def contains_password(encoded: bytes) -> bool:
    """Compare the entire UTF-8 value; raise only a fixed error on failure."""
    try:
        with _CORPUS_PATH.open("rb") as source:
            corpus = source.read(_CORPUS_BYTES + 1)
    except OSError:
        raise ValueError("No se pudo comprobar la contraseña. Intenta de nuevo más tarde.") from None
    if len(corpus) != _CORPUS_BYTES or sha256(corpus).hexdigest() != _CORPUS_SHA256:
        raise ValueError("No se pudo comprobar la contraseña. Intenta de nuevo más tarde.")

    wanted = sha256(encoded).digest()
    lower, upper = 0, len(corpus) // _DIGEST_BYTES
    while lower < upper:
        middle = (lower + upper) // 2
        offset = middle * _DIGEST_BYTES
        found = corpus[offset:offset + _DIGEST_BYTES]
        if found < wanted:
            lower = middle + 1
        elif found > wanted:
            upper = middle
        else:
            return True
    return False
