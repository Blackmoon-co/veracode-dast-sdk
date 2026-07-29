import logging
from typing import Any

import pytest

from veracode_dast.client import HttpResponse
from veracode_dast.exceptions import (
    AnalysisProfileValidationError,
    VeracodeNotFoundError,
    VeracodeValidationError,
)
from veracode_dast.models.analysis_profile import AnalysisProfileType, AnalysisProfileUpdate
from veracode_dast.services.analysis_profiles import AnalysisProfilesService


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


def _profile_fixture(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "analysis_profile_id": "ap-1",
        "parent_analysis_profile_id": "ap-parent",
        "name": "Production",
        "mode": "STANDARD",
        "allowed_urls": {"effective_value": [], "is_inherited": True},
        "denied_urls": {"effective_value": [], "is_inherited": True},
        "seed_urls": {"effective_value": [], "is_inherited": True},
        "grouped_urls": {"effective_value": [], "is_inherited": True},
        "crawler_enabled": {"effective_value": True, "is_inherited": True},
        "crawler_mode": {"effective_value": "SMART", "is_inherited": True},
        "rate_limit": {"effective_value": 300, "is_inherited": True},
        "max_duration": {"effective_value": 120, "is_inherited": True},
        "max_crawl_duration": {"effective_value": 60, "is_inherited": True},
    }
    data.update(overrides)
    return data


def _page_response(profiles: list[dict[str, object]]) -> HttpResponse:
    return HttpResponse(
        200,
        {
            "_embedded": {"analysis_profiles": profiles},
            "page": {"number": 0, "size": 10, "total_pages": 1, "total_elements": len(profiles)},
        },
        {},
    )


def test_list_default_query_parameters() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([]))
    service = AnalysisProfilesService(stub)  # type: ignore[arg-type]

    service.list()

    assert stub.calls[0]["params"] == {"page": 0, "limit": 10}


def test_list_forwards_target_id_and_types() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([]))
    service = AnalysisProfilesService(stub)  # type: ignore[arg-type]

    service.list(target_id="t-1", types=[AnalysisProfileType.TARGET, AnalysisProfileType.ORG])

    params = stub.calls[0]["params"]
    assert params["target_id"] == "t-1"
    assert params["type"] == ["TARGET", "ORG"]


def test_get_blank_id_raises_without_http_call() -> None:
    stub = _StubHttpClient()
    service = AnalysisProfilesService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisProfileValidationError):
        service.get(" ")
    assert stub.calls == []


def test_get_success() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, _profile_fixture(), {}))
    service = AnalysisProfilesService(stub)  # type: ignore[arg-type]

    profile = service.get("ap-1")

    assert profile.analysis_profile_id == "ap-1"
    assert profile.allowed_urls.is_inherited is True


def test_get_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="GET", url="x", status_code=404))
    service = AnalysisProfilesService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.get("missing")


def test_update_blank_id_raises_without_http_call() -> None:
    stub = _StubHttpClient()
    service = AnalysisProfilesService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisProfileValidationError):
        service.update("", AnalysisProfileUpdate(rate_limit=300))
    assert stub.calls == []


def test_update_always_sends_method_patch_and_partial_body() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, _profile_fixture(), {}))
    service = AnalysisProfilesService(stub)  # type: ignore[arg-type]

    service.update("ap-1", AnalysisProfileUpdate(rate_limit=300))

    assert stub.calls[0]["params"] == {"method": "PATCH"}
    assert stub.calls[0]["json"] == {"rate_limit": 300}


def test_update_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="PUT", url="x", status_code=404))
    service = AnalysisProfilesService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.update("missing", AnalysisProfileUpdate(rate_limit=300))


def test_update_validation_error_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeValidationError("bad", method="PUT", url="x", status_code=422))
    service = AnalysisProfilesService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeValidationError):
        service.update("ap-1", AnalysisProfileUpdate(rate_limit=1))


def test_no_log_record_contains_business_data(caplog: pytest.LogCaptureFixture) -> None:
    stub = _StubHttpClient()
    stub.queue(
        HttpResponse(
            200,
            _profile_fixture(
                allowed_urls={"effective_value": ["secret-url"], "is_inherited": False}
            ),
            {},
        )
    )
    service = AnalysisProfilesService(stub)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        service.get("ap-1")

    for record in caplog.records:
        assert "secret-url" not in record.getMessage()
