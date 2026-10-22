"""Finite current37 PG phases; no collection or SQL at import time."""
import json
from pathlib import Path

from tests.ci_web37.pg_legacy import specification

ROOT = Path(__file__).resolve().parents[2]
CURRENT = (
    ("migration37", "tests/integration_account_security37_pg_migrations.py", 12),
    ("nutrition", "tests/integration_current37_nutrition.py", 13),
    ("notifications", "tests/integration_current37_notifications.py", 29),
    ("account", "tests/integration_current37_account.py", 35),
    ("independent-qa", "tests/integration_security_account37_peer.py", 30),
    ("restore", "tests/integration_current37_restore.py", 1),
    ("security-notifications", "tests/integration_current37_security_notifications.py", 31),
    ("onboarding-author", "tests/integration_current37_onboarding_author.py", 16),
    ("onboarding-security", "tests/integration_current37_onboarding_security.py", 19),
    ("qa26-primary", "tests/integration_current37_qa26_primary.py", 7),
    ("qa26-registration", "tests/integration_current37_qa26_registration.py", 2),
)


def phases():
    legacy = specification()["groups"]
    rows = [{"key": "legacy-" + key, "module": entry["companion"], "pool": entry["expected_pool"],
             "cases": len(entry["original_cases"]), "witness": "current37"} for key, entry in legacy.items()]
    rows += [{"key": key, "module": module, "cases": count, "pool": 1,
              "witness": "transition37" if key == "migration37" else
                         "independent_qa37" if key in {"independent-qa", "restore"} else "current37"}
             for key, module, count in CURRENT]
    oracle = json.loads((ROOT / "tests/ci_web37/pg-current37-nodeids.json").read_bytes())
    if len(rows) != 29 or sum(row["cases"] for row in rows) != 429 or len(oracle) != 29:
        raise ValueError("Current37 PG required phase/identity inventory differs")
    for row in rows:
        name = row["module"][:-3].replace("/", ".")
        row["expected"] = oracle[name]
        if len(row["expected"]) != row["cases"] or len(set(map(tuple, row["expected"]))) != row["cases"]:
            raise ValueError("Current37 PG required phase identities differ")
    return rows
