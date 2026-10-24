"""Recorded PG39 CHECK casts: pure comparisons, no SQL/restore/server claims."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from web.database.alembic.schema_contract_v2 import (
    canonical_signature, normalize_check_sql, schema_contracts_equal,
    schema_signatures_equal,
)
from web.database.alembic.policy_contract_v2 import policy_signatures_equal

RECORD = json.loads((Path(__file__).parent / "data/schema_contract_v2/pg39_restore_pairs.json").read_bytes())
OUTER = "ALL (ARRAY['eligible'::character varying, 'executing'::character varying]::text[])"
ELEMENT = "ALL (ARRAY['eligible'::character varying::text, 'executing'::character varying::text])"


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.mark.parametrize("case", RECORD["differences"], ids=["privacy-item-any", "privacy-closed-all", "fact-context-any", "fact-event-any"])
def test_all_four_real39_check_pairs_are_symmetric_idempotent_and_keep_operator(case):
    actual, expected = case["actual"], case["expected"]
    assert actual != expected
    assert normalize_check_sql(actual) == normalize_check_sql(expected)
    assert normalize_check_sql(normalize_check_sql(actual)) == normalize_check_sql(actual)
    assert normalize_check_sql(normalize_check_sql(expected)) == normalize_check_sql(expected)
    for left, right in ((actual, expected), (expected, actual)):
        a = {"dialect": "postgresql", "tables": {"owned": {"checks": [{"name": "strict", "sql": left}]}}}
        b = {"dialect": "postgresql", "tables": {"owned": {"checks": [{"name": "strict", "sql": right}]}}}
        assert schema_signatures_equal(a, b)
    if case["path"] == "/tables/privacy_requests/checks/0/sql":
        normalized = normalize_check_sql(expected)
        assert normalized == actual and " <> ALL " in normalized and "ANY" not in normalized


def test_full44_table_catalog_normalizes_only_the_four_recorded_check_leaves_on_copies():
    actual, expected = deepcopy(RECORD["actual"]), deepcopy(RECORD["expected"])
    a_before, e_before = deepcopy(actual), deepcopy(expected)
    assert actual != expected and len(actual["tables"]) == len(expected["tables"]) == 44
    projected = deepcopy(expected)
    for case in RECORD["differences"]:
        _, root, table, checks, index, leaf = case["path"].split("/")
        assert (root, checks, leaf) == ("tables", "checks", "sql")
        assert actual[root][table][checks][int(index)][leaf] == case["actual"]
        assert expected[root][table][checks][int(index)][leaf] == case["expected"]
        projected[root][table][checks][int(index)][leaf] = case["actual"]
    assert projected == actual
    assert canonical_signature(expected) == actual and canonical_signature(actual) == actual
    assert schema_signatures_equal(actual, expected) and schema_signatures_equal(expected, actual)
    assert actual == a_before and expected == e_before


@pytest.mark.parametrize("quantifier,operator", [("ANY", "="), ("ANY", "<>"), ("ALL", "="), ("ALL", "<>")])
def test_quantifier_and_comparison_operator_are_preserved_separately(quantifier, operator):
    outer = "state::text " + operator + " " + OUTER.replace("ALL", quantifier, 1)
    element = "state::text " + operator + " " + ELEMENT.replace("ALL", quantifier, 1)
    assert normalize_check_sql(outer) == element
    other_quantifier = "ALL" if quantifier == "ANY" else "ANY"
    other_operator = "<>" if operator == "=" else "="
    assert normalize_check_sql(outer.replace(" " + quantifier + " ", " " + other_quantifier + " ", 1)) != element
    assert normalize_check_sql(outer.replace("::text " + operator, "::text " + other_operator, 1)) != element


@pytest.mark.parametrize("old,new", [
    (" <> ALL ", " = ALL "), (" ALL ", " ANY "),
    ("'eligible'", "'denied'"), ("state::text", "other_state::text"),
    (" OR ", " AND "), (" IS NOT NULL", " IS NULL"),
    (" OR ", "  OR "), ("closed_at", "other_closed_at"),
])
def test_actual39_all_rejects_changed_predicate_operator_null_branch_or_spacing(old, new):
    case = RECORD["differences"][1]
    changed = case["actual"].replace(old, new, 1)
    assert changed != case["actual"]
    assert normalize_check_sql(changed) != normalize_check_sql(case["expected"])


@pytest.mark.parametrize("quantifier", ["ANY", "ALL"])
@pytest.mark.parametrize("template", [
    "QUANT (ARRAY['eligible'::character varying(8), 'executing'::character varying(9)]::text[])",
    "QUANT (ARRAY['eligible'::varchar, 'executing'::varchar]::text[])",
    "QUANT (ARRAY['eligible'::text, 'executing'::text]::text[])",
    "QUANT (ARRAY['eligible'::citext, 'executing'::citext]::text[])",
    "QUANT (ARRAY['eligible'::character varying::text, 'executing'::character varying]::text[])",
    "QUANT (ARRAY['eligible'::character varying::text, 'executing'::character varying::text]::text[])",
    "QUANT (ARRAY['eligible'::character varying, 'executing'::character varying])",
    "QUANT (ARRAY['eligible'::character varying, NULL]::text[])",
    "QUANT (ARRAY[lower('eligible')::character varying, 'executing'::character varying]::text[])",
    "QUANT (ARRAY['eligible'::character varying, 'executing'::character varying]::text[][])",
    "QUANT (ARRAY['eligible'::character varying, 'executing'::character varying]::text[] COLLATE special)",
    "QUANT (ARRAY['eligible'::character varying,'executing'::character varying]::text[])",
    "QUANT (ARRAY[]::text[])",
])
def test_unknown_types_typmods_null_expressions_dimensions_and_cast_forms_remain_literal(quantifier, template):
    unknown = template.replace("QUANT", quantifier)
    assert normalize_check_sql(unknown) == unknown


@pytest.mark.parametrize("wrapper", ["string", "identifier", "line-comment", "block-comment", "nested-comment", "dollar", "tagged-dollar"])
def test_all_text_in_quoted_identifiers_comments_and_dollar_regions_stays_opaque(wrapper):
    def wrap(sql):
        return {
            "string": "'" + sql.replace("'", "''") + "'",
            "identifier": '"' + sql.replace('"', '""') + '"',
            "line-comment": "-- " + sql + "\n",
            "block-comment": "/* " + sql + " */",
            "nested-comment": "/* outer /* " + sql + " */ end */",
            "dollar": "$$" + sql + "$$",
            "tagged-dollar": "$all_guard$" + sql + "$all_guard$",
        }[wrapper]
    outer, element = wrap(OUTER), wrap(ELEMENT)
    assert normalize_check_sql(outer) == outer and normalize_check_sql(element) == element
    assert normalize_check_sql(outer) != normalize_check_sql(element)
    assert normalize_check_sql(outer + " AND x::text <> " + OUTER) == outer + " AND x::text <> " + ELEMENT


@pytest.mark.parametrize("quantifier", ["ANY", "ALL"])
@pytest.mark.parametrize("prefix", ["namespace_\u0301", "\u03c0", "namespace_\u200d", "namespace_\uff21"])
def test_non_ascii_prefix_cannot_open_an_unknown_identifier_boundary(quantifier, prefix):
    outer, element = OUTER.replace("ALL", quantifier, 1), ELEMENT.replace("ALL", quantifier, 1)
    unknown = prefix + outer
    assert normalize_check_sql(unknown) == unknown
    assert normalize_check_sql(prefix + element) == prefix + element
    assert normalize_check_sql(unknown) != normalize_check_sql(prefix + element)
    assert normalize_check_sql(unknown + " AND x::text <> " + outer) == unknown + " AND x::text <> " + element


@pytest.mark.parametrize("suffix", ["'unterminated", '"unterminated', "/* unterminated", "$tag$unterminated", "E'\\\\escaped'", "$\u03c0$unknown " + OUTER + "$\u03c0$"])
def test_ambiguous_or_unsupported_lexical_context_keeps_the_whole_all_expression_literal(suffix):
    sql = OUTER + " OR " + suffix
    assert normalize_check_sql(sql) == sql


@pytest.mark.parametrize("dialect", ["sqlite", "POSTGRESQL", "postgresql16", None])
def test_no_pg_dialect_alias_or_other_signature_enables_check_casts(dialect):
    actual, expected = deepcopy(RECORD["actual"]), deepcopy(RECORD["expected"])
    actual["dialect"] = expected["dialect"] = dialect
    assert canonical_signature(actual) == actual and canonical_signature(expected) == expected
    assert not schema_signatures_equal(actual, expected) and not schema_signatures_equal(expected, actual)


@pytest.mark.parametrize("field", ["default", "index-predicate", "nullable", "column-type", "type-length", "foreign-key", "check-name", "index-name", "extra-leaf"])
def test_full39_other_catalog_leaves_stay_exact_even_when_the_four_checks_match(field):
    actual, expected = deepcopy(RECORD["actual"]), deepcopy(RECORD["expected"])
    table = actual["tables"]["privacy_requests"]
    if field == "default":
        table["columns"][0]["default"] = ELEMENT
        expected["tables"]["privacy_requests"]["columns"][0]["default"] = OUTER
    elif field == "index-predicate":
        table["indexes"][0]["where"] = ELEMENT
        expected["tables"]["privacy_requests"]["indexes"][0]["where"] = OUTER
    elif field == "nullable":
        table["columns"][0]["nullable"] = not table["columns"][0]["nullable"]
    elif field == "column-type":
        table["columns"][0]["type"] = "UNREVIEWED-TYPE"
    elif field == "type-length":
        table["columns"][0]["type_attributes"]["length"] = 777
    elif field == "foreign-key":
        table["foreign_keys"][0]["options"]["ondelete"] = "SET NULL"
    elif field == "check-name":
        table["checks"][0]["name"] += "_changed"
    elif field == "index-name":
        table["indexes"][0]["name"] += "_changed"
    else:
        actual["extra_catalog_leaf"] = True
    assert not schema_signatures_equal(actual, expected) and not schema_signatures_equal(expected, actual)


@pytest.mark.parametrize("section", ["tenant_security", "product_analytics_security"])
def test_new_all_cast_rule_never_expands_the_pinned_policy_comparator(section):
    def policy(sql):
        return {"dialect": "postgresql", "policies": [["owned", "read", "SELECT", ["app"], "PERMISSIVE", sql, None]]}
    assert not policy_signatures_equal(policy(OUTER), policy(ELEMENT))
    actual = {"signature": RECORD["actual"], section: policy(ELEMENT)}
    expected = {"signature": RECORD["expected"], section: policy(OUTER)}
    assert not schema_contracts_equal(actual, expected) and not schema_contracts_equal(expected, actual)


def test_all_preserves_doubled_quotes_value_order_and_every_parenthesis():
    outer = "ALL (ARRAY['owner''s gym'::character varying, ''::character varying]::text[])"
    element = "ALL (ARRAY['owner''s gym'::character varying::text, ''::character varying::text])"
    assert normalize_check_sql(outer) == element
    assert normalize_check_sql("(" + outer + ")") != element
    reverse = "ALL (ARRAY[''::character varying, 'owner''s gym'::character varying]::text[])"
    assert normalize_check_sql(reverse) != element
