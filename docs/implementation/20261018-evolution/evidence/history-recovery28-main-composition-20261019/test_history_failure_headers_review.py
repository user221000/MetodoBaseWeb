"""Private history headers at the query-error boundary, both real factories."""
import json
from pathlib import Path

from sqlalchemy import event

from tests.test_personal_history_pagination import history_http, plans, get


def test_private_headers_survive_a_summary_query_failure(history_http):
    plans(history_http[1], 3)
    position = get(history_http, limit=1).json()['next_cursor']
    def unavailable(connection, cursor, statement, parameters, context, executemany):
        if 'FROM planes_generados JOIN clientes' in statement:
            raise RuntimeError('Synthetic independent history query unavailable')
    event.listen(history_http[1], 'before_cursor_execute', unavailable)
    try:
        response = get(history_http, cursor=position)
    finally:
        event.remove(history_http[1], 'before_cursor_execute', unavailable)
    assert response.status_code >= 500
    safe = {'factory': history_http[0].app.title, 'status': response.status_code,
        'cache-control': response.headers.get('cache-control'), 'referrer-policy': response.headers.get('referrer-policy'),
        'cursor_echoed_in_body': position in response.text, 'body_has_planes': '"planes"' in response.text}
    target = Path(__file__).parent / ('failure-headers-' + history_http[0].app.title.replace(' ', '_') + '.json')
    assert not target.exists()
    target.write_text(json.dumps(safe, indent=2) + '\n', encoding='utf8')
    assert 'no-store' in response.headers.get('cache-control', '').lower().split(', ')
    assert response.headers.get('referrer-policy') == 'no-referrer'
