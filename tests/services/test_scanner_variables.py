import logging
from pathlib import Path
from typing import Any

import pytest

from veracode_dast.client import HttpResponse
from veracode_dast.exceptions import ScannerVariableValidationError, VeracodeNotFoundError
from veracode_dast.services.scanner_variables import ScannerVariablesService


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
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]

    with pytest.raises(ScannerVariableValidationError):
        service.get(" ")
    assert stub.calls == []


def test_get_success() -> None:
    stub = _StubHttpClient()
    stub.queue(
        HttpResponse(
            200,
            [
                {
                    "effective_value": {"reference_key": "username", "value": "admin"},
                    "is_inherited": False,
                }
            ],
            {},
        )
    )
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]

    result = service.get("ap-1")

    assert len(result.variables) == 1


def test_get_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="GET", url="x", status_code=404))
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.get("missing")


def test_update_blank_id_raises_without_http_call() -> None:
    stub = _StubHttpClient()
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]

    with pytest.raises(ScannerVariableValidationError):
        service.update("", {"variables": []})
    assert stub.calls == []


def test_update_readme_example_transformation() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, [], {}))
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]

    config = {
        "variables": [
            {"reference_key": "username", "value": "admin"},
            {"reference_key": "password", "value": "secret123"},
            {"reference_key": "otp", "value": "ABCDEFGHIJKLMNOP", "totp_seed": True},
        ]
    }
    service.update("ap-1", config)

    assert stub.calls[0]["json"] == [
        {"reference_key": "username", "value": "admin", "evaluation_mode": "RAW"},
        {"reference_key": "password", "value": "secret123", "evaluation_mode": "RAW"},
        {"reference_key": "otp", "value": "ABCDEFGHIJKLMNOP", "evaluation_mode": "TOTP"},
    ]


def test_update_no_read_then_merge() -> None:
    """A config listing fewer variables than an existing set sends only those."""
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, [], {}))
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]

    service.update("ap-1", {"variables": [{"reference_key": "username", "value": "admin"}]})

    assert len(stub.calls) == 1
    assert stub.calls[0]["json"] == [
        {"reference_key": "username", "value": "admin", "evaluation_mode": "RAW"}
    ]


def test_update_empty_variables_with_204_response() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(204, None, {}))
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]

    result = service.update("ap-1", {"variables": []})

    assert result.variables == []
    assert stub.calls[0]["json"] == []


def test_update_accepts_file_and_dict_identically(tmp_path: Path) -> None:
    config = {"variables": [{"reference_key": "username", "value": "admin"}]}
    path = tmp_path / "scanner-variables.json"
    path.write_text(
        '{"variables": [{"reference_key": "username", "value": "admin"}]}', encoding="utf-8"
    )

    stub_a = _StubHttpClient()
    stub_a.queue(HttpResponse(200, [], {}))
    ScannerVariablesService(stub_a).update("ap-1", config)  # type: ignore[arg-type]

    stub_b = _StubHttpClient()
    stub_b.queue(HttpResponse(200, [], {}))
    ScannerVariablesService(stub_b).update("ap-1", path)  # type: ignore[arg-type]

    assert stub_a.calls[0]["json"] == stub_b.calls[0]["json"]


def test_update_config_must_be_object(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]
    path = tmp_path / "config.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ScannerVariableValidationError) as exc_info:
        service.update("ap-1", path)
    assert exc_info.value.rule == "config_must_be_object"
    assert stub.calls == []


@pytest.mark.parametrize(
    ("config", "rule"),
    [
        ({}, "variables_key_required"),
        ({"variables": ["not-a-dict"]}, "variable_must_be_object"),
        ({"variables": [{"value": "x"}]}, "reference_key_required"),
        ({"variables": [{"reference_key": "k"}]}, "value_required"),
        (
            {
                "variables": [
                    {"reference_key": "k", "value": "a"},
                    {"reference_key": "k", "value": "b"},
                ]
            },
            "duplicate_reference_key",
        ),
        (
            {"variables": [{"reference_key": "k", "value": "a", "totp_seed": "yes"}]},
            "invalid_totp_configuration",
        ),
    ],
)
def test_update_validation_failures_raise_before_http_call(config: Any, rule: str) -> None:
    stub = _StubHttpClient()
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]

    with pytest.raises(ScannerVariableValidationError) as exc_info:
        service.update("ap-1", config)
    assert exc_info.value.rule == rule
    assert stub.calls == []


def test_update_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="PUT", url="x", status_code=404))
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.update("missing", {"variables": []})


def test_no_log_record_contains_variable_values(caplog: pytest.LogCaptureFixture) -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, [], {}))
    service = ScannerVariablesService(stub)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        service.update(
            "ap-1",
            {
                "variables": [
                    {"reference_key": "otp", "value": "ABCDEFGHIJKLMNOP", "totp_seed": True}
                ]
            },
        )

    for record in caplog.records:
        assert "ABCDEFGHIJKLMNOP" not in record.getMessage()
