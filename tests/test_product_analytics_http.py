"""Actual API/SaaS factories, genuine password/MFA session and finite privacy boundary."""
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from tests import product_analytics_fixtures as f
from tests.followup34_http import PASSWORD
from web.database.models import Cliente, UserRole, Usuario
from web.services import product_analytics

account37_engine = f.account37_engine
followup_db = f.followup_db
analytics_http = f.analytics_http
PATH = "/api/analytics/producto"


def actor(case, role=UserRole.VIEWER, *, team=False):
    """Only membership is seeded; acceptance uses the real password endpoint."""
    from web.auth import hash_password
    identity, email = str(uuid.uuid4()), uuid.uuid4().hex + "@example.invalid"
    with Session(case["admin"]) as db:
        db.add(Usuario(id=identity, email=email, password_hash=hash_password(PASSWORD),
            nombre="Synthetic analytics reader", tipo="usuario", role=role,
            team_gym_id=case["user"] if team else None))
        db.commit()
    login = case["raw"].post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, "Persisted analytics actor password authentication"
    case["raw"].headers["Authorization"] = "Bearer " + login.json()["token"]
    me = case["raw"].get("/api/auth/me")
    assert me.status_code == 200 and me.json()["id"] == identity
    return identity


def private(response):
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    csp = response.headers["content-security-policy"]
    assert "default-src 'none'" in csp and "https:" not in csp and "unsafe" not in csp


def test_authentic_owner_and_individual_reports_without_writes_or_private_projection(analytics_http, monkeypatch):
    from web.database import repository
    def forbidden_statistics(*args, **kwargs):
        raise AssertionError("Product facts must not call health statistics")
    monkeypatch.setattr(repository, "obtener_estadisticas", forbidden_statistics)
    case = analytics_http
    queries = []
    def observe(_c, _cursor, sql, _params, _ctx, _many):
        queries.append(sql.lower())
    event.listen(case["engine"], "before_cursor_execute", observe)
    try:
        gym = case["raw"].get(PATH, params={"context": "gym"})
    finally:
        event.remove(case["engine"], "before_cursor_execute", observe)
    assert gym.status_code == 200
    private(gym)
    body = gym.json()
    assert body["scope"] == "gym" and body["unit"] == "workspace"
    assert body["snapshot"]["source_revision"] is None
    assert body["snapshot"]["source_revision_status"] == "unavailable"
    assert body["preparation_as_of"] == {"client_registered": True, "plan_saved": False}
    assert case["user"] not in gym.text and case["profile"] not in gym.text
    assert not any(q.lstrip().split(None, 1)[0] in {"insert", "update", "delete", "create", "alter"} for q in queries)
    identity = actor(case)
    result = case["raw"].get(PATH, params={"context": "personal"})
    assert result.status_code == 200 and result.json()["unit"] == "personal_account"
    assert result.json()["preparation_as_of"] == {"profile_present": False, "plan_present": False}
    assert all("link_acceptances" not in week for week in result.json()["weekly"])
    assert case["raw"].get(PATH, params={"context": "gym"}).status_code == 403
    with Session(case["admin"]) as db:
        assert db.query(Cliente).filter_by(gym_id=identity).count() == 0


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.NUTRIOLOGO, UserRole.VIEWER])
def test_real_team_roles_keep_workspace_rights_distinct_from_own_activity(analytics_http, role):
    case = analytics_http
    actor(case, role, team=True)
    own = case["raw"].get(PATH, params={"context": "personal"})
    assert own.status_code == 200 and own.json()["scope"] == "personal"
    gym = case["raw"].get(PATH, params={"context": "gym"})
    assert gym.status_code == (200 if role == UserRole.ADMIN else 403)
    private(gym)


def test_invalid_queries_never_open_r30_reader_session_or_statistics(analytics_http, monkeypatch):
    from web.database import repository
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("An invalid query entered the analytics reader")
    monkeypatch.setattr(product_analytics, "read_report", forbidden)
    monkeypatch.setattr(repository, "obtener_estadisticas", forbidden)
    raw = analytics_http["raw"]
    for query in ("", "context=personal&context=gym", "context=unknown", "context=personal&gym_id=other",
                  "context=personal&from=0&through=2026-10-21", "context=personal&from=2026-10-19",
                  "context=personal&through=2026-10-21", "context=personal&profile_id=x",
                  "context=personal&from=2026-10-19&through=2026-10-21&through=2026-10-21"):
        response = raw.get(PATH + "?" + query)
        assert response.status_code == 422 and response.json()["detail"]["code"] == "analytics_invalid_input"
        private(response)
    assert calls == []


def test_exact_privacy_paths_all_methods_and_neighbours_are_unchanged(analytics_http, monkeypatch):
    raw = analytics_http["raw"]
    raw.headers.pop("Authorization", None)
    for path in (PATH, PATH + "/"):
        response = raw.head(path)
        assert response.status_code == 405
        private(response)
        # The existing SaaS CSRF admission precedes routing on unsafe methods.
        # It stays enabled; HEAD proves the router's method405 independently.
        unsafe = raw.post(path)
        assert unsafe.status_code == (403 if analytics_http["factory_name"] == "web.main_web" else 405)
        private(unsafe)
        missing = raw.get(path, params={"context": "personal"})
        assert missing.status_code == 401 and missing.headers["www-authenticate"] == "Bearer"
        private(missing)
    for path in (PATH + "-neighbour", PATH + "/neighbour", "/login"):
        neighbour = raw.get(path)
        assert neighbour.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "https://accounts.google.com" in neighbour.headers["content-security-policy"]
    # Match the class that each real factory actually installs across module reloads.
    if analytics_http["factory_name"] == "api.app":
        from web.middleware import RateLimiterMiddleware
    elif analytics_http["factory_name"] == "web.main_web":
        from web.middleware.rate_limiter import RateLimiterMiddleware
    else:
        raise AssertionError("Unknown analytics factory installation binding")
    from web.middleware.rate_limiter import RateLimiterStore
    layer = raw.app.middleware_stack
    while layer is not None and not isinstance(layer, RateLimiterMiddleware):
        layer = getattr(layer, "app", None)
    assert layer is not None
    with monkeypatch.context() as controlled_bucket:
        # The ordinary isolated launcher disables this global budget. Enable
        # only this real middleware instance for the intentional429 canary.
        controlled_bucket.setattr(layer, "enabled", True)
        controlled_bucket.setattr(layer, "store", RateLimiterStore(1, 1))
        assert raw.get(PATH, params={"context": "invalid"}).status_code == 422
        limited = raw.get(PATH, params={"context": "personal"})
    assert limited.status_code == 429
    private(limited)


def test_read_failure_is_opaque_and_cleanup_precedes_response(analytics_http, monkeypatch, caplog):
    from web.database import engine as database
    raw = analytics_http["raw"]
    closed = []
    original = database._SessionLocal
    class FailingSession(Session):
        def close(self):
            closed.append(True)
            super().close()
            raise RuntimeError("SYNTHETIC_PRIVATE_CLOSE_DETAIL")
    def owned():
        return FailingSession(analytics_http["engine"], autoflush=False)
    # Authentication keeps its normal Session; only the R30 factory is supplied.
    real_read = product_analytics.read_report
    monkeypatch.setattr(product_analytics, "read_report", lambda *a, **kw: real_read(*a, factory=owned, **kw))
    response = raw.get(PATH, params={"context": "gym"})
    assert response.status_code == 503 and response.json()["detail"]["code"] == "analytics_unavailable"
    assert closed and database._SessionLocal is original
    assert "SYNTHETIC_PRIVATE_CLOSE_DETAIL" not in response.text + caplog.text
    private(response)


@pytest.mark.parametrize("fault", ["internal_http500", "outside"])
def test_internal_and_outer_failures_use_opaque_factory_boundary(analytics_http, monkeypatch, fault):
    from fastapi import HTTPException

    from web.routes.product_analytics import router
    raw = analytics_http["raw"]
    if fault == "internal_http500":
        def failed(*args, **kwargs):
            raise HTTPException(500, "SYNTHETIC_INTERNAL_PRIVATE_DETAIL")
        monkeypatch.setattr(product_analytics, "_preparation", failed)
    else:
        route = next(row for row in raw.app.routes if getattr(row, "original_router", None) is router)
        async def outer(scope, receive, send):
            raise RuntimeError("SYNTHETIC_OUTER_PRIVATE_DETAIL")
        monkeypatch.setattr(route, "handle", outer)
    result = raw.get(PATH, params={"context": "gym"})
    assert result.status_code == (503 if fault == "internal_http500" else 500)
    assert "SYNTHETIC_" not in result.text
    private(result)
