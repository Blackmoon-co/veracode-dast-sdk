import logging

import pytest
from veracode_api_signing.plugin_requests import RequestsAuthPluginVeracodeHMAC

from veracode_dast.auth import create_hmac_auth, get_veracode_auth
from veracode_dast.config import VeracodeCredentials
from veracode_dast.exceptions import MissingCredentialsError


def test_create_hmac_auth_returns_populated_provider() -> None:
    credentials = VeracodeCredentials(api_key_id="id-123", api_key_secret="secret-456")

    auth = create_hmac_auth(credentials)

    assert isinstance(auth, RequestsAuthPluginVeracodeHMAC)
    assert auth.api_key_id == "id-123"
    assert auth.api_key_secret == "secret-456"


def test_get_veracode_auth_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERACODE_API_KEY_ID", "id-123")
    monkeypatch.setenv("VERACODE_API_KEY_SECRET", "secret-456")

    auth = get_veracode_auth()

    assert isinstance(auth, RequestsAuthPluginVeracodeHMAC)
    assert auth.api_key_id == "id-123"
    assert auth.api_key_secret == "secret-456"


def test_get_veracode_auth_propagates_missing_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VERACODE_API_KEY_ID", raising=False)
    monkeypatch.delenv("VERACODE_API_KEY_SECRET", raising=False)

    with pytest.raises(MissingCredentialsError):
        get_veracode_auth()


def test_get_veracode_auth_does_not_log_values(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("VERACODE_API_KEY_ID", "super-secret-id")
    monkeypatch.setenv("VERACODE_API_KEY_SECRET", "super-secret-key")

    with caplog.at_level(logging.DEBUG):
        get_veracode_auth()

    for record in caplog.records:
        assert "super-secret-id" not in record.getMessage()
        assert "super-secret-key" not in record.getMessage()
