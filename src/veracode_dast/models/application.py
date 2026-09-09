"""Typed models for the DAST Target Configuration Service's Applications resource."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Application:
    """A Veracode Application, as returned by `GET /applications`.

    Attributes:
        guid: The application's UUID. This is the value passed to
            `TargetsService.link()`.
        id: The application's identifier. A string in this OpenAPI schema,
            distinct from `Target.application_id` (an int64 field on a
            different schema).
        name: The application's display name.
        linked_scan_target_url: URL of the scan already linked to this
            application, if any.
    """

    guid: str
    id: str
    name: str
    linked_scan_target_url: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Application:
        """Builds an `Application` from a `GET /applications` list item.

        Args:
            data: The raw application object from the API response.

        Returns:
            The corresponding `Application`.
        """
        return cls(
            guid=data["guid"],
            id=data["id"],
            name=data["name"],
            linked_scan_target_url=data.get("linked_scan_target_url"),
        )


@dataclass(frozen=True)
class ApplicationPage:
    """One page of `GET /applications` results.

    Mirrors the OpenAPI `PagedApplications` schema, minus the `_links`
    HATEOAS array (same decision as `TargetPage`).

    Attributes:
        items: The applications on this page.
        page_number: The zero-based page number.
        page_size: The number of items requested per page.
        total_pages: The total number of pages available.
        total_elements: The total number of applications across all pages.
    """

    items: list[Application]
    page_number: int
    page_size: int
    total_pages: int
    total_elements: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ApplicationPage:
        """Builds an `ApplicationPage` from a `GET /applications` response.

        Reads `_embedded.Applications` (capital `A`, per the OpenAPI
        `EmbeddedApplications` schema); a missing `_embedded` or missing
        `Applications` yields an empty `items` list.

        Args:
            data: The raw HAL-shaped response body.

        Returns:
            The corresponding `ApplicationPage`.
        """
        items = [
            Application.from_api(item)
            for item in data.get("_embedded", {}).get("Applications", [])
        ]
        page = data["page"]
        return cls(
            items=items,
            page_number=page["number"],
            page_size=page["size"],
            total_pages=page["total_pages"],
            total_elements=page["total_elements"],
        )
