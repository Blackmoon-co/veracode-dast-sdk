"""Veracode HMAC authentication provider construction.

Wraps ``veracode-api-signing`` only. Never owns a base URL, endpoint, or any
Veracode-service-specific configuration (AGENTS.md §3.1) — the resulting
auth provider is reused across every Veracode API domain. Never imports
``requests``.
"""

from __future__ import annotations

import logging

from veracode_api_signing.plugin_requests import RequestsAuthPluginVeracodeHMAC

from veracode_dast.config import VeracodeCredentials, load_credentials_from_env

logger = logging.getLogger(__name__)


def create_hmac_auth(credentials: VeracodeCredentials) -> RequestsAuthPluginVeracodeHMAC:
    """Builds a Veracode HMAC authentication provider from credentials.

    Args:
        credentials: The Veracode API credentials to sign requests with.

    Returns:
        A ``requests``-compatible auth provider implementing the Veracode
        HMAC signing scheme.
    """
    auth = RequestsAuthPluginVeracodeHMAC(
        api_key_id=credentials.api_key_id,
        api_key_secret=credentials.api_key_secret,
    )
    logger.debug("Veracode HMAC authentication provider created")
    return auth


def get_veracode_auth() -> RequestsAuthPluginVeracodeHMAC:
    """Loads credentials from the environment and builds an auth provider.

    This is the single entry point future components should call to obtain
    a ready-made Veracode authentication provider.

    Returns:
        A ``requests``-compatible auth provider implementing the Veracode
        HMAC signing scheme.

    Raises:
        MissingCredentialsError: If required credential environment
            variables are unset or empty.
    """
    credentials = load_credentials_from_env()
    return create_hmac_auth(credentials)
