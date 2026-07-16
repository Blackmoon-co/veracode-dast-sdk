import logging

import pytest

from veracode_dast.config import VeracodeCredentials, load_credentials_from_env
from veracode_dast.exceptions import MissingCredentialsError


def test_load_credentials_from_env_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERACODE_API_KEY_ID", "id-123")
    monkeypatch.setenv("VERACODE_API_KEY_SECRET", "secret-456")

    creds = load_credentials_from_env()

    assert creds == VeracodeCredentials(api_key_id="id-123", api_key_secret="secret-456")


def test_load_credentials_from_env_missing_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VERACODE_API_KEY_ID", raising=False)
    monkeypatch.setenv("VERACODE_API_KEY_SECRET", "secret-456")

    with pytest.raises(MissingCredentialsError) as exc_info:
        load_credentials_from_env()

    assert exc_info.value.missing_variables == ["VERACODE_API_KEY_ID"]


def test_load_credentials_from_env_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERACODE_API_KEY_ID", "id-123")
    monkeypatch.delenv("VERACODE_API_KEY_SECRET", raising=False)

    with pytest.raises(MissingCredentialsError) as exc_info:
        load_credentials_from_env()

    assert exc_info.value.missing_variables == ["VERACODE_API_KEY_SECRET"]


def test_load_credentials_from_env_missing_both(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VERACODE_API_KEY_ID", raising=False)
    monkeypatch.delenv("VERACODE_API_KEY_SECRET", raising=False)

    with pytest.raises(MissingCredentialsError) as exc_info:
        load_credentials_from_env()

    assert exc_info.value.missing_variables == ["VERACODE_API_KEY_ID", "VERACODE_API_KEY_SECRET"]


def test_load_credentials_from_env_empty_string_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERACODE_API_KEY_ID", "")
    monkeypatch.setenv("VERACODE_API_KEY_SECRET", "secret-456")

    with pytest.raises(MissingCredentialsError) as exc_info:
        load_credentials_from_env()

    assert exc_info.value.missing_variables == ["VERACODE_API_KEY_ID"]


def test_load_credentials_from_env_does_not_log_values(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("VERACODE_API_KEY_ID", "super-secret-id")
    monkeypatch.setenv("VERACODE_API_KEY_SECRET", "super-secret-key")

    with caplog.at_level(logging.DEBUG):
        load_credentials_from_env()

    for record in caplog.records:
        assert "super-secret-id" not in record.getMessage()
        assert "super-secret-key" not in record.getMessage()
