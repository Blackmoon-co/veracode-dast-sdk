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


class TeamValidationError(VeracodeSDKError):
    """Raised for SDK-level Team Management parameter validation failures.

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        """Initializes the error.

        Args:
            message: A human-readable description of the failure.
            rule: A short identifier of which validation rule failed.
        """
        self.rule = rule
        super().__init__(message)


class TeamNotFoundError(VeracodeSDKError):
    """Raised when no Team matches a `get_by_name` lookup.

    Attributes:
        name: The team name that was searched for.
    """

    def __init__(self, name: str) -> None:
        """Initializes the error.

        Args:
            name: The team name that was searched for.
        """
        self.name = name
        super().__init__(f"No team found with name: {name}")


class TargetValidationError(VeracodeSDKError):
    """Raised for SDK-level Target Management parameter validation failures.

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        """Initializes the error.

        Args:
            message: A human-readable description of the failure.
            rule: A short identifier of which validation rule failed.
        """
        self.rule = rule
        super().__init__(message)


class TargetNotFoundError(VeracodeSDKError):
    """Raised when no Target matches a `get_by_name`/`update_by_name` lookup.

    Attributes:
        name: The target name that was searched for.
    """

    def __init__(self, name: str) -> None:
        """Initializes the error.

        Args:
            name: The target name that was searched for.
        """
        self.name = name
        super().__init__(f"No target found with name: {name}")


class ApiSpecificationValidationError(VeracodeSDKError):
    """Raised for SDK-level API Specification parameter validation failures.

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        """Initializes the error.

        Args:
            message: A human-readable description of the failure.
            rule: A short identifier of which validation rule failed.
        """
        self.rule = rule
        super().__init__(message)


class ApiSpecificationFileNotFoundError(VeracodeSDKError):
    """Raised when `upload()`'s local file path does not exist.

    Attributes:
        path: The file path that was not found.
    """

    def __init__(self, message: str, *, path: str) -> None:
        """Initializes the error.

        Args:
            message: A human-readable description of the failure.
            path: The file path that was not found.
        """
        self.path = path
        super().__init__(message)


class ConfigFileNotFoundError(VeracodeSDKError):
    """Raised when an SDK Configuration file path does not exist.

    Attributes:
        path: The file path that was not found.
    """

    def __init__(self, path: str) -> None:
        """Initializes the error.

        Args:
            path: The file path that was not found.
        """
        self.path = path
        super().__init__(f"SDK Configuration file not found: {path}")


class ConfigFileInvalidError(VeracodeSDKError):
    """Raised when an SDK Configuration file's contents are not valid JSON.

    Attributes:
        path: The file path that failed to parse.
        reason: The underlying `json.JSONDecodeError` message.
    """

    def __init__(self, path: str, *, reason: str) -> None:
        """Initializes the error.

        Args:
            path: The file path that failed to parse.
            reason: The underlying `json.JSONDecodeError` message.
        """
        self.path = path
        self.reason = reason
        super().__init__(f"SDK Configuration file is not valid JSON: {path} ({reason})")


class ScannerValidationError(VeracodeSDKError):
    """Raised for SDK-level Scanner Profile parameter/configuration
    validation failures.

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        """Initializes the error.

        Args:
            message: A human-readable description of the failure.
            rule: A short identifier of which validation rule failed.
        """
        self.rule = rule
        super().__init__(message)


class UnknownScannerError(VeracodeSDKError):
    """Raised when an SDK Configuration names a scanner outside the known
    ScannerType set.

    Attributes:
        scanner_id: The unrecognized name from the configuration.
        suggestion: The closest known ScannerType name, or None if no
            close match was found.
    """

    def __init__(self, scanner_id: str, *, suggestion: str | None) -> None:
        """Initializes the error.

        Args:
            scanner_id: The unrecognized name from the configuration.
            suggestion: The closest known ScannerType name, or None.
        """
        self.scanner_id = scanner_id
        self.suggestion = suggestion
        message = f"Unknown scanner '{scanner_id}'."
        if suggestion:
            message += f"\n\nDid you mean '{suggestion}'?"
        super().__init__(message)


class AnalysisProfileValidationError(VeracodeSDKError):
    """Raised for SDK-level Analysis Profile parameter validation failures.

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        """Initializes the error.

        Args:
            message: A human-readable description of the failure.
            rule: A short identifier of which validation rule failed.
        """
        self.rule = rule
        super().__init__(message)


class AuthenticationValidationError(VeracodeSDKError):
    """Raised for SDK-level Authentication parameter/configuration
    validation failures.

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        """Initializes the error.

        Args:
            message: A human-readable description of the failure.
            rule: A short identifier of which validation rule failed.
        """
        self.rule = rule
        super().__init__(message)


class UnknownAuthenticationTypeError(VeracodeSDKError):
    """Raised when an SDK Configuration names an authentication type
    outside the seven known `AuthenticationType` members.

    Attributes:
        type_name: The unrecognized `type` value from the configuration.
        suggestion: The closest known `AuthenticationType` value, or None.
    """

    def __init__(self, type_name: str, *, suggestion: str | None) -> None:
        """Initializes the error.

        Args:
            type_name: The unrecognized `type` value from the configuration.
            suggestion: The closest known `AuthenticationType` value, or None.
        """
        self.type_name = type_name
        self.suggestion = suggestion
        message = f"Unknown authentication type '{type_name}'."
        if suggestion:
            message += f"\n\nDid you mean '{suggestion}'?"
        super().__init__(message)


class ScannerVariableValidationError(VeracodeSDKError):
    """Raised for SDK-level Scanner Variable parameter/configuration
    validation failures.

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        """Initializes the error.

        Args:
            message: A human-readable description of the failure.
            rule: A short identifier of which validation rule failed.
        """
        self.rule = rule
        super().__init__(message)


class IsmGatewayValidationError(VeracodeSDKError):
    """Raised for SDK-level ISM Gateway parameter/configuration validation
    failures.

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        """Initializes the error.

        Args:
            message: A human-readable description of the failure.
            rule: A short identifier of which validation rule failed.
        """
        self.rule = rule
        super().__init__(message)


class GatewayNotFoundError(VeracodeSDKError):
    """Raised when no available ISM Gateway matches a requested name.

    Attributes:
        name: The gateway name that did not match any available gateway.
        suggestion: The closest available gateway name, or None if no
            close match was found.
    """

    def __init__(self, name: str, *, suggestion: str | None = None) -> None:
        """Initializes the error.

        Args:
            name: The gateway name that did not match any available gateway.
            suggestion: The closest available gateway name, or None.
        """
        self.name = name
        self.suggestion = suggestion
        message = f"ISM Gateway '{name}' was not found."
        if suggestion:
            message += f"\n\nDid you mean '{suggestion}'?"
        super().__init__(message)


class GatewayNameNotUniqueError(VeracodeSDKError):
    """Raised when more than one available ISM Gateway shares the
    requested name.

    Attributes:
        name: The ambiguous gateway name.
        matches: The `id` of every gateway that matched.
    """

    def __init__(self, name: str, *, matches: list[str]) -> None:
        """Initializes the error.

        Args:
            name: The ambiguous gateway name.
            matches: The `id` of every gateway that matched.
        """
        self.name = name
        self.matches = matches
        super().__init__(
            f"Multiple ISM Gateways are named '{name}'; cannot resolve unambiguously."
        )
