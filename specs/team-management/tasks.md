# Tasks — Team Management

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Do not start implementation until this specification is reviewed and
approved.

---

- [ ] 1. Pre-implementation: confirm Admin API details left open by
      requirements.md §0.3
  - [x] ~~Confirm whether a server-side name filter exists on `GET
        /teams`~~ — resolved: the Veracode-authored Postman collection
        (`openApi/Veracode Example.postman_collection.json`) confirms a
        `team_name` "containing name" filter (requirements.md §0.2).
  - [x] ~~Confirm whether `GET /teams`/`GET /teams/{id}` return any field
        beyond `team_id`/`team_name`~~ — resolved: the collection's
        `POST /teams` (create) body requires only `team_name`, and every
        script that reads a team object reads only `team_id`/`team_name`
        (requirements.md §0.2). No other field is modeled.
  - [ ] 1.1 Against a live Veracode account (or a captured real response),
        confirm the exact JSON key names/casing of `GET /teams`'s
        page-metadata object — still open; no test script in the
        collection reads this object (requirements.md §0.3)
  - [ ] 1.2 Confirm the `team_name` filter's exact matching algorithm
        (case sensitivity; substring-only vs. also matching other
        fields) against a live account — still open (requirements.md
        §0.3); does not block implementation, since `get_by_name` never
        trusts the filter as exact regardless (requirements.md §3.1)
  - [ ] 1.3 Record any further findings as an update to requirements.md §0
        before starting task 2
  - _Requirements: §0.3_

- [ ] 2. `Team` model (`models/team.py`)
  - [ ] 2.1 Create `src/veracode_dast/models/` package (`__init__.py`) if
        not already created by Target Management
  - [ ] 2.2 Implement `Team` as a frozen dataclass: `team_id: str`,
        `team_name: str`
  - [ ] 2.3 Implement `Team.from_api(data: dict) -> Team`, reading only
        `team_id`/`team_name`, ignoring any other key present
  - [ ] 2.4 Add Google-style docstrings and full type hints
  - _Requirements: 2.3, 3.1, 5.1, 5.2, 5.4_

- [ ] 3. `TeamPage` model (`models/team.py`)
  - [ ] 3.1 Implement `TeamPage` as a frozen dataclass with `items:
        list[Team]`; add page-metadata attributes only once task 1.1
        confirms their real JSON key names — do NOT assume `TargetPage`'s
        attribute names (`page_number`/`page_size`/`total_pages`/
        `total_elements`) carry over to the Admin API
  - [ ] 3.2 Implement `TeamPage.from_api(data: dict) -> TeamPage`, reading
        `_embedded.teams` and whatever page-metadata keys task 1.1 found
  - [ ] 3.3 Add Google-style docstrings and full type hints
  - _Requirements: 1.3, 5.3, 5.4_

- [ ] 4. Exception additions (`exceptions.py`)
  - [ ] 4.1 Implement `TeamValidationError(VeracodeSDKError)` with a
        `rule` attribute; confirm it is NOT a subclass of
        `VeracodeApiError`
  - [ ] 4.2 Implement `TeamNotFoundError(VeracodeSDKError)` with a `name`
        attribute; confirm it is NOT a subclass of `VeracodeApiError` or
        `VeracodeNotFoundError`
  - [ ] 4.3 Confirm both follow the naming convention in
        [target-management design
        §2.2](../target-management/design.md#22-srcveracode_dastexceptionspy)
        (prefixed by resource name, subclassing `VeracodeSDKError`
        directly)
  - [ ] 4.4 Add Google-style docstrings and full type hints
  - _Requirements: 7.1, 7.2, 7.3_

- [ ] 5. `TeamService` construction (`services/teams.py`)
  - [ ] 5.1 Create `src/veracode_dast/services/` package (`__init__.py`)
        if not already created by Target Management
  - [ ] 5.2 Define `ADMIN_API_BASE_URL` and `_DEFAULT_PAGE_SIZE` as module
        constants in `services/teams.py` — the base URL literal lives
        here, not in `client.py` (task 9)
  - [ ] 5.3 Implement `TeamService.__init__(self, http_client:
        HttpClient)`, storing the client and a module logger; no other
        state; confirm `TeamService` never constructs an `HttpClient`
        itself and never imports `services/targets.py`
  - [ ] 5.4 Implement a private helper raising `TeamValidationError` for a
        blank string argument, reused by `get` and `get_by_name`
  - [ ] 5.5 Add Google-style docstrings and full type hints
  - _Requirements: 2.2, 3.2, 6.1, 6.2, 9.2, 9.3, 10.4_

- [ ] 6. `TeamService.list`
  - [ ] 6.1 Implement `list(*, page=0, size=_DEFAULT_PAGE_SIZE,
        team_name=None) -> TeamPage`
  - [ ] 6.2 Build the `GET /teams` query parameters from only the
        supplied arguments (`page`, `size`, and `team_name` only when
        not `None`), matching §0.2's REST defaults
  - [ ] 6.3 Build `TeamPage` via `TeamPage.from_api`
  - [ ] 6.4 Emit the `INFO` log from design.md §7 on success
  - [ ] 6.5 Add Google-style docstring and full type hints; document
        that `team_name` is a "containing name" filter, not a guaranteed
        exact match (requirements.md §1.6)
  - [ ] 6.6 Confirm `list()` never calls `GET /teams/self` (requirements.md
        §1.5)
  - _Requirements: 1.1–1.7, 8.1_

- [ ] 7. `TeamService.get`
  - [ ] 7.1 Implement `get(team_id: str) -> Team`
  - [ ] 7.2 Run the blank-string check (task 5.4) before calling `GET
        /teams/{team_id}`
  - [ ] 7.3 Build `Team` via `Team.from_api`; confirm
        `VeracodeNotFoundError` from the HTTP Client is not caught
  - [ ] 7.4 Emit the `INFO` log from design.md §7 on success
  - [ ] 7.5 Add Google-style docstring and full type hints
  - _Requirements: 2.1–2.4, 8.2_

- [ ] 8. `TeamService.get_by_name` and `TeamService.exists`
  - [ ] 8.1 Implement `get_by_name(name: str) -> Team`
  - [ ] 8.2 Run the blank-string check (task 5.4) before calling `list`
  - [ ] 8.3 Call `list(team_name=name)` page by page (same `size` and
        `team_name` filter, incrementing `page`), scanning `items` for an
        exact `team_name` match (case-sensitive by default per
        requirements.md §3.1.1 — an SDK-side assumption, documented in
        code as such, not an Admin API-confirmed rule) — never trust the
        `team_name` filter alone as an exact match, since it is only
        confirmed as "containing name" (requirements.md §0.2/§0.3) —
        until an exact match is found or every page has been scanned
  - [ ] 8.4 Raise `TeamNotFoundError(name)` when no page contains an exact
        match
  - [ ] 8.5 Emit the `INFO` logs from design.md §7 for both the
        match-found and no-match outcomes
  - [ ] 8.6 Implement `exists(name: str) -> bool`: return `True` if
        `get_by_name` returns a `Team`; catch only `TeamNotFoundError` and
        return `False`; let every other exception propagate
  - [ ] 8.7 Add Google-style docstrings and full type hints
  - _Requirements: 3.1–3.6, 4.1–4.2, 8.3_

- [ ] 9. `VeracodeClient` (`client.py`)
  - [ ] 9.1 Import `ADMIN_API_BASE_URL` and `TeamService` from
        `veracode_dast.services.teams`
  - [ ] 9.2 Extend `VeracodeClient.__init__`: construct a second
        `HttpClient` with `ADMIN_API_BASE_URL` and the same `auth`
        instance already obtained for `client.targets`; construct
        `TeamService` with it; assign it to `self.teams`
  - [ ] 9.3 Confirm the existing `client.targets` wiring is unchanged, and
        that `client.py` still contains no Veracode API base-URL literal
        of its own — only the two constants imported from
        `services/targets.py` and `services/teams.py`
  - [ ] 9.4 Add/update Google-style docstring and full type hints
  - _Requirements: 9.3, 10.2_

- [ ] 10. Unit tests — models (`tests/models/test_team.py`)
  - [ ] 10.1 `Team.from_api` round-trips a fixture matching the confirmed
        response shape; confirm an unrecognized extra key in the fixture
        does not raise
  - [ ] 10.2 `TeamPage.from_api` round-trips a `_embedded.teams` +
        page-metadata fixture (using the mapping confirmed in task 1.1)
  - _Requirements: 5.1–5.4_

- [ ] 11. Unit tests — service (`tests/services/test_teams.py`)
  - [ ] 11.1 Stub/fake `HttpClient` returning prepared `HttpResponse`
        values or raising prepared `VeracodeApiError` subclasses
  - [ ] 11.2 `list()`: default `page`/`size` match §0.2; supplied
        `page`/`size`/`team_name` are forwarded; confirm `team_name` is
        omitted from the query entirely when not supplied
  - [ ] 11.3 `get()`: blank `team_id` → `TeamValidationError`, stub never
        called; 200 → `Team`; 404 → `VeracodeNotFoundError` propagates
  - [ ] 11.4 `get_by_name()`: blank `name` → `TeamValidationError`, stub
        never called; confirm `list` is called with `team_name=name`;
        exact match on first page; a fixture page containing a
        substring-only match (not exact) to confirm it is correctly
        rejected and scanning continues; match requiring a second page
        (stubbed multi-page sequence); no match across all pages →
        `TeamNotFoundError`
  - [ ] 11.5 `exists()`: match found → `True`; `TeamNotFoundError` → `False`;
        a stubbed `VeracodeApiError` from `get_by_name` propagates instead
        of being swallowed
  - [ ] 11.6 `caplog` assertion: no captured log record contains any field
        beyond `team_id`/`team_name`/`name`
  - _Requirements: 1.1–1.7, 2.1–2.4, 3.1–3.6, 4.1–4.2, 6.1–6.2, 7.1–7.5,
    8.1–8.5, 11.1–11.3_

- [ ] 12. Example
  - [ ] 12.1 Add `examples/team_management_example.py` using stdlib
        `argparse` to accept a Team name as a command-line argument —
        never hardcoded, never read from the environment by the example
        itself, matching
        [target-management design
        §10](../target-management/design.md#10-file-layout-introduced-by-this-feature)
  - [ ] 12.2 Script body: construct `VeracodeClient()`, call
        `get_by_name(...)` with the parsed argument, print the resolved
        `Team`; if not found, let `TeamNotFoundError` surface as a clear
        script failure rather than catching and hiding it
  - [ ] 12.3 Confirm the script contains no Azure DevOps-specific code and
        no dependency on `TargetsService`
  - _AGENTS.md Definition of Done_

- [ ] 13. Quality gates
  - [ ] 13.1 `ruff check` passes with no new warnings
  - [ ] 13.2 `mypy` passes in strict mode for `models/team.py`,
        `services/teams.py`, the extended `client.py`, and the extended
        `exceptions.py`
  - [ ] 13.3 `pytest` passes for `test_team.py` and `test_teams.py`
  - _AGENTS.md Definition of Done_

---

## Dependency order

1 (Admin API confirmation) should complete, or its findings be explicitly
accepted as still-open, before 2–3 (models) are finalized — the exact
`TeamPage` field mapping depends on it. 2–4 (models + exceptions) have no
dependency on each other and can be implemented in any order, but must
precede 5–9 (service + client), which import them. 5 must precede 6–8
(they share the validation helper and constructor). 8 (`get_by_name`,
`exists`) calls `list` (6) directly, so it must come after it. 9 depends
on 5–8 being complete. 10–11 depend on their respective implementation
tasks; 12 depends on 9; 13 depends on everything above.

## Explicitly not part of these tasks

Per [requirements.md §9](requirements.md#9-boundaries-non-goals-for-this-feature):
no Team creation, update, or deletion; no User management, Roles,
Business Units, or Organization management; no direct `requests` import
or HMAC logic inside this feature; no dependency on
`services/targets.py`; no pagination cap, caching, or retry logic beyond
the HTTP Client's own.

The following were identified as valuable but are explicitly deferred
rather than part of this feature's tasks (see [design.md
§13](design.md#13-additional-architectural-recommendations-not-implemented-here)):
a page cap for `get_by_name`'s multi-page scan (now narrowed by the
confirmed `team_name` filter, but still uncapped — requirements.md §3.6),
to be revisited only if it proves slow in practice; and skipping the
client-side exact-match check entirely, to be revisited only if task 1.2
confirms the `team_name` filter is already an exact match.
