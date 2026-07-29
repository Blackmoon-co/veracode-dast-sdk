# Requirements — Authentications

Source context: [README.md](README.md). Architecture and conventions:
[AGENTS.md](../../AGENTS.md). Phase 2 ("Configure Targets"), per
[AGENTS.md §10](../../AGENTS.md#10-roadmap). Depends on the
[HTTP Client](../http-client/requirements.md) and reuses
`TARGET_CONFIGURATION_SERVICE_BASE_URL` from
[Target Management](../target-management/requirements.md) (same Veracode
API domain as [API Specification Management](../api-specification-management/requirements.md)).
Conceptually sits below [Analysis Profiles](../analysis-profile/README.md),
the same way [Scanner Profiles](../scanners-profiles/requirements.md) does:
`analysis_profile_id` is always supplied by the caller; this feature never
resolves, creates, or validates an Analysis Profile itself. Follows the
same **SDK Configuration → Loader → Validator → Transformer → HttpClient**
pipeline [Scanner Profiles](../scanners-profiles/design.md#2-architecture)
established as the first configuration-driven Phase 2 feature, reusing its
shared `utils/sdk_config.py` rather than re-implementing configuration
loading.

---

## 0. OpenAPI Review

Source: `openApi/Veracode-veracode-dast-target-configuration-service-api-1.0.0-resolved.json`,
server `https://api.veracode.com/dae/api/tcs-api/api/v1` (no new base URL).

### 0.1 In-scope REST endpoints

| Method | Path | operationId | Purpose |
|---|---|---|---|
| GET | `/analysis_profiles/{analysis_profile_id}/authentications` | `getEffectiveAuthentications` | Retrieve the effective, per-mechanism authentication configuration. |
| PUT | `/analysis_profiles/{analysis_profile_id}/system_authentication` | `updateSystemAuthentication` | Update HTTP Basic (system) authentication. |
| PUT | `/analysis_profiles/{analysis_profile_id}/application_authentication` | `updateApplicationAuthentication` | Update form-based application authentication. |
| PUT | `/analysis_profiles/{analysis_profile_id}/certificate_authentication` | `updateCertificateAuthentication` | Update client certificate authentication. |
| PUT | `/analysis_profiles/{analysis_profile_id}/script_authentication` | `updateScriptAuthentication` | Update login/logout script authentication. |
| PUT | `/analysis_profiles/{analysis_profile_id}/srm_authentication` | `updateSRMAuthentication` | Update Scriptable Request Modification authentication. |
| PUT | `/analysis_profiles/{analysis_profile_id}/oauth2_authentication` | `updateOAuth2Authentication` | Update OAuth 2.0 authentication. |
| PUT | `/analysis_profiles/{analysis_profile_id}/parameter_authentications` | `updateParameterAuthentications` | Replace the full list of parameter authentications. |

Eight endpoints, all tagged `authentication` in the OpenAPI document. One
`GET` returns the complete effective picture across every mechanism at
once; there is no per-mechanism `GET`. Each mechanism has its own `PUT` —
there is no single, unified "update authentication" endpoint. Path
parameter `analysis_profile_id` is a `UUIDWithoutHyphens` (32 hex chars, no
dashes) on every endpoint; this feature does not reformat or validate its
shape beyond the generic blank-string check in §5 — malformed IDs are
rejected by the API (404) and propagate unchanged.

**Load-bearing asymmetry:** six of the seven `PUT` endpoints (every one
except `parameter_authentications`) accept an optional `method=PATCH` query
parameter — "If set to PATCH, updates the content to values in the
request, but null values and absent attributes are ignored." Without it,
`PUT` is a full replace of that mechanism's fields. `parameter_authentications`
defines **no** `method` parameter at all — it is unconditionally a
full-array replace: whatever list is submitted becomes the complete set of
parameter authentications, and any previously-configured entry not
included is deleted. See §3.5 and design.md §7 for how this shapes
`update()`.

Every `PUT` endpoint also documents a `204` response ("You have
successfully removed `<mechanism>` authentication from the analysis
profile") for the case where a full-replace `PUT` (no `method=PATCH`) is
sent with all fields absent/null — this feature never triggers that path;
see §3.5 and §12.3.

### 0.2 Schemas — response (per-mechanism, returned by `GET .../authentications` wrapped in an `Effective*` envelope, and by each `PUT` directly)

| Schema | Required | Properties |
|---|---|---|
| `SystemAuthentication` | `username` | `username`, `password` |
| `ApplicationAuthentication` | `login_url`, `username` | `username`, `password`, `login_url`, `enable_ai_login` |
| `CertificateAuthentication` | *(none)* | `password`, `base64_pkcs12`, `cert_name` |
| `ScriptAuthentication` | *(none)* | `login_script` (`Script`), `logout_script` (`Script`) |
| `SRMAuthentication` | *(none)* | `script_name`, `script_type` (`ScriptTypeEnum`), `script_body` |
| `OAuth2Authentication` | *(none)* | `access_token_url`, `client_id`, `client_secret`, `authorization_url`, `grant_type` (`OAuth2GrantType`), `username`, `password`, `redirect_url`, `scope`, `use_openid_connect` (default `false`), `openid_url` |
| `ParameterAuthentication` (list item) | `key`, `title`, `type` | `id` (`UUIDWithoutHyphens`), `title` (1–255 chars), `type` (`ParameterAuthenticationType`), `key` (1–255 chars), `value` (1–10000 chars) |

`Script` (embedded in `ScriptAuthentication`): `script_name`, `script_type`
(`ScriptTypeEnum`), `script_body` — no required fields.

`ScriptTypeEnum`: `SELENIUM`, `JAVASCRIPT`. Description notes "JavaScript
is the only supported format" specifically for SRM, while the shared enum
still lists `SELENIUM` for login/logout scripts — this feature does not
enforce that SRM-specific narrowing client-side (§5.9, same class of
decision as [scanners-profiles requirements §5.7](../scanners-profiles/requirements.md#5-validation-rules)).

`OAuth2GrantType`: `CLIENT_CREDENTIALS`, `PASSWORD`, `AUTHORIZATION_CODE`,
`AUTHORIZATION_CODE_PKCE`.

`ParameterAuthenticationType`: `GET_PARAMETER`, `HTTP_HEADER`, `COOKIE`,
`LOCAL_STORAGE`, `SESSION_STORAGE`.

### 0.3 Schemas — request (`PUT` body per mechanism)

| Schema | Notes |
|---|---|
| `SystemAuthenticationUpdateRequest` | `username`, `password` — both nullable. |
| `ApplicationAuthenticationUpdateRequest` | Own property `login_url` (nullable) `allOf` `SystemAuthenticationUpdateRequest` (adds `username`, `password`). **`enable_ai_login` is documented in this schema's `example` block but is absent from its actual `properties`/`allOf`** — an observed OpenAPI inconsistency, preserved as-is rather than silently invented away (same practice as [analysis-profile requirements §0.7](../analysis-profile/requirements.md#07-http-status-codes-and-error-responses)'s preserved `501` note). `enable_ai_login` is therefore response-only in this feature — see §3.1. |
| `CertificateAuthenticationUpdateRequest` | `cert_name`, `base64_pkcs12`, `password` — all nullable. |
| `ScriptAuthenticationUpdateRequest` | `login_script`, `logout_script` (both `Script`, nullable). |
| `SRMAuthenticationUpdateRequest` | `script_name`, `script_type`, `script_body` — all nullable; description on `script_body` notes "base64 encoded" (the response schema's `script_body` description does not repeat this note — this feature does not perform any base64 transcoding itself; §3.1 and §5.6). |
| `OAuth2AuthenticationUpdateRequest` | Same 11 fields as `OAuth2Authentication`, all nullable, none required. |
| `ParameterAuthenticationsUpdateRequest` | A bare JSON **array** of `ParameterAuthentication` — not an object. See §0.1's load-bearing asymmetry. |

### 0.4 Schemas — GET envelope

`EffectiveAuthentications` — one property per mechanism, each an
`Effective<Mechanism>Authentication` wrapper:

```json
{
  "system_authentication": { "is_inherited": false, "effective_value": { "...SystemAuthentication..." } },
  "application_authentication": null,
  "certificate_authentication": null,
  "script_authentication": null,
  "srm_authentication": null,
  "oauth2_authentication": null,
  "parameter_authentications": { "is_inherited": true, "effective_value": [ "...ParameterAuthentication..." ] }
}
```

Each `Effective*Authentication` wrapper is itself `nullable: true` (the
mechanism may be entirely unconfigured, on this profile or any parent) and,
when non-null, requires both `effective_value` and `is_inherited` — the
same `{effective_value, is_inherited}` shape already established by
[analysis-profile requirements §0.5](../analysis-profile/requirements.md#05-schemas)'s
`InheritedValue[T]`. **All seven mechanisms are independent and may be
configured simultaneously** — e.g. certificate authentication (TLS client
cert) and form-based application authentication (login flow) commonly
coexist on the same Analysis Profile. This is not a discriminated union
with one active member; see §3.1.

### 0.5 HTTP status codes and error responses

| Endpoint | Status | Meaning | Body schema |
|---|---|---|---|
| GET `.../authentications` | 200 | Success | `EffectiveAuthentications` |
| GET `.../authentications` | 401 | Unauthorized | none defined |
| GET `.../authentications` | 404 | Unknown analysis profile ID | `Problem` (`AnalysisProfile404Response`) |
| GET `.../authentications` | 500 | Server error | `Problem` |
| PUT `.../<mechanism>_authentication(s)` | 200 | Updated | mechanism's response schema (§0.2) |
| PUT `.../<mechanism>_authentication(s)` | 204 | Removed (full-replace, all fields absent/null) | none |
| PUT `.../<mechanism>_authentication(s)` | 401 | Unauthorized | none defined |
| PUT `.../<mechanism>_authentication(s)` | 404 | Unknown analysis profile **or** authentication identifier | `Problem` (`Authentication404Response`) |
| PUT `.../<mechanism>_authentication(s)` | 500 | Server error | `Problem` |

No `400`/`422` is documented for any of these eight endpoints. The
per-field constraints in §0.2/§0.3 (string length ranges, enum
membership) are Veracode's own server-side validation; if Veracode ever
returns one as a `422`, it propagates unchanged as `VeracodeValidationError`
via the HTTP Client's existing status mapping (same posture as
[scanners-profiles requirements §0.3](../scanners-profiles/requirements.md#0-openapi-review)).

---

## 1. Overview

Authentication lets Veracode DAST access protected areas of an application
during a scan. Per [README.md](README.md), users never construct any of
the seven Veracode API request models above by hand — they author one
small SDK Configuration document naming a single mechanism (`{"type":
"basic", ...}`, `{"type": "oauth2", ...}`, etc.) and the SDK loads it,
validates it, transforms it into the correct mechanism's Veracode API
request, calls the correct endpoint, and returns a strongly typed model.

This feature is the second configuration-driven Phase 2 module, after
[Scanner Profiles](../scanners-profiles/requirements.md). It reuses that
feature's `utils/sdk_config.py` (`load_json_config`, `suggest_closest`)
unchanged rather than re-implementing JSON loading or "did you mean"
suggestions (§9), and — unlike Scanner Profiles' single endpoint — adds
one new layer of its own: dispatching to one of seven different
endpoints/schemas based on a `type` discriminator in the SDK
Configuration.

## 2. Goals

- Retrieve the complete, effective authentication configuration for an
  Analysis Profile — every mechanism, its inheritance status, and its
  current values — as strongly typed models.
- Let users configure exactly one authentication mechanism per `update()`
  call using the SDK Configuration format, instead of any of the seven
  Veracode API request shapes.
- Validate SDK Configuration structurally, by `type`, and by mechanism
  before any HTTP call is made.
- Transform validated SDK Configuration into the correct Veracode API
  request automatically, dispatching to the correct one of eight
  endpoints.
- Reuse the shared `HttpClient`, exception hierarchy,
  `TARGET_CONFIGURATION_SERVICE_BASE_URL`, and `utils/sdk_config.py`
  already established by Target Management / API Specification Management
  / Scanner Profiles — no new HTTP/auth/config-loading code.
- Never expose a credential, secret, certificate, token, or script body in
  a log line or a model's default string representation (README
  "Returned Model").

## 3. Functional Requirements

### 3.1 README/OpenAPI reconciliation (read before §3.2–§3.6)

README's worked examples and "Returned Model" section describe a single,
flat `Authentication(type=..., username=...)` resource. The real API has
no such resource: it has seven **independent, simultaneously-configurable**
mechanisms (§0.4), each with its own request/response schema, and no
`type` field appears on any of them (a caller already knows which
mechanism they configured or are inspecting). Per this repository's
established practice of treating the OpenAPI contract as the authoritative
behavior — not the README's illustrative shape — this feature resolves
the gap as follows, while fully preserving README's *calling convention*
(a config-file-driven `update()`, a no-argument-shape `get()`):

- **`get()` returns `AuthenticationConfiguration`** (§4.8) — one optional,
  inheritance-aware field per mechanism, mirroring `EffectiveAuthentications`
  exactly (§0.4) — not a flat `Authentication(type=..., username=...)`.
  A caller inspects the mechanism(s) they care about, e.g.
  `config.system_authentication.effective_value.username` (or checks
  `config.system_authentication is None`).
- **`update()` returns the single typed model the server actually returns**
  for whichever mechanism was configured — one of `SystemAuthentication`,
  `ApplicationAuthentication`, `CertificateAuthentication`,
  `ScriptAuthentication`, `SRMAuthentication`, `OAuth2Authentication`, or
  `list[ParameterAuthentication]` (the `Authentication` union alias, §4.9)
  — never a synthesized flat object carrying an invented `type` field.
- **README's two worked SDK Configuration examples remain the literal,
  authoritative format for `"basic"` and `"oauth2"`, with one field-level
  correction each:** `"oauth2"`'s example uses `token_url` and a lowercase
  `"client_credentials"`; the real request schema names these fields
  `access_token_url` (§0.3) and the real enum member is `CLIENT_CREDENTIALS`
  (§0.2). This feature's SDK Configuration format uses the OpenAPI's real
  field names and enum spelling throughout, for every one of the seven
  mechanisms — the same choice already made for every other typed
  enum/field in this codebase (`TargetType.WEB_APP`, `CrawlerMode.SMART`,
  `ScannerType.sql_injection`, none of which invent a friendlier casing
  than the API uses). `"basic"`'s example (`username`, `password`) needed
  no correction — it already matches `SystemAuthenticationUpdateRequest`
  verbatim.
- **README's "Supported Authentication Types" list names six mechanisms
  and explicitly says "including"** (README §"Supported Authentication
  Types": "Examples include: ... Support for additional authentication
  mechanisms will follow future Veracode API enhancements."). The OpenAPI
  defines a seventh — Form-based Application Authentication
  (`application_authentication`) — which this non-exhaustive wording does
  not exclude. Per the same "OpenAPI is authoritative" practice, this
  feature implements all seven, mapped to SDK Configuration `type` values
  `basic`, `application`, `certificate`, `script`, `srm`, `oauth2`,
  `parameter` (§4.1).

### 3.2 Get Authentication Configuration

**User story:** As an SDK consumer, I want to see every authentication
mechanism currently in effect for an Analysis Profile — including which
values are inherited from a parent profile — so I can audit or reason
about scan authentication before changing it.

3.2.1. WHEN `client.authentications.get(analysis_profile_id)` is called
THEN THE SYSTEM SHALL call `GET /analysis_profiles/{analysis_profile_id}/authentications`.

3.2.2. IF `analysis_profile_id` is blank (empty or whitespace-only) THEN
THE SYSTEM SHALL raise `AuthenticationValidationError` (§6.1) and SHALL NOT
make an HTTP call.

3.2.3. WHEN `GET .../authentications` responds 200 THEN THE SYSTEM SHALL
return a typed `AuthenticationConfiguration` (§4.8) built from the
response body, with each of the seven fields either `None` (mechanism
unconfigured on this profile and every parent) or an `InheritedValue[X]`
carrying `effective_value` and `is_inherited`, per §0.4.

3.2.4. WHEN `GET .../authentications` responds 404 THEN THE SYSTEM SHALL
let `VeracodeNotFoundError` propagate unchanged.

### 3.3 Update Authentication Configuration — dispatch

**User story:** As an SDK consumer, I want to configure one authentication
mechanism using a single SDK Configuration document, without knowing which
of the seven Veracode endpoints or request shapes corresponds to it.

3.3.1. `update(analysis_profile_id, config_file)` SHALL accept
`config_file` as either a path to an SDK Configuration JSON file or an
already-loaded/in-memory `dict` — same acceptance as
[scanners-profiles requirements §3.2](../scanners-profiles/requirements.md#3-functional-requirements),
via the shared `load_json_config()` (§9).

3.3.2. `update()` SHALL perform, in order, before any HTTP call: load
configuration (3.3.1) → validate top-level structure (§5.1–§5.4) →
resolve `type` to one of the seven known mechanisms (§5.5) → validate
that mechanism's fields (§5.6–§5.12) → transform to that mechanism's
Veracode API request shape (design.md §7).

3.3.3. THE SYSTEM SHALL dispatch to exactly one of the eight endpoints in
§0.1 based on `config["authentication"]["type"]` — never call more than
one `PUT` endpoint per `update()` call.

3.3.4. On success, `update()` SHALL return the typed model matching the
dispatched mechanism's actual response schema (§3.1), built from the
**server's** response body — never a locally reconstructed value.

3.3.5. Both `get()` and `update()` SHALL reject a blank/whitespace-only
`analysis_profile_id` before any HTTP call, raising
`AuthenticationValidationError` (§6.1).

### 3.4 Update — the six field-based mechanisms (`basic`, `application`, `certificate`, `script`, `srm`, `oauth2`)

3.4.1. For these six `type` values, THE SYSTEM SHALL call the
corresponding `PUT` endpoint (§0.1) with query parameter `method=PATCH`
— always, unconditionally. THE SYSTEM SHALL NOT expose a way to call any
of these six endpoints as a plain (full-replace) `PUT` — the same
safety-critical decision
[analysis-profile requirements §3.4.2](../analysis-profile/requirements.md#34-update-analysis-profile)
already made for `AnalysisProfilesService.update()`, for the identical
reason: a full-replace risks silently nulling every field the caller
didn't mention, and (per §0.1) can trigger the `204` "removed" outcome,
which this feature never exposes as an intended result (§12.3).

3.4.2. THE SYSTEM SHALL build each mechanism's request body from exactly
the fields defined on its `*UpdateRequest` schema (§0.3), using the
caller-supplied SDK Configuration fields for that mechanism (§4.2–§4.7)
— field names matching the OpenAPI verbatim (§3.1).

3.4.3. For `type: "application"`, THE SYSTEM SHALL NOT accept or forward
an `enable_ai_login` field — per §0.3, it is not part of
`ApplicationAuthenticationUpdateRequest`. It remains readable on `get()`'s
`ApplicationAuthentication.enable_ai_login` (response-only).

### 3.5 Update — `parameter` (full-array replace)

3.5.1. For `type: "parameter"`, THE SYSTEM SHALL call `PUT
/analysis_profiles/{analysis_profile_id}/parameter_authentications` with
**no** `method` query parameter (§0.1 — this endpoint defines none) and a
JSON array body built from the SDK Configuration's `parameters` list
(§4.7).

3.5.2. THE SYSTEM SHALL document, and SHALL NOT silently obscure, that
this call **replaces the entire list** of parameter authentications: any
previously-configured entry not present in the submitted `parameters`
list is deleted by Veracode. This is the opposite merge behavior from
§3.4's six PATCH-based mechanisms, and is the one place in this feature
where omission has a destructive effect.

3.5.3. An empty `"parameters": []` SHALL be accepted and SHALL result in
removing every parameter authentication currently configured on the
profile — this is a deliberate, valid outcome (§3.5.2), not an error.

### 3.6 Sensitive data handling

**User story:** As an SDK consumer, I want credentials, secrets, and
tokens I configure to never leak into a log file or an accidental
`print()`/`repr()` of a model.

3.6.1. THE SYSTEM SHALL NOT include the following fields' values in any
log record emitted by this feature: `password` (all four mechanisms that
have one), `client_secret` (OAuth 2.0), `base64_pkcs12` (Certificate),
`value` (Parameter Authentication), `script_body` (Script and SRM).

3.6.2. THE SYSTEM SHALL suppress the same fields listed in 3.6.1 from
every typed model's default string representation (`repr`/`str`), per
[README "Returned Model"](README.md#returned-model) ("Sensitive
information ... should never be exposed by the SDK models or logs.").
See design.md §3.1 for the mechanism (`field(repr=False)`).

3.6.3. THE SYSTEM SHALL log, at most, the `analysis_profile_id` and the
authentication `type` on a successful `update()` — never any field value
from the SDK Configuration or the API response.

## 4. Typed models and enumerations

**User story:** As an SDK consumer, I want every authentication mechanism
and its fields as real Python types, so invalid `type`/enum values are
caught by my editor and by `mypy` instead of at runtime inside Veracode's
API.

4.1. THE SYSTEM SHALL define `AuthenticationType(StrEnum)` with members
`BASIC = "basic"`, `APPLICATION = "application"`,
`CERTIFICATE = "certificate"`, `SCRIPT = "script"`, `SRM = "srm"`,
`OAUTH2 = "oauth2"`, `PARAMETER = "parameter"` — the seven SDK
Configuration discriminator values (§3.1), used only by this SDK (not sent
to the API; §0.1 shows there is no `type` field on the wire).

4.2. THE SYSTEM SHALL define `ScriptType(StrEnum)` with members
`SELENIUM`, `JAVASCRIPT` (the OpenAPI's `ScriptTypeEnum`, renamed for the
same resource-prefixing-avoidance reason
[analysis-profile requirements §4.2](../analysis-profile/requirements.md#4-typed-models-and-enumerations)
renamed `ModeEnum`→`AnalysisProfileMode`: dropping the redundant `Enum`
suffix already established by `CrawlerMode`/`DirectoryRestrictions`).

4.3. THE SYSTEM SHALL define `OAuth2GrantType(StrEnum)` with members
`CLIENT_CREDENTIALS`, `PASSWORD`, `AUTHORIZATION_CODE`,
`AUTHORIZATION_CODE_PKCE` (the OpenAPI's `OAuth2GrantType`, unchanged
name — already resource-prefixed).

4.4. THE SYSTEM SHALL define `ParameterAuthenticationType(StrEnum)` with
members `GET_PARAMETER`, `HTTP_HEADER`, `COOKIE`, `LOCAL_STORAGE`,
`SESSION_STORAGE` (the OpenAPI's `ParameterAuthenticationType`, unchanged
name).

4.5. THE SYSTEM SHALL define a `Script` model (`script_name: str | None`,
`script_type: ScriptType | None`, `script_body: str | None`, with
`script_body` excluded from `repr`, §3.6.2), reused by both
`ScriptAuthentication.login_script`/`logout_script`.

4.6. THE SYSTEM SHALL define one response model per mechanism —
`SystemAuthentication`, `ApplicationAuthentication`,
`CertificateAuthentication`, `ScriptAuthentication`, `SRMAuthentication`,
`OAuth2Authentication` — and `ParameterAuthentication` (list item), each
with a `from_api` classmethod, fields matching §0.2 verbatim (no renaming;
§3.1), and the sensitive fields listed in §3.6.1 excluded from `repr`.

4.7. THE SYSTEM SHALL define one SDK Configuration model per mechanism —
`BasicAuthenticationConfig`, `ApplicationAuthenticationConfig`,
`CertificateAuthenticationConfig`, `ScriptAuthenticationConfig`,
`SRMAuthenticationConfig`, `OAuth2AuthenticationConfig`,
`ParameterAuthenticationConfig` (holding a `parameters:
list[ParameterAuthenticationEntry]`) — fields matching §0.3 verbatim,
each with a `to_api()` producing that mechanism's `*UpdateRequest` (or, for
`parameter`, the bare array) shape.

4.8. THE SYSTEM SHALL define a reusable `InheritedValue[T]` generic model
(`models/common.py`) with fields `effective_value: T` and
`is_inherited: bool` — reusing
[analysis-profile requirements §4.5](../analysis-profile/requirements.md#4-typed-models-and-enumerations)'s
model unchanged rather than redefining an equivalent wrapper (see §9).

4.9. THE SYSTEM SHALL define `AuthenticationConfiguration` (a frozen
dataclass with seven fields — `system_authentication`,
`application_authentication`, `certificate_authentication`,
`script_authentication`, `srm_authentication`, `oauth2_authentication`,
`parameter_authentications` — each `InheritedValue[X] | None`, matching
§0.4 field-for-field) with a `from_api` classmethod, and a module-level
type alias `Authentication = SystemAuthentication | ApplicationAuthentication
| CertificateAuthentication | ScriptAuthentication | SRMAuthentication |
OAuth2Authentication | list[ParameterAuthentication]` for `update()`'s
return type (§3.1).

4.10. Every model and enum defined by this feature SHALL comply with the
model rules in [AGENTS.md §3](../../AGENTS.md#3-architecture) (models
never perform HTTP requests, contain business logic, or depend on the
HTTP Client).

## 5. Validation Rules

All of the following are checked **before** any HTTP call, and each
raises before any network I/O occurs:

5.1. `analysis_profile_id` must be non-blank (after `.strip()`) →
`AuthenticationValidationError(rule="analysis_profile_id_required")`.

5.2. The loaded configuration must be a JSON object containing an
`"authentication"` key whose value is itself a JSON object →
`AuthenticationValidationError(rule="authentication_key_required")`.

5.3. `config["authentication"]` must contain a `"type"` key →
`AuthenticationValidationError(rule="type_required")`.

5.4. `config["authentication"]["type"]` must be a string.

5.5. `config["authentication"]["type"]` must be a known
`AuthenticationType` member (§4.1) → `UnknownAuthenticationTypeError`,
carrying the offending value and, when a close match exists, a suggestion
— same "did you mean" mechanism as
[scanners-profiles requirements §5.5](../scanners-profiles/requirements.md#5-validation-rules),
reusing `suggest_closest()` (§9).

5.6. `type: "basic"`: `username` and `password` are both required,
non-blank strings → `AuthenticationValidationError(rule="basic_username_required")`
/ `rule="basic_password_required"`.

5.7. `type: "application"`: `username`, `password`, and `login_url` are
all required, non-blank strings → `AuthenticationValidationError(rule="application_<field>_required")`,
matching `ApplicationAuthentication`'s own `required: [login_url,
username]` (§0.2) plus `password` (present on every other read/write path
for this mechanism, and meaningless to omit for a login flow).

5.8. `type: "certificate"`: `base64_pkcs12` is required, a non-blank
string → `AuthenticationValidationError(rule="certificate_base64_pkcs12_required")`.
`cert_name` and `password`, if present, must be strings. Length/format
constraints already present in the OpenAPI (§0.3) are not duplicated
client-side (§5.13).

5.9. `type: "script"`: at least one of `login_script`/`logout_script`
must be present → `AuthenticationValidationError(rule="script_requires_login_or_logout")`
(an entirely empty script configuration is a no-op the API cannot act on).
Each present script, if it has a `script_type`, must be a valid
`ScriptType` member. THE SYSTEM SHALL NOT enforce the SRM-only
"JavaScript is the only supported format" note (§0.2) here — it does not
apply to login/logout scripts.

5.10. `type: "srm"`: `script_body` is required, a non-blank string →
`AuthenticationValidationError(rule="srm_script_body_required")`.
`script_type`, if present, must be a valid `ScriptType` member. THE SYSTEM
SHALL NOT enforce "JavaScript only" (§0.2) as a client-side restriction to
`JAVASCRIPT` — that is Veracode's own documented-but-not-schema-enforced
business rule, left to the server (same class of decision as
[scanners-profiles requirements §5.7](../scanners-profiles/requirements.md#5-validation-rules)).

5.11. `type: "oauth2"`: `grant_type` is required and must be a valid
`OAuth2GrantType` member → `AuthenticationValidationError(rule="oauth2_grant_type_required")`
/ `UnknownAuthenticationTypeError`-style handling is not reused here (this
is a nested enum, not the top-level `type` discriminator) — an invalid
`grant_type` raises `AuthenticationValidationError(rule="oauth2_grant_type_invalid")`.
THE SYSTEM SHALL NOT enforce which of the remaining ten fields are
required for a given `grant_type` (e.g. `client_secret` for
`CLIENT_CREDENTIALS`, `username`/`password` for `PASSWORD`) — the OpenAPI
does not encode this as a schema constraint, and replicating it
client-side would require this SDK to track a Veracode business rule that
can change independently of this package (same reasoning as §5.10).

5.12. `type: "parameter"`: `parameters` is required and must be a JSON
array (possibly empty, §3.5.3) → `AuthenticationValidationError(rule="parameter_parameters_required")`.
Each entry must be an object with non-blank string `title`, `key`, and a
`type` that is a valid `ParameterAuthenticationType` member →
`AuthenticationValidationError(rule="parameter_entry_invalid")`, naming
the offending index. `value`, if present, must be a string. `id`, if
present, is passed through unchanged (§4.7) — not validated as a
`UUIDWithoutHyphens` client-side (malformed IDs are Veracode's to reject).

5.13. THE SYSTEM SHALL NOT duplicate any length/format/pattern constraint
already present in the OpenAPI (§0.2/§0.3) as client-side validation
beyond the presence/type/enum-membership checks in §5.6–§5.12 — the same
distinction
[analysis-profile requirements §3.4.6](../analysis-profile/requirements.md#34-update-analysis-profile)
draws between validation worth mirroring client-side and validation that
would just duplicate the server. Values outside these bounds surface as
`VeracodeValidationError` (422) from the HTTP Client, unmodified.

## 6. Error handling

**User story:** As an SDK consumer, I want a clear distinction between "my
configuration was obviously invalid before any request was sent" and
"Veracode rejected my request," so I can handle each case appropriately.

6.1. THE SYSTEM SHALL define `AuthenticationValidationError(VeracodeSDKError)`
for every rule in §5.1–§5.12 except §5.5, following the naming/subclassing
convention established by every prior feature's `<Resource>ValidationError`
(e.g.
[scanners-profiles design §3.2](../scanners-profiles/design.md#32-srcveracode_dastexceptionspy-extended)).

6.2. THE SYSTEM SHALL define `UnknownAuthenticationTypeError(VeracodeSDKError)`
for §5.5, carrying the offending `type` value and an optional suggestion —
same shape and rationale as `UnknownScannerError`
([scanners-profiles design §3.2](../scanners-profiles/design.md#32-srcveracode_dastexceptionspy-extended)):
structured data a caller may want to handle programmatically, not just a
formatted message.

6.3. THE SYSTEM SHALL reuse `ConfigFileNotFoundError`/`ConfigFileInvalidError`
from `utils/sdk_config.py` (§9) — not redefine them.

6.4. THE SYSTEM SHALL NOT define any other new exception type. Every
failure that occurs after an HTTP request is sent (401, 404, 422, other
4xx, 5xx, connection errors, timeouts) SHALL surface as whichever
exception the HTTP Client already defines for that condition, unmodified.
In particular, THE SYSTEM SHALL NOT define an Authentication-specific "not
found" exception — both `AnalysisProfile404Response` and
`Authentication404Response` (§0.5) already map to `VeracodeNotFoundError`
via the HTTP Client's existing status-code mapping.

6.5. THE SYSTEM SHALL NOT catch and swallow any exception raised by the
HTTP Client; `AuthenticationsService` only ever lets it propagate.

## 7. Logging

**User story:** As an SDK maintainer, I want Authentications to log
meaningful business events without ever writing a credential, secret, or
script body to a log file.

7.1. WHEN an authentication mechanism is successfully updated THEN THE
SYSTEM SHALL emit an INFO-level log naming the operation, the
`analysis_profile_id`, and the `type` — nothing else (§3.6.3).

7.2. WHEN an Authentication Configuration is successfully retrieved THEN
THE SYSTEM SHALL emit an INFO-level log naming the `analysis_profile_id`
and, optionally, which mechanisms are currently configured (by name only,
never their values).

7.3. THE SYSTEM SHALL NOT log any field listed in §3.6.1
(`password`, `client_secret`, `base64_pkcs12`, `value`, `script_body`),
under any log level, anywhere in this feature.

7.4. THE SYSTEM SHALL NOT re-implement HTTP request/response logging;
that responsibility belongs entirely to the HTTP Client.

## 8. Public interface and reuse

**User story:** As an SDK consumer, I want `client.authentications` to be
the resource-oriented entry point AGENTS.md promises, reusing the same
HTTP Client instance already constructed for the rest of the DAST Target
Configuration Service domain.

8.1. THE SYSTEM SHALL expose an `AuthenticationsService` class whose
public methods are exactly `get` and `update`, matching README's Features
list ("Retrieve Authentication configuration", "Update Authentication
configuration"). THE SYSTEM SHALL NOT add a `delete`/`remove` method — the
API's only removal path is the full-replace `204` outcome (§0.1), which
this feature intentionally never exposes (§3.4.1, §12.3).

8.2. THE SYSTEM SHALL wire `AuthenticationsService` onto `VeracodeClient`
as `client.authentications`, reusing the same `HttpClient` instance
already constructed for `TargetsService`/`ApiSpecificationsService` (both
configured with `TARGET_CONFIGURATION_SERVICE_BASE_URL`) rather than
constructing a new one.

8.3. Every public class and method introduced by this feature SHALL
comply with the code conventions in
[AGENTS.md §7](../../AGENTS.md#7-code-conventions) (complete type hints,
Google-style docstrings).

8.4. `AuthenticationsService` SHALL comply with the Stateless principle in
[AGENTS.md §5](../../AGENTS.md#5-design-principles): it holds only its
`HttpClient` instance; no authentication data is cached or retained
between calls.

## 9. Reuse of prior Phase 2 building blocks

9.1. THE SYSTEM SHALL reuse `utils/sdk_config.load_json_config()` and
`utils/sdk_config.suggest_closest()`, introduced by
[Scanner Profiles](../scanners-profiles/design.md#3-components-and-interfaces),
unchanged. If this feature is implemented before Scanner Profiles, it
creates `utils/sdk_config.py` exactly per
[scanners-profiles design §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared);
whichever feature lands first implements it once.

9.2. THE SYSTEM SHALL reuse `models/common.InheritedValue[T]`, introduced
by [Analysis Profiles](../analysis-profile/requirements.md#4-typed-models-and-enumerations)
(§4.8), under the same first-implemented-wins rule as §9.1.

9.3. THE SYSTEM SHALL NOT modify `services/targets.py`,
`services/api_specifications.py`, `services/teams.py`, or
`services/scanners.py` (if present) — every reuse in this feature is an
import, never an edit.

## 10. Non-Functional Requirements

- **Reuse over duplication.** No new Veracode API base URL, no new
  `HttpClient` instance, no re-implementation of `load_json_config`/
  `suggest_closest`/`InheritedValue[T]` (§9).
- **Stateless.** `AuthenticationsService` holds only an injected
  `HttpClient`; every call is independent (§8.4).
- **Platform-agnostic.** No dependency on Azure DevOps, a CLI, or any
  other specific consumer (per
  [AGENTS.md §5](../../AGENTS.md#5-design-principles)).
- **Typed.** Every public method has complete type hints; every response
  is returned as a frozen dataclass, never a raw `dict`.
- **No secret ever logged or defaulted into a `repr()`** (§3.6, §7.3) —
  the single hardest requirement in this feature, given how many of the
  seven mechanisms carry a credential-shaped field.
- **Testable offline.** Every test in this feature runs without network
  access or real credentials (§9).
- **Extensible.** A future eighth mechanism (README: "Support for
  additional authentication mechanisms will follow future Veracode API
  enhancements") is added by extending `AuthenticationType`, adding one
  config/response model pair, and one dispatch-table entry — not by
  restructuring `AuthenticationsService.update()` (see design.md §11).

## 11. Acceptance Criteria

1. **Given** a valid `analysis_profile_id`, **when** `get(...)` is called,
   **then** exactly one `GET .../authentications` request is made and the
   result is an `AuthenticationConfiguration` whose seven fields are each
   `None` or an `InheritedValue` with `effective_value`/`is_inherited`
   populated from the response (§3.2.3).
2. **Given** a blank `analysis_profile_id`, **when** `get(...)` or
   `update(...)` is called, **then** `AuthenticationValidationError` is
   raised and no HTTP request is made (§3.2.2, §3.3.5).
3. **Given** the exact README `"basic"` SDK Configuration example, **when**
   `update(analysis_profile_id, config_file="authentication.json")` is
   called, **then** the request is `PUT .../system_authentication?method=PATCH`
   with body `{"username": "admin", "password": "secret123"}`, and the
   result is a `SystemAuthentication` built from the response (§3.4).
4. **Given** the README `"oauth2"` example with `token_url`/lowercase
   `grant_type` corrected per §3.1 (`access_token_url`,
   `"CLIENT_CREDENTIALS"`), **when** `update(...)` is called, **then** the
   request is `PUT .../oauth2_authentication?method=PATCH` with a body
   using the corrected field names, and the result is an
   `OAuth2Authentication` (§3.4, §5.11).
5. **Given** `{"authentication": {"type": "parameter", "parameters":
   [{"title": "API Key", "type": "HTTP_HEADER", "key": "X-API-Key",
   "value": "secret-token"}]}}`, **when** `update(...)` is called, **then**
   the request is `PUT .../parameter_authentications` — **no** `method`
   query parameter — with a bare JSON array body (§3.5).
6. **Given** `{"authentication": {"type": "parameter", "parameters": []}}`,
   **when** `update(...)` is called, **then** the request body is `[]`
   and no error is raised (§3.5.3).
7. **Given** `{"authentication": {"type": "aouth2", ...}}` (typo), **when**
   `update(...)` is called, **then** `UnknownAuthenticationTypeError` is
   raised with a message containing `Unknown authentication type 'aouth2'.`
   and `Did you mean 'oauth2'?`, and no HTTP call is made (§5.5).
8. **Given** a 404 response, **when** `get(...)` or `update(...)` is
   called, **then** `VeracodeNotFoundError` propagates unchanged (§3.2.4,
   §6.4).
9. **Given** any successful `update(...)` call whose SDK Configuration
   includes a `password`/`client_secret`/`base64_pkcs12`/`value`/
   `script_body` field, **when** the resulting log output and the
   returned model's `repr()` are inspected, **then** neither contains that
   field's value (§3.6, §7.3).
10. **Given** `VeracodeClient()`, **when** it is constructed, **then**
    `client.authentications` is an `AuthenticationsService` sharing the
    same `HttpClient` instance as `client.targets` (§8.2).

## 12. Out of Scope

12.1. THE SYSTEM SHALL NOT implement a `delete`/`remove` operation for any
authentication mechanism, nor any way to trigger the `204` full-replace
"removed" outcome documented in §0.1/§0.5 — README documents only Get and
Update (§8.1).

12.2. THE SYSTEM SHALL NOT implement Scanner Variables — README's
"Relationship with Scanner Variables" section describes them as a
complementary, independent Phase 2 feature (runtime values such as TOTP
codes that a Login Script or SRM script may reference); this feature adds
no dependency on it and no code that reads or writes `ScannerVariable`.

12.3. THE SYSTEM SHALL NOT implement ISM Gateway configuration
(README "Future Vision") or any integration between Authentication and
Analysis Profiles/Scanner Profiles beyond both taking an
`analysis_profile_id` supplied by the caller.

12.4. THE SYSTEM SHALL NOT implement a combined, multi-resource
`dast-config.json` — this feature only ever reads a single Authentication
SDK Configuration document naming exactly one mechanism per `update()`
call.

12.5. THE SYSTEM SHALL NOT replicate any Veracode server-side business
rule not encoded as an OpenAPI schema constraint — grant-type-specific
OAuth2 field requirements (§5.11), the SRM-only JavaScript restriction
(§5.10), or any length/format/pattern constraint already in the OpenAPI
(§5.13).

12.6. THE SYSTEM SHALL NOT implement retry, caching, or pagination logic
beyond what the HTTP Client already provides — `GET .../authentications`
is not paginated.

12.7. THE SYSTEM SHALL NOT modify `services/targets.py`,
`services/api_specifications.py`, `services/teams.py`, or
`services/scanners.py` — every reuse in this feature is an import, never
an edit (§9.3).
