"""Exact source successor for the published merged production root layer.

This authenticates source bytes and proves an append-only inverse to the
already reviewed APT child. It does not certify a build or image containment.
The original APT and native Merkle authorities remain unchanged.
"""
from __future__ import annotations

import hashlib

PARENT_BYTES = 24652
PARENT_SHA256 = "cddd4f4103ac0954ce3b93fed71e35a7b2525d5fab588279a78f1f5376342586"
SUFFIX_BYTES = 2120
SUFFIX_SHA256 = "c610675d5a54d8509474ea5418c9eccf6af4db32ce838dbff6fd007998462574"
DOCKER_PIN = {"bytes": 26772,
              "raw_sha256": "601f9953e0c78c46181899de402b6fb04cf3a6bc4515e0c3122ee719dca317c5",
              "git_blob": "b909b444872af0d73b1aca9a04c1166ecb10a514"}


def transition(parent_transition):
    return {"schema": "current57-production-root-layer-source-child-v1",
            "parent_transition": parent_transition,
            "Dockerfile": dict(DOCKER_PIN),
            "append_only_inverse": {"parent_bytes": PARENT_BYTES,
                "parent_sha256": PARENT_SHA256, "suffix_bytes": SUFFIX_BYTES,
                "suffix_sha256": SUFFIX_SHA256},
            "scope": "exact_source_transition_no_build_or_runtime_claim"}


def inverse(raw):
    if (type(raw) is not bytes or len(raw) != DOCKER_PIN["bytes"]
            or hashlib.sha256(raw).hexdigest() != DOCKER_PIN["raw_sha256"]):
        raise ValueError("Exact production Docker source identity differs")
    parent, suffix = raw[:PARENT_BYTES], raw[PARENT_BYTES:]
    if (len(suffix) != SUFFIX_BYTES or hashlib.sha256(parent).hexdigest() != PARENT_SHA256
            or hashlib.sha256(suffix).hexdigest() != SUFFIX_SHA256):
        raise ValueError("Production root-layer inverse did not recover the exact APT child")
    return parent
