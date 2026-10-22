"""Sixteen original R22 real HTTP criteria, admin setup/restricted37 runtime."""
from tests.ci_web37.pg_onboarding import export

globals().update(export("tests/test_onboarding22_facts.py", __name__))
