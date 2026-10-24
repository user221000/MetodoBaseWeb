"""Explicit v2 baseline, civil cutoffs and typed aggregate boundary."""
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import hashlib

import pytest

from web import product_analytics_domain as v1
from web.product_analytics_v2 import aggregate, validate_report

NOW = datetime(2026, 10, 23, 18, tzinfo=UTC)
PERIOD = v1.period('2026-10-19', '2026-10-23', now=NOW)


def rehash(value):
    value['result_hash'] = hashlib.sha256(v1.canonical({k: v for k, v in value.items() if k != 'result_hash'})).hexdigest()
    return value


def test_empty_or_only_origin_declarations_do_not_invent_baseline():
    for rows in ([], [('origin_declared', 'demo', NOW, 'private-client', 'private-source')]):
        value = aggregate(rows, PERIOD, now=NOW, context='gym')
        assert value['baseline']['status'] == 'not_observed'
        assert value['baseline']['first_observed_fact'] is None
        assert value['baseline']['retention_D7'] is None and value['baseline']['targets'] is None
        assert value['coverage']['past_events_backfilled'] is False
        assert 'private-client' not in str(value) and 'private-source' not in str(value)


def test_origin_snapshots_separate_same_client_without_retrospective_classification():
    rows = [('plan_saved', 'demo', NOW - timedelta(days=2), 'client-a', 'plan-a'),
            ('plan_saved', 'customer', NOW - timedelta(days=1), 'client-a', 'plan-b'),
            ('assigned_plan_http200', 'demo', NOW, 'client-a', 'publication-a')]
    value = aggregate(rows, PERIOD, now=NOW, context='gym')
    counts = value['baseline']['event_counts_by_origin']
    assert counts['demo']['plan_saved'] == counts['customer']['plan_saved'] == 1
    assert counts['demo']['assigned_plan_http200'] == 1 and counts['customer']['assigned_plan_http200'] == 0
    assert value['baseline']['observed_subjects_by_origin'] == {'unknown': 0, 'demo': 1, 'customer': 1}
    assert value['classification']['customer_is_payment'] is False
    assert all(identifier not in str(value) for identifier in ('client-a', 'plan-a', 'publication-a'))


def test_closed_civil_upper_bound_and_inclusive_asof_are_distinct():
    day_end = datetime(2026, 10, 20, 6, tzinfo=UTC)  # local next midnight
    rows = [('plan_saved', 'unknown', day_end - timedelta(microseconds=1), None, '1'),
            ('plan_saved', 'unknown', day_end, None, '2')]
    value = aggregate(rows, v1.period('2026-10-19', '2026-10-19', now=NOW), now=NOW, context='personal')
    assert value['baseline']['event_counts_by_origin']['unknown']['plan_saved'] == 1
    exact = aggregate([('plan_saved', 'unknown', NOW, None, '3')], PERIOD, now=NOW, context='personal')
    assert exact['baseline']['event_counts_by_origin']['unknown']['plan_saved'] == 1


@pytest.mark.parametrize('mutant', ['bool_count', 'classification_bool', 'coverage_bool', 'extra_id', 'week_mismatch', 'retention'])
def test_rehashed_mutations_do_not_loosen_v2_contract(mutant):
    value = deepcopy(aggregate([('plan_saved', 'unknown', NOW, 'client', 'source')], PERIOD, now=NOW, context='gym'))
    if mutant == 'bool_count': value['baseline']['event_counts_by_origin']['unknown']['plan_saved'] = True
    elif mutant == 'classification_bool': value['classification']['customer_is_payment'] = 0
    elif mutant == 'coverage_bool': value['coverage']['past_events_backfilled'] = 0
    elif mutant == 'extra_id': value['client_id'] = 'private'
    elif mutant == 'week_mismatch': value['weeks'][0]['by_origin']['unknown']['plan_saved'] = 2
    else: value['baseline']['retention_D7'] = 1.0
    with pytest.raises(ValueError): validate_report(rehash(value))
