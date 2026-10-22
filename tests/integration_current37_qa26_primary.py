"""Original QA26 seven:6 real HTTP cases +1 finite ASGI case; current37 PG."""
from tests.ci_web37.pg_originals import primary9

globals().update(primary9("test_security_qa26_primary_peer.py"))
