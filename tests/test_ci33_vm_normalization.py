"""Typed label conversion cannot manufacture success or collapse identities."""
from __future__ import annotations

import copy

import pytest

from tests.ci_google33.normalize_vm import normalize


@pytest.mark.parametrize('label', ['name', 'code'])
def test_every_producer_label_and_status_is_preserved_once(label):
    value = {'scope': 'synthetic VM only', 'total': 2, 'passed': 2,
             'results': [{label: 'first', 'passed': True}, {label: 'second', 'passed': True}]}
    before = copy.deepcopy(value)
    result = normalize(value, label, 2)
    assert [row['case'] for row in result['results']] == [row[label] for row in value['results']]
    assert result['passed'] == result['total'] == 2 and value == before


@pytest.mark.parametrize('label', ['name', 'code'])
@pytest.mark.parametrize('mutation', ['false', 'bool-count', 'duplicate', 'missing', 'extra', 'wrong-label', 'empty-label'])
def test_incomplete_mixed_or_unconfirmed_rows_fail_closed(label, mutation):
    value = {'scope': 'synthetic VM only', 'total': 2, 'passed': 2,
             'results': [{label: 'first', 'passed': True}, {label: 'second', 'passed': True}]}
    if mutation == 'false':
        value['results'][0]['passed'] = False
    elif mutation == 'bool-count':
        value['total'] = True
    elif mutation == 'duplicate':
        value['results'][1][label] = 'first'
    elif mutation == 'missing':
        value['results'].pop()
    elif mutation == 'extra':
        value['results'][0]['unreviewed'] = 'synthetic-private-marker'
    elif mutation == 'wrong-label':
        value['results'][0] = {'case': 'first', 'passed': True}
    else:
        value['results'][0][label] = ''
    with pytest.raises(ValueError):
        normalize(value, label, 2)
