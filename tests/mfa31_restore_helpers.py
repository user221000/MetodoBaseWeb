"""Populated MFA31 restore witnesses; no prior restore fixture is retargeted."""
import base64
from datetime import datetime, timezone
import json

from fastapi import HTTPException
import pytest
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from web.database.models import Usuario, UserRole, MfaCredential, MfaRecoveryCode, MfaAuthorization
from web.database.mfa_policy import bind_mfa_actor
from web.services import mfa_service as mfa
from web.services.mfa_crypto import decrypt, opaque_digest, totp

KEY = base64.urlsafe_b64encode(b"mfa-restore31-synthetic-key-000000"[:32]).decode()
PASSWORD = "SyntheticRestoreMfaPassword123"


def populate_mfa31(engine, monkeypatch):
    from web.auth import crear_access_token, hash_password, identity_from_user
    from web.database.tenant_context import configure_tenant_engine
    from web.settings import get_settings
    configure_tenant_engine(engine)
    monkeypatch.setattr(get_settings(),"MFA_ENCRYPTION_KEY",KEY)
    ids = ["restore-mfa-owner-a", "restore-mfa-owner-b", "restore-mfa-member"]
    with Session(engine) as db:
        for index, actor in enumerate(ids):
            db.add(Usuario(id=actor,email=actor+"@example.invalid",password_hash=hash_password(PASSWORD),
                nombre="Synthetic restore MFA",tipo="gym" if index < 2 else "usuario",
                role=UserRole.OWNER if index < 2 else UserRole.ADMIN,
                team_gym_id=ids[0] if index == 2 else None,session_version=0,activo=True))
            db.flush()
        db.commit()
    now = datetime.now(timezone.utc)
    expected = {"actors":{}, "private_material":[], "grant":None, "proofs":[]}
    for actor in ids:
        with Session(engine) as db:
            current = identity_from_user(db.get(Usuario,actor),db)
        access = crear_access_token(current)
        with Session(engine) as db:
            primary = mfa.reauthenticate(db,current,access,password=PASSWORD,now=now)["reauthentication_token"]
        with Session(engine) as db:
            pending = mfa.enroll(db,current,access,primary,now=now)
        seed = base64.b32decode(pending["secret"])
        with Session(engine) as db:
            kit = mfa.confirm_enrollment(db,current,pending["enrollment_id"],totp(seed,int(now.timestamp())//30),now=now)
        with Session(engine) as db:
            current = identity_from_user(db.get(Usuario,actor),db)
        with Session(engine) as db:
            challenge = mfa.login(db,current,now=now)["challenge"]
        with Session(engine) as db:
            pair = mfa.verify_login(db,challenge,recovery_code=kit["recovery_codes"][0],now=now)
        expected["actors"][actor] = {"identity":current,"seed":seed,"access":pair["token"],"codes":kit["recovery_codes"],"consumed_challenge":challenge}
        expected["private_material"].extend([access,primary,pending["secret"],pending["otpauth_uri"],
            challenge,pair["token"],pair["refresh_token"],*kit["recovery_codes"]])
    owner = expected["actors"][ids[0]]
    with Session(engine) as db:
        primary = mfa.reauthenticate(db,owner["identity"],owner["access"],password=PASSWORD,now=now)["reauthentication_token"]
    with Session(engine) as db:
        replacement = mfa.enroll(db,owner["identity"],owner["access"],primary,recovery_code=owner["codes"][1],now=now)
    for consumed in (True,False):
        with Session(engine) as db:
            grant = mfa.issue_step_up(db,owner["identity"],owner["access"],"POST","/api/billing/portal",{"return_url":"/dashboard"},now=now)["grant"]
        if consumed:
            with Session(engine) as db:
                mfa.consume_step_up(db,owner["identity"],owner["access"],grant,"POST","/api/billing/portal",{"return_url":"/dashboard"},now=now)
                db.commit()
            expected["consumed_grant"] = grant
        else:
            expected["grant"] = grant
        expected["private_material"].append(grant)
    other = expected["actors"][ids[1]]
    with Session(engine) as db:
        challenge = mfa.login(db,other["identity"],now=now)["challenge"]
    with Session(engine) as db:
        primary = mfa.reauthenticate(db,other["identity"],other["access"],password=PASSWORD,now=now)["reauthentication_token"]
    expected["private_material"].extend([challenge,primary,replacement["secret"],replacement["otpauth_uri"]])
    expected["now"] = now
    return expected


def reject_plain_mfa31(rows, expected):
    serialized = json.dumps(rows,default=str)
    assert all(value not in serialized for value in expected["private_material"])
    assert len(rows["mfa_credentials"]) == 3 and len(rows["mfa_recovery_codes"]) == 24
    assert any(row["pending_ciphertext"] is not None for row in rows["mfa_credentials"])
    assert sum(row["used_at"] is not None for row in rows["mfa_recovery_codes"]) == 4
    assert {row["purpose"] for row in rows["mfa_authorizations"]} == {"login","reauth","action"}
    assert {row["consumed_at"] is not None for row in rows["mfa_authorizations"] if row["purpose"] == "action"} == {True,False}


def verify_restored_mfa31(target, restricted, expected, monkeypatch):
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(),"MFA_ENCRYPTION_KEY",KEY)
    with restricted.connect() as db:
        assert tuple(db.execute(text("SELECT rolsuper,rolbypassrls,pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='mfa_credentials'::regclass),'MEMBER') FROM pg_roles WHERE rolname=current_user")).one()) == (False,False,False)
        flags = db.execute(text("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname IN ('mfa_credentials','mfa_recovery_codes') ORDER BY relname")).all()
        assert len(flags) == 2 and all(tuple(row[1:]) == (True,True) for row in flags)
    with Session(restricted) as db:
        assert db.scalars(select(MfaCredential)).all() == []
        assert db.scalars(select(MfaRecoveryCode)).all() == []
    for actor, material in expected["actors"].items():
        with Session(restricted) as db:
            state = mfa.status(db,material["identity"],now=expected["now"])
            assert state["enabled"] is True
            row = db.scalars(select(MfaCredential)).one()
            assert row.user_id == actor and row.generation == 1
            assert decrypt(row.secret_ciphertext,mfa.configuration(),mfa._aad(row,1,"active")) == material["seed"]
            codes = db.scalars(select(MfaRecoveryCode)).all()
            assert len(codes) == 8 and all(code.user_id == actor for code in codes)
            assert {code.code_hash for code in codes} == {opaque_digest("recovery",value) for value in material["codes"]}
            assert db.scalar(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == actor,
                MfaRecoveryCode.code_hash == opaque_digest("recovery",material["codes"][0]),
                MfaRecoveryCode.used_at.is_(None))) is None
            assert state["pending"] is (actor == "restore-mfa-owner-a")
        with Session(restricted) as db, pytest.raises(HTTPException) as used_challenge:
            mfa.verify_login(db,material["consumed_challenge"],recovery_code=material["codes"][1])
        assert used_challenge.value.status_code == 400
        with Session(restricted) as db:
            assert db.scalars(select(MfaCredential)).all() == []
    actor = "restore-mfa-owner-a"
    owner = expected["actors"][actor]
    with Session(restricted) as db, pytest.raises(HTTPException) as used_grant:
        mfa.consume_step_up(db,owner["identity"],owner["access"],expected["consumed_grant"],"POST","/api/billing/portal",{"return_url":"/dashboard"})
    assert used_grant.value.status_code == 400
    with Session(restricted) as db:
        mfa.consume_step_up(db,owner["identity"],owner["access"],expected["grant"],"POST","/api/billing/portal",{"return_url":"/dashboard"},now=expected["now"])
        db.rollback()  # Validation must leave the restored physical rows exact.
    with Session(target) as db:
        assert db.get(MfaAuthorization,opaque_digest("action",expected["grant"])).consumed_at is None
    with Session(restricted) as db:
        bind_mfa_actor(db,actor)
        with pytest.raises(Exception) as caught:
            db.execute(update(MfaCredential).where(MfaCredential.user_id == actor).values(user_id="restore-mfa-owner-b"))
        assert getattr(caught.value.orig,"pgcode",None) == "42501"
    return {"actors":3,"tenants":2,"active_factors":3,"pending_replacement":1,
        "recovery_codes":24,"used_recovery_codes":4,"force_actor_isolation":True,
        "ciphertext_decrypts_only_with_independent_key_and_original_aad":True,
        "unused_grant_validated_then_rolled_back":True,"plaintext_absent_from_physical_rows":True}
