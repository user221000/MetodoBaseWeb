"""The V7-only original assertion capsule; original V5/V6 capsule stays intact."""
import hashlib
import json

from tests.ci_web37.git_history import FIXTURES, HistoryProof

MANIFEST_SHA256 = "b81f4bde3e9c7a62bccac1e025d3ac7c81e2694fbb668a52f53f609fab68c2f9"


def load():
    raw = (FIXTURES / "r05-v7-history.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("The finite original V7 historical manifest differs")
    return HistoryProof((FIXTURES / "r05-v7-history-objects.zip").read_bytes(), json.loads(raw))
