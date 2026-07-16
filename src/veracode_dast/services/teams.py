"""Team Management: read-only access to the Admin API's Teams resource.

Never imports or depends on `services/targets.py` — Team Management is
independent of Target Management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from veracode_dast.exceptions import TeamNotFoundError, TeamValidationError
from veracode_dast.models.team import Team, TeamPage

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

ADMIN_API_BASE_URL: Final = "https://api.veracode.com/api/authn/v2"
_BASE_PATH: Final = "/teams"
_DEFAULT_PAGE_SIZE: Final = 20

logger = logging.getLogger(__name__)


class TeamService:
    """Read-only access to Veracode Teams (Admin API)."""

    def __init__(self, http_client: HttpClient) -> None:
        """Initializes the service.

        Args:
            http_client: An `HttpClient` configured with `ADMIN_API_BASE_URL`.
        """
        self._http_client = http_client

    def list(
        self,
        *,
        page: int = 0,
        size: int = _DEFAULT_PAGE_SIZE,
        team_name: str | None = None,
    ) -> TeamPage:
        """Lists Teams, one page at a time.

        Note:
            `team_name` is a "containing name" (substring) filter, not a
            guaranteed exact match. Never calls `GET /teams/self`.

        Args:
            page: The zero-based page number to fetch.
            size: The number of items per page.
            team_name: An optional substring filter on team name.

        Returns:
            The requested page of Teams.
        """
        params: dict[str, object] = {"page": page, "size": size}
        if team_name is not None:
            params["team_name"] = team_name
        response = self._http_client.get(_BASE_PATH, params=params)
        team_page = TeamPage.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Listed %d team(s) (page %d)", len(team_page.items), page)
        return team_page

    def get(self, team_id: str) -> Team:
        """Gets one Team by ID.

        Args:
            team_id: The team's unique identifier.

        Returns:
            The matching Team.

        Raises:
            TeamValidationError: If `team_id` is blank.
            VeracodeNotFoundError: If no team exists with that ID.
        """
        self._require_non_blank(team_id, rule="team_id_required")
        response = self._http_client.get(f"{_BASE_PATH}/{team_id}")
        team = Team.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Retrieved team %s", team_id)
        return team

    def get_by_name(self, name: str) -> Team:
        """Resolves a Team by exact name.

        Scans every page of `list(team_name=name)` for an exact,
        case-sensitive `team_name` match, since the `team_name` filter is
        only a substring filter, not a guaranteed exact match.

        Args:
            name: The exact team name to resolve.

        Returns:
            The matching Team.

        Raises:
            TeamValidationError: If `name` is blank.
            TeamNotFoundError: If no team has that exact name.
        """
        self._require_non_blank(name, rule="name_required")
        page_number = 0
        while True:
            page = self.list(page=page_number, team_name=name)
            for team in page.items:
                if team.team_name == name:
                    logger.info("Resolved team %r to team_id=%s", name, team.team_id)
                    return team
            if page_number + 1 >= page.total_pages:
                break
            page_number += 1
        logger.info("No team found matching name %r", name)
        raise TeamNotFoundError(name)

    def exists(self, name: str) -> bool:
        """Checks whether a Team with the given exact name exists.

        Args:
            name: The exact team name to check.

        Returns:
            True if a team with that exact name exists, False otherwise.
        """
        try:
            self.get_by_name(name)
        except TeamNotFoundError:
            return False
        return True

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise TeamValidationError("Value must not be blank", rule=rule)
