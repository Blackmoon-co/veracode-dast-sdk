"""Typed models for the DAST Target Configuration Service's Analysis
Profiles resource."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from veracode_dast.models.api_specification import ApiSpecification
from veracode_dast.models.common import InheritedValue


class AnalysisProfileType(StrEnum):
    """The kind of Analysis Profile."""

    TARGET = "TARGET"
    ORG = "ORG"
    SYSTEM = "SYSTEM"


class AnalysisProfileMode(StrEnum):
    """Whether Enterprise-mode features are enabled for a profile."""

    STANDARD = "STANDARD"
    ENTERPRISE = "ENTERPRISE"


class CrawlerMode(StrEnum):
    """How thoroughly the crawler explores a target."""

    SMART = "SMART"
    EXHAUSTIVE = "EXHAUSTIVE"


class DirectoryRestrictions(StrEnum):
    """How strictly crawling is confined to the seed URL's directory."""

    DIR_AND_SUBDIR = "DIR_AND_SUBDIR"
    DIR_ONLY = "DIR_ONLY"
    NO_RESTRICTIONS = "NO_RESTRICTIONS"


_UNSET: Final = object()


@dataclass(frozen=True)
class AnalysisProfile:
    """A Veracode DAST Analysis Profile, as returned by the REST API.

    Fields wrapped in `InheritedValue` may be inherited from
    `parent_analysis_profile_id` — check `is_inherited` before assuming a
    value was set directly on this profile.

    Attributes:
        analysis_profile_id: The profile's unique identifier.
        parent_analysis_profile_id: The parent profile this one inherits
            unset values from.
        name: The profile's display name (read-only — set implicitly when
            the underlying Target is created).
        mode: Whether Enterprise-mode features are enabled.
        allowed_urls: URLs the crawler is allowed to visit.
        denied_urls: URLs the crawler must not visit.
        seed_urls: URLs the crawler starts from.
        grouped_urls: URL groups treated as equivalent during crawling.
        crawler_enabled: Whether the crawler runs during scans.
        crawler_mode: How thoroughly the crawler explores the target.
        rate_limit: Maximum requests per second sent during scanning.
        max_duration: Maximum scan duration, in minutes.
        max_crawl_duration: Maximum crawl duration, in minutes.
        target_id: The Target this profile belongs to, if this is a
            TARGET-level profile.
        max_browsers: Maximum concurrent browsers during a scan, if set.
        api_spec: The API specification associated with this profile, if any.
        similarity_threshold: How alike two pages must be to be deduplicated.
        directory_restrictions: How strictly crawling stays within the
            seed URL's directory, if set.
        enable_all_target_protocols: Whether all of the target's protocols
            are scanned, if set.
    """

    analysis_profile_id: str
    parent_analysis_profile_id: str
    name: str
    mode: AnalysisProfileMode
    allowed_urls: InheritedValue[list[str]]
    denied_urls: InheritedValue[list[str]]
    seed_urls: InheritedValue[list[str]]
    grouped_urls: InheritedValue[list[str]]
    crawler_enabled: InheritedValue[bool]
    crawler_mode: InheritedValue[CrawlerMode]
    rate_limit: InheritedValue[int]
    max_duration: InheritedValue[int]
    max_crawl_duration: InheritedValue[int]
    target_id: str | None = None
    max_browsers: InheritedValue[int] | None = None
    api_spec: ApiSpecification | None = None
    similarity_threshold: InheritedValue[float] | None = None
    directory_restrictions: InheritedValue[DirectoryRestrictions | None] | None = None
    enable_all_target_protocols: InheritedValue[bool] | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AnalysisProfile:
        """Builds an `AnalysisProfile` from a Target Configuration Service
        response.

        Args:
            data: The raw analysis profile object from the API response.

        Returns:
            The corresponding `AnalysisProfile`.
        """
        target_id = data.get("target_id")

        max_browsers = data.get("max_browsers")
        similarity_threshold = data.get("similarity_threshold")
        directory_restrictions = data.get("directory_restrictions")
        enable_all_target_protocols = data.get("enable_all_target_protocols")
        api_spec = data.get("api_spec")
        crawler_mode = data["crawler_mode"]

        return cls(
            analysis_profile_id=data["analysis_profile_id"],
            parent_analysis_profile_id=data["parent_analysis_profile_id"],
            name=data["name"],
            mode=AnalysisProfileMode(data["mode"]),
            allowed_urls=InheritedValue.from_api(data["allowed_urls"]),
            denied_urls=InheritedValue.from_api(data["denied_urls"]),
            seed_urls=InheritedValue.from_api(data["seed_urls"]),
            grouped_urls=InheritedValue.from_api(data["grouped_urls"]),
            crawler_enabled=InheritedValue.from_api(data["crawler_enabled"]),
            crawler_mode=InheritedValue(
                effective_value=CrawlerMode(crawler_mode["effective_value"]),
                is_inherited=crawler_mode["is_inherited"],
            ),
            rate_limit=InheritedValue.from_api(data["rate_limit"]),
            max_duration=InheritedValue.from_api(data["max_duration"]),
            max_crawl_duration=InheritedValue.from_api(data["max_crawl_duration"]),
            target_id=target_id,
            max_browsers=InheritedValue.from_api(max_browsers)
            if max_browsers is not None
            else None,
            api_spec=ApiSpecification.from_api(api_spec, target_id=target_id or "")
            if api_spec is not None
            else None,
            similarity_threshold=InheritedValue.from_api(similarity_threshold)
            if similarity_threshold is not None
            else None,
            directory_restrictions=InheritedValue(
                effective_value=DirectoryRestrictions(directory_restrictions["effective_value"])
                if directory_restrictions["effective_value"] is not None
                else None,
                is_inherited=directory_restrictions["is_inherited"],
            )
            if directory_restrictions is not None
            else None,
            enable_all_target_protocols=InheritedValue.from_api(enable_all_target_protocols)
            if enable_all_target_protocols is not None
            else None,
        )


@dataclass(frozen=True)
class AnalysisProfileSummary:
    """One Analysis Profile as it appears in a `list()` result.

    A smaller shape than `AnalysisProfile` — carries no configuration
    values, only enough to identify a profile.

    Attributes:
        analysis_profile_id: The profile's unique identifier.
        name: The profile's display name.
        target_id: The Target this profile belongs to, if any.
    """

    analysis_profile_id: str
    name: str
    target_id: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AnalysisProfileSummary:
        """Builds an `AnalysisProfileSummary` from a list-item object.

        Args:
            data: The raw list-item object from the API response.

        Returns:
            The corresponding `AnalysisProfileSummary`.
        """
        return cls(
            analysis_profile_id=data["analysis_profile_id"],
            name=data["name"],
            target_id=data.get("target_id"),
        )


@dataclass(frozen=True)
class AnalysisProfileUpdate:
    """Partial parameters to update an existing Analysis Profile.

    Every field defaults to an internal "unset" sentinel; only explicitly
    passed fields (including an explicit `None`, for the four nullable
    array fields and `directory_restrictions`) are sent to the API.

    Does not expose `name` or `description`: `AnalysisProfileUpdateRequest`
    accepts neither.

    Attributes:
        allowed_urls: URLs the crawler is allowed to visit, if changing.
        denied_urls: URLs the crawler must not visit, if changing.
        seed_urls: URLs the crawler starts from, if changing.
        grouped_urls: URL groups treated as equivalent, if changing.
        crawler_mode: How thoroughly the crawler explores the target, if
            changing.
        rate_limit: Maximum requests per second (50-1,000,000,000), if
            changing.
        max_duration: Maximum scan duration in minutes (50-129,599), if
            changing.
        max_crawl_duration: Maximum crawl duration in minutes (1-129,599),
            if changing.
        max_browsers: Maximum concurrent browsers (1-12), if changing.
        scope_rules: Enterprise-mode API scan scope rules, if changing.
        similarity_threshold: Page similarity threshold (0.6-0.99), if
            changing.
        directory_restrictions: How strictly crawling stays within the
            seed URL's directory, if changing (pass `None` explicitly to
            clear it).
        enable_all_target_protocols: Whether all of the target's protocols
            are scanned, if changing.
    """

    allowed_urls: Any = _UNSET
    denied_urls: Any = _UNSET
    seed_urls: Any = _UNSET
    grouped_urls: Any = _UNSET
    crawler_mode: Any = _UNSET
    rate_limit: Any = _UNSET
    max_duration: Any = _UNSET
    max_crawl_duration: Any = _UNSET
    max_browsers: Any = _UNSET
    scope_rules: Any = _UNSET
    similarity_threshold: Any = _UNSET
    directory_restrictions: Any = _UNSET
    enable_all_target_protocols: Any = _UNSET

    def to_api(self) -> dict[str, Any]:
        """Builds the `PUT /analysis_profiles/{id}?method=PATCH` request body.

        Returns:
            A JSON-serializable request body containing only
            explicitly-set fields; an explicitly-set `None` is preserved
            as JSON `null`.
        """
        body: dict[str, Any] = {}
        if self.allowed_urls is not _UNSET:
            body["allowed_urls"] = self.allowed_urls
        if self.denied_urls is not _UNSET:
            body["denied_urls"] = self.denied_urls
        if self.seed_urls is not _UNSET:
            body["seed_urls"] = self.seed_urls
        if self.grouped_urls is not _UNSET:
            body["grouped_urls"] = self.grouped_urls
        if self.crawler_mode is not _UNSET:
            body["crawler_mode"] = (
                self.crawler_mode.value if self.crawler_mode is not None else None
            )
        if self.rate_limit is not _UNSET:
            body["rate_limit"] = self.rate_limit
        if self.max_duration is not _UNSET:
            body["max_duration"] = self.max_duration
        if self.max_crawl_duration is not _UNSET:
            body["max_crawl_duration"] = self.max_crawl_duration
        if self.max_browsers is not _UNSET:
            body["max_browsers"] = self.max_browsers
        if self.scope_rules is not _UNSET:
            body["scope_rules"] = (
                [rule.to_api() for rule in self.scope_rules]
                if self.scope_rules is not None
                else None
            )
        if self.similarity_threshold is not _UNSET:
            body["similarity_threshold"] = self.similarity_threshold
        if self.directory_restrictions is not _UNSET:
            body["directory_restrictions"] = (
                self.directory_restrictions.value
                if self.directory_restrictions is not None
                else None
            )
        if self.enable_all_target_protocols is not _UNSET:
            body["enable_all_target_protocols"] = self.enable_all_target_protocols
        return body


@dataclass(frozen=True)
class AnalysisProfilePage:
    """One page of `GET /analysis_profiles` results.

    Directly iterable over its `items`.

    Attributes:
        items: The analysis profile summaries on this page.
        page_number: The zero-based page number.
        page_size: The number of items requested per page.
        total_pages: The total number of pages available.
        total_elements: The total number of profiles across all pages.
    """

    items: list[AnalysisProfileSummary]
    page_number: int
    page_size: int
    total_pages: int
    total_elements: int

    def __iter__(self) -> Iterator[AnalysisProfileSummary]:
        return iter(self.items)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AnalysisProfilePage:
        """Builds an `AnalysisProfilePage` from a `GET /analysis_profiles`
        response.

        Args:
            data: The raw HAL-shaped response body.

        Returns:
            The corresponding `AnalysisProfilePage`.
        """
        items = [
            AnalysisProfileSummary.from_api(item)
            for item in data.get("_embedded", {}).get("analysis_profiles", [])
        ]
        page = data["page"]
        return cls(
            items=items,
            page_number=page["number"],
            page_size=page["size"],
            total_pages=page["total_pages"],
            total_elements=page["total_elements"],
        )
