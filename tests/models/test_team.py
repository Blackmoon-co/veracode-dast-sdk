from veracode_dast.models.team import Team, TeamPage


def test_team_from_api_reads_only_known_fields() -> None:
    data = {
        "team_id": "abc-123",
        "team_name": "Development",
        "business_unit": {"bu_id": "x", "bu_name": "y"},
        "organization": {"org_id": "z"},
        "member_only": False,
    }

    team = Team.from_api(data)

    assert team == Team(team_id="abc-123", team_name="Development")


def test_team_page_from_api_round_trips() -> None:
    data = {
        "_embedded": {
            "teams": [
                {"team_id": "1", "team_name": "Alpha"},
                {"team_id": "2", "team_name": "Beta"},
            ]
        },
        "page": {"size": 20, "total_elements": 2, "total_pages": 1, "number": 0},
    }

    page = TeamPage.from_api(data)

    assert page == TeamPage(
        items=[Team(team_id="1", team_name="Alpha"), Team(team_id="2", team_name="Beta")],
        page_number=0,
        page_size=20,
        total_pages=1,
        total_elements=2,
    )
