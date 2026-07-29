from veracode_dast.models.scanner import Scanner, ScannerProfile, ScannerType


def test_scanner_type_has_35_members() -> None:
    assert len(list(ScannerType)) == 35


def test_scanner_from_api_maps_field_names() -> None:
    scanner = Scanner.from_api(
        {"id": "sql_injection", "effective_value": True, "is_inherited": False, "is_editable": True}
    )
    assert scanner == Scanner(id="sql_injection", enabled=True, inherited=False, editable=True)


def test_scanner_profile_constructs_with_only_scanners() -> None:
    profile = ScannerProfile(
        scanners=[Scanner(id="xss", enabled=True, inherited=False, editable=True)]
    )
    assert profile.analysis_profile_id is None
    assert profile.parent_analysis_profile_id is None


def test_scanner_profile_from_api() -> None:
    data = {
        "analysis_profile_id": "ap-1",
        "parent_analysis_profile_id": "ap-parent",
        "scanners": [
            {"id": "xss", "effective_value": True, "is_inherited": False, "is_editable": True},
            {"id": "csrf", "effective_value": False, "is_inherited": True, "is_editable": False},
        ],
    }
    profile = ScannerProfile.from_api(data)
    assert profile.analysis_profile_id == "ap-1"
    assert profile.parent_analysis_profile_id == "ap-parent"
    assert len(profile.scanners) == 2
    assert profile.scanners[0].id == "xss"
