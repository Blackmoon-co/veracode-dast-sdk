"""Authentications: configure how Veracode DAST authenticates to a
protected application, for an existing Analysis Profile.

Seven independent mechanisms (`basic`, `application`, `certificate`,
`script`, `srm`, `oauth2`, `parameter`), each with its own Veracode API
endpoint and request shape. Callers author one small SDK Configuration
document naming a single mechanism; this service validates it, transforms
it into that mechanism's request, and dispatches to the correct endpoint.

Never logs or exposes a credential/secret/certificate/token/script body.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from veracode_dast.exceptions import (
    AuthenticationValidationError,
    UnknownAuthenticationTypeError,
)
from veracode_dast.models.authentication import (
    ApplicationAuthentication,
    ApplicationAuthenticationConfig,
    Authentication,
    AuthenticationConfiguration,
    AuthenticationType,
    BasicAuthenticationConfig,
    CertificateAuthentication,
    CertificateAuthenticationConfig,
    OAuth2Authentication,
    OAuth2AuthenticationConfig,
    OAuth2GrantType,
    ParameterAuthentication,
    ParameterAuthenticationConfig,
    ParameterAuthenticationEntry,
    ParameterAuthenticationType,
    ScriptAuthentication,
    ScriptAuthenticationConfig,
    ScriptConfig,
    ScriptType,
    SRMAuthentication,
    SRMAuthenticationConfig,
    SystemAuthentication,
)
from veracode_dast.utils.sdk_config import load_json_config, suggest_closest

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

_AUTHENTICATIONS_PATH = "/analysis_profiles/{analysis_profile_id}/authentications"

_MECHANISM_PATHS: Final[dict[AuthenticationType, str]] = {
    AuthenticationType.BASIC: "/analysis_profiles/{analysis_profile_id}/system_authentication",
    AuthenticationType.APPLICATION: (
        "/analysis_profiles/{analysis_profile_id}/application_authentication"
    ),
    AuthenticationType.CERTIFICATE: (
        "/analysis_profiles/{analysis_profile_id}/certificate_authentication"
    ),
    AuthenticationType.SCRIPT: "/analysis_profiles/{analysis_profile_id}/script_authentication",
    AuthenticationType.SRM: "/analysis_profiles/{analysis_profile_id}/srm_authentication",
    AuthenticationType.OAUTH2: "/analysis_profiles/{analysis_profile_id}/oauth2_authentication",
    AuthenticationType.PARAMETER: (
        "/analysis_profiles/{analysis_profile_id}/parameter_authentications"
    ),
}
# Every mechanism except PARAMETER supports (and this feature always sends)
# ?method=PATCH — parameter_authentications defines no `method` parameter.
_SUPPORTS_PATCH: Final[frozenset[AuthenticationType]] = frozenset(_MECHANISM_PATHS) - {
    AuthenticationType.PARAMETER
}

logger = logging.getLogger(__name__)


class AuthenticationsService:
    """Manages Authentication configuration for existing Analysis Profiles."""

    def __init__(self, http_client: HttpClient) -> None:
        """Initializes the service.

        Args:
            http_client: An `HttpClient` configured with
                `TARGET_CONFIGURATION_SERVICE_BASE_URL` — the same
                instance already constructed for `TargetsService`.
        """
        self._http_client = http_client

    def get(self, analysis_profile_id: str) -> AuthenticationConfiguration:
        """Gets the effective Authentication configuration for an Analysis
        Profile.

        Args:
            analysis_profile_id: The profile's unique identifier.

        Returns:
            The profile's Authentication configuration.

        Raises:
            AuthenticationValidationError: If `analysis_profile_id` is blank.
            VeracodeNotFoundError: If no profile exists with that ID.
        """
        self._require_non_blank(analysis_profile_id)
        response = self._http_client.get(
            _AUTHENTICATIONS_PATH.format(analysis_profile_id=analysis_profile_id)
        )
        config = AuthenticationConfiguration.from_api(response.data)  # type: ignore[arg-type]
        logger.info(
            "Retrieved authentication configuration for analysis profile %s",
            analysis_profile_id,
        )
        return config

    def update(
        self,
        analysis_profile_id: str,
        config_file: str | Path | dict[str, Any],
    ) -> Authentication:
        """Configures exactly one authentication mechanism from an SDK
        Configuration document.

        Args:
            analysis_profile_id: The profile's unique identifier.
            config_file: A path to an SDK Configuration JSON file, or an
                already-loaded dict naming exactly one mechanism.

        Returns:
            The server's response, typed for whichever mechanism was
            configured.

        Raises:
            AuthenticationValidationError: If `analysis_profile_id` is
                blank, or the configuration fails structural/per-mechanism
                validation.
            UnknownAuthenticationTypeError: If the configured `type` is not
                one of the seven known mechanisms.
            VeracodeNotFoundError: If no profile exists with that ID.
        """
        self._require_non_blank(analysis_profile_id)

        config = load_json_config(config_file)
        auth_type, body = self._validate_and_transform(config)

        path = _MECHANISM_PATHS[auth_type].format(analysis_profile_id=analysis_profile_id)
        params = {"method": "PATCH"} if auth_type in _SUPPORTS_PATCH else None

        logger.info(
            "Updating %s authentication for analysis profile %s",
            auth_type.value,
            analysis_profile_id,
        )
        response = self._http_client.put(path, json=body, params=params)
        result = self._build_response(auth_type, response.data)
        logger.info(
            "%s authentication updated for analysis profile %s",
            auth_type.value,
            analysis_profile_id,
        )
        return result

    def _validate_and_transform(
        self, config: dict[str, Any]
    ) -> tuple[AuthenticationType, dict[str, Any] | list[Any]]:
        auth = config.get("authentication") if isinstance(config, dict) else None
        if not isinstance(auth, dict):
            raise AuthenticationValidationError(
                "SDK Configuration must contain an 'authentication' object",
                rule="authentication_key_required",
            )
        type_value = auth.get("type")
        if not isinstance(type_value, str):
            raise AuthenticationValidationError(
                "SDK Configuration's 'authentication.type' is required", rule="type_required"
            )
        known = {member.value for member in AuthenticationType}
        if type_value not in known:
            raise UnknownAuthenticationTypeError(
                type_value, suggestion=suggest_closest(type_value, known)
            )
        auth_type = AuthenticationType(type_value)

        body: dict[str, Any] | list[Any]
        match auth_type:
            case AuthenticationType.BASIC:
                body = self._basic_config(auth).to_api()
            case AuthenticationType.APPLICATION:
                body = self._application_config(auth).to_api()
            case AuthenticationType.CERTIFICATE:
                body = self._certificate_config(auth).to_api()
            case AuthenticationType.SCRIPT:
                body = self._script_config(auth).to_api()
            case AuthenticationType.SRM:
                body = self._srm_config(auth).to_api()
            case AuthenticationType.OAUTH2:
                body = self._oauth2_config(auth).to_api()
            case AuthenticationType.PARAMETER:
                body = self._parameter_config(auth).to_api()
            case _:  # pragma: no cover - AuthenticationType is a closed set
                raise AssertionError(f"Unhandled authentication type: {auth_type}")
        return auth_type, body

    @staticmethod
    def _build_response(auth_type: AuthenticationType, data: Any) -> Authentication:
        match auth_type:
            case AuthenticationType.BASIC:
                return SystemAuthentication.from_api(data)
            case AuthenticationType.APPLICATION:
                return ApplicationAuthentication.from_api(data)
            case AuthenticationType.CERTIFICATE:
                return CertificateAuthentication.from_api(data)
            case AuthenticationType.SCRIPT:
                return ScriptAuthentication.from_api(data)
            case AuthenticationType.SRM:
                return SRMAuthentication.from_api(data)
            case AuthenticationType.OAUTH2:
                return OAuth2Authentication.from_api(data)
            case AuthenticationType.PARAMETER:
                return [ParameterAuthentication.from_api(item) for item in data]
            case _:  # pragma: no cover - AuthenticationType is a closed set
                raise AssertionError(f"Unhandled authentication type: {auth_type}")

    @staticmethod
    def _basic_config(auth: dict[str, Any]) -> BasicAuthenticationConfig:
        username = auth.get("username")
        if not isinstance(username, str) or not username.strip():
            raise AuthenticationValidationError(
                "'username' is required for type 'basic'", rule="basic_username_required"
            )
        password = auth.get("password")
        if not isinstance(password, str) or not password.strip():
            raise AuthenticationValidationError(
                "'password' is required for type 'basic'", rule="basic_password_required"
            )
        return BasicAuthenticationConfig(username=username, password=password)

    @staticmethod
    def _application_config(auth: dict[str, Any]) -> ApplicationAuthenticationConfig:
        username = auth.get("username")
        if not isinstance(username, str) or not username.strip():
            raise AuthenticationValidationError(
                "'username' is required for type 'application'",
                rule="application_username_required",
            )
        password = auth.get("password")
        if not isinstance(password, str) or not password.strip():
            raise AuthenticationValidationError(
                "'password' is required for type 'application'",
                rule="application_password_required",
            )
        login_url = auth.get("login_url")
        if not isinstance(login_url, str) or not login_url.strip():
            raise AuthenticationValidationError(
                "'login_url' is required for type 'application'",
                rule="application_login_url_required",
            )
        return ApplicationAuthenticationConfig(
            username=username, password=password, login_url=login_url
        )

    @staticmethod
    def _certificate_config(auth: dict[str, Any]) -> CertificateAuthenticationConfig:
        base64_pkcs12 = auth.get("base64_pkcs12")
        if not isinstance(base64_pkcs12, str) or not base64_pkcs12.strip():
            raise AuthenticationValidationError(
                "'base64_pkcs12' is required for type 'certificate'",
                rule="certificate_base64_pkcs12_required",
            )
        cert_name = auth.get("cert_name")
        password = auth.get("password")
        return CertificateAuthenticationConfig(
            base64_pkcs12=base64_pkcs12, cert_name=cert_name, password=password
        )

    @staticmethod
    def _script_config(auth: dict[str, Any]) -> ScriptAuthenticationConfig:
        login_script = auth.get("login_script")
        logout_script = auth.get("logout_script")
        if login_script is None and logout_script is None:
            raise AuthenticationValidationError(
                "At least one of 'login_script'/'logout_script' is required for type 'script'",
                rule="script_requires_login_or_logout",
            )
        return ScriptAuthenticationConfig(
            login_script=AuthenticationsService._script_entry(login_script),
            logout_script=AuthenticationsService._script_entry(logout_script),
        )

    @staticmethod
    def _script_entry(script: Any) -> ScriptConfig | None:
        if script is None:
            return None
        script_type_value = script.get("script_type") if isinstance(script, dict) else None
        script_type = None
        if script_type_value:
            try:
                script_type = ScriptType(script_type_value)
            except ValueError as exc:
                raise AuthenticationValidationError(
                    f"'{script_type_value}' is not a valid script_type", rule="script_type_invalid"
                ) from exc
        return ScriptConfig(
            script_name=script.get("script_name") if isinstance(script, dict) else None,
            script_type=script_type,
            script_body=script.get("script_body") if isinstance(script, dict) else None,
        )

    @staticmethod
    def _srm_config(auth: dict[str, Any]) -> SRMAuthenticationConfig:
        script_body = auth.get("script_body")
        if not isinstance(script_body, str) or not script_body.strip():
            raise AuthenticationValidationError(
                "'script_body' is required for type 'srm'", rule="srm_script_body_required"
            )
        script_type_value = auth.get("script_type")
        script_type = None
        if script_type_value:
            try:
                script_type = ScriptType(script_type_value)
            except ValueError as exc:
                raise AuthenticationValidationError(
                    f"'{script_type_value}' is not a valid script_type", rule="script_type_invalid"
                ) from exc
        return SRMAuthenticationConfig(
            script_body=script_body, script_name=auth.get("script_name"), script_type=script_type
        )

    @staticmethod
    def _oauth2_config(auth: dict[str, Any]) -> OAuth2AuthenticationConfig:
        grant_type_value = auth.get("grant_type")
        if grant_type_value is None:
            raise AuthenticationValidationError(
                "'grant_type' is required for type 'oauth2'", rule="oauth2_grant_type_required"
            )
        try:
            grant_type = OAuth2GrantType(grant_type_value)
        except ValueError as exc:
            raise AuthenticationValidationError(
                f"'{grant_type_value}' is not a valid grant_type", rule="oauth2_grant_type_invalid"
            ) from exc
        return OAuth2AuthenticationConfig(
            grant_type=grant_type,
            access_token_url=auth.get("access_token_url"),
            client_id=auth.get("client_id"),
            client_secret=auth.get("client_secret"),
            authorization_url=auth.get("authorization_url"),
            username=auth.get("username"),
            password=auth.get("password"),
            redirect_url=auth.get("redirect_url"),
            scope=auth.get("scope"),
            use_openid_connect=auth.get("use_openid_connect"),
            openid_url=auth.get("openid_url"),
        )

    @staticmethod
    def _parameter_config(auth: dict[str, Any]) -> ParameterAuthenticationConfig:
        parameters = auth.get("parameters")
        if not isinstance(parameters, list):
            raise AuthenticationValidationError(
                "'parameters' is required for type 'parameter' and must be an array",
                rule="parameter_parameters_required",
            )
        entries: list[ParameterAuthenticationEntry] = []
        for index, entry in enumerate(parameters):
            if not isinstance(entry, dict):
                raise AuthenticationValidationError(
                    f"parameters[{index}] must be an object", rule="parameter_entry_invalid"
                )
            title = entry.get("title")
            key = entry.get("key")
            type_value = entry.get("type")
            value = entry.get("value")
            if (
                not isinstance(title, str)
                or not title.strip()
                or not isinstance(key, str)
                or not key.strip()
                or not isinstance(type_value, str)
                or type_value not in {member.value for member in ParameterAuthenticationType}
                or (value is not None and not isinstance(value, str))
            ):
                raise AuthenticationValidationError(
                    f"parameters[{index}] must have a non-blank 'title', 'key', and a valid 'type'",
                    rule="parameter_entry_invalid",
                )
            entries.append(
                ParameterAuthenticationEntry(
                    title=title,
                    type=ParameterAuthenticationType(type_value),
                    key=key,
                    id=entry.get("id"),
                    value=value,
                )
            )
        return ParameterAuthenticationConfig(parameters=entries)

    @staticmethod
    def _require_non_blank(analysis_profile_id: str) -> None:
        if not analysis_profile_id or not analysis_profile_id.strip():
            raise AuthenticationValidationError(
                "analysis_profile_id must not be blank", rule="analysis_profile_id_required"
            )
