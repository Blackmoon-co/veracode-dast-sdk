"""Typed models for the DAST Target Configuration Service's ISM Gateway
resource.

Class names (`ISMGateway`, `ISMEndpoint`) intentionally keep README's
literal spelling rather than this SDK's usual `Api`-not-`API`-style casing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ISMEndpoint:
    """One internal scanning endpoint under an ISM gateway.

    Field names mirror the OpenAPI `IsmEndpoint` schema exactly (`token`
    is kept as-is, not renamed to `id`) because the OpenAPI never
    documents what `token` actually represents.

    Attributes:
        token: The endpoint's identifier, used as `endpointUuid` when
            assigning a gateway. Treated as security-sensitive — never
            logged.
        name: The endpoint's display name, if any.
        status: The endpoint's status, if any.
    """

    token: str
    name: str | None = None
    status: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ISMEndpoint:
        """Builds an `ISMEndpoint` from an API response object."""
        return cls(token=data["token"], name=data.get("name"), status=data.get("status"))


@dataclass(frozen=True)
class ISMGateway:
    """An ISM gateway available to the account, or assigned to a target.

    Attributes:
        id: The gateway's unique identifier (the API's `refId`).
        name: The gateway's human-readable name.
        status: The gateway's status, if any.
        hostname: The gateway's network hostname, if any.
        endpoints: The gateway's internal scanning endpoints.
    """

    id: str
    name: str
    status: str | None = None
    hostname: str | None = None
    endpoints: list[ISMEndpoint] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ISMGateway:
        """Builds an `ISMGateway` from an API response object.

        Maps the OpenAPI's `refId` to `id`.
        """
        return cls(
            id=data["refId"],
            name=data["name"],
            status=data.get("status"),
            hostname=data.get("hostname"),
            endpoints=[ISMEndpoint.from_api(e) for e in data.get("endpoints", [])],
        )
