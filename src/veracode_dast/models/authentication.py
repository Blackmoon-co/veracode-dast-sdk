"""Typed models for the DAST Target Configuration Service's Authentication
resource.

Seven independent, simultaneously-configurable mechanisms — no discriminated
union with one active member. Every field carrying a credential, secret,
certificate, or script body is excluded from the default `repr()`/`str()`
via `field(repr=False)`, and never logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from veracode_dast.models.common import InheritedValue


class AuthenticationType(StrEnum):
    """The seven SDK Configuration discriminator values.

    Used only by this SDK — not sent to the Veracode API, which has no
    `type` field on any authentication mechanism's schema.
    """

    BASIC = "basic"
    APPLICATION = "application"
    CERTIFICATE = "certificate"
    SCRIPT = "script"
    SRM = "srm"
    OAUTH2 = "oauth2"
    PARAMETER = "parameter"


class ScriptType(StrEnum):
    """The format of a login/logout or SRM script."""

    SELENIUM = "SELENIUM"
    JAVASCRIPT = "JAVASCRIPT"


class OAuth2GrantType(StrEnum):
    """The OAuth 2.0 grant type used to obtain a token."""

    CLIENT_CREDENTIALS = "CLIENT_CREDENTIALS"
    PASSWORD = "PASSWORD"
    AUTHORIZATION_CODE = "AUTHORIZATION_CODE"
    AUTHORIZATION_CODE_PKCE = "AUTHORIZATION_CODE_PKCE"


class ParameterAuthenticationType(StrEnum):
    """Where a Parameter Authentication value is placed on each request."""

    GET_PARAMETER = "GET_PARAMETER"
    HTTP_HEADER = "HTTP_HEADER"
    COOKIE = "COOKIE"
    LOCAL_STORAGE = "LOCAL_STORAGE"
    SESSION_STORAGE = "SESSION_STORAGE"


# --- Response models -------------------------------------------------------


@dataclass(frozen=True)
class Script:
    """A login or logout script.

    Attributes:
        script_name: The script's display name.
        script_type: The script's format.
        script_body: The script's source. Never logged or shown in repr.
    """

    script_name: str | None = None
    script_type: ScriptType | None = None
    script_body: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any] | None) -> Script | None:
        """Builds a `Script` from a raw API object, or None if absent.

        Args:
            data: The raw script object, or None.

        Returns:
            The corresponding `Script`, or None.
        """
        if data is None:
            return None
        script_type = data.get("script_type")
        return cls(
            script_name=data.get("script_name"),
            script_type=ScriptType(script_type) if script_type else None,
            script_body=data.get("script_body"),
        )


@dataclass(frozen=True)
class SystemAuthentication:
    """HTTP Basic (system) authentication.

    Attributes:
        username: The username to authenticate with.
        password: The password to authenticate with. Never logged or
            shown in repr.
    """

    username: str
    password: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> SystemAuthentication:
        """Builds a `SystemAuthentication` from an API response object."""
        return cls(username=data["username"], password=data.get("password"))


@dataclass(frozen=True)
class ApplicationAuthentication:
    """Form-based application authentication.

    Attributes:
        username: The username to authenticate with.
        login_url: The application's login URL.
        password: The password to authenticate with. Never logged or
            shown in repr.
        enable_ai_login: Whether AI-assisted login is enabled. Response-only
            — never accepted by `ApplicationAuthenticationConfig`.
    """

    username: str
    login_url: str
    password: str | None = field(default=None, repr=False)
    enable_ai_login: bool | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ApplicationAuthentication:
        """Builds an `ApplicationAuthentication` from an API response object."""
        return cls(
            username=data["username"],
            login_url=data["login_url"],
            password=data.get("password"),
            enable_ai_login=data.get("enable_ai_login"),
        )


@dataclass(frozen=True)
class CertificateAuthentication:
    """Client certificate authentication.

    Attributes:
        cert_name: The certificate's display name.
        base64_pkcs12: The base64-encoded PKCS#12 certificate. Never
            logged or shown in repr.
        password: The certificate's password. Never logged or shown in
            repr.
    """

    cert_name: str | None = None
    base64_pkcs12: str | None = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CertificateAuthentication:
        """Builds a `CertificateAuthentication` from an API response object."""
        return cls(
            cert_name=data.get("cert_name"),
            base64_pkcs12=data.get("base64_pkcs12"),
            password=data.get("password"),
        )


@dataclass(frozen=True)
class ScriptAuthentication:
    """Login/logout script authentication.

    Attributes:
        login_script: The login script, if configured.
        logout_script: The logout script, if configured.
    """

    login_script: Script | None = None
    logout_script: Script | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ScriptAuthentication:
        """Builds a `ScriptAuthentication` from an API response object."""
        return cls(
            login_script=Script.from_api(data.get("login_script")),
            logout_script=Script.from_api(data.get("logout_script")),
        )


@dataclass(frozen=True)
class SRMAuthentication:
    """Scriptable Request Modification authentication.

    Attributes:
        script_name: The script's display name.
        script_type: The script's format.
        script_body: The script's source (base64 encoded). Never logged or
            shown in repr.
    """

    script_name: str | None = None
    script_type: ScriptType | None = None
    script_body: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> SRMAuthentication:
        """Builds an `SRMAuthentication` from an API response object."""
        script_type = data.get("script_type")
        return cls(
            script_name=data.get("script_name"),
            script_type=ScriptType(script_type) if script_type else None,
            script_body=data.get("script_body"),
        )


@dataclass(frozen=True)
class OAuth2Authentication:
    """OAuth 2.0 authentication.

    Attributes:
        grant_type: The OAuth 2.0 grant type used to obtain a token.
        access_token_url: The token endpoint URL.
        client_id: The OAuth client ID.
        authorization_url: The authorization endpoint URL.
        username: The resource-owner username, for the `PASSWORD` grant.
        redirect_url: The redirect URL, for authorization-code grants.
        scope: The requested OAuth scope.
        use_openid_connect: Whether OpenID Connect is used.
        openid_url: The OpenID Connect discovery URL.
        client_secret: The OAuth client secret. Never logged or shown in
            repr.
        password: The resource-owner password, for the `PASSWORD` grant.
            Never logged or shown in repr.
    """

    grant_type: OAuth2GrantType
    access_token_url: str | None = None
    client_id: str | None = None
    authorization_url: str | None = None
    username: str | None = None
    redirect_url: str | None = None
    scope: str | None = None
    use_openid_connect: bool = False
    openid_url: str | None = None
    client_secret: str | None = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> OAuth2Authentication:
        """Builds an `OAuth2Authentication` from an API response object."""
        return cls(
            grant_type=OAuth2GrantType(data["grant_type"]),
            access_token_url=data.get("access_token_url"),
            client_id=data.get("client_id"),
            authorization_url=data.get("authorization_url"),
            username=data.get("username"),
            redirect_url=data.get("redirect_url"),
            scope=data.get("scope"),
            use_openid_connect=data.get("use_openid_connect", False),
            openid_url=data.get("openid_url"),
            client_secret=data.get("client_secret"),
            password=data.get("password"),
        )


@dataclass(frozen=True)
class ParameterAuthentication:
    """One Parameter Authentication entry.

    Attributes:
        title: A display title for this entry.
        type: Where this value is placed on each request.
        key: The parameter/header/cookie/storage key name.
        id: The entry's API-assigned identifier, if any.
        value: The parameter's value. Never logged or shown in repr.
    """

    title: str
    type: ParameterAuthenticationType
    key: str
    id: str | None = None
    value: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ParameterAuthentication:
        """Builds a `ParameterAuthentication` from an API response object."""
        return cls(
            title=data["title"],
            type=ParameterAuthenticationType(data["type"]),
            key=data["key"],
            id=data.get("id"),
            value=data.get("value"),
        )


@dataclass(frozen=True)
class AuthenticationConfiguration:
    """The complete effective Authentication configuration for an Analysis
    Profile — one optional, inheritance-aware field per mechanism.

    Attributes:
        system_authentication: HTTP Basic authentication, if configured.
        application_authentication: Form-based authentication, if configured.
        certificate_authentication: Client certificate authentication, if
            configured.
        script_authentication: Login/logout script authentication, if
            configured.
        srm_authentication: Scriptable Request Modification authentication,
            if configured.
        oauth2_authentication: OAuth 2.0 authentication, if configured.
        parameter_authentications: Parameter Authentication entries, if
            configured.
    """

    system_authentication: InheritedValue[SystemAuthentication] | None = None
    application_authentication: InheritedValue[ApplicationAuthentication] | None = None
    certificate_authentication: InheritedValue[CertificateAuthentication] | None = None
    script_authentication: InheritedValue[ScriptAuthentication] | None = None
    srm_authentication: InheritedValue[SRMAuthentication] | None = None
    oauth2_authentication: InheritedValue[OAuth2Authentication] | None = None
    parameter_authentications: InheritedValue[list[ParameterAuthentication]] | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AuthenticationConfiguration:
        """Builds an `AuthenticationConfiguration` from an
        `EffectiveAuthentications` response.

        Each field is None when the API returns null for that mechanism.

        Args:
            data: The raw response body.

        Returns:
            The corresponding `AuthenticationConfiguration`.
        """

        def _wrap(key: str, builder: Any) -> InheritedValue[Any] | None:
            wrapper = data.get(key)
            if wrapper is None:
                return None
            return InheritedValue(
                effective_value=builder(wrapper["effective_value"]),
                is_inherited=wrapper["is_inherited"],
            )

        return cls(
            system_authentication=_wrap("system_authentication", SystemAuthentication.from_api),
            application_authentication=_wrap(
                "application_authentication", ApplicationAuthentication.from_api
            ),
            certificate_authentication=_wrap(
                "certificate_authentication", CertificateAuthentication.from_api
            ),
            script_authentication=_wrap("script_authentication", ScriptAuthentication.from_api),
            srm_authentication=_wrap("srm_authentication", SRMAuthentication.from_api),
            oauth2_authentication=_wrap("oauth2_authentication", OAuth2Authentication.from_api),
            parameter_authentications=_wrap(
                "parameter_authentications",
                lambda items: [ParameterAuthentication.from_api(item) for item in items],
            ),
        )


Authentication = (
    SystemAuthentication
    | ApplicationAuthentication
    | CertificateAuthentication
    | ScriptAuthentication
    | SRMAuthentication
    | OAuth2Authentication
    | list[ParameterAuthentication]
)
"""The return type of `AuthenticationsService.update()` — the server's
actual response shape for whichever mechanism was configured."""


# --- SDK Configuration models -----------------------------------------------


@dataclass(frozen=True)
class BasicAuthenticationConfig:
    """SDK Configuration for `type: "basic"`.

    Attributes:
        username: The username to authenticate with.
        password: The password to authenticate with.
    """

    username: str
    password: str

    def to_api(self) -> dict[str, Any]:
        """Builds the `SystemAuthenticationUpdateRequest` body."""
        return {"username": self.username, "password": self.password}


@dataclass(frozen=True)
class ApplicationAuthenticationConfig:
    """SDK Configuration for `type: "application"`.

    Attributes:
        username: The username to authenticate with.
        password: The password to authenticate with.
        login_url: The application's login URL.
    """

    username: str
    password: str
    login_url: str

    def to_api(self) -> dict[str, Any]:
        """Builds the `ApplicationAuthenticationUpdateRequest` body."""
        return {"username": self.username, "password": self.password, "login_url": self.login_url}


@dataclass(frozen=True)
class CertificateAuthenticationConfig:
    """SDK Configuration for `type: "certificate"`.

    Attributes:
        base64_pkcs12: The base64-encoded PKCS#12 certificate.
        cert_name: The certificate's display name, if changing.
        password: The certificate's password, if changing.
    """

    base64_pkcs12: str
    cert_name: str | None = None
    password: str | None = None

    def to_api(self) -> dict[str, Any]:
        """Builds the `CertificateAuthenticationUpdateRequest` body."""
        body: dict[str, Any] = {"base64_pkcs12": self.base64_pkcs12}
        if self.cert_name is not None:
            body["cert_name"] = self.cert_name
        if self.password is not None:
            body["password"] = self.password
        return body


@dataclass(frozen=True)
class ScriptConfig:
    """SDK Configuration for one login or logout script.

    Attributes:
        script_name: The script's display name, if changing.
        script_type: The script's format, if changing.
        script_body: The script's source, if changing.
    """

    script_name: str | None = None
    script_type: ScriptType | None = None
    script_body: str | None = None

    def to_api(self) -> dict[str, Any]:
        """Builds this script's `Script` request-body shape."""
        body: dict[str, Any] = {}
        if self.script_name is not None:
            body["script_name"] = self.script_name
        if self.script_type is not None:
            body["script_type"] = self.script_type.value
        if self.script_body is not None:
            body["script_body"] = self.script_body
        return body


@dataclass(frozen=True)
class ScriptAuthenticationConfig:
    """SDK Configuration for `type: "script"`.

    Attributes:
        login_script: The login script, if changing.
        logout_script: The logout script, if changing.
    """

    login_script: ScriptConfig | None = None
    logout_script: ScriptConfig | None = None

    def to_api(self) -> dict[str, Any]:
        """Builds the `ScriptAuthenticationUpdateRequest` body."""
        body: dict[str, Any] = {}
        if self.login_script is not None:
            body["login_script"] = self.login_script.to_api()
        if self.logout_script is not None:
            body["logout_script"] = self.logout_script.to_api()
        return body


@dataclass(frozen=True)
class SRMAuthenticationConfig:
    """SDK Configuration for `type: "srm"`.

    Attributes:
        script_body: The SRM script's source (base64 encoded).
        script_name: The script's display name, if changing.
        script_type: The script's format, if changing.
    """

    script_body: str
    script_name: str | None = None
    script_type: ScriptType | None = None

    def to_api(self) -> dict[str, Any]:
        """Builds the `SRMAuthenticationUpdateRequest` body."""
        body: dict[str, Any] = {"script_body": self.script_body}
        if self.script_name is not None:
            body["script_name"] = self.script_name
        if self.script_type is not None:
            body["script_type"] = self.script_type.value
        return body


@dataclass(frozen=True)
class OAuth2AuthenticationConfig:
    """SDK Configuration for `type: "oauth2"`.

    Attributes:
        grant_type: The OAuth 2.0 grant type used to obtain a token.
        access_token_url: The token endpoint URL, if changing.
        client_id: The OAuth client ID, if changing.
        client_secret: The OAuth client secret, if changing.
        authorization_url: The authorization endpoint URL, if changing.
        username: The resource-owner username, if changing.
        password: The resource-owner password, if changing.
        redirect_url: The redirect URL, if changing.
        scope: The requested OAuth scope, if changing.
        use_openid_connect: Whether OpenID Connect is used, if changing.
        openid_url: The OpenID Connect discovery URL, if changing.
    """

    grant_type: OAuth2GrantType
    access_token_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    authorization_url: str | None = None
    username: str | None = None
    password: str | None = None
    redirect_url: str | None = None
    scope: str | None = None
    use_openid_connect: bool | None = None
    openid_url: str | None = None

    def to_api(self) -> dict[str, Any]:
        """Builds the `OAuth2AuthenticationUpdateRequest` body."""
        body: dict[str, Any] = {"grant_type": self.grant_type.value}
        optional: dict[str, Any] = {
            "access_token_url": self.access_token_url,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "authorization_url": self.authorization_url,
            "username": self.username,
            "password": self.password,
            "redirect_url": self.redirect_url,
            "scope": self.scope,
            "use_openid_connect": self.use_openid_connect,
            "openid_url": self.openid_url,
        }
        for key, value in optional.items():
            if value is not None:
                body[key] = value
        return body


@dataclass(frozen=True)
class ParameterAuthenticationEntry:
    """SDK Configuration for one Parameter Authentication entry.

    Attributes:
        title: A display title for this entry.
        type: Where this value is placed on each request.
        key: The parameter/header/cookie/storage key name.
        id: The entry's existing identifier, if updating one in place.
        value: The parameter's value.
    """

    title: str
    type: ParameterAuthenticationType
    key: str
    id: str | None = None
    value: str | None = None

    def to_api(self) -> dict[str, Any]:
        """Builds this entry's `ParameterAuthentication` request-body shape."""
        body: dict[str, Any] = {"title": self.title, "type": self.type.value, "key": self.key}
        if self.id is not None:
            body["id"] = self.id
        if self.value is not None:
            body["value"] = self.value
        return body


@dataclass(frozen=True)
class ParameterAuthenticationConfig:
    """SDK Configuration for `type: "parameter"`.

    Attributes:
        parameters: The complete list of Parameter Authentication entries.
            Replaces the entire existing list (§3.5 of requirements.md).
    """

    parameters: list[ParameterAuthenticationEntry]

    def to_api(self) -> list[dict[str, Any]]:
        """Builds the `ParameterAuthenticationsUpdateRequest` body (a bare
        array, not an object)."""
        return [entry.to_api() for entry in self.parameters]
