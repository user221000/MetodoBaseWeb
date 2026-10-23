"""Authenticated v8 reader for its unchanged historical assertion bodies."""
import hashlib
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tests/fixtures/r05-v8-reader-original.py.RAW"
PIN = "bca03e24026a60511312019fdb2c9bde39de598dc1c74097c7f660370fb68cf3"


def original_source():
    raw = RAW.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN:
        raise RuntimeError("The authenticated historical v8 reader differs")
    return raw


review = ModuleType("r05_authenticated_historical_v8")
review.__file__ = str(RAW)
exec(compile(original_source(), str(RAW), "exec"), review.__dict__)
