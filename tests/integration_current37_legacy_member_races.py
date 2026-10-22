"""Explicit current37 fixture companion; original 4 domain criteria remain unchanged."""
from tests.ci_web37.pg_legacy import export_group

globals().update(export_group('member-races'))
