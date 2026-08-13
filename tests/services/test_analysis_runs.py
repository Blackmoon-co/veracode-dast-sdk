import logging
from pathlib import Path
from typing import Any

import pytest

from veracode_dast.client import HttpResponse
from veracode_dast.exceptions import (
    AnalysisRunTimeoutError,
    AnalysisRunValidationError,
    VeracodeNotFoundError,
)
from veracode_dast.models.analysis_run import StopActionType
from veracode_dast.models.target import TargetStatus
from veracode_dast.services import analysis_runs as analysis_runs_module
from veracode_dast.services.analysis_runs import AnalysisRunsService


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


def _run_fixture(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "analysis_run_id": "run-1",
        "target_id": "t-1",
        "scan_number": 1,
        "started_at": "2026-08-11T10:00:00Z",
        "url": "https://example.com",
        "target_protocol": "HTTPS",
        "scan_type": "ENTERPRISE",
        "started_by_name": "jane.doe",
        "max_duration": 14400,
        "max_crawl_duration": 3600,
    }
    data.update(overrides)
    return data


def _run_response(**overrides: object) -> HttpResponse:
    return HttpResponse(200, _run_fixture(**overrides), {})


def _page_response(runs: list[dict[str, object]]) -> HttpResponse:
    return HttpResponse(
        200,
        {
            "_embedded": {"analysis_runs": runs},
            "page": {"size": 10, "total_elements": len(runs), "total_pages": 1, "number": 0},
        },
        {},
    )


# --- start() ---


def test_start_sends_expected_body_and_returns_run() -> None:
    stub = _StubHttpClient()
    stub.queue(_run_response())
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    run = service.start("t-1")

    assert run.analysis_run_id == "run-1"
    assert stub.calls[0]["path"] == "/analysis_run"
    assert stub.calls[0]["json"] == {"id": "t-1"}


def test_start_blank_target_id_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError):
        service.start("  ")
    assert stub.calls == []


# --- stop() ---


def test_stop_default_action_is_stop_delete() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, None, {}))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    result = service.stop("t-1")

    assert result is None
    assert stub.calls[0]["path"] == "/analysis_run/t-1/stop"
    assert stub.calls[0]["params"] == {"action": "STOP_DELETE"}


def test_stop_accepts_enum_action() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, None, {}))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    service.stop("t-1", action=StopActionType.STOP_SAVE)

    assert stub.calls[0]["params"] == {"action": "STOP_SAVE"}


def test_stop_accepts_plain_string_action() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, None, {}))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    service.stop("t-1", action="STOP_SAVE")

    assert stub.calls[0]["params"] == {"action": "STOP_SAVE"}


def test_stop_invalid_string_action_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError) as exc_info:
        service.stop("t-1", action="cancel")
    assert stub.calls == []
    assert exc_info.value.rule == "invalid_stop_action"


def test_stop_blank_target_id_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError):
        service.stop("")
    assert stub.calls == []


# --- list() ---


def test_list_default_query_parameters() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([]))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    service.list("t-1")

    assert stub.calls[0]["path"] == "/targets/t-1/analysis_runs"
    assert stub.calls[0]["params"] == {"page": 0, "limit": 10}


def test_list_returns_page_of_runs() -> None:
    stub = _StubHttpClient()
    stub.queue(_page_response([_run_fixture()]))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    page = service.list("t-1")

    assert len(page.items) == 1
    assert page.items[0].analysis_run_id == "run-1"


def test_list_blank_target_id_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError):
        service.list(" ")
    assert stub.calls == []


def test_list_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="GET", url="x", status_code=404))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.list("missing")


# --- get() ---


def test_get_success() -> None:
    stub = _StubHttpClient()
    stub.queue(_run_response())
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    run = service.get("t-1", "run-1")

    assert run.analysis_run_id == "run-1"
    assert stub.calls[0]["path"] == "/targets/t-1/analysis_runs/run-1"


def test_get_blank_target_id_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError):
        service.get("", "run-1")
    assert stub.calls == []


def test_get_blank_analysis_run_id_raises_without_call() -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError):
        service.get("t-1", "  ")
    assert stub.calls == []


def test_get_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="GET", url="x", status_code=404))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.get("t-1", "missing")


# --- wait_for_completion() ---


def test_wait_for_completion_polls_until_terminal_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub = _StubHttpClient()
    stub.queue(_run_response(status="RUNNING"))
    stub.queue(_run_response(status="RUNNING"))
    stub.queue(_run_response(status="FINISHED"))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    sleep_calls: list[float] = []
    monkeypatch.setattr(analysis_runs_module.time, "sleep", sleep_calls.append)

    run = service.wait_for_completion("t-1", "run-1", poll_interval=5)

    assert run.status == TargetStatus.FINISHED
    assert len(stub.calls) == 3
    assert sleep_calls == [5, 5]


def test_wait_for_completion_treats_missing_status_as_non_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub = _StubHttpClient()
    stub.queue(_run_response(status=None))
    stub.queue(_run_response(status="FINISHED"))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    monkeypatch.setattr(analysis_runs_module.time, "sleep", lambda _seconds: None)

    run = service.wait_for_completion("t-1", "run-1", poll_interval=1)

    assert run.status == TargetStatus.FINISHED
    assert len(stub.calls) == 2


def test_wait_for_completion_stopped_and_failed_are_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(analysis_runs_module.time, "sleep", lambda _seconds: None)

    for status in ("STOPPED", "FAILED"):
        stub = _StubHttpClient()
        stub.queue(_run_response(status=status))
        service = AnalysisRunsService(stub)  # type: ignore[arg-type]

        run = service.wait_for_completion("t-1", "run-1", poll_interval=1)

        assert run.status == TargetStatus(status)


def test_wait_for_completion_timeout_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubHttpClient()
    stub.queue(_run_response(status="RUNNING"))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    fake_times = iter([0.0, 100.0])
    monkeypatch.setattr(analysis_runs_module.time, "monotonic", lambda: next(fake_times))
    sleep_calls: list[float] = []
    monkeypatch.setattr(analysis_runs_module.time, "sleep", sleep_calls.append)

    with pytest.raises(AnalysisRunTimeoutError) as exc_info:
        service.wait_for_completion("t-1", "run-1", poll_interval=5, timeout=10)

    assert sleep_calls == []
    assert exc_info.value.last_status == TargetStatus.RUNNING
    assert exc_info.value.target_id == "t-1"
    assert exc_info.value.analysis_run_id == "run-1"


def test_wait_for_completion_poll_interval_must_be_positive() -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError):
        service.wait_for_completion("t-1", "run-1", poll_interval=0)
    assert stub.calls == []


def test_wait_for_completion_timeout_must_be_positive() -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError):
        service.wait_for_completion("t-1", "run-1", timeout=0)
    assert stub.calls == []


# --- get_report() ---


def test_get_report_writes_bytes_to_destination(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, b"%PDF-1.4 report bytes", {}))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]
    destination = tmp_path / "report.pdf"

    result = service.get_report("t-1", "run-1", "pdf", destination)

    assert result == destination
    assert destination.read_bytes() == b"%PDF-1.4 report bytes"
    assert stub.calls[0]["path"] == "/targets/t-1/analysis_runs/run-1/report/pdf"


def test_get_report_invalid_format_raises_without_call(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError) as exc_info:
        service.get_report("t-1", "run-1", "xml", tmp_path / "report.xml")
    assert stub.calls == []
    assert exc_info.value.rule == "invalid_report_format"


def test_get_report_missing_destination_parent_raises_without_call(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError):
        service.get_report("t-1", "run-1", "pdf", tmp_path / "no-such-dir" / "report.pdf")
    assert stub.calls == []


def test_get_report_blank_target_id_raises_without_call(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError):
        service.get_report(" ", "run-1", "pdf", tmp_path / "report.pdf")
    assert stub.calls == []


def test_get_report_blank_analysis_run_id_raises_without_call(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(AnalysisRunValidationError):
        service.get_report("t-1", "", "pdf", tmp_path / "report.pdf")
    assert stub.calls == []


def test_get_report_not_found_propagates(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="GET", url="x", status_code=404))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.get_report("t-1", "run-1", "pdf", tmp_path / "report.pdf")


def test_no_log_record_contains_report_bytes(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, b"top-secret-finding-details", {}))
    service = AnalysisRunsService(stub)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        service.get_report("t-1", "run-1", "pdf", tmp_path / "report.pdf")

    for record in caplog.records:
        assert "top-secret-finding-details" not in record.getMessage()
