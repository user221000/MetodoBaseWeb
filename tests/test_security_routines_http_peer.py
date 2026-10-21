"""Independent current37 real HTTP routine boundaries, no principal override."""
import re
import uuid
from datetime import UTC, datetime
from html.parser import HTMLParser

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from tests import account_security37_http as existing
from tests.followup34_http import PASSWORD
from web.database.models import Cliente, UserRole, Usuario

account37_engine = existing.account37_engine
followup_db = existing.followup_db
routine_peer_http = existing.account_http
URL = "/api/rutinas/catalogo"


def actor(case, *, role=UserRole.VIEWER, team=None, tipo="usuario"):
    from web.auth import hash_password

    identifier, email = str(uuid.uuid4()), uuid.uuid4().hex + "@example.invalid"
    with Session(case["admin"]) as db:
        db.add(Usuario(id=identifier, email=email, nombre="Synthetic peer reader",
                       password_hash=hash_password(PASSWORD), tipo=tipo, role=role,
                       team_gym_id=team))
        db.commit()
    reply = case["raw"].post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert reply.status_code == 200, "Persisted peer actor real password login"
    case["raw"].headers["Authorization"] = "Bearer " + reply.json()["token"]
    me = case["raw"].get("/api/auth/me")
    assert me.status_code == 200 and me.json()["id"] == identifier
    assert not case["raw"].app.dependency_overrides
    return identifier


def private(reply, status):
    assert reply.status_code == status
    assert reply.headers["cache-control"] == "no-store"
    assert reply.headers["referrer-policy"] == "no-referrer"
    assert reply.headers["x-content-type-options"] == "nosniff"
    assert "application/json" in reply.headers["content-type"]


def get(case, scope, **extra):
    return case["raw"].get(URL, params={"context": scope, **extra})


def test_real_matrix_is_read_only_generic_and_never_adopts_client(routine_peer_http):
    case = routine_peer_http
    with Session(case["admin"]) as db:
        before = db.scalar(select(func.count()).select_from(Cliente))
    owner = get(case, "gym")
    private(owner, 200)
    program = owner.json()["program"]
    assert [len(s["exercises"]) for s in program["sessions"]] == [4, 4, 5]
    for role, team, gym in [(UserRole.VIEWER, None, False), (UserRole.ADMIN, case["user"], True),
                            (UserRole.NUTRIOLOGO, case["user"], True), (UserRole.VIEWER, case["user"], True)]:
        identifier = actor(case, role=role, team=team)
        statements = []

        def observe(_connection, _cursor, sql, _parameters, _context, _many, statements=statements):
            statements.append(sql.lstrip().split(None, 1)[0].upper())

        event.listen(case["engine"], "before_cursor_execute", observe)
        try:
            for _ in range(2):
                reply = get(case, "personal", gym_id=case["user"], client_id=case["profile"],
                            user_id=case["user"], team_gym_id=case["user"])
                private(reply, 200)
                assert reply.json() == {"version": 1, "scope": "personal", "program": program}
                assert all(value not in reply.text for value in (identifier, case["profile"], case["user"]))
            private(get(case, "gym", client_id=case["profile"]), 200 if gym else 403)
        finally:
            event.remove(case["engine"], "before_cursor_execute", observe)
        assert statements and not set(statements) & {"INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "ALTER", "DROP"}
    with Session(case["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(Cliente)) == before


def test_actor_revocation_null_invite_and_signed_scope_forgery(routine_peer_http):
    case = routine_peer_http
    for change in ("inactive", "deleted", "invitation_empty", "sv_increment", "tenant_transfer"):
        identifier = actor(case, team=case["user"])
        private(get(case, "gym"), 200)
        with Session(case["admin"]) as db:
            row = db.get(Usuario, identifier)
            if change == "inactive":
                row.activo = False
            elif change == "deleted":
                row.deleted_at = datetime.now(UTC)
            elif change == "invitation_empty":
                row.invitation_token = ""
            elif change == "sv_increment":
                row.session_version += 1
            else:
                row.team_gym_id = None
            db.commit()
        try:
            reply = get(case, "gym", gym_id=case["user"], client_id=case["profile"])
            assert reply.status_code in (401, 403)
            private(reply, reply.status_code)
            assert "program" not in reply.json()
        finally:
            if change == "invitation_empty":
                with Session(case["admin"]) as db:
                    db.get(Usuario, identifier).invitation_token = None
                    db.commit()
    actor(case)
    from web.auth import _decode_token, _make_token

    access = case["raw"].headers["Authorization"][7:]
    original = _decode_token(access)
    # Negative tampering under the isolated test signer; no fabricated positive acceptance.
    for key, value in (("role", "owner"), ("team_gym_id", case["user"]), ("sv", True), ("id", str(uuid.uuid4()))):
        case["raw"].headers["Authorization"] = "Bearer " + _make_token({**original, key: value})
        reply = get(case, "gym", gym_id=case["user"])
        assert reply.status_code in (401, 403)
        private(reply, reply.status_code)
        assert "program" not in reply.json()


def test_parent_must_remain_canonical_for_both_spaces(routine_peer_http):
    case = routine_peer_http
    identifier = actor(case, team=case["user"])
    assert identifier != case["user"]
    for changes in ({"role": UserRole.ADMIN}, {"invitation_token": ""},
                    {"deleted_at": datetime.now(UTC)}, {"team_gym_id": identifier},
                    {"tipo": "usuario"}, {"activo": False}):
        private(get(case, "gym"), 200)
        with Session(case["admin"]) as db:
            parent = db.get(Usuario, case["user"])
            original = {key: getattr(parent, key) for key in changes}
            for key, value in changes.items():
                setattr(parent, key, value)
            db.commit()
        try:
            for scope in ("gym", "personal"):
                reply = get(case, scope)
                assert reply.status_code in (401, 403)
                private(reply, reply.status_code)
                assert "program" not in reply.json()
        finally:
            with Session(case["admin"]) as db:
                parent = db.get(Usuario, case["user"])
                for key, value in original.items():
                    setattr(parent, key, value)
                db.commit()


def test_ambiguity_validation_and_methods_have_no_fallback(routine_peer_http):
    case = routine_peer_http
    actor(case, role=UserRole.OWNER)
    for scope in ("personal", "gym"):
        reply = get(case, scope)
        private(reply, 403)
        assert reply.json()["detail"]["code"] == "routine_context_forbidden"
    for value in (None, "", "GYM", "personal/../gym", "private-sentinel@example.invalid"):
        reply = case["raw"].get(URL, params={} if value is None else {"context": value})
        private(reply, 422)
        assert reply.json()["detail"]["code"] == "routine_invalid_context"
        assert "private-sentinel" not in reply.text
    assert case["raw"].post(URL, json={"context": "gym"}).status_code == 405
    case["raw"].headers.pop("Authorization", None)
    reply = get(case, "gym")
    private(reply, 401)
    assert reply.headers["www-authenticate"] == "Bearer"


def test_owned_read_failure_is_opaque_after_real_auth(routine_peer_http, monkeypatch):
    from web.routes import routines

    case = routine_peer_http
    private(get(case, "gym"), 200)

    def broken(principal, scope):
        assert principal["id"] == case["user"] and scope == "gym"
        raise RuntimeError("SELECT password_hash; private-sentinel@example.invalid")

    monkeypatch.setattr(routines, "_read", broken)
    reply = get(case, "gym")
    private(reply, 503)
    assert reply.json()["detail"]["code"] == "routine_unavailable"
    assert all(value not in reply.text for value in ("SELECT", "password_hash", "sentinel", case["user"]))


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts.append(dict(attrs))


def test_all_four_public_shells_are_inert_and_nonce_bound(routine_peer_http):
    case = routine_peer_http
    case["raw"].headers.pop("Authorization", None)
    nonces = set()
    for path in ("/rutinas", "/rutinas/", "/mis-rutinas", "/mis-rutinas/"):
        reply = case["raw"].get(path)
        assert reply.status_code == 200
        parser = Scripts()
        parser.feed(reply.text)
        csp = reply.headers["content-security-policy"]
        nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
        nonces.add(nonce)
        own = [row for row in parser.scripts if row.get("src", "").startswith("/static/js/")]
        assert own and all(row.get("nonce") == nonce for row in own)
        assert 'data-routine-content hidden' in reply.text
        assert all(value not in reply.text for value in ("chest-press", case["user"], case["profile"]))
        assert 'data-scope="' + ("personal" if "mis-rutinas" in path else "gym") + '"' in reply.text
    assert len(nonces) == 4
