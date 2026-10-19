"""Composition fails closed and synthetic workers cannot inherit object providers."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("factory", ["web.main_web", "api.app"])
def test_factory_rejects_missing_storage_before_database_or_publication(factory, monkeypatch):
    from config.settings import get_settings
    from web.database import engine
    settings = get_settings()
    monkeypatch.setattr(settings, "OBJECT_STORAGE_BACKEND", "")
    monkeypatch.setattr(engine, "get_engine", lambda: pytest.fail("Database touched before invalid storage rejected"))
    with pytest.raises(ValueError, match="not configured"):
        importlib.import_module(factory).create_app()


def test_isolation_discards_inherited_provider_keys_and_uses_worker_private_root():
    names = ("AWS_PROFILE", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_CONFIG_FILE",
        "AWS_ENDPOINT_URL", "AWS_SHARED_CREDENTIALS_FILE", "S3_ENDPOINT", "OBJECT_STORAGE_S3_ACCESS_KEY",
        "OBJECT_STORAGE_S3_SECRET_KEY", "OBJECT_STORAGE_S3_ENDPOINT", "OBJECT_STORAGE_S3_BUCKET")
    env = dict(os.environ)
    env.update({name: "synthetic-inherited-private-marker" for name in names})
    env["OBJECT_STORAGE_BACKEND"] = "s3"
    env["OBJECT_STORAGE_LOCAL_ROOT"] = "C:/unapproved-source"
    env["PYTEST_XDIST_WORKER"] = "gw987"
    code = ("import os,json; from tests.isolation import prepare_environment; root=prepare_environment(); "
        "print(json.dumps({'cleared': [os.environ.get(name) for name in " + repr(names) + "], "
        "'backend':os.environ['OBJECT_STORAGE_BACKEND'], 'root':os.environ['OBJECT_STORAGE_LOCAL_ROOT'], 'worker':str(root)}))")
    completed = subprocess.run([sys.executable, "-X", "utf8", "-c", code], env=env,
        capture_output=True, text=True, encoding="utf-8", check=True)
    result = json.loads(completed.stdout)
    assert result["cleared"] == [""] * len(names)
    assert result["backend"] == "local"
    assert Path(result["root"]) == Path(result["worker"]) / "private_objects"
    assert Path(result["worker"]).name == "gw987"
