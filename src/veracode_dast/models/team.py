"""Typed models for the Admin API's Teams resource."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Team:
    """A Veracode Team.

    Attributes:
        team_id: The team's unique identifier (UUID).
        team_name: The team's display name.
    """

    team_id: str
    team_name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Team:
        """Builds a `Team` from a Teams API response object.

        Only `team_id`/`team_name` are read; every other key present in a
        real response (e.g. `business_unit`, `organization`) is ignored.

        Args:
            data: The raw team object from the API response.

        Returns:
            The corresponding `Team`.
        """
        return cls(team_id=data["team_id"], team_name=data["team_name"])


@dataclass(frozen=True)
class TeamPage:
    """One page of `GET /teams` results.

    Attributes:
        items: The teams on this page.
        page_number: The zero-based page number.
        page_size: The number of items requested per page.
        total_pages: The total number of pages available.
        total_elements: The total number of teams across all pages.
    """

    items: list[Team]
    page_number: int
    page_size: int
    total_pages: int
    total_elements: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> TeamPage:
        """Builds a `TeamPage` from a `GET /teams` response.

        Args:
            data: The raw HAL-shaped response body.

        Returns:
            The corresponding `TeamPage`.
        """
        items = [Team.from_api(item) for item in data.get("_embedded", {}).get("teams", [])]
        page = data["page"]
        return cls(
            items=items,
            page_number=page["number"],
            page_size=page["size"],
            total_pages=page["total_pages"],
            total_elements=page["total_elements"],
        )
