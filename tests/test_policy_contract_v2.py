"""Catalog-only policy cast equivalence; no SQL, services or restore execution."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys

import pytest
from web.database.alembic.policy_contract_v2 import (
    canonical_policy_signature, normalize_policy_sql, policy_signatures_equal,
)
from web.database.alembic.schema_contract_v2 import schema_contracts_equal

RECORD = json.loads((Path(__file__).parent / "data/schema_contract_v2/pg38_policy_restore_pairs.json").read_bytes())
STRUCTURE = json.loads((Path(__file__).parent / "data/schema_contract_v2/pg38_restore_pairs.json").read_bytes())
OUTER = "ANY ((ARRAY['origin_declared'::character varying, 'plan_assignment_published'::character varying])::text[])"
ELEMENT = "ANY (ARRAY[('origin_declared'::character varying)::text, ('plan_assignment_published'::character varying)::text])"


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def _minimal(sql, slot=5):
    row = ["facts", "read", "PERMISSIVE", "{public}", "SELECT", None, None]
    row[slot] = sql
    return {"dialect": "postgresql", "policies": [row]}


@pytest.mark.parametrize("case", RECORD["sections"], ids=["tenant-read36", "product-read1"])
def test_real_catalog_pairs_are_symmetric_idempotent_and_copy_safe(case):
    actual, expected = deepcopy(case["actual"]), deepcopy(case["expected"])
    old_actual, old_expected = deepcopy(actual), deepcopy(expected)
    assert actual != expected
    assert policy_signatures_equal(actual, expected) and policy_signatures_equal(expected, actual)
    assert canonical_policy_signature(actual) == actual
    assert canonical_policy_signature(expected) == actual
    assert canonical_policy_signature(canonical_policy_signature(expected)) == actual
    assert actual == old_actual and expected == old_expected
    changed = []
    for index, (left, right) in enumerate(zip(expected["policies"], actual["policies"])):
        assert len(left) == len(right) == 7
        for slot, (a, b) in enumerate(zip(left, right)):
            if a != b:
                changed.append(f"/policies/{index}/{slot}")
    assert changed == [case["path"]]
    for key in actual.keys() - {"policies"}:
        assert actual[key] == expected[key]


@pytest.mark.parametrize("case", RECORD["sections"], ids=["tenant-origin", "product-origin"])
def test_original_source_catalogs_are_literal_and_unchanged(case):
    assert case["source_actual"] == case["source_expected"]
    before = deepcopy(case["source_actual"])
    assert policy_signatures_equal(case["source_actual"], case["source_expected"])
    assert case["source_actual"] == before


@pytest.mark.parametrize("slot", [5, 6], ids=["qual", "with-check"])
def test_only_policy_expression_slots_admit_the_observed_casts(slot):
    actual, expected = _minimal(ELEMENT, slot), _minimal(OUTER, slot)
    assert policy_signatures_equal(actual, expected) and policy_signatures_equal(expected, actual)
    other = 6 if slot == 5 else 5
    assert canonical_policy_signature(expected)["policies"][0][other] is None


@pytest.mark.parametrize("old,new", [
    (" OR ", " AND "), (" AND ", " OR "),
    ("owner_id", "foreign_owner_id"), ("r12_actor_valid()", "true"),
    ("app.current_tenant", "app.mfa_actor"), ("'gym'::text", "'personal'::text"),
    ("'active'::text", "'revoked'::text"), ("NULLIF(", "COALESCE("),
    (" = ANY ", " <> ANY "), (" AND ", "  AND "),
], ids=["or-and", "and-or", "owner", "r12-actor", "tenant-setting", "context", "membership", "null-semantics", "operator", "spacing"])
def test_cast_equivalence_never_hides_a_changed_authorization_predicate(old, new):
    case = RECORD["sections"][0]
    actual, expected = deepcopy(case["actual"]), deepcopy(case["expected"])
    row = actual["policies"][36]
    assert old in row[5]
    row[5] = row[5].replace(old, new, 1)
    assert not policy_signatures_equal(actual, expected)
    assert not policy_signatures_equal(expected, actual)


@pytest.mark.parametrize("field", ["table", "policy-name", "permissive", "roles", "command", "row-order", "row-length"])
def test_policy_identity_roles_command_layout_and_order_remain_exact(field):
    case = RECORD["sections"][1]
    actual, expected = deepcopy(case["actual"]), deepcopy(case["expected"])
    row = actual["policies"][1]
    if field == "table":
        row[0] = "other_facts"
    elif field == "policy-name":
        row[1] = "other_read"
    elif field == "permissive":
        row[2] = "RESTRICTIVE"
    elif field == "roles":
        row[3] = "{other_role}"
    elif field == "command":
        row[4] = "ALL"
    elif field == "row-order":
        actual["policies"].reverse()
    else:
        row.append("unexpected")
    assert not policy_signatures_equal(actual, expected)
    assert not policy_signatures_equal(expected, actual)


@pytest.mark.parametrize("field", ["tenant-force", "tenant-rls", "set-tenant-body", "function-body", "function-proacl", "function-owner-security", "trigger", "product-force", "product-rls"])
def test_functions_acl_tables_flags_and_triggers_are_never_normalized(field):
    case = RECORD["sections"][0 if field.startswith("tenant") or field.startswith("set-tenant") else 1]
    actual, expected = deepcopy(case["actual"]), deepcopy(case["expected"])
    if field == "tenant-force":
        actual["tables"][0][2] = not actual["tables"][0][2]
    elif field == "tenant-rls":
        actual["tables"][0][1] = not actual["tables"][0][1]
    elif field == "set-tenant-body":
        actual["set_tenant"][0][2] += " "
    elif field == "function-body":
        actual["functions"][0][8] += " "
    elif field == "function-proacl":
        actual["functions"][0][7] = ["=X/other_role"]
    elif field == "function-owner-security":
        actual["functions"][0][3] = not actual["functions"][0][3]
    elif field == "trigger":
        actual["triggers"][0][5] += " "
    elif field == "product-force":
        actual["flags"][0][2] = not actual["flags"][0][2]
    else:
        actual["flags"][0][1] = not actual["flags"][0][1]
    assert not policy_signatures_equal(actual, expected)
    assert not policy_signatures_equal(expected, actual)


def test_whole_contract_composes_structure_and_only_two_security_sections():
    actual = {"signature": deepcopy(STRUCTURE["actual"])}
    expected = {"signature": deepcopy(STRUCTURE["expected"])}
    for key, case in zip(("tenant_security", "product_analytics_security"), RECORD["sections"]):
        actual[key], expected[key] = deepcopy(case["actual"]), deepcopy(case["expected"])
    old_actual, old_expected = deepcopy(actual), deepcopy(expected)
    assert schema_contracts_equal(actual, expected) and schema_contracts_equal(expected, actual)
    assert actual == old_actual and expected == old_expected
    expected["signature"]["tables"]["product_analytics_facts"]["columns"][0]["nullable"] = True
    actual["signature"]["tables"]["product_analytics_facts"]["columns"][0]["nullable"] = False
    assert not schema_contracts_equal(actual, expected)
    expected.pop("tenant_security")
    assert not schema_contracts_equal(actual, expected)


@pytest.mark.parametrize("section", ["member_link_security", "history_order_index", "progress_security", "google_identity_security", "followup_security", "notification_security", "privacy_security", "unknown_security"])
def test_all_other_contract_sections_keep_literal_comparison(section):
    actual = {"signature": deepcopy(STRUCTURE["actual"]), section: _minimal(ELEMENT)}
    expected = {"signature": deepcopy(STRUCTURE["expected"]), section: _minimal(OUTER)}
    assert not schema_contracts_equal(actual, expected)
    assert not schema_contracts_equal(expected, actual)


@pytest.mark.parametrize("wrapper", ["string", "identifier", "line-comment", "block-comment", "nested-comment", "dollar", "tagged-dollar"])
def test_policy_cast_text_in_opaque_regions_is_never_rewritten(wrapper):
    def wrap(sql):
        return {
            "string": "'" + sql.replace("'", "''") + "'",
            "identifier": '"' + sql.replace('"', '""') + '"',
            "line-comment": "-- " + sql + "\n",
            "block-comment": "/* " + sql + " */",
            "nested-comment": "/* nested /* " + sql + " */ end */",
            "dollar": "$$" + sql + "$$",
            "tagged-dollar": "$policy_v2$" + sql + "$policy_v2$",
        }[wrapper]
    left, right = wrap(OUTER), wrap(ELEMENT)
    assert normalize_policy_sql(left) == left and normalize_policy_sql(right) == right
    assert normalize_policy_sql(left) != normalize_policy_sql(right)
    assert normalize_policy_sql(left + " AND x::text = " + OUTER) == left + " AND x::text = " + ELEMENT


@pytest.mark.parametrize("unknown", [
    OUTER.replace("character varying", "character varying(32)"),
    OUTER.replace("character varying", "varchar"),
    OUTER.replace("character varying", "text"),
    OUTER.replace("character varying", "citext"),
    OUTER.replace("'plan_assignment_published'::character varying", "NULL"),
    OUTER.replace("'origin_declared'::character varying", "lower('origin_declared')::character varying"),
    OUTER.replace("::text[]", "::text[][]"),
    OUTER.replace("::text[]", "::text[] COLLATE other_collation"),
    OUTER.replace(", ", ","),
    OUTER.replace("ANY ((ARRAY", "ANY (ARRAY").replace("])::text[]", "]::text[]"),
    ELEMENT.replace("('origin_declared'::character varying)::text", "'origin_declared'::character varying::text"),
    ELEMENT.replace("('origin_declared'::character varying)::text", "('origin_declared'::character varying)"),
    "NOT" + OUTER,
    "catalog." + OUTER,
    "namespace_\u03c0" + OUTER,
    OUTER.replace("ANY ", "ANY  "),
], ids=["typmod", "varchar-alias", "text-source", "citext", "null", "function", "dimension", "collation", "spacing", "check-form", "mixed-parentheses", "mixed-casts", "identifier-prefix", "qualified", "unicode-prefix", "keyword-spacing"])
def test_unreviewed_policy_cast_forms_types_and_null_remain_literal(unknown):
    assert normalize_policy_sql(unknown) == unknown
    assert normalize_policy_sql(unknown) != ELEMENT


@pytest.mark.parametrize("suffix", ["'unterminated", '"unterminated', "/* unterminated", "$tag$unterminated", "E'\\\\escaped'", "$\u03c0$literal " + OUTER + "$\u03c0$", "$1"], ids=["string", "identifier", "comment", "dollar", "escape", "unicode-dollar", "parameter"])
def test_ambiguous_policy_lexical_context_disables_the_whole_rewrite(suffix):
    sql = OUTER + " AND " + suffix
    assert normalize_policy_sql(sql) == sql


@pytest.mark.parametrize("kind", ["sqlite", "missing-dialect", "other-field", "tuple-row", "short-row", "long-row", "renamed-policies"])
def test_non_pg_and_non_policy_shapes_remain_literal(kind):
    actual, expected = _minimal(ELEMENT), _minimal(OUTER)
    if kind == "sqlite":
        actual["dialect"] = expected["dialect"] = "sqlite"
    elif kind == "missing-dialect":
        actual.pop("dialect"); expected.pop("dialect")
    elif kind == "other-field":
        actual = {"dialect": "postgresql", "policies": [], "sql": ELEMENT}
        expected = {"dialect": "postgresql", "policies": [], "sql": OUTER}
    elif kind == "tuple-row":
        actual["policies"][0] = tuple(actual["policies"][0])
        expected["policies"][0] = tuple(expected["policies"][0])
    elif kind == "short-row":
        actual["policies"][0].pop(); expected["policies"][0].pop()
    elif kind == "long-row":
        actual["policies"][0].append(None); expected["policies"][0].append(None)
    else:
        actual["other_policies"] = actual.pop("policies")
        expected["other_policies"] = expected.pop("policies")
    assert not policy_signatures_equal(actual, expected)
    assert not policy_signatures_equal(expected, actual)


def test_literal_values_order_parentheses_and_non_string_values_stay_exact():
    outer = "ANY ((ARRAY['owner''s fact'::character varying, ''::character varying])::text[])"
    element = "ANY (ARRAY[('owner''s fact'::character varying)::text, (''::character varying)::text])"
    assert normalize_policy_sql(outer) == element
    assert normalize_policy_sql("(" + OUTER + ")") != normalize_policy_sql(ELEMENT)
    reversed_values = ELEMENT.replace("'origin_declared'", "'temporary'").replace("'plan_assignment_published'", "'origin_declared'").replace("'temporary'", "'plan_assignment_published'")
    assert normalize_policy_sql(OUTER) != normalize_policy_sql(reversed_values)
    for value in (None, 0, False, [], {}):
        assert normalize_policy_sql(value) == value


@pytest.mark.parametrize("first", ["schema_contract_v2", "policy_contract_v2"], ids=["schema-first", "policy-first"])
def test_fresh_import_orders_compose_without_a_cycle_and_restore_module_bindings(first):
    package = importlib.import_module("web.database.alembic")
    names = ("schema_contract_v2", "policy_contract_v2")
    missing = object()
    saved_modules = {name: sys.modules.get("web.database.alembic." + name, missing) for name in names}
    saved_attributes = {name: vars(package).get(name, missing) for name in names}
    try:
        for name in names:
            sys.modules.pop("web.database.alembic." + name, None)
            vars(package).pop(name, None)
        importlib.import_module("web.database.alembic." + first)
        for name in names:
            importlib.import_module("web.database.alembic." + name)
        schema = sys.modules["web.database.alembic.schema_contract_v2"]
        policy = sys.modules["web.database.alembic.policy_contract_v2"]
        assert schema.schema_contracts_equal({"tenant_security": _minimal(ELEMENT)}, {"tenant_security": _minimal(OUTER)})
        assert policy.policy_signatures_equal(_minimal(ELEMENT), _minimal(OUTER))
    finally:
        for name in names:
            full = "web.database.alembic." + name
            if saved_modules[name] is missing:
                sys.modules.pop(full, None)
            else:
                sys.modules[full] = saved_modules[name]
            if saved_attributes[name] is missing:
                vars(package).pop(name, None)
            else:
                vars(package)[name] = saved_attributes[name]
    for name in names:
        assert sys.modules.get("web.database.alembic." + name, missing) is saved_modules[name]
        assert vars(package).get(name, missing) is saved_attributes[name]


def test_combining_mark_prefix_is_not_a_policy_expression_boundary():
    prefixed_outer = "namespace_\u0301" + OUTER
    prefixed_element = "namespace_\u0301" + ELEMENT
    assert normalize_policy_sql(prefixed_outer) == prefixed_outer
    assert normalize_policy_sql(prefixed_element) == prefixed_element
    assert normalize_policy_sql(prefixed_outer) != normalize_policy_sql(prefixed_element)
    # An independent expression after the unknown name still has a safe boundary.
    sql = prefixed_outer + " AND x::text = " + OUTER
    assert normalize_policy_sql(sql) == prefixed_outer + " AND x::text = " + ELEMENT
