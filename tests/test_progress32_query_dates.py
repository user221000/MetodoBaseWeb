"""Query date spelling must be an explicit ISO civil date, never an epoch."""
from tests.test_personal_progress_http import progress_db,progress_http


def test_epoch_query_is_rejected_as_a_whole(progress_http):
    c=progress_http
    result=c['client_http'].get('/api/usuario/progreso/completados?from=0&through=0',headers=c['headers']['person'])
    assert result.status_code==422 and result.json()['detail']['code']=='progress_invalid_input'
