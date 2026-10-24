"""Recorded restore cast pairs and structural/quoted-text rejection canaries.

Pure comparison tests: no SQL, application factory, server or restore claims.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from web.database.alembic.schema_contract_v2 import (
    canonical_signature, normalize_check_sql, schema_contracts_equal,
    schema_signatures_equal,
)

RECORD = json.loads((Path(__file__).parent / "data/schema_contract_v2/pg38_restore_pairs.json").read_bytes())
OUTER = "ANY (ARRAY['gym'::character varying, 'personal'::character varying]::text[])"
ELEMENT = "ANY (ARRAY['gym'::character varying::text, 'personal'::character varying::text])"


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    # These pure signature comparisons must not create an unrelated unit DB.
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.mark.parametrize("case", RECORD["differences"], ids=["nested-and-check0", "nested-or-check3"])
def test_real_restored_check_pairs_have_symmetric_idempotent_cast_equivalence(case):
    actual, expected = case["actual"], case["expected"]
    assert actual != expected
    assert normalize_check_sql(actual) == normalize_check_sql(expected)
    assert normalize_check_sql(normalize_check_sql(actual)) == normalize_check_sql(actual)
    assert normalize_check_sql(normalize_check_sql(expected)) == normalize_check_sql(expected)
    for left, right in ((actual, expected), (expected, actual)):
        a = {"dialect": "postgresql", "tables": {"fact": {"checks": [{"name": "strict", "sql": left}]}}}
        b = {"dialect": "postgresql", "tables": {"fact": {"checks": [{"name": "strict", "sql": right}]}}}
        assert schema_signatures_equal(a, b)


def test_real_table_projection_preserves_every_other_field_and_inputs():
    actual, expected = deepcopy(RECORD["actual"]), deepcopy(RECORD["expected"])
    a_before, e_before = deepcopy(actual), deepcopy(expected)
    assert actual != expected
    assert schema_signatures_equal(actual, expected) and schema_signatures_equal(expected, actual)
    assert actual == a_before and expected == e_before
    normalized = canonical_signature(actual)
    differences = []
    original_checks = actual["tables"]["product_analytics_facts"]["checks"]
    new_checks = normalized["tables"]["product_analytics_facts"]["checks"]
    # The restored form is already canonical: every actual leaf is literal.
    assert normalized == actual
    expected_normalized = canonical_signature(expected)
    for index, (old, new) in enumerate(zip(expected["tables"]["product_analytics_facts"]["checks"], new_checks)):
        if old != new:
            differences.append(index)
    assert differences == [0, 3] and expected_normalized == actual
    assert original_checks == a_before["tables"]["product_analytics_facts"]["checks"]


@pytest.mark.parametrize("old,new", [
    (" AND ", " OR "), (" OR ", " AND "), ("'gym'", "'other'"),
    ("context::text", "different_context::text"), (" IS NULL", " IS NOT NULL"),
    (" = ANY ", " <> ANY "), ("client_id IS NOT NULL", "client_id IS NULL"),
    (" AND ", "  AND "),
])
def test_cast_equivalence_never_hides_a_changed_predicate(old, new):
    expected = RECORD["differences"][0]["expected"]
    changed = RECORD["differences"][0]["actual"].replace(old, new, 1)
    assert changed != RECORD["differences"][0]["actual"]
    assert normalize_check_sql(changed) != normalize_check_sql(expected)


def test_cast_equivalence_preserves_parentheses_array_order_and_null_branch():
    a, e = RECORD["differences"][0]["actual"], RECORD["differences"][0]["expected"]
    for changed in ("(" + a + ")", a.replace("'gym'::character varying::text, 'personal'::character varying::text",
            "'personal'::character varying::text, 'gym'::character varying::text"),
            a + " OR client_id IS NULL"):
        assert normalize_check_sql(changed) != normalize_check_sql(e)


@pytest.mark.parametrize("wrapper", ["string", "identifier", "line-comment", "block-comment", "nested-comment", "dollar", "tagged-dollar"])
def test_cast_text_inside_quoted_or_comment_regions_is_never_rewritten(wrapper):
    def wrap(sql):
        return {
            "string": "'" + sql.replace("'", "''") + "'",
            "identifier": '"' + sql.replace('"', '""') + '"',
            "line-comment": "-- " + sql + "\n",
            "block-comment": "/* " + sql + " */",
            "nested-comment": "/* outer /* " + sql + " */ end */",
            "dollar": "$$" + sql + "$$",
            "tagged-dollar": "$guard_39$" + sql + "$guard_39$",
        }[wrapper]
    outer, element = wrap(OUTER), wrap(ELEMENT)
    assert normalize_check_sql(outer) == outer and normalize_check_sql(element) == element
    assert normalize_check_sql(outer) != normalize_check_sql(element)
    # A genuine expression after the opaque span may normalize independently.
    assert normalize_check_sql(outer + " AND x::text = " + OUTER) == outer + " AND x::text = " + ELEMENT


def test_unrecognized_unicode_dollar_tag_disables_the_entire_rewrite():
    quoted = "$\u03c0$literal prefix " + OUTER + "$\u03c0$"
    assert normalize_check_sql(quoted) == quoted
    sql = quoted + " AND x::text = " + OUTER
    assert normalize_check_sql(sql) == sql
    element_quoted = "$\u03c0$literal prefix " + ELEMENT + "$\u03c0$"
    assert normalize_check_sql(quoted) != normalize_check_sql(element_quoted)


@pytest.mark.parametrize("unknown", [
    "ANY (ARRAY['gym'::character varying(3), 'personal'::character varying(8)]::text[])",
    "ANY (ARRAY['gym'::varchar, 'personal'::varchar]::text[])",
    "ANY (ARRAY['gym'::citext, 'personal'::citext]::text[])",
    "ANY (ARRAY['gym'::character, 'personal'::character]::text[])",
    "ANY (ARRAY['gym'::character varying::text, 'personal'::character varying]::text[])",
    "ANY (ARRAY['gym'::character varying, 'personal'::character varying])",
    "ANY (ARRAY['gym'::character varying::text, 'personal'::character varying::text]::text[])",
    "ANY (ARRAY['gym'::character varying, NULL]::text[])",
    "ANY (ARRAY[lower('gym')::character varying, 'personal'::character varying]::text[])",
    "ANY (ARRAY['gym'::character varying, 'personal'::character varying]::text[][])",
    "ANY (ARRAY['gym'::character varying, 'personal'::character varying]::text[] COLLATE special)",
    "ANY (ARRAY['gym'::character varying,'personal'::character varying]::text[])",
    "ARRAY['gym'::character varying, 'personal'::character varying]::text[]",
    "NOTANY (ARRAY['gym'::character varying, 'personal'::character varying]::text[])",
    "catalog.ANY (ARRAY['gym'::character varying, 'personal'::character varying]::text[])",
    "namespace_\u03c0ANY (ARRAY['gym'::character varying, 'personal'::character varying]::text[])",
])
def test_unreviewed_array_type_expression_or_syntax_stays_literal(unknown):
    assert normalize_check_sql(unknown) == unknown
    assert normalize_check_sql(unknown) != ELEMENT


@pytest.mark.parametrize("suffix", ["'unterminated", '"unterminated', "/* unterminated", "$tag$unterminated", "E'\\\\escaped'", "'\\\\ambiguous'"])
def test_ambiguous_lexical_context_disables_the_entire_rewrite(suffix):
    sql = OUTER + " AND " + suffix
    assert normalize_check_sql(sql) == sql


def test_doubled_quote_literal_values_are_preserved_exactly():
    outer = "ANY (ARRAY['owner''s gym'::character varying, ''::character varying]::text[])"
    element = "ANY (ARRAY['owner''s gym'::character varying::text, ''::character varying::text])"
    assert normalize_check_sql(outer) == element


@pytest.mark.parametrize("field", ["nullable", "default", "foreign-key", "index", "index-predicate", "column-type", "type-length", "primary-key", "unique", "check-name"])
def test_all_non_check_structure_remains_exact(field):
    actual, expected = deepcopy(RECORD["actual"]), deepcopy(RECORD["expected"])
    table = actual["tables"]["product_analytics_facts"]
    if field == "nullable":
        table["columns"][0]["nullable"] = not table["columns"][0]["nullable"]
    elif field == "default":
        table["columns"][0]["default"] = "unexpected-default"
    elif field == "foreign-key":
        table["foreign_keys"][0]["options"]["ondelete"] = "CASCADE"
    elif field == "index":
        table["indexes"][0]["unique"] = not table["indexes"][0]["unique"]
    elif field == "index-predicate":
        table["indexes"][0]["where"] = "context = 'foreign'"
    elif field == "column-type":
        table["columns"][0]["type"] = "TEXT"
    elif field == "type-length":
        table["columns"][0]["type_attributes"]["length"] = 999
    elif field == "primary-key":
        table["primary_key"] = ["subject_id"]
    elif field == "unique":
        table["unique"].append(["context"])
    else:
        table["checks"][0]["name"] += "_changed"
    assert not schema_signatures_equal(actual, expected)
    assert not schema_signatures_equal(expected, actual)


@pytest.mark.parametrize("field", ["default", "where"])
def test_equivalent_cast_text_is_not_normalized_in_defaults_or_indexes(field):
    actual, expected = deepcopy(RECORD["actual"]), deepcopy(RECORD["expected"])
    for signature, value in ((actual, OUTER), (expected, ELEMENT)):
        table = signature["tables"]["product_analytics_facts"]
        row = table["columns"][0] if field == "default" else table["indexes"][0]
        row[field] = value
    assert not schema_signatures_equal(actual, expected)


def test_security_envelope_missing_fields_dialect_and_sqlite_remain_strict():
    actual = {"signature": deepcopy(RECORD["actual"]), "tenant_security": {"force": True}, "privacy_security": {"sql": OUTER}}
    expected = {"signature": deepcopy(RECORD["expected"]), "tenant_security": {"force": True}, "privacy_security": {"sql": OUTER}}
    assert schema_contracts_equal(actual, expected) and schema_contracts_equal(expected, actual)
    expected["privacy_security"]["sql"] = ELEMENT
    assert not schema_contracts_equal(actual, expected)
    expected["privacy_security"]["sql"] = OUTER
    expected["tenant_security"]["force"] = False
    assert not schema_contracts_equal(actual, expected)
    expected.pop("tenant_security")
    assert not schema_contracts_equal(actual, expected)
    a, e = deepcopy(RECORD["actual"]), deepcopy(RECORD["expected"])
    a["dialect"] = "sqlite"
    assert not schema_signatures_equal(a, e)
    e["dialect"] = "sqlite"
    assert not schema_signatures_equal(a, e)
