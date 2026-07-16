# Requirements — Team Management

Source context: [README.md](README.md). Architecture and conventions:
[AGENTS.md](../../AGENTS.md). Builds on
[specs/authentication](../authentication/requirements.md) and
[specs/http-client](../http-client/requirements.md) — this feature reuses
both unchanged. Sibling precedent:
[specs/target-management](../target-management/requirements.md) — the
first Service built on this SDK's architecture; Team Management is the
second Service, and the first outside the DAST API domain (AGENTS.md
§3.2, §3.3).

REST contract: the Veracode **Admin API** (also called the Identity API),
base URL `https://api.veracode.com/api/authn/v2` (AGENTS.md §3.3). Unlike
Target Management, no resolved OpenAPI document for this API exists in
this repository; §0 originally relied on Veracode's public documentation
and the Veracode-maintained `veracode-api-py` client library. It has
since been substantially strengthened by a real Veracode-authored Postman
collection (`openApi/Veracode Example.postman_collection.json`), which
exercises the actual `Teams` endpoints end-to-end and is the strongest
evidence available in this repository for this API — see §0.1/§0.2. §0
documents what this feature's Admin API review actually established, and
— just as importantly — what it still does **not** establish. Nothing in
§1–§11 asserts a REST behavior beyond what §0 documents; where §0 could
not confirm a detail, the corresponding requirement says so explicitly
rather than guessing.

Format: Admin API review, then user story + EARS-style acceptance
criteria per requirement.

---

## 0. Admin API Review

### 0.1 Sources consulted

- **`openApi/Veracode Example.postman_collection.json`** — a real,
  Veracode-authored Postman collection with working requests, test
  scripts, and inline query-parameter descriptions for `Teams`, `Custom
  Roles`, `Business Units`, and `Users` against the actual Admin API. This
  is the highest-confidence source in this review — it is executable
  evidence of real request/response shapes, not documentation prose — and
  supersedes the weaker sources below wherever they conflict.
- [Identity REST API overview](https://docs.veracode.com/r/c_identity_intro) — base URL, resource list, pagination defaults, auth scheme.
- [Get team details with the REST API](https://docs.veracode.com/r/c_identity_team_info) — `GET /teams`, `GET /teams/{teamId}`.
- [Create a team](https://docs.veracode.com/r/c_identity_create_team) — referenced to confirm what fields a Team can carry (create is out of scope, but its request shape implies response fields).
- [`veracode-api-py`](https://github.com/veracode/veracode-api-py) (Veracode's own community Python API wrapper), `docs/users.md` / `docs/api.md` — documents concrete Teams method signatures, consistent with the Postman collection.

Several `docs.veracode.com` pages render their body via client-side
JavaScript and returned no extractable text to this review's tooling;
where that happened, the finding is sourced from search-result excerpts
and `veracode-api-py` instead, clearly marked in §0.3 as weaker evidence.
Everything the Postman collection actually exercises is now treated as
confirmed (§0.2); only what no source — including the collection —
demonstrates remains in §0.3, a checkpoint to verify against a live
account before finalizing that piece of code (tasks.md).

### 0.2 Confirmed

- Base URL: `https://api.veracode.com/api/authn/v2` (also recorded in
  AGENTS.md §3.3, and as the collection's `admin_base_url` variable).
  Same VERACODE-HMAC-SHA-256 authentication mechanism as every other
  Veracode API (AGENTS.md §3.1) — no new auth code needed.
- `GET /teams` — lists teams, **organization-wide** (for a credential with
  the Administrator role — the collection's `Teams` folder is explicitly
  documented as "for use by someone who has the Veracode role called
  'Administrator'"). Paginated via `page` and `size` query parameters
  (confirmed default page size 20).
- **`GET /teams/self` is a separate, distinct endpoint** — not a query
  parameter on `GET /teams` — returning only the teams the calling
  credential belongs to. This resolves what was previously an open
  question (org-wide vs. member-only listing is a choice of *endpoint*,
  not a flag): `list()`/`get_by_name()` (§1, §3) intentionally always call
  plain `GET /teams`, never `GET /teams/self`, since README's Background
  requires resolving *any* Team in the organization by name, not only
  ones the credential itself belongs to. `GET /teams/self` is confirmed
  to exist but is not used or exposed by this feature (§9).
- **`GET /teams` supports a `team_name` query parameter**, documented
  inline in the collection as "Filter by team containing name" — i.e. a
  substring/contains filter, not a guaranteed exact match. This
  supersedes the earlier "no server-side name filter" finding (previously
  in §0.3) and materially changes §3's design: `get_by_name()` can now
  narrow server-side via `team_name`, then confirm an exact match
  client-side — the same two-step pattern Target Management's
  `get_by_name` already uses
  ([target-management requirements §0.3](../target-management/requirements.md),
  §10.1), rather than a full unbounded scan.
- `GET /teams` also supports `only_manageable` ("Return only teams you
  can manage" — relevant to a Team Admin-scoped credential) and `deleted`
  ("Return teams that are soft deleted"), confirming Teams support
  soft-delete. Neither is required by any operation in README's Scope;
  both are confirmed to exist but are not exposed as `list()` parameters
  in this phase (§1.6) — the same "confirmed but out of scope" treatment
  [target-management requirements §0.2](../target-management/requirements.md)
  gives endpoints it doesn't implement.
- `GET /teams/{team_id}` — returns one team by ID. `team_id` is a
  hyphenated, UUID-shaped identifier (the collection's environment
  variable holding it is literally named `team_uuid`).
- **A team resource carries exactly `team_id` and `team_name`** — this is
  now strongly confirmed, not just "at least": every script in the
  collection that reads a team object (`Get teams`, `Get teams self`,
  `Get team by UUID`, and the `teams` array nested in `Get user by ID`'s
  response) reads only these two fields, and **`POST /teams` (create) —
  the strongest signal of what a Team fundamentally is — requires only
  `{"team_name": "..."}`**, with no `description`, no parent-Team
  reference, and no Business Unit at creation time.
- **Business Unit is confirmed as a separate resource** (`bu_id`,
  `bu_name`), and Teams are added *to* a Business Unit via `PUT
  /business_units/{bu_id}` with a `teams: [{"team_id": "..."}]` body —
  i.e. Business Unit holds a reference to Teams, not the reverse. This
  directly confirms §0.2's — now former §0.3 — finding that "Parent Team"
  (README's Team Model wording) has no real analog on the Team resource
  itself; the closest real relationship is Business Unit, and it points
  the opposite direction, is out of scope (README's Out of Scope), and is
  not modeled on `Team` (§5.2).
- `POST /teams` (create, out of scope) returns `201` with a body
  containing `team_id`; `DELETE /teams/{team_id}` (delete, out of scope)
  returns `200`, not `204`. Recorded for completeness even though Phase 1
  never calls either.
- Administrative Team operations (create/update/delete — all out of
  scope per README) require an Admin/Team Admin API role, per the
  collection's folder-level description. Read operations in this
  feature's scope (`GET /teams`, `GET /teams/{id}`) are not documented as
  requiring elevated privileges beyond a valid API credential.

### 0.3 Not independently confirmed (treated conservatively below)

- **Exact pagination metadata shape.** `page`/`size` as request query
  parameters, and the `_embedded.teams` response array, are confirmed.
  No test script in the collection ever reads a page-metadata object
  (e.g. total-pages/total-elements-style fields) — every script only
  iterates `response._embedded.teams`. The exact JSON key names and
  casing of that metadata (e.g. whether it matches Target Management's
  snake_case `total_pages`/`total_elements`, or uses different
  casing/names) remain unconfirmed by any source, including the
  collection.
- **Whether the `team_name` filter is case-sensitive, or matches
  substrings only, or also matches on other fields.** The collection's
  own description says "containing name," but the saved example request
  actually leaves `team_name` **disabled** and instead fetches up to
  `size=500` unfiltered results, filtering with a client-side
  `.includes(...)` check in its test script. A real Veracode-authored
  example choosing not to rely on the filter, and to re-check with a
  substring match itself, is informative — it suggests the filter alone
  isn't treated as sufficient for an exact lookup even by Veracode's own
  example — but it does not document the filter's precise matching
  algorithm.
- **Error response body shape.** Not confirmed, and not needed: per
  [specs/http-client design §4](../http-client/design.md#4-error-handling),
  `HttpClient`'s error translation is keyed entirely on HTTP status code,
  never on response body shape. Whatever error body the Admin API
  returns, the existing status-code-keyed exception hierarchy (§7)
  applies unchanged.

---

## 1. List Teams

**User story:** As an SDK consumer, I want to list Teams with pagination,
so I can page through every Team the API credential can see without
writing raw HTTP calls.

**Acceptance criteria:**

1.1. WHEN `client.teams.list()` is called with no arguments THEN THE
SYSTEM SHALL call `GET /teams` with no query parameters other than the
REST API's own defaults (`page=0`, `size=20`, per §0.2).

1.2. WHEN `client.teams.list(page=..., size=...)` is called THEN THE
SYSTEM SHALL forward each supplied value as the corresponding `GET /teams`
query parameter.

1.3. WHEN `GET /teams` responds 200 THEN THE SYSTEM SHALL return a typed
`TeamPage` containing the list of `Team` models and page metadata, built
from whatever page-metadata shape the response actually contains (§0.3 —
exact key names are confirmed against a live response during
implementation, not assumed here).

1.4. THE SYSTEM SHALL NOT aggregate multiple pages into one `list()` call.
One `list(...)` call always corresponds to exactly one `GET /teams`
request — same convention as
[target-management requirements §1.6](../target-management/requirements.md).

1.5. `list()` SHALL always call `GET /teams` (organization-wide, per
§0.2), and SHALL NEVER call `GET /teams/self`. Unlike the earlier version
of this requirement, this is no longer a hedge against an unconfirmed
access-control behavior — §0.2 confirms these are two distinct endpoints,
and README's Background requires resolving *any* Team in the
organization by name, not only ones the configured credential happens to
belong to. `GET /teams/self` is out of scope for this feature (§9.1);
nothing in this feature calls it.

1.6. WHEN `client.teams.list(team_name=...)` is called THEN THE SYSTEM
SHALL forward it as the `GET /teams` `team_name` query parameter (§0.2).
THE SYSTEM SHALL NOT treat a non-empty result as a confirmed exact match
— per §0.3, the filter is documented only as "containing name," so any
caller of `list(team_name=...)` (namely `get_by_name`, §3) must still
verify an exact match itself.

1.7. THE SYSTEM SHALL NOT expose `only_manageable` or `deleted` as
`list()` parameters in this phase, even though §0.2 confirms both exist
on `GET /teams`. Neither is required by any operation in README's Scope;
adding them now would be speculative surface with no current caller.

---

## 2. Get Team by ID

**User story:** As an SDK consumer, I want to fetch one Team by its ID, so
I can look up a specific Team's current state (e.g. to confirm a
previously resolved `team_id` still exists).

**Acceptance criteria:**

2.1. WHEN `client.teams.get(team_id)` is called THEN THE SYSTEM SHALL call
`GET /teams/{team_id}` with the given ID.

2.2. BEFORE calling `GET /teams/{team_id}`, IF `team_id` is empty or
blank THEN THE SYSTEM SHALL raise `TeamValidationError` (§7) without
making an HTTP call.

2.3. WHEN `GET /teams/{team_id}` responds 200 THEN THE SYSTEM SHALL return
a typed `Team` model built from the response body (§5).

2.4. WHEN `GET /teams/{team_id}` responds 404 THEN THE SYSTEM SHALL let
`VeracodeNotFoundError` (raised by the HTTP Client, per
[specs/http-client requirements §8.3](../http-client/requirements.md))
propagate unchanged — Team Management adds no ID-lookup-specific "not
found" exception, mirroring
[target-management requirements §2.3](../target-management/requirements.md).

---

## 3. Get Team by Name (resolution strategy)

**User story:** As an SDK consumer (typically a CI/CD pipeline that only
knows a Team's name), I want to resolve that name to a Team — and its
`team_id` — without hand-rolling list-then-filter logic myself.

**Acceptance criteria:**

3.1. WHEN `client.teams.get_by_name(name)` is called THEN THE SYSTEM
SHALL call `list(team_name=name)` (§1.6) to narrow server-side, then scan
the returned `Team` items for an exact `team_name` match. This mirrors
Target Management's `get_by_name`
([target-management requirements §10.1](../target-management/requirements.md)):
narrow via a confirmed filter, then confirm an exact match client-side,
rather than trusting the filter as exact (§0.3 — the Admin API's own
`team_name` filter is documented only as "containing name").

3.1.1. Whether the exact-match comparison in 3.1 is case-sensitive is an
SDK-side matching choice, not a behavior confirmed by the Admin API
review (§0) — no source in §0.1 documents how Veracode itself compares
Team names (e.g. whether two names differing only by case can coexist).
Absent that confirmation, THE SYSTEM SHALL default to a case-sensitive
comparison (the conservative choice: it never reports a match the
caller's exact input didn't specify) and this choice SHALL be documented
in code as an assumption, not presented as an Admin API rule. This is
revisited if a future review confirms Veracode's own case-folding
behavior for Team names.

3.2. BEFORE calling `list()`, IF `name` is empty or blank THEN THE SYSTEM
SHALL raise `TeamValidationError` (§7) without making an HTTP call.

3.3. IF no exact match is found on the first page and more pages remain
THEN THE SYSTEM SHALL request subsequent pages (same `team_name` filter,
incrementing `page`) until a match is found or every page has been
scanned. Because `team_name` already narrows the result set server-side
(§0.2), this scan is now expected to cover only Teams whose name contains
`name`, not the organization's entire Team list — a materially smaller
scan than this requirement previously specified, before the filter was
confirmed.

3.4. WHEN no Team matches `name` after every page is scanned THEN THE
SYSTEM SHALL raise `TeamNotFoundError` (§7). This is a deliberate
divergence from
[target-management requirements §10.1](../target-management/requirements.md)/
§10.3 (`get_by_name` there returns `None` on no match) — see design.md's
Architecture Decisions appendix for the rationale.

3.5. `get_by_name` SHALL NOT require any REST endpoint beyond `GET
/teams`, per README's "must never require additional Veracode endpoints."

3.6. THE SYSTEM SHALL NOT cap the number of pages scanned by
`get_by_name`. Even narrowed by `team_name` (§3.1), an organization with
many Teams sharing a common substring could still return several pages;
this remains a documented, accepted limitation (see design.md §13), not a
defect to silently work around — just a smaller one than before this
review's refinement.

---

## 4. Team Exists

**User story:** As an SDK consumer, I want a simple boolean check for
whether a Team name exists, so I don't have to catch an exception just to
answer a yes/no question in scripts that branch on it.

**Acceptance criteria:**

4.1. WHEN `client.teams.exists(name)` is called THEN THE SYSTEM SHALL call
`get_by_name(name)` (§3), return `True` if it returns a `Team`, and return
`False` — not propagate — if it raises `TeamNotFoundError`.

4.2. `exists` SHALL let any exception other than `TeamNotFoundError`
(e.g. `TeamValidationError`, any `VeracodeApiError` subclass) propagate
unchanged.

---

## 5. Typed models

**User story:** As an SDK consumer, I want Team data as a real Python
type, so I get attribute access and editor autocomplete instead of a raw
dict.

**Acceptance criteria:**

5.1. THE SYSTEM SHALL define a `Team` model with exactly the fields
confirmed in §0.2: `team_id: str`, `team_name: str`.

5.2. THE SYSTEM SHALL NOT model `description`, `parent team`, `business
unit`, or `members` on `Team` in this phase, per §0.3's findings and
README's Out of Scope (Business Units, User management). `Team.from_api`
SHALL ignore any additional keys present in the response body rather than
raising on their presence, so this feature keeps working unmodified if
the live API returns extra fields this phase doesn't model.

5.3. THE SYSTEM SHALL define a `TeamPage` model exposing at least
`items: list[Team]`, built from whatever page-metadata fields the live
`GET /teams` response actually contains (§0.3); the exact set of exposed
metadata fields is a design/implementation detail confirmed against a
live response (design.md, tasks.md), not fixed by this requirement.

5.4. THE SYSTEM SHALL define `Team` and `TeamPage` as typed models that
comply with the model rules in [AGENTS.md
§3](../../AGENTS.md#3-architecture) (models never perform HTTP requests,
contain business logic, or depend on the HTTP Client) — same rule Target
Management's models follow.

---

## 6. Client-side validation

**User story:** As an SDK consumer, I want an obviously invalid lookup
parameter rejected immediately, so I don't make a pointless round trip to
Veracode.

**Acceptance criteria:**

6.1. THE SYSTEM SHALL perform the checks in 2.2 and 3.2 before sending
any HTTP request.

6.2. THE SYSTEM SHALL NOT perform any other client-side validation — in
particular, THE SYSTEM SHALL NOT guess at or enforce a format for
`team_id` (e.g. a UUID pattern) or a length limit for `name`, since
neither is confirmed by §0. Client-side validation strictly mirrors what
this review actually established, per README's "must never replace
server-side validation."

---

## 7. Error handling

**User story:** As an SDK consumer, I want a clear distinction between "my
lookup parameter was invalid before any request was sent" and "the Team
genuinely doesn't exist" and "Veracode rejected the request," so I can
handle each case appropriately.

**Acceptance criteria:**

7.1. THE SYSTEM SHALL define `TeamValidationError(VeracodeSDKError)` — not
a subclass of `VeracodeApiError` — for the checks in §6, since no HTTP
request was made when it is raised.

7.2. THE SYSTEM SHALL define `TeamNotFoundError(VeracodeSDKError)` — also
not a subclass of `VeracodeApiError` — raised by `get_by_name` (§3.4) when
no Team matches the given name. This is distinct from
`VeracodeNotFoundError` (raised by the HTTP Client for an actual REST
404, per [specs/http-client requirements
§8.3](../http-client/requirements.md)): reaching "no match" here means
every underlying `GET /teams` call **succeeded** — it simply never
returned a matching name — so no REST call ever failed.

7.3. Both exceptions SHALL follow the naming/subclassing convention
established by
[target-management design §2.2](../target-management/design.md#22-srcveracode_dastexceptionspy)
(`<Resource><Reason>Error`, subclassing `VeracodeSDKError` directly) —
reused here, not reinvented, per this feature's Purpose of being a
reusable building block for future services too.

7.4. THE SYSTEM SHALL NOT define any other new exception type. Every
failure that occurs after an HTTP request is sent (401, 403, 404 from
`get`, other 4xx, 5xx, connection errors, timeouts) SHALL surface as
whichever exception [specs/http-client requirements
§8](../http-client/requirements.md) already defines, unmodified and
unwrapped — Team Management never wraps or replaces an HTTP exception
(README's Error Handling section).

7.5. THE SYSTEM SHALL NOT catch and swallow any exception raised by the
HTTP Client, except for the single documented `TeamNotFoundError` →
`False` translation inside `exists` (§4.1).

---

## 8. Logging

**User story:** As an SDK maintainer, I want Team lookups to be
traceable in CI/CD logs, so a pipeline failure caused by an unresolved
Team name is diagnosable without re-running with a debugger.

**Acceptance criteria:**

8.1. WHEN `list()` completes successfully THEN THE SYSTEM SHALL emit an
INFO-level log stating how many Teams were returned on that page.

8.2. WHEN `get(team_id)` completes successfully THEN THE SYSTEM SHALL
emit an INFO-level log naming the requested `team_id`.

8.3. WHEN `get_by_name(name)` resolves successfully THEN THE SYSTEM SHALL
emit an INFO-level log naming the requested `name` and the resolved
`team_id`. WHEN it raises `TeamNotFoundError` THEN THE SYSTEM SHALL emit
an INFO-level (not ERROR — this is an expected, non-exceptional outcome
for `exists()` callers) log naming the requested `name` and stating that
no match was found.

8.4. THE SYSTEM SHALL NOT log full `Team` payloads or any field beyond
`team_id`/`team_name`, and SHALL NOT log HTTP-level details already owned
by the shared HTTP Client (headers, auth signatures, request/response
bodies) — per README's Logging section and
[AGENTS.md §6.2](../../AGENTS.md#62-business-data).

8.5. THE SYSTEM SHALL NOT re-implement HTTP request/response logging;
that responsibility belongs entirely to the HTTP Client, per
[specs/http-client requirements §9.6](../http-client/requirements.md).

---

## 9. Boundaries (non-goals for this feature)

**User story:** As the SDK architect, I want Team Management strictly
scoped to Team discovery, so unrelated Admin API resources don't creep in.

**Acceptance criteria:**

9.1. THE SYSTEM SHALL NOT implement Team creation, update, or deletion;
User management; Roles; Business Units; or Organization management, per
README's Out of Scope.

9.2. THE SYSTEM SHALL comply with the service-layer rules in [AGENTS.md
§3](../../AGENTS.md#3-architecture): every REST call goes through an
injected `HttpClient` instance, not `requests` directly, `auth.py`, or
`config.py`.

9.3. `TeamService` itself SHALL NOT construct an `HttpClient` other than
the one it is given; it never reads environment variables or calls
`get_veracode_auth()` itself. THE SYSTEM SHALL NOT hardcode the Admin API
base URL inside `client.py` — ownership of that value belongs to the Team
Management service, same convention as
[target-management requirements §11.4](../target-management/requirements.md).

9.4. THE SYSTEM SHALL NOT implement pagination-aggregation beyond the
bounded, single-purpose page scan in §3.3, caching, or retry logic beyond
what the HTTP Client already provides.

---

## 10. Public interface and reuse

**User story:** As an SDK consumer, I want `client.teams` alongside
`client.targets`, so resolving a Team and creating a Target read as one
consistent SDK. As a maintainer of a future SDK feature, I want Team
Management usable without depending on Target Management, so it's a true
shared building block, not a Target-only helper in disguise.

**Acceptance criteria:**

10.1. THE SYSTEM SHALL expose a `TeamService` class whose public methods
are exactly `list`, `get`, `get_by_name`, and `exists`, matching README's
Scope and Public SDK API.

10.2. THE SYSTEM SHALL wire `TeamService` onto `VeracodeClient` as
`client.teams`, using `get_veracode_auth()` (the same shared auth
provider Target Management uses) and the Admin API base URL owned by the
Team Management service, per [AGENTS.md
§9](../../AGENTS.md#9-desired-public-api). This is the first feature to
give `VeracodeClient` a second Service and a second Veracode API base
URL — validating, for the first time, the multi-domain design AGENTS.md
§3.1–§3.3 already anticipated.

10.3. `TeamService` SHALL NOT import, reference, or depend on
`TargetsService` or any Target Management module, per README's
"Team Management module is intentionally independent from Target
Management." Any coupling between the two happens only in consumer code
(README's "Relationship with Target Management" workflow), never inside
either service.

10.4. THE SYSTEM SHALL comply with the code conventions in [AGENTS.md
§7](../../AGENTS.md#7-code-conventions) (complete type hints, Google-style
docstrings) and the Platform Agnostic and Stateless principles in
[AGENTS.md §5](../../AGENTS.md#5-design-principles): `TeamService` holds
only its `HttpClient` instance; no Team data is cached or retained
between calls.

---

## 11. Testability

**User story:** As a maintainer, I want to verify request shaping,
response parsing, and the multi-page `get_by_name` scan without a real
Veracode account.

**Acceptance criteria:**

11.1. THE SYSTEM SHALL allow every `TeamService` method to be tested by
constructing it with a fake/stub `HttpClient` returning prepared
`HttpResponse` values, with no real network access, environment
variables, or Veracode credentials required — same pattern as
[target-management requirements
§13.1](../target-management/requirements.md).

11.2. THE SYSTEM SHALL NOT require a new third-party mocking/HTTP-fixture
dependency beyond what [specs/http-client requirements
§12](../http-client/requirements.md) already establishes.

11.3. THE SYSTEM SHALL allow `get_by_name`'s multi-page scan (§3.3) and
`exists`'s `TeamNotFoundError`-to-`False` translation (§4.1) to be
exercised deterministically by stubbing successive `HttpClient.get`
return values.
