"""Closed, credential-free runtime metadata accepted by CI33 publication."""
from __future__ import annotations

import json
import re

REVISION = {'31': '20261019_mfa', '32': '20261019_personal_progress',
            '33': '20261019_google_subjects'}
COUNTS = {'32': (33, 34, 24, 10), '33': (35, 36, 26, 12)}
CONTRACT_HASHES = {'32': 'a933274f911f680dee9a3eac32cdda67f88cebc7717ad527a544a0181c6d6197',
                   '33': '3e005c2ae4226db1d916e2ce3e54a57f6ace09839741971b1ccf955faa6c782f'}
TRANSITION_FIELDS = {'database_kind', 'runtime_revision', 'actual_tables',
                     'role_flags4', 'database_nonowner', 'owned_tables',
                     'application_pool_size', 'blank_GUCs', 'schema_sha256'}
HASHES = {'global_contract_sha256', 'functions_sha256', 'triggers_sha256', 'foreign_keys_sha256',
          'google_identity_signature_sha256', 'history_index_sha256'}
FIELDS = {'database_kind', 'runtime_revision', 'model_tables', 'actual_tables',
          'application_role_restricted_nonowner', 'role_flags4', 'owned_tables',
          'FORCE_RLS_tables', 'application_pool_size', 'signed_functions',
          'signed_triggers', 'blank_GUCs', 'foreign_keys_validated', *HASHES}


def closed_json(raw):
    def distinct(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=distinct)


def validate(value, *, schema='33', pool=1, transition=False):
    if transition:
        allowed = {REVISION[schema], REVISION[str(int(schema) - 1)]}
        if not isinstance(value, dict) or set(value) != TRANSITION_FIELDS:
            raise ValueError('Transition witness fields differ')
        if value['runtime_revision'] not in allowed:
            raise ValueError('Unexpected transition revision')
        expected_tables = {'31': 33, '32': 34, '33': 36}
        revision_schema = next(s for s, revision in REVISION.items() if revision == value['runtime_revision'])
        if type(value['actual_tables']) is not int or value['actual_tables'] != expected_tables[revision_schema]:
            raise ValueError('Transition physical count differs')
        if (value['database_kind'] != 'postgresql' or value['role_flags4'] != [False] * 4
                or not all(type(v) is bool for v in value['role_flags4'])
                or value['database_nonowner'] is not True or value['blank_GUCs'] is not True
                or type(value['owned_tables']) is not int or value['owned_tables'] != 0
                or type(value['application_pool_size']) is not int or value['application_pool_size'] != pool
                or not isinstance(value['schema_sha256'], str)
                or not re.fullmatch('[a-f0-9]{64}', value['schema_sha256'])):
            raise ValueError('Transition role, pool or signature differs')
        return value
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError('Runtime witness fields differ from the closed contract')
    if value['runtime_revision'] != REVISION[schema]:
        raise ValueError('Runtime head is not the required current/historical head')
    model, tables, functions, triggers = COUNTS[schema]
    integers = {'model_tables': model, 'actual_tables': tables, 'owned_tables': 0,
                'FORCE_RLS_tables': 26, 'application_pool_size': pool,
                'signed_functions': functions, 'signed_triggers': triggers}
    if any(type(value[k]) is not int or value[k] != v for k, v in integers.items()):
        raise ValueError('Measured physical or pool counts differ')
    if value['database_kind'] != 'postgresql' or value['role_flags4'] != [False] * 4:
        raise ValueError('PostgreSQL restricted role is required')
    if not all(type(v) is bool for v in value['role_flags4']):
        raise ValueError('Role flags must be real booleans')
    for key in ('application_role_restricted_nonowner', 'blank_GUCs', 'foreign_keys_validated'):
        if value[key] is not True:
            raise ValueError('A required runtime safety witness is absent')
    if any(not isinstance(value[k], str) or not re.fullmatch('[a-f0-9]{64}', value[k]) for k in HASHES):
        raise ValueError('Runtime signature hash is missing or malformed')
    if value['global_contract_sha256'] != CONTRACT_HASHES[schema]:
        raise ValueError('Actual complete runtime signature differs from the frozen global contract')
    return value


def validate_sqlite(value):
    expected = {'database_kind', 'runtime_revision', 'model_tables', 'actual_tables',
                'foreign_keys_clean', 'schema_sha256', 'google_identity_signature_sha256'}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError('SQLite witness fields differ')
    if (value['database_kind'] != 'sqlite' or value['runtime_revision'] != REVISION['33']
            or type(value['model_tables']) is not int or value['model_tables'] != 35
            or type(value['actual_tables']) is not int or value['actual_tables'] != 36
            or value['foreign_keys_clean'] is not True):
        raise ValueError('SQLite measured revision or physical counts differ')
    for key in ('schema_sha256', 'google_identity_signature_sha256'):
        if not isinstance(value[key], str) or not re.fullmatch('[a-f0-9]{64}', value[key]):
            raise ValueError('SQLite actual signature is absent')
    return value


def validate_browser_inventory(value):
    if (not isinstance(value, dict) or set(value) != {'phase', 'member', 'followup', 'daily', 'mfa_sqlite', 'closed_UUID_leases'}
            or value['phase'] != 'owned_startup_after_upgrade_before_browser_business'
            or type(value['closed_UUID_leases']) is not int or value['closed_UUID_leases'] != 3):
        raise ValueError('Browser runtime inventory or resource closure differs')
    for label, pool in [('member', 20), ('followup', 10), ('daily', 20)]:
        validate(value[label], pool=pool)
    validate_sqlite(value['mfa_sqlite'])
    return value
