"""BrowserAuthRoute admission without SQL, provider or authentication substitutes.

The real route adapter and canonical configuration execute on synthetic HTTP
requests. The downstream handler only records whether admission reached it;
these cases do not claim real login, rotation or browser-generated headers.
"""
import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from web.browser_session import BrowserAuthRoute
from web.settings import get_settings

ORIGIN = "https://origin-policy.example.invalid"
COOKIE = "synthetic-existing-cookie-not-an-authentication-proof"
PATHS = ("/api/auth/refresh", "/api/auth/browser/migrate",
         "/api/account/security/password")


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    """This module deliberately opens no database."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    """The admission harness has no persistent state to clear."""
    yield


@pytest.fixture
def admission(monkeypatch):
    monkeypatch.setattr(get_settings(), "BASE_URL", ORIGIN)
    events = []

    def dependency():
        events.append("dependency")

    async def handler():
        events.append("handler")
        return JSONResponse({"downstream_reached": True})

    router = APIRouter(route_class=BrowserAuthRoute)
    for path in (*PATHS, "/api/auth/refresh/", "/api/auth/refresh-neighbor"):
        router.add_api_route(path, handler, methods=["POST", "GET"],
                             dependencies=[Depends(dependency)])
    app = FastAPI()
    app.include_router(router)
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as client:
        client.cookies.set("__Host-mb_refresh", COOKIE,
                           domain="origin-policy.example.invalid", path="/")
        yield client, events


def headers(origin=ORIGIN):
    return [("X-MetodoBase-Browser", "1"), ("Content-Type", "application/json"),
            ("Origin", origin)]


def unchanged_cookie(client, response):
    assert client.cookies.get("__Host-mb_refresh") == COOKIE
    assert response.headers.get_list("set-cookie") == []


def rejected(admission, response, status=403):
    client, events = admission
    assert response.status_code == status
    assert response.json()["detail"]["code"] == (
        "browser_input_invalid" if status == 415 else "browser_origin_invalid")
    assert events == [], "Admission must precede dependencies and the handler"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    unchanged_cookie(client, response)


@pytest.mark.parametrize("fetch_metadata", [False, True])
@pytest.mark.parametrize("content_type", ["application/json", "application/json; charset=UTF-8"])
def test_canonical_origin_reaches_handler_without_requiring_fetch_metadata(
    admission, fetch_metadata, content_type,
):
    client, events = admission
    request_headers = [(key, content_type if key == "Content-Type" else value)
                       for key, value in headers()]
    if fetch_metadata:
        request_headers.append(("Sec-Fetch-Site", "same-origin"))
    response = client.post(PATHS[0], headers=request_headers, content="{}")
    assert response.status_code == 200 and response.json() == {"downstream_reached": True}
    assert events == ["dependency", "handler"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    unchanged_cookie(client, response)


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("variant", ["null", "missing", "foreign", "port", "default_port",
                                    "scheme", "duplicate", "mixed_duplicate", "trailing_slash"])
def test_null_missing_ambiguous_or_noncanonical_origin_never_reaches_authority(
    admission, path, variant,
):
    client, _ = admission
    values = {
        "null": "null", "foreign": "https://outside.example.invalid",
        "port": ORIGIN + ":8443", "default_port": ORIGIN + ":443",
        "scheme": ORIGIN.replace("https:", "http:"), "trailing_slash": ORIGIN + "/",
    }
    request_headers = headers(values.get(variant, ORIGIN))
    if variant == "missing":
        request_headers = [(key, value) for key, value in request_headers if key != "Origin"]
    elif variant in {"duplicate", "mixed_duplicate"}:
        request_headers.append(("Origin", ORIGIN if variant == "duplicate"
                                else "https://outside.example.invalid"))
    # Same-origin Fetch Metadata cannot authorize an opaque or malformed Origin.
    request_headers.append(("Sec-Fetch-Site", "same-origin"))
    rejected(admission, client.post(path, headers=request_headers, content="{}"))


@pytest.mark.parametrize("variant", ["marker", "duplicate_marker", "content_type",
                                    "duplicate_content_type", "query", "method", "slash", "neighbor"])
def test_other_browser_transport_boundaries_still_precede_cookie_or_handler_work(admission, variant):
    client, _ = admission
    path, method, request_headers, status = PATHS[0], "POST", headers(), 403
    if variant == "marker":
        request_headers = [(key, "0" if key == "X-MetodoBase-Browser" else value)
                           for key, value in request_headers]
    elif variant == "duplicate_marker":
        request_headers.append(("X-MetodoBase-Browser", "1"))
    elif variant == "content_type":
        request_headers = [(key, "text/plain" if key == "Content-Type" else value)
                           for key, value in request_headers]
        status = 415
    elif variant == "duplicate_content_type":
        request_headers.append(("Content-Type", "application/json"))
        status = 415
    elif variant == "query":
        path += "?unexpected=1"
    elif variant == "method":
        method = "GET"
    elif variant == "slash":
        path += "/"
    else:
        path += "-neighbor"
    rejected(admission, client.request(method, path, headers=request_headers, content="{}"), status)


def test_legacy_caller_without_browser_marker_keeps_its_existing_route_contract(admission):
    client, events = admission
    response = client.post(PATHS[0], json={})
    assert response.status_code == 200 and events == ["dependency", "handler"]
    unchanged_cookie(client, response)
