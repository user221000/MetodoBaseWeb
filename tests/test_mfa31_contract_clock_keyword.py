"""The temporary test clock preserves the original named-now call signature."""
from datetime import timedelta
from inspect import signature
import pytest


def test_fixture_clock_keeps_named_default_and_original_validation():
    from tests import mfa31_contract_client as helper
    from web.services import mfa_service as service
    original=service.instant;explicit=original()-timedelta(seconds=10)
    try:
        with helper._authentication_clock() as fixed:
            assert signature(service.instant)==signature(original)
            assert service.instant(now=None)==fixed
            assert service.instant(now=explicit)==original(now=explicit)
            with pytest.raises(ValueError):service.instant(now=explicit.replace(tzinfo=None))
    finally:
        assert service.instant is original
        assert helper._AUTHENTICATION_INSTANT.get() is None
