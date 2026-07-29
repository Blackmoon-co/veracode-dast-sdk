from veracode_dast.models.scanner_variable import ScannerVariable, ScannerVariables


def test_from_api_totp_seed_true() -> None:
    variable = ScannerVariable.from_api(
        {
            "effective_value": {
                "id": "sv-1",
                "reference_key": "otp",
                "value": "ABCDEFGHIJKLMNOP",
                "evaluation_mode": "TOTP",
            },
            "is_inherited": False,
        }
    )
    assert variable.totp_seed is True
    assert variable.is_inherited is False
    assert variable.id == "sv-1"


def test_from_api_evaluation_mode_absent_defaults_to_raw() -> None:
    variable = ScannerVariable.from_api(
        {"effective_value": {"reference_key": "username", "value": "admin"}, "is_inherited": True}
    )
    assert variable.totp_seed is False
    assert variable.id is None


def test_to_api_maps_totp_seed_to_evaluation_mode() -> None:
    assert ScannerVariable(reference_key="otp", value="x", totp_seed=True).to_api() == {
        "reference_key": "otp",
        "value": "x",
        "evaluation_mode": "TOTP",
    }
    assert ScannerVariable(reference_key="username", value="admin", totp_seed=False).to_api() == {
        "reference_key": "username",
        "value": "admin",
        "evaluation_mode": "RAW",
    }


def test_to_api_never_includes_id() -> None:
    variable = ScannerVariable(reference_key="username", value="admin", id="sv-1")
    assert "id" not in variable.to_api()


def test_readme_returned_model_construction() -> None:
    variable = ScannerVariable(reference_key="username", value="admin", totp_seed=False)
    assert variable.is_inherited is False
    assert variable.id is None


def test_scanner_variables_from_api_is_a_bare_array() -> None:
    data = [
        {"effective_value": {"reference_key": "username", "value": "admin"}, "is_inherited": False},
    ]
    result = ScannerVariables.from_api(data)
    assert len(result.variables) == 1
