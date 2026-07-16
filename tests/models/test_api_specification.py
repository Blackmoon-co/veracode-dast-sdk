from veracode_dast.models.api_specification import (
    ApiSpecification,
    ScopeRule,
    ScopeRuleType,
    ScopeType,
)


def test_scope_rule_from_api() -> None:
    rule = ScopeRule.from_api(
        {
            "uuid": "u-1",
            "http_method": "GET",
            "url": "/foo",
            "scope_type": "AUDIT",
            "scope_rule_type": "PATTERN",
            "scope_rule_index": 0,
        }
    )

    assert rule == ScopeRule(
        uuid="u-1",
        http_method="GET",
        url="/foo",
        scope_type=ScopeType.AUDIT,
        scope_rule_type=ScopeRuleType.PATTERN,
        scope_rule_index=0,
    )


def test_api_specification_from_api_round_trips() -> None:
    data = {
        "target_id": "t-1",
        "api_spec_s3_id": "s3-1",
        "api_spec_name": "openapi.yaml",
        "uploaded_at": "2024-01-01T00:00:00Z",
        "scope_rules": [
            {
                "uuid": "u-1",
                "http_method": "GET",
                "url": "/foo",
                "scope_type": "AUDIT",
                "scope_rule_type": "PATTERN",
                "scope_rule_index": 0,
            }
        ],
    }

    spec = ApiSpecification.from_api(data, target_id="t-1")

    assert spec.target_id == "t-1"
    assert spec.api_spec_name == "openapi.yaml"
    assert len(spec.scope_rules) == 1


def test_api_specification_from_api_falls_back_to_supplied_target_id() -> None:
    spec = ApiSpecification.from_api({}, target_id="t-2")

    assert spec.target_id == "t-2"
    assert spec.api_spec_name is None
    assert spec.scope_rules == []
