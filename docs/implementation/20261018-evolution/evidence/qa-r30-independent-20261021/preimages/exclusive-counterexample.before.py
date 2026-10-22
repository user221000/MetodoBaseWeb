"""Independent through-exclusive anchor counterexample; no SQL or providers."""
import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from web import product_analytics_domain as domain
from web.product_analytics_baseline import build_baseline

MONDAY = datetime(2026, 10, 19, 6, tzinfo=UTC)
PREPARATION = {'profile_present': False, 'plan_present': False}


def test_anchor_cannot_start_at_the_excluded_next_civil_midnight():
    value = domain.build_report('personal', PREPARATION, [], [], [], now=MONDAY + timedelta(days=2),
        start='2026-10-12', through='2026-10-18', schema_revision='20261020_account_security')
    assert value['cohort']['evaluated_at'] == '2026-10-19T06:00:00Z'
    value['cohort'].update(anchor_week='2026-10-19', population_units=1)
    for name in ('observed_repeat_publication_d7', 'observed_repeat_publication_d30'):
        value['cohort'][name]['denominator'] = 1
    value['result_hash'] = hashlib.sha256(domain.canonical({key: item for key, item in value.items()
                                                         if key != 'result_hash'})).hexdigest()
    with pytest.raises(domain.AnalyticsInput):
        build_baseline(value)


def test_anchor_at_asof_is_valid_when_that_civil_day_is_included():
    value = domain.build_report('personal', PREPARATION, [MONDAY], [], [], now=MONDAY,
        start='2026-10-19', through='2026-10-19', schema_revision='20261020_account_security')
    assert build_baseline(value)['report']['weekly'][0]['saved_publications'] == 1


def test_anchor_just_before_the_excluded_midnight_is_retained():
    value = domain.build_report('personal', PREPARATION, [MONDAY - timedelta(microseconds=1)], [], [],
        now=MONDAY + timedelta(days=2), start='2026-10-12', through='2026-10-18',
        schema_revision='20261020_account_security')
    assert build_baseline(value)['report']['weekly'][0]['saved_publications'] == 1
