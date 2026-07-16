import logging
from pathlib import Path
from typing import Any

import pytest

from veracode_dast.client import HttpResponse
from veracode_dast.exceptions import (
    ApiSpecificationFileNotFoundError,
    ApiSpecificationValidationError,
    VeracodeApiError,
    VeracodeNotFoundError,
)
from veracode_dast.services.api_specifications import ApiSpecificationsService


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


def test_upload_blank_target_id_raises_without_call(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]
    spec_file = tmp_path / "openapi.yaml"
    spec_file.write_text("openapi: 3.0.0")

    with pytest.raises(ApiSpecificationValidationError):
        service.upload("  ", spec_file)
    assert stub.calls == []


def test_upload_missing_file_raises_without_call(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(ApiSpecificationFileNotFoundError):
        service.upload("t-1", tmp_path / "missing.yaml")
    assert stub.calls == []


def test_upload_sends_multipart_specfile(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, {"target_id": "t-1", "api_spec_name": "openapi.yaml"}, {}))
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]
    spec_file = tmp_path / "openapi.yaml"
    spec_file.write_text("openapi: 3.0.0")

    spec = service.upload("t-1", spec_file)

    assert spec.api_spec_name == "openapi.yaml"
    call = stub.calls[0]
    assert call["path"] == "/targets/t-1/spec"
    filename, content, _content_type = call["files"]["specFile"]
    assert filename == "openapi.yaml"
    assert content == b"openapi: 3.0.0"


def test_upload_server_rejection_propagates_unmodified(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeApiError("bad spec", method="POST", url="x", status_code=400))
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]
    spec_file = tmp_path / "openapi.yaml"
    spec_file.write_text("not a real spec")

    with pytest.raises(VeracodeApiError):
        service.upload("t-1", spec_file)


def test_get_blank_target_id_raises() -> None:
    stub = _StubHttpClient()
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(ApiSpecificationValidationError):
        service.get("")
    assert stub.calls == []


def test_get_success() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, {"target_id": "t-1", "api_spec_name": "openapi.yaml"}, {}))
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]

    spec = service.get("t-1")

    assert spec.api_spec_name == "openapi.yaml"
    assert stub.calls[0]["path"] == "/targets/t-1/spec"


def test_get_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="GET", url="x", status_code=404))
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.get("t-1")


def test_download_blank_target_id_raises() -> None:
    stub = _StubHttpClient()
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(ApiSpecificationValidationError):
        service.download(" ", "/tmp/whatever.yaml")
    assert stub.calls == []


def test_download_missing_destination_parent_raises(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(ApiSpecificationValidationError):
        service.download("t-1", tmp_path / "no-such-dir" / "out.yaml")
    assert stub.calls == []


def test_download_writes_bytes_to_destination(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, b"openapi: 3.0.0", {}))
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]
    destination = tmp_path / "downloaded.yaml"

    result = service.download("t-1", destination)

    assert result == destination
    assert destination.read_bytes() == b"openapi: 3.0.0"


def test_download_not_found_propagates(tmp_path: Path) -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="GET", url="x", status_code=404))
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.download("t-1", tmp_path / "out.yaml")


def test_no_log_record_contains_file_contents(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, {"target_id": "t-1", "api_spec_name": "openapi.yaml"}, {}))
    service = ApiSpecificationsService(stub)  # type: ignore[arg-type]
    spec_file = tmp_path / "openapi.yaml"
    spec_file.write_text("top-secret-spec-content: true")

    with caplog.at_level(logging.INFO):
        service.upload("t-1", spec_file)

    for record in caplog.records:
        assert "top-secret-spec-content" not in record.getMessage()
