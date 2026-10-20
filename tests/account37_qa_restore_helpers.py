"""Additive37 populated restore checks; no historical oracle is modified."""
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from web.database.account_security_schema_v1 import NAMES
from web.database.models import Usuario
from web.services import account_security as account, mfa_service as mfa


def private_backup_temporaries(monkeypatch, directory):
    import tempfile
    original = tempfile.TemporaryDirectory
    def private_directory(*args, **kwargs):
        if kwargs.get("dir") is not None:
            assert Path(kwargs["dir"]).resolve().is_relative_to(directory.resolve())
        else:
            kwargs["dir"] = str(directory)
        return original(*args, **kwargs)
    monkeypatch.setattr(tempfile, "TemporaryDirectory", private_directory)


def historical33_tables37(signature):
    from tests.notifications36_restore_helpers import historical33_tables
    tables = historical33_tables(signature)
    user = tables["usuarios"]
    assert set(NAMES) <= {column["name"] for column in user["columns"]}
    user["columns"] = [column for column in user["columns"] if column["name"] not in NAMES]
    checks = {"ck_usuario_verified_email_state", "ck_usuario_email_verification_state"}
    assert checks <= {row["name"] for row in user["checks"]}
    user["checks"] = [row for row in user["checks"] if row["name"] not in checks]
    assert any(row["name"] == "ix_usuarios_email_verification_hash" for row in user["indexes"])
    user["indexes"] = [row for row in user["indexes"] if row["name"] != "ix_usuarios_email_verification_hash"]
    return tables


def populate_contact37(source_url, source, monkeypatch):
    from tests.account37_qa_pg_fixtures import witness
    from tests.integration_provider_subjects import application_engine
    from web.auth import identity_from_user
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(), "RESEND_API_KEY", "synthetic-restore37-no-network")
    application = application_engine(source_url, source)
    witness(application)
    factory = sessionmaker(bind=application, expire_on_commit=True, autoflush=False)
    now = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=2)
    actors = {"pending": "restore-professional-member", "verified": "restore-personal-user", "stale": "restore-foreign-gym"}
    expected = {"actors": actors, "tokens": {}, "now": now}
    try:
        for state, user in actors.items():
            with Session(source) as db:
                identity = identity_from_user(db.get(Usuario, user), db)
            packets = []
            reply = account.issue_email(identity, factory=factory, now=now,
                sender=lambda recipient, link: packets.append((recipient, link)) or True)
            assert reply["delivery"] == "provider_accepted" and len(packets) == 1
            token = parse_qs(urlsplit(packets[0][1]).fragment)["token"][0]
            expected["tokens"][state] = token
            if state != "pending":
                assert account.confirm_email(token, factory=factory, now=now + timedelta(seconds=1))["email_verified"] is True
            if state == "stale":
                with Session(source) as db:
                    actor = db.get(Usuario, user)
                    original = actor.email
                    actor.email = "restore37-changed@example.invalid"
                    db.commit()
                    actor.email = original
                    db.commit()
                    assert actor.notification_contact_version == 2
    finally:
        application.dispose()
    return expected


def reject_plain_contact37(rows, expected):
    encoded = json.dumps(rows, default=str)
    assert all(token not in encoded for token in expected["tokens"].values())
    users = {row["id"]: row for row in rows["usuarios"]}
    pending = users[expected["actors"]["pending"]]
    assert pending["email_verification_hash"] == account.digest(expected["tokens"]["pending"])
    assert len(pending["email_verification_hash"]) == 64
    assert mfa.aware(pending["email_verification_expires_at"]) - mfa.aware(pending["email_verification_issued_at"]) == timedelta(minutes=30)
    assert pending["email_verification_session_version"] == pending["session_version"]
    assert pending["email_verification_contact_version"] == pending["notification_contact_version"]
    for state in ("verified", "stale"):
        actor = users[expected["actors"][state]]
        assert actor["email_verified_at"] is not None and all(actor[name] is None for name in account.PENDING)
        assert mfa.aware(actor["email_verified_at"]).utcoffset() == timedelta(0)
    assert users[expected["actors"]["verified"]]["email_verified_contact_version"] == 0
    assert users[expected["actors"]["stale"]]["email_verified_contact_version"] == 0
    assert users[expected["actors"]["stale"]]["notification_contact_version"] == 2


def assert_encrypted_contact37(manifest_path, expected):
    from scripts.backup_restore import MAGIC, verified_artifacts
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest["encryption"] == "AES-256-GCM" and manifest["authentication"] == "HMAC-SHA256-HKDF-v1"
    assert {row["kind"] for row in manifest["artifacts"]} == {"postgres", "objects"}
    for artifact in manifest["artifacts"]:
        content = (manifest_path.parent / artifact["file"]).read_bytes()
        assert content.startswith(MAGIC)
        assert all(token.encode() not in content for token in expected["tokens"].values())
    with verified_artifacts(manifest_path) as (_verified, artifacts):
        assert set(artifacts) == {"postgres", "objects"}


def verify_restored_contact37(admin, application, expected, snapshot):
    from tests.account37_qa_pg_fixtures import assert_blank_pool, witness
    from web.auth import identity_from_user
    baseline = snapshot(admin)
    reject_plain_contact37(baseline, expected)
    witness(application)
    factory = sessionmaker(bind=application, expire_on_commit=True, autoflush=False)
    statuses = {}
    for state, user in expected["actors"].items():
        with Session(application) as db:
            identity = identity_from_user(db.get(Usuario, user), db)
            statuses[state] = account.email_status(db, identity)["email_verified"]
    assert statuses == {"pending": False, "verified": True, "stale": False}
    pending = expected["actors"]["pending"]
    clauses = ["email_verification_expires_at=email_verification_issued_at",
               "email_verification_session_version=-1", "email_verified_at=now()"]
    for clause in clauses:
        with pytest.raises(IntegrityError) as failure, admin.begin() as db:
            db.execute(text("UPDATE usuarios SET " + clause + " WHERE id=:id"), {"id": pending})
        assert failure.value.orig.pgcode == "23514"
        assert snapshot(admin) == baseline
    fields = ",".join(account.PENDING)
    with pytest.raises(IntegrityError) as failure, admin.begin() as db:
        db.execute(text("UPDATE usuarios SET (" + fields + ")=(SELECT " + fields + " FROM usuarios WHERE id=:source) WHERE id=:target"),
                   {"source": pending, "target": expected["actors"]["stale"]})
    assert failure.value.orig.pgcode == "23505"
    assert snapshot(admin) == baseline
    # Only after every historical exact comparison do we consume one restored
    # purpose proof. The resulting row delta is enumerated, never excluded.
    assert account.confirm_email(expected["tokens"]["pending"], factory=factory)["email_verified"] is True
    with pytest.raises(HTTPException) as failure:
        account.confirm_email(expected["tokens"]["pending"], factory=factory)
    assert failure.value.status_code == 400
    after = snapshot(admin)
    for table in baseline:
        if table not in {"usuarios", "auth_audit_log"}:
            assert after[table] == baseline[table]
    before_users = {row["id"]: row for row in baseline["usuarios"]}
    after_users = {row["id"]: row for row in after["usuarios"]}
    assert before_users.keys() == after_users.keys()
    allowed = {*account.PENDING, "email_verified_at", "email_verified_contact_version"}
    for identifier, row in before_users.items():
        actual = after_users[identifier]
        if identifier != pending:
            assert actual == row
        else:
            assert {key: value for key, value in actual.items() if key not in allowed} == {key: value for key, value in row.items() if key not in allowed}
            assert all(actual[key] is None for key in account.PENDING)
            assert actual["email_verified_at"] is not None
            assert actual["email_verified_contact_version"] == actual["notification_contact_version"]
    audits = {row["id"]: row for row in baseline["auth_audit_log"]}
    actual_audits = {row["id"]: row for row in after["auth_audit_log"]}
    assert set(audits) <= set(actual_audits)
    assert all(actual_audits[identifier] == row for identifier, row in audits.items())
    added = [row for identifier, row in actual_audits.items() if identifier not in audits]
    assert len(added) == 1 and added[0]["event_type"] == "email_contact_verified" and added[0]["user_id"] == pending
    assert added[0]["event_metadata"] == {"purpose": "contact"}
    assert_blank_pool(application)
    return {"pending_verified_stale_metadata_restored": True, "purpose_proof_one_use_restored": True,
            "unique_and_state_checks": 4, "post_historical_mutation":"Exactly pending user seven evidence fields and one contact audit row; every other row exact.",
            "UTC": True, "no_new_session_role_MFA_or_refresh_authority": True}
