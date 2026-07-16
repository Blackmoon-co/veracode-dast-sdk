"""Infrastructure configuration: loading Veracode API credentials.

Only reads ``VERACODE_API_KEY_ID`` and ``VERACODE_API_KEY_SECRET`` from the
environment, per AGENTS.md's separation between infrastructure config (env
vars) and business data (always caller-supplied). Never imports ``requests``
or any base-URL/endpoint configuration.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from veracode_dast.exceptions import MissingCredentialsError

logger = logging.getLogger(__name__)

_API_KEY_ID_VAR = "VERACODE_API_KEY_ID"
_API_KEY_SECRET_VAR = "VERACODE_API_KEY_SECRET"


@dataclass(frozen=True)
class VeracodeCredentials:
    """Veracode API credentials.

    Attributes:
        api_key_id: The Veracode API key ID.
        api_key_secret: The Veracode API key secret.
    """

    api_key_id: str
    api_key_secret: str


def load_credentials_from_env() -> VeracodeCredentials:
    """Loads Veracode API credentials from the environment.

    Reads ``VERACODE_API_KEY_ID`` and ``VERACODE_API_KEY_SECRET``. An unset
    or empty-string value is treated as missing.

    Returns:
        The loaded credentials.

    Raises:
        MissingCredentialsError: If either environment variable is unset
            or empty, naming every missing variable.
    """
    api_key_id = os.environ.get(_API_KEY_ID_VAR, "")
    api_key_secret = os.environ.get(_API_KEY_SECRET_VAR, "")

    missing = [
        name
        for name, value in ((_API_KEY_ID_VAR, api_key_id), (_API_KEY_SECRET_VAR, api_key_secret))
        if not value
    ]
    if missing:
        raise MissingCredentialsError(missing)

    logger.debug("Veracode credentials loaded from environment")
    return VeracodeCredentials(api_key_id=api_key_id, api_key_secret=api_key_secret)
