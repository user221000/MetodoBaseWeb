"""Independent SDK configuration checks; run with --noconftest and no network."""
from dataclasses import replace
from unittest.mock import patch

import pytest

from web.storage.configuration import ObjectStoreConfiguration, build_object_store


def configuration(**changes):
    return replace(ObjectStoreConfiguration(backend="s3", bucket="synthetic-private-review",
        region="us-east-1", access_key="synthetic-explicit-access", secret_key="synthetic-explicit-secret"), **changes)


@pytest.mark.parametrize("endpoint", ["https://user:synthetic-private-marker@example.invalid",
    "https://example.invalid/?token=synthetic-private-marker", "https://example.invalid/#synthetic-private-marker"])
def test_invalid_endpoint_secrets_are_hidden_before_validation(endpoint):
    value = configuration(endpoint=endpoint)
    assert "synthetic-private-marker" not in repr(value)
    with patch("boto3.session.Session") as sdk:
        with pytest.raises(ValueError) as error:
            build_object_store(value)
    sdk.assert_not_called()
    assert "synthetic-private-marker" not in str(error.value)


def test_explicit_credentials_and_absent_session_token_ignore_environment_chain(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "synthetic-inherited-access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "synthetic-inherited-secret")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "synthetic-inherited-session")
    monkeypatch.setenv("AWS_CONTAINER_CREDENTIALS_FULL_URI", "http://127.0.0.1:9/not-a-credential-provider")
    store = build_object_store(configuration(endpoint="https://objects.example.invalid"))
    try:
        credentials = store.client._request_signer._credentials.get_frozen_credentials()
        assert credentials.access_key == "synthetic-explicit-access"
        assert credentials.secret_key == "synthetic-explicit-secret"
        assert credentials.token is None
        assert store.client.meta.endpoint_url == "https://objects.example.invalid"
    finally:
        store.client.close()


def test_shared_profile_cannot_override_endpoint_credentials_or_transport_budget(monkeypatch, tmp_path):
    config = tmp_path / "synthetic-config"
    credentials = tmp_path / "synthetic-credentials"
    config.write_text("[profile review]\nregion = invalid-region\nendpoint_url = http://untrusted.example.invalid\ncredential_process = never-run-this-process\nmax_attempts = 99\n", encoding="utf-8")
    credentials.write_text("[review]\naws_access_key_id = synthetic-file-access\naws_secret_access_key = synthetic-file-secret\naws_session_token = synthetic-file-token\n", encoding="utf-8")
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(credentials))
    monkeypatch.setenv("AWS_PROFILE", "review")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://untrusted-environment.example.invalid")
    with patch("subprocess.Popen", side_effect=AssertionError("Credential process must never run")):
        store = build_object_store(configuration())
    try:
        assert store.client.meta.endpoint_url in {"https://s3.amazonaws.com", "https://s3.us-east-1.amazonaws.com"}
        assert store.client.meta.region_name == "us-east-1"
        assert store.client.meta.config.connect_timeout == 3
        assert store.client.meta.config.read_timeout == 10
        assert store.client.meta.config.retries["total_max_attempts"] == 2
        assert store.client._request_signer._credentials.get_frozen_credentials().access_key == "synthetic-explicit-access"
    finally:
        store.client.close()
