# Requirements — Target Management

Source context: [README.md](README.md). Architecture and conventions:
[AGENTS.md](../../AGENTS.md). Builds on
[specs/authentication](../authentication/requirements.md) and
[specs/http-client](../http-client/requirements.md) — this feature is the
first Service built on top of both.

REST contract: `openApi/Veracode-veracode-dast-target-configuration-service-api-1.0.0-resolved.json`
("Veracode DAST Target Configuration Service API", v1.0.0, server
`https://api.veracode.com/dae/api/tcs-api/api/v1`).

Format: OpenAPI review, then user story + EARS-style acceptance criteria
per requirement.

---

## 0. OpenAPI Review

This section documents the portion of the OpenAPI contract relevant to
Target Management, per README's "OpenAPI Review" instruction. It is the
factual basis the requirements below are derived from — nothing in §1–§13
introduces a REST behavior not captured here.

### 0.1 In-scope REST endpoints

| Method | Path | operationId | Purpose |
|---|---|---|---|
| GET | `/targets` | `getTargets` | List targets (paginated, filterable, sortable). |
| POST | `/targets` | `createTarget` | Create a target. |
| GET | `/targets/{target_id}` | `getTargetById` | Get one target by ID. |
| PUT | `/targets/{target_id}` | `updateTarget` | Update a target. |
| DELETE | `/targets/{target_id}` | `deleteTargetById` | Delete a target. |

### 0.2 Additional Target operations found in the OpenAPI (out of scope)

The `target` tag in the OpenAPI defines more operations than the five
above. Per the README's Scope and Out-of-Scope sections, these are
documented here for completeness but are **not** implemented by this
feature:

| Method | Path | operationId | Why out of scope |
|---|---|---|---|
| GET | `/targets/{target_id}/spec` | `getTargetApiSpec` | API Specification management — Phase 2. |
| POST | `/targets/{target_id}/spec` | `uploadTargetApiSpec` | API Specification management — Phase 2. |
| GET | `/targets/{target_id}/spec/download` | `downloadTargetApiSpecContents` | API Specification management — Phase 2. |
| PUT | `/targets/{target_id}/link` | `linkTarget` | Application linking — not listed in README Scope; deferred until a feature explicitly covers it. |
| DELETE | `/targets/{target_id}/link` | `unlinkTarget` | Same as above. |

None of these are called, referenced, or required by this feature. The
`Target` response model's `application_name`, `application_uuid`, and
`application_id` fields (§0.4) are still exposed for reading, since they
are part of the `Target` schema returned by the in-scope GET/LIST/CREATE/
UPDATE calls — only the endpoints that *write* them are out of scope.

### 0.3 Query parameters — `GET /targets`

| Name | Required | Type | Constraints | Default |
|---|---|---|---|---|
| `page` | No | integer | min 0 | 0 |
| `limit` | No | integer | min 10, max 200 | 10 |
| `sort_by` | No | enum (`SortBy`) | `name`, `url`, `target_type`, `last_scan`, `status`, `max_cvss` | `name` |
| `sort_order` | No | enum (`SortOrder`) | `asc`, `desc` | `asc` |
| `name` | No | string | 1–255 chars, pattern `^[ -~]+$` | — |
| `url` | No | string | 1–1000 chars, pattern `^[ -~]+$` | — |
| `search_term` | No | string | 1–1000 chars, pattern `^[ -~]+$` | — |
| `target_type` | No | enum | `WEB_APP`, `API` | — |

### 0.4 Schemas

**`Target`** (response body for get/list-item/create/update) — required:
`target_id`, `name`, `protocol`, `url`, `target_type`, `scan_type`,
`is_sec_lead_only`, `teams`, `created_at`, `updated_at`. Optional:
`api_specification_file_url`, `description`, `last_scan`,
`application_name`, `application_uuid`, `application_id`, `max_cvss`,
`status` (enum `Status`: `RUNNING`, `STOPPING`, `STOPPED`, `FINISHED`,
`FAILED`).

**`TargetRequest`** (`POST /targets` body) — `TargetRequestBase` plus
required: `authorized_to_scan`, `is_sec_lead_only`, `name`, `protocol`,
`scan_type`, `target_type`, `url`.

**`TargetRequestBase`** (shared by create and update):

| Field | Type | Constraints |
|---|---|---|
| `name` | string | 1–255 chars, pattern `^[\p{L}\p{Nl}\p{Nd}\p{Print}]*$` |
| `protocol` | enum | `HTTP`, `HTTPS` |
| `url` | string | max 1000 chars |
| `api_specification_file_url` | string | max 255 chars. **Mandatory if `target_type` is `API`** (conditional rule, not in the `required` list). |
| `description` | string | pattern `^[\p{L}\p{Nl}\p{Nd}\p{Print}]*$` |
| `teams` | array\<string\> | nullable. "Currently we support assigning 1 team for each target." |

Additional fields only on `TargetRequest` (create), not on
`TargetUpdateRequest`:

| Field | Type | Constraints |
|---|---|---|
| `target_type` | enum | `WEB_APP`, `API` |
| `scan_type` | enum | `QUICK`, `FULL`, `ENTERPRISE` |
| `is_sec_lead_only` | boolean | **Conditional:** if `true`, `teams` must be null; if `false`, at least one team is required. |
| `authorized_to_scan` | boolean | — |

**`TargetUpdateRequest`** (`PUT /targets/{target_id}` body) —
`TargetRequestBase` with **no additional required fields at all** — every
field, including `name`, `protocol`, and `url`, is optional on update.
`target_type`, `scan_type`, `is_sec_lead_only`, and `authorized_to_scan`
are **not present** on `TargetUpdateRequest` — the REST contract does not
allow changing them via this endpoint.

**`PagedTargets`** (`GET /targets` 200 body) — required `page`
(`PageMeta`: `number`, `size`, `total_pages`, `total_elements`, all
required integers); `_embedded.targets: Target[]`; `_links: Link[]`
(HATEOAS navigation links, each with optional `href`/`rel`/`templated`).

**`Problem`** / **`ProblemError`** — RFC 7807 problem-details body used on
error responses that define a schema. `ProblemError.code` is a large,
API-wide enumeration (not specific to targets) shared with every other
resource in this OpenAPI document (analysis profiles, scanners,
schedules, discovered targets, ...). Target-relevant codes observed
include: `TARGET_NAME_NOT_UNIQUE`, `TARGET_NOT_FOUND`,
`INVALID_SEC_LEAD_PERMISSIONS`, `INVALID_TEAM_COUNT`, `TEAM_UNAUTHORIZED`,
`API_SPEC_URL_REQUIRED`, `MALFORMED_TARGET_URL`, `TARGET_LIMIT_EXCEEDED`,
`ORGANIZATION_FORBIDDEN`.

### 0.5 Enumerations

| OpenAPI schema | Values | Used by |
|---|---|---|
| target type (inline enum) | `WEB_APP`, `API` | `TargetRequest.target_type`, `Target.target_type`, `GET /targets` `target_type` filter |
| target scan type (inline enum) | `QUICK`, `FULL`, `ENTERPRISE` | `TargetRequest.scan_type`, `Target.scan_type` |
| protocol (inline enum) | `HTTP`, `HTTPS` | `TargetRequestBase.protocol`, `Target.protocol` |
| `SortBy` | `name`, `url`, `target_type`, `last_scan`, `status`, `max_cvss` | `GET /targets` `sort_by` |
| `SortOrder` | `asc`, `desc` | `GET /targets` `sort_order` |
| `Status` | `RUNNING`, `STOPPING`, `STOPPED`, `FINISHED`, `FAILED` | `Target.status` |

### 0.6 Conditional validation rules (server-enforced, documented for SDK-side lightweight mirroring)

1. `api_specification_file_url` is mandatory when `target_type == API`
   (create only — `target_type` cannot be set on update).
2. If `is_sec_lead_only == true`, `teams` must be null/empty. If
   `is_sec_lead_only == false`, at least one team is required.
3. `teams` currently accepts at most 1 entry ("Currently we support
   assigning 1 team for each target").

### 0.7 HTTP status codes and error responses

| Endpoint | Status | Meaning | Body schema |
|---|---|---|---|
| GET `/targets` | 200 | Success | `PagedTargets` |
| GET `/targets` | 401 | Unauthorized | none defined |
| GET `/targets` | 500 | Server error | `Problem` |
| POST `/targets` | 201 | Created | `Target` (+ `location` header) |
| POST `/targets` | 400 | Invalid request | `Problem` (`application/problem+json`) |
| POST `/targets` | 401 | Unauthorized | none defined |
| POST `/targets` | 501 | Server error | `Problem` |
| GET `/targets/{id}` | 200 | Success | `Target` |
| GET `/targets/{id}` | 401 | Unauthorized | none defined |
| GET `/targets/{id}` | 403 | Forbidden | none defined |
| GET `/targets/{id}` | 404 | Unknown target ID | `Problem` |
| GET `/targets/{id}` | 500 | Server error | `Problem` |
| PUT `/targets/{id}` | 200 | Success | `Target` |
| PUT `/targets/{id}` | 400 | Invalid request | `Problem` |
| PUT `/targets/{id}` | 401 | Unauthorized | none defined |
| PUT `/targets/{id}` | 403 | Forbidden | none defined |
| PUT `/targets/{id}` | 501 | Server error | `Problem` |
| DELETE `/targets/{id}` | 204 | Deleted | none |
| DELETE `/targets/{id}` | 401 | Unauthorized | none defined |
| DELETE `/targets/{id}` | 404 | Unknown target ID | none defined |
| DELETE `/targets/{id}` | 500 | Server error | `Problem` |

**Observed inconsistency, preserved as-is:** the OpenAPI document labels
`createTarget`'s and `updateTarget`'s server-error response `501` rather
than `500` (both are described as "Server-side error. Please try again
later."). This is not normalized or "corrected" in the SDK — per
[specs/http-client requirements §8.6](../http-client/requirements.md),
the HTTP Client already maps *every* unmapped status in the 500–599 range
to `VeracodeApiError` uniformly, so this document's status code is
irrelevant to how the SDK behaves; no target-specific handling is needed
either way.

---

## 1. List Targets

**User story:** As an SDK consumer, I want to list targets with the same
filtering, sorting, and pagination the REST API supports, so I can find
targets without writing raw HTTP calls.

**Acceptance criteria:**

1.1. WHEN `client.targets.list()` is called with no arguments THEN THE
SYSTEM SHALL call `GET /targets` with no query parameters other than the
REST API's own defaults (`page=0`, `limit=10`, `sort_by=name`,
`sort_order=asc`), per §0.3.

1.2. WHEN `client.targets.list()` is called with any of `page`, `limit`,
`sort_by`, `sort_order`, `name`, `url`, `search_term`, `target_type` THEN
THE SYSTEM SHALL forward each supplied value as the corresponding `GET
/targets` query parameter, per §0.3.

1.3. THE SYSTEM SHALL type `sort_by` as `TargetSortBy`, `sort_order` as
`SortOrder`, and `target_type` as `TargetType` (§6), rather than accepting
arbitrary strings.

1.4. WHEN `GET /targets` responds 200 THEN THE SYSTEM SHALL return a typed
`TargetPage` containing the list of `Target` models (from `_embedded.
targets`) and page metadata (`number`, `size`, `total_pages`,
`total_elements`, from `page`), per §0.4.

1.5. THE SYSTEM SHALL NOT expose the `_links` HATEOAS array from
`PagedTargets` on `TargetPage`. This is an architectural decision, not a
requirement derived from the OpenAPI or README — see design.md §12
("Pagination decisions").

1.6. THE SYSTEM SHALL NOT aggregate multiple pages into one call. One
`list(...)` call always corresponds to exactly one `GET /targets` request.

---

## 2. Get Target by ID

**User story:** As an SDK consumer, I want to fetch one target by its ID,
so I can look up a specific target's current state.

**Acceptance criteria:**

2.1. WHEN `client.targets.get(target_id)` is called THEN THE SYSTEM SHALL
call `GET /targets/{target_id}` with the given ID.

2.2. WHEN `GET /targets/{target_id}` responds 200 THEN THE SYSTEM SHALL
return a typed `Target` model built from the response body, per §0.4.

2.3. WHEN `GET /targets/{target_id}` responds 404 THEN THE SYSTEM SHALL
let `VeracodeNotFoundError` (raised by the HTTP Client, per
[specs/http-client requirements §8.3](../http-client/requirements.md))
propagate unchanged — Target Management adds no target-specific "not
found" exception.

---

## 3. Create Target

**User story:** As an SDK consumer, I want to create a target with a
typed request object, so I get IDE autocomplete and early feedback on
malformed data instead of building a raw JSON payload by hand.

**Acceptance criteria:**

3.1. WHEN `client.targets.create(...)` is called THEN THE SYSTEM SHALL
build a `TargetRequest`-shaped JSON body from the caller-supplied
`TargetCreate` model and call `POST /targets`.

3.2. THE SYSTEM SHALL require `name`, `url`, `protocol`, `target_type`,
`scan_type`, `authorized_to_scan`, and `is_sec_lead_only` on `TargetCreate`
— every field the OpenAPI `TargetRequest` schema marks required (§0.4) —
and SHALL NOT supply a default value for any of them.

3.3. THE SYSTEM SHALL type `protocol` as `Protocol`, `target_type` as
`TargetType`, and `scan_type` as `ScanType` (§6) on `TargetCreate`.

3.4. `api_specification_file_url`, `description`, and `teams` SHALL be
optional on `TargetCreate`, matching `TargetRequestBase` (§0.4).

3.5. BEFORE calling `POST /targets`, IF `target_type == TargetType.API`
and `api_specification_file_url` is not provided THEN THE SYSTEM SHALL
raise `TargetValidationError` (§8) without making an HTTP call, mirroring
the conditional rule in §0.6.1. This is a client-side convenience — the
server enforces the same rule independently (`API_SPEC_URL_REQUIRED`) and
continues to do so regardless of this check.

3.6. BEFORE calling `POST /targets`, IF `is_sec_lead_only is True` and
`teams` is non-empty, OR `is_sec_lead_only is False` and `teams` is empty
or `None`, THEN THE SYSTEM SHALL raise `TargetValidationError` (§8),
mirroring §0.6.2.

3.7. BEFORE calling `POST /targets`, IF `teams` contains more than one
entry THEN THE SYSTEM SHALL raise `TargetValidationError` (§8), mirroring
the current server-side limit in §0.6.3.

3.8. THE SYSTEM SHALL NOT check target name uniqueness before calling
`POST /targets` — that remains a server-side check
(`TARGET_NAME_NOT_UNIQUE`); a consumer that wants to avoid the resulting
error can compose `exists()`/`ensure()` (§10) themselves.

3.9. WHEN `POST /targets` responds 201 THEN THE SYSTEM SHALL return a
typed `Target` model built from the response body, per §0.4.

---

## 4. Update Target

**User story:** As an SDK consumer, I want to update only the fields of a
target I actually intend to change, so that fields I don't mention are
left untouched by the SDK.

**Acceptance criteria:**

4.1. WHEN `client.targets.update(target_id, ...)` is called THEN THE
SYSTEM SHALL build a `TargetUpdateRequest`-shaped JSON body from the
caller-supplied `TargetUpdate` model containing only the fields the
caller explicitly set, and call `PUT /targets/{target_id}`.

4.2. `TargetUpdate` SHALL expose exactly the fields `TargetUpdateRequest`
accepts — `name`, `protocol`, `url`, `api_specification_file_url`,
`description`, `teams` — all optional, matching §0.4. THE SYSTEM SHALL NOT
expose `target_type`, `scan_type`, `is_sec_lead_only`, or
`authorized_to_scan` on `TargetUpdate`, since `TargetUpdateRequest` does
not accept them; the REST API does not support changing them via this
endpoint.

4.3. THE SYSTEM SHALL retain the distinction between a field the caller
never mentioned and a field the caller explicitly set to `None`, so that
a caller can deliberately clear a nullable field such as `teams` without
affecting any field they didn't set. THE SYSTEM SHALL NOT send a field
the caller never touched. (How this distinction is represented
internally is a design concern — see design.md §2.1.)

4.4. WHEN `PUT /targets/{target_id}` responds 200 THEN THE SYSTEM SHALL
return a typed `Target` model built from the response body, per §0.4.

4.5. IF `teams` is explicitly set on `TargetUpdate` with more than one
entry THEN THE SYSTEM SHALL raise `TargetValidationError` (§8), mirroring
§0.6.3.

4.6. `update` SHALL always require the caller to already know `target_id`
— there is no REST operation that updates a target by `name` alone. A
caller who only has a `name` uses `update_by_name` (§10) instead.

---

## 5. Delete Target

**User story:** As an SDK consumer, I want to delete a target by ID, so I
can remove targets that are no longer needed.

**Acceptance criteria:**

5.1. WHEN `client.targets.delete(target_id)` is called THEN THE SYSTEM
SHALL call `DELETE /targets/{target_id}`.

5.2. WHEN `DELETE /targets/{target_id}` responds 204 THEN THE SYSTEM
SHALL return `None`.

5.3. WHEN `DELETE /targets/{target_id}` responds 404 THEN THE SYSTEM
SHALL let `VeracodeNotFoundError` propagate unchanged, per 2.3's rationale.

---

## 6. Typed models and enumerations

**User story:** As an SDK consumer, I want target-related enums and
models as real Python types, so invalid values are caught by my editor
and by `mypy` instead of at runtime inside Veracode's API.

**Acceptance criteria:**

6.1. THE SYSTEM SHALL define `TargetType(str, Enum)` with members `WEB_APP`
and `API`.

6.2. THE SYSTEM SHALL define `ScanType(str, Enum)` with members `QUICK`,
`FULL`, and `ENTERPRISE`.

6.3. THE SYSTEM SHALL define `Protocol(str, Enum)` with members `HTTP` and
`HTTPS`.

6.4. THE SYSTEM SHALL define `TargetSortBy(str, Enum)` with members
`NAME`, `URL`, `TARGET_TYPE`, `LAST_SCAN`, `STATUS`, and `MAX_CVSS`,
mapping to the OpenAPI `SortBy` values `name`, `url`, `target_type`,
`last_scan`, `status`, `max_cvss`.

6.5. THE SYSTEM SHALL define `SortOrder(str, Enum)` with members `ASC` and
`DESC`.

6.6. THE SYSTEM SHALL define `TargetStatus(str, Enum)` with members
`RUNNING`, `STOPPING`, `STOPPED`, `FINISHED`, and `FAILED` — the same
values as the OpenAPI `Status` schema (§0.5). Renaming `Status` to
`TargetStatus` is an architectural decision, not a requirement derived
from the OpenAPI — see design.md §12 ("Target model decisions").

6.7. THE SYSTEM SHALL NOT model `ProblemError.code` as a Python enum. It
is a single enumeration shared by the entire Veracode DAST Target
Configuration Service API (analysis profiles, scanners, discovered
targets, schedules, ...), not owned by Target Management; modeling a
target-scoped subset of it would either omit valid values returned for
non-target errors passing through the same exception types, or require
this feature to track an API-wide enumeration it doesn't own. Error codes
remain available to a consumer as plain strings inside the exception's
`response_body` (already exposed by
[specs/http-client requirements §8.10](../http-client/requirements.md)).

6.8. THE SYSTEM SHALL define `Target`, `TargetCreate`, `TargetUpdate`, and
`TargetPage` as typed models (§0.4) that comply with the model rules in
[AGENTS.md §3](../../AGENTS.md#3-architecture) (models never perform HTTP
requests, contain business logic, or depend on the HTTP Client).

6.9. THE SYSTEM SHALL NOT define a model for `Problem`/`ProblemError`/
`Link` — these are generic REST transport/error shapes already handled by
the HTTP Client's exception attributes (§0.7), not Target resources.

---

## 7. Client-side validation

**User story:** As an SDK consumer, I want obviously invalid target data
rejected immediately with a clear message, so I don't have to make a
round trip to Veracode to learn my request was malformed.

**Acceptance criteria:**

7.1. THE SYSTEM SHALL perform the checks in 3.2, 3.5, 3.6, 3.7, and 4.5
before sending any HTTP request for `create`/`update`.

7.2. THE SYSTEM SHALL NOT duplicate every server-side constraint from
§0.4 (e.g. the `name`/`description` Unicode pattern, exact length limits)
as client-side validation. Only the conditional rules in §0.6 — which a
caller cannot discover from Python type hints alone — are validated
client-side; field types and required-ness are already enforced by the
typed models themselves (§6.8) and by `mypy`.

7.3. THE SYSTEM SHALL NOT perform any validation that could reject a
request the server would accept, or accept a request the server would
reject in a way not covered by §0.6 — client-side validation strictly
mirrors documented server rules, per README's "must never replace
server-side validation."

---

## 8. Error handling

**User story:** As an SDK consumer, I want a clear distinction between "my
request was invalid before it was even sent" and "Veracode rejected my
request," so I can handle each case appropriately.

**Acceptance criteria:**

8.1. THE SYSTEM SHALL define `TargetValidationError(VeracodeSDKError)` —
not a subclass of `VeracodeApiError` — for the client-side checks in §7,
since no HTTP request was made when it is raised.

8.2. THE SYSTEM SHALL define `TargetNotFoundError(VeracodeSDKError)` —
also not a subclass of `VeracodeApiError` — raised by `update_by_name`
(§10.10) when no target matches the given `name`. This is distinct from
`VeracodeNotFoundError` (raised by the HTTP Client for an actual REST 404,
per [specs/http-client requirements
§8.3](../http-client/requirements.md)): reaching "no match" here means the
`GET /targets` call `get_by_name` made underneath **succeeded** — it
simply returned zero matching results — so no REST call ever failed.

8.3. THE SYSTEM SHALL NOT define any other new exception type beyond
`TargetValidationError` and `TargetNotFoundError`. Every failure that
occurs after an HTTP request is sent (401, 403, 404, 409, 422, other
4xx, 5xx, connection errors, timeouts) SHALL surface as whichever
exception [specs/http-client requirements
§8](../http-client/requirements.md) already defines for that condition,
unmodified and unwrapped.

8.4. THE SYSTEM SHALL NOT catch and swallow any exception raised by the
HTTP Client; Target Management only ever lets it propagate, per README's
"Target Management should only handle Target-specific business
scenarios."

8.5. `TargetValidationError` and `TargetNotFoundError` SHALL follow the
naming convention documented in design.md §2.2: prefixed by the resource
name, subclassing `VeracodeSDKError` directly rather than
`VeracodeApiError`. This convention is intended for reuse by future
resource-specific services, per design.md §2.2.

---

## 9. Logging

**User story:** As an SDK maintainer, I want Target Management to log
meaningful business events, so target lifecycle actions are traceable
without duplicating the HTTP Client's own request/response logging.

**Acceptance criteria:**

9.1. WHEN a target is successfully created, updated, or deleted THEN THE
SYSTEM SHALL emit an INFO-level log naming the operation and the
`target_id` (for update/delete) or the resulting `target_id` (for
create).

9.2. WHEN `ensure()` (§10) creates a new target because none matched THEN
THE SYSTEM SHALL emit an INFO-level log stating that a new target was
created by `ensure`, distinguishing this from an ordinary `create()` call
in the log message.

9.3. THE SYSTEM SHALL NOT log target `url`, `description`, or any other
business data value beyond `target_id` and `name` — per README, "sensitive
information must never be logged," and per [AGENTS.md
§6.2](../../AGENTS.md#62-business-data) these are consumer-supplied
business data, not something this feature should assume is safe to log in
full.

9.4. THE SYSTEM SHALL NOT re-implement HTTP request/response logging;
that responsibility belongs entirely to the HTTP Client, per
[specs/http-client requirements §9.6](../http-client/requirements.md).

---

## 10. Convenience methods (`get_by_name`, `exists`, `ensure`, `update_by_name`)

**User story:** As an SDK consumer, I want common "does this target
already exist" workflows handled for me, so I don't have to hand-roll
list-then-filter logic in every script that manages targets idempotently.

**Acceptance criteria:**

10.1. WHEN `client.targets.get_by_name(name)` is called THEN THE SYSTEM
SHALL call `list(name=name)` (§1) and return the first returned `Target`
whose `name` matches the argument exactly (case-sensitive), or `None` if
no returned target matches.

10.2. IF the first page returned by 10.1 does not contain an exact match
but `page.total_pages > 1` THEN THE SYSTEM SHALL request subsequent pages
(same `name` filter, incrementing `page`) until an exact match is found or
all pages are exhausted. Scanning multiple pages, rather than trusting the
first page alone, is an architectural decision — see design.md §12
("Convenience methods").

10.3. `get_by_name` SHALL NOT raise `VeracodeNotFoundError` or any other
exception when no target matches; a caller distinguishes "not found" from
an actual failure by checking for `None` versus a raised exception.

10.4. WHEN `client.targets.exists(name)` is called THEN THE SYSTEM SHALL
call `get_by_name(name)` and return `True` if it returns a `Target`,
`False` if it returns `None`.

10.5. WHEN `client.targets.ensure(...)` is called with the same arguments
as `create` (§3) THEN THE SYSTEM SHALL call `get_by_name(name)` first; IF
a match is found, THE SYSTEM SHALL return the existing `Target` unchanged
and SHALL NOT call `create` or `update`; IF no match is found, THE SYSTEM
SHALL call `create(...)` with the supplied arguments and return the newly
created `Target`.

10.6. `ensure` SHALL NOT compare the existing target's fields against the
caller-supplied arguments, and SHALL NOT call `update` to reconcile any
difference. This scope boundary is an architectural decision, not a
requirement derived from the OpenAPI or README — see design.md §12
("`ensure()` behavior").

10.7. `get_by_name`, `exists`, and `ensure` SHALL NOT require any REST
endpoint beyond `GET /targets` and `POST /targets`, per README's "must
never require additional Veracode endpoints."

10.8. WHEN `client.targets.update_by_name(name, target)` is called THEN
THE SYSTEM SHALL call `get_by_name(name)` first, per requirements.md §4.6.

10.9. IF `get_by_name(name)` (10.8) returns a `Target` THEN THE SYSTEM
SHALL call `update(found.target_id, target)` (§4) and return its result.

10.10. IF `get_by_name(name)` (10.8) returns `None` THEN THE SYSTEM SHALL
raise `TargetNotFoundError` (§8.2) and SHALL NOT call `update` or send a
`PUT` request. Raising rather than returning `None` here (unlike
`get_by_name` itself) is an architectural decision — see design.md §12
("`update_by_name()` behavior").

10.11. `update_by_name` SHALL NOT require any REST endpoint beyond
`GET /targets` and `PUT /targets/{target_id}` — both already used by
`get_by_name` and `update` respectively, per README's "must never require
additional Veracode endpoints."

---

## 11. Boundaries (non-goals for this feature)

**User story:** As the SDK architect, I want Target Management strictly
scoped to the Target resource, so unrelated resources don't creep into
the first Service implementation.

**Acceptance criteria:**

11.1. THE SYSTEM SHALL NOT implement Target Configuration, Analysis
Profiles, Scanner Configuration, Scanner Variables, Authentication
Configuration, Analysis/scan execution, Reports, Discovered Targets, ISM
Gateways, or Schedules, per README's Out of Scope.

11.2. THE SYSTEM SHALL NOT implement `getTargetApiSpec`,
`uploadTargetApiSpec`, `downloadTargetApiSpecContents`, `linkTarget`, or
`unlinkTarget` (§0.2), even though they share the `target` tag in the
OpenAPI document.

11.3. THE SYSTEM SHALL comply with the service-layer rules in [AGENTS.md
§3](../../AGENTS.md#3-architecture): every REST call goes through an
injected `HttpClient` instance, not `requests` directly, `auth.py`, or
`config.py`.

11.4. `TargetsService` itself SHALL NOT construct an `HttpClient`; it
only ever receives one, already configured, via its constructor. THE
SYSTEM SHALL NOT hardcode the DAST Target Configuration Service base URL
(`https://api.veracode.com/dae/api/tcs-api/api/v1`, §0) inside `client.py`
— ownership of that value belongs to the Target Management service, per
[AGENTS.md §3.1](../../AGENTS.md#31-authentication-is-base-url-agnostic):
"adding a new Veracode API base URL is a change to a service, never to
`auth.py` or `client.py`." (Which module exports the constant and how
`client.py` obtains it is a design concern — see design.md §2.3–§2.4.)

11.5. THE SYSTEM SHALL NOT implement pagination-aggregation, caching, or
retry logic beyond what the HTTP Client already provides — Target
Management's only added looping behavior is the bounded, single-purpose
page scan in 10.2.

---

## 12. Public interface and reuse

**User story:** As an SDK consumer, I want `client.targets` to be the
resource-oriented entry point AGENTS.md promises, so my code reads
naturally regardless of where it runs.

**Acceptance criteria:**

12.1. THE SYSTEM SHALL expose a `TargetsService` class whose public
methods are exactly `list`, `get`, `create`, `update`, `delete`,
`get_by_name`, `exists`, `ensure`, and `update_by_name`, matching
README's Scope and "Expected Public API." `update_by_name` composes
`get_by_name` (§10.1) and `update` (§4) with no new REST endpoint, per
§10.11. The choice to add `update_by_name` as a convenience method beyond
README's original examples is an architectural decision — see design.md
§12 ("Convenience methods").

12.2. THE SYSTEM SHALL wire `TargetsService` onto `VeracodeClient` as
`client.targets`, using `get_veracode_auth()` for authentication and the
base URL owned by the Target Management service (§11.4), per [AGENTS.md
§9](../../AGENTS.md#9-desired-public-api). This is the first feature to
introduce `VeracodeClient`'s actual wiring — it was deliberately left
unbuilt by both prior features (see [specs/http-client design
§1](../http-client/design.md#1-overview)). (The exact construction
sequence is a design concern — see design.md §2.4.)

12.3. Every public class and method introduced by this feature SHALL
comply with the code conventions in [AGENTS.md
§7](../../AGENTS.md#7-code-conventions) (complete type hints, Google-style
docstrings).

12.4. THE SYSTEM SHALL comply with the Platform Agnostic principle in
[AGENTS.md §5](../../AGENTS.md#5-design-principles): no dependency on
Azure DevOps, a CLI, or any other specific consumer.

12.5. `TargetsService` SHALL comply with the Stateless principle in
[AGENTS.md §5](../../AGENTS.md#5-design-principles): it holds only its
`HttpClient` instance; no target data is cached or retained between
calls.

---

## 13. Testability

**User story:** As a maintainer, I want to verify request shaping,
response parsing, validation, and convenience-method composition without
a real Veracode account.

**Acceptance criteria:**

13.1. THE SYSTEM SHALL allow every `TargetsService` method to be tested by
constructing it with a fake/stub `HttpClient` (or a `pytest` `monkeypatch`
of its `get`/`post`/`put`/`delete` methods) returning prepared
`HttpResponse` values, with no real network access, environment
variables, or Veracode credentials required.

13.2. THE SYSTEM SHALL NOT require a new third-party mocking/HTTP-fixture
dependency beyond what [specs/http-client requirements
§12](../http-client/requirements.md) already establishes.

13.3. THE SYSTEM SHALL allow `ensure`'s two branches (found vs. not found)
and `get_by_name`'s multi-page scan (10.2) to be exercised deterministically
by stubbing successive `list`/`HttpClient.get` return values.
