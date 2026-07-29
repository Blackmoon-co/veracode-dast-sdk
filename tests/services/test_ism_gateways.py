import logging
from typing import Any

import pytest

from veracode_dast.client import HttpResponse
from veracode_dast.exceptions import (
    GatewayNameNotUniqueError,
    GatewayNotFoundError,
    IsmGatewayValidationError,
    VeracodeNotFoundError,
)
from veracode_dast.models.ism_gateway import ISMEndpoint, ISMGateway
from veracode_dast.services.ism_gateways import (
    IsmGatewaysService,
    _build_target_ism_gateway_payload,
    _extract_gateway_name_from_config,
    _resolve_gateway_by_name,
    _select_endpoint,
)


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


def _gateways_response(gateways: list[dict[str, object]]) -> HttpResponse:
    return HttpResponse(200, gateways, {})


def _gateway_fixture(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "refId": "gw-1",
        "name": "Corporate Gateway",
        "status": "ONLINE",
        "endpoints": [{"token": "tok-1", "name": "ep-1", "status": "ONLINE"}],
    }
    data.update(overrides)
    return data


# --- Gateway Resolver ---


def test_resolve_gateway_by_name_exact_match() -> None:
    gateway = ISMGateway(id="gw-1", name="Corporate Gateway")
    assert _resolve_gateway_by_name("Corporate Gateway", [gateway]) is gateway


def test_resolve_gateway_by_name_not_found_with_suggestion() -> None:
    gateway = ISMGateway(id="gw-1", name="Corporate Gateway")
    with pytest.raises(GatewayNotFoundError) as exc_info:
        _resolve_gateway_by_name("Corprate Gateway", [gateway])
    assert "Did you mean 'Corporate Gateway'?" in str(exc_info.value)


def test_resolve_gateway_by_name_ambiguous() -> None:
    gateways = [ISMGateway(id="gw-1", name="Dup"), ISMGateway(id="gw-2", name="Dup")]
    with pytest.raises(GatewayNameNotUniqueError) as exc_info:
        _resolve_gateway_by_name("Dup", gateways)
    assert exc_info.value.matches == ["gw-1", "gw-2"]


def test_select_endpoint_exactly_one() -> None:
    endpoint = ISMEndpoint(token="tok-1")
    gateway = ISMGateway(id="gw-1", name="G", endpoints=[endpoint])
    assert _select_endpoint(gateway) is endpoint


def test_select_endpoint_zero_raises() -> None:
    gateway = ISMGateway(id="gw-1", name="G", endpoints=[])
    with pytest.raises(IsmGatewayValidationError) as exc_info:
        _select_endpoint(gateway)
    assert exc_info.value.rule == "gateway_has_no_endpoint"


def test_select_endpoint_multiple_raises() -> None:
    gateway = ISMGateway(
        id="gw-1", name="G", endpoints=[ISMEndpoint(token="a"), ISMEndpoint(token="b")]
    )
    with pytest.raises(IsmGatewayValidationError) as exc_info:
        _select_endpoint(gateway)
    assert exc_info.value.rule == "gateway_endpoint_ambiguous"


def test_extract_gateway_name_from_config_valid() -> None:
    assert _extract_gateway_name_from_config({"gateway": {"name": "Corporate Gateway"}}) == (
        "Corporate Gateway"
    )


@pytest.mark.parametrize(
    ("config", "rule"),
    [
        (["not", "a", "dict"], "config_must_be_object"),
        ({}, "gateway_key_required"),
        ({"gateway": {}}, "gateway_name_required"),
        ({"gateway": {"name": "  "}}, "gateway_name_required"),
    ],
)
def test_extract_gateway_name_from_config_failures(config: Any, rule: str) -> None:
    with pytest.raises(IsmGatewayValidationError) as exc_info:
        _extract_gateway_name_from_config(config)
    assert exc_info.value.rule == rule


def test_build_target_ism_gateway_payload() -> None:
    gateway = ISMGateway(id="gw-1", name="G")
    endpoint = ISMEndpoint(token="tok-1")
    assert _build_target_ism_gateway_payload(gateway, endpoint) == {
        "gatewayUuid": "gw-1",
        "endpointUuid": "tok-1",
    }


# --- IsmGatewaysService ---


def test_list_returns_gateways() -> None:
    stub = _StubHttpClient()
    stub.queue(_gateways_response([_gateway_fixture()]))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    gateways = service.list()

    assert len(gateways) == 1
    assert gateways[0].id == "gw-1"


def test_get_blank_id_raises_without_http_call() -> None:
    stub = _StubHttpClient()
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(IsmGatewayValidationError):
        service.get(" ")
    assert stub.calls == []


def test_get_unassigned_target_returns_none() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, {}, {}))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    assert service.get("t-1") is None


def test_get_assigned_target_returns_matching_gateway() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, {"gatewayUuid": "gw-1", "endpointUuid": "tok-1"}, {}))
    stub.queue(_gateways_response([_gateway_fixture()]))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    gateway = service.get("t-1")

    assert gateway is not None
    assert gateway.id == "gw-1"
    assert len(stub.calls) == 2


def test_get_gateway_uuid_with_no_list_match_raises() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, {"gatewayUuid": "unknown-gw"}, {}))
    stub.queue(_gateways_response([_gateway_fixture()]))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(IsmGatewayValidationError) as exc_info:
        service.get("t-1")
    assert exc_info.value.rule == "gateway_not_found_by_id"


def test_update_blank_id_raises_without_http_call() -> None:
    stub = _StubHttpClient()
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(IsmGatewayValidationError):
        service.update(" ", gateway_name="Corporate Gateway")
    assert stub.calls == []


def test_update_neither_gateway_name_nor_config_file_raises() -> None:
    stub = _StubHttpClient()
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(IsmGatewayValidationError) as exc_info:
        service.update("t-1")
    assert exc_info.value.rule == "gateway_name_or_config_file_required"
    assert stub.calls == []


def test_update_both_gateway_name_and_config_file_raises() -> None:
    stub = _StubHttpClient()
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(IsmGatewayValidationError) as exc_info:
        service.update(
            "t-1", gateway_name="Corporate Gateway", config_file={"gateway": {"name": "x"}}
        )
    assert exc_info.value.rule == "gateway_name_or_config_file_required"
    assert stub.calls == []


def test_update_by_gateway_name_success() -> None:
    stub = _StubHttpClient()
    stub.queue(_gateways_response([_gateway_fixture()]))
    stub.queue(HttpResponse(200, {"gatewayUuid": "gw-1", "endpointUuid": "tok-1"}, {}))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    gateway = service.update("t-1", gateway_name="Corporate Gateway")

    assert gateway.id == "gw-1"
    put_call = stub.calls[-1]
    assert put_call["path"] == "/ism_gateways/targets/t-1"
    assert put_call["json"] == {"gatewayUuid": "gw-1", "endpointUuid": "tok-1"}


def test_update_by_config_file_matches_gateway_name_call() -> None:
    stub_a = _StubHttpClient()
    stub_a.queue(_gateways_response([_gateway_fixture()]))
    stub_a.queue(HttpResponse(200, {}, {}))
    IsmGatewaysService(stub_a).update(  # type: ignore[arg-type]
        "t-1", config_file={"gateway": {"name": "Corporate Gateway"}}
    )

    stub_b = _StubHttpClient()
    stub_b.queue(_gateways_response([_gateway_fixture()]))
    stub_b.queue(HttpResponse(200, {}, {}))
    IsmGatewaysService(stub_b).update("t-1", gateway_name="Corporate Gateway")  # type: ignore[arg-type]

    assert stub_a.calls[-1]["json"] == stub_b.calls[-1]["json"]


def test_update_unresolvable_name_no_put_call() -> None:
    stub = _StubHttpClient()
    stub.queue(_gateways_response([_gateway_fixture()]))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(GatewayNotFoundError):
        service.update("t-1", gateway_name="Unknown Gateway")
    assert all(call["verb"] != "PUT" for call in stub.calls)


def test_update_ambiguous_name_no_put_call() -> None:
    stub = _StubHttpClient()
    stub.queue(_gateways_response([_gateway_fixture(refId="gw-1"), _gateway_fixture(refId="gw-2")]))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(GatewayNameNotUniqueError):
        service.update("t-1", gateway_name="Corporate Gateway")
    assert all(call["verb"] != "PUT" for call in stub.calls)


def test_update_endpoint_ambiguous_no_put_call() -> None:
    stub = _StubHttpClient()
    stub.queue(_gateways_response([_gateway_fixture(endpoints=[{"token": "a"}, {"token": "b"}])]))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(IsmGatewayValidationError):
        service.update("t-1", gateway_name="Corporate Gateway")
    assert all(call["verb"] != "PUT" for call in stub.calls)


def test_update_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.queue(_gateways_response([_gateway_fixture()]))
    stub.raise_next(VeracodeNotFoundError("nope", method="PUT", url="x", status_code=404))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.update("missing", gateway_name="Corporate Gateway")


def test_remove_blank_id_raises_without_http_call() -> None:
    stub = _StubHttpClient()
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(IsmGatewayValidationError):
        service.remove(" ")
    assert stub.calls == []


def test_remove_success_sends_empty_body() -> None:
    stub = _StubHttpClient()
    stub.queue(HttpResponse(200, {}, {}))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    assert service.remove("t-1") is None
    assert stub.calls[0]["json"] == {}


def test_remove_not_found_propagates() -> None:
    stub = _StubHttpClient()
    stub.raise_next(VeracodeNotFoundError("nope", method="PUT", url="x", status_code=404))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with pytest.raises(VeracodeNotFoundError):
        service.remove("missing")


def test_no_log_record_contains_token(caplog: pytest.LogCaptureFixture) -> None:
    stub = _StubHttpClient()
    stub.queue(_gateways_response([_gateway_fixture(endpoints=[{"token": "top-secret-token"}])]))
    stub.queue(HttpResponse(200, {}, {}))
    service = IsmGatewaysService(stub)  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO):
        service.update("t-1", gateway_name="Corporate Gateway")

    for record in caplog.records:
        assert "top-secret-token" not in record.getMessage()
