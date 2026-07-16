"""Typed models for the DAST Target Configuration Service's Targets resource."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final


class TargetType(StrEnum):
    """The kind of DAST Target."""

    WEB_APP = "WEB_APP"
    API = "API"


class ScanType(StrEnum):
    """The scan depth configured for a Target."""

    QUICK = "QUICK"
    FULL = "FULL"
    ENTERPRISE = "ENTERPRISE"


class Protocol(StrEnum):
    """The protocol a Target is scanned over."""

    HTTP = "HTTP"
    HTTPS = "HTTPS"


class TargetSortBy(StrEnum):
    """Fields `TargetsService.list()` can sort by."""

    NAME = "name"
    URL = "url"
    TARGET_TYPE = "target_type"
    LAST_SCAN = "last_scan"
    STATUS = "status"
    MAX_CVSS = "max_cvss"


class SortOrder(StrEnum):
    """Sort direction for `TargetsService.list()`."""

    ASC = "asc"
    DESC = "desc"


class TargetStatus(StrEnum):
    """The last known scan status of a Target."""

    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


_UNSET: Final = object()


@dataclass(frozen=True)
class Target:
    """A Veracode DAST Target.

    Attributes:
        target_id: The target's unique identifier.
        name: The target's display name.
        protocol: The protocol the target is scanned over.
        url: The target's URL.
        target_type: Whether this is a web application or API target.
        scan_type: The configured scan depth.
        is_sec_lead_only: Whether this target is restricted to security leads.
        teams: IDs of teams this target is visible to.
        created_at: When the target was created (UTC datetime string).
        updated_at: When the target was last updated (UTC datetime string).
        api_specification_file_url: The API specification file URL, if any.
        description: The target's description, if any.
        last_scan: When the target was last scanned, if ever.
        application_name: The linked application's name, if linked.
        application_uuid: The linked application's UUID, if linked.
        application_id: The linked application's numeric ID, if linked.
        max_cvss: The highest CVSS score found, if any scan has run.
        status: The last known scan status, if any.
    """

    target_id: str
    name: str
    protocol: Protocol
    url: str
    target_type: TargetType
    scan_type: ScanType
    is_sec_lead_only: bool
    teams: list[str]
    created_at: str
    updated_at: str
    api_specification_file_url: str | None = None
    description: str | None = None
    last_scan: str | None = None
    application_name: str | None = None
    application_uuid: str | None = None
    application_id: int | None = None
    max_cvss: float | None = None
    status: TargetStatus | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Target:
        """Builds a `Target` from a Target Configuration Service response.

        Args:
            data: The raw target object from the API response.

        Returns:
            The corresponding `Target`.
        """
        status = data.get("status")
        return cls(
            target_id=data["target_id"],
            name=data["name"],
            protocol=Protocol(data["protocol"]),
            url=data["url"],
            target_type=TargetType(data["target_type"]),
            scan_type=ScanType(data["scan_type"]),
            is_sec_lead_only=data["is_sec_lead_only"],
            teams=list(data["teams"]) if data.get("teams") else [],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            api_specification_file_url=data.get("api_specification_file_url"),
            description=data.get("description"),
            last_scan=data.get("last_scan"),
            application_name=data.get("application_name"),
            application_uuid=data.get("application_uuid"),
            application_id=data.get("application_id"),
            max_cvss=data.get("max_cvss"),
            status=TargetStatus(status) if status else None,
        )


@dataclass(frozen=True)
class TargetCreate:
    """Parameters to create a new Target.

    Attributes:
        name: The target's display name. Must be unique in the organization.
        url: The target's URL.
        protocol: The protocol the target is scanned over.
        target_type: Whether this is a web application or API target.
        scan_type: The configured scan depth.
        authorized_to_scan: Confirms the caller is authorized to scan this URL.
        is_sec_lead_only: If True, `teams` must be empty/None. If False, at
            least one team is required.
        api_specification_file_url: Required if `target_type` is `API`.
        description: An optional description.
        teams: IDs of teams this target is visible to (at most one, Phase 1).
    """

    name: str
    url: str
    protocol: Protocol
    target_type: TargetType
    scan_type: ScanType
    authorized_to_scan: bool
    is_sec_lead_only: bool
    api_specification_file_url: str | None = None
    description: str | None = None
    teams: list[str] | None = None

    def to_api(self) -> dict[str, Any]:
        """Builds the `POST /targets` request body.

        Returns:
            A JSON-serializable request body, omitting unset optional fields.
        """
        body: dict[str, Any] = {
            "name": self.name,
            "url": self.url,
            "protocol": self.protocol.value,
            "target_type": self.target_type.value,
            "scan_type": self.scan_type.value,
            "authorized_to_scan": self.authorized_to_scan,
            "is_sec_lead_only": self.is_sec_lead_only,
        }
        if self.api_specification_file_url is not None:
            body["api_specification_file_url"] = self.api_specification_file_url
        if self.description is not None:
            body["description"] = self.description
        if self.teams is not None:
            body["teams"] = self.teams
        return body


@dataclass(frozen=True)
class TargetUpdate:
    """Partial parameters to update an existing Target.

    Every field defaults to an internal "unset" sentinel; only explicitly
    passed fields (including an explicit `None`) are sent to the API.

    Attributes:
        name: The target's new display name, if changing.
        protocol: The target's new protocol, if changing.
        url: The target's new URL, if changing.
        api_specification_file_url: The new API specification file URL, if
            changing (pass `None` explicitly to clear it).
        description: The new description, if changing (pass `None`
            explicitly to clear it).
        teams: The new team list, if changing (pass `None` explicitly to
            clear it; at most one team).
    """

    name: Any = _UNSET
    protocol: Any = _UNSET
    url: Any = _UNSET
    api_specification_file_url: Any = _UNSET
    description: Any = _UNSET
    teams: Any = _UNSET

    def to_api(self) -> dict[str, Any]:
        """Builds the `PUT /targets/{target_id}` request body.

        Returns:
            A JSON-serializable request body containing only explicitly-set
            fields; an explicitly-set `None` is preserved as JSON `null`.
        """
        body: dict[str, Any] = {}
        if self.name is not _UNSET:
            body["name"] = self.name
        if self.protocol is not _UNSET:
            body["protocol"] = self.protocol.value if self.protocol is not None else None
        if self.url is not _UNSET:
            body["url"] = self.url
        if self.api_specification_file_url is not _UNSET:
            body["api_specification_file_url"] = self.api_specification_file_url
        if self.description is not _UNSET:
            body["description"] = self.description
        if self.teams is not _UNSET:
            body["teams"] = self.teams
        return body


@dataclass(frozen=True)
class TargetPage:
    """One page of `GET /targets` results.

    Attributes:
        items: The targets on this page.
        page_number: The zero-based page number.
        page_size: The number of items requested per page.
        total_pages: The total number of pages available.
        total_elements: The total number of targets across all pages.
    """

    items: list[Target]
    page_number: int
    page_size: int
    total_pages: int
    total_elements: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> TargetPage:
        """Builds a `TargetPage` from a `GET /targets` response.

        Args:
            data: The raw HAL-shaped response body.

        Returns:
            The corresponding `TargetPage`.
        """
        items = [Target.from_api(item) for item in data.get("_embedded", {}).get("targets", [])]
        page = data["page"]
        return cls(
            items=items,
            page_number=page["number"],
            page_size=page["size"],
            total_pages=page["total_pages"],
            total_elements=page["total_elements"],
        )
