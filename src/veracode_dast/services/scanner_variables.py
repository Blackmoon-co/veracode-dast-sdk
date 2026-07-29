"""Scanner Variables: runtime values consumed by authentication mechanisms
(login scripts, MFA/TOTP) during an authenticated DAST scan.

`update()` always sends the caller's entire SDK Configuration as the new,
complete list of Scanner Variables for the Analysis Profile — it never
merges with, or first reads, the profile's existing Scanner Variables. Any
existing variable whose `reference_key` is absent from the configuration is
removed by the server.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from veracode_dast.exceptions import ScannerVariableValidationError
from veracode_dast.models.scanner_variable import ScannerVariable, ScannerVariables
from veracode_dast.utils.sdk_config import load_json_config

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

_SCANNER_VARIABLES_PATH = "/analysis_profiles/{analysis_profile_id}/scanner_variables"

logger = logging.getLogger(__name__)


class ScannerVariablesService:
    """Reads and replaces Scanner Variables for existing Analysis Profiles."""

    def __init__(self, http_client: HttpClient) -> None:
        """Initializes the service.

        Args:
            http_client: An `HttpClient` configured with
                `TARGET_CONFIGURATION_SERVICE_BASE_URL` — the same
                instance already constructed for `TargetsService` and
                sibling Phase 2 services. This class never constructs its
                own `HttpClient`.
        """
        self._http_client = http_client

    def get(self, analysis_profile_id: str) -> ScannerVariables:
        """Gets the effective Scanner Variables for an Analysis Profile.

        Args:
            analysis_profile_id: The profile's unique identifier.

        Returns:
            The profile's current Scanner Variables.

        Raises:
            ScannerVariableValidationError: If `analysis_profile_id` is blank.
            VeracodeNotFoundError: If no profile exists with that ID.
        """
        self._require_non_blank(analysis_profile_id, rule="analysis_profile_id_required")
        response = self._http_client.get(
            _SCANNER_VARIABLES_PATH.format(analysis_profile_id=analysis_profile_id)
        )
        result = ScannerVariables.from_api(response.data)  # type: ignore[arg-type]
        logger.info(
            "Retrieved %d scanner variable(s) for analysis profile %s",
            len(result.variables),
            analysis_profile_id,
        )
        return result

    def update(
        self, analysis_profile_id: str, config_file: str | Path | dict[str, Any]
    ) -> ScannerVariables:
        """Replaces the Scanner Variables for an Analysis Profile.

        Sends the entire SDK Configuration as the new, complete list of
        Scanner Variables — any existing variable whose `reference_key` is
        absent from `config_file` is removed by the server. Passing
        `{"variables": []}` deletes every Scanner Variable from the profile.

        Args:
            analysis_profile_id: The profile's unique identifier.
            config_file: A path to an SDK Configuration JSON file, or an
                already-loaded dict of the same shape.

        Returns:
            The profile's Scanner Variables after the update.

        Raises:
            ScannerVariableValidationError: If `analysis_profile_id` is
                blank, or `config_file` fails structural/semantic
                validation.
            VeracodeNotFoundError: If no profile exists with that ID.
        """
        self._require_non_blank(analysis_profile_id, rule="analysis_profile_id_required")
        config = load_json_config(config_file)
        variables = self._validate(config)

        logger.info(
            "Updating scanner variables for analysis profile %s (%d variable(s))",
            analysis_profile_id,
            len(variables),
        )
        response = self._http_client.put(
            _SCANNER_VARIABLES_PATH.format(analysis_profile_id=analysis_profile_id),
            json=[variable.to_api() for variable in variables],
        )
        result = (
            ScannerVariables(variables=[])
            if response.data is None
            else ScannerVariables.from_api(response.data)  # type: ignore[arg-type]
        )
        logger.info("Scanner variables updated for analysis profile %s", analysis_profile_id)
        return result

    @staticmethod
    def _validate(config: dict[str, Any]) -> list[ScannerVariable]:
        if not isinstance(config, dict):
            raise ScannerVariableValidationError(
                "SDK Configuration must be a JSON object", rule="config_must_be_object"
            )
        raw_variables = config.get("variables")
        if not isinstance(raw_variables, list):
            raise ScannerVariableValidationError(
                "SDK Configuration must contain a 'variables' array",
                rule="variables_key_required",
            )

        seen_keys: set[str] = set()
        variables: list[ScannerVariable] = []
        for entry in raw_variables:
            if not isinstance(entry, dict):
                raise ScannerVariableValidationError(
                    "Each entry in 'variables' must be a JSON object",
                    rule="variable_must_be_object",
                )
            reference_key = entry.get("reference_key")
            if not isinstance(reference_key, str) or not reference_key.strip():
                raise ScannerVariableValidationError(
                    "Each scanner variable requires a non-blank 'reference_key'",
                    rule="reference_key_required",
                )
            if reference_key in seen_keys:
                raise ScannerVariableValidationError(
                    f"Duplicate scanner variable reference_key: '{reference_key}'",
                    rule="duplicate_reference_key",
                )
            seen_keys.add(reference_key)

            value = entry.get("value")
            if not isinstance(value, str) or not value:
                raise ScannerVariableValidationError(
                    f"Scanner variable '{reference_key}' requires a non-blank 'value'",
                    rule="value_required",
                )

            totp_seed = entry.get("totp_seed", False)
            if not isinstance(totp_seed, bool):
                raise ScannerVariableValidationError(
                    f"Scanner variable '{reference_key}': 'totp_seed' must be a boolean",
                    rule="invalid_totp_configuration",
                )

            variables.append(
                ScannerVariable(reference_key=reference_key, value=value, totp_seed=totp_seed)
            )
        return variables

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise ScannerVariableValidationError("Value must not be blank", rule=rule)
