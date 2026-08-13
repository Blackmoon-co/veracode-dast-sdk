"""Generic, resource-agnostic HTTP client for Veracode REST APIs.

This is the only component in the SDK allowed to import ``requests``. Every
SDK service depends on an instance of :class:`HttpClient` instead of calling
``requests`` directly. Authentication is always injected, never created —
this module never imports ``auth.py``/``config.py``.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

import requests
from requests.adapters import HTTPAdapter
from requests.auth import AuthBase
from urllib3.util.retry import Retry

from veracode_dast.auth import get_veracode_auth
from veracode_dast.exceptions import (
    VeracodeApiError,
    VeracodeAuthenticationError,
    VeracodeAuthorizationError,
    VeracodeConflictError,
    VeracodeConnectionError,
    VeracodeNotFoundError,
    VeracodeTimeoutError,
    VeracodeValidationError,
)
from veracode_dast.services.analysis_profiles import AnalysisProfilesService
from veracode_dast.services.analysis_runs import AnalysisRunsService
from veracode_dast.services.api_specifications import ApiSpecificationsService
from veracode_dast.services.authentications import AuthenticationsService
from veracode_dast.services.ism_gateways import IsmGatewaysService
from veracode_dast.services.scanner_variables import ScannerVariablesService
from veracode_dast.services.scanners import ScannersService
from veracode_dast.services.targets import TARGET_CONFIGURATION_SERVICE_BASE_URL, TargetsService
from veracode_dast.services.teams import ADMIN_API_BASE_URL, TeamService

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT: Final = 30.0
DEFAULT_MAX_RETRIES: Final = 3
_RETRY_STATUS_FORCELIST: Final = (429, 500, 502, 503, 504)
_RETRIABLE_METHODS: Final = frozenset({"GET", "PUT", "DELETE", "HEAD", "OPTIONS"})
_STATUS_EXCEPTIONS: Final[dict[int, type[VeracodeApiError]]] = {
    401: VeracodeAuthenticationError,
    403: VeracodeAuthorizationError,
    404: VeracodeNotFoundError,
    409: VeracodeConflictError,
    422: VeracodeValidationError,
}


@dataclass(frozen=True)
class HttpResponse:
    """A plain, requests-independent view of an HTTP response.

    Attributes:
        status_code: The HTTP status code of a successful (2xx) response.
        data: The deserialized JSON body as a dict/list, the raw response
            bytes when the request was made with ``raw=True``, or None if
            the response body was empty. Never a typed model.
        headers: The response headers.
    """

    status_code: int
    data: dict[str, Any] | list[Any] | bytes | None
    headers: Mapping[str, str]


class HttpClient:
    """Generic, resource-agnostic HTTP client for the Veracode REST APIs.

    This is the only component in the SDK allowed to import ``requests``.
    Every SDK service must depend on an instance of this class instead of
    calling ``requests`` directly.
    """

    def __init__(
        self,
        base_url: str,
        auth: AuthBase,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """Creates a configured HTTP client for one Veracode API.

        Args:
            base_url: Scheme + host (+ path prefix) every request made by
                this instance is resolved against, e.g.
                ``"https://api.veracode.com/dae/api/tcs-api/api/v1"``.
                Required — this class has no default, since a given
                instance is always scoped to one specific Veracode API.
            auth: A ready-made ``requests``-compatible auth provider (e.g.
                the result of calling ``get_veracode_auth()``). Required —
                this class never creates authentication itself.
            timeout: Seconds to wait for a response before raising
                ``VeracodeTimeoutError``.
            max_retries: Maximum retry attempts for idempotent methods on
                connection errors or the statuses in
                ``_RETRY_STATUS_FORCELIST``.
        """
        self._base_url = base_url
        self._auth = auth
        self._timeout = timeout
        self._session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=_RETRY_STATUS_FORCELIST,
            allowed_methods=_RETRIABLE_METHODS,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        raw: bool = False,
    ) -> HttpResponse:
        """Sends an HTTP GET request.

        Args:
            path: Request path, joined onto this client's ``base_url``.
            params: Query parameters.
            headers: Additional headers, overriding defaults on conflict.
            raw: If True, returns the raw response body as ``bytes``
                instead of parsing it as JSON. Use for binary responses
                (e.g. ``Content-Type: application/octet-stream``).

        Returns:
            The resulting response.
        """
        return self._request("GET", path, params=params, headers=headers, raw=raw)

    def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        files: Mapping[str, tuple[str, bytes, str]] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        """Sends an HTTP POST request.

        Args:
            path: Request path, joined onto this client's ``base_url``.
            json: JSON request body. Mutually exclusive with ``files``.
            files: Multipart file fields, each a ``(filename, content,
                content_type)`` tuple, sent as ``multipart/form-data``.
                Mutually exclusive with ``json``.
            params: Query parameters.
            headers: Additional headers, overriding defaults on conflict.

        Returns:
            The resulting response.
        """
        return self._request("POST", path, json=json, files=files, params=params, headers=headers)

    def put(
        self,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        """Sends an HTTP PUT request.

        Args:
            path: Request path, joined onto this client's ``base_url``.
            json: JSON request body.
            params: Query parameters.
            headers: Additional headers, overriding defaults on conflict.

        Returns:
            The resulting response.
        """
        return self._request("PUT", path, json=json, params=params, headers=headers)

    def patch(
        self,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        """Sends an HTTP PATCH request.

        Args:
            path: Request path, joined onto this client's ``base_url``.
            json: JSON request body.
            params: Query parameters.
            headers: Additional headers, overriding defaults on conflict.

        Returns:
            The resulting response.
        """
        return self._request("PATCH", path, json=json, params=params, headers=headers)

    def delete(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        """Sends an HTTP DELETE request.

        Args:
            path: Request path, joined onto this client's ``base_url``.
            params: Query parameters.
            headers: Additional headers, overriding defaults on conflict.

        Returns:
            The resulting response.
        """
        return self._request("DELETE", path, params=params, headers=headers)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        files: Mapping[str, tuple[str, bytes, str]] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        raw: bool = False,
    ) -> HttpResponse:
        url = f"{self._base_url.rstrip('/')}/{path.lstrip('/')}"
        request_headers: dict[str, str] = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)

        logger.debug("HTTP %s %s", method, url)
        try:
            response = self._session.request(
                method,
                url,
                json=json,
                files=files,
                params=params,
                headers=request_headers,
                auth=self._auth,
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout as exc:
            logger.error("HTTP %s %s failed: %s", method, url, type(exc).__name__)
            raise VeracodeTimeoutError(
                f"Request timed out: {method} {url}", method=method, url=url
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("HTTP %s %s failed: %s", method, url, type(exc).__name__)
            raise VeracodeConnectionError(
                f"Connection failed: {method} {url}", method=method, url=url
            ) from exc

        if response.status_code >= 400:
            exception_cls = _STATUS_EXCEPTIONS.get(response.status_code, VeracodeApiError)
            try:
                body: dict[str, Any] | list[Any] | str | None = response.json()
            except ValueError:
                body = response.text or None
            logger.error(
                "HTTP %s %s failed: %s", method, url, exception_cls.__name__
            )
            raise exception_cls(
                f"{method} {url} failed with status {response.status_code}",
                method=method,
                url=url,
                status_code=response.status_code,
                response_body=body,
            )

        logger.debug("HTTP %s %s -> %s", method, url, response.status_code)

        if raw:
            return HttpResponse(response.status_code, response.content or None, response.headers)

        if not response.content:
            return HttpResponse(response.status_code, None, response.headers)
        try:
            return HttpResponse(response.status_code, response.json(), response.headers)
        except ValueError as exc:
            logger.error("HTTP %s %s failed: %s", method, url, type(exc).__name__)
            raise VeracodeApiError(
                f"{method} {url} returned a non-JSON 2xx body",
                method=method,
                url=url,
                status_code=response.status_code,
                response_body=response.text,
            ) from exc


class VeracodeClient:
    """Public SDK entry point, exposing one attribute per Veracode resource.

    Reads credentials from the environment once (via `get_veracode_auth()`)
    and reuses the resulting auth provider across every Veracode API
    domain this SDK talks to.
    """

    def __init__(self) -> None:
        """Initializes every configured service.

        Raises:
            MissingCredentialsError: If required credential environment
                variables are unset or empty.
        """
        auth = get_veracode_auth()
        self.teams = TeamService(HttpClient(base_url=ADMIN_API_BASE_URL, auth=auth))
        tcs_http_client = HttpClient(base_url=TARGET_CONFIGURATION_SERVICE_BASE_URL, auth=auth)
        self.targets = TargetsService(tcs_http_client)
        self.api_specifications = ApiSpecificationsService(tcs_http_client)
        self.analysis_profiles = AnalysisProfilesService(tcs_http_client)
        self.scanners = ScannersService(tcs_http_client)
        self.authentications = AuthenticationsService(tcs_http_client)
        self.scanner_variables = ScannerVariablesService(tcs_http_client)
        self.ism_gateways = IsmGatewaysService(tcs_http_client)
        self.analysis_runs = AnalysisRunsService(tcs_http_client)
