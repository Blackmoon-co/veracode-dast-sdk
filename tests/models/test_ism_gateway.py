from veracode_dast.models.ism_gateway import ISMEndpoint, ISMGateway


def test_ism_endpoint_from_api() -> None:
    endpoint = ISMEndpoint.from_api({"token": "tok-1", "name": "ep-1", "status": "ONLINE"})
    assert endpoint == ISMEndpoint(token="tok-1", name="ep-1", status="ONLINE")


def test_ism_gateway_from_api_maps_ref_id_to_id() -> None:
    gateway = ISMGateway.from_api(
        {
            "refId": "gateway-id",
            "name": "Corporate Gateway",
            "hostname": "gw.example.com",
            "status": "ONLINE",
            "endpoints": [{"token": "tok-1", "name": "ep-1", "status": "ONLINE"}],
        }
    )
    assert gateway.id == "gateway-id"
    assert len(gateway.endpoints) == 1


def test_readme_returned_model_construction() -> None:
    gateway = ISMGateway(id="gateway-id", name="Corporate Gateway", status="ONLINE")
    assert gateway.hostname is None
    assert gateway.endpoints == []
