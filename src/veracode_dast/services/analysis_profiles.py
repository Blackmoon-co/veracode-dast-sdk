"""Analysis Profiles: read and update the root DAST scan configuration
resource.

Never creates or deletes Analysis Profiles — the REST API exposes neither
operation. Never imports `services/targets.py`, `services/teams.py`, or
`services/api_specifications.py` — it only reuses two of API Specification
Management's *models*.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from veracode_dast.exceptions import AnalysisProfileValidationError
from veracode_dast.models.analysis_profile import (
    AnalysisProfile,
    AnalysisProfilePage,
    AnalysisProfileType,
    AnalysisProfileUpdate,
)

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

_BASE_PATH = "/analysis_profiles"

logger = logging.getLogger(__name__)


class AnalysisProfilesService:
    """Read and update access to Veracode DAST Analysis Profiles."""

    def __init__(self, http_client: HttpClient) -> None:
        """Initializes the service.

        Args:
            http_client: An `HttpClient` configured with
                `TARGET_CONFIGURATION_SERVICE_BASE_URL` — the same
                instance already constructed for `TargetsService`/
                `ApiSpecificationsService`. This class never constructs
                its own `HttpClient`.
        """
        self._http_client = http_client

    def list(
        self,
        *,
        page: int = 0,
        limit: int = 10,
        target_id: str | None = None,
        types: list[AnalysisProfileType] | None = None,
    ) -> AnalysisProfilePage:
        """Lists Analysis Profiles, one page at a time.

        Args:
            page: The zero-based page number to fetch.
            limit: The number of items per page.
            target_id: Filter to profiles belonging to one Target.
            types: Filter to one or more Analysis Profile types.

        Returns:
            The requested page of Analysis Profiles.
        """
        params: dict[str, object] = {"page": page, "limit": limit}
        if target_id is not None:
            params["target_id"] = target_id
        if types is not None:
            params["type"] = [t.value for t in types]
        response = self._http_client.get(_BASE_PATH, params=params)
        result = AnalysisProfilePage.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Listed %d analysis profile(s) (page %d)", len(result.items), page)
        return result

    def get(self, analysis_profile_id: str) -> AnalysisProfile:
        """Gets one Analysis Profile by ID.

        Args:
            analysis_profile_id: The profile's unique identifier.

        Returns:
            The matching Analysis Profile.

        Raises:
            AnalysisProfileValidationError: If `analysis_profile_id` is blank.
            VeracodeNotFoundError: If no profile exists with that ID.
        """
        self._require_non_blank(analysis_profile_id, rule="analysis_profile_id_required")
        response = self._http_client.get(f"{_BASE_PATH}/{analysis_profile_id}")
        profile = AnalysisProfile.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Retrieved analysis profile %s", analysis_profile_id)
        return profile

    def update(
        self, analysis_profile_id: str, analysis_profile: AnalysisProfileUpdate
    ) -> AnalysisProfile:
        """Updates an Analysis Profile, changing only the fields set on
        `analysis_profile`.

        Always sends `method=PATCH` so that fields not present on
        `analysis_profile` are left untouched rather than cleared — this
        is a full PUT-as-replace endpoint unless that query parameter is
        present.

        Args:
            analysis_profile_id: The profile's unique identifier.
            analysis_profile: The fields to change.

        Returns:
            The updated Analysis Profile.

        Raises:
            AnalysisProfileValidationError: If `analysis_profile_id` is blank.
            VeracodeNotFoundError: If no profile exists with that ID.
            VeracodeValidationError: If a supplied value violates a
                server-side range constraint.
        """
        self._require_non_blank(analysis_profile_id, rule="analysis_profile_id_required")
        response = self._http_client.put(
            f"{_BASE_PATH}/{analysis_profile_id}",
            json=analysis_profile.to_api(),
            params={"method": "PATCH"},
        )
        profile = AnalysisProfile.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Updated analysis profile %s", analysis_profile_id)
        return profile

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise AnalysisProfileValidationError("Value must not be blank", rule=rule)
