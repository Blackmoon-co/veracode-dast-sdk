# Design — Authentications

Implements [requirements.md](requirements.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Extends
[Target Management](../target-management/design.md) (reuses its base-URL
constant) and [Scanner Profiles](../scanners-profiles/design.md) (reuses
its configuration-loading pipeline and `utils/sdk_config.py`).

---

## 1. Overview

`AuthenticationsService.get()` is a thin read — one HTTP call, one model
built from the response — the same shape as
`ApiSpecificationsService.get()`/`ScannersService.get()`. The interesting
part of this feature is `update()`: it must turn one SDK Configuration
document into the correct one of **seven** different Veracode API
requests, entirely client-side, before any HTTP call happens. Where
[Scanner Profiles](../scanners-profiles/design.md) had exactly one
transformation to implement, this feature has seven — one per
authentication mechanism — selected by a `type` discriminator. §2 shows
both shapes; §6–§7 work through the per-mechanism dispatch.

## 2. Architecture

This feature adds one service and its models to the existing layered
architecture (AGENTS.md §3) — no new layer, no change to `HttpClient`:

```
VeracodeClient
      ↓
  HTTP Client              (reused, unmodified)
      ↓
AuthenticationsService      ← THIS FEATURE
      ↓
AuthenticationConfiguration, SystemAuthentication, ApplicationAuthentication,
CertificateAuthentication, ScriptAuthentication, SRMAuthentication,
OAuth2Authentication, ParameterAuthentication   (models)
      ↓
  REST API  (DAST Target Configuration Service, same base URL as Targets)
```

`get()` is a single call, one model, no dispatch:

```
GET /analysis_profiles/{id}/authentications
      ↓
AuthenticationConfiguration.from_api(response.data)
```

`update()` carries the SDK Configuration through four stages, the third of
which (validate) and fourth (transform) are mechanism-dependent —
everything else is shared with [Scanner Profiles](../scanners-profiles/design.md#2-architecture):

```
SDK Configuration                 (authentication.json, or an in-memory dict)
      ↓
Configuration Loader               load_json_config()               [reused, unchanged]
      ↓
Type resolution                    config["authentication"]["type"] → AuthenticationType
      ↓
Validator + Transformer            one `match` arm per mechanism      ← new in this feature
      ↓
HttpClient                         PUT /analysis_profiles/{id}/<mechanism-path>[?method=PATCH]
      ↓
Veracode API
```

A registry/callable-per-mechanism abstraction (e.g. a `Mechanism` base
class with seven subclasses) was considered and rejected: each mechanism's
validation and request-shape differ enough that such a class would carry
no shared behavior beyond an empty interface — exactly the
interface-with-one-real-implementation AGENTS.md §5 ("Simple") warns
against, the same conclusion
[scanners-profiles design §2](../scanners-profiles/design.md#2-architecture)
already reached for Loader/Validator/Transformer. Instead, a single
`match config_type:` statement (Python 3.11+, AGENTS.md §7) in one private
method is the smallest thing that solves the problem — the same role
`client.py`'s `_STATUS_EXCEPTIONS` dict plays for status-code dispatch,
just expressed as a `match` because each arm's *behavior* differs, not
just a returned class.

## 3. Components and Interfaces

### 3.1 `src/veracode_dast/models/common.py` (new, or reused if Analysis Profiles lands first)

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class InheritedValue(Generic[T]):
    """A value that may be inherited from a parent Analysis Profile.

    Attributes:
        effective_value: The value currently in effect.
        is_inherited: True if `effective_value` comes from a parent
            profile rather than being set directly on this one.
    """

    effective_value: T
    is_inherited: bool
```

Exactly [analysis-profile requirements §4.5](../analysis-profile/requirements.md#4-typed-models-and-enumerations)'s
model. If Analysis Profiles has already been implemented when this feature
lands, this file already exists and is imported unchanged; otherwise this
feature creates it (requirements.md §9.2).

### 3.2 `src/veracode_dast/models/authentication.py`

Enums (`StrEnum`, matching every existing enum in this codebase —
`models/target.py`, `models/scanner.py`):

```python
class AuthenticationType(StrEnum):
    BASIC = "basic"
    APPLICATION = "application"
    CERTIFICATE = "certificate"
    SCRIPT = "script"
    SRM = "srm"
    OAUTH2 = "oauth2"
    PARAMETER = "parameter"


class ScriptType(StrEnum):
    SELENIUM = "SELENIUM"
    JAVASCRIPT = "JAVASCRIPT"


class OAuth2GrantType(StrEnum):
    CLIENT_CREDENTIALS = "CLIENT_CREDENTIALS"
    PASSWORD = "PASSWORD"
    AUTHORIZATION_CODE = "AUTHORIZATION_CODE"
    AUTHORIZATION_CODE_PKCE = "AUTHORIZATION_CODE_PKCE"


class ParameterAuthenticationType(StrEnum):
    GET_PARAMETER = "GET_PARAMETER"
    HTTP_HEADER = "HTTP_HEADER"
    COOKIE = "COOKIE"
    LOCAL_STORAGE = "LOCAL_STORAGE"
    SESSION_STORAGE = "SESSION_STORAGE"
```

Response models — field names match the OpenAPI verbatim (requirements.md
§3.1); sensitive fields use `field(repr=False)` (stdlib `dataclasses`
feature — no new dependency) so the value is omitted from the default
`repr()`/`str()` and therefore from any `logger.info("%s", obj)`-style
call, satisfying requirements.md §3.6.2:

```python
@dataclass(frozen=True)
class Script:
    script_name: str | None = None
    script_type: ScriptType | None = None
    script_body: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any] | None) -> Script | None:
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
    username: str
    password: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> SystemAuthentication:
        return cls(username=data["username"], password=data.get("password"))


@dataclass(frozen=True)
class ApplicationAuthentication:
    username: str
    login_url: str
    password: str | None = field(default=None, repr=False)
    enable_ai_login: bool | None = None
    # ^ response-only; never accepted by ApplicationAuthenticationConfig (requirements.md §3.4.3)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ApplicationAuthentication: ...


@dataclass(frozen=True)
class CertificateAuthentication:
    cert_name: str | None = None
    base64_pkcs12: str | None = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CertificateAuthentication: ...


@dataclass(frozen=True)
class ScriptAuthentication:
    login_script: Script | None = None
    logout_script: Script | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ScriptAuthentication:
        return cls(
            login_script=Script.from_api(data.get("login_script")),
            logout_script=Script.from_api(data.get("logout_script")),
        )


@dataclass(frozen=True)
class SRMAuthentication:
    script_name: str | None = None
    script_type: ScriptType | None = None
    script_body: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> SRMAuthentication: ...


@dataclass(frozen=True)
class OAuth2Authentication:
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
    def from_api(cls, data: dict[str, Any]) -> OAuth2Authentication: ...


@dataclass(frozen=True)
class ParameterAuthentication:
    title: str
    type: ParameterAuthenticationType
    key: str
    id: str | None = None
    value: str | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ParameterAuthentication: ...
```

The aggregate returned by `get()`, and the `update()` return-type alias
(requirements.md §3.1, §4.9):

```python
@dataclass(frozen=True)
class AuthenticationConfiguration:
    system_authentication: InheritedValue[SystemAuthentication] | None = None
    application_authentication: InheritedValue[ApplicationAuthentication] | None = None
    certificate_authentication: InheritedValue[CertificateAuthentication] | None = None
    script_authentication: InheritedValue[ScriptAuthentication] | None = None
    srm_authentication: InheritedValue[SRMAuthentication] | None = None
    oauth2_authentication: InheritedValue[OAuth2Authentication] | None = None
    parameter_authentications: InheritedValue[list[ParameterAuthentication]] | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AuthenticationConfiguration:
        """Maps `EffectiveAuthentications`; each field is None when the
        API returns null for that mechanism (requirements.md §0.4)."""
        ...


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
actual response shape for whichever mechanism was configured
(requirements.md §3.1)."""
```

SDK Configuration models — one per mechanism, field names matching §0.3
verbatim, each producing exactly that mechanism's `*UpdateRequest` (or
bare array) shape via `to_api()`:

```python
@dataclass(frozen=True)
class BasicAuthenticationConfig:
    username: str
    password: str

    def to_api(self) -> dict[str, Any]:
        return {"username": self.username, "password": self.password}


@dataclass(frozen=True)
class ApplicationAuthenticationConfig:
    username: str
    password: str
    login_url: str

    def to_api(self) -> dict[str, Any]:
        return {"username": self.username, "password": self.password, "login_url": self.login_url}


@dataclass(frozen=True)
class CertificateAuthenticationConfig:
    base64_pkcs12: str
    cert_name: str | None = None
    password: str | None = None

    def to_api(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ScriptConfig:
    script_name: str | None = None
    script_type: ScriptType | None = None
    script_body: str | None = None

    def to_api(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ScriptAuthenticationConfig:
    login_script: ScriptConfig | None = None
    logout_script: ScriptConfig | None = None

    def to_api(self) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if self.login_script is not None:
            body["login_script"] = self.login_script.to_api()
        if self.logout_script is not None:
            body["logout_script"] = self.logout_script.to_api()
        return body


@dataclass(frozen=True)
class SRMAuthenticationConfig:
    script_body: str
    script_name: str | None = None
    script_type: ScriptType | None = None

    def to_api(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class OAuth2AuthenticationConfig:
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

    def to_api(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ParameterAuthenticationEntry:
    title: str
    type: ParameterAuthenticationType
    key: str
    id: str | None = None
    value: str | None = None

    def to_api(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ParameterAuthenticationConfig:
    parameters: list[ParameterAuthenticationEntry]

    def to_api(self) -> list[dict[str, Any]]:
        return [entry.to_api() for entry in self.parameters]
```

`ScriptConfig`/`ParameterAuthenticationEntry` are the SDK-Configuration-side
counterparts of `Script`/`ParameterAuthentication` — kept as separate
classes rather than reusing the response model directly, because the
response models carry API-assigned/response-only data (`ParameterAuthentication.id`
is present either way, but a response `Script`/`ParameterAuthentication`
has no `to_api()` and a config `ScriptConfig`/`ParameterAuthenticationEntry`
has no need for the response-only shape guarantees `from_api()` provides).
This mirrors the existing `TargetCreate`/`Target` split in
`models/target.py` — request-shaped and response-shaped models are never
collapsed into one class in this codebase.

### 3.3 `src/veracode_dast/exceptions.py` (extended)

```python
class AuthenticationValidationError(VeracodeSDKError):
    """Raised for SDK-level Authentication parameter/configuration
    validation failures (requirements.md §5).

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        self.rule = rule
        super().__init__(message)


class UnknownAuthenticationTypeError(VeracodeSDKError):
    """Raised when an SDK Configuration names an authentication type
    outside the seven known `AuthenticationType` members
    (requirements.md §5.5).

    Attributes:
        type_name: The unrecognized `type` value from the configuration.
        suggestion: The closest known `AuthenticationType` value, or None.
    """

    def __init__(self, type_name: str, *, suggestion: str | None) -> None:
        self.type_name = type_name
        self.suggestion = suggestion
        message = f"Unknown authentication type '{type_name}'."
        if suggestion:
            message += f"\n\nDid you mean '{suggestion}'?"
        super().__init__(message)
```

Both subclass `VeracodeSDKError` directly, matching every prior feature's
`<Resource>ValidationError`/`Unknown<Resource>Error` pair (e.g.
[scanners-profiles design §3.2](../scanners-profiles/design.md#32-srcveracode_dastexceptionspy-extended)).
`ConfigFileNotFoundError`/`ConfigFileInvalidError` are **not** redefined
here — reused unchanged from `utils/sdk_config.py` (§3.4).

### 3.4 `src/veracode_dast/utils/sdk_config.py` (reused, unchanged)

`load_json_config()` and `suggest_closest()`, exactly as specified in
[scanners-profiles design §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared).
This feature adds no new function to this module — both operations it
needs (load a path-or-dict, suggest a close match for an unrecognized
`type`) are already resource-agnostic. If this feature is implemented
before Scanner Profiles, it creates this file verbatim from that design;
otherwise it is an unmodified import (requirements.md §9.1).

### 3.5 `src/veracode_dast/services/authentications.py`

```python
from veracode_dast.services.targets import TARGET_CONFIGURATION_SERVICE_BASE_URL

_AUTHENTICATIONS_PATH = "/analysis_profiles/{analysis_profile_id}/authentications"

_MECHANISM_PATHS: Final[dict[AuthenticationType, str]] = {
    AuthenticationType.BASIC: "/analysis_profiles/{analysis_profile_id}/system_authentication",
    AuthenticationType.APPLICATION: "/analysis_profiles/{analysis_profile_id}/application_authentication",
    AuthenticationType.CERTIFICATE: "/analysis_profiles/{analysis_profile_id}/certificate_authentication",
    AuthenticationType.SCRIPT: "/analysis_profiles/{analysis_profile_id}/script_authentication",
    AuthenticationType.SRM: "/analysis_profiles/{analysis_profile_id}/srm_authentication",
    AuthenticationType.OAUTH2: "/analysis_profiles/{analysis_profile_id}/oauth2_authentication",
    AuthenticationType.PARAMETER: "/analysis_profiles/{analysis_profile_id}/parameter_authentications",
}
# Every mechanism except PARAMETER supports (and this feature always sends)
# ?method=PATCH — requirements.md §0.1's load-bearing asymmetry.
_SUPPORTS_PATCH: Final[frozenset[AuthenticationType]] = frozenset(_MECHANISM_PATHS) - {
    AuthenticationType.PARAMETER
}

logger = logging.getLogger(__name__)


class AuthenticationsService:
    """Manages Authentication configuration for existing Analysis Profiles."""

    def __init__(self, http_client: HttpClient) -> None:
        self._http_client = http_client

    def get(self, analysis_profile_id: str) -> AuthenticationConfiguration:
        self._require_non_blank(analysis_profile_id)
        response = self._http_client.get(
            _AUTHENTICATIONS_PATH.format(analysis_profile_id=analysis_profile_id)
        )
        config = AuthenticationConfiguration.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Retrieved authentication configuration for analysis profile %s", analysis_profile_id)
        return config

    def update(
        self,
        analysis_profile_id: str,
        config_file: str | Path | dict[str, Any],
    ) -> Authentication:
        self._require_non_blank(analysis_profile_id)

        config = load_json_config(config_file)
        auth_type, body = self._validate_and_transform(config)

        path = _MECHANISM_PATHS[auth_type].format(analysis_profile_id=analysis_profile_id)
        params = {"method": "PATCH"} if auth_type in _SUPPORTS_PATCH else None

        logger.info("Updating %s authentication for analysis profile %s", auth_type.value, analysis_profile_id)
        response = self._http_client.put(path, json=body, params=params)
        result = self._build_response(auth_type, response.data)
        logger.info("%s authentication updated for analysis profile %s", auth_type.value, analysis_profile_id)
        return result

    @staticmethod
    def _require_non_blank(analysis_profile_id: str) -> None:
        if not analysis_profile_id or not analysis_profile_id.strip():
            raise AuthenticationValidationError(
                "analysis_profile_id must not be blank", rule="analysis_profile_id_required"
            )
```

`_validate_and_transform` and `_build_response` are covered in §6/§7 —
each is one `match auth_type:` statement with one arm per
`AuthenticationType` member, so adding an eighth mechanism later touches
exactly these two methods plus `_MECHANISM_PATHS` (§11).

## 4. Service Responsibilities

| Responsibility | Owner |
|---|---|
| HTTP transport, HMAC auth, retries, status→exception mapping | `HttpClient` (unchanged) |
| Loading SDK Configuration (file or dict) | `utils/sdk_config.load_json_config` (reused, unchanged) |
| `type` resolution + "did you mean" suggestion | `AuthenticationsService._validate_and_transform` + `utils/sdk_config.suggest_closest` (reused) |
| Per-mechanism structural/required-field validation | `AuthenticationsService._validate_and_transform` |
| Per-mechanism SDK Configuration → API request transformation | `AuthenticationsService._validate_and_transform` (via each `*Config.to_api()`) |
| Endpoint/`method=PATCH` selection | `_MECHANISM_PATHS` / `_SUPPORTS_PATCH` (module-level data) |
| Building typed models from API responses | `AuthenticationConfiguration.from_api` / each mechanism's `from_api` |
| Business-event logging (never field values) | `AuthenticationsService` |

## 5. SDK Configuration Flow

1. Caller calls `client.authentications.update(analysis_profile_id, config_file)`.
2. `load_json_config()` returns a plain dict, whether `config_file` was a
   path or already a dict.
3. `_validate_and_transform()` resolves `config["authentication"]["type"]`
   to an `AuthenticationType`, validates that mechanism's required fields
   (§6), and builds the mechanism's `*Config` object, returning
   `(auth_type, body)` where `body` is already the API request shape
   (`.to_api()`'s output — §7).
4. `AuthenticationsService.update()` selects the endpoint path and whether
   to send `?method=PATCH` from `_MECHANISM_PATHS`/`_SUPPORTS_PATCH`.
5. `HttpClient.put()` sends the request; a non-2xx response raises the
   appropriate exception per §9 and `update()` never catches it.
6. On 200, the response is parsed into the matching typed model (§3.2)
   and returned.

This matches the five-step flow in
[README "Update Authentication"](README.md#update-authentication),
adjusted for the mechanism-dispatch this feature adds.

## 6. Validation Flow

Two passes, both entirely local (no HTTP), inside `_validate_and_transform`:

1. **Structural** — `config` is a dict with an `"authentication"` object
   containing a string `"type"` (requirements.md §5.2–§5.4).
2. **Type resolution** — `type` must be a known `AuthenticationType`
   member, else `UnknownAuthenticationTypeError` via `suggest_closest()`
   against the seven known values (requirements.md §5.5).
3. **Per-mechanism** — one `match` arm per member, each building that
   mechanism's `*Config` dataclass directly from `config["authentication"]`
   (missing/blank required fields raise `AuthenticationValidationError`
   with the `rule=` values enumerated in requirements.md §5.6–§5.12):

```python
def _validate_and_transform(
    self, config: dict[str, Any]
) -> tuple[AuthenticationType, dict[str, Any] | list[Any]]:
    auth = config.get("authentication")
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
        raise UnknownAuthenticationTypeError(type_value, suggestion=suggest_closest(type_value, known))
    auth_type = AuthenticationType(type_value)

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
    return auth_type, body
```

Each `_<mechanism>_config` static helper does exactly the presence/type/
enum-membership checks requirements.md §5.6–§5.12 specify — no length,
format, or pattern checks (requirements.md §5.13), and no cross-field
business rules (OAuth2 grant-type-specific requirements, SRM's
JavaScript-only note — requirements.md §5.10–§5.11). For example:

```python
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
```

`_parameter_config` additionally validates each list entry (requirements.md
§5.12), raising `AuthenticationValidationError(rule="parameter_entry_invalid")`
naming the offending index on failure, and accepts an empty list
unchanged (requirements.md §3.5.3).

## 7. Transformation Layer

Each mechanism's `to_api()` produces exactly that mechanism's
`*UpdateRequest` shape (or, for `parameter`, a bare array) — no separate
`Transformer` class, matching
[scanners-profiles design §7](../scanners-profiles/design.md#7-transformation-layer)'s
reasoning: a dedicated class would add a layer with exactly one call site.

```python
# type: "basic"  (README, unchanged)
{"authentication": {"type": "basic", "username": "admin", "password": "secret123"}}
# -> PUT .../system_authentication?method=PATCH
{"username": "admin", "password": "secret123"}

# type: "oauth2"  (README, field names corrected per requirements.md §3.1)
{"authentication": {"type": "oauth2", "grant_type": "CLIENT_CREDENTIALS",
                     "access_token_url": "https://example.com/oauth/token",
                     "client_id": "client-id", "client_secret": "client-secret"}}
# -> PUT .../oauth2_authentication?method=PATCH
{"grant_type": "CLIENT_CREDENTIALS", "access_token_url": "https://example.com/oauth/token",
 "client_id": "client-id", "client_secret": "client-secret"}

# type: "parameter"
{"authentication": {"type": "parameter", "parameters": [
    {"title": "API Key", "type": "HTTP_HEADER", "key": "X-API-Key", "value": "secret-token"}
]}}
# -> PUT .../parameter_authentications   (no ?method — full-array replace)
[{"title": "API Key", "type": "HTTP_HEADER", "key": "X-API-Key", "value": "secret-token"}]
```

Each `*Config.to_api()` omits a field entirely when its value is `None`
(mirroring `TargetCreate.to_api()`'s omit-when-unset convention in
`models/target.py`) rather than sending an explicit `null` — since every
mechanism except `parameter` is always called with `method=PATCH`
(requirements.md §3.4.1), an omitted field and an explicit `null` are
handled identically server-side ("null values and absent attributes are
ignored"), so there is no partial-update sentinel (`_UNSET`) needed here
the way `TargetUpdate`/`AnalysisProfileUpdate` need one — those support a
*caller-omits-vs-explicit-None* distinction that this feature's SDK
Configuration format has no use for (a caller who wants to leave a field
alone under PATCH semantics simply doesn't include the key at all).

## 8. Models

Covered in [§3.2](#32-srcveracode_dastmodelsauthenticationpy). No single
"SDK Configuration model" spans all seven mechanisms — each mechanism has
its own config/response model pair, since their fields are genuinely
different (requirements.md §4.6–§4.7). `InheritedValue[T]` (§3.1) is the
only model this feature shares with another Phase 2 feature.

## 9. Error Handling

| Failure | Exception | Raised by |
|---|---|---|
| Blank `analysis_profile_id` | `AuthenticationValidationError(rule="analysis_profile_id_required")` | `AuthenticationsService` |
| `config_file` path does not exist / not valid JSON | `ConfigFileNotFoundError` / `ConfigFileInvalidError` | `utils.sdk_config.load_json_config` (reused) |
| Missing/malformed `authentication`/`type` | `AuthenticationValidationError` | `AuthenticationsService._validate_and_transform` |
| Unknown `type` value | `UnknownAuthenticationTypeError` | `AuthenticationsService._validate_and_transform` |
| Missing/invalid required field for the resolved mechanism | `AuthenticationValidationError(rule="<mechanism>_<field>_required"/"_invalid")` | `AuthenticationsService._<mechanism>_config` |
| HTTP 401 | `VeracodeAuthenticationError` | `HttpClient` (unchanged) |
| HTTP 404 (unknown analysis profile or authentication ID) | `VeracodeNotFoundError` | `HttpClient` (unchanged) |
| HTTP 422 (any Veracode-side constraint) | `VeracodeValidationError` | `HttpClient` (unchanged) |
| HTTP 500 | `VeracodeApiError` | `HttpClient` (unchanged) |

Client-side checks always raise before any HTTP call (requirements.md §5);
every HTTP Client exception propagates unmodified — same shape as
[scanners-profiles design §9](../scanners-profiles/design.md#9-error-handling).

## 10. Testing Strategy

Location: `tests/models/test_authentication.py`,
`tests/services/test_authentications.py`. Same stub-`HttpClient` approach
as every prior feature — no mocking library, no real sockets.
`tests/utils/test_sdk_config.py` already exists once Scanner Profiles is
implemented and needs no changes for this feature.

Cases:

- `from_api` for every one of the seven response models, plus
  `AuthenticationConfiguration.from_api` with a fixture shaped like
  requirements.md §0.4 — some mechanisms present (`InheritedValue`
  populated), some `None`.
- `AuthenticationsService.get()`: blank `analysis_profile_id` →
  `AuthenticationValidationError`, no HTTP call; 200 →
  `AuthenticationConfiguration`; 404 → `VeracodeNotFoundError` propagates.
- `AuthenticationsService.update()`, one case per mechanism:
  - the exact README `"basic"`/`"oauth2"` (corrected field names) examples
    → request body matches §7 exactly, `method=PATCH` present, 200 →
    correctly-typed response model.
  - `"parameter"` → request has **no** `method` query parameter and a
    bare-array body; an empty `"parameters": []` is accepted.
  - each mechanism's missing-required-field cases → the exact
    `AuthenticationValidationError(rule=...)` from requirements.md
    §5.6–§5.12, no HTTP call.
  - `{"authentication": {"type": "aouth2", ...}}` → `UnknownAuthenticationTypeError`
    with `suggestion == "oauth2"` (README-equivalent "did you mean"
    reproduction, same as
    [scanners-profiles design §10](../scanners-profiles/design.md#10-testing-strategy)).
  - 404 → `VeracodeNotFoundError` propagates unchanged.
- `caplog` assertion, run against every mechanism: no captured log record
  contains any value from `password`, `client_secret`, `base64_pkcs12`,
  `value`, or `script_body` — the single most important test in this
  feature (requirements.md §3.6.3, §7.3).
- `repr()`/`str()` assertion, run against a populated instance of every
  response model carrying a sensitive field: the field's value never
  appears in the output (requirements.md §3.6.2).

## 11. Future Extensibility

README ("Supported Authentication Types"): "Support for additional
authentication mechanisms will follow future Veracode API enhancements."
Adding an eighth mechanism touches exactly:

1. One new `AuthenticationType` member.
2. One new response model + one new `*Config` model in
   `models/authentication.py`.
3. One new entry in `_MECHANISM_PATHS` (and `_SUPPORTS_PATCH`, if it
   doesn't support `method=PATCH`).
4. One new `match` arm in `_validate_and_transform` and one in
   `_build_response`.

No change to `get()`, to `AuthenticationConfiguration` beyond one new
field, to `utils/sdk_config.py`, or to any other feature's files — the
same extensibility guarantee
[scanners-profiles design §11](../scanners-profiles/design.md#11-future-extensibility)
already establishes for its own resource.

## 12. File Layout Introduced by This Feature

```
src/veracode_dast/
├── models/authentication.py    # 4 enums, 7 response models + Script,
│                                # 7 config models + ScriptConfig/ParameterAuthenticationEntry,
│                                # AuthenticationConfiguration, Authentication (alias)
├── models/common.py             # InheritedValue[T] (new, or reused — §3.1)
├── services/authentications.py # AuthenticationsService
├── client.py                    # (+) self.authentications, sharing client.targets' HttpClient
└── exceptions.py                # (+) AuthenticationValidationError, UnknownAuthenticationTypeError

tests/
├── models/test_authentication.py
└── services/test_authentications.py

examples/
└── authentications_example.py

specs/authentications/
└── authentication.json          # sample SDK Configuration fixture, mirrors the README
```

`utils/sdk_config.py` is listed here only if this feature is implemented
before Scanner Profiles (§3.4); otherwise it is pre-existing and
unmodified.

## 13. Traceability

| Component | Requirements covered |
|---|---|
| `AuthenticationsService.get` | 3.2 |
| `AuthenticationsService.update` | 3.3–3.5 |
| `AuthenticationType`, `ScriptType`, `OAuth2GrantType`, `ParameterAuthenticationType` | §4.1–§4.4 |
| `Script`, per-mechanism response models | §4.5–§4.6, §0.2 |
| Per-mechanism `*Config` models | §4.7, §0.3 |
| `InheritedValue[T]`, `AuthenticationConfiguration`, `Authentication` alias | §4.8–§4.9, §0.4, §3.1 |
| `AuthenticationsService._validate_and_transform` | §5 (all) |
| `AuthenticationValidationError`, `UnknownAuthenticationTypeError` | §6.1–§6.2 |
| `field(repr=False)` on sensitive fields, logging discipline | §3.6, §7 |
| `utils/sdk_config.py` reuse | §9.1 |
| `models/common.py` reuse | §9.2 |
| Public interface, `HttpClient` reuse | §8 |
| Testing strategy | §9 (design.md), §10 (design.md) |
| Future Extensibility | §10 (requirements.md, NFR "Extensible"), §11 (design.md) |
