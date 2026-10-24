"""Symmetric comparison v2 over frozen v1 signatures; no schema mutation.

Only PostgreSQL CHECKs admit the observed varchar-literal ANY/ALL array cast
placement. The signature producer, historical v1 and RAW targets stay stable.
"""
from copy import deepcopy
import re

_VALUE = r"'(?:[^'\\]|'')*'"
_ITEM = re.compile(r"(?P<value>" + _VALUE + r")::character varying(?P<cast>::text)?")
_BARE_ITEM = _VALUE + r"::character varying(?:::text)?"
_ANY = re.compile(
    r"(?P<quantifier>ANY|ALL) \(ARRAY\[(?P<items>" + _BARE_ITEM + r"(?:, " + _BARE_ITEM
    + r")*)\](?P<cast>::text\[\])?\)"
)
_DOLLAR = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")


def _opaque_end(sql, start):
    """Copy quoted/comment regions; ambiguous escaping disables all rewrites."""
    character = sql[start]
    if character in {"'", '"'}:
        index = start + 1
        while index < len(sql):
            if sql[index] == "\\":
                return -1  # No assumption about escape-string/session settings.
            if sql[index] == character:
                if index + 1 < len(sql) and sql[index + 1] == character:
                    index += 2
                    continue
                return index + 1
            index += 1
        return -1
    if sql.startswith("--", start):
        end = sql.find("\n", start + 2)
        return len(sql) if end == -1 else end + 1
    if sql.startswith("/*", start):
        index, depth = start + 2, 1
        while index < len(sql):
            if sql.startswith("/*", index):
                depth += 1
                index += 2
            elif sql.startswith("*/", index):
                depth -= 1
                index += 2
                if not depth:
                    return index
            else:
                index += 1
        return -1
    if character == "$":
        delimiter = _DOLLAR.match(sql, start)
        if delimiter:
            end = sql.find(delimiter[0], delimiter.end())
            return -1 if end == -1 else end + len(delimiter[0])
        # PostgreSQL permits additional identifier characters in dollar tags.
        # Unsupported tags/parameters/names must never expose their contents.
        return -1
    return None


def normalize_check_sql(sql):
    """Preserve every character except one of two complete literal cast forms."""
    if not isinstance(sql, str):
        return sql
    output, index = [], 0
    while index < len(sql):
        end = _opaque_end(sql, index)
        if end == -1:
            return sql
        if end is not None:
            output.append(sql[index:end])
            index = end
            continue
        inside_name = index and (not sql[index - 1].isascii()
                                 or sql[index - 1].isalnum() or sql[index - 1] in "_$.")
        match = None if inside_name else _ANY.match(sql, index)
        if match:
            items = list(_ITEM.finditer(match["items"]))
            per_item = [item["cast"] is not None for item in items]
            outer = match["cast"] is not None
            # Deliberately exclude mixed/redundant casts and every other type,
            # expression, NULL, typmod, dimension, collation or spacing variant.
            if (outer and not any(per_item)) or (not outer and all(per_item)):
                output.append(match["quantifier"] + " (ARRAY[" + ", ".join(item["value"] + "::character varying::text" for item in items) + "])")
                index = match.end()
                continue
        output.append(sql[index])
        index += 1
    return "".join(output)


def canonical_signature(signature):
    """Only CHECK sql leaves change, on a copy, for PostgreSQL signatures."""
    result = deepcopy(signature)
    if not isinstance(result, dict) or result.get("dialect") != "postgresql":
        return result
    for table in result.get("tables", {}).values():
        for check in table.get("checks", []):
            check["sql"] = normalize_check_sql(check["sql"])
    return result


def schema_signatures_equal(actual, expected):
    return canonical_signature(actual) == canonical_signature(expected)


def schema_contracts_equal(actual, expected):
    """Compare structure plus two policy sections; every other leaf stays exact."""
    # Lazy import avoids a cycle: the policy helper reuses our opaque lexer.
    from web.database.alembic.policy_contract_v2 import policy_signatures_equal
    if not isinstance(actual, dict) or not isinstance(expected, dict) or actual.keys() != expected.keys():
        return False
    return all(schema_signatures_equal(actual[key], expected[key]) if key == "signature"
               else policy_signatures_equal(actual[key], expected[key])
               if key in {"tenant_security", "product_analytics_security"}
               else actual[key] == expected[key] for key in actual)
