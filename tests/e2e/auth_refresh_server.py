"""Own auth-race browser fixture; frozen isolated runtime on port 8772.

Only the loopback port is adapted in memory. No backend or accepted fixture
is edited, no inherited database/credentials are used, and external sockets
are blocked by the underlying fixture before product imports.
"""
from pathlib import Path

fixture = Path(__file__).with_name('gym_branding_server.py').resolve()
source = fixture.read_text(encoding='utf-8').replace('8770', '8772')
exec(compile(source, str(fixture), 'exec'), {'__name__': '__main__', '__file__': str(fixture)})
