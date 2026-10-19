"""Reproduce a TOTP counter crossing in the actual current31 HTTP fixture."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

repo = Path(r'F:\mb-mfa31-compose-20261019')
root = Path(r'F:\mb-mfa31-clock-fixture-20261019')
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-mfa31-fixture-clock-source-20261019')
head = '6a75d096ea3d63d9e78c76d33b7e243160b23364'
assert not root.exists() and not out.exists()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).decode().strip() == head
assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repo)
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
result = subprocess.run(['git', '-c', 'core.autocrlf=false', 'worktree', 'add', '-b',
    'implementation/mfa31-fixture-clock-20261019', str(root), head], cwd=repo, capture_output=True)
(out / 'worktree.stdout.raw.log').write_bytes(result.stdout)
(out / 'worktree.stderr.raw.log').write_bytes(result.stderr)
assert result.returncode == 0
path = 'tests/ci_mfa31/current_link_fixtures.py'
(out / 'current_link_fixtures.before.RAW.py').write_bytes((root / path).read_bytes())
(out / 'current_link_fixtures.before.GitLF.py').write_bytes(subprocess.check_output(['git', 'show', head + ':' + path], cwd=repo))
code = '''"""Real HTTP fixture authentication remains deterministic at a TOTP boundary."""
from datetime import datetime, timedelta, timezone

import pytest

from tests.current_mfa31_publication_fixtures import case, http, link_db  # noqa: F401


@pytest.fixture(autouse=True)
def crossed_counter(monkeypatch):
    from tests.ci_mfa31 import current_link_fixtures
    from web.services import mfa_service
    from web.services.mfa_crypto import totp

    # Both instants are recent enough for genuine primary/factor freshness.
    # Simulate generation immediately before, and delivery immediately after,
    # one real 30-second counter boundary; no identity/API is replaced.
    generated = (datetime.now(timezone.utc) - timedelta(minutes=2)).replace(second=29, microsecond=900000)
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
'''
ast.parse(code)
target = root / 'tests/test_current_mfa31_fixture_clock.py'
with target.open('xb') as stream:
    stream.write(code.encode('utf-8'))
(out / 'test-original.RAW.py').write_bytes(target.read_bytes())
print(json.dumps({'head': head, 'root': str(root), 'product_changed': False,
    'test_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'scope': 'Prepared a deterministic boundary reproduction. Original broad error cause remains a hypothesis until observed.'}))
