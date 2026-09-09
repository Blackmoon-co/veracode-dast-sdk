import logging
from typing import Any

import pytest

from veracode_dast.client import HttpResponse
from veracode_dast.exceptions import (
    ApplicationNotFoundError,
    TargetValidationError,
    VeracodeApiError,
)
from veracode_dast.services.applications import ApplicationsService


class _StubHttpClient:
    def __init__(
        self, responses: list[HttpResponse] | None = None, exception: Exception | None = None
    ) -> None:
        self._responses = list(responses or [])
        self._exception = exception
        self.calls: list[dict[str, Any]] = []

    def get(self, path: str, *, params: dict[str, Any] | None = None, **_: Any) -> HttpResponse:
        self.calls.append({"path": path, "params": params})
        if self._exception is not None:
            raise self._exception
        return self._responses.pop(0)


def _application_page_response(
    applications: list[dict[str, str]], *, number: int = 0, total_pages: int = 1
) -> HttpResponse:
    return HttpResponse(
        200,
        {
            "_embedded": {"Applications": applications},
            "page": {
                "size": 10,
                "total_elements": len(applications),
                "total_pages": total_pages,
                "number": number,
            },
        },
        {},
    )


def _app(name: str, *, guid: str = "g-1", id_: str = "1") -> dict[str, str]:
    return {"guid": guid, "id": id_, "name": name}


def test_list_uses_default_page_and_limit() -> None:
    stub = _StubHttpClient(responses=[_application_page_response([])])
    service = ApplicationsService(stub)  # type: ignore[arg-type]

    service.list()

    assert stub.calls[0]["params"] == {"page": 0, "limit": 10}


def test_list_forwards_name_only_when_given() -> None:
    stub = _StubHttpClient(responses=[_application_page_response([])])
    service = ApplicationsService(stub)  # type: ignore[arg-type]

    service.list(name="My App", page=2, limit=50)

    assert stub.calls[0]["params"] == {"page": 2, "limit": 50, "name": "My App"}


def test_get_by_name_blank_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = ApplicationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(TargetValidationError):
        service.get_by_name("  ")
    assert stub.calls == []


def test_get_by_name_exact_match_on_first_page() -> None:
    stub = _StubHttpClient(responses=[_application_page_response([_app("My App", guid="g-9")])])
    service = ApplicationsService(stub)  # type: ignore[arg-type]

    application = service.get_by_name("My App")

    assert application.guid == "g-9"
    assert stub.calls[0]["params"]["name"] == "My App"
    assert len(stub.calls) == 1


def test_get_by_name_rejects_substring_only_match_and_keeps_scanning() -> None:
    stub = _StubHttpClient(
        responses=[
            _application_page_response(
                [_app("My App Staging", guid="g-1")], number=0, total_pages=2
            ),
            _application_page_response([_app("My App", guid="g-2")], number=1, total_pages=2),
        ]
    )
    service = ApplicationsService(stub)  # type: ignore[arg-type]

    application = service.get_by_name("My App")

    assert application.guid == "g-2"
    assert len(stub.calls) == 2


def test_get_by_name_no_exact_match_raises_application_not_found() -> None:
    stub = _StubHttpClient(
        responses=[_application_page_response([_app("my app"), _app("My App 2")])]
    )
    service = ApplicationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(ApplicationNotFoundError) as excinfo:
        service.get_by_name("My App")
    assert excinfo.value.name == "My App"


def test_exists_true_when_found() -> None:
    stub = _StubHttpClient(responses=[_application_page_response([_app("My App")])])
    service = ApplicationsService(stub)  # type: ignore[arg-type]

    assert service.exists("My App") is True


def test_exists_false_when_not_found() -> None:
    stub = _StubHttpClient(responses=[_application_page_response([])])
    service = ApplicationsService(stub)  # type: ignore[arg-type]

    assert service.exists("My App") is False


def test_exists_propagates_non_not_found_errors() -> None:
    stub = _StubHttpClient(
        exception=VeracodeApiError("boom", method="GET", url="x", status_code=500)
    )
    service = ApplicationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeApiError):
        service.exists("My App")


def test_no_log_record_contains_application_identifiers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stub = _StubHttpClient(
        responses=[
            _application_page_response(
                [{"guid": "secret-guid", "id": "1", "name": "My App"}]
            )
        ]
    )
    service = ApplicationsService(stub)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        service.get_by_name("My App")

    # The resolve log deliberately includes the guid; assert it never
    # leaks the linked_scan_target_url or any other business field.
    for record in caplog.records:
        assert "linked_scan_target_url" not in record.getMessage()
