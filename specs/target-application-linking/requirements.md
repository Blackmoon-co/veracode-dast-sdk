# Requirements — Target ↔ Application Linking

Traceable to [README.md](README.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Depends on the
[HTTP Client](../http-client/requirements.md) and extends
[Target Management](../target-management/requirements.md): it implements
the two `target`-tagged endpoints that spec listed as out of scope
"deferred until a feature explicitly covers it"
([target-management/requirements.md §0.2](../target-management/requirements.md#02-additional-target-operations-found-in-the-openapi-out-of-scope)),
and adds one read-only sibling service (`ApplicationsService`) on the same
Veracode API domain and base URL.

Reuses `TARGET_CONFIGURATION_SERVICE_BASE_URL` and `TargetValidationError`
from Target Management; reuses the `get_by_name` / `exists` name-resolution
pattern from [Team Management](../team-management/requirements.md).

---

## 0. OpenAPI Review

Source: `openApi/Veracode-veracode-dast-target-configuration-service-api-1.0.0-resolved.json`,
server `https://api.veracode.com/dae/api/tcs-api/api/v1` (**no new base
URL**).

### 0.1 In-scope REST endpoints

| Method | Path | operationId | Purpose |
|---|---|---|---|
| GET | `/applications` | `getApplications` | List applications (paged, filter by `name`). |
| PUT | `/targets/{target_id}/link` | `linkTarget` | Link a Target to an Application by Application UUID. |
| DELETE | `/targets/{target_id}/link` | `unlinkTarget` | Unlink a Target from its Application. |

### 0.2 Query parameters — `GET /applications`

| Name | Required | Type | Constraints | Default |
|---|---|---|---|---|
| `page` | No | integer | min 0 | 0 |
| `limit` | No | integer | min 10, max 200 | 10 |
| `name` | No | string | 1–1000 chars, pattern `^[ -~]+$` (printable ASCII) | — |

The `name` filter's exact matching semantics are **not documented** (no
statement of exact vs. substring). `get_by_name` therefore does its own
exact, case-sensitive comparison client-side and scans every page —
identical to `TeamService.get_by_name`
([team-management/requirements.md](../team-management/requirements.md)).

### 0.3 Path / body parameters — link & unlink

`linkTarget` / `unlinkTarget` both take `target_id` (path, `string`,
required). `linkTarget` additionally requires a `TargetLinkRequest` body.

**`TargetLinkRequest`** — required `application_uuid` (`string`,
`minLength: 1`). No other fields. Example: `{"application_uuid":
"60E630B1-4AB7-4415-B920-5DD30B2E3A45"}`.

### 0.4 Schemas

**`PagedApplications`** (`GET /applications` 200 body) — required `page`
(`PageMeta`: `number`, `size`, `total_pages`, `total_elements`, all
required integers — identical shape to `PagedTargets`); `_embedded`
(`EmbeddedApplications`); `_links` (`Link[]`, HATEOAS — not exposed by the
SDK, same decision as `TargetPage`,
[target-management/requirements.md §1.5](../target-management/requirements.md#1-list-targets)).

**`EmbeddedApplications`** — required `Applications` (**capital `A`**):
`Application[]`. `_embedded` may be absent entirely when the page is empty
— the SDK treats a missing `_embedded` or missing `Applications` as an
empty list, same guard as `TargetPage.from_api`.

**`Application`** — required `guid`, `id`, `name`:

| Field | Type | Notes |
|---|---|---|
| `guid` | string | Application UUID. This is the value passed to `linkTarget`. |
| `id` | string | Application identifier. **String**, not integer, in this schema. |
| `name` | string | Application name. |
| `linked_scan_target_url` | string | Optional. URL of the scan already linked to this Application, if any. |

Note: the `Target` response schema
([target-management/requirements.md §0.4](../target-management/requirements.md#04-schemas))
has `application_id` typed as `integer` (`int64`). That is a different
field on a different schema; `Application.id` here is its own `string`
field and is modelled as `str`. No attempt is made to reconcile the two.

**`Problem` / `ProblemError`** — RFC 7807 body on the error responses that
define a schema. `ProblemError.code` is the same API-wide enumeration
Target Management already declined to model
([target-management/requirements.md §6.7](../target-management/requirements.md#6-typed-models-and-enumerations));
codes relevant to this feature that appear in it:
`APPLICATION_NOT_FOUND`, `TARGET_ALREADY_LINKED_TO_APPLICATION`,
`APPLICATION_ALREADY_LINKED_TO_TARGET`,
`TARGET_NOT_LINKED_TO_ANY_APPLICATION`,
`INVALID_STATUS_TO_UNLINK_APPLICATION`. Not modelled as an enum — a
consumer reads them as plain strings from the exception's `response_body`.

### 0.5 Why the TCS `/applications` endpoint, not the AppSec one

The Veracode "Example" Postman collection
(`openApi/Veracode Example.postman_collection.json`) lists an
"Applications" request against `GET https://api.veracode.com/appsec/v1/applications`.
This SDK does **not** use that:

1. The DAST TCS OpenAPI document — the source of truth for every
   Target-related spec — defines its own `GET /applications` returning
   exactly `guid` / `id` / `name` / `linked_scan_target_url`, which is
   everything linking needs.
2. It is on `TARGET_CONFIGURATION_SERVICE_BASE_URL`, already wired for
   `client.targets` and its siblings — no new base URL constant, no new
   `HttpClient`, no new Veracode API domain.
3. Using the AppSec API would pull in a whole domain
   ([AGENTS.md §3.3](../../AGENTS.md#33-supported-veracode-api-domains))
   that the roadmap still files under "Later / unscheduled", for one
   lookup the DAST API already serves.

If a future feature genuinely needs the richer AppSec Applications
resource (business criticality, policy, teams, custom fields), that is a
separate spec that introduces the AppSec domain deliberately — not a
reason to route this lookup there now.

### 0.6 HTTP status codes

| Endpoint | Status | Meaning | Body |
|---|---|---|---|
| GET `/applications` | 200 | Success | `PagedApplications` |
| GET `/applications` | 401 | Unauthorized | none |
| GET `/applications` | 500 | Server error | `Problem` |
| PUT `/targets/{id}/link` | 204 | Linked | none |
| PUT `/targets/{id}/link` | 400 | Malformed / invalid payload | `Problem` |
| PUT `/targets/{id}/link` | 401 / 403 | Unauthorized / forbidden | none |
| PUT `/targets/{id}/link` | 404 | Target or Application not found | none |
| PUT `/targets/{id}/link` | 409 | Target/Application already linked | none |
| PUT `/targets/{id}/link` | 422 | Target must be of enterprise type | none |
| PUT `/targets/{id}/link` | 500 | Server error | `Problem` |
| DELETE `/targets/{id}/link` | 204 | Unlinked | none |
| DELETE `/targets/{id}/link` | 400 | Malformed | `Problem` |
| DELETE `/targets/{id}/link` | 401 / 403 | Unauthorized / forbidden | none |
| DELETE `/targets/{id}/link` | 404 | Target not found | none |
| DELETE `/targets/{id}/link` | 409 | Result import(s) still in progress | none |
| DELETE `/targets/{id}/link` | 422 | Target must be of enterprise type | none |
| DELETE `/targets/{id}/link` | 501 | Server error | `Problem` |

Every one of these is already mapped centrally by the HTTP Client
(401→`VeracodeAuthenticationError`, 403→`VeracodeAuthorizationError`,
404→`VeracodeNotFoundError`, 409→`VeracodeConflictError`,
422→`VeracodeValidationError`, everything else 4xx/5xx→`VeracodeApiError`,
per [client.py](../../src/veracode_dast/client.py) `_STATUS_EXCEPTIONS`).
**No new status-code handling is added by this feature.** The `unlinkTarget`
`501`-instead-of-`500` label is the same documented inconsistency Target
Management already noted and left alone
([target-management/requirements.md §0.7](../target-management/requirements.md#07-http-status-codes-and-error-responses)).

---

## 1. Overview

Two additions to the existing layered architecture, both on
`TARGET_CONFIGURATION_SERVICE_BASE_URL`:

- **`ApplicationsService`** (`client.applications`) — read-only:
  `list`, `get_by_name`, `exists`. Structurally a copy of
  `TeamService`, against `/applications` instead of `/teams`.
- **`TargetsService.link` / `.unlink`** — two new methods on the existing
  service, one HTTP call each.

No configuration document, no new base URL, no new `HttpClient`, no change
to `TargetCreate` / `TargetUpdate` / `Target`.

## 2. Goals

- Resolve a Veracode Application to its UUID by exact name.
- Link an existing Target to an Application by that UUID, and unlink it.
- Reuse the shared `HttpClient`, the exception hierarchy,
  `TARGET_CONFIGURATION_SERVICE_BASE_URL`, and `TargetValidationError` —
  add exactly one new exception (`ApplicationNotFoundError`).
- Keep the "resolve app → resolve team → create target → link" ordering
  in the **example script**, not the SDK.

## 3. Functional Requirements

### 3.1 `ApplicationsService`

3.1.1. `list(*, name: str | None = None, page: int = 0, limit: int = 10)
       -> ApplicationPage`. Calls `GET /applications`, forwarding `name`
       only when not `None`; returns `ApplicationPage.from_api(response.data)`.
       One call = one HTTP request; never aggregates pages.

3.1.2. `get_by_name(name: str) -> Application`. Rejects a blank/whitespace
       `name` before any HTTP call
       (`TargetValidationError(rule="name_required")` — §5.1). Then scans
       `list(name=name)` page by page for an **exact, case-sensitive**
       `name` match and returns the first `Application` that matches. If no
       page contains an exact match, raises `ApplicationNotFoundError(name)`
       (§4). Identical control flow to `TeamService.get_by_name`.

3.1.3. `exists(name: str) -> bool`. Calls `get_by_name(name)`; returns
       `True` on success, `False` if it raises `ApplicationNotFoundError`.
       Any other exception propagates.

### 3.2 `TargetsService.link` / `.unlink`

3.2.1. `link(target_id: str, application_uuid: str) -> None`. Rejects a
       blank `target_id` (`rule="target_id_required"`) or blank
       `application_uuid` (`rule="application_uuid_required"`) before any
       HTTP call (§5.1). Calls
       `PUT /targets/{target_id}/link` with body
       `{"application_uuid": application_uuid}`. Returns `None` on `204`.

3.2.2. `unlink(target_id: str) -> None`. Rejects a blank `target_id`
       (`rule="target_id_required"`) before any HTTP call. Calls
       `DELETE /targets/{target_id}/link`. Returns `None` on `204`.

3.2.3. Neither method reads, fetches, or validates the Target's
       `scan_type`, link state, or existence beforehand (§5.3). Every
       server-side rejection (`404`, `409`, `422`, ...) surfaces as the
       HTTP Client exception already mapped for that status, unchanged.

### 3.3 Models

3.3.1. `Application` — frozen dataclass: `guid: str`, `id: str`,
       `name: str`, `linked_scan_target_url: str | None = None`. Plus
       `from_api(data: dict) -> Application`.

3.3.2. `ApplicationPage` — frozen dataclass: `items: list[Application]`,
       `page_number: int`, `page_size: int`, `total_pages: int`,
       `total_elements: int`. Plus `from_api(data: dict) -> ApplicationPage`
       reading `_embedded.Applications` (capital `A`) and
       `page.{number,size,total_pages,total_elements}` — a missing
       `_embedded`/`Applications` yields `items == []`.

3.3.3. Neither model imports `requests` or `HttpClient`, performs I/O, or
       carries business logic ([AGENTS.md §3](../../AGENTS.md#3-architecture)).

## 4. New Exception

`ApplicationNotFoundError(VeracodeSDKError)` — carries `name` (the string
searched for); message `f"No application found with name: {name}"`.
**Not** a subclass of `VeracodeApiError`: the `GET /applications` call it
follows returned `200` — there was no failed request. Exact shape and
rationale mirror `TeamNotFoundError`
([exceptions.py](../../src/veracode_dast/exceptions.py)).

## 5. Validation Rules

Checked **before** any HTTP call; each raises before network I/O:

5.1. Blank/whitespace-only string arguments →
     `TargetValidationError(rule=...)`:
     - `ApplicationsService.get_by_name` / `exists`: `name` →
       `rule="name_required"`.
     - `TargetsService.link` / `unlink`: `target_id` →
       `rule="target_id_required"`; `link`'s `application_uuid` →
       `rule="application_uuid_required"`.

     `TargetValidationError` is reused rather than introducing an
     `ApplicationValidationError` — the two blank-string checks are the
     only client-side validation this feature has, and Target Management's
     existing type is already the right shape (`rule` attribute,
     subclasses `VeracodeSDKError`).

5.2. No client-side check of Application-name character set / length
     (the OpenAPI `^[ -~]+$`, 1–1000). Consistent with
     [target-management/requirements.md §7.2](../target-management/requirements.md#7-client-side-validation)
     — field-format rules are left to the server.

5.3. No client-side check that the Target is ENTERPRISE scan type before
     `link()` / `unlink()`, even though the OpenAPI documents a `422`
     "Target must be of enterprise type". Enforcing it client-side would
     require an extra `GET /targets/{id}` per link call and would risk
     rejecting a request the server would accept if that rule is relaxed.
     The `422` propagates as `VeracodeValidationError`. This is the same
     principle as
     [target-management/requirements.md §7.3](../target-management/requirements.md#7-client-side-validation)
     ("never reject a request the server would accept").

5.4. `link()` is **not** made idempotent. An already-linked Target yields
     `409` → `VeracodeConflictError`, propagated unchanged. The SDK does
     not swallow it or pre-check link state; a caller that wants
     idempotency catches `VeracodeConflictError` or calls `unlink()`
     first. (Rationale: matches `create()`'s treatment of
     `TARGET_NAME_NOT_UNIQUE` — the SDK exposes `exists`/`ensure` for
     opt-in idempotency rather than baking it into the primitive.)

## 6. Non-Functional Requirements

6.1. Stateless: `ApplicationsService` holds only an injected `HttpClient`;
     `link`/`unlink` add no state to `TargetsService`
     ([AGENTS.md §5](../../AGENTS.md#5-design-principles)).

6.2. Full type hints and Google-style docstrings on every public and
     private function ([AGENTS.md §7](../../AGENTS.md#7-code-conventions)).

6.3. No direct `requests` import; every call goes through the shared
     `HttpClient` ([AGENTS.md §3](../../AGENTS.md#3-architecture)).

6.4. No business data (`name`, `target_id`, `application_uuid`) read from
     an environment variable
     ([AGENTS.md §6.2](../../AGENTS.md#62-business-data)).

6.5. Logging at meaningful points only, matching `TeamService`'s
     precedent: `INFO` when `get_by_name` resolves a name (the name and
     `guid`, exactly as `TeamService` logs the name and `team_id`); `INFO`
     on a successful `link` / `unlink` naming **only** `target_id` — never
     the `application_uuid`; validation "not found" at `INFO`. No
     request/response logging (the HTTP Client owns that). No
     `linked_scan_target_url` (a business URL, like a Target's `url`) in
     any log record.

6.6. `ApplicationsService` never imports or depends on
     `services/targets.py`, and `TargetsService.link`/`unlink` never
     import `ApplicationsService` — the two are composed only by the
     caller (the example), exactly as Team Management is kept independent
     of Target Management
     ([services/teams.py](../../src/veracode_dast/services/teams.py) module
     docstring).

## 7. Acceptance Criteria

- `client.applications.list(name="X")` sends `GET /applications?name=X`
  (plus `page=0`, `limit=10`) and returns an `ApplicationPage` whose
  `items` match `_embedded.Applications` and whose paging fields match
  `page.*`.
- `client.applications.list()` sends no `name` query parameter.
- Given a page whose `_embedded` is absent, `ApplicationPage.from_api`
  yields `items == []` (no `KeyError`).
- `client.applications.get_by_name("My App")` returns the `Application`
  whose `name == "My App"` exactly; given only a case-different or
  substring row, it raises `ApplicationNotFoundError`.
- `get_by_name` scans page 2 when page 1 has no exact match and
  `page.total_pages > 1`; returns `None`-equivalent behaviour as a raise,
  never as a return value.
- `client.applications.exists("My App")` returns `True` when
  `get_by_name` succeeds and `False` when it raises
  `ApplicationNotFoundError`; a `500` from the underlying call propagates
  as `VeracodeApiError` (not swallowed into `False`).
- Blank `name` → `TargetValidationError(rule="name_required")`, no HTTP
  call.
- `client.targets.link("t-1", "app-uuid")` sends
  `PUT /targets/t-1/link` with body exactly `{"application_uuid":
  "app-uuid"}` and returns `None` on `204`.
- `client.targets.unlink("t-1")` sends `DELETE /targets/t-1/link` and
  returns `None` on `204`.
- Blank `target_id` or blank `application_uuid` →
  `TargetValidationError` with the matching `rule`, no HTTP call.
- A `404` / `409` / `422` from `link()` propagates as
  `VeracodeNotFoundError` / `VeracodeConflictError` /
  `VeracodeValidationError` respectively, unchanged and unwrapped.
- `client.applications` shares the **same `HttpClient` instance** as
  `client.targets` (asserted by object identity in the wiring test).

## 8. Out of Scope

Per [README.md "Out of scope"](README.md#out-of-scope):

- The AppSec Applications API and any other AppSec-domain resource.
- Create / update / delete of Applications.
- Any change to `TargetCreate`, `TargetUpdate`, `Target`, or the target
  create/update flow.
- A `TargetsService.link_by_app_name(...)` convenience that composes the
  lookup and the link — deliberately left as caller composition
  ([README.md "Motivating requirement"](README.md#motivating-requirement)),
  so `services/targets.py` gains no dependency on `ApplicationsService`.
- Result-import status handling after a link.
- Reading/parsing HATEOAS `_links`.
- Any CLI or execution-platform integration
  ([AGENTS.md §1](../../AGENTS.md#1-project-vision) non-goals).

---

## 9. Testability

Stub/fake `HttpClient` returning prepared `HttpResponse` values or raising
prepared `VeracodeApiError` subclasses — same approach as
[target-management/requirements.md §13](../target-management/requirements.md#13-testability)
and every other service spec. No real network, environment variables, or
Veracode credentials. `get_by_name`'s multi-page scan is exercised by
scripting successive `HttpClient.get` return values, exactly as
`TeamService.get_by_name`'s tests do.
