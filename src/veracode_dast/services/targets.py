"""Target Management: CRUD and convenience operations for DAST Targets."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final

from veracode_dast.exceptions import TargetNotFoundError, TargetValidationError
from veracode_dast.models.target import (
    SortOrder,
    Target,
    TargetCreate,
    TargetPage,
    TargetSortBy,
    TargetType,
    TargetUpdate,
)

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

TARGET_CONFIGURATION_SERVICE_BASE_URL: Final = "https://api.veracode.com/dae/api/tcs-api/api/v1"
_BASE_PATH: Final = "/targets"

logger = logging.getLogger(__name__)


class TargetsService:
    """CRUD and convenience operations for DAST Targets."""

    def __init__(self, http_client: HttpClient) -> None:
        """Initializes the service.

        Args:
            http_client: An `HttpClient` configured with
                `TARGET_CONFIGURATION_SERVICE_BASE_URL`.
        """
        self._http_client = http_client

    def list(
        self,
        *,
        page: int = 0,
        limit: int = 10,
        sort_by: TargetSortBy = TargetSortBy.NAME,
        sort_order: SortOrder = SortOrder.ASC,
        name: str | None = None,
        url: str | None = None,
        search_term: str | None = None,
        target_type: TargetType | None = None,
    ) -> TargetPage:
        """Lists Targets, one page at a time.

        Args:
            page: The zero-based page number to fetch.
            limit: The number of items per page (10-200).
            sort_by: The field to sort results by.
            sort_order: The sort direction.
            name: An optional filter on target name.
            url: An optional filter on target URL.
            search_term: An optional filter matching name or URL.
            target_type: An optional filter on target type.

        Returns:
            The requested page of Targets.
        """
        params: dict[str, Any] = {
            "page": page,
            "limit": limit,
            "sort_by": sort_by.value,
            "sort_order": sort_order.value,
        }
        if name is not None:
            params["name"] = name
        if url is not None:
            params["url"] = url
        if search_term is not None:
            params["search_term"] = search_term
        if target_type is not None:
            params["target_type"] = target_type.value
        response = self._http_client.get(_BASE_PATH, params=params)
        return TargetPage.from_api(response.data)  # type: ignore[arg-type]

    def get(self, target_id: str) -> Target:
        """Gets one Target by ID.

        Args:
            target_id: The target's unique identifier.

        Returns:
            The matching Target.

        Raises:
            VeracodeNotFoundError: If no target exists with that ID.
        """
        response = self._http_client.get(f"{_BASE_PATH}/{target_id}")
        return Target.from_api(response.data)  # type: ignore[arg-type]

    def create(self, target: TargetCreate) -> Target:
        """Creates a new Target.

        Args:
            target: The parameters for the new target.

        Returns:
            The created Target.

        Raises:
            TargetValidationError: If a client-side validation rule fails.
        """
        self._validate(
            target.target_type,
            target.api_specification_file_url,
            target.is_sec_lead_only,
            target.teams,
        )
        response = self._http_client.post(_BASE_PATH, json=target.to_api())
        created = Target.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Created target %s (target_id=%s)", created.name, created.target_id)
        return created

    def update(self, target_id: str, target: TargetUpdate) -> Target:
        """Updates an existing Target.

        Args:
            target_id: The target's unique identifier.
            target: The fields to update.

        Returns:
            The updated Target.

        Raises:
            TargetValidationError: If `teams` is explicitly set with more
                than one entry.
        """
        if isinstance(target.teams, list) and len(target.teams) > 1:
            raise TargetValidationError("At most one team is supported", rule="teams_max_one")
        response = self._http_client.put(f"{_BASE_PATH}/{target_id}", json=target.to_api())
        updated = Target.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Updated target %s (target_id=%s)", updated.name, target_id)
        return updated

    def delete(self, target_id: str) -> None:
        """Deletes a Target.

        Args:
            target_id: The target's unique identifier.

        Raises:
            VeracodeNotFoundError: If no target exists with that ID.
        """
        self._http_client.delete(f"{_BASE_PATH}/{target_id}")
        logger.info("Deleted target (target_id=%s)", target_id)

    def get_by_name(self, name: str) -> Target | None:
        """Resolves a Target by exact name.

        Scans every page of `list(name=name)` for an exact, case-sensitive
        `name` match.

        Args:
            name: The exact target name to resolve.

        Returns:
            The matching Target, or None if no target has that exact name.
        """
        page_number = 0
        while True:
            page = self.list(page=page_number, name=name)
            for item in page.items:
                if item.name == name:
                    return item
            if page_number + 1 >= page.total_pages:
                break
            page_number += 1
        return None

    def exists(self, name: str) -> bool:
        """Checks whether a Target with the given exact name exists.

        Args:
            name: The exact target name to check.

        Returns:
            True if a target with that exact name exists, False otherwise.
        """
        return self.get_by_name(name) is not None

    def ensure(self, target: TargetCreate) -> Target:
        """Gets an existing Target by name, or creates it if absent.

        Never updates an existing target's fields — a pure get-or-create.

        Args:
            target: The parameters to create the target with, if absent.

        Returns:
            The existing or newly-created Target.
        """
        existing = self.get_by_name(target.name)
        if existing is not None:
            logger.info(
                "Target %s already exists (target_id=%s)", target.name, existing.target_id
            )
            return existing
        created = self.create(target)
        logger.info("Target %s created by ensure() (target_id=%s)", created.name, created.target_id)
        return created

    def update_by_name(self, name: str, target: TargetUpdate) -> Target:
        """Resolves a Target by exact name, then updates it.

        Args:
            name: The exact target name to resolve.
            target: The fields to update.

        Returns:
            The updated Target.

        Raises:
            TargetNotFoundError: If no target has that exact name.
        """
        existing = self.get_by_name(name)
        if existing is None:
            raise TargetNotFoundError(name)
        return self.update(existing.target_id, target)

    @staticmethod
    def _validate(
        target_type: TargetType,
        api_specification_file_url: str | None,
        is_sec_lead_only: bool,
        teams: Sequence[str] | None,
    ) -> None:
        if target_type == TargetType.API and not api_specification_file_url:
            raise TargetValidationError(
                "api_specification_file_url is required when target_type is API",
                rule="api_target_requires_spec_url",
            )
        if is_sec_lead_only and teams:
            raise TargetValidationError(
                "teams must be empty when is_sec_lead_only is True",
                rule="sec_lead_only_excludes_teams",
            )
        if not is_sec_lead_only and not teams:
            raise TargetValidationError(
                "At least one team is required when is_sec_lead_only is False",
                rule="teams_required_unless_sec_lead_only",
            )
        if teams and len(teams) > 1:
            raise TargetValidationError("At most one team is supported", rule="teams_max_one")
