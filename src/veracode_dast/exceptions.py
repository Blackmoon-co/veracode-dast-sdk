"""SDK exception hierarchy.

Every exception raised by this SDK subclasses :class:`VeracodeSDKError`,
so callers can catch one base class to handle any SDK failure.
"""

from __future__ import annotations


class VeracodeSDKError(Exception):
    """Root of every exception raised by this SDK."""


class VeracodeAuthError(VeracodeSDKError):
    """Raised when obtaining a Veracode authentication provider fails."""


class MissingCredentialsError(VeracodeAuthError):
    """Raised when one or more required credential environment variables
    are unset or empty.

    Attributes:
        missing_variables: Names of the environment variables that were
            missing. Never includes any credential value.
    """

    def __init__(self, missing_variables: list[str]) -> None:
        """Initializes the error with the names of the missing variables.

        Args:
            missing_variables: Names of the missing environment variables.
        """
        self.missing_variables = missing_variables
        joined = ", ".join(missing_variables)
        super().__init__(f"Missing required Veracode credential environment variable(s): {joined}")
