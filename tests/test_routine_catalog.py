"""Generic content and real HTTP session/role/read-only contracts."""
import json
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from core.routine_catalog import get_exercise_catalog, get_routine_program
from tests import account_security37_http as fixtures
from tests.followup34_http import PASSWORD
from web.database.models import Usuario, UserRole

ENDPOINT = "/api/rutinas/catalogo"
account37_engine = fixtures.account37_engine
followup_db = fixtures.followup_db
routine_http = fixtures.account_http


def test_catalog_is_generic_bounded_independent_and_complete():
    first, second = get_routine_program(), get_routine_program()
    assert first == second
    assert [row["id"] for row in first["sessions"]] == ["push", "pull", "legs"]
    identifiers = []
    for session in first["sessions"]:
        assert len(session["exercises"]) == 6
        for exercise in session["exercises"]:
            identifiers.append(exercise["id"])
            assert exercise["sets"] == {"minimum": 1, "maximum": 1}
            assert exercise["repetition_unit"] in {"repetitions", "seconds"}
            if exercise["repetition_unit"] == "seconds":
                assert exercise["slot"] == "core"
                assert exercise["repetitions"].startswith("20–30")
            else:
                assert exercise["repetitions"].removesuffix(" por lado") in {"8–12", "10–15"}
            assert 60 <= exercise["rest_seconds"] <= 120
            assert len(exercise["cues"]) >= 2
            assert exercise["equipment"] and exercise["alternative"]["equipment"]
            assert exercise["alternative"]["name"] and exercise["alternative"]["cue"]
    assert len(identifiers) == len(set(identifiers)) == 18
    assert len(json.dumps(first, ensure_ascii=False).encode()) < 32768
    assert "no asegura" in first["guideline_note"]
    first["sessions"][0]["exercises"][0]["cues"].append("Untrusted edit")
    assert get_routine_program() == second


def test_schedule_contract_allows_adjacent_days_and_continuous_rotation():
    first, second = get_routine_program(), get_routine_program()
    schedule = first["schedule"]
    assert schedule["sessions_per_week"] == 3
    assert schedule["available_sessions"] == [3, 4, 5, 6]
    assert schedule["nonconsecutive"] is False
    assert schedule["cycle"] == ["push", "pull", "legs"]
    assert schedule["rotation"] == "continuous"
    assert schedule["minimum_rest_days"] == 1
    assert len(schedule["days"]) == 7
    assert schedule["default_days"] == [0, 2, 4]
    schedule["default_days"].append(6)
    schedule["cycle"].reverse()
    schedule["available_sessions"].clear()
    assert get_routine_program() == second


def test_leg_library_preserves_named_gym_variants_and_seconds():
    library = {row["id"]: row for row in get_exercise_catalog()}
    assert "45°" in library["leg-press"]["name"]
    assert "mancuernas" in library["dumbbell-romanian-deadlift"]["name"]
    assert "sentado" in library["seated-leg-curl"]["name"]
    assert "No necesitas tocar el suelo" in library["dumbbell-romanian-deadlift"]["cues"][1]
    assert library["forearm-plank"]["repetition_unit"] == "seconds"
    assert library["machine-hip-adduction"]["muscles"] == ["Aductores de cadera"]
    assert "Glúteo medio" in library["machine-hip-abduction"]["muscles"]
    program = get_routine_program()
    assert program["generated"] is False
    assert [sum(row["sets"]["maximum"] for row in session["exercises"])
            for session in program["sessions"]] == [6, 6, 6]
    assert "5–6 días sólo si ya toleras" in program["starting_point"]


def login_actor(case, role=UserRole.VIEWER, *, team=False):
    """Fixture membership is persisted; identity comes from real password HTTP."""
    from web.auth import hash_password
    identity = str(uuid.uuid4())
    email = uuid.uuid4().hex + "@example.invalid"
    with Session(case["admin"]) as db:
        db.add(Usuario(id=identity, email=email, password_hash=hash_password(PASSWORD),
            nombre="Synthetic routine reader", tipo="usuario", role=role,
            team_gym_id=case["user"] if team else None))
        db.commit()
    reply = case["raw"].post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert reply.status_code == 200, "Real password login for persisted catalogue reader"
    token = reply.json()["token"]
    case["raw"].headers["Authorization"] = "Bearer " + token
    me = case["raw"].get("/api/auth/me")
    assert me.status_code == 200 and me.json()["id"] == identity
    return identity


def test_owner_and_personal_have_no_cross_space_or_bootstrap(routine_http):
    case = routine_http
    response = case["raw"].get(ENDPOINT, params={"context": "gym"})
    assert response.status_code == 200
    assert response.json() == {"version": 1, "scope": "gym", "program": get_routine_program()}
    assert response.headers["cache-control"] == "no-store"
    assert case["raw"].get(ENDPOINT, params={"context": "personal"}).status_code == 403
    login_actor(case)
    response = case["raw"].get(ENDPOINT, params={"context": "personal"})
    assert response.status_code == 200 and response.json()["program"] == get_routine_program()
    assert case["raw"].get(ENDPOINT, params={"context": "gym"}).status_code == 403
    # Every catalogue access includes the real bearer verifier; none uses an
    # auth dependency override or a fabricated positive token.
    assert not case["raw"].app.dependency_overrides


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER])
def test_valid_team_can_read_both_general_spaces(routine_http, role):
    case = routine_http
    login_actor(case, role, team=True)
    permissions = case["raw"].get("/api/auth/me").json()["permissions"]
    for context in ("gym", "personal"):
        response = case["raw"].get(ENDPOINT, params={"context": context})
        assert response.status_code == 200
        assert response.json()["scope"] == context
        assert response.json()["program"] == get_routine_program()
    assert case["raw"].get("/api/auth/me").json()["permissions"] == permissions


def test_read_paths_do_not_write_or_return_subject_data(routine_http):
    case = routine_http
    statements = []
    def observe(_connection, _cursor, sql, _parameters, _context, _many):
        statements.append(sql.lstrip().split(None, 1)[0].upper())
    event.listen(case["engine"], "before_cursor_execute", observe)
    try:
        for _ in range(2):
            reply = case["raw"].get(ENDPOINT, params={"context": "gym"})
            assert reply.status_code == 200
    finally:
        event.remove(case["engine"], "before_cursor_execute", observe)
    assert not ({"INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"} & set(statements))
    assert set(reply.json()) == {"version", "scope", "program"}
    assert case["user"] not in reply.text and case["profile"] not in reply.text


@pytest.mark.parametrize("change", ["inactive", "deleted", "pending", "stale_sv", "parent_changed"])
def test_persisted_revocation_is_enforced(routine_http, change):
    case = routine_http
    actor = login_actor(case, UserRole.NUTRIOLOGO, team=True)
    with Session(case["admin"]) as db:
        row = db.get(Usuario, case["user"] if change == "parent_changed" else actor)
        if change in ("inactive", "parent_changed"):
            row.activo = False
        elif change == "deleted":
            from datetime import datetime, timezone
            row.deleted_at = datetime.now(timezone.utc)
        elif change == "pending":
            row.invitation_token = ""
        else:
            row.session_version += 1
        db.commit()
    try:
        reply = case["raw"].get(ENDPOINT, params={"context": "gym"})
        assert reply.status_code in (401, 403)
        assert "sessions" not in reply.json()
    finally:
        if change == "pending":
            # This fixture's migrated module DB is shared across factories;
            # an empty non-NULL token is UNIQUE. Restore only our own actor so
            # the second factory exercises the same ambiguity, not a seed
            # collision before its HTTP assertion.
            with Session(case["admin"]) as db:
                db.get(Usuario, actor).invitation_token = None
                db.commit()


def test_ambiguous_owner_and_methods_fail_without_adopting_profile(routine_http):
    case = routine_http
    login_actor(case, UserRole.OWNER)
    for context in ("personal", "gym"):
        reply = case["raw"].get(ENDPOINT, params={"context": context})
        assert reply.status_code == 403
        assert reply.json()["detail"]["code"] == "routine_context_forbidden"
    assert case["raw"].post(ENDPOINT, json={}).status_code == 405
    assert case["raw"].get(ENDPOINT).status_code == 422
    assert case["raw"].get(ENDPOINT, params={"context": "another-gym"}).status_code == 422


def test_missing_and_malformed_bearer_are_denied(routine_http):
    raw = routine_http["raw"]
    raw.headers.pop("Authorization", None)
    assert raw.get(ENDPOINT, params={"context": "gym"}).status_code == 401
    raw.headers["Authorization"] = "Bearer malformed"
    assert raw.get(ENDPOINT, params={"context": "personal"}).status_code == 401


def test_pages_are_inert_and_keyboard_controls_are_native(routine_http):
    raw = routine_http["raw"]
    raw.headers.pop("Authorization", None)
    for path, scope in (("/rutinas", "gym"), ("/mis-rutinas", "personal")):
        for suffix in ("", "/"):
            reply = raw.get(path + suffix)
            assert reply.status_code == 200
            assert 'data-scope="' + scope + '"' in reply.text
            assert 'data-routine-content hidden' in reply.text
            assert 'data-routine-sessions></div>' in reply.text
            assert 'role="status"' in reply.text
            assert 'type="button"' in reply.text
            assert 'class="routines-days" aria-describedby=' in reply.text
            assert '/static/js/rutinas.js' in reply.text
            assert 'chest-press' not in reply.text


def test_service_uses_only_eligibility_projection(routine_http):
    case = routine_http
    from web.services.routine_catalog import catalog_for_subject
    principal = case["raw"].get("/api/auth/me").json()
    queries = []
    def observe(_connection, _cursor, sql, _parameters, _context, _many):
        queries.append(sql)
    event.listen(case["engine"], "before_cursor_execute", observe)
    try:
        with Session(case["engine"]) as db:
            result = catalog_for_subject(db, principal, "gym")
    finally:
        event.remove(case["engine"], "before_cursor_execute", observe)
    assert result["program"] == get_routine_program()
    assert len(queries) == 1
    assert not any(word in queries[0].lower() for word in ("password", "email", "nombre", "cliente"))


def test_cleanup_failure_does_not_return_catalogue(monkeypatch):
    from web.routes import routines
    from web.database import engine
    from web.services import routine_catalog
    class BrokenSession:
        invalidated = False
        def close(self):
            raise RuntimeError("Synthetic close uncertainty")
        def invalidate(self):
            self.invalidated = True
    session = BrokenSession()
    monkeypatch.setattr(engine, "SessionLocal", lambda: session)
    monkeypatch.setattr(routine_catalog, "catalog_for_subject", lambda *_: {"program": "not-published"})
    with pytest.raises(RuntimeError, match="cleanup unavailable"):
        routines._read({}, "gym")
    assert session.invalidated
