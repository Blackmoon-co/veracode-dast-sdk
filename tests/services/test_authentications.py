import logging
from typing import Any

import pytest

from veracode_dast.client import HttpResponse
from veracode_dast.exceptions import (
    AuthenticationValidationError,
    UnknownAuthenticationTypeError,
    VeracodeNotFoundError,
)
from veracode_dast.models.authentication import (
    OAuth2Authentication,
    ParameterAuthentication,
    SystemAuthentication,
)
from veracode_dast.services.authentications import AuthenticationsService


class _StubHttpClient:
    def __init__(self) -> None:
        self._queue: list[HttpResponse] = []
        self._exception: Exception | None = None
        self.calls: list[dict[str, Any]] = []

    def queue(self, response: HttpResponse) -> None:
        self._queue.append(response)

    def raise_next(self, exception: Exception) -> None:
        self._exception = exception

    def _handle(self, verb: str, path: str, **kwargs: Any) -> HttpResponse:
        self.calls.append({"verb": verb, "path": path, **kwargs})
        if self._exception is not None:
            raise self._exception
        return self._queue.pop(0)

    def get(self, path: str, **kwargs: Any) -> HttpResponse:
        return self._handle("GET", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> HttpResponse:
        return self._handle("PUT", path, **kwargs)


def test_get_blank_id_raises_without_http_call() -> None:
    stub = _StubHttpClient()
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AuthenticationValidationError):
        service.get(" ")
    assert stub.calls == []


def test_get_success() -> None:
    stub = _StubHttpClient()
    stub.queue(
        HttpResponse(
            200,
            {
                "system_authentication": {
                    "is_inherited": False,
                    "effective_value": {"username": "admin", "password": "secret123"},
                },
                "application_authentication": None,
                "certificate_authentication": None,
                "script_authentication": None,
                "srm_authentication": None,
                "oauth2_authentication": None,
                "parameter_authentications": None,
            },
            {},
        )
    )
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    config = service.get("ap-1")

    assert config.system_authentication is not None
    assert config.system_authentication.effective_value.username == "admin"


def test_get_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="GET", url="x", status_code=404))
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.get("missing")


def test_update_blank_id_raises_without_http_call() -> None:
    stub = _StubHttpClient()
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AuthenticationValidationError):
        service.update("", {"authentication": {"type": "basic", "username": "a", "password": "b"}})
    assert stub.calls == []


def test_update_basic_readme_example() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, {"username": "admin", "password": "secret123"}, {}))
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    config = {"authentication": {"type": "basic", "username": "admin", "password": "secret123"}}
    result = service.update("ap-1", config)

    assert stub.calls[0]["path"] == "/analysis_profiles/ap-1/system_authentication"
    assert stub.calls[0]["params"] == {"method": "PATCH"}
    assert stub.calls[0]["json"] == {"username": "admin", "password": "secret123"}
    assert isinstance(result, SystemAuthentication)


def test_update_oauth2_corrected_readme_example() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, {"grant_type": "CLIENT_CREDENTIALS"}, {}))
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    config = {
        "authentication": {
            "type": "oauth2",
            "grant_type": "CLIENT_CREDENTIALS",
            "access_token_url": "https://example.com/oauth/token",
            "client_id": "client-id",
            "client_secret": "client-secret",
        }
    }
    result = service.update("ap-1", config)

    assert stub.calls[0]["path"] == "/analysis_profiles/ap-1/oauth2_authentication"
    assert stub.calls[0]["params"] == {"method": "PATCH"}
    assert stub.calls[0]["json"] == {
        "grant_type": "CLIENT_CREDENTIALS",
        "access_token_url": "https://example.com/oauth/token",
        "client_id": "client-id",
        "client_secret": "client-secret",
    }
    assert isinstance(result, OAuth2Authentication)


def test_update_parameter_has_no_method_query_param_and_bare_array_body() -> None:
    stub = _StubHttpClient()
    stub.queue(
        HttpResponse(
            200,
            [
                {
                    "title": "API Key",
                    "type": "HTTP_HEADER",
                    "key": "X-API-Key",
                    "value": "secret-token",
                }
            ],
            {},
        )
    )
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    config = {
        "authentication": {
            "type": "parameter",
            "parameters": [
                {
                    "title": "API Key",
                    "type": "HTTP_HEADER",
                    "key": "X-API-Key",
                    "value": "secret-token",
                }
            ],
        }
    }
    result = service.update("ap-1", config)

    assert stub.calls[0]["path"] == "/analysis_profiles/ap-1/parameter_authentications"
    assert stub.calls[0]["params"] is None
    assert stub.calls[0]["json"] == [
        {"title": "API Key", "type": "HTTP_HEADER", "key": "X-API-Key", "value": "secret-token"}
    ]
    assert isinstance(result, list)
    assert isinstance(result[0], ParameterAuthentication)


def test_update_parameter_empty_list_is_accepted() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, [], {}))
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    config = {"authentication": {"type": "parameter", "parameters": []}}
    result = service.update("ap-1", config)

    assert stub.calls[0]["json"] == []
    assert result == []


@pytest.mark.parametrize(
    ("config", "rule"),
    [
        ({}, "authentication_key_required"),
        ({"authentication": {}}, "type_required"),
        ({"authentication": {"type": "basic", "password": "x"}}, "basic_username_required"),
        ({"authentication": {"type": "basic", "username": "a"}}, "basic_password_required"),
        (
            {"authentication": {"type": "application", "password": "x", "login_url": "y"}},
            "application_username_required",
        ),
        (
            {"authentication": {"type": "application", "username": "a", "login_url": "y"}},
            "application_password_required",
        ),
        (
            {"authentication": {"type": "application", "username": "a", "password": "b"}},
            "application_login_url_required",
        ),
        ({"authentication": {"type": "certificate"}}, "certificate_base64_pkcs12_required"),
        ({"authentication": {"type": "script"}}, "script_requires_login_or_logout"),
        (
            {"authentication": {"type": "script", "login_script": {"script_type": "NOT_REAL"}}},
            "script_type_invalid",
        ),
        ({"authentication": {"type": "srm"}}, "srm_script_body_required"),
        (
            {"authentication": {"type": "srm", "script_body": "x", "script_type": "NOT_REAL"}},
            "script_type_invalid",
        ),
        ({"authentication": {"type": "oauth2"}}, "oauth2_grant_type_required"),
        (
            {"authentication": {"type": "oauth2", "grant_type": "NOT_REAL"}},
            "oauth2_grant_type_invalid",
        ),
        ({"authentication": {"type": "parameter"}}, "parameter_parameters_required"),
        (
            {"authentication": {"type": "parameter", "parameters": [{"title": "x"}]}},
            "parameter_entry_invalid",
        ),
    ],
)
def test_update_validation_failures_raise_before_http_call(
    config: dict[str, Any], rule: str
) -> None:
    stub = _StubHttpClient()
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AuthenticationValidationError) as exc_info:
        service.update("ap-1", config)
    assert exc_info.value.rule == rule
    assert stub.calls == []


def test_update_unknown_type_suggests_closest() -> None:
    stub = _StubHttpClient()
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    config = {"authentication": {"type": "aouth2", "grant_type": "CLIENT_CREDENTIALS"}}
    with pytest.raises(UnknownAuthenticationTypeError) as exc_info:
        service.update("ap-1", config)
    assert "Unknown authentication type 'aouth2'." in str(exc_info.value)
    assert "Did you mean 'oauth2'?" in str(exc_info.value)
    assert stub.calls == []


def test_update_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="PUT", url="x", status_code=404))
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.update(
            "missing", {"authentication": {"type": "basic", "username": "a", "password": "b"}}
        )


def test_no_log_record_contains_sensitive_values(caplog: pytest.LogCaptureFixture) -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, {"username": "admin", "password": "top-secret-value"}, {}))
    service = AuthenticationsService(stub)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        service.update(
            "ap-1",
            {
                "authentication": {
                    "type": "basic",
                    "username": "admin",
                    "password": "top-secret-value",
                }
            },
        )

    for record in caplog.records:
        assert "top-secret-value" not in record.getMessage()
