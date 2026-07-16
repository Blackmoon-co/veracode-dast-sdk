"""SDK exception hierarchy.

Every exception raised by this SDK subclasses :class:`VeracodeSDKError`,
so callers can catch one base class to handle any SDK failure.
"""

from __future__ import annotations

from typing import Any


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


class VeracodeApiError(VeracodeSDKError):
    """Base class for all HTTP-transport-level failures, and the exception
    raised directly for any status code with no more specific subclass
    below.

    Attributes:
        method: The HTTP method of the request that failed (e.g. "GET").
        url: The full request URL.
        status_code: The HTTP status code, or None if the failure occurred
            before a response was received (connection error, timeout, or
            local JSON-decode failure).
        response_body: The parsed JSON body (dict/list), the raw response
            text if it wasn't valid JSON, or None if no response was
            received.
    """

    def __init__(
        self,
        message: str,
        *,
        method: str,
        url: str,
        status_code: int | None = None,
        response_body: dict[str, Any] | list[Any] | str | None = None,
    ) -> None:
        """Initializes the error with request/response context.

        Args:
            message: A human-readable description of the failure.
            method: The HTTP method of the request that failed.
            url: The full request URL.
            status_code: The HTTP status code, if a response was received.
            response_body: The parsed or raw response body, if any.
        """
        self.method = method
        self.url = url
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class VeracodeConnectionError(VeracodeApiError):
    """Raised when a request fails at the connection level (DNS failure,
    refused connection, reset connection) after retries are exhausted."""


class VeracodeTimeoutError(VeracodeApiError):
    """Raised when a request exceeds its configured timeout."""


class VeracodeAuthenticationError(VeracodeApiError):
    """Raised for HTTP responses with status code 401."""


class VeracodeAuthorizationError(VeracodeApiError):
    """Raised for HTTP responses with status code 403."""


class VeracodeNotFoundError(VeracodeApiError):
    """Raised for HTTP responses with status code 404."""


class VeracodeConflictError(VeracodeApiError):
    """Raised for HTTP responses with status code 409."""


class VeracodeValidationError(VeracodeApiError):
    """Raised for HTTP responses with status code 422."""
