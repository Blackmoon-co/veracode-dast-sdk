# Requirements — ISM Gateways

Traceable to [README.md](README.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Phase 2 ("Configure
Targets"), per [AGENTS.md §10](../../AGENTS.md#10-roadmap). Reuses
[specs/target-management](../target-management/requirements.md) (the
`HttpClient` instance and `TARGET_CONFIGURATION_SERVICE_BASE_URL`
constant) and the configuration-driven pipeline first built by
[specs/scanners-profiles](../scanners-profiles/requirements.md)
(`utils/sdk_config.load_json_config`, `suggest_closest`,
`ConfigFileNotFoundError`, `ConfigFileInvalidError`) — this feature adds
no new API base URL, no new Veracode API domain, and no second
config-loading implementation.

REST contract: `openApi/Veracode-veracode-dast-target-configuration-service-api-1.0.0-resolved.json`
("Veracode DAST Target Configuration Service API", v1.0.0, server
`https://api.veracode.com/dae/api/tcs-api/api/v1`).

Format: OpenAPI review, README/OpenAPI reconciliation (unusually
significant for this feature — read before anything else), then
Functional Requirements as EARS-style ("THE SYSTEM SHALL...") acceptance
criteria, Non-Functional Requirements, a scenario-based Acceptance
Criteria checklist, and an explicit Out of Scope section.

---

## 0. OpenAPI Contract Reference

This section documents the portion of the OpenAPI contract relevant to
ISM Gateways. It is the factual basis §3's Functional Requirements are
derived from — nothing below introduces a REST behavior not captured
here.

### 0.1 In-scope REST endpoints

| Method | Path | operationId | Purpose |
|---|---|---|---|
| GET | `/ism_gateways` | `getIsmGateways` | List every ISM gateway available to the account. |
| GET | `/ism_gateways/targets/{target_id}` | `getTargetIsmGateway` | Get the ISM gateway currently assigned to a target. |
| PUT | `/ism_gateways/targets/{target_id}` | `updateTargetIsmGateway` | Assign, change, or clear the ISM gateway assigned to a target. |

There is no fourth `ism_gateway`-tagged operation in the OpenAPI document
— these three are the entire tag.

### 0.2 Schemas

**`IsmGateway`** (`getIsmGateways` 200 array item) — no `required` list
(every property is technically optional per the schema; in practice a
registered gateway always has each of these):

| Field | Type | Notes |
|---|---|---|
| `refId` | string | The gateway's unique identifier. |
| `name` | string | Human-readable gateway name — what README calls "gateway name." |
| `hostname` | string | The gateway's network hostname. |
| `endpoints` | array of `IsmEndpoint` | See below. |
| `status` | string | Unconstrained (no enum in the OpenAPI); README's example shows `"ONLINE"`. |

**`IsmEndpoint`** (item of `IsmGateway.endpoints`) — no `required` list,
no field descriptions in the OpenAPI document:

| Field | Type | Notes |
|---|---|---|
| `token` | string | No description given. The only field on this schema that is not obviously a display label — see §1.3 for why this feature treats it as the endpoint's identifier. |
| `name` | string | No description given. |
| `status` | string | No description given. |

**`TargetIsmGateway`** (`getTargetIsmGateway`/`updateTargetIsmGateway` 200
body, and `updateTargetIsmGateway` request body) — no `required` list:

| Field | Type |
|---|---|
| `gatewayUuid` | string |
| `endpointUuid` | string |

This is the **only** shape the assignment endpoints read or write. It
carries no gateway name, no status, no hostname — just the two
identifiers. Neither field is documented as nullable, but neither is
required either; §1.4 covers what an unassigned target's `GET` response
and a "clear the assignment" `PUT` request look like.

**`Problem`** — the same RFC 7807 problem-details shape already
documented in
[specs/target-management requirements §0.4](../target-management/requirements.md#04-schemas).
The API-wide error-code enum includes `ISM_GATEWAY_MAPPING_ERROR` and
`TARGET_ISM_CONFIGURATION_REQUIRED`, both scoped to this resource; neither
is replicated client-side (§6.9) — they propagate through whatever HTTP
status the HTTP Client maps them to.

### 0.3 HTTP status codes and error responses

| Endpoint | Status | Meaning | Body schema |
|---|---|---|---|
| GET `/ism_gateways` | 200 | Success | `IsmGateway[]` |
| GET `/ism_gateways` | 401 | Unauthorized | none defined |
| GET `/ism_gateways` | 403 | Forbidden | none defined |
| GET `/ism_gateways` | 404 | Resource not found | none defined |
| GET `/ism_gateways` | 500 | Server error | `Problem` |
| GET `/ism_gateways/targets/{id}` | 200 | Success | `TargetIsmGateway` |
| GET `/ism_gateways/targets/{id}` | 401 | Unauthorized | none defined |
| GET `/ism_gateways/targets/{id}` | 403 | Forbidden | none defined |
| GET `/ism_gateways/targets/{id}` | 500 | Server error | `Problem` |
| PUT `/ism_gateways/targets/{id}` | 200 | Success | `TargetIsmGateway` |
| PUT `/ism_gateways/targets/{id}` | 401 | Unauthorized | none defined |
| PUT `/ism_gateways/targets/{id}` | 403 | Forbidden | none defined |
| PUT `/ism_gateways/targets/{id}` | 404 | Resource not found (unknown `target_id`) | none defined |
| PUT `/ism_gateways/targets/{id}` | 500 | Server error | `Problem` |

**0.3.1 — `GET /ism_gateways/targets/{id}` documents no 404.** Only GET
`/ism_gateways` (the list endpoint) documents 404 among the per-target
endpoints; the target-scoped GET does not. Combined with §0.2's
observation that neither `gatewayUuid` nor `endpointUuid` is required,
this is read as: an existing target with no ISM gateway assigned
returns **200** with an empty/absent-valued `TargetIsmGateway`, not a 404
— see §1.4 and §3.3.

**0.3.2 — No `method=PATCH` query parameter, unlike Analysis Profile's
`PUT`.** [specs/analysis-profile requirements §0.4](../analysis-profile/requirements.md#04-query-parameters--put-analysis_profilesanalysis_profile_id)
documents `method=PATCH` as load-bearing for that resource's partial-update
semantics. No equivalent parameter exists on `updateTargetIsmGateway` —
this `PUT` is read as an ordinary full-replace, which is exactly the
behavior §3.4 (`remove()`) relies on: submitting an empty body clears
both fields rather than leaving them unchanged.

---

## 1. README/OpenAPI Reconciliation (read before §3)

Per this repository's established practice of treating the OpenAPI
contract as the authoritative *behavior* while README documents the
authoritative *calling convention*
([specs/analysis-profile requirements §3.1](../analysis-profile/requirements.md#31-readmeopenapi-reconciliation-read-before-4-8),
[specs/scanner-variables requirements §3.1](../scanner-variables/requirements.md#31-readmeopenapi-reconciliation-read-before-32-35)),
this feature has three divergences to reconcile — more than usual, and
more consequential, since one of them changes a method's addressing
parameter, not just a request-body field name.

### 1.1 The scoping identifier is `target_id`, not `analysis_profile_id`

README's every example — `get()`, `update()`, `remove()` — passes
`analysis_profile_id`. The task brief that commissioned this module does
the same. But **no endpoint anywhere in the OpenAPI document accepts an
`analysis_profile_id`** for ISM Gateway operations; both target-scoped
endpoints are `/ism_gateways/targets/{target_id}` (§0.1), and the path
parameter is explicitly documented as `"description": "ID of the
target."`.

This is not a cosmetic naming choice: `AnalysisProfile.target_id` is
**optional** ([specs/analysis-profile requirements §0.5](../analysis-profile/requirements.md#05-schemas))
— only `TARGET`-type profiles have one; `ORG`/`SYSTEM`-type profiles do
not. "The ISM gateway associated with an Analysis Profile" is therefore
not even a coherent concept for two of the three profile types the REST
API defines. ISM Gateway assignment is, per the actual contract, a
property of a **Target**, not of an Analysis Profile.

**Resolution:** every public method in this feature takes `target_id`,
matching the OpenAPI exactly. This makes `IsmGatewaysService`
architecturally a sibling of
[`ApiSpecificationsService`](../api-specification-management/design.md)
(also addressed by `target_id` alone, e.g. `upload(target_id, ...)`,
`get(target_id)`), not of `ScannersService`/`ScannerVariablesService`
(addressed by `analysis_profile_id`). A caller who starts from an
`analysis_profile_id` and needs a `target_id` resolves it themselves —
e.g. `client.analysis_profiles.get(analysis_profile_id).target_id` — the
same way README's own "Related Services" section already shows two
separate calls used in sequence, rather than one service reaching into
another's REST surface. `IsmGatewaysService` gains no dependency on
`AnalysisProfilesService` because of this.

README's parameter *name* is superseded; its *behavioral promise* — name-
based gateway configuration, no manual ID handling — is fully preserved
(see §1.2–§1.3).

### 1.2 Assigning a gateway requires resolving an endpoint too, not just a gateway

README's mental model is flat: one `gateway_name` in, one `ISMGateway`
out. The real request/response shape (`TargetIsmGateway`, §0.2) is
two-level: a gateway has a list of `endpoints`, and assignment requires
**both** `gatewayUuid` and `endpointUuid` — README never mentions
"endpoint" once.

**Resolution:** the SDK still exposes only `gateway_name` to callers
(README's promise is kept in full); internally, the Gateway Resolver
(§3.2) also selects the target gateway's endpoint automatically:

- Exactly one endpoint on the resolved gateway → selected automatically,
  no caller involvement.
- Zero endpoints → resolution fails (`IsmGatewayValidationError`,
  rule `gateway_has_no_endpoint`) — there is nothing to assign.
- More than one endpoint → resolution fails
  (`IsmGatewayValidationError`, rule `gateway_endpoint_ambiguous`) rather
  than guessing. Neither README nor the OpenAPI describe any way for a
  caller to name a specific endpoint, so inventing a selection rule for
  the multi-endpoint case would be undocumented behavior masquerading as
  a real feature. See §13.2 for the deferred extension.

### 1.3 `IsmEndpoint.token` is assumed to be the endpoint's identifier — flagged, not asserted

`TargetIsmGateway.endpointUuid` needs *some* value; `IsmEndpoint` (§0.2)
has exactly three fields (`token`, `name`, `status`), none documented as
an identifier, and the OpenAPI gives zero descriptive text for any of the
three. `name`/`status` read as a display label and a state, by analogy
with `IsmGateway`'s own `name`/`status`; `token` is the only remaining
candidate.

**This is an assumption, not a confirmed fact.** It is used because it is
the best available reading of an underspecified schema, not because the
OpenAPI or any example payload confirms it. §13.5 requires this
assumption be validated against a live/sandbox Veracode account before
`update()`/`remove()` ship; if it proves wrong, only the Gateway
Resolver's endpoint-selection step (design.md §5) needs to change — no
public interface is affected.

`IsmEndpoint.token` is also treated as security-sensitive (its name alone
suggests it may function like a credential) and is never logged, matching
the treatment of `ScannerVariable.value` in
[specs/scanner-variables requirements §8.3](../scanner-variables/requirements.md#8-logging).

### 1.4 `remove()` has no REST operation of its own

The OpenAPI defines no `DELETE /ism_gateways/targets/{target_id}` (§0.1).
Per §0.3.1/§0.3.2, `PUT` has no `method=PATCH`-equivalent parameter and
neither request field is required, so a plain full-replace `PUT` with an
empty body is read as the mechanism for "no gateway assigned" — the same
shape `getTargetIsmGateway` is assumed to return for a target that has
never had one assigned. `remove()` is implemented as `PUT
/ism_gateways/targets/{target_id}` with body `{}` (§3.4). This is flagged
alongside §1.3 as an assumption requiring live-account validation before
release (§13.5) — the OpenAPI does not explicitly document empty-body
`PUT` semantics for this endpoint the way it documents `method=PATCH` for
Analysis Profiles.

### 1.5 Exception naming keeps README's exact names where README fixes them

README's own "Exceptions" and "Validation" sections literally name
`GatewayNotFoundError` and describe "Duplicate gateway names" as a
distinct validation case. Per the same practice
[specs/scanners-profiles design §3.2](../scanners-profiles/design.md#32-srcveracode_dastexceptionspy-extended)
applied to `UnknownScannerError` (a README-fixed exception name kept
verbatim), this feature keeps `GatewayNotFoundError` exactly as README
spells it — not renamed to `IsmGatewayNotFoundError` — and extends the
same short "Gateway"-prefixed family to the sibling ambiguous-name case,
`GatewayNameNotUniqueError` (§6.2–§6.3). Every other new exception
follows the SDK's standard `<Resource>ValidationError` convention:
`IsmGatewayValidationError`.

### 1.6 The public model class keeps README's literal `ISMGateway` spelling

The SDK's general convention drops acronym casing in class names (`Api`,
not `API` — see `ApiSpecification`). README, however, spells the
returned model `ISMGateway` explicitly and repeatedly, including in a
literal constructor call (`ISMGateway(id="gateway-id", name="Corporate
Gateway", status="ONLINE")`, README "Returned Model"). Per §1.5's same
reasoning, this one class name is kept exactly as README fixes it:
`ISMGateway` (and its nested `ISMEndpoint`), while every class this
feature invents itself — the service, the exceptions — follows the SDK's
ordinary PascalCase convention (`IsmGatewaysService`,
`IsmGatewayValidationError`).

---

## 2. Overview

The ISM Gateways service manages which Internal Scanning Management
gateway, if any, a DAST Target uses to reach a privately hosted
application. Per [README.md](README.md), users configure a gateway by
name; the SDK is responsible for listing available gateways, resolving a
name to the `gatewayUuid`/`endpointUuid` pair the REST API actually
requires (§1.2–§1.3), calling the API, and returning a strongly typed,
human-readable `ISMGateway`. Unlike Scanner Profiles/Scanner Variables,
this feature supports **two** equivalent ways to specify the desired
gateway on `update()` — a direct `gateway_name` keyword argument, or a
`config_file` — rather than being config-only.

This is the first Phase 2 feature whose primary REST resource is
addressed by `target_id` rather than `analysis_profile_id` (§1.1), and
the first to need to resolve a human-readable name into **two** REST
identifiers rather than one.

## 3. Goals

- Provide typed, resource-oriented access to ISM Gateways:
  `client.ism_gateways.list()`, `.get(target_id)`,
  `.update(target_id, ...)`, `.remove(target_id)`, matching
  [README.md](README.md)'s behavioral promise (parameter naming
  superseded per §1.1).
- Let users express the desired gateway using a plain `gateway_name`
  string or an SDK Configuration file — never a `gatewayUuid`/
  `endpointUuid` pair.
- Validate structure and resolve names to identifiers entirely
  client-side, before any HTTP call that assigns a gateway.
- Reuse the shared `HttpClient`, exception hierarchy,
  `TARGET_CONFIGURATION_SERVICE_BASE_URL`, and the
  `utils/sdk_config.py` Loader/suggestion helper already established (or
  to be established) by Scanner Profiles — no new HTTP/auth code, no
  second JSON-loading implementation.
- Produce descriptive, specific exceptions for every gateway-resolution
  failure mode README documents (not found, ambiguous/duplicate name).

## 4. Functional Requirements

### 4.1 List available ISM Gateways

**User story:** As an SDK consumer, I want to see every ISM gateway
available to my account, so I can find the name I need before assigning
it to a target.

4.1.1. WHEN `client.ism_gateways.list()` is called THEN THE SYSTEM SHALL
call `GET /ism_gateways` with no parameters.

4.1.2. WHEN `GET /ism_gateways` responds 200 THEN THE SYSTEM SHALL return
`list[ISMGateway]`, one entry per array item, via `ISMGateway.from_api`.

4.1.3. THE SYSTEM SHALL NOT wrap the result in a page/container object —
the REST response is a bare array with no pagination metadata (§0.2), so
none is invented.

### 4.2 Get the gateway assigned to a target

**User story:** As an SDK consumer, I want to know which gateway, if any,
a target currently uses, so I can inspect or confirm its configuration
without hand-building a REST call.

4.2.1. WHEN `client.ism_gateways.get(target_id)` is called THEN THE
SYSTEM SHALL call `GET /ism_gateways/targets/{target_id}`.

4.2.2. IF `target_id` is blank (empty or whitespace-only) THEN THE SYSTEM
SHALL raise `IsmGatewayValidationError` (rule `target_id_required`, §6.1)
and SHALL NOT make an HTTP call.

4.2.3. WHEN `GET .../targets/{target_id}` responds 200 with both
`gatewayUuid` and `endpointUuid` present THEN THE SYSTEM SHALL call
`list()` (§4.1), find the `ISMGateway` whose `id` equals the response's
`gatewayUuid`, and return it.

4.2.4. WHEN `GET .../targets/{target_id}` responds 200 with `gatewayUuid`
absent, null, or blank THEN THE SYSTEM SHALL return `None` — per §0.3.1,
a target with no gateway assigned is a normal, successful outcome, not an
error.

4.2.5. IF `list()` (invoked by 4.2.3) contains no gateway matching the
response's `gatewayUuid` THEN THE SYSTEM SHALL raise
`IsmGatewayValidationError` (rule `gateway_not_found_by_id`) — an
inconsistent-account-state case (the assignment references a gateway
that no longer exists in `list()`), not a caller mistake, but still a
condition the SDK cannot silently paper over by returning a nameless
result.

4.2.6. WHEN `GET .../targets/{target_id}` responds with any error status
THEN THE SYSTEM SHALL let the corresponding HTTP Client exception
propagate unchanged (§0.3: no 404 is documented for this endpoint, so a
404 — if the API ever returns one for an unknown `target_id` — surfaces
as `VeracodeNotFoundError` the same as any other unmapped case).

### 4.3 Update (assign or change) the gateway assigned to a target

**User story:** As an SDK consumer, I want to assign a gateway to a
target by name, or from a small configuration file, without ever
constructing a `gatewayUuid`/`endpointUuid` pair myself.

4.3.1. `client.ism_gateways.update(target_id, *, gateway_name=None,
config_file=None)` SHALL accept **exactly one** of `gateway_name` (a
plain string) or `config_file` (a path to an SDK Configuration JSON file,
or an already-loaded `dict[str, Any]`) — matching both call forms shown
in [README.md](README.md) "Update Gateway Assignment".

4.3.2. IF neither `gateway_name` nor `config_file` is supplied, OR both
are supplied, THEN THE SYSTEM SHALL raise `IsmGatewayValidationError`
(rule `gateway_name_or_config_file_required`) and SHALL NOT make an HTTP
call.

4.3.3. IF `target_id` is blank THEN THE SYSTEM SHALL raise
`IsmGatewayValidationError` (rule `target_id_required`) and SHALL NOT
make an HTTP call.

4.3.4. WHEN `config_file` is supplied THEN THE SYSTEM SHALL, before any
HTTP call: load it via the shared Loader (§8.1), validate its structure
(§6.4–§6.6), and extract the configured gateway name — matching
[README.md "SDK Configuration"](README.md#sdk-configuration)'s
`{"gateway": {"name": "<gateway name>"}}` shape.

4.3.5. Once a `gateway_name` is known (directly supplied, or extracted
per 4.3.4), THE SYSTEM SHALL resolve it via the Gateway Resolver (§5):
call `list()`, find every `ISMGateway` whose `name` matches exactly
(case-sensitive), and select that gateway's sole endpoint (§1.2).

4.3.6. IF gateway-name resolution (4.3.5) matches zero gateways THEN THE
SYSTEM SHALL raise `GatewayNotFoundError` (§6.2), naming the requested
gateway and, if a close match exists among the available names,
suggesting it — matching
[README.md "Validation"](README.md#validation)'s example message ("ISM
Gateway 'Corporate Gateway' was not found.") exactly when no suggestion
is available.

4.3.7. IF gateway-name resolution (4.3.5) matches more than one gateway
THEN THE SYSTEM SHALL raise `GatewayNameNotUniqueError` (§6.3) — README
"Validation" lists "Duplicate gateway names" as a distinct case from "not
found."

4.3.8. IF the resolved gateway has zero endpoints THEN THE SYSTEM SHALL
raise `IsmGatewayValidationError` (rule `gateway_has_no_endpoint`, §1.2).

4.3.9. IF the resolved gateway has more than one endpoint THEN THE SYSTEM
SHALL raise `IsmGatewayValidationError` (rule `gateway_endpoint_ambiguous`,
§1.2).

4.3.10. WHEN resolution succeeds (exactly one matching gateway, exactly
one endpoint on it) THEN THE SYSTEM SHALL call `PUT
/ism_gateways/targets/{target_id}` with body `{"gatewayUuid": <gateway.id>,
"endpointUuid": <endpoint.token>}` (§1.3).

4.3.11. WHEN `PUT .../targets/{target_id}` responds 200 THEN THE SYSTEM
SHALL return the `ISMGateway` resolved in 4.3.5 — the same object already
used to build the request — rather than issuing a second `list()` call to
rebuild it from the response, since `TargetIsmGateway`'s response carries
no name/status/hostname data to rebuild one from (§0.2).

4.3.12. WHEN `PUT .../targets/{target_id}` responds with any error status
THEN THE SYSTEM SHALL let the corresponding HTTP Client exception
propagate unchanged (404 → `VeracodeNotFoundError` for an unknown
`target_id`, per §0.3).

### 4.4 Remove a gateway assignment

**User story:** As an SDK consumer, I want to clear a target's gateway
assignment, so the target no longer requires internal scanning
infrastructure.

4.4.1. WHEN `client.ism_gateways.remove(target_id)` is called THEN THE
SYSTEM SHALL call `PUT /ism_gateways/targets/{target_id}` with an empty
body (`{}`), per §1.4.

4.4.2. IF `target_id` is blank THEN THE SYSTEM SHALL raise
`IsmGatewayValidationError` (rule `target_id_required`) and SHALL NOT
make an HTTP call.

4.4.3. WHEN `PUT .../targets/{target_id}` responds 200 THEN THE SYSTEM
SHALL return `None`.

4.4.4. WHEN `PUT .../targets/{target_id}` responds with any error status
THEN THE SYSTEM SHALL let the corresponding HTTP Client exception
propagate unchanged.

## 5. The Gateway Resolver

**User story:** As an SDK maintainer, I want name-to-identifier
resolution implemented once, as small, independently testable functions,
so `update()`'s only job is orchestrating already-tested pieces.

5.1. THE SYSTEM SHALL implement gateway-name resolution and
endpoint-selection as plain functions operating on already-fetched
`list[ISMGateway]` data (no `HttpClient` dependency of their own) —
matching the "plain functions, not classes" precedent set by
[specs/scanners-profiles design §2](../scanners-profiles/design.md#2-architecture).

5.2. Name resolution (§4.3.5–§4.3.7) and endpoint selection
(§4.3.8–§4.3.9) SHALL be implemented as two separate functions, each
raising its own specific exception(s) — not folded into one function that
raises a single generic error for every failure mode, since README
documents each failure mode with its own distinct meaning and (for "not
found") its own message format.

5.3. THE SYSTEM SHALL reuse `utils/sdk_config.suggest_closest` (§8.2) for
the "did you mean" hint in `GatewayNotFoundError` (§4.3.6), matching it
against the **live** list of gateway names returned by `list()` at
resolution time — not a fixed/closed enum, since gateway names are
account-specific business data with no fixed universe, unlike Scanner
Profiles' 35-member `ScannerType` set.

## 6. Client-side validation and error handling

**User story:** As an SDK consumer, I want a clear distinction between
"my input was invalid before any request was sent," "the gateway I named
doesn't resolve unambiguously," and "Veracode rejected my request," so I
can handle each case appropriately.

6.1. THE SYSTEM SHALL define `IsmGatewayValidationError(VeracodeSDKError)`
— not a subclass of `VeracodeApiError` — with a `rule` attribute,
following the `<Resource>ValidationError` convention established by
`TargetValidationError`/`ScannerValidationError`/etc. Rules: §4.2.2,
§4.2.5, §4.3.2, §4.3.3, §4.3.8, §4.3.9, §4.4.2, and the config-structure
rules in §6.4–§6.6.

6.2. THE SYSTEM SHALL define `GatewayNotFoundError(VeracodeSDKError)` —
not a subclass of `VeracodeApiError` or `VeracodeNotFoundError` — raised
by the Gateway Resolver (§4.3.6) when zero gateways match the requested
name. Per §1.5, this exact class name is kept as README fixes it, not
prefixed `IsmGateway`.

6.3. THE SYSTEM SHALL define `GatewayNameNotUniqueError(VeracodeSDKError)`
— same subclassing rule as §6.2 — raised by the Gateway Resolver
(§4.3.7) when more than one gateway matches the requested name, carrying
the requested `name` and the matched gateways' `id` values.

6.4. `config_file`, once loaded, must deserialize to a JSON **object**
(Python `dict`) → `IsmGatewayValidationError(rule="config_must_be_object")`
— README "Invalid configuration structure".

6.5. The loaded configuration must contain a `"gateway"` key whose value
is itself a JSON object → `IsmGatewayValidationError(rule="gateway_key_required")`
— README "Invalid configuration structure".

6.6. `config["gateway"]` must contain a non-blank `"name"` string →
`IsmGatewayValidationError(rule="gateway_name_required")` — README
"Missing gateway name".

6.7. When `config_file` is a filesystem path, the file must exist and
contain valid JSON → `ConfigFileNotFoundError` / `ConfigFileInvalidError`
(reused from
[specs/scanners-profiles design §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared),
not redefined, per §8.1).

6.8. THE SYSTEM SHALL NOT define any other new exception type. Every
failure that occurs after an HTTP request is sent (401, 403, 404, 500,
connection errors, timeouts) SHALL surface as whichever exception the
HTTP Client already defines for that condition, unmodified and
unwrapped.

6.9. THE SYSTEM SHALL NOT attempt to replicate `ISM_GATEWAY_MAPPING_ERROR`
or `TARGET_ISM_CONFIGURATION_REQUIRED` (§0.2) as client-side validation —
these are Veracode business rules (e.g. a target's scan type may be
incompatible with ISM gateway assignment) this feature does not try to
predict; if returned, they propagate as whichever status-mapped exception
the HTTP Client already raises.

6.10. THE SYSTEM SHALL NOT catch and swallow any exception raised by the
HTTP Client; `IsmGatewaysService` only ever lets it propagate.

## 7. Typed models and enumerations

**User story:** As an SDK consumer, I want ISM-Gateway-related models as
real Python types, so a malformed configuration or an unresolved gateway
is caught before it reaches Veracode's API.

7.1. THE SYSTEM SHALL define `ISMEndpoint` as a frozen dataclass with
fields `token: str`, `name: str | None = None`, `status: str | None =
None`, with a `from_api()` classmethod.

7.2. THE SYSTEM SHALL define `ISMGateway` as a frozen dataclass with
fields `id: str`, `name: str`, `status: str | None = None`, `hostname:
str | None = None`, `endpoints: list[ISMEndpoint] = field(default_factory=list)`,
with a `from_api()` classmethod mapping the OpenAPI's `refId` to `id`
(§0.2). `hostname`/`endpoints` default so that
[README.md "Returned Model"](README.md#returned-model)'s exact
`ISMGateway(id="gateway-id", name="Corporate Gateway", status="ONLINE")`
constructor call remains valid unmodified.

7.3. Per §1.6, THE SYSTEM SHALL name these two classes `ISMGateway` and
`ISMEndpoint` exactly, not `IsmGateway`/`IsmEndpoint`.

7.4. THE SYSTEM SHALL NOT define a public model for `TargetIsmGateway` —
it is a private request/response shape (a plain `dict[str, Any]`)
internal to `IsmGatewaysService.update`/`remove`, never returned to or
constructed by a caller (§4.3.11 always returns an `ISMGateway`, never
the raw `TargetIsmGateway` body).

7.5. THE SYSTEM SHALL NOT define a model for `Problem`/`ProblemError` —
the same generic REST transport shape already excluded by every prior
Phase 1/2 feature (e.g.
[specs/target-management requirements §6.9](../target-management/requirements.md#6-typed-models-and-enumerations)).

7.6. Both models SHALL comply with the model rules in
[AGENTS.md §3](../../AGENTS.md#3-architecture) (never perform HTTP
requests, contain business logic, or depend on the HTTP Client).

## 8. Configuration pipeline reuse

**User story:** As an SDK maintainer, I want ISM Gateway configuration
loading built on the exact same infrastructure Scanner Profiles/Scanner
Variables already established, so there is only ever one JSON-loading
implementation in this codebase.

8.1. THE SYSTEM SHALL reuse `utils/sdk_config.load_json_config` (path-or-
dict loading) rather than re-implementing it. If Scanner Profiles has not
yet been implemented when this feature is built, `utils/sdk_config.py`
(and `ConfigFileNotFoundError`/`ConfigFileInvalidError` in
`exceptions.py`) SHALL be created first, exactly as
[specs/scanners-profiles design §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared)
defines them — matching the same ordering caveat already documented by
[specs/scanner-variables requirements §9.5](../scanner-variables/requirements.md#9-public-interface-and-reuse).

8.2. THE SYSTEM SHALL reuse `utils/sdk_config.suggest_closest` (§5.3)
rather than re-implementing "did you mean" matching.

8.3. THE SYSTEM SHALL NOT modify `utils/sdk_config.py`,
`services/scanners.py`, `services/scanner_variables.py`,
`services/targets.py`, `services/api_specifications.py`, or
`services/analysis_profiles.py` — every reuse in this feature is an
import, never an edit.

## 9. Logging

**User story:** As an SDK maintainer, I want ISM Gateways to log
meaningful business events, without ever leaking `IsmEndpoint.token`.

9.1. WHEN gateways are successfully listed THEN THE SYSTEM SHALL emit an
INFO-level log stating how many gateways were returned.

9.2. WHEN `get()` returns an `ISMGateway` THEN THE SYSTEM SHALL emit an
INFO-level log naming the `target_id` and the resolved gateway's `name`.
WHEN `get()` returns `None` THEN THE SYSTEM SHALL emit an INFO-level log
stating that no gateway is assigned to `target_id`.

9.3. WHEN a gateway is successfully assigned (`update()`) THEN THE SYSTEM
SHALL emit an INFO-level log naming `target_id` and the assigned
gateway's `name`.

9.4. WHEN a gateway assignment is successfully removed THEN THE SYSTEM
SHALL emit an INFO-level log naming `target_id`.

9.5. **THE SYSTEM SHALL NEVER log `IsmEndpoint.token`, under any
circumstance, at any log level** — per §1.3, its name alone suggests
credential-like sensitivity, and this feature treats it with the same
strictness
[specs/scanner-variables requirements §8.3](../scanner-variables/requirements.md#8-logging)
applies to `ScannerVariable.value`.

9.6. THE SYSTEM SHALL NOT re-implement HTTP request/response logging;
that responsibility belongs entirely to the HTTP Client.

## 10. Public interface and reuse

**User story:** As an SDK consumer, I want `client.ism_gateways` to be
the resource-oriented entry point AGENTS.md promises, reusing the same
`HttpClient` instance already constructed for sibling Target-scoped
Phase 1/2 features.

10.1. THE SYSTEM SHALL expose an `IsmGatewaysService` class whose public
methods are exactly `list`, `get`, `update`, and `remove`, matching
README's Features list (parameter naming superseded per §1.1).

10.2. THE SYSTEM SHALL wire `IsmGatewaysService` onto `VeracodeClient` as
`client.ism_gateways`, reusing the same `HttpClient` instance already
constructed for `TargetsService`/`ApiSpecificationsService` (both
configured with `TARGET_CONFIGURATION_SERVICE_BASE_URL`) rather than
constructing a new one. THE SYSTEM SHALL NOT introduce a new Veracode API
base URL or a new `HttpClient` instance for this feature.

10.3. Every public class and method introduced by this feature SHALL
comply with the code conventions in
[AGENTS.md §7](../../AGENTS.md#7-code-conventions) (complete type hints,
Google-style docstrings).

10.4. `IsmGatewaysService` SHALL comply with the Stateless principle in
[AGENTS.md §5](../../AGENTS.md#5-design-principles): it holds only its
`HttpClient` instance; no gateway data is cached or retained between
calls (every `update()`/`get()` call re-fetches `list()`).

## 11. Testability

**User story:** As a maintainer, I want to verify resolution, structural
validation, and request shaping without a real Veracode account.

11.1. THE SYSTEM SHALL allow every `IsmGatewaysService` method to be
tested by constructing it with a fake/stub `HttpClient` returning
prepared `HttpResponse` values, with no real network access, environment
variables, or Veracode credentials required — the same pattern already
used by `tests/services/test_targets.py`.

11.2. THE SYSTEM SHALL allow the Gateway Resolver's name-resolution and
endpoint-selection functions (§5) to be unit-tested directly against
plain `list[ISMGateway]` fixtures, with no `HttpClient` involved at all.

11.3. THE SYSTEM SHALL NOT require a new third-party mocking/HTTP-fixture
dependency beyond what
[specs/http-client requirements §12](../http-client/requirements.md)
already establishes.

---

## 12. Non-Functional Requirements

- **Reuse over duplication.** No new Veracode API base URL, no new
  `HttpClient` instance, no re-implementation of `utils/sdk_config.py`'s
  Loader/suggestion helper or its `ConfigFileNotFoundError`/
  `ConfigFileInvalidError` exceptions.
- **Stateless.** `IsmGatewaysService` holds only an injected `HttpClient`;
  every call is independent (§10.4).
- **Platform-agnostic.** No dependency on Azure DevOps, a CLI, or any
  other specific consumer.
- **Typed.** Every public method has complete type hints; every response
  is a frozen dataclass, never a raw `dict`/`list`.
- **Testable offline.** Every test in this feature runs without network
  access or real credentials (§11).
- **Sensitive data never logged.** No log record produced by this
  feature ever contains `IsmEndpoint.token` (§9.5).
- **Assumptions flagged, not hidden.** §1.3's `token`-as-identifier
  reading and §1.4's empty-body-`PUT`-as-remove reading are explicitly
  documented as unconfirmed and gated on live-account validation (§13.5),
  never presented as settled fact.
- **No behavior change to Target Management, API Specification
  Management, Analysis Profiles, Scanner Profiles, or Scanner
  Variables.** This feature only adds a new service/model pair and three
  new exception classes; it does not modify any existing service, model,
  or `utils/sdk_config.py`.

---

## 13. Acceptance Criteria

Scenario-based checklist a reviewer can run through to confirm this
feature meets requirements.

1. **Given** no arguments, **when** `client.ism_gateways.list()` is
   called, **then** exactly one `GET /ism_gateways` request is made and
   the result is a plain `list[ISMGateway]` (§4.1.1–§4.1.3).
2. **Given** a target with no gateway assigned, **when** `get(target_id)`
   is called, **then** it returns `None` without raising (§4.2.4).
3. **Given** a target with a gateway assigned, **when** `get(target_id)`
   is called, **then** exactly two requests are made (`GET
   .../targets/{id}` then `GET /ism_gateways`) and the result is the
   matching `ISMGateway` (§4.2.3).
4. **Given** a blank `target_id`, **when** `get()`, `update()`, or
   `remove()` is called, **then** `IsmGatewayValidationError` is raised
   and no HTTP request is made (§4.2.2, §4.3.3, §4.4.2).
5. **Given** `gateway_name="Corporate Gateway"` matching exactly one
   available gateway with exactly one endpoint, **when** `update(...)` is
   called, **then** the request is `PUT /ism_gateways/targets/{id}` with
   body `{"gatewayUuid": <refId>, "endpointUuid": <token>}`, and the
   returned `ISMGateway` matches the resolved gateway (§4.3.5, §4.3.10,
   §4.3.11).
6. **Given** the exact SDK Configuration from
   [README "SDK Configuration"](README.md#sdk-configuration), **when**
   `update(target_id, config_file="ism-gateway.json")` is called,
   **then** the extracted gateway name and resulting request match
   scenario 5 exactly (§4.3.4).
7. **Given** both `gateway_name` and `config_file` supplied (or neither),
   **when** `update(...)` is called, **then**
   `IsmGatewayValidationError(rule="gateway_name_or_config_file_required")`
   is raised before any HTTP request (§4.3.2).
8. **Given** a `gateway_name` matching no available gateway, **when**
   `update(...)` is called, **then** `GatewayNotFoundError` is raised with
   the message `ISM Gateway '<name>' was not found.` before any HTTP
   request, reproducing README's "Validation" example (§4.3.6).
9. **Given** a `gateway_name` matching two available gateways, **when**
   `update(...)` is called, **then** `GatewayNameNotUniqueError` is
   raised before any HTTP request (§4.3.7).
10. **Given** a resolved gateway with zero or with more than one
    endpoint, **when** `update(...)` is called, **then**
    `IsmGatewayValidationError` is raised with the matching `rule`, before
    any HTTP request (§4.3.8–§4.3.9).
11. **Given** any `target_id`, **when** `remove(target_id)` is called,
    **then** the request is `PUT /ism_gateways/targets/{id}` with body
    `{}`, and `remove()` returns `None` on 200 (§4.4.1, §4.4.3).
12. **Given** a 404 response from the HTTP Client on `PUT`, **when**
    `update(...)` or `remove(...)` is called, **then**
    `VeracodeNotFoundError` propagates unmodified (§4.3.12, §4.4.4).
13. **Given** `VeracodeClient()`, **when** it is constructed, **then**
    `client.ism_gateways` is an `IsmGatewaysService` sharing the same
    `HttpClient` instance as `client.targets` (§10.2).
14. **Given** any successful call in a test asserting on `caplog`,
    **when** the captured log records are inspected, **then** none
    contains any `IsmEndpoint.token` value (§9.5).

---

## 14. Out of Scope

14.1. THE SYSTEM SHALL NOT implement any way for a caller to select a
specific endpoint on a multi-endpoint gateway (§1.2, §4.3.9) — deferred
until a concrete need is identified (§13.2 in design.md).

14.2. THE SYSTEM SHALL NOT implement `analysis_profile_id`-based
resolution of `target_id` inside this feature (§1.1) — a caller performs
that lookup themselves via `client.analysis_profiles.get(...)`.

14.3. THE SYSTEM SHALL NOT implement Target Management, Analysis
Profiles, Scanner Profiles, Scanner Variables, or Authentication
Configuration — each is (or will be) its own feature with its own spec.

14.4. THE SYSTEM SHALL NOT replicate `ISM_GATEWAY_MAPPING_ERROR` or
`TARGET_ISM_CONFIGURATION_REQUIRED` server-side business rules
client-side (§6.9).

14.5. THE SYSTEM SHALL NOT implement caching, retry logic, or
pagination-aggregation beyond what the HTTP Client already provides —
every `list()` call is a fresh `GET /ism_gateways` request.

14.6. THE SYSTEM SHALL NOT implement a CLI or any execution-platform
integration (AGENTS.md §1 non-goals).

14.7. Per §13.5 (design.md), THE SYSTEM SHALL treat §1.3's
`token`-as-`endpointUuid` mapping and §1.4's empty-body-`PUT`-as-`remove`
behavior as **required manual validation against a live/sandbox Veracode
account before this feature ships** — this is not a deferred nice-to-have
like §14.1, but a blocking precondition on correctness, since both
readings are inferred from an underspecified schema rather than confirmed
by any documented example.
