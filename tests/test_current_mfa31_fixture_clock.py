"""Real HTTP fixture authentication remains deterministic at a TOTP boundary."""
from datetime import UTC, datetime, timedelta

import pytest

from tests import current_google33_publication_fixtures as fixture_contract

case = fixture_contract.case
http = fixture_contract.http
link_db = fixture_contract.link_db


@pytest.fixture(autouse=True)
def crossed_counter(monkeypatch):
    from tests.ci_mfa31 import current_link_fixtures
    from web.services import mfa_service
    from web.services.mfa_crypto import totp

    # Both instants are recent enough for genuine primary/factor freshness.
    # Simulate generation immediately before, and delivery immediately after,
    # one real 30-second counter boundary; no identity/API is replaced.
    generated = (datetime.now(UTC) - timedelta(minutes=2)).replace(second=29, microsecond=900000)
    arrival = generated + timedelta(milliseconds=200)
    seed = b"12345678901234567890"
    # A fixed RFC test seed makes the precondition inspectable without ever
    # storing a returned seed, recovery kit, access pair or operation grant.
    assert totp(seed, int(generated.timestamp()) // 30) != totp(seed, int(arrival.timestamp()) // 30)

    class GeneratorClock:
        @staticmethod
        def now(_zone=None):
            return generated

    original_instant = mfa_service.instant
    original_entropy = mfa_service.secrets.token_bytes
    monkeypatch.setattr(current_link_fixtures, "datetime", GeneratorClock)
    monkeypatch.setattr(mfa_service, "instant", lambda supplied=None:
        original_instant(arrival if supplied is None else supplied))
    monkeypatch.setattr(mfa_service.secrets, "token_bytes", lambda size=32:
        seed if size == 20 else original_entropy(size))


@pytest.mark.parametrize("link_db", ["sqlite"], indirect=True)
def test_real_fixture_uses_one_mfa_clock_across_counter_boundary(http):
    client = http["client_http"]
    for key in ("gym", "othergym", "person", "other"):
        headers = http["headers"][key]
        assert client.get("/api/auth/me", headers=headers).status_code == 200
        status = client.get("/api/auth/mfa/status", headers=headers)
        assert status.status_code == 200 and status.json()["enabled"] is True
        assert status.json()["recovery_codes_remaining"] == 7
