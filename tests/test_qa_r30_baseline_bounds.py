"""Only consequences derivable from a published anchor week are enforced."""
import hashlib
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from web import product_analytics_domain as domain
from web.product_analytics_baseline import build_baseline

MONDAY = datetime(2026, 10, 19, 6, tzinfo=UTC)  # Mexico Monday 00:00.


def report(anchor, cutoff, *, start='2026-10-19', through=None):
    last = through or cutoff.astimezone(ZoneInfo(domain.ZONE)).date().isoformat()
    return domain.build_report('personal', {'profile_present': False, 'plan_present': False},
        [anchor], [], [], now=cutoff, start=start, through=last, schema_revision='20261020_account_security')


def rehash(value):
    value['result_hash'] = hashlib.sha256(domain.canonical({key: item for key, item in value.items()
                                                         if key != 'result_hash'})).hexdigest()
    return value


@pytest.mark.parametrize('label,end', [('d7', 14), ('d30', 37)])
@pytest.mark.parametrize('offset', [-1, 0, 1])
def test_exact_earliest_maturity_boundary_keeps_real_reports(label, end, offset):
    cutoff = MONDAY + timedelta(days=end, microseconds=offset)
    value = report(MONDAY, cutoff)
    row = build_baseline(value)['report']['cohort']['observed_repeat_publication_' + label]
    assert row['mature'] is (offset >= 0)
    assert row['numerator'] == (0 if offset >= 0 else None)


@pytest.mark.parametrize('label,end', [('d7', 14), ('d30', 37)])
@pytest.mark.parametrize('anchor_offset', [0, 6])
def test_same_published_week_can_legitimately_have_either_maturity(label, end, anchor_offset):
    # The exact anchor is absent from the wire: six days of ambiguity remain.
    value = report(MONDAY + timedelta(days=anchor_offset), MONDAY + timedelta(days=end + 2))
    row = build_baseline(value)['report']['cohort']['observed_repeat_publication_' + label]
    assert row['mature'] is (anchor_offset == 0)
    assert row['numerator'] == (0 if anchor_offset == 0 else None)


@pytest.mark.parametrize('label,end', [('d7', 14), ('d30', 37)])
def test_immaturity_is_impossible_after_latest_anchor_window_end(label, end):
    value = report(MONDAY + timedelta(days=7, microseconds=-1), MONDAY + timedelta(days=7 + end))
    value['cohort']['observed_repeat_publication_' + label].update(mature=False, numerator=None, ratio=None)
    with pytest.raises(domain.AnalyticsInput):
        build_baseline(rehash(value))


@pytest.mark.parametrize('label,end', [('d7', 14), ('d30', 37)])
def test_latest_possible_anchor_can_still_be_immature_just_before_its_end(label, end):
    anchor = MONDAY + timedelta(days=7, microseconds=-1)
    value = report(anchor, MONDAY + timedelta(days=7 + end, microseconds=-2))
    row = build_baseline(value)['report']['cohort']['observed_repeat_publication_' + label]
    assert row['mature'] is False and row['numerator'] is None


def test_partial_civil_cutoff_controls_maturity_even_when_asof_is_later():
    value = report(MONDAY + timedelta(hours=1), MONDAY + timedelta(days=50), through='2026-10-20')
    accepted = build_baseline(value)['report']
    assert accepted['cohort']['evaluated_at'] == '2026-10-21T06:00:00Z'
    assert accepted['cohort']['observed_repeat_publication_d7']['numerator'] is None
    assert accepted['weekly'][0]['saved_publications'] == 1


def test_anchor_week_end_uses_civil_timezone_across_historical_dst():
    # This Mexico week lasted 169 elapsed hours. A fixed seven-UTC-day
    # approximation would reject a legitimate unknown D7 during its last hour.
    anchor = datetime(2019, 10, 28, 5, 30, tzinfo=UTC)
    cutoff = datetime(2019, 11, 11, 5, 15, tzinfo=UTC)
    value = report(anchor, cutoff, start='2019-10-21')
    row = build_baseline(value)['report']['cohort']['observed_repeat_publication_d7']
    assert value['cohort']['anchor_week'] == '2019-10-21'
    assert row['mature'] is False and row['numerator'] is None


def test_anchor_outside_visible_period_can_have_no_visible_publication():
    value = report(MONDAY, MONDAY + timedelta(days=50), start='2026-11-30')
    assert all(week['saved_publications'] == 0 for week in value['weekly'])
    assert build_baseline(value)['report']['cohort']['observed_repeat_publication_d30']['mature'] is True


def test_count_in_a_different_week_cannot_replace_the_visible_anchor_fact():
    value = report(MONDAY, MONDAY + timedelta(days=15))
    value['weekly'][0]['saved_publications'] = 0
    value['weekly'][1]['saved_publications'] = 1
    with pytest.raises(domain.AnalyticsInput):
        build_baseline(rehash(value))


def test_publication_cannot_precede_the_retained_anchor_week():
    value = report(MONDAY + timedelta(days=7), MONDAY + timedelta(days=15))
    value['weekly'][0]['saved_publications'] = 1
    with pytest.raises(domain.AnalyticsInput):
        build_baseline(rehash(value))


def test_response_budget_is_checked_before_unknown_field_validation():
    value = report(MONDAY, MONDAY + timedelta(days=1))
    value['oversized_private_field'] = 'x' * domain.MAX_BYTES
    with pytest.raises(domain.AnalyticsVolume):
        build_baseline(rehash(value))
