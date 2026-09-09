from veracode_dast.models.application import Application, ApplicationPage


def test_application_from_api_reads_all_fields() -> None:
    data = {
        "guid": "60e630b1-4ab7-4415-b920-5dd30b2e3a45",
        "id": "123456",
        "name": "My App",
        "linked_scan_target_url": "https://api.example.com",
    }

    application = Application.from_api(data)

    assert application == Application(
        guid="60e630b1-4ab7-4415-b920-5dd30b2e3a45",
        id="123456",
        name="My App",
        linked_scan_target_url="https://api.example.com",
    )


def test_application_from_api_optional_url_absent() -> None:
    data = {"guid": "g-1", "id": "1", "name": "My App"}

    application = Application.from_api(data)

    assert application.linked_scan_target_url is None


def test_application_page_from_api_round_trips() -> None:
    data = {
        "_embedded": {
            "Applications": [
                {"guid": "g-1", "id": "1", "name": "Alpha"},
                {"guid": "g-2", "id": "2", "name": "Beta"},
            ]
        },
        "page": {"size": 10, "total_elements": 2, "total_pages": 1, "number": 0},
    }

    page = ApplicationPage.from_api(data)

    assert page == ApplicationPage(
        items=[
            Application(guid="g-1", id="1", name="Alpha"),
            Application(guid="g-2", id="2", name="Beta"),
        ],
        page_number=0,
        page_size=10,
        total_pages=1,
        total_elements=2,
    )


def test_application_page_from_api_missing_embedded_yields_empty_items() -> None:
    data = {"page": {"size": 10, "total_elements": 0, "total_pages": 1, "number": 0}}

    page = ApplicationPage.from_api(data)

    assert page.items == []
