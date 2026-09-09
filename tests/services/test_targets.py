import logging
from typing import Any

import pytest

from veracode_dast.client import HttpResponse
from veracode_dast.exceptions import (
    TargetNotFoundError,
    TargetValidationError,
    VeracodeApiError,
    VeracodeConflictError,
    VeracodeNotFoundError,
    VeracodeValidationError,
)
from veracode_dast.models.target import Protocol, ScanType, TargetCreate, TargetType, TargetUpdate
from veracode_dast.services.targets import TargetsService


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

    def post(self, path: str, **kwargs: Any) -> HttpResponse:
        return self._handle("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> HttpResponse:
        return self._handle("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> HttpResponse:
        return self._handle("DELETE", path, **kwargs)


def _target_fixture(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "target_id": "t-1",
        "name": "My Target",
        "protocol": "HTTPS",
        "url": "sub.domain.tld",
        "target_type": "WEB_APP",
        "scan_type": "QUICK",
        "is_sec_lead_only": False,
        "teams": ["1"],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
    }
    data.update(overrides)
    return data


def _page_response(
    targets: list[dict[str, object]], *, number: int = 0, total_pages: int = 1
) -> HttpResponse:
    return HttpResponse(
        200,
        {
            "_embedded": {"targets": targets},
            "page": {
                "size": 10,
                "total_elements": len(targets),
                "total_pages": total_pages,
                "number": number,
            },
        },
        {},
    )


def _valid_create(**overrides: object) -> TargetCreate:
    kwargs: dict[str, object] = {
        "name": "My Target",
        "url": "sub.domain.tld",
        "protocol": Protocol.HTTPS,
        "target_type": TargetType.WEB_APP,
        "scan_type": ScanType.QUICK,
        "authorized_to_scan": True,
        "is_sec_lead_only": False,
        "teams": ["1"],
    }
    kwargs.update(overrides)
    return TargetCreate(**kwargs)  # type: ignore[arg-type]


def test_list_default_query_parameters() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([]))
    service = TargetsService(stub)  # type: ignore[arg-type]

    service.list()

    assert stub.calls[0]["params"] == {
        "page": 0,
        "limit": 10,
        "sort_by": "name",
        "sort_order": "asc",
    }


def test_list_forwards_supplied_arguments() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([]))
    service = TargetsService(stub)  # type: ignore[arg-type]

    service.list(name="Foo", url="bar.tld", search_term="baz", target_type=TargetType.API)

    params = stub.calls[0]["params"]
    assert params["name"] == "Foo"
    assert params["url"] == "bar.tld"
    assert params["search_term"] == "baz"
    assert params["target_type"] == "API"


def test_get_success() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, _target_fixture(), {}))
    service = TargetsService(stub)  # type: ignore[arg-type]

    target = service.get("t-1")

    assert target.target_id == "t-1"


def test_get_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="GET", url="x", status_code=404))
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.get("missing")


def test_create_success() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(201, _target_fixture(), {}))
    service = TargetsService(stub)  # type: ignore[arg-type]

    target = service.create(_valid_create())

    assert target.target_id == "t-1"
    assert stub.calls[0]["json"]["name"] == "My Target"


def test_create_api_target_requires_spec_url() -> None:
    stub = _StubHttpClient()
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(TargetValidationError):
        service.create(_valid_create(target_type=TargetType.API, api_specification_file_url=None))
    assert stub.calls == []


def test_create_sec_lead_only_excludes_teams() -> None:
    stub = _StubHttpClient()
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(TargetValidationError):
        service.create(_valid_create(is_sec_lead_only=True, teams=["1"]))
    assert stub.calls == []


def test_create_requires_teams_unless_sec_lead_only() -> None:
    stub = _StubHttpClient()
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(TargetValidationError):
        service.create(_valid_create(is_sec_lead_only=False, teams=None))
    assert stub.calls == []


def test_create_teams_max_one() -> None:
    stub = _StubHttpClient()
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(TargetValidationError):
        service.create(_valid_create(teams=["1", "2"]))
    assert stub.calls == []


def test_create_server_error_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeApiError("bad", method="POST", url="x", status_code=400))
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeApiError):
        service.create(_valid_create())


def test_update_only_sends_explicitly_set_fields() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, _target_fixture(name="New Name"), {}))
    service = TargetsService(stub)  # type: ignore[arg-type]

    service.update("t-1", TargetUpdate(name="New Name", teams=None))

    assert stub.calls[0]["json"] == {"name": "New Name", "teams": None}


def test_update_teams_max_one_raises_before_call() -> None:
    stub = _StubHttpClient()
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(TargetValidationError):
        service.update("t-1", TargetUpdate(teams=["1", "2"]))
    assert stub.calls == []


def test_delete_success() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(204, None, {}))
    service = TargetsService(stub)  # type: ignore[arg-type]

    assert service.delete("t-1") is None


def test_delete_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="DELETE", url="x", status_code=404))
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.delete("missing")


def test_get_by_name_match_on_first_page() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([_target_fixture(name="Match")]))
    service = TargetsService(stub)  # type: ignore[arg-type]

    target = service.get_by_name("Match")

    assert target is not None
    assert target.name == "Match"


def test_get_by_name_match_requires_second_page() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([_target_fixture(name="Other")], number=0, total_pages=2))
    stub.queue(_page_response([_target_fixture(name="Match")], number=1, total_pages=2))
    service = TargetsService(stub)  # type: ignore[arg-type]

    target = service.get_by_name("Match")

    assert target is not None
    assert len(stub.calls) == 2


def test_get_by_name_no_match_returns_none() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([_target_fixture(name="Other")]))
    service = TargetsService(stub)  # type: ignore[arg-type]

    assert service.get_by_name("Missing") is None


def test_exists_delegates_to_get_by_name() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([_target_fixture(name="Match")]))
    service = TargetsService(stub)  # type: ignore[arg-type]

    assert service.exists("Match") is True


def test_ensure_returns_existing_without_creating() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([_target_fixture(name="My Target")]))
    service = TargetsService(stub)  # type: ignore[arg-type]

    result = service.ensure(_valid_create())

    assert result.target_id == "t-1"
    assert all(call["verb"] != "POST" for call in stub.calls)


def test_ensure_creates_when_missing() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([]))
    stub.queue(HttpResponse(201, _target_fixture(), {}))
    service = TargetsService(stub)  # type: ignore[arg-type]

    result = service.ensure(_valid_create())

    assert result.target_id == "t-1"
    assert any(call["verb"] == "POST" for call in stub.calls)
    assert all(call["verb"] != "PUT" for call in stub.calls)


def test_update_by_name_found() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([_target_fixture(name="My Target")]))
    stub.queue(HttpResponse(200, _target_fixture(name="Renamed"), {}))
    service = TargetsService(stub)  # type: ignore[arg-type]

    result = service.update_by_name("My Target", TargetUpdate(name="Renamed"))

    assert result.name == "Renamed"
    put_calls = [call for call in stub.calls if call["verb"] == "PUT"]
    assert put_calls[0]["path"] == "/targets/t-1"


def test_update_by_name_not_found_raises_without_put() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([]))
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(TargetNotFoundError):
        service.update_by_name("Missing", TargetUpdate(name="Renamed"))
    assert all(call["verb"] != "PUT" for call in stub.calls)


def test_no_log_record_contains_business_data(caplog: pytest.LogCaptureFixture) -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(201, _target_fixture(url="secret-internal-host.example"), {}))
    service = TargetsService(stub)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        service.create(_valid_create())

    for record in caplog.records:
        message = record.getMessage()
        assert "secret-internal-host.example" not in message


def test_link_sends_application_uuid_body() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(204, None, {}))
    service = TargetsService(stub)  # type: ignore[arg-type]

    assert service.link("t-1", "app-uuid") is None
    assert stub.calls[0]["verb"] == "PUT"
    assert stub.calls[0]["path"] == "/targets/t-1/link"
    assert stub.calls[0]["json"] == {"application_uuid": "app-uuid"}


def test_link_blank_target_id_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(TargetValidationError) as excinfo:
        service.link("  ", "app-uuid")
    assert excinfo.value.rule == "target_id_required"
    assert stub.calls == []


def test_link_blank_application_uuid_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(TargetValidationError) as excinfo:
        service.link("t-1", "")
    assert excinfo.value.rule == "application_uuid_required"
    assert stub.calls == []


@pytest.mark.parametrize(
    ("status", "exception"),
    [
        (404, VeracodeNotFoundError),
        (409, VeracodeConflictError),
        (422, VeracodeValidationError),
    ],
)
def test_link_server_errors_propagate(
    status: int, exception: type[VeracodeApiError]
) -> None:
    stub = _StubHttpClient()
    stub.raise_next(exception("boom", method="PUT", url="x", status_code=status))
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(exception):
        service.link("t-1", "app-uuid")


def test_unlink_sends_delete() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(204, None, {}))
    service = TargetsService(stub)  # type: ignore[arg-type]

    assert service.unlink("t-1") is None
    assert stub.calls[0]["verb"] == "DELETE"
    assert stub.calls[0]["path"] == "/targets/t-1/link"


def test_unlink_blank_target_id_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = TargetsService(stub)  # type: ignore[arg-type]

    with pytest.raises(TargetValidationError):
        service.unlink("")
    assert stub.calls == []


def test_link_unlink_logs_do_not_contain_application_uuid(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(204, None, {}))
    stub.queue(HttpResponse(204, None, {}))
    service = TargetsService(stub)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        service.link("t-1", "secret-app-uuid")
        service.unlink("t-1")

    for record in caplog.records:
        assert "secret-app-uuid" not in record.getMessage()
