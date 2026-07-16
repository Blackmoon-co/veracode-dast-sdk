from veracode_dast.models.target import (
    Protocol,
    ScanType,
    Target,
    TargetCreate,
    TargetPage,
    TargetType,
    TargetUpdate,
)


def _target_api_fixture(**overrides: object) -> dict[str, object]:
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


def test_target_from_api_round_trips_required_fields() -> None:
    target = Target.from_api(_target_api_fixture())

    assert target.target_id == "t-1"
    assert target.protocol == Protocol.HTTPS
    assert target.target_type == TargetType.WEB_APP
    assert target.scan_type == ScanType.QUICK
    assert target.teams == ["1"]
    assert target.description is None
    assert target.status is None


def test_target_from_api_reads_optional_fields() -> None:
    target = Target.from_api(
        _target_api_fixture(
            description="Example description.",
            application_uuid="550e8400-e29b-41d4-a716-446655440000",
            application_id=123,
            status="RUNNING",
        )
    )

    assert target.description == "Example description."
    assert target.application_id == 123
    assert target.status is not None
    assert target.status.value == "RUNNING"


def test_target_create_to_api_omits_unset_optional_fields() -> None:
    create = TargetCreate(
        name="My Target",
        url="sub.domain.tld",
        protocol=Protocol.HTTPS,
        target_type=TargetType.WEB_APP,
        scan_type=ScanType.QUICK,
        authorized_to_scan=True,
        is_sec_lead_only=False,
        teams=["1"],
    )

    body = create.to_api()

    assert body == {
        "name": "My Target",
        "url": "sub.domain.tld",
        "protocol": "HTTPS",
        "target_type": "WEB_APP",
        "scan_type": "QUICK",
        "authorized_to_scan": True,
        "is_sec_lead_only": False,
        "teams": ["1"],
    }
    assert "description" not in body
    assert "api_specification_file_url" not in body


def test_target_update_to_api_only_includes_explicitly_set_fields() -> None:
    update = TargetUpdate(name="New Name", teams=None)

    body = update.to_api()

    assert body == {"name": "New Name", "teams": None}
    assert "url" not in body
    assert "protocol" not in body


def test_target_page_from_api_round_trips_and_hides_links() -> None:
    data = {
        "_embedded": {"targets": [_target_api_fixture()]},
        "_links": {"self": {"href": "https://example.com"}},
        "page": {"size": 10, "total_elements": 1, "total_pages": 1, "number": 0},
    }

    page = TargetPage.from_api(data)

    assert len(page.items) == 1
    assert page.total_elements == 1
    assert not hasattr(page, "_links")
