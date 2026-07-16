import logging
from typing import Any

import pytest

from veracode_dast.client import HttpResponse
from veracode_dast.exceptions import (
    TeamNotFoundError,
    TeamValidationError,
    VeracodeApiError,
    VeracodeNotFoundError,
)
from veracode_dast.services.teams import TeamService


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


def _team_page_response(
    teams: list[dict[str, str]], *, number: int = 0, total_pages: int = 1
) -> HttpResponse:
    return HttpResponse(
        200,
        {
            "_embedded": {"teams": teams},
            "page": {
                "size": 20,
                "total_elements": len(teams),
                "total_pages": total_pages,
                "number": number,
            },
        },
        {},
    )


def test_list_uses_default_page_and_size() -> None:
    stub = _StubHttpClient(responses=[_team_page_response([])])
    service = TeamService(stub)  # type: ignore[arg-type]

    service.list()

    assert stub.calls[0]["params"] == {"page": 0, "size": 20}


def test_list_forwards_supplied_arguments() -> None:
    stub = _StubHttpClient(responses=[_team_page_response([])])
    service = TeamService(stub)  # type: ignore[arg-type]

    service.list(page=2, size=50, team_name="Dev")

    assert stub.calls[0]["params"] == {"page": 2, "size": 50, "team_name": "Dev"}


def test_get_blank_team_id_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = TeamService(stub)  # type: ignore[arg-type]

    with pytest.raises(TeamValidationError):
        service.get("  ")
    assert stub.calls == []


def test_get_success() -> None:
    stub = _StubHttpClient(
        responses=[HttpResponse(200, {"team_id": "abc", "team_name": "Development"}, {})]
    )
    service = TeamService(stub)  # type: ignore[arg-type]

    team = service.get("abc")

    assert team.team_id == "abc"
    assert stub.calls[0]["path"] == "/teams/abc"


def test_get_not_found_propagates() -> None:
    stub = _StubHttpClient(
        exception=VeracodeNotFoundError("nope", method="GET", url="x", status_code=404)
    )
    service = TeamService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.get("missing")


def test_get_by_name_blank_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = TeamService(stub)  # type: ignore[arg-type]

    with pytest.raises(TeamValidationError):
        service.get_by_name("")
    assert stub.calls == []


def test_get_by_name_exact_match_on_first_page() -> None:
    stub = _StubHttpClient(
        responses=[_team_page_response([{"team_id": "1", "team_name": "Development"}])]
    )
    service = TeamService(stub)  # type: ignore[arg-type]

    team = service.get_by_name("Development")

    assert team.team_id == "1"
    assert stub.calls[0]["params"]["team_name"] == "Development"


def test_get_by_name_rejects_substring_only_match_and_keeps_scanning() -> None:
    stub = _StubHttpClient(
        responses=[
            _team_page_response(
                [{"team_id": "1", "team_name": "Development Team"}], number=0, total_pages=2
            ),
            _team_page_response(
                [{"team_id": "2", "team_name": "Development"}], number=1, total_pages=2
            ),
        ]
    )
    service = TeamService(stub)  # type: ignore[arg-type]

    team = service.get_by_name("Development")

    assert team.team_id == "2"
    assert len(stub.calls) == 2


def test_get_by_name_no_match_raises_team_not_found() -> None:
    stub = _StubHttpClient(
        responses=[_team_page_response([{"team_id": "1", "team_name": "Other"}])]
    )
    service = TeamService(stub)  # type: ignore[arg-type]

    with pytest.raises(TeamNotFoundError):
        service.get_by_name("Development")


def test_exists_true_when_found() -> None:
    stub = _StubHttpClient(
        responses=[_team_page_response([{"team_id": "1", "team_name": "Development"}])]
    )
    service = TeamService(stub)  # type: ignore[arg-type]

    assert service.exists("Development") is True


def test_exists_false_when_not_found() -> None:
    stub = _StubHttpClient(responses=[_team_page_response([])])
    service = TeamService(stub)  # type: ignore[arg-type]

    assert service.exists("Development") is False


def test_exists_propagates_non_not_found_errors() -> None:
    stub = _StubHttpClient(
        exception=VeracodeApiError("boom", method="GET", url="x", status_code=500)
    )
    service = TeamService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeApiError):
        service.exists("Development")


def test_no_log_record_contains_extra_fields(caplog: pytest.LogCaptureFixture) -> None:
    stub = _StubHttpClient(
        responses=[_team_page_response([{"team_id": "1", "team_name": "Development"}])]
    )
    service = TeamService(stub)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        service.get_by_name("Development")

    for record in caplog.records:
        message = record.getMessage()
        assert "business_unit" not in message
        assert "organization" not in message
