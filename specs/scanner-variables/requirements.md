# Requirements — Scanner Variables

Source context: [README.md](README.md). Architecture and conventions:
[AGENTS.md](../../AGENTS.md). Phase 2 ("Configure Targets"), per
[AGENTS.md §10](../../AGENTS.md#10-roadmap). Reuses
[specs/target-management](../target-management/requirements.md) (the
`HttpClient` instance and `TARGET_CONFIGURATION_SERVICE_BASE_URL`
constant) and the configuration-driven pipeline first built by
[specs/scanners-profiles](../scanners-profiles/requirements.md)
(`utils/sdk_config.load_json_config`, `ConfigFileNotFoundError`,
`ConfigFileInvalidError`) — this feature adds no new API base URL, no new
Veracode API domain, and no second config-loading implementation.
Conceptually a sibling of [Scanner Profiles](../scanners-profiles/README.md)
and [Analysis Profiles](../analysis-profile/README.md): `analysis_profile_id`
is always supplied by the caller; this module never resolves, creates, or
validates an Analysis Profile itself.

REST contract: `openApi/Veracode-veracode-dast-target-configuration-service-api-1.0.0-resolved.json`
("Veracode DAST Target Configuration Service API", v1.0.0, server
`https://api.veracode.com/dae/api/tcs-api/api/v1`).

Format: OpenAPI review, then Functional Requirements as EARS-style ("THE
SYSTEM SHALL...") acceptance criteria grouped by capability, followed by
Non-Functional Requirements, a scenario-based Acceptance Criteria checklist,
and an explicit Out of Scope section.

---

## 0. OpenAPI Contract Reference

This section documents the portion of the OpenAPI contract relevant to
Scanner Variables. It is the factual basis Functional Requirements §3–§8
are derived from — nothing below introduces a REST behavior not captured
here.

### 0.1 In-scope REST endpoints

| Method | Path | operationId | Purpose |
|---|---|---|---|
| GET | `/analysis_profiles/{analysis_profile_id}/scanner_variables` | `getEffectiveScannerVariables` | Retrieve the effective Scanner Variables for an Analysis Profile. |
| PUT | `/analysis_profiles/{analysis_profile_id}/scanner_variables` | `updateScannerVariables` | Replace the Scanner Variables for an Analysis Profile. |

Path parameter `analysis_profile_id` is a `UUIDWithoutHyphens` (32 hex
chars, no dashes) on both endpoints — this feature does not reformat or
validate its shape beyond the generic blank-string check in §5; malformed
IDs are rejected by the API (404) and propagate unchanged.

### 0.2 Schemas — response shape (`GET` and `PUT` 200)

**`ScannerVariable`** (required: `reference_key`, `value`):

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | string (`UUIDWithoutHyphens`) | — | Assigned by the API; optional. |
| `reference_key` | string | 1–255 chars | The name authentication mechanisms use to look up this value. |
| `value` | string | 1–255 chars | The variable's value. |
| `evaluation_mode` | `ScannerVariableEvaluationMode` enum | `RAW` \| `TOTP`, default `RAW` | See §0.4. |
| `utilize_in_ai_assisted_login` | boolean | default `false` | See §3.1.4 — out of scope for this feature. |

**`InheritableValue`** (required: `is_inherited`) — the same generic
"is this value inherited from a parent Analysis Profile" wrapper shape
already documented by
[specs/analysis-profile requirements §0.5](../analysis-profile/requirements.md#05-schemas)
(`{effective_value, is_inherited}`), reused here via `allOf`.

**`EffectiveScannerVariable`** (required: `effective_value`, `is_inherited`,
via `allOf: [InheritableValue]` plus its own `effective_value` property) —
one entry of a `GET`/`PUT` 200 response array: `{"effective_value":
<ScannerVariable>, "is_inherited": <boolean>}`. The schema additionally
marks the whole object `"nullable": true`; no consumer need or documented
scenario for a `null` array entry has been identified, so this feature
does not add special handling for it (§0.5.1's "no code path this feature
does not otherwise cover" default: if the API ever sends one,
`ScannerVariable.from_api` raises a `TypeError`/`KeyError`, which is
acceptable — inventing defensive handling for an unobserved case would be
speculative).

**`EffectiveScannerVariables`** — `array` of `EffectiveScannerVariable`.
This is the entire 200-response body for **both** `GET` and `PUT` — there
is no wrapping object, no `analysis_profile_id` echoed back, and no
pagination.

### 0.3 Schema — request shape (`PUT` body)

**`ScannerVariablesUpdateRequest`** — a **flat JSON array** of
`ScannerVariable` objects (not wrapped in `{"variables": [...]}`, and not
paired with `is_inherited` — that wrapper only appears in responses). This
is the complete, authoritative shape of what `PUT` accepts: every
`ScannerVariable` the caller wants to exist after the call, and nothing
else — see §3.3 and design.md §8 for why this matters.

### 0.4 Enumerations

| OpenAPI schema | Values | Used by |
|---|---|---|
| `ScannerVariableEvaluationMode` | `RAW` (default), `TOTP` | `ScannerVariable.evaluation_mode` — "`TOTP` for Time-Based One-Time Password and `RAW` for as-is evaluation" (OpenAPI description, verbatim). |

Per README's "SDK Configuration" and "Returned Model" sections, this SDK
exposes this enum to callers as a simplified `totp_seed: bool` field —
`True` ⇄ `"TOTP"`, `False`/absent ⇄ `"RAW"` — never the raw enum. See
§3.1.1.

### 0.5 HTTP status codes and error responses

| Endpoint | Status | Meaning | Body schema |
|---|---|---|---|
| GET `.../scanner_variables` | 200 | Success | `EffectiveScannerVariables` |
| GET `.../scanner_variables` | 401 | Unauthorized | none defined |
| GET `.../scanner_variables` | 404 | Unknown `analysis_profile_id` | `Problem` (via `AnalysisProfile404Response`) |
| GET `.../scanner_variables` | 500 | Server error | `Problem` |
| PUT `.../scanner_variables` | 200 | Success — variables replaced | `EffectiveScannerVariables` |
| PUT `.../scanner_variables` | 204 | **Success — all variables deleted** | none |
| PUT `.../scanner_variables` | 401 | Unauthorized | none defined |
| PUT `.../scanner_variables` | 404 | Unknown `analysis_profile_id` | `Problem` (via `Authentication404Response`) |
| PUT `.../scanner_variables` | 500 | Server error | `Problem` |

**0.5.1 — The 204 response is load-bearing for this feature's design.**
"Successfully deleted the scanner variables from the analysis profile"
(OpenAPI description, verbatim) is the documented outcome of a `PUT` whose
body is (or reduces to) an empty array. This is only a coherent behavior if
`PUT` **replaces the entire Scanner Variables list** rather than merging
with what already exists — an endpoint that merged-by-key would never have
a reason to say "deleted" for an empty submission; it would simply be a
no-op. This single documented status code is the confirming evidence for
the full-replace semantics that drive §3.3, §3.3.1–§3.3.4, and design.md §8.

**0.5.2 — Observed inconsistency, preserved as-is.** The `PUT` endpoint's
404 response is documented via `Authentication404Response` ("Unknown
analysis profile or authentication identifier..."), while `GET` uses
`AnalysisProfile404Response` ("Unknown analysis profile identifier...").
Both resolve to the same `Problem` schema, and both conditions are the
same real-world case (`analysis_profile_id` unknown) — this is presumed to
be a copy-paste artifact in Veracode's OpenAPI document, not a
Scanner-Variables-specific behavior difference, matching the same class of
observed-and-preserved inconsistency already noted in
[specs/analysis-profile requirements §0.7](../analysis-profile/requirements.md#07-http-status-codes-and-error-responses).
No code distinguishes between the two; both surface as `VeracodeNotFoundError`.

**0.5.3 — No 400/422 is documented for either endpoint.** Unlike some other
DAST Target Configuration Service resources, no `Problem`-shaped 400/422
response is defined here for e.g. a `reference_key`/`value` exceeding its
255-character bound. If Veracode ever returns one, it propagates unchanged
via the HTTP Client's existing status-code mapping (`VeracodeValidationError`
for 422, `VeracodeApiError` for an unmapped 4xx) — this feature does not
invent a response shape the OpenAPI document doesn't define.

---

## 1. Overview

The Scanner Variables service manages the runtime values (credentials,
TOTP/MFA seeds, tokens) that authentication mechanisms — login scripts,
multi-factor authentication — reference by name during an authenticated
DAST scan. Per [README.md](README.md), users never build the Veracode
API's `ScannerVariablesUpdateRequest` array by hand — they author a small,
flat SDK Configuration document (`{"variables": [{"reference_key": ...,
"value": ..., "totp_seed": ...}, ...]}`) and the SDK is responsible for
loading it, validating it, transforming it into the API request shape,
calling the API, and returning strongly typed models.

This feature follows the same configuration-driven pipeline (Loader →
Validator → Transformer) [specs/scanners-profiles](../scanners-profiles/requirements.md#1-overview)
established as reusable infrastructure, and reuses that pipeline's Loader
rather than re-implementing it (§8.5).

## 2. Goals

- Retrieve the current effective Scanner Variables for an Analysis
  Profile as strongly typed models (`ScannerVariables`, `ScannerVariable`).
- Let users express desired Scanner Variable state using the SDK
  Configuration format instead of the Veracode OpenAPI request shape,
  including the `totp_seed` simplification over the API's `evaluation_mode`
  enum.
- Validate SDK Configuration structurally and semantically (required keys,
  duplicate `reference_key`s, TOTP flag type) before any HTTP call is made.
- Transform validated SDK Configuration into the Veracode API request
  automatically and invisibly to the caller.
- Make the full-replace nature of `update()` explicit and impossible to
  trigger by accident, rather than a surprise a caller discovers after
  variables silently disappear.
- Reuse the shared `HttpClient`, exception hierarchy,
  `TARGET_CONFIGURATION_SERVICE_BASE_URL`, and `utils/sdk_config.py`
  Loader already established by Target Management / Scanner Profiles — no
  new HTTP/auth code, no second JSON-loading implementation.

## 3. Functional Requirements

### 3.1 README/OpenAPI reconciliation (read before §3.2–§3.5)

README's "SDK Configuration" and "Returned Model" sections describe a
shape that does not map field-for-field onto the OpenAPI `ScannerVariable`
schema (§0.2). Per this repository's established practice of treating the
OpenAPI contract as the authoritative *behavior* while README documents the
authoritative *calling convention*
([specs/analysis-profile requirements §3.1](../analysis-profile/requirements.md#31-readmeopenapi-reconciliation-read-before-4-8)),
each divergence is reconciled explicitly below.

3.1.1. **`totp_seed` is a deliberate simplification, not a bug to fix.**
README's design philosophy is explicit: "Unlike the Veracode REST API,
which exposes raw request models, this SDK provides a simplified
configuration format." The API's real field is `evaluation_mode`
(`RAW`/`TOTP`, §0.4); README's public shape is a boolean, `totp_seed`. THE
SYSTEM SHALL map `totp_seed=True` ⇄ `evaluation_mode="TOTP"` and
`totp_seed=False`/absent ⇄ `evaluation_mode="RAW"`, and SHALL NOT expose
`evaluation_mode` or a public `ScannerVariableEvaluationMode` enum type
anywhere in this feature's public interface — doing so would defeat the
purpose of the simplification README documents.

3.1.2. **`is_inherited` is preserved even though README's "Returned Model"
example omits it.** `EffectiveScannerVariable.is_inherited` (§0.2) is
required by the schema on every entry — real, always-present data telling
a caller whether a variable's value comes from a parent Analysis Profile.
Discarding it would lose information the API deliberately provides, the
same reasoning
[specs/analysis-profile requirements §6.1](../analysis-profile/design.md#61-why-inheritedvaluet-instead-of-exposing-raw-values)
already applied to `AnalysisProfile`'s wrapped fields. THE SYSTEM SHALL
add `is_inherited: bool = False` to `ScannerVariable` (§4), defaulting to
`False` so README's literal `ScannerVariable(reference_key="username",
value="admin", totp_seed=False)` constructor call remains valid without
modification.

3.1.3. **`id` is preserved as an optional, read-only field for the same
reason.** `ScannerVariable.id` (§0.2) is real API-assigned data a caller
may want to reference or log. THE SYSTEM SHALL add `id: str | None = None`
to the SDK's `ScannerVariable` model, populated only by `from_api()`. THE
SYSTEM SHALL NOT accept `id` from SDK Configuration, and SHALL NOT include
it when building a `PUT` request body (§7 — `to_api()` never emits `id`).

3.1.4. **`utilize_in_ai_assisted_login` is out of scope.** This API field
describes a distinct, not-yet-scoped authentication capability (AI-Assisted
Login), and README's SDK Configuration and Returned Model examples do not
mention it. THE SYSTEM SHALL NOT expose it as an SDK Configuration key,
SHALL NOT read it into any model, and SHALL NOT send it on `update()` —
the server applies its own documented default (`false`) whenever this
feature's request omits it. This is intentionally minimal, not an
oversight — see §12.1 and design.md §8 for the resulting caveat that a
`update()` call re-sending an existing variable resets this field to
`false` if it was ever set to `true` by some means outside this SDK.

### 3.2 Get Scanner Variables

**User story:** As an SDK consumer, I want to fetch the Scanner Variables
currently effective for an Analysis Profile, so I can inspect them (e.g.
before building an updated configuration) without a raw HTTP call.

3.2.1. WHEN `client.scanner_variables.get(analysis_profile_id)` is called
THEN THE SYSTEM SHALL call `GET
/analysis_profiles/{analysis_profile_id}/scanner_variables` with the given
ID.

3.2.2. IF `analysis_profile_id` is blank (empty or whitespace-only) THEN
THE SYSTEM SHALL raise `ScannerVariableValidationError` (§6.1) and SHALL
NOT make an HTTP call.

3.2.3. WHEN `GET .../scanner_variables` responds 200 THEN THE SYSTEM SHALL
return a typed `ScannerVariables` model whose `variables` list contains one
`ScannerVariable` per entry in the response array, built via
`ScannerVariable.from_api` (preserving `is_inherited` and `id`, per §3.1.2,
§3.1.3).

3.2.4. WHEN `GET .../scanner_variables` responds 404 THEN THE SYSTEM SHALL
let `VeracodeNotFoundError` propagate unchanged.

### 3.3 Update Scanner Variables — full-replace semantics

**User story:** As an SDK consumer, I want to apply a Scanner Variables
configuration and get back exactly the state Veracode now has, understanding
clearly that this call sets the *complete* list rather than patching
individual entries — so I don't accidentally delete variables I forgot to
list.

3.3.1. WHEN `client.scanner_variables.update(analysis_profile_id,
config_file)` is called THEN THE SYSTEM SHALL send the caller's **entire**
validated SDK Configuration `variables` list as the `PUT
/analysis_profiles/{analysis_profile_id}/scanner_variables` request body,
matching `ScannerVariablesUpdateRequest`'s flat-array shape (§0.3).

3.3.2. **THE SYSTEM SHALL NOT merge the supplied configuration with the
Analysis Profile's existing Scanner Variables.** Per §0.5.1, `PUT` is
documented as a full replace — any existing variable whose `reference_key`
is absent from `config_file` is removed by the server, not left unchanged.
THE SYSTEM SHALL NOT call `get()` internally before `update()` to
auto-preserve variables the caller didn't mention — doing so would mask
this behavior rather than make it visible, and README documents no such
merge step in "Update Scanner Variables"'s five-step description. A caller
who wants to keep an existing variable must include it in `config_file`
themselves. This is a safety-critical design decision — see design.md §8.

3.3.3. `config_file` SHALL be either a path to an SDK Configuration JSON
file or an already-loaded/in-memory `dict[str, Any]` — the README's
file-based example is the primary path; accepting a dict too costs nothing
extra and matches the precedent already established by
[specs/scanners-profiles requirements §3.2](../scanners-profiles/requirements.md#3-functional-requirements).

3.3.4. `update()` SHALL perform, in order, before any HTTP call: load
configuration (via the reused Loader, §8.5) → validate structure and
semantics (§5) → transform to the API request shape (§7's `to_api()` per
variable) — matching the steps already documented in
[README.md "Update Scanner Variables"](README.md#update-scanner-variables).

3.3.5. IF `analysis_profile_id` is blank THEN THE SYSTEM SHALL raise
`ScannerVariableValidationError` (§6.1) and SHALL NOT make an HTTP call.

3.3.6. WHEN `PUT .../scanner_variables` responds 200 THEN THE SYSTEM SHALL
return a typed `ScannerVariables` model built from the response body,
per §0.2 — the **server's** post-update state, never a locally
reconstructed one.

3.3.7. WHEN `PUT .../scanner_variables` responds 204 THEN THE SYSTEM SHALL
return `ScannerVariables(variables=[])` — the documented outcome of
submitting an empty (or emptied-down-to-empty) `variables` list (§0.5.1).
THE SYSTEM SHALL NOT attempt to parse a response body in this case (none
is sent).

3.3.8. WHEN `PUT .../scanner_variables` responds 404 THEN THE SYSTEM SHALL
let `VeracodeNotFoundError` propagate unchanged.

### 3.4 SDK Configuration format

**User story:** As an SDK consumer, I want to author Scanner Variables in
the same small, readable JSON shape README documents, without needing to
know the Veracode API's field names.

3.4.1. THE SYSTEM SHALL accept an SDK Configuration document shaped as
`{"variables": [{"reference_key": <str>, "value": <str>, "totp_seed":
<bool, optional, default false>}, ...]}`, matching
[README.md "SDK Configuration"](README.md#sdk-configuration) exactly.

3.4.2. THE SYSTEM SHALL preserve the order of `config_file`'s `variables`
array in the generated `PUT` request body (Python 3.7+ dict/list ordering)
— the same ordering guarantee
[specs/scanners-profiles requirements §7 note](../scanners-profiles/design.md#7-transformation-layer)
already documents for Scanner Profiles.

3.4.3. `{"variables": []}` SHALL be accepted as valid input — but, unlike
Scanner Profiles' equivalent empty case (an inert no-op, per
[specs/scanners-profiles requirements §5.3](../scanners-profiles/requirements.md#5-validation-rules)),
THE SYSTEM SHALL NOT treat it as a no-op: submitting it via `update()`
deletes every existing Scanner Variable from the Analysis Profile (§3.3.2,
§3.3.7). This distinction SHALL be documented prominently, not left
implicit, given how easy it would be to assume symmetry with Scanner
Profiles' behavior.

## 4. Typed models and enumerations

**User story:** As an SDK consumer, I want Scanner-Variable-related models
as real Python types, so a malformed configuration is caught by my editor
and by `mypy` instead of at runtime inside Veracode's API.

4.1. THE SYSTEM SHALL define `ScannerVariable` as a frozen dataclass with
fields `reference_key: str`, `value: str | None = None`,
`totp_seed: bool = False`, `is_inherited: bool = False`,
`id: str | None = None` (§3.1.2, §3.1.3), with `from_api()` and `to_api()`
methods (§7). `value` is `None` on a model built by `from_api()`: the API
stores values write-only and omits them from `GET`/`PUT` responses even
though the OpenAPI schema marks `value` required. Callers still supply a
non-blank `value` when constructing variables to write (§5.7).

4.2. THE SYSTEM SHALL define `ScannerVariables` as a frozen dataclass with
a single field `variables: list[ScannerVariable]`, with a `from_api()`
classmethod, matching
[README.md "Returned Model"](README.md#returned-model)'s
`ScannerVariables(variables=[...])` shape exactly.

4.3. THE SYSTEM SHALL NOT define a public `ScannerVariableEvaluationMode`
enum type, per §3.1.1 — the `RAW`/`TOTP` distinction is represented
internally only, as the two string literals used inside `to_api()`/
`from_api()`, never as part of this feature's public interface.

4.4. THE SYSTEM SHALL NOT define a model for `Problem`, `ProblemError`,
`InheritableValue`, or `EffectiveScannerVariable` as standalone types —
`InheritableValue`'s `is_inherited` is folded directly onto
`ScannerVariable` (§3.1.2) rather than kept as a separate generic wrapper,
because — unlike Analysis Profile's thirteen independently wrapped fields
— exactly one field on this resource carries the wrapper, so a generic
`InheritedValue[T]` (already available from
[specs/analysis-profile design §2.3](../analysis-profile/design.md#23-a-new-shared-module-modelscommonpy))
would add a layer of indirection (`ScannerVariable.value_wrapper.effective_value.value`)
for no benefit over a flat field. `Problem`/`ProblemError` are the same
generic REST transport shapes already excluded by
[specs/analysis-profile requirements §4.8](../analysis-profile/requirements.md#4-typed-models-and-enumerations).

4.5. Both models SHALL comply with the model rules in
[AGENTS.md §3](../../AGENTS.md#3-architecture) (never perform HTTP
requests, contain business logic, or depend on the HTTP Client).

## 5. Client-side validation

**User story:** As an SDK consumer, I want an obviously malformed Scanner
Variables configuration rejected immediately, with a message that tells me
exactly what's wrong, so I don't make a round trip to Veracode — and don't
silently delete variables via a typo — for a mistake my code could catch
locally.

All of the following are checked **before** any HTTP call, and each raises
before any network I/O occurs. Every rule below maps directly onto one of
the five categories listed in
[README.md "Validation"](README.md#validation) ("Missing reference keys",
"Duplicate variables", "Missing values", "Invalid TOTP configuration",
"Invalid configuration structure").

5.1. `analysis_profile_id` must be non-blank (after `.strip()`) →
`ScannerVariableValidationError(rule="analysis_profile_id_required")`.

5.2. `config_file`, once loaded, must deserialize to a JSON **object**
(Python `dict`) →
`ScannerVariableValidationError(rule="config_must_be_object")` — README
"Invalid configuration structure".

5.3. The loaded configuration must contain a `"variables"` key whose value
is a JSON **array** →
`ScannerVariableValidationError(rule="variables_key_required")` — README
"Invalid configuration structure". Per §3.4.3, an empty array is
structurally valid but is **not** a no-op at the `update()` level.

5.4. Every entry inside `"variables"` must itself be a JSON object →
`ScannerVariableValidationError(rule="variable_must_be_object")` — README
"Invalid configuration structure".

5.5. Every entry must contain a non-blank `"reference_key"` string →
`ScannerVariableValidationError(rule="reference_key_required")` — README
"Missing reference keys".

5.6. No two entries in `"variables"` may share the same `"reference_key"`
→ `ScannerVariableValidationError(rule="duplicate_reference_key")`, naming
the offending key — README "Duplicate variables". This is checked because,
unlike Scanner Profiles' fixed-size scanner set, `variables` is an
arbitrary-length list where a duplicate key is unambiguously an authoring
mistake, not a meaningful configuration.

5.7. Every entry must contain a non-blank `"value"` string →
`ScannerVariableValidationError(rule="value_required")` — README "Missing
values".

5.8. `"totp_seed"`, when present, must be a JSON boolean (not a string or
number) →
`ScannerVariableValidationError(rule="invalid_totp_configuration")` —
README "Invalid TOTP configuration". When absent, it defaults to `False`
(§4.1); its absence is not itself an error.

5.9. When `config_file` is a filesystem path, the file must exist and
contain valid JSON → `ConfigFileNotFoundError` / `ConfigFileInvalidError`
(reused from
[specs/scanners-profiles design §3.2](../scanners-profiles/design.md#32-srcveracode_dastexceptionspy-extended),
not redefined — §8.5).

5.10. THE SYSTEM SHALL NOT duplicate the server-side 1–255 character
length bound on `reference_key`/`value` (§0.2) as client-side validation —
same reasoning
[specs/analysis-profile requirements §3.4.6](../analysis-profile/requirements.md#34-update-analysis-profile)
already applies to Analysis Profile's numeric ranges: a simple, independent
bound documented on the model, not a conditional rule a caller couldn't
discover from type hints. A value outside these bounds surfaces as
whichever exception the HTTP Client maps the resulting status code to
(§0.5.3), unmodified.

5.11. THE SYSTEM SHALL NOT validate whether a `totp_seed=true` value is
actually a well-formed TOTP seed (e.g. valid Base32) — that is a Veracode
business rule this feature does not attempt to replicate, the same
reasoning
[specs/scanners-profiles requirements §5.7](../scanners-profiles/requirements.md#5-validation-rules)
already applies to scanner-eligibility rules.

5.12. THE SYSTEM SHALL NOT validate unrecognized keys inside a `variables`
entry (e.g. a typo'd field name beyond `reference_key`/`value`/
`totp_seed`) — README's "Validation" section documents no such rule, and
inventing one would be an unrequested restriction (contrast with §5.5–5.8,
which all trace to a README-documented category).

## 6. Error handling

**User story:** As an SDK consumer, I want a clear distinction between "my
configuration was obviously invalid before any request was sent" and
"Veracode rejected my request," so I can handle each case appropriately.

6.1. THE SYSTEM SHALL define
`ScannerVariableValidationError(VeracodeSDKError)` — not a subclass of
`VeracodeApiError` — with a `rule` attribute, for every check in §5.1–§5.8,
following the exact naming/subclassing convention already established by
`ScannerValidationError`/`AnalysisProfileValidationError` (`<Resource>ValidationError`,
subclassing `VeracodeSDKError` directly).

6.2. THE SYSTEM SHALL reuse `ConfigFileNotFoundError`/`ConfigFileInvalidError`
from `utils/sdk_config.py` (§5.9, §8.5) rather than defining
Scanner-Variables-specific equivalents.

6.3. THE SYSTEM SHALL NOT define an "unknown reference key" exception
analogous to Scanner Profiles' `UnknownScannerError` — `reference_key`
values are arbitrary, consumer-defined strings with no closed set to check
membership against (unlike Scanner Profiles' 35-member `ScannerType`), so
no "did you mean" suggestion mechanism applies here (§12.4).

6.4. THE SYSTEM SHALL NOT define any other new exception type. Every
failure that occurs after an HTTP request is sent (401, 404, 500, other
statuses, connection errors, timeouts) SHALL surface as whichever
exception the HTTP Client already defines for that condition, unmodified
and unwrapped.

6.5. THE SYSTEM SHALL NOT catch and swallow any exception raised by the
HTTP Client; `ScannerVariablesService` only ever lets it propagate.

## 7. Transformation

**User story:** As an SDK consumer, I want the SDK Configuration's
simplified shape transformed into the Veracode API's request shape
automatically, so I never construct `ScannerVariablesUpdateRequest`
objects by hand.

7.1. THE SYSTEM SHALL transform each validated SDK Configuration entry
into a `ScannerVariable`, then into its API request shape via `to_api()`:
`{"reference_key": ..., "value": ..., "evaluation_mode": "TOTP" if
totp_seed else "RAW"}` — never including `id` or
`utilize_in_ai_assisted_login` (§3.1.3, §3.1.4).

7.2. THE SYSTEM SHALL build the `PUT` request body as a flat JSON array of
these objects — `[variable.to_api() for variable in variables]` — matching
`ScannerVariablesUpdateRequest`'s shape (§0.3) exactly; THE SYSTEM SHALL
NOT wrap it in a `{"variables": [...]}` object (that shape is the SDK
Configuration's, not the API request's).

## 8. Logging

**User story:** As an SDK maintainer, I want Scanner Variables to log
meaningful business events, without ever leaking a variable's value —
these are credentials, TOTP seeds, and tokens by definition (README
"Runtime Variables").

8.1. WHEN Scanner Variables are successfully retrieved THEN THE SYSTEM
SHALL emit an INFO-level log stating how many variables were returned and
the `analysis_profile_id`.

8.2. WHEN Scanner Variables are successfully updated THEN THE SYSTEM SHALL
emit an INFO-level log naming the operation, the `analysis_profile_id`,
and the number of variables sent.

8.3. **THE SYSTEM SHALL NEVER log a `ScannerVariable.value`, under any
circumstance, at any log level.** This is the single most safety-critical
requirement in this specification: these values are, per README, "Login
script variables," "Multi-factor authentication (TOTP) secrets," "Runtime
credentials," and "Authentication tokens." `reference_key` names MAY be
logged (they are identifiers, not secrets) alongside counts, matching
[AGENTS.md §6.2](../../AGENTS.md#62-business-data)'s "business data" rule
applied at maximum strictness.

8.4. THE SYSTEM SHALL NOT re-implement HTTP request/response logging;
that responsibility belongs entirely to the HTTP Client.

## 9. Public interface and reuse

**User story:** As an SDK consumer, I want `client.scanner_variables` to
be the resource-oriented entry point README and AGENTS.md promise, reusing
the same `HttpClient` instance and configuration-loading infrastructure
already built for sibling Phase 2 features.

9.1. THE SYSTEM SHALL expose a `ScannerVariablesService` class whose public
methods are exactly `get` and `update`, matching README's Features list.
THE SYSTEM SHALL NOT add `create`, `delete`, or any `get_by_name`-style
convenience method — the REST API exposes neither a create/delete
operation distinct from `update()` (an empty `update()` already deletes
everything, §3.3.7) nor any filter a name-based lookup could use.

9.2. THE SYSTEM SHALL wire `ScannerVariablesService` onto `VeracodeClient`
as `client.scanner_variables`, reusing the same `HttpClient` instance
already constructed for `TargetsService`/`ApiSpecificationsService`/sibling
Phase 2 services (all configured with
`TARGET_CONFIGURATION_SERVICE_BASE_URL`) rather than constructing a new
one.

9.3. Every public class and method introduced by this feature SHALL
comply with the code conventions in
[AGENTS.md §7](../../AGENTS.md#7-code-conventions) (complete type hints,
Google-style docstrings).

9.4. `ScannerVariablesService` SHALL comply with the Stateless principle in
[AGENTS.md §5](../../AGENTS.md#5-design-principles): it holds only its
`HttpClient` instance; no scanner variable data is cached or retained
between calls.

9.5. **THE SYSTEM SHALL reuse `utils/sdk_config.load_json_config`**
(config loading, path-or-dict) from
[specs/scanners-profiles design §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared)
rather than re-implementing it. If Scanner Profiles has not yet been
implemented when this feature is built, `utils/sdk_config.py` (and
`ConfigFileNotFoundError`/`ConfigFileInvalidError` in `exceptions.py`) SHALL
be created first, exactly as that spec defines them — this feature does
not define a second, parallel Loader.

9.6. THE SYSTEM SHALL NOT reuse or need `suggest_closest()` — per §6.3,
there is no closed name set for `reference_key` to validate membership
against.

## 10. Testability

**User story:** As a maintainer, I want to verify request shaping, response
parsing, full-replace behavior, and the configuration pipeline without a
real Veracode account.

10.1. THE SYSTEM SHALL allow every `ScannerVariablesService` method to be
tested by constructing it with a fake/stub `HttpClient` returning prepared
`HttpResponse` values, with no real network access, environment variables,
or Veracode credentials required — the same pattern already used by
`tests/services/test_targets.py` and `tests/services/test_scanners.py`.

10.2. THE SYSTEM SHALL NOT require a new third-party mocking/HTTP-fixture
dependency beyond what
[specs/http-client requirements §12](../http-client/requirements.md)
already establishes.

---

## 11. Non-Functional Requirements

- **Reuse over duplication.** No new Veracode API base URL, no new
  `HttpClient` instance, no re-implementation of `utils/sdk_config.py`'s
  Loader or its `ConfigFileNotFoundError`/`ConfigFileInvalidError`
  exceptions.
- **Stateless.** `ScannerVariablesService` holds only an injected
  `HttpClient`; every call is independent (§9.4).
- **Platform-agnostic.** No dependency on Azure DevOps, a CLI, or any
  other specific consumer (per
  [AGENTS.md §5](../../AGENTS.md#5-design-principles)).
- **Typed.** Every public method has complete type hints; every response
  is returned as a frozen dataclass, never a raw `dict`/`list`.
- **Testable offline.** Every test in this feature runs without network
  access or real credentials (§10).
- **Secrets never logged.** No log record produced by this feature ever
  contains a `ScannerVariable.value` (§8.3) — the strictest logging rule
  in this SDK, since this resource's entire purpose is storing credentials.
- **Full-replace semantics are explicit, not hidden.** `update()`'s
  behavior (§3.3.2) is documented in this spec, in design.md, and in the
  service's own docstring — never silently mitigated by an auto-merge that
  would mask what the real API does (§3.3.2).
- **No behavior change to Target Management, API Specification
  Management, Analysis Profiles, or Scanner Profiles.** This feature only
  adds a new service/model pair and one new exception class; it does not
  modify any existing service, model, or the shared `utils/sdk_config.py`
  beyond what Scanner Profiles already defines there.

---

## 12. Acceptance Criteria

Scenario-based checklist a reviewer can run through to confirm this
feature meets requirements. Each scenario references the Functional
Requirement it verifies.

1. **Given** a valid `analysis_profile_id`, **when** `get(...)` is called,
   **then** exactly one `GET` request is made and the result's
   `.variables` contains one `ScannerVariable` per response entry, with
   `is_inherited`/`id` populated from the response (§3.2.1, §3.2.3).
2. **Given** a blank `analysis_profile_id`, **when** `get(...)` or
   `update(...)` is called, **then** `ScannerVariableValidationError` is
   raised and no HTTP request is made (§3.2.2, §3.3.5).
3. **Given** the exact SDK Configuration from
   [README "SDK Configuration"](README.md#sdk-configuration), **when**
   `update(analysis_profile_id=..., config_file="scanner-variables.json")`
   is called, **then** the `PUT` request body is a flat JSON array whose
   `otp` entry has `"evaluation_mode": "TOTP"` and whose other entries have
   `"evaluation_mode": "RAW"`, and the call returns the updated
   `ScannerVariables` (§3.1.1, §7.1, §7.2).
4. **Given** an Analysis Profile that currently has three Scanner
   Variables, **when** `update(...)` is called with a configuration
   listing only one of them, **then** the request body contains only that
   one entry — confirming this feature performs no read-then-merge — and
   after the call, only that one variable remains (per the real API's
   full-replace behavior) (§3.3.1, §3.3.2).
5. **Given** `config_file={"variables": []}`, **when** `update(...)` is
   called and the HTTP Client returns a 204 response, **then** `update()`
   returns `ScannerVariables(variables=[])` without attempting to parse a
   response body (§3.3.7).
6. **Given** a configuration containing two entries with the same
   `reference_key`, **when** `update(...)` is called, **then**
   `ScannerVariableValidationError(rule="duplicate_reference_key")` is
   raised before any HTTP request is made (§5.6).
7. **Given** a configuration entry with `"totp_seed": "yes"` (a string, not
   a boolean), **when** `update(...)` is called, **then**
   `ScannerVariableValidationError(rule="invalid_totp_configuration")` is
   raised before any HTTP request is made (§5.8).
8. **Given** a configuration missing a `"reference_key"` or `"value"` on
   one entry, **when** `update(...)` is called, **then** the corresponding
   `ScannerVariableValidationError` is raised before any HTTP request is
   made (§5.5, §5.7).
9. **Given** a 404 response from the HTTP Client, **when** `get(...)` or
   `update(...)` is called, **then** `VeracodeNotFoundError` propagates
   unmodified (§3.2.4, §3.3.8).
10. **Given** `VeracodeClient()`, **when** it is constructed, **then**
    `client.scanner_variables` is a `ScannerVariablesService` sharing the
    same `HttpClient` instance as `client.targets` (§9.2).
11. **Given** any successful `get()`/`update()` call in a test asserting on
    `caplog`, **when** the captured log records are inspected, **then**
    none contains any configured `value` (§8.3).

---

## 13. Out of Scope

13.1. THE SYSTEM SHALL NOT expose `utilize_in_ai_assisted_login` as an SDK
Configuration key or model field (§3.1.4) — AI-Assisted Login is a
distinct, not-yet-scoped authentication capability.

13.2. THE SYSTEM SHALL NOT implement a read-then-merge convenience on top
of `update()` (§3.3.2) — this would mask, not solve, the full-replace
behavior the real API implements; a future feature could add one
explicitly (e.g. `upsert()`) if a concrete consumer need arises, but none
is identified now.

13.3. THE SYSTEM SHALL NOT implement an "unknown reference key" /
"did you mean" suggestion mechanism (§6.3, §9.6) — there is no closed set
of valid `reference_key` values to check membership against.

13.4. THE SYSTEM SHALL NOT implement Authentication Configuration, Scanner
Profiles, Analysis Profiles CRUD, Crawl Configuration, or ISM Gateway
configuration — each is (or will be) its own feature with its own spec,
per [README.md "Future Vision"](README.md#future-vision).

13.5. THE SYSTEM SHALL NOT validate whether a `totp_seed=true` value is a
well-formed TOTP seed, or replicate any other Veracode business rule
server-side (§5.11).

13.6. THE SYSTEM SHALL NOT implement a combined, multi-resource
`dast-config.json` (README "Future Vision") — this feature only ever reads
a single Scanner Variables configuration document.

13.7. THE SYSTEM SHALL NOT modify `services/targets.py`,
`services/api_specifications.py`, `services/teams.py`,
`services/analysis_profiles.py`, `services/scanners.py`, or
`utils/sdk_config.py` — every reuse in this feature is an import, never an
edit.

13.8. THE SYSTEM SHALL NOT implement a CLI or any execution-platform
integration (AGENTS.md §1 non-goals).
