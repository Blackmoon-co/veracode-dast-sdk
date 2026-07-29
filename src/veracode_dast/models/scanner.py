"""Typed models for the DAST Target Configuration Service's Scanner Profile
resource."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ScannerType(StrEnum):
    """The closed set of valid DAST scanner identifiers."""

    FINGERPRINTING = "fingerprinting"
    SSL = "ssl"
    HTTP_HEADER = "http_header"
    PORTSCAN = "portscan"
    FUZZER = "fuzzer"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    FILE_INCLUSION = "file_inclusion"
    DESERIALIZATION = "deserialization"
    XXE = "xxe"
    COMMAND_INJECTION = "command_injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CSRF = "csrf"
    LDAP_INJECTION = "ldap_injection"
    COMMON_LOGIN = "common_login"
    TRACE_METHOD = "trace_method"
    CODE_INJECTION = "code_injection"
    UNSECURED_LOGIN = "unsecured_login"
    CLICKJACKING = "clickjacking"
    SSTI = "ssti"
    OBSOLETE_RESOURCE = "obsolete_resource"
    INSECURE_JWT = "insecure_jwt"
    BACKUP_FILE = "backup_file"
    ERROR_PATTERN = "error_pattern"
    OPEN_REDIRECT = "open_redirect"
    SSRF = "ssrf"
    WEBSERVER_DIR_LIST = "webserver_dir_list"
    HTTP_RESP_SPLIT = "http_resp_split"
    VIEW_STATE = "view_state"
    FILE_UPLOAD = "file_upload"
    FLASH = "flash"
    FILE_DIR_EXPOSURE = "file_dir_exposure"
    URL_SESSION = "url_session"
    STRUTS2 = "struts2"
    MALICIOUS_HOST = "malicious_host"


@dataclass(frozen=True)
class Scanner:
    """One scanner's effective state for an Analysis Profile.

    Attributes:
        id: The scanner's identifier.
        enabled: Whether the scanner is currently enabled.
        inherited: Whether `enabled` is inherited from a parent profile.
        editable: Whether this scanner's state can be changed on this
            profile.
    """

    id: str
    enabled: bool
    inherited: bool
    editable: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Scanner:
        """Builds a `Scanner` from a `ScannerValue` API response object.

        Args:
            data: The raw scanner object from the API response.

        Returns:
            The corresponding `Scanner`.
        """
        return cls(
            id=data["id"],
            enabled=data["effective_value"],
            inherited=data["is_inherited"],
            editable=data["is_editable"],
        )


@dataclass(frozen=True)
class ScannerProfile:
    """The effective Scanner Profile for an Analysis Profile.

    Attributes:
        scanners: Every scanner's effective state.
        analysis_profile_id: The profile's unique identifier, if known.
        parent_analysis_profile_id: The parent profile, if known.
    """

    scanners: list[Scanner] = field(default_factory=list)
    analysis_profile_id: str | None = None
    parent_analysis_profile_id: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ScannerProfile:
        """Builds a `ScannerProfile` from a `GET`/`PUT` `.../scanners` response.

        Args:
            data: The raw response body.

        Returns:
            The corresponding `ScannerProfile`.
        """
        return cls(
            scanners=[Scanner.from_api(item) for item in data.get("scanners", [])],
            analysis_profile_id=data.get("analysis_profile_id"),
            parent_analysis_profile_id=data.get("parent_analysis_profile_id"),
        )
