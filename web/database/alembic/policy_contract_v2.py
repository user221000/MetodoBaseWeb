"""Policy comparison v2: only observed varchar-array casts in PG expressions.

The v1 catalog producers and RAW targets stay unchanged. No SQL is executed.
"""
from copy import deepcopy
import re

from web.database.alembic.schema_contract_v2 import _VALUE, _opaque_end

_LITERAL = re.compile(r"(?P<value>" + _VALUE + r")::character varying")
_OUTER_ITEM = _VALUE + r"::character varying"
_ELEMENT_ITEM = r"\(" + _OUTER_ITEM + r"\)::text"
_OUTER = re.compile(r"ANY \(\(ARRAY\[(?P<items>" + _OUTER_ITEM
                    + r"(?:, " + _OUTER_ITEM + r")*)\]\)::text\[\]\)")
_ELEMENT = re.compile(r"ANY \(ARRAY\[(?P<items>" + _ELEMENT_ITEM
                      + r"(?:, " + _ELEMENT_ITEM + r")*)\]\)")


def normalize_policy_sql(sql):
    """Preserve all text except the two recorded parenthesized cast forms."""
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
        match = None if inside_name else (_OUTER.match(sql, index) or _ELEMENT.match(sql, index))
        if match:
            literals = _LITERAL.finditer(match["items"])
            output.append("ANY (ARRAY[" + ", ".join("(" + item["value"]
                          + "::character varying)::text" for item in literals) + "])")
            index = match.end()
            continue
        output.append(sql[index])
        index += 1
    return "".join(output)


def canonical_policy_signature(signature):
    """Normalize copies of QUAL/WITH_CHECK only, in seven-field PG rows."""
    result = deepcopy(signature)
    if not isinstance(result, dict) or result.get("dialect") != "postgresql":
        return result
    policies = result.get("policies")
    if not isinstance(policies, list):
        return result
    for row in policies:
        if isinstance(row, list) and len(row) == 7:
            row[5] = normalize_policy_sql(row[5])
            row[6] = normalize_policy_sql(row[6])
    return result


def policy_signatures_equal(actual, expected):
    """Both sides receive the same rule; every other catalog leaf stays exact."""
    return canonical_policy_signature(actual) == canonical_policy_signature(expected)
