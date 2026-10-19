"""Explicit SDK configuration cannot inherit an endpoint or credential chain.

Run explicitly in the SDK target with --noconftest. No database or remote service
is used, and no generated adapter writes a bucket during construction.
"""
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from web.storage.configuration import ObjectStoreConfiguration, build_object_store
from web.storage.objects import ObjectUnavailable


def configured(**changes):
    return replace(ObjectStoreConfiguration(backend="s3", bucket="synthetic-private-tests",
        region="us-east-1", access_key="synthetic-access-only", secret_key="synthetic-secret-only",
        endpoint="https://objects.example.invalid"), **changes)


@pytest.mark.parametrize("changes", [
    {"backend": "unknown"}, {"local_root": Path(".")}, {"bucket": ""}, {"bucket": "bad/path"},
    {"region": ""}, {"access_key": ""}, {"secret_key": ""},
    {"endpoint": "https://user:password@example.invalid"},
    {"endpoint": "https://example.invalid/?token=opaque"},
    {"endpoint": "https://example.invalid/bucket"},
    {"endpoint": "http://example.invalid"},
    {"endpoint": "http://127.0.0.1:9000", "production": True},
    {"endpoint": "https://example.invalid:invalid"},
])
def test_invalid_configuration_never_constructs_sdk_or_fallback(changes, tmp_path):
    with patch("boto3.session.Session") as session, patch("web.storage.configuration.LocalObjectStore") as local:
        with pytest.raises(ValueError):
            build_object_store(configured(**changes))
    session.assert_not_called()
    local.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_explicit_session_and_config_override_environment(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://untrusted.example.invalid")
    monkeypatch.setenv("AWS_ENDPOINT_URL_S3", "http://untrusted.example.invalid")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "must-not-be-used")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-be-used")
    monkeypatch.setenv("AWS_MAX_ATTEMPTS", "19")
    store = build_object_store(configured())
    assert store.client.meta.endpoint_url == "https://objects.example.invalid"
    credentials = store.client._request_signer._credentials.get_frozen_credentials()
    assert credentials.access_key == "synthetic-access-only"
    assert credentials.secret_key == "synthetic-secret-only"
    assert credentials.token is None
    assert store.client.meta.config.connect_timeout == 3
    assert store.client.meta.config.read_timeout == 10
    assert store.client.meta.config.retries["total_max_attempts"] == 2
    store.client.close()


def test_aws_endpoint_resolver_ignores_environment_override(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://untrusted.example.invalid")
    monkeypatch.setenv("AWS_ENDPOINT_URL_S3", "http://untrusted.example.invalid")
    store = build_object_store(configured(endpoint=None))
    assert store.client.meta.endpoint_url in {"https://s3.amazonaws.com", "https://s3.us-east-1.amazonaws.com"}
    store.client.close()


@pytest.mark.parametrize("endpoint", ["http://127.0.0.1:9000", "http://[::1]:9000", "http://localhost:9000"])
def test_development_loopback_provider_can_be_configured(endpoint):
    store = build_object_store(configured(endpoint=endpoint))
    assert store.client.meta.endpoint_url == endpoint
    store.client.close()


def test_client_failure_is_sanitized_without_local_fallback(tmp_path):
    with patch("boto3.session.Session", side_effect=RuntimeError("sensitive-configuration")), patch("web.storage.configuration.LocalObjectStore") as local:
        with pytest.raises(ObjectUnavailable) as failed:
            build_object_store(configured())
    assert "sensitive-configuration" not in str(failed.value)
    local.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_credentials_are_absent_from_configuration_representation():
    result = repr(configured(session_token="synthetic-session-only",
        endpoint="https://synthetic-user:synthetic-password@example.invalid/?token=synthetic-query"))
    assert "synthetic-access-only" not in result
    assert "synthetic-secret-only" not in result
    assert "synthetic-session-only" not in result
    assert "synthetic-password" not in result
    assert "synthetic-query" not in result


def test_explicit_local_store_reopens_existing_bytes_after_reconstruction(tmp_path):
    from web.storage.objects import describe

    configuration = ObjectStoreConfiguration(backend="local", local_root=tmp_path / "private")
    data = b"%PDF-synthetic-reconstruction"
    descriptor = describe("synthetic-owner", "plan_pdf", data, "application/pdf")
    build_object_store(configuration).put(descriptor, data, owner_id="synthetic-owner")
    assert build_object_store(configuration).read(descriptor, owner_id="synthetic-owner") == data


@pytest.mark.parametrize("configuration", [
    ObjectStoreConfiguration(backend="local"),
    ObjectStoreConfiguration(backend="local", local_root=Path("relative")),
    ObjectStoreConfiguration(backend="local", local_root=Path.cwd(), bucket="unexpected"),
])
def test_local_configuration_cannot_silently_select_a_source_tree(configuration):
    with patch("web.storage.configuration.LocalObjectStore") as local:
        with pytest.raises(ValueError):
            build_object_store(configuration)
    local.assert_not_called()


@pytest.mark.parametrize("relative", ["static", "web/static", "web/static/uploads/objects"])
def test_private_store_rejects_roots_served_publicly(tmp_path, monkeypatch, relative):
    monkeypatch.setattr("web.storage.configuration._APPLICATION_ROOT", tmp_path)
    public = tmp_path / relative
    with patch("web.storage.configuration.LocalObjectStore") as local:
        with pytest.raises(ValueError):
            build_object_store(ObjectStoreConfiguration(backend="local", local_root=public))
    local.assert_not_called()
    assert not public.exists()
