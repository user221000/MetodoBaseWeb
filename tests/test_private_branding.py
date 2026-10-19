"""Decoded, private logos and replacement failures through real HTTP factories."""
import importlib
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin
import pytest
from sqlalchemy.orm import Session


def png():
    output = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("private-synthetic-note", "synthetic-private-metadata")
    Image.new("RGB", (4, 4), "red").save(output, format="PNG", pnginfo=metadata)
    return output.getvalue()


@pytest.fixture(params=["web.main_web", "api.app"])
def branding(request, test_gym_user):
    with TestClient(importlib.import_module(request.param).create_app(), raise_server_exceptions=False) as client:
        yield client, test_gym_user


def upload(case, content=None, filename="logo.png"):
    return case[0].post("/api/gym/logo", headers=case[1]["auth_headers"],
        files={"file": (filename, png() if content is None else content, "application/octet-stream")})


def test_private_logo_survives_adapter_reconstruction_and_strips_source_metadata(branding):
    from web.database.engine import get_engine
    from web.database.models import GymProfile, StoredObject
    from web.storage.runtime import _configured_store
    response = upload(branding)
    assert response.status_code == 200, response.text
    assert response.json() == {"success": True, "logo_url": "/api/gym/logo", "has_private_logo": True}
    _configured_store.cache_clear()
    downloaded = branding[0].get("/api/gym/logo", headers=branding[1]["auth_headers"])
    assert downloaded.status_code == 200 and downloaded.headers["content-type"] == "image/png"
    assert downloaded.headers["cache-control"] == "no-store"
    assert downloaded.headers["referrer-policy"] == "no-referrer"
    with Image.open(BytesIO(downloaded.content)) as image:
        assert image.size == (4, 4) and not image.info
    assert b"synthetic-private-metadata" not in downloaded.content
    assert branding[0].get("/api/gym/logo").status_code == 401
    with Session(get_engine()) as db:
        obj = db.query(StoredObject).one()
        profile = db.query(GymProfile).one()
        assert obj.kind == "gym_logo" and obj.status == "ready"
        assert profile.logo_object_id == obj.id and profile.logo_url == ""


@pytest.mark.parametrize("content,filename", [(b"\x89PNGnot-a-valid-image", "bad.png"),
    (b"", "empty.png"), (b"RIFFnot-webp", "bad.webp"), (b"<svg/>", "logo.svg"),
    (b"x" * (2 * 1024 * 1024 + 1), "large.png")], ids=["truncated-png", "empty", "invalid-webp", "svg", "oversize"])
def test_invalid_images_do_not_create_intents(branding, content, filename):
    from web.database.engine import get_engine
    from web.database.models import StoredObject
    assert upload(branding, content, filename).status_code == 400
    with Session(get_engine()) as db:
        assert db.query(StoredObject).count() == 0


def test_uncertain_replacement_keeps_old_reference_and_new_pending_intent(branding, monkeypatch):
    from web.database.engine import get_engine
    from web.database.models import GymProfile, StoredObject
    from web.services import private_objects
    from web.storage.objects import ObjectUnavailable
    assert upload(branding).status_code == 200
    old = branding[0].get("/api/gym/logo", headers=branding[1]["auth_headers"]).content
    store = private_objects.get_object_store()
    original = store.put
    def ambiguous(descriptor, data, *, owner_id):
        original(descriptor, data, owner_id=owner_id)
        raise ObjectUnavailable("Synthetic private provider error")
    monkeypatch.setattr(store, "put", ambiguous)
    assert upload(branding).status_code == 503
    assert branding[0].get("/api/gym/logo", headers=branding[1]["auth_headers"]).content == old
    with Session(get_engine()) as db:
        objects = db.query(StoredObject).all()
        assert sorted(row.status for row in objects) == ["pending", "ready"]
        assert db.query(GymProfile).one().logo_object_id == next(row.id for row in objects if row.status == "ready")


def test_pixel_limit_is_checked_before_decoding_large_surface(monkeypatch):
    from web.services import gym_logos
    monkeypatch.setattr(gym_logos, "MAX_LOGO_PIXELS", 3)
    with pytest.raises(ValueError):
        gym_logos.normalize_logo(png(), ".png")
