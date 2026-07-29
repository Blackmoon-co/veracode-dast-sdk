import logging
from pathlib import Path
from typing import Any

import pytest

from veracode_dast.client import HttpResponse
from veracode_dast.exceptions import (
    ScannerValidationError,
    UnknownScannerError,
    VeracodeNotFoundError,
)
from veracode_dast.services.scanners import ScannersService


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


def _profile_response(**overrides: object) -> HttpResponse:
    data: dict[str, object] = {
        "analysis_profile_id": "ap-1",
        "parent_analysis_profile_id": "ap-parent",
        "scanners": [
            {
                "id": "sql_injection",
                "effective_value": True,
                "is_inherited": False,
                "is_editable": True,
            },
        ],
    }
    data.update(overrides)
    return HttpResponse(200, data, {})


def test_get_blank_id_raises_without_http_call() -> None:
    stub = _StubHttpClient()
    service = ScannersService(stub)  # type: ignore[arg-type]

    with pytest.raises(ScannerValidationError):
        service.get("  ")
    assert stub.calls == []


def test_get_success() -> None:
    stub = _StubHttpClient()
    stub.queue(_profile_response())
    service = ScannersService(stub)  # type: ignore[arg-type]

    profile = service.get("ap-1")

    assert profile.analysis_profile_id == "ap-1"
    assert stub.calls[0]["path"] == "/analysis_profiles/ap-1/scanners"


def test_get_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="GET", url="x", status_code=404))
    service = ScannersService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.get("missing")


def test_update_blank_id_raises_without_http_call() -> None:
    stub = _StubHttpClient()
    service = ScannersService(stub)  # type: ignore[arg-type]

    with pytest.raises(ScannerValidationError):
        service.update("", {"scanners": {"xss": True}})
    assert stub.calls == []


def test_update_readme_example_transformation(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    stub.queue(_profile_response())
    service = ScannersService(stub)  # type: ignore[arg-type]

    config = {"scanners": {"sql_injection": True, "xss": True, "csrf": False}}
    service.update("ap-1", config)

    assert stub.calls[0]["json"] == {
        "scanners": [
            {"id": "sql_injection", "value": True},
            {"id": "xss", "value": True},
            {"id": "csrf", "value": False},
        ]
    }


def test_update_accepts_file_path(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    stub.queue(_profile_response())
    service = ScannersService(stub)  # type: ignore[arg-type]

    path = tmp_path / "scanner-profile.json"
    path.write_text('{"scanners": {"xss": true}}', encoding="utf-8")

    service.update("ap-1", path)

    assert stub.calls[0]["json"] == {"scanners": [{"id": "xss", "value": True}]}


def test_update_config_must_be_object(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    service = ScannersService(stub)  # type: ignore[arg-type]
    path = tmp_path / "config.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ScannerValidationError):
        service.update("ap-1", path)
    assert stub.calls == []


def test_update_missing_scanners_key() -> None:
    stub = _StubHttpClient()
    service = ScannersService(stub)  # type: ignore[arg-type]

    with pytest.raises(ScannerValidationError):
        service.update("ap-1", {})
    assert stub.calls == []


def test_update_non_bool_value() -> None:
    stub = _StubHttpClient()
    service = ScannersService(stub)  # type: ignore[arg-type]

    with pytest.raises(ScannerValidationError):
        service.update("ap-1", {"scanners": {"xss": "yes"}})
    assert stub.calls == []


def test_update_empty_scanners_is_valid() -> None:
    stub = _StubHttpClient()
    stub.queue(_profile_response())
    service = ScannersService(stub)  # type: ignore[arg-type]

    service.update("ap-1", {"scanners": {}})

    assert stub.calls[0]["json"] == {"scanners": []}


def test_update_unknown_scanner_suggests_closest() -> None:
    stub = _StubHttpClient()
    service = ScannersService(stub)  # type: ignore[arg-type]

    with pytest.raises(UnknownScannerError) as exc_info:
        service.update("ap-1", {"scanners": {"sql": True}})
    assert "Unknown scanner 'sql'." in str(exc_info.value)
    assert "Did you mean 'sql_injection'?" in str(exc_info.value)
    assert stub.calls == []


def test_update_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="PUT", url="x", status_code=404))
    service = ScannersService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.update("missing", {"scanners": {"xss": True}})


def test_no_log_record_contains_full_payload(caplog: pytest.LogCaptureFixture) -> None:
    stub = _StubHttpClient()
    stub.queue(_profile_response())
    service = ScannersService(stub)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        service.update("ap-1", {"scanners": {"sql_injection": True}})

    for record in caplog.records:
        assert "sql_injection" not in record.getMessage()
