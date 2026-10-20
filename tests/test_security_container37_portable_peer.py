"""Explicit Linux/fresh-checkout companion for the original forty peer cases."""
from tests.ci_web37.container_peer_portable import (
    export_tests,
    input_copy,
    original_expat_source,
)

globals().update(export_tests())

__all__ = ["input_copy", "original_expat_source"]
