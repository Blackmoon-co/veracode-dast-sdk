from veracode_dast.models.analysis_profile import (
    AnalysisProfile,
    AnalysisProfilePage,
    AnalysisProfileSummary,
    AnalysisProfileUpdate,
    CrawlerMode,
    DirectoryRestrictions,
)
from veracode_dast.models.api_specification import ScopeRule, ScopeRuleType, ScopeType
from veracode_dast.models.common import InheritedValue


def _profile_fixture(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "analysis_profile_id": "ap-1",
        "parent_analysis_profile_id": "ap-parent",
        "name": "Production",
        "mode": "STANDARD",
        "allowed_urls": {"effective_value": ["https://example.com"], "is_inherited": False},
        "denied_urls": {"effective_value": [], "is_inherited": True},
        "seed_urls": {"effective_value": ["https://example.com"], "is_inherited": False},
        "grouped_urls": {"effective_value": [], "is_inherited": True},
        "crawler_enabled": {"effective_value": True, "is_inherited": False},
        "crawler_mode": {"effective_value": "SMART", "is_inherited": False},
        "rate_limit": {"effective_value": 300, "is_inherited": False},
        "max_duration": {"effective_value": 120, "is_inherited": True},
        "max_crawl_duration": {"effective_value": 60, "is_inherited": True},
    }
    data.update(overrides)
    return data


def test_inherited_value_from_api_list_and_bool_fields() -> None:
    profile = AnalysisProfile.from_api(_profile_fixture())
    assert profile.allowed_urls == InheritedValue(
        effective_value=["https://example.com"], is_inherited=False
    )
    assert profile.crawler_enabled == InheritedValue(effective_value=True, is_inherited=False)


def test_analysis_profile_from_api_with_api_spec() -> None:
    data = _profile_fixture(
        target_id="t-1",
        api_spec={
            "api_spec_s3_id": "s3-1",
            "api_spec_name": "spec.yaml",
        },
    )
    profile = AnalysisProfile.from_api(data)

    assert profile.analysis_profile_id == "ap-1"
    assert profile.mode.value == "STANDARD"
    assert profile.crawler_mode.effective_value == CrawlerMode.SMART
    assert profile.api_spec is not None
    assert profile.api_spec.target_id == "t-1"
    assert profile.api_spec.api_spec_name == "spec.yaml"


def test_analysis_profile_from_api_optional_fields_absent() -> None:
    profile = AnalysisProfile.from_api(_profile_fixture())
    assert profile.target_id is None
    assert profile.max_browsers is None
    assert profile.api_spec is None
    assert profile.similarity_threshold is None
    assert profile.directory_restrictions is None
    assert profile.enable_all_target_protocols is None


def test_analysis_profile_directory_restrictions_null_effective_value() -> None:
    data = _profile_fixture(directory_restrictions={"effective_value": None, "is_inherited": True})
    profile = AnalysisProfile.from_api(data)
    assert profile.directory_restrictions is not None
    assert profile.directory_restrictions.effective_value is None


def test_analysis_profile_directory_restrictions_set() -> None:
    data = _profile_fixture(
        directory_restrictions={"effective_value": "DIR_ONLY", "is_inherited": False}
    )
    profile = AnalysisProfile.from_api(data)
    assert profile.directory_restrictions is not None
    assert profile.directory_restrictions.effective_value == DirectoryRestrictions.DIR_ONLY


def test_analysis_profile_summary_from_api() -> None:
    summary = AnalysisProfileSummary.from_api({"analysis_profile_id": "ap-1", "name": "Production"})
    assert summary.target_id is None


def test_analysis_profile_update_to_api_unset_fields_absent() -> None:
    update = AnalysisProfileUpdate(rate_limit=300)
    assert update.to_api() == {"rate_limit": 300}


def test_analysis_profile_update_explicit_none() -> None:
    update = AnalysisProfileUpdate(allowed_urls=None)
    assert update.to_api() == {"allowed_urls": None}


def test_analysis_profile_update_scope_rules_serialize() -> None:
    rule = ScopeRule(
        uuid="rule-1",
        http_method="GET",
        url="/api/*",
        scope_type=ScopeType.AUDIT,
        scope_rule_type=ScopeRuleType.PATTERN,
        scope_rule_index=0,
    )
    update = AnalysisProfileUpdate(scope_rules=[rule])
    assert update.to_api() == {
        "scope_rules": [
            {
                "uuid": "rule-1",
                "http_method": "GET",
                "url": "/api/*",
                "scope_type": "AUDIT",
                "scope_rule_type": "PATTERN",
                "scope_rule_index": 0,
            }
        ]
    }


def test_analysis_profile_page_from_api_and_iteration() -> None:
    data = {
        "_embedded": {
            "analysis_profiles": [
                {"analysis_profile_id": "ap-1", "name": "Production"},
                {"analysis_profile_id": "ap-2", "name": "Staging", "target_id": "t-2"},
            ]
        },
        "page": {"number": 0, "size": 10, "total_pages": 1, "total_elements": 2},
    }
    page = AnalysisProfilePage.from_api(data)

    assert list(page) == page.items
    assert not hasattr(page, "_links")
