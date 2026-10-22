"""Independent R30 counterexamples: hashes do not excuse impossible maturity.

These are pure baseline validation cases, not claims that the authenticated
report endpoint lets an attacker supply a report or establish real provenance.
"""
import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from web import product_analytics_domain as domain
from web.product_analytics_baseline import build_baseline

NOW = datetime(2026, 10, 21, 18, tzinfo=UTC)


def actual(saved):
    return domain.build_report("personal", {"profile_present": False, "plan_present": False},
                               saved, [], [], now=NOW, start="2026-10-19", through="2026-10-21",
                               schema_revision="20261020_account_security")


def rehash(value):
    value["result_hash"] = hashlib.sha256(domain.canonical({key: item for key, item in value.items()
                                                           if key != "result_hash"})).hexdigest()
    return value


def test_impossible_same_week_maturity_cannot_become_a_baseline():
    value = actual([NOW - timedelta(days=1)])
    assert value["cohort"]["anchor_week"] == "2026-10-19"
    assert value["cohort"]["observed_repeat_publication_d7"]["numerator"] is None
    value["cohort"]["observed_repeat_publication_d7"].update(mature=True, numerator=0, ratio=0.0)
    with pytest.raises(domain.AnalyticsInput):
        build_baseline(rehash(value))


def test_later_maturity_cannot_coexist_with_earlier_immaturity():
    value = actual([NOW - timedelta(days=50)])
    assert value["cohort"]["observed_repeat_publication_d30"]["mature"] is True
    value["cohort"]["observed_repeat_publication_d7"].update(mature=False, numerator=None, ratio=None)
    with pytest.raises(domain.AnalyticsInput):
        build_baseline(rehash(value))


def test_visible_anchor_requires_at_least_its_own_publication():
    value = actual([NOW - timedelta(days=1)])
    assert value["weekly"][0]["saved_publications"] == 1
    value["weekly"][0]["saved_publications"] = 0
    with pytest.raises(domain.AnalyticsInput):
        build_baseline(rehash(value))


def test_genuine_recent_unknown_and_old_observed_zero_are_both_preserved():
    recent = actual([NOW - timedelta(days=1)])
    old = actual([NOW - timedelta(days=50)])
    assert build_baseline(recent)["report"]["cohort"]["observed_repeat_publication_d7"]["numerator"] is None
    assert build_baseline(old)["report"]["cohort"]["observed_repeat_publication_d30"]["numerator"] == 0
    assert old["weekly"][0]["saved_publications"] == 0
