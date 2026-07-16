"""Typed models for the DAST Target Configuration Service's API Specification
resource."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ScopeType(StrEnum):
    """How a scope rule affects scanning."""

    AUDIT = "AUDIT"
    BLOCK = "BLOCK"
    IGNORE = "IGNORE"


class ScopeRuleType(StrEnum):
    """How a scope rule matches requests."""

    PATTERN = "PATTERN"
    INDEX = "INDEX"


@dataclass(frozen=True)
class ScopeRule:
    """An Enterprise-mode API scan scope rule.

    Attributes:
        uuid: The scope rule's unique identifier.
        http_method: The HTTP method the rule applies to.
        url: The URL (or pattern) the rule applies to.
        scope_type: How this rule affects scanning.
        scope_rule_type: How this rule matches requests.
        scope_rule_index: The rule's position in the scope rule list.
    """

    uuid: str
    http_method: str
    url: str
    scope_type: ScopeType
    scope_rule_type: ScopeRuleType
    scope_rule_index: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ScopeRule:
        """Builds a `ScopeRule` from an API response object.

        Args:
            data: The raw scope rule object from the API response.

        Returns:
            The corresponding `ScopeRule`.
        """
        return cls(
            uuid=data["uuid"],
            http_method=data["http_method"],
            url=data["url"],
            scope_type=ScopeType(data["scope_type"]),
            scope_rule_type=ScopeRuleType(data["scope_rule_type"]),
            scope_rule_index=data["scope_rule_index"],
        )


@dataclass(frozen=True)
class ApiSpecification:
    """Metadata for a Target's uploaded API Specification.

    Every field besides `target_id` defaults to `None`/`[]`: the upstream
    OpenAPI schema for this resource is internally inconsistent (it lists a
    required `specId` field that is never defined), so no field beyond
    `target_id` — which this SDK always supplies from the caller regardless
    of what the response contains — is assumed present.

    Attributes:
        target_id: ID of the target this specification belongs to.
        api_spec_s3_id: The specification's identifier on S3.
        api_spec_name: The specification's name.
        api_spec_url: The specification URL provided by the client, if any.
        api_spec_type: The specification's type.
        analysis_run_id: ID of the analysis run, if any.
        uploaded_at: When the specification was uploaded (UTC datetime string).
        updated_at: When the specification was last updated (UTC datetime string).
        uploaded_by: Principal who uploaded the specification.
        updated_by: Principal who last modified the specification.
        scope_rules: Enterprise-mode API scan scope rules.
    """

    target_id: str
    api_spec_s3_id: str | None = None
    api_spec_name: str | None = None
    api_spec_url: str | None = None
    api_spec_type: str | None = None
    analysis_run_id: str | None = None
    uploaded_at: str | None = None
    updated_at: str | None = None
    uploaded_by: str | None = None
    updated_by: str | None = None
    scope_rules: list[ScopeRule] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any], *, target_id: str) -> ApiSpecification:
        """Builds an `ApiSpecification` from an API response.

        Args:
            data: The raw response body.
            target_id: The target ID to use if the response omits one.

        Returns:
            The corresponding `ApiSpecification`.
        """
        return cls(
            target_id=data.get("target_id", target_id),
            api_spec_s3_id=data.get("api_spec_s3_id"),
            api_spec_name=data.get("api_spec_name"),
            api_spec_url=data.get("api_spec_url"),
            api_spec_type=data.get("api_spec_type"),
            analysis_run_id=data.get("analysis_run_id"),
            uploaded_at=data.get("uploaded_at"),
            updated_at=data.get("updated_at"),
            uploaded_by=data.get("uploaded_by"),
            updated_by=data.get("updated_by"),
            scope_rules=[ScopeRule.from_api(rule) for rule in data.get("scope_rules") or []],
        )
