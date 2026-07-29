# Requirements — Analysis Profiles

Source context: [README.md](README.md). Architecture and conventions:
[AGENTS.md](../../AGENTS.md). Phase 2 ("Configure Targets"), per
[AGENTS.md §10](../../AGENTS.md#10-roadmap). Reuses
[specs/target-management](../target-management/requirements.md) (the
`HttpClient` instance and `TARGET_CONFIGURATION_SERVICE_BASE_URL`
constant) and [specs/api-specification-management](../api-specification-management/requirements.md)
(`ApiSpecification`, `ScopeRule`, `ScopeType`, `ScopeRuleType` models) —
this feature adds no new API base URL and no new Veracode API domain.

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
Analysis Profiles. It is the factual basis Functional Requirements §1–§8
are derived from — nothing below introduces a REST behavior not captured
here.

### 0.1 In-scope REST endpoints

| Method | Path | operationId | Purpose |
|---|---|---|---|
| GET | `/analysis_profiles` | `getAnalysisProfiles` | List analysis profiles (paginated, filterable by `target_id` and `type`). |
| GET | `/analysis_profiles/{analysis_profile_id}` | `getAnalysisProfileById` | Get one analysis profile by ID. |
| PUT | `/analysis_profiles/{analysis_profile_id}` | `updateAnalysisProfile` | Update an analysis profile. |

### 0.2 Other `analysis_profiles`-tagged operations found in the OpenAPI (out of scope)

The OpenAPI document defines many more operations under `/analysis_profiles/*`
than the three above. Per README's Scope and this document's §9 (Out of
Scope), these are listed here for completeness but are **not** implemented
by this feature:

| Method | Path | operationId | Why out of scope |
|---|---|---|---|
| PUT | `/analysis_profiles/{id}/parent` | `updateAnalysisProfileParent` | Profile hierarchy re-parenting — no consumer need identified; not in README Scope. |
| GET | `/analysis_profiles/assignable_parent_profiles` | `getAssignableParentProfiles` | Supports re-parenting only; deferred with it. |
| GET/PUT/DELETE | `/analysis_profiles/{id}/schedule` | `get/update/deleteAnalysisProfileSchedule` | Schedules — explicitly out of scope for the whole SDK until a later phase, per [AGENTS.md §2](../../AGENTS.md#2-scope). |
| GET | `/analysis_profiles/{id}/authentications` | `getAnalysisProfileAuthentications` | Authentication Configuration — a distinct Phase 2 feature with its own spec. |
| PUT | `/analysis_profiles/{id}/system_authentication` | `updateSystemAuthentication` | Same as above. |
| PUT | `/analysis_profiles/{id}/certificate_authentication` | `updateCertificateAuthentication` | Same as above. |
| PUT | `/analysis_profiles/{id}/script_authentication` | `updateScriptAuthentication` | Same as above. |
| PUT | `/analysis_profiles/{id}/application_authentication` | `updateApplicationAuthentication` | Same as above. |
| PUT | `/analysis_profiles/{id}/parameter_authentications` | `updateParameterAuthentications` | Same as above. |
| PUT | `/analysis_profiles/{id}/srm_authentication` | `updateSrmAuthentication` | Same as above. |
| PUT | `/analysis_profiles/{id}/oauth2_authentication` | `updateOauth2Authentication` | Same as above. |
| GET/PUT | `/analysis_profiles/{id}/scanners` | `get/updateAnalysisProfileScanners` | Scanner Configuration — a distinct Phase 2 feature (see [specs/scanners-profiles](../scanners-profiles/README.md)). |
| GET/PUT | `/analysis_profiles/{id}/scanner_variables` | `get/updateScannerVariables` | Scanner Variables — a distinct Phase 2 feature. |
| GET/PUT | `/analysis_profiles/{id}/crawl_configuration` | `get/updateCrawlConfiguration` | Crawl Configuration — not listed in README Scope; deferred until a feature explicitly covers it. |

None of these are called, referenced, or required by this feature. Every
one of them addresses an existing analysis profile by
`analysis_profile_id` — exactly the identifier this feature's `list()`/
`get()` already return — so a future feature implementing any of them
composes on top of this one without changes here (see design.md §9,
"Future Extensibility").

### 0.3 Query parameters — `GET /analysis_profiles`

| Name | Required | Type | Constraints | Default |
|---|---|---|---|---|
| `page` | No | integer | min 0 | 0 |
| `limit` | No | integer | min 10, max 200 | 10 |
| `target_id` | No | string | — | — |
| `type` | No | array of `AnalysisProfileType` | `TARGET`, `ORG`, `SYSTEM` | — |

Unlike `GET /targets` (requirements.md §0.3 of
[specs/target-management](../target-management/requirements.md)), this
endpoint has no `sort_by`/`sort_order`/`name`/`search_term` parameters —
the OpenAPI defines none, so this feature does not invent any.

### 0.4 Query parameters — `PUT /analysis_profiles/{analysis_profile_id}`

| Name | Required | Type | Constraints |
|---|---|---|---|
| `method` | No | enum | Only allowed value: `PATCH`. "If set to PATCH, updates the content to values in the request, but null values and absent attributes are ignored." |

**This parameter is load-bearing for this feature's design.** Without it,
`PUT` is a full replace: any field the caller omits from the request body
is treated as absent/null by the server, not "leave unchanged." See §3.2
and design.md §3.3 ("Why `update()` always sends `method=PATCH`").

### 0.5 Schemas

**`AnalysisProfile`** (response body for get/update) — required:
`allowed_urls`, `analysis_profile_id`, `crawler_enabled`, `crawler_mode`,
`denied_urls`, `grouped_urls`, `max_crawl_duration`, `max_duration`,
`mode`, `name`, `parent_analysis_profile_id`, `rate_limit`, `seed_urls`.
Optional: `target_id`, `max_browsers`, `api_spec`, `similarity_threshold`,
`directory_restrictions`, `enable_all_target_protocols`.

Thirteen of these fields (`allowed_urls`, `denied_urls`, `seed_urls`,
`grouped_urls`, `crawler_enabled`, `crawler_mode`, `rate_limit`,
`max_duration`, `max_crawl_duration`, `max_browsers`,
`similarity_threshold`, `directory_restrictions`,
`enable_all_target_protocols`) all share one wrapper shape:

```json
{ "effective_value": <T>, "is_inherited": <boolean> }
```

`is_inherited` tells the caller whether `effective_value` comes from this
profile directly or is inherited from `parent_analysis_profile_id` — this
is intrinsic to how Analysis Profiles work (target-level profiles inherit
from org-level profiles, per the OpenAPI's own description of
`getAnalysisProfileById`: "Each target level analysis profile inherits
values from a parent analysis profile") and must not be discarded.

**`AnalysisProfileListItem`** (list item, embedded in `PagedAnalysisProfiles`)
— required: `analysis_profile_id`, `name`. Optional: `target_id`. A much
smaller shape than `AnalysisProfile` — it carries no configuration values,
only enough to identify a profile and (optionally) the target it belongs
to.

**`AnalysisProfileUpdateRequest`** (`PUT` body) — no required fields; every
property is optional. Properties: `allowed_urls`, `denied_urls`,
`seed_urls`, `grouped_urls` (arrays of string, nullable), `crawler_mode`
(`CrawlerModeEnum`: `SMART`, `EXHAUSTIVE`), `rate_limit` (integer, 50–1,000,000,000),
`max_duration` (integer, 50–129,599), `max_crawl_duration` (integer,
1–129,599), `max_browsers` (integer, 1–12), `scope_rules` (array of
`ScopeRule`), `similarity_threshold` (number, 0.6–0.99),
`directory_restrictions` (`DirectoryRestrictionsEnum`: `DIR_AND_SUBDIR`,
`DIR_ONLY`, `NO_RESTRICTIONS`, nullable), `enable_all_target_protocols`
(boolean).

**`AnalysisProfileUpdateRequest` does not define `name` or `description`.**
See §3.1 for why this matters and how it is reconciled with README.

**`ScopeRule`** — identical in shape to the `ScopeRule` schema already
consumed by [specs/api-specification-management](../api-specification-management/requirements.md)
(`uuid`, `http_method`, `url`, `scope_type`, `scope_rule_type`,
`scope_rule_index`). This feature reuses that feature's `ScopeRule`,
`ScopeType`, `ScopeRuleType` models rather than redefining them — see
design.md §5.3.

**`ApiSpec`** — identical in shape to the schema already consumed by
`ApiSpecification` in
[specs/api-specification-management](../api-specification-management/requirements.md)
(`api_spec_s3_id`, `api_spec_name`, `api_spec_url`, `api_spec_type`,
`target_id`, `analysis_run_id`, `uploaded_at`, `updated_at`, `uploaded_by`,
`updated_by`, `scope_rules`). This feature reuses `ApiSpecification`
rather than defining a second, parallel model for the same shape — see
design.md §5.3.

**`PagedAnalysisProfiles`** (`GET /analysis_profiles` 200 body) — required
`page` (`PageMeta`: `number`, `size`, `total_pages`, `total_elements`, all
required integers); `_embedded.analysis_profiles: AnalysisProfileListItem[]`;
`_links: Link[]` (HATEOAS navigation, not exposed — same decision as
[specs/target-management requirements §1.5](../target-management/requirements.md#1-list-targets),
applied here for consistency).

**`Problem`** / **`ProblemError`** — the same RFC 7807 problem-details
shapes already documented in
[specs/target-management requirements §0.4](../target-management/requirements.md#04-schemas).
`ProblemError.code` includes, among values shared with every other
resource, `ANALYSIS_PROFILE_NOT_FOUND`.

### 0.6 Enumerations

| OpenAPI schema | Values | Used by |
|---|---|---|
| `AnalysisProfileType` | `TARGET`, `ORG`, `SYSTEM` | `GET /analysis_profiles` `type` filter |
| `ModeEnum` | `STANDARD`, `ENTERPRISE` | `AnalysisProfile.mode` |
| `CrawlerModeEnum` | `SMART`, `EXHAUSTIVE` | `AnalysisProfile.crawler_mode.effective_value`, `AnalysisProfileUpdateRequest.crawler_mode` |
| `DirectoryRestrictionsEnum` | `DIR_AND_SUBDIR`, `DIR_ONLY`, `NO_RESTRICTIONS` (nullable) | `AnalysisProfile.directory_restrictions.effective_value`, `AnalysisProfileUpdateRequest.directory_restrictions` |

### 0.7 HTTP status codes and error responses

| Endpoint | Status | Meaning | Body schema |
|---|---|---|---|
| GET `/analysis_profiles` | 200 | Success | `PagedAnalysisProfiles` |
| GET `/analysis_profiles` | 401 | Unauthorized | none defined |
| GET `/analysis_profiles` | 500 | Server error | `Problem` |
| GET `/analysis_profiles/{id}` | 200 | Success | `AnalysisProfile` |
| GET `/analysis_profiles/{id}` | 401 | Unauthorized | none defined |
| GET `/analysis_profiles/{id}` | 403 | Forbidden | none defined |
| GET `/analysis_profiles/{id}` | 404 | Unknown profile ID | none defined |
| GET `/analysis_profiles/{id}` | 500 | Server error | `Problem` |
| PUT `/analysis_profiles/{id}` | 200 | Success | `AnalysisProfile` |
| PUT `/analysis_profiles/{id}` | 400 | Invalid request | `Problem` |
| PUT `/analysis_profiles/{id}` | 401 | Unauthorized | none defined |
| PUT `/analysis_profiles/{id}` | 403 | Forbidden | none defined |
| PUT `/analysis_profiles/{id}` | 404 | Unknown profile ID | none defined |
| PUT `/analysis_profiles/{id}` | 501 | Server error | `Problem` |

**Observed inconsistency, preserved as-is:** `updateAnalysisProfile`'s
server-error response is labeled `501`, matching the same documented
inconsistency already noted and left unnormalized in
[specs/target-management requirements §0.7](../target-management/requirements.md#07-http-status-codes-and-error-responses)
for `createTarget`/`updateTarget`. The HTTP Client already maps every
unmapped 5xx status uniformly to `VeracodeApiError`, so no
Analysis-Profile-specific handling is needed either way.

---

## 1. Overview

Analysis Profiles are the root configuration resource for a DAST scan:
every other Phase 2 configuration resource (Scanner Profiles, Scanner
Variables, Authentication) is addressed by `analysis_profile_id`, and
target-level profiles inherit unset values from an org-level parent
profile. This feature gives the SDK read and update access to that root
resource — `list`, `get`, `update` — so a consumer can resolve the
`analysis_profile_id` a Target implies and adjust its crawl/scan
configuration before those dependent resources are configured.

This feature does not create or delete Analysis Profiles (the REST API
does not expose either operation — profiles are created implicitly when a
Target is created) and does not implement any of the sub-resources listed
in §0.2.

## 2. Goals

- Provide typed, resource-oriented access to Analysis Profiles:
  `client.analysis_profiles.list()`, `.get(id)`, `.update(id, ...)`,
  matching [README.md](README.md).
- Preserve the inheritance semantics (`effective_value`/`is_inherited`)
  the real API exposes, rather than flattening them away.
- Make `update()` safe to call with only the fields a consumer actually
  intends to change, without silently nulling out the rest of the
  profile's configuration.
- Reuse everything Phase 1 and the API Specification Management feature
  already built (`HttpClient`, the DAST Target Configuration Service base
  URL, `ApiSpecification`, `ScopeRule`) instead of duplicating any of it.
- Establish `analysis_profile_id` as the addressing scheme every future
  Phase 2 sub-resource (Scanner Profiles, Scanner Variables,
  Authentication) will build on, without this feature depending on any of
  them.

## 3. Functional Requirements

### 3.1 README/OpenAPI reconciliation (read before §4–§8)

README's "Update Analysis Profile" example calls
`update(analysis_profile_id=..., name="Production Profile",
description="Production DAST profile")`. Neither `name` nor `description`
exists on `AnalysisProfileUpdateRequest` (§0.5): `name` has no update
endpoint at all in the OpenAPI (it is set once, implicitly, when the
underlying Target is created), and no `AnalysisProfile`-scoped
`description` field exists anywhere in the OpenAPI document.

Per this repository's established practice of treating the OpenAPI
contract as the authoritative behavior — not the README's illustrative
field names — the same reconciliation
[specs/target-management requirements §4.2](../target-management/requirements.md#4-update-target)
applied to `TargetUpdate` applies here: `AnalysisProfileUpdate` (§4.3)
exposes exactly the fields `AnalysisProfileUpdateRequest` accepts, and
**not** `name` or `description`. README's calling *convention* — a
keyword-argument partial update returning the updated typed model — is
preserved; only the two placeholder field names in its example are
superseded by the real, implementation-ready field set. This is flagged
here prominently, rather than silently, because it is a materially
different method signature from what README's example literally shows.

### 3.2 List Analysis Profiles

**User story:** As an SDK consumer, I want to list Analysis Profiles with
the same filtering and pagination the REST API supports, so I can find the
profile for a given Target without a raw HTTP call.

3.2.1. WHEN `client.analysis_profiles.list()` is called with no arguments
THEN THE SYSTEM SHALL call `GET /analysis_profiles` with no query
parameters other than the REST API's own defaults (`page=0`, `limit=10`),
per §0.3.

3.2.2. WHEN `client.analysis_profiles.list()` is called with any of
`page`, `limit`, `target_id`, `types` THEN THE SYSTEM SHALL forward each
supplied value as the corresponding `GET /analysis_profiles` query
parameter (`types` forwarded as the repeated `type` parameter), per §0.3.

3.2.3. THE SYSTEM SHALL type `types` as `list[AnalysisProfileType]` (§4.1),
rather than accepting arbitrary strings.

3.2.4. WHEN `GET /analysis_profiles` responds 200 THEN THE SYSTEM SHALL
return a typed `AnalysisProfilePage` containing the list of
`AnalysisProfileSummary` models (from `_embedded.analysis_profiles`) and
page metadata (`number`, `size`, `total_pages`, `total_elements`, from
`page`), per §0.5.

3.2.5. THE SYSTEM SHALL NOT expose the `_links` HATEOAS array from
`PagedAnalysisProfiles` on `AnalysisProfilePage`, for the same reason as
[specs/target-management requirements §1.5](../target-management/requirements.md#1-list-targets)
(every navigation `_links` could express is already reachable by calling
`list()` again with an incremented `page`).

3.2.6. THE SYSTEM SHALL NOT aggregate multiple pages into one call. One
`list(...)` call always corresponds to exactly one `GET /analysis_profiles`
request.

3.2.7. `AnalysisProfilePage` SHALL be directly iterable over its
`AnalysisProfileSummary` items (`for profile in profiles:`), matching
README's documented usage, in addition to exposing `items` and page
metadata explicitly. This is an architectural decision — see design.md §9
("Why `AnalysisProfilePage` is iterable").

### 3.3 Get Analysis Profile by ID

**User story:** As an SDK consumer, I want to fetch one Analysis Profile
by its ID, so I can inspect its current crawl/scan configuration before
configuring dependent resources.

3.3.1. WHEN `client.analysis_profiles.get(analysis_profile_id)` is called
THEN THE SYSTEM SHALL call `GET /analysis_profiles/{analysis_profile_id}`
with the given ID.

3.3.2. IF `analysis_profile_id` is blank (empty or whitespace-only) THEN
THE SYSTEM SHALL raise `AnalysisProfileValidationError` (§6.1) and SHALL
NOT make an HTTP call — the same blank-ID guard already established by
`TeamService.get`/`ApiSpecificationsService.get` for their respective ID
parameters.

3.3.3. WHEN `GET /analysis_profiles/{analysis_profile_id}` responds 200
THEN THE SYSTEM SHALL return a typed `AnalysisProfile` model built from
the response body, preserving every field's `effective_value`/
`is_inherited` pair (§0.5, §4.2).

3.3.4. WHEN `GET /analysis_profiles/{analysis_profile_id}` responds 404
THEN THE SYSTEM SHALL let `VeracodeNotFoundError` (raised by the HTTP
Client) propagate unchanged — this feature adds no Analysis-Profile-specific
"not found" exception.

### 3.4 Update Analysis Profile

**User story:** As an SDK consumer, I want to change only the crawl/scan
configuration fields I actually intend to change, so that fields I don't
mention keep their current value — including whatever they currently
inherit from a parent profile.

3.4.1. WHEN `client.analysis_profiles.update(analysis_profile_id, ...)` is
called THEN THE SYSTEM SHALL build an `AnalysisProfileUpdateRequest`-shaped
JSON body from the caller-supplied `AnalysisProfileUpdate` model containing
only the fields the caller explicitly set, and call `PUT
/analysis_profiles/{analysis_profile_id}?method=PATCH`.

3.4.2. THE SYSTEM SHALL always include `method=PATCH` on every `update()`
call. THE SYSTEM SHALL NOT expose a way to call this endpoint as a plain
(full-replace) `PUT` — doing so would risk silently clearing every field
the caller didn't mention, per §0.4's documented full-replace-vs-partial
semantics. This is a safety-critical design decision — see design.md §3.3.

3.4.3. `AnalysisProfileUpdate` SHALL expose exactly the fields
`AnalysisProfileUpdateRequest` accepts — `allowed_urls`, `denied_urls`,
`seed_urls`, `grouped_urls`, `crawler_mode`, `rate_limit`, `max_duration`,
`max_crawl_duration`, `max_browsers`, `scope_rules`, `similarity_threshold`,
`directory_restrictions`, `enable_all_target_protocols` — all optional,
matching §0.5. Per §3.1, THE SYSTEM SHALL NOT expose `name` or
`description` on `AnalysisProfileUpdate`.

3.4.4. THE SYSTEM SHALL retain the distinction between a field the caller
never mentioned and a field the caller explicitly set to `None`, for the
four nullable array fields (`allowed_urls`, `denied_urls`, `seed_urls`,
`grouped_urls`) and `directory_restrictions` — mirroring the sentinel
approach in
[specs/target-management design §2.1](../target-management/design.md#21-srcveracode_dastmodelstargetpy)
("Why a sentinel instead of `Optional[X] = None`"). THE SYSTEM SHALL NOT
send a field the caller never touched.

3.4.5. IF `analysis_profile_id` is blank THEN THE SYSTEM SHALL raise
`AnalysisProfileValidationError` (§6.1) and SHALL NOT make an HTTP call.

3.4.6. THE SYSTEM SHALL NOT duplicate the numeric range constraints on
`rate_limit`, `max_duration`, `max_crawl_duration`, `max_browsers`, or
`similarity_threshold` (§0.5) as client-side validation. These are simple,
independent bounds documented on the typed model's docstrings, not
conditional cross-field rules a caller cannot discover from type hints
alone — the same distinction
[specs/target-management requirements §7.2](../target-management/requirements.md#7-client-side-validation)
draws between validation worth mirroring client-side and validation that
would just duplicate the server. Attempting a value outside these bounds
surfaces as `VeracodeValidationError` (422) from the HTTP Client,
unmodified.

3.4.7. WHEN `PUT /analysis_profiles/{analysis_profile_id}?method=PATCH`
responds 200 THEN THE SYSTEM SHALL return a typed `AnalysisProfile` model
built from the response body, per §0.5.

3.4.8. WHEN `PUT /analysis_profiles/{analysis_profile_id}?method=PATCH`
responds 404 THEN THE SYSTEM SHALL let `VeracodeNotFoundError` propagate
unchanged.

## 4. Typed models and enumerations

**User story:** As an SDK consumer, I want Analysis-Profile-related enums
and models as real Python types, so invalid values are caught by my editor
and by `mypy` instead of at runtime inside Veracode's API.

4.1. THE SYSTEM SHALL define `AnalysisProfileType(StrEnum)` with members
`TARGET`, `ORG`, `SYSTEM`.

4.2. THE SYSTEM SHALL define `AnalysisProfileMode(StrEnum)` with members
`STANDARD`, `ENTERPRISE` (the OpenAPI's `ModeEnum`, renamed for the same
resource-prefixing reason
[specs/target-management requirements §6.6](../target-management/requirements.md#6-typed-models-and-enumerations)
renamed `Status` to `TargetStatus`: `Mode` is too generic a name to own
unqualified).

4.3. THE SYSTEM SHALL define `CrawlerMode(StrEnum)` with members `SMART`,
`EXHAUSTIVE` (the OpenAPI's `CrawlerModeEnum`).

4.4. THE SYSTEM SHALL define `DirectoryRestrictions(StrEnum)` with members
`DIR_AND_SUBDIR`, `DIR_ONLY`, `NO_RESTRICTIONS` (the OpenAPI's
`DirectoryRestrictionsEnum`).

4.5. THE SYSTEM SHALL define a reusable `InheritedValue[T]` generic model
(`models/common.py`) with fields `effective_value: T` and
`is_inherited: bool`, matching the `{effective_value, is_inherited}` shape
repeated thirteen times across the `AnalysisProfile` schema (§0.5). THE
SYSTEM SHALL NOT define thirteen separate wrapper classes for the same
shape.

4.6. THE SYSTEM SHALL define `AnalysisProfile`, `AnalysisProfileSummary`,
`AnalysisProfileUpdate`, and `AnalysisProfilePage` as typed models (§0.5)
that comply with the model rules in
[AGENTS.md §3](../../AGENTS.md#3-architecture) (models never perform HTTP
requests, contain business logic, or depend on the HTTP Client).

4.7. THE SYSTEM SHALL reuse `ApiSpecification`, `ScopeRule`, `ScopeType`,
and `ScopeRuleType` from
[specs/api-specification-management](../api-specification-management/design.md)
for `AnalysisProfile.api_spec` and `AnalysisProfileUpdate.scope_rules`
respectively. THE SYSTEM SHALL NOT define a second, parallel model for
either shape.

4.8. THE SYSTEM SHALL NOT define a model for `Problem`, `ProblemError`, or
`Link` — these are generic REST transport/error shapes already handled by
the HTTP Client's exception attributes, not Analysis Profile resources
(same rule as
[specs/target-management requirements §6.9](../target-management/requirements.md#6-typed-models-and-enumerations)).

## 5. Client-side validation

**User story:** As an SDK consumer, I want an obviously invalid
`analysis_profile_id` rejected immediately, so I don't make a round trip
to Veracode for a mistake my code could catch locally.

5.1. THE SYSTEM SHALL raise `AnalysisProfileValidationError` (§6.1) when
`analysis_profile_id` is blank on `get()` or `update()`, before any HTTP
request is made — matching the blank-ID guard already established by
`TeamService`/`ApiSpecificationsService`.

5.2. THE SYSTEM SHALL NOT perform any other client-side validation. Per
§3.4.6, numeric range constraints are left to the server; there are no
conditional cross-field rules on `AnalysisProfileUpdateRequest` analogous
to Target's `is_sec_lead_only`/`teams` rule, so none are invented here.

## 6. Error handling

**User story:** As an SDK consumer, I want a clear distinction between "my
`analysis_profile_id` was obviously invalid before any request was sent"
and "Veracode rejected my request," so I can handle each case
appropriately.

6.1. THE SYSTEM SHALL define `AnalysisProfileValidationError(VeracodeSDKError)`
— not a subclass of `VeracodeApiError` — for the blank-ID check in §5,
following the naming/subclassing convention established in
[specs/target-management design §2.2](../target-management/design.md#22-srcveracode_dastexceptionspy-extended)
("`<Resource><Reason>Error`, subclassing `VeracodeSDKError` directly").

6.2. THE SYSTEM SHALL NOT define any other new exception type. Every
failure that occurs after an HTTP request is sent (401, 403, 404, 422,
other 4xx, 5xx, connection errors, timeouts) SHALL surface as whichever
exception the HTTP Client already defines for that condition, unmodified
and unwrapped. In particular, THE SYSTEM SHALL NOT define an
Analysis-Profile-specific "not found" exception — this feature has no
`get_by_name`-style convenience method that would need one (see §9).

6.3. THE SYSTEM SHALL NOT catch and swallow any exception raised by the
HTTP Client; `AnalysisProfilesService` only ever lets it propagate.

## 7. Logging

**User story:** As an SDK maintainer, I want Analysis Profiles to log
meaningful business events, without duplicating the HTTP Client's own
request/response logging.

7.1. WHEN an Analysis Profile is successfully updated THEN THE SYSTEM
SHALL emit an INFO-level log naming the operation and the
`analysis_profile_id`.

7.2. WHEN Analysis Profiles are successfully listed THEN THE SYSTEM SHALL
emit an INFO-level log stating how many profiles were returned and the
requested page.

7.3. THE SYSTEM SHALL NOT log `allowed_urls`, `denied_urls`, `seed_urls`,
`grouped_urls`, or any other business-data field beyond
`analysis_profile_id`/`name`/counts — per
[AGENTS.md §6.2](../../AGENTS.md#62-business-data), these are
consumer-supplied business data, and per README, "sensitive information
must never be logged."

7.4. THE SYSTEM SHALL NOT re-implement HTTP request/response logging;
that responsibility belongs entirely to the HTTP Client.

## 8. Public interface and reuse

**User story:** As an SDK consumer, I want `client.analysis_profiles` to
be the resource-oriented entry point AGENTS.md promises, reusing the same
HTTP Client instance already constructed for Target Management.

8.1. THE SYSTEM SHALL expose an `AnalysisProfilesService` class whose
public methods are exactly `list`, `get`, and `update`, matching README's
Features list. THE SYSTEM SHALL NOT add `create`, `delete`, or any
`get_by_name`-style convenience method — the REST API exposes no create/
delete operation for Analysis Profiles (§1), and no filter on
`GET /analysis_profiles` supports an exact-name lookup the way `GET
/targets`'s `name` filter does (§0.3).

8.2. THE SYSTEM SHALL wire `AnalysisProfilesService` onto `VeracodeClient`
as `client.analysis_profiles`, reusing the same `HttpClient` instance
already constructed for `TargetsService`/`ApiSpecificationsService` (both
configured with `TARGET_CONFIGURATION_SERVICE_BASE_URL`) rather than
constructing a new one. THE SYSTEM SHALL NOT introduce a new Veracode API
base URL or a new `HttpClient` instance for this feature.

8.3. Every public class and method introduced by this feature SHALL
comply with the code conventions in
[AGENTS.md §7](../../AGENTS.md#7-code-conventions) (complete type hints,
Google-style docstrings).

8.4. `AnalysisProfilesService` SHALL comply with the Stateless principle in
[AGENTS.md §5](../../AGENTS.md#5-design-principles): it holds only its
`HttpClient` instance; no profile data is cached or retained between
calls.

## 9. Testability

**User story:** As a maintainer, I want to verify request shaping,
response parsing, and the partial-update body construction without a real
Veracode account.

9.1. THE SYSTEM SHALL allow every `AnalysisProfilesService` method to be
tested by constructing it with a fake/stub `HttpClient` returning prepared
`HttpResponse` values, with no real network access, environment variables,
or Veracode credentials required — the same pattern already used by
`tests/services/test_targets.py` and `tests/services/test_teams.py`.

9.2. THE SYSTEM SHALL NOT require a new third-party mocking/HTTP-fixture
dependency beyond what
[specs/http-client requirements §12](../http-client/requirements.md)
already establishes.

---

## 10. Non-Functional Requirements

- **Reuse over duplication.** No new Veracode API base URL, no new
  `HttpClient` instance, no re-implementation of `ApiSpecification`/
  `ScopeRule`/`ScopeType`/`ScopeRuleType`, no re-implementation of the
  `_UNSET`-sentinel partial-update pattern already established by
  `TargetUpdate`.
- **Stateless.** `AnalysisProfilesService` holds only an injected
  `HttpClient`; every call is independent (§8.4, per
  [AGENTS.md §5](../../AGENTS.md#5-design-principles)).
- **Platform-agnostic.** No dependency on Azure DevOps, a CLI, or any
  other specific consumer (per
  [AGENTS.md §5](../../AGENTS.md#5-design-principles)).
- **Typed.** Every public method has complete type hints; every response
  is returned as a frozen dataclass, never a raw `dict`.
- **Testable offline.** Every test in this feature runs without network
  access or real credentials (§9).
- **No business data logged beyond identifiers/counts** (§7.3), matching
  [AGENTS.md §6.2](../../AGENTS.md#62-business-data).
- **No behavior change to Target Management or API Specification
  Management.** This feature only adds a new service/model pair and one
  new exception class; it does not modify `services/targets.py`,
  `services/api_specifications.py`, or their models.
- **Extensible.** Adding this feature must not require future Scanner
  Profiles/Scanner Variables/Authentication features to change anything
  here beyond consuming `AnalysisProfile`/`AnalysisProfileSummary`'s
  `analysis_profile_id` field (see design.md §9).

---

## 11. Acceptance Criteria

Scenario-based checklist a reviewer can run through to confirm this
feature meets requirements. Each scenario references the Functional
Requirement it verifies.

1. **Given** no arguments, **when** `client.analysis_profiles.list()` is
   called, **then** exactly one `GET /analysis_profiles` request is made
   with no query parameters beyond the REST API's own defaults, and the
   result is directly iterable over `AnalysisProfileSummary` items (§3.2.1,
   §3.2.7).
2. **Given** `target_id` and `types` arguments, **when** `list(...)` is
   called, **then** both are forwarded as query parameters and `types` is
   sent as repeated `type` values (§3.2.2, §3.2.3).
3. **Given** a valid `analysis_profile_id`, **when** `get(...)` is called,
   **then** the returned `AnalysisProfile` preserves every field's
   `effective_value` and `is_inherited` (§3.3.3).
4. **Given** a blank `analysis_profile_id`, **when** `get(...)` or
   `update(...)` is called, **then** `AnalysisProfileValidationError` is
   raised and no HTTP request is made (§3.3.2, §3.4.5).
5. **Given** an `AnalysisProfileUpdate` with only `rate_limit` set,
   **when** `update(...)` is called, **then** the request is
   `PUT /analysis_profiles/{id}?method=PATCH` with a body containing only
   `{"rate_limit": ...}` (§3.4.1, §3.4.2).
6. **Given** an `AnalysisProfileUpdate` with `allowed_urls=None` explicitly
   set, **when** `update(...)` is called, **then** the request body
   contains `"allowed_urls": null`, and any field never mentioned is
   absent from the body entirely (§3.4.4).
7. **Given** a 404 response from the HTTP Client, **when** `get(...)` or
   `update(...)` is called, **then** `VeracodeNotFoundError` propagates
   unmodified (§3.3.4, §3.4.8).
8. **Given** an `AnalysisProfile` response whose body includes `api_spec`,
   **when** `get(...)` is called, **then** the result's `.api_spec` is an
   `ApiSpecification` instance (§4.7), not a second, parallel model.
9. **Given** `VeracodeClient()`, **when** it is constructed, **then**
   `client.analysis_profiles` is an `AnalysisProfilesService` sharing the
   same `HttpClient` instance as `client.targets` (§8.2).

---

## 12. Out of Scope

12.1. THE SYSTEM SHALL NOT implement any of the endpoints listed in §0.2:
profile re-parenting (`parent`, `assignable_parent_profiles`), Schedules,
Authentication Configuration (all seven `*_authentication` PUT operations
plus `authentications` GET), Scanner Configuration (`scanners`), Scanner
Variables (`scanner_variables`), or Crawl Configuration
(`crawl_configuration`) — each is (or will be) its own feature with its
own spec.

12.2. THE SYSTEM SHALL NOT implement create or delete for Analysis
Profiles — the REST API exposes neither operation; profiles are created
implicitly alongside a Target.

12.3. THE SYSTEM SHALL NOT implement any `get_by_name`/`exists`/`ensure`-style
convenience method. Unlike Targets and Teams, Analysis Profiles have no
REST filter that narrows to an exact match on a caller-known identifier
other than `analysis_profile_id` itself (which the caller must already
have, typically from a Target lookup) — inventing a name-based convenience
here would not be backed by any REST capability.

12.4. THE SYSTEM SHALL NOT implement pagination-aggregation, caching, or
retry logic beyond what the HTTP Client already provides.

12.5. THE SYSTEM SHALL NOT modify `services/targets.py`,
`services/api_specifications.py`, `services/teams.py`, or any of their
models — every reuse in this feature is an import, never an edit.

12.6. THE SYSTEM SHALL NOT introduce a config-file-driven update workflow
(unlike [specs/scanners-profiles](../scanners-profiles/README.md)'s
JSON-configuration approach) — README documents `update()` as a plain
keyword-argument call, and nothing in this feature's scope calls for a
file format.
