"""Application resolution: read-only access to the DAST Target
Configuration Service's Applications resource.

Never imports or depends on `services/targets.py` — Application resolution
is independent of Target Management, exactly like Team Management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from veracode_dast.exceptions import ApplicationNotFoundError, TargetValidationError
from veracode_dast.models.application import Application, ApplicationPage

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

_BASE_PATH: Final = "/applications"
_DEFAULT_PAGE_SIZE: Final = 10

logger = logging.getLogger(__name__)


class ApplicationsService:
    """Read-only access to Veracode Applications (DAST TCS domain)."""

    def __init__(self, http_client: HttpClient) -> None:
        """Initializes the service.

        Args:
            http_client: An `HttpClient` configured with
                `TARGET_CONFIGURATION_SERVICE_BASE_URL` (the same instance
                `TargetsService` uses).
        """
        self._http_client = http_client

    def list(
        self,
        *,
        name: str | None = None,
        page: int = 0,
        limit: int = _DEFAULT_PAGE_SIZE,
    ) -> ApplicationPage:
        """Lists Applications, one page at a time.

        Note:
            The `name` filter's matching semantics are undocumented in the
            OpenAPI; `get_by_name` does its own exact comparison rather
            than trusting this filter.

        Args:
            name: An optional filter on application name.
            page: The zero-based page number to fetch.
            limit: The number of items per page (10-200).

        Returns:
            The requested page of Applications.
        """
        params: dict[str, object] = {"page": page, "limit": limit}
        if name is not None:
            params["name"] = name
        response = self._http_client.get(_BASE_PATH, params=params)
        return ApplicationPage.from_api(response.data)  # type: ignore[arg-type]

    def get_by_name(self, name: str) -> Application:
        """Resolves an Application by exact, case-sensitive name.

        Scans every page of `list(name=name)`, since the `name` filter is
        not documented as an exact match.

        Args:
            name: The exact application name to resolve.

        Returns:
            The matching Application.

        Raises:
            TargetValidationError: If `name` is blank.
            ApplicationNotFoundError: If no application has that exact name.
        """
        self._require_non_blank(name, rule="name_required")
        page_number = 0
        while True:
            page = self.list(name=name, page=page_number)
            for application in page.items:
                if application.name == name:
                    logger.info("Resolved application %r to guid=%s", name, application.guid)
                    return application
            if page_number + 1 >= page.total_pages:
                break
            page_number += 1
        logger.info("No application found matching name %r", name)
        raise ApplicationNotFoundError(name)

    def exists(self, name: str) -> bool:
        """Checks whether an Application with the given exact name exists.

        Args:
            name: The exact application name to check.

        Returns:
            True if an application with that exact name exists, False
            otherwise. Any error other than `ApplicationNotFoundError`
            propagates.
        """
        try:
            self.get_by_name(name)
        except ApplicationNotFoundError:
            return False
        return True

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise TargetValidationError("Value must not be blank", rule=rule)
