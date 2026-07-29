"""ISM Gateways: manages Internal Scanning Management gateway assignment
for existing DAST Targets, so Veracode DAST can reach non-publicly
accessible applications.

Every public method takes `target_id`, not `analysis_profile_id`: no
OpenAPI endpoint for this resource accepts an `analysis_profile_id`, and
`AnalysisProfile.target_id` is optional (only `TARGET`-type profiles have
one). A caller starting from an `analysis_profile_id` resolves `target_id`
themselves, e.g. `client.analysis_profiles.get(analysis_profile_id).target_id`.

Callers configure a gateway by human-readable name; this service resolves
the name to the `gatewayUuid`/`endpointUuid` pair the REST API requires.

Two assumptions here are inferred from an underspecified OpenAPI schema,
not confirmed by a documented example, and should be validated against a
live/sandbox Veracode account: `IsmEndpoint.token` is used as the
endpoint identifier (`endpointUuid`), and an empty-body `PUT` is used to
clear a gateway assignment (`remove()`). If either proves wrong, only
`_select_endpoint`/`remove()` need to change — no public interface is
affected.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from veracode_dast.exceptions import (
    GatewayNameNotUniqueError,
    GatewayNotFoundError,
    IsmGatewayValidationError,
)
from veracode_dast.models.ism_gateway import ISMEndpoint, ISMGateway
from veracode_dast.utils.sdk_config import load_json_config, suggest_closest

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

_ISM_GATEWAYS_PATH = "/ism_gateways"
_TARGET_ISM_GATEWAY_PATH = "/ism_gateways/targets/{target_id}"

logger = logging.getLogger(__name__)


def _resolve_gateway_by_name(name: str, gateways: list[ISMGateway]) -> ISMGateway:
    """Finds the gateway named exactly `name` among `gateways`.

    A pure function over already-fetched data — no `HttpClient` involved.

    Args:
        name: The exact gateway name to resolve.
        gateways: Every gateway available to the account.

    Returns:
        The matching gateway.

    Raises:
        GatewayNotFoundError: If no gateway matches.
        GatewayNameNotUniqueError: If more than one gateway matches.
    """
    matches = [g for g in gateways if g.name == name]
    if not matches:
        suggestion = suggest_closest(name, [g.name for g in gateways])
        raise GatewayNotFoundError(name, suggestion=suggestion)
    if len(matches) > 1:
        raise GatewayNameNotUniqueError(name, matches=[g.id for g in matches])
    return matches[0]


def _select_endpoint(gateway: ISMGateway) -> ISMEndpoint:
    """Selects the sole endpoint of `gateway`.

    Args:
        gateway: The gateway to select an endpoint from.

    Returns:
        The gateway's sole endpoint.

    Raises:
        IsmGatewayValidationError: If `gateway` has zero or more than one
            endpoint — this feature never guesses among multiple.
    """
    if not gateway.endpoints:
        raise IsmGatewayValidationError(
            f"ISM Gateway '{gateway.name}' has no endpoints to assign.",
            rule="gateway_has_no_endpoint",
        )
    if len(gateway.endpoints) > 1:
        raise IsmGatewayValidationError(
            f"ISM Gateway '{gateway.name}' has more than one endpoint; "
            "this SDK cannot resolve which one to use.",
            rule="gateway_endpoint_ambiguous",
        )
    return gateway.endpoints[0]


def _build_target_ism_gateway_payload(gateway: ISMGateway, endpoint: ISMEndpoint) -> dict[str, Any]:
    """Builds the `TargetIsmGateway` request body.

    Args:
        gateway: The resolved gateway.
        endpoint: The resolved gateway's sole endpoint.

    Returns:
        The `{"gatewayUuid": ..., "endpointUuid": ...}` request body.
    """
    return {"gatewayUuid": gateway.id, "endpointUuid": endpoint.token}


def _extract_gateway_name_from_config(config: dict[str, Any]) -> str:
    """Validates SDK Configuration structure and returns the configured
    gateway name.

    No dedicated SDK Configuration model is introduced for this shape — it
    stays a plain `dict[str, Any]` end-to-end, since it has no behavior of
    its own beyond this validation.

    Args:
        config: The loaded SDK Configuration document.

    Returns:
        The configured gateway name.

    Raises:
        IsmGatewayValidationError: On any structural violation.
    """
    if not isinstance(config, dict):
        raise IsmGatewayValidationError(
            "SDK Configuration must be a JSON object", rule="config_must_be_object"
        )
    gateway = config.get("gateway")
    if not isinstance(gateway, dict):
        raise IsmGatewayValidationError(
            "SDK Configuration must contain a 'gateway' object", rule="gateway_key_required"
        )
    name = gateway.get("name")
    if not isinstance(name, str) or not name.strip():
        raise IsmGatewayValidationError(
            "SDK Configuration's 'gateway.name' must be a non-blank string",
            rule="gateway_name_required",
        )
    return name


class IsmGatewaysService:
    """Manages ISM Gateway assignment for existing DAST Targets."""

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

    def list(self) -> list[ISMGateway]:
        """Lists every ISM gateway available to the account.

        Returns:
            Every available gateway.
        """
        response = self._http_client.get(_ISM_GATEWAYS_PATH)
        raw_gateways: list[dict[str, Any]] = response.data or []  # type: ignore[assignment]
        gateways = [ISMGateway.from_api(item) for item in raw_gateways]
        logger.info("Retrieved %d ISM gateway(s)", len(gateways))
        return gateways

    def get(self, target_id: str) -> ISMGateway | None:
        """Gets the ISM gateway currently assigned to a target, if any.

        Args:
            target_id: The target's unique identifier.

        Returns:
            The assigned gateway, or None if the target has no gateway
            assigned.

        Raises:
            IsmGatewayValidationError: If `target_id` is blank, or the
                assignment references a gateway no longer in `list()`.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        response = self._http_client.get(_TARGET_ISM_GATEWAY_PATH.format(target_id=target_id))
        data = response.data or {}
        gateway_uuid = data.get("gatewayUuid")  # type: ignore[union-attr]
        if not gateway_uuid:
            logger.info("No ISM gateway assigned to target %s", target_id)
            return None

        gateway = next((g for g in self.list() if g.id == gateway_uuid), None)
        if gateway is None:
            raise IsmGatewayValidationError(
                f"Target {target_id} references ISM gateway {gateway_uuid}, "
                "which no longer exists in this account's gateway list.",
                rule="gateway_not_found_by_id",
            )
        logger.info("Target %s is assigned ISM gateway %s", target_id, gateway.name)
        return gateway

    def update(
        self,
        target_id: str,
        *,
        gateway_name: str | None = None,
        config_file: str | Path | dict[str, Any] | None = None,
    ) -> ISMGateway:
        """Assigns or changes the ISM gateway assigned to a target.

        Args:
            target_id: The target's unique identifier.
            gateway_name: The exact name of the gateway to assign. Exactly
                one of `gateway_name`/`config_file` must be supplied.
            config_file: A path to an SDK Configuration JSON file (or an
                already-loaded dict) naming the gateway to assign, per
                README's `{"gateway": {"name": "<gateway name>"}}` shape.

        Returns:
            The assigned gateway.

        Raises:
            IsmGatewayValidationError: If `target_id` is blank, if neither
                or both of `gateway_name`/`config_file` are supplied, if
                `config_file` fails structural validation, or if the
                resolved gateway has zero or more than one endpoint.
            GatewayNotFoundError: If no gateway matches `gateway_name`.
            GatewayNameNotUniqueError: If more than one gateway matches
                `gateway_name`.
            VeracodeNotFoundError: If no target exists with that ID.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        if (gateway_name is None) == (config_file is None):
            raise IsmGatewayValidationError(
                "Exactly one of gateway_name or config_file must be provided",
                rule="gateway_name_or_config_file_required",
            )

        if config_file is not None:
            config = load_json_config(config_file)
            gateway_name = _extract_gateway_name_from_config(config)

        gateway = _resolve_gateway_by_name(gateway_name, self.list())  # type: ignore[arg-type]
        endpoint = _select_endpoint(gateway)

        logger.info("Assigning ISM gateway %s to target %s", gateway.name, target_id)
        self._http_client.put(
            _TARGET_ISM_GATEWAY_PATH.format(target_id=target_id),
            json=_build_target_ism_gateway_payload(gateway, endpoint),
        )
        logger.info("Assigned ISM gateway %s to target %s", gateway.name, target_id)
        return gateway

    def remove(self, target_id: str) -> None:
        """Removes the ISM gateway assignment from a target.

        Args:
            target_id: The target's unique identifier.

        Raises:
            IsmGatewayValidationError: If `target_id` is blank.
            VeracodeNotFoundError: If no target exists with that ID.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        logger.info("Removing ISM gateway assignment from target %s", target_id)
        self._http_client.put(_TARGET_ISM_GATEWAY_PATH.format(target_id=target_id), json={})
        logger.info("Removed ISM gateway assignment from target %s", target_id)

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise IsmGatewayValidationError("Value must not be blank", rule=rule)
