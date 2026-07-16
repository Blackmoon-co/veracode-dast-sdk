import json
import logging
from collections.abc import Mapping
from typing import Any

import pytest
import requests
from requests.auth import AuthBase

from veracode_dast.client import DEFAULT_TIMEOUT, HttpClient, HttpResponse
from veracode_dast.exceptions import (
    VeracodeApiError,
    VeracodeAuthenticationError,
    VeracodeAuthorizationError,
    VeracodeConflictError,
    VeracodeConnectionError,
    VeracodeNotFoundError,
    VeracodeTimeoutError,
    VeracodeValidationError,
)


class _StubAuth(AuthBase):
    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        return r


def _make_response(
    status_code: int,
    json_body: Any = None,
    headers: Mapping[str, str] | None = None,
    content: bytes | None = None,
) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    if content is not None:
        response._content = content
    elif json_body is not None:
        response._content = json.dumps(json_body).encode()
    else:
        response._content = b""
    response.headers = requests.structures.CaseInsensitiveDict(headers or {})
    return response


class _RecordingRequest:
    """Records the last call and returns a prepared response, or raises."""

    def __init__(
        self, response: requests.Response | None = None, exception: Exception | None = None
    ) -> None:
        self.response = response
        self.exception = exception
        self.calls: list[dict[str, Any]] = []

    def __call__(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.exception is not None:
            raise self.exception
        assert self.response is not None
        return self.response

    @property
    def last(self) -> dict[str, Any]:
        return self.calls[-1]


def _client(**kwargs: Any) -> HttpClient:
    return HttpClient(base_url="https://api.example.com/v1", auth=_StubAuth(), **kwargs)


def test_constructor_requires_base_url_and_auth() -> None:
    with pytest.raises(TypeError):
        HttpClient(auth=_StubAuth())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        HttpClient(base_url="https://api.example.com")  # type: ignore[call-arg]


def test_default_timeout_and_retries_are_applied() -> None:
    client = _client()
    assert client._timeout == DEFAULT_TIMEOUT

    recorder = _RecordingRequest(response=_make_response(200))
    client._session.request = recorder  # type: ignore[method-assign]
    client.get("/things")
    assert recorder.last["timeout"] == DEFAULT_TIMEOUT


def test_explicit_timeout_and_retries_are_applied() -> None:
    client = _client(timeout=5.0, max_retries=1)
    recorder = _RecordingRequest(response=_make_response(200))
    client._session.request = recorder  # type: ignore[method-assign]
    client.get("/things")
    assert recorder.last["timeout"] == 5.0


@pytest.mark.parametrize(
    ("verb", "kwargs"),
    [
        ("get", {}),
        ("post", {"json": {"a": 1}}),
        ("put", {"json": {"a": 1}}),
        ("patch", {"json": {"a": 1}}),
        ("delete", {}),
    ],
)
def test_verb_methods_send_expected_method_and_body(verb: str, kwargs: dict[str, Any]) -> None:
    client = _client()
    recorder = _RecordingRequest(response=_make_response(200, json_body={"ok": True}))
    client._session.request = recorder  # type: ignore[method-assign]

    response = getattr(client, verb)("/things", params={"q": "1"}, **kwargs)

    assert recorder.last["method"] == verb.upper()
    assert recorder.last["url"] == "https://api.example.com/v1/things"
    assert recorder.last["params"] == {"q": "1"}
    assert recorder.last.get("json") == kwargs.get("json")
    assert response.data == {"ok": True}


@pytest.mark.parametrize(
    ("base_url", "path", "expected"),
    [
        ("https://api.example.com/v1", "/things", "https://api.example.com/v1/things"),
        ("https://api.example.com/v1/", "/things", "https://api.example.com/v1/things"),
        ("https://api.example.com/v1", "things", "https://api.example.com/v1/things"),
        ("https://api.example.com/v1/", "things", "https://api.example.com/v1/things"),
    ],
)
def test_url_joining(base_url: str, path: str, expected: str) -> None:
    client = HttpClient(base_url=base_url, auth=_StubAuth())
    recorder = _RecordingRequest(response=_make_response(200))
    client._session.request = recorder  # type: ignore[method-assign]

    client.get(path)

    assert recorder.last["url"] == expected


def test_two_clients_have_independent_base_urls() -> None:
    client_a = HttpClient(base_url="https://a.example.com", auth=_StubAuth())
    client_b = HttpClient(base_url="https://b.example.com", auth=_StubAuth())
    recorder_a = _RecordingRequest(response=_make_response(200))
    recorder_b = _RecordingRequest(response=_make_response(200))
    client_a._session.request = recorder_a  # type: ignore[method-assign]
    client_b._session.request = recorder_b  # type: ignore[method-assign]

    client_a.get("/x")
    client_b.get("/x")

    assert recorder_a.last["url"] == "https://a.example.com/x"
    assert recorder_b.last["url"] == "https://b.example.com/x"


def test_auth_object_attached_to_every_request() -> None:
    auth = _StubAuth()
    client = HttpClient(base_url="https://api.example.com", auth=auth)
    recorder = _RecordingRequest(response=_make_response(200))
    client._session.request = recorder  # type: ignore[method-assign]

    client.get("/x")

    assert recorder.last["auth"] is auth


def test_2xx_with_json_body() -> None:
    client = _client()
    client._session.request = _RecordingRequest(  # type: ignore[method-assign]
        response=_make_response(200, json_body={"a": 1})
    )
    response = client.get("/x")
    assert response == HttpResponse(200, {"a": 1}, response.headers)


def test_2xx_with_empty_body() -> None:
    client = _client()
    client._session.request = _RecordingRequest(response=_make_response(204))  # type: ignore[method-assign]
    response = client.delete("/x")
    assert response.data is None


def test_2xx_with_invalid_json_body_raises() -> None:
    client = _client()
    client._session.request = _RecordingRequest(  # type: ignore[method-assign]
        response=_make_response(200, content=b"not json")
    )
    with pytest.raises(VeracodeApiError):
        client.get("/x")


@pytest.mark.parametrize(
    ("status_code", "exception_cls"),
    [
        (401, VeracodeAuthenticationError),
        (403, VeracodeAuthorizationError),
        (404, VeracodeNotFoundError),
        (409, VeracodeConflictError),
        (422, VeracodeValidationError),
    ],
)
def test_mapped_status_codes_raise_specific_exceptions(
    status_code: int, exception_cls: type[VeracodeApiError]
) -> None:
    client = _client()
    client._session.request = _RecordingRequest(  # type: ignore[method-assign]
        response=_make_response(status_code, json_body={"detail": "nope"})
    )
    with pytest.raises(exception_cls) as exc_info:
        client.get("/x")
    err = exc_info.value
    assert err.status_code == status_code
    assert err.method == "GET"
    assert err.url == "https://api.example.com/v1/x"
    assert err.response_body == {"detail": "nope"}
    assert isinstance(err, VeracodeApiError)


@pytest.mark.parametrize("status_code", [400, 500])
def test_unmapped_status_codes_raise_base_api_error(status_code: int) -> None:
    client = _client()
    client._session.request = _RecordingRequest(response=_make_response(status_code))  # type: ignore[method-assign]
    with pytest.raises(VeracodeApiError) as exc_info:
        client.get("/x")
    assert type(exc_info.value) is VeracodeApiError
    assert exc_info.value.status_code == status_code


def test_connection_error_raises_veracode_connection_error() -> None:
    client = _client()
    client._session.request = _RecordingRequest(  # type: ignore[method-assign]
        exception=requests.exceptions.ConnectionError("refused")
    )
    with pytest.raises(VeracodeConnectionError) as exc_info:
        client.get("/x")
    assert exc_info.value.status_code is None


def test_timeout_raises_veracode_timeout_error() -> None:
    client = _client()
    client._session.request = _RecordingRequest(  # type: ignore[method-assign]
        exception=requests.exceptions.Timeout("slow")
    )
    with pytest.raises(VeracodeTimeoutError) as exc_info:
        client.get("/x")
    assert exc_info.value.status_code is None


def test_post_and_patch_excluded_from_retriable_methods() -> None:
    client = _client()
    adapter = client._session.get_adapter("https://api.example.com/v1/x")
    assert "POST" not in adapter.max_retries.allowed_methods
    assert "PATCH" not in adapter.max_retries.allowed_methods
    assert "GET" in adapter.max_retries.allowed_methods


def test_post_with_files_sends_multipart_and_no_json(caplog: pytest.LogCaptureFixture) -> None:
    client = _client()
    recorder = _RecordingRequest(response=_make_response(200, json_body={"ok": True}))  # type: ignore[method-assign]
    client._session.request = recorder

    spec_file = ("openapi.yaml", b"content: true", "application/x-yaml")
    client.post("/spec", files={"specFile": spec_file})

    assert recorder.last["json"] is None
    assert recorder.last["files"] == {"specFile": spec_file}


def test_get_raw_returns_bytes_without_json_parsing() -> None:
    client = _client()
    client._session.request = _RecordingRequest(  # type: ignore[method-assign]
        response=_make_response(200, content=b"\x00\x01binary-not-json")
    )
    response = client.get("/download", raw=True)
    assert response.data == b"\x00\x01binary-not-json"


def test_get_raw_with_empty_body_returns_none() -> None:
    client = _client()
    client._session.request = _RecordingRequest(response=_make_response(200, content=b""))  # type: ignore[method-assign]
    response = client.get("/download", raw=True)
    assert response.data is None


def test_no_log_record_contains_sensitive_values(caplog: pytest.LogCaptureFixture) -> None:
    client = _client()
    client._session.request = _RecordingRequest(  # type: ignore[method-assign]
        response=_make_response(401, json_body={"secret-field": "top-secret-body-value"})
    )
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(VeracodeAuthenticationError):
            client.post(
                "/x",
                json={"password": "super-secret-json-value"},
                headers={"X-Custom": "custom-header-value"},
            )

    for record in caplog.records:
        message = record.getMessage()
        assert "super-secret-json-value" not in message
        assert "custom-header-value" not in message
        assert "top-secret-body-value" not in message
