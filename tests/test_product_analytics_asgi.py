"""Real Response seam: complete body acceptance, failed send and no publication."""
import asyncio

import pytest

from web import product_analytics_http as adapter


@pytest.mark.parametrize('publication', [None, {'id': 'publication', 'version': 1}])
def test_observation_occurs_only_after_complete_asgi_body(monkeypatch, publication):
    events = []
    def observed(*args): events.append(('observed', args))
    monkeypatch.setattr(adapter, 'assigned_plan_served', observed)
    async def send(message): events.append((message['type'], message.get('more_body', False)))
    response = adapter.AssignedPlanResponse({'publication': publication}, {'id': 'actor', 'email': 'must-not-be-copied'}, 'link')
    asyncio.run(response({'type': 'http'}, None, send))
    assert events[:2] == [('http.response.start', False), ('http.response.body', False)]
    assert len(events) == (3 if publication else 2)
    if publication:
        assert 'email' not in events[-1][1][0]
        assert events[-1][1][1:] == ('link', 'publication', 1)


def test_failed_body_send_never_records_access(monkeypatch):
    observed = []
    monkeypatch.setattr(adapter, 'assigned_plan_served', lambda *args: observed.append(args))
    async def send(message):
        if message['type'] == 'http.response.body': raise OSError('synthetic disconnected send')
    response = adapter.AssignedPlanResponse({'publication': {'id': 'publication', 'version': 1}}, {}, 'link')
    with pytest.raises(OSError): asyncio.run(response({'type': 'http'}, None, send))
    assert observed == []
