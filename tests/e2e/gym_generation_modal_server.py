"""Own ephemeral modal follow-up; reuses the frozen isolated fixture on 8771.

Adaptations are the loopback port and a persisted synthetic Clinic entitlement
before app startup, so repeated creation cases do not consume Free's daily
fixture allowance. This never edits the original fixture or product modules.
Current metadata is used only in this temporary SQLite; the independent gate
keeps its separate 24-table snapshot on port 8769.
"""
from pathlib import Path

fixture = Path(__file__).with_name('gym_generation_server.py').resolve()
source = fixture.read_text(encoding='utf-8').replace('8769', '8771')
source = source.replace('    import uvicorn', '''    from datetime import datetime, timedelta, timezone
    from web.database.models import Subscription
    with Session(engine) as db:
        db.add(Subscription(gym_id='synthetic-generation-owner', plan='clinica', status='active', max_clientes=0, current_period_end=datetime.now(timezone.utc)+timedelta(days=30)))
        db.commit()
    import uvicorn''')
exec(compile(source, str(fixture), 'exec'), {'__name__': '__main__', '__file__': str(fixture)})
