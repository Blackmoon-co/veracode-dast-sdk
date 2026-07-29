"""Scanner Profiles: enable/disable DAST security scanners for an existing
Analysis Profile.

Configuration-driven: callers author a small SDK Configuration document
(`{"scanners": {"<name>": <bool>, ...}}`) instead of the Veracode API's
`ScannerProfileUpdateRequest` shape.

Not every `ScannerType` is editable, or even present, on every Analysis
Profile: which scanners appear and whether each is editable depends on the
Target's `scan_type`/`target_type`. Confirmed live against a QUICK/WEB_APP
Target: only `fingerprinting`, `http_header`, `portscan`, and `ssl` were
editable (`sql_injection`, `xss`, `csrf`, `deserialization`, `xxe`, and
others came back `editable=False` and a PUT including them fails with a
400 `SQL_INJECTION_SCANNER_INVALID`-style error). Callers should check the
`editable` field on `Scanner` from `get()` before calling `update()`,
rather than assuming the full `ScannerType` enum applies.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from veracode_dast.exceptions import ScannerValidationError, UnknownScannerError
from veracode_dast.models.scanner import ScannerProfile, ScannerType
from veracode_dast.utils.sdk_config import load_json_config, suggest_closest

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

_SCANNERS_PATH = "/analysis_profiles/{analysis_profile_id}/scanners"

logger = logging.getLogger(__name__)


class ScannersService:
    """Manages Scanner Profiles for existing Analysis Profiles."""

    def __init__(self, http_client: HttpClient) -> None:
        """Initializes the service.

        Args:
            http_client: An `HttpClient` configured with
                `TARGET_CONFIGURATION_SERVICE_BASE_URL` — the same
                instance already constructed for `TargetsService`.
        """
        self._http_client = http_client

    def get(self, analysis_profile_id: str) -> ScannerProfile:
        """Gets the effective Scanner Profile for an Analysis Profile.

        Args:
            analysis_profile_id: The profile's unique identifier.

        Returns:
            The profile's current Scanner Profile.

        Raises:
            ScannerValidationError: If `analysis_profile_id` is blank.
            VeracodeNotFoundError: If no profile exists with that ID.
        """
        self._require_non_blank(analysis_profile_id, rule="analysis_profile_id_required")
        response = self._http_client.get(
            _SCANNERS_PATH.format(analysis_profile_id=analysis_profile_id)
        )
        profile = ScannerProfile.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Retrieved scanner profile for analysis profile %s", analysis_profile_id)
        return profile

    def update(
        self,
        analysis_profile_id: str,
        config_file: str | Path | dict[str, Any],
    ) -> ScannerProfile:
        """Updates a Scanner Profile from an SDK Configuration document.

        Scanners not mentioned in `config_file` are left untouched.

        Args:
            analysis_profile_id: The profile's unique identifier.
            config_file: A path to an SDK Configuration JSON file, or an
                already-loaded dict of the same shape.

        Returns:
            The profile's Scanner Profile after the update.

        Raises:
            ScannerValidationError: If `analysis_profile_id` is blank, or
                `config_file` fails structural validation.
            UnknownScannerError: If a configured scanner name is not a
                known `ScannerType`.
            VeracodeNotFoundError: If no profile exists with that ID.
        """
        self._require_non_blank(analysis_profile_id, rule="analysis_profile_id_required")

        config = load_json_config(config_file)
        scanners = self._validate(config)

        payload = {
            "scanners": [{"id": name, "value": value} for name, value in scanners.items()]
        }

        logger.info(
            "Updating scanner profile for analysis profile %s (%d scanner(s))",
            analysis_profile_id,
            len(scanners),
        )
        response = self._http_client.put(
            _SCANNERS_PATH.format(analysis_profile_id=analysis_profile_id),
            json=payload,
        )
        profile = ScannerProfile.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Scanner profile updated for analysis profile %s", analysis_profile_id)
        return profile

    @staticmethod
    def _validate(config: dict[str, Any]) -> dict[str, bool]:
        if not isinstance(config, dict):
            raise ScannerValidationError(
                "SDK Configuration must be a JSON object", rule="config_must_be_object"
            )
        scanners = config.get("scanners")
        if not isinstance(scanners, dict):
            raise ScannerValidationError(
                "SDK Configuration must contain a 'scanners' object",
                rule="scanners_key_required",
            )
        known = {member.value for member in ScannerType}
        for name, value in scanners.items():
            if not isinstance(value, bool):
                raise ScannerValidationError(
                    f"Scanner '{name}' value must be a boolean",
                    rule="scanner_value_must_be_bool",
                )
            if name not in known:
                raise UnknownScannerError(name, suggestion=suggest_closest(name, known))
        return scanners

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise ScannerValidationError("Value must not be blank", rule=rule)
