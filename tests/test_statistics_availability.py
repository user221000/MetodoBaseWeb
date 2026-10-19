"""Unavailable dashboard data must not be reported as a measured zero."""
import importlib
import logging

from fastapi import HTTPException
import pytest


OWNER = {'id':'stats-owner', 'role':'owner', 'tipo':'gym', 'team_gym_id':None}


@pytest.mark.parametrize('module_name', ['web.routes.stats', 'api.routes.stats'])
@pytest.mark.parametrize('failed_query', ['obtener_estadisticas', 'obtener_planes_por_dia'])
def test_statistics_failure_is_visible_and_does_not_log_query_data(module_name, failed_query, monkeypatch, caplog):
    module = importlib.import_module(module_name)
    private_detail = 'synthetic-private-statistics-detail'
    monkeypatch.setattr(module.repo, 'obtener_estadisticas', lambda *a, **kw: {'total_clientes':0})
    monkeypatch.setattr(module.repo, 'obtener_planes_por_dia', lambda *a, **kw: [])

    def fail(*args, **kwargs):
        raise RuntimeError(private_detail)

    monkeypatch.setattr(module.repo, failed_query, fail)
    with caplog.at_level(logging.ERROR), pytest.raises(HTTPException) as failure:
        module.obtener_estadisticas(periodo=None, db=object(), usuario=OWNER)
    assert failure.value.status_code == 503
    assert failure.value.detail == {'code':'statistics_unavailable',
        'message':'No fue posible consultar las estadísticas. Vuelve a intentar.'}
    assert private_detail not in str(failure.value.detail)
    assert private_detail not in caplog.text
    assert 'stats-owner' not in caplog.text
    records = [item for item in caplog.records if item.name == module.__name__]
    assert len(records) == 1
    assert 'RuntimeError' in records[0].getMessage()
    assert records[0].exc_info is None and records[0].stack_info is None


@pytest.mark.parametrize('module_name', ['web.routes.stats', 'api.routes.stats'])
def test_confirmed_empty_statistics_still_returns_successful_zeroes(module_name, monkeypatch):
    module = importlib.import_module(module_name)
    observed = []

    def facts(db, gym_id, *args, **kwargs):
        observed.append(gym_id)
        return {'total_clientes':0, 'planes_periodo':0, 'tasa_retencion':0.0}

    monkeypatch.setattr(module.repo, 'obtener_estadisticas', facts)
    monkeypatch.setattr(module.repo, 'obtener_planes_por_dia', lambda *a, **kw: [])
    assert module.obtener_estadisticas(periodo=None, db=object(), usuario=OWNER) == {
        'total_clientes':0, 'planes_periodo':0, 'tasa_retencion':0.0,
        'planes_por_dia':[], 'planes_labels':[]}
    assert observed == [OWNER['id']]


def test_statistics_permission_denial_is_not_relabelled_as_outage(monkeypatch):
    from web.routes import stats

    def forbidden_query(*args, **kwargs):
        raise AssertionError('A denied request must not read statistics')

    monkeypatch.setattr(stats.repo, 'obtener_estadisticas', forbidden_query)
    with pytest.raises(HTTPException) as failure:
        stats.obtener_estadisticas(periodo=None, db=object(), usuario={
            'id':'stats-viewer', 'role':'viewer', 'tipo':'gym', 'team_gym_id':'stats-owner'})
    assert failure.value.status_code == 403
