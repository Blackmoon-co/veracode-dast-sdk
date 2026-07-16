# Tasks — Target Management

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Do not start implementation until this specification is reviewed and
approved.

---

- [ ] 1. Enumerations (`models/target.py`)
  - [ ] 1.1 Create `src/veracode_dast/models/` package (`__init__.py`) —
        first content in this previously-empty directory
  - [ ] 1.2 Implement `TargetType(str, Enum)`: `WEB_APP`, `API`
  - [ ] 1.3 Implement `ScanType(str, Enum)`: `QUICK`, `FULL`, `ENTERPRISE`
  - [ ] 1.4 Implement `Protocol(str, Enum)`: `HTTP`, `HTTPS`
  - [ ] 1.5 Implement `TargetSortBy(str, Enum)`: `NAME`, `URL`,
        `TARGET_TYPE`, `LAST_SCAN`, `STATUS`, `MAX_CVSS` (values `name`,
        `url`, `target_type`, `last_scan`, `status`, `max_cvss`)
  - [ ] 1.6 Implement `SortOrder(str, Enum)`: `ASC`, `DESC` (values `asc`,
        `desc`)
  - [ ] 1.7 Implement `TargetStatus(str, Enum)`: `RUNNING`, `STOPPING`,
        `STOPPED`, `FINISHED`, `FAILED`
  - [ ] 1.8 Do NOT implement a `ProblemError.code` enum (design.md §5)
  - [ ] 1.9 Add Google-style docstrings and full type hints
  - _Requirements: 6.1–6.7_

- [ ] 2. `Target` model
  - [ ] 2.1 Implement `Target` as a frozen dataclass with the fields in
        design.md §2.1 (required fields matching OpenAPI `Target.required`
        exactly; optional fields default to `None`)
  - [ ] 2.2 Implement `Target.from_api(data: dict) -> Target`
  - [ ] 2.3 Add Google-style docstrings and full type hints
  - _Requirements: 2.2, 3.9, 4.4, 6.8_

- [ ] 3. `TargetCreate` model
  - [ ] 3.1 Implement `TargetCreate` as a frozen dataclass: required
        `name`, `url`, `protocol`, `target_type`, `scan_type`,
        `authorized_to_scan`, `is_sec_lead_only` (no defaults); optional
        `api_specification_file_url`, `description`, `teams`
  - [ ] 3.2 Implement `TargetCreate.to_api() -> dict`
  - [ ] 3.3 Add Google-style docstrings and full type hints
  - _Requirements: 3.1–3.4, 6.8_

- [ ] 4. `TargetUpdate` model
  - [ ] 4.1 Define the private `_UNSET` sentinel
  - [ ] 4.2 Implement `TargetUpdate` as a frozen dataclass: `name`,
        `protocol`, `url`, `api_specification_file_url`, `description`,
        `teams`, all defaulting to `_UNSET`
  - [ ] 4.3 Implement `TargetUpdate.to_api() -> dict` returning only
        explicitly-set fields, preserving an explicit `None` (e.g.
        `teams=None`) as JSON `null` rather than omitting it
  - [ ] 4.4 Confirm `target_type`/`scan_type`/`is_sec_lead_only`/
        `authorized_to_scan` are NOT fields on this class
  - [ ] 4.5 Add Google-style docstrings and full type hints
  - _Requirements: 4.1–4.3, 6.8_

- [ ] 5. `TargetPage` model
  - [ ] 5.1 Implement `TargetPage` as a frozen dataclass: `items:
        list[Target]`, `page_number`, `page_size`, `total_pages`,
        `total_elements`
  - [ ] 5.2 Implement `TargetPage.from_api(data: dict) -> TargetPage`,
        reading `_embedded.targets` and `page.{number,size,total_pages,
        total_elements}`; do NOT read or expose `_links`
  - [ ] 5.3 Add Google-style docstrings and full type hints
  - _Requirements: 1.4, 1.5, 6.8_

- [ ] 6. Exception additions (`exceptions.py`)
  - [ ] 6.1 Implement `TargetValidationError(VeracodeSDKError)` with a
        `rule` attribute; confirm it is NOT a subclass of
        `VeracodeApiError`
  - [ ] 6.2 Implement `TargetNotFoundError(VeracodeSDKError)` with a
        `name` attribute; confirm it is NOT a subclass of
        `VeracodeApiError` or `VeracodeNotFoundError`
  - [ ] 6.3 Confirm both follow the naming convention in design.md §2.2
        (prefixed by resource name, subclassing `VeracodeSDKError`
        directly)
  - [ ] 6.4 Add Google-style docstrings and full type hints
  - _Requirements: 8.1, 8.2, 8.5_

- [ ] 7. `TargetsService` construction and `create`/`update` validation
  - [ ] 7.1 Create `src/veracode_dast/services/` package (`__init__.py`)
        — first content in this previously-empty directory
  - [ ] 7.2 Define `TARGET_CONFIGURATION_SERVICE_BASE_URL` as a module
        constant in `services/targets.py`
        (`"https://api.veracode.com/dae/api/tcs-api/api/v1"`) — the base
        URL literal lives here, not in `client.py` (task 16)
  - [ ] 7.3 Implement `TargetsService.__init__(self, http_client:
        HttpClient)`, storing the client and a module logger; no other
        state; confirm `TargetsService` never constructs an `HttpClient`
        itself
  - [ ] 7.4 Implement the three conditional checks as private helpers:
        API target requires `api_specification_file_url`; `is_sec_lead_only`/
        `teams` mutual-exclusion/requirement; `teams` length <= 1 — each
        raising `TargetValidationError` with a distinct `rule` value
  - [ ] 7.5 Confirm no HTTP call is made before every applicable check
        passes
  - [ ] 7.6 Add Google-style docstrings and full type hints
  - _Requirements: 3.5–3.7, 4.5, 7.1–7.3, 8.1, 11.4, 12.5_

- [ ] 8. `TargetsService.list`
  - [ ] 8.1 Implement `list(*, page=0, limit=10, sort_by=TargetSortBy.NAME,
        sort_order=SortOrder.ASC, name=None, url=None, search_term=None,
        target_type=None) -> TargetPage`
  - [ ] 8.2 Build the `GET /targets` query parameters from only the
        supplied arguments, matching §0.3's REST defaults exactly
  - [ ] 8.3 Build `TargetPage` via `TargetPage.from_api`
  - [ ] 8.4 Add Google-style docstring and full type hints
  - _Requirements: 1.1–1.6_

- [ ] 9. `TargetsService.get`
  - [ ] 9.1 Implement `get(target_id: str) -> Target`
  - [ ] 9.2 Call `GET /targets/{target_id}`; build `Target` via
        `Target.from_api`
  - [ ] 9.3 Confirm `VeracodeNotFoundError` from the HTTP Client is not
        caught
  - [ ] 9.4 Add Google-style docstring and full type hints
  - _Requirements: 2.1–2.3_

- [ ] 10. `TargetsService.create`
  - [ ] 10.1 Implement `create(target: TargetCreate) -> Target`
  - [ ] 10.2 Run the validations from task 7 before calling `POST /targets`
  - [ ] 10.3 Call `POST /targets` with `target.to_api()`; build `Target`
        from the 201 response
  - [ ] 10.4 Emit the `INFO` log from design.md §7 on success
  - [ ] 10.5 Add Google-style docstring and full type hints
  - _Requirements: 3.1–3.9, 9.1_

- [ ] 11. `TargetsService.update`
  - [ ] 11.1 Implement `update(target_id: str, target: TargetUpdate) ->
        Target`
  - [ ] 11.2 Run the `teams` length validation from task 7 if `teams` is
        explicitly set
  - [ ] 11.3 Call `PUT /targets/{target_id}` with `target.to_api()`; build
        `Target` from the 200 response
  - [ ] 11.4 Emit the `INFO` log from design.md §7 on success
  - [ ] 11.5 Add Google-style docstring and full type hints
  - _Requirements: 4.1–4.5, 9.1_

- [ ] 12. `TargetsService.delete`
  - [ ] 12.1 Implement `delete(target_id: str) -> None`
  - [ ] 12.2 Call `DELETE /targets/{target_id}`; confirm `VeracodeNotFoundError`
        propagates unchanged on 404
  - [ ] 12.3 Emit the `INFO` log from design.md §7 on success
  - [ ] 12.4 Add Google-style docstring and full type hints
  - _Requirements: 5.1–5.3, 9.1_

- [ ] 13. `TargetsService.get_by_name`
  - [ ] 13.1 Implement `get_by_name(name: str) -> Target | None`
  - [ ] 13.2 Call `list(name=name)`; scan `items` for an exact,
        case-sensitive `name` match
  - [ ] 13.3 If no match on the first page and `total_pages > 1`, request
        subsequent pages (same `name` filter) until a match is found or
        pages are exhausted
  - [ ] 13.4 Return `None` (never raise) when no target matches
  - [ ] 13.5 Add Google-style docstring and full type hints
  - _Requirements: 10.1–10.3_

- [ ] 14. `TargetsService.exists`
  - [ ] 14.1 Implement `exists(name: str) -> bool` as
        `get_by_name(name) is not None`
  - [ ] 14.2 Add Google-style docstring and full type hints
  - _Requirements: 10.4_

- [ ] 15. `TargetsService.ensure`
  - [ ] 15.1 Implement `ensure(target: TargetCreate) -> Target`
  - [ ] 15.2 Call `get_by_name(target.name)` first; if found, return it
        unchanged and log the "already exists" message (design.md §7);
        do NOT call `create` or `update`
  - [ ] 15.3 If not found, call `create(target)`, log the "created by
        ensure" message (design.md §7, requirements.md §9.2), and return
        its result
  - [ ] 15.4 Add Google-style docstring and full type hints
  - _Requirements: 10.5–10.7, 9.2_

- [ ] 16. `TargetsService.update_by_name`
  - [ ] 16.1 Implement `update_by_name(name: str, target: TargetUpdate) ->
        Target`
  - [ ] 16.2 Call `get_by_name(name)` first; if found, call
        `update(found.target_id, target)` and return its result
  - [ ] 16.3 If not found, raise `TargetNotFoundError(name)` and confirm
        no `update`/`PUT` call is made
  - [ ] 16.4 Add Google-style docstring and full type hints
  - _Requirements: 4.6, 10.8–10.11_

- [ ] 17. `VeracodeClient` (`client.py`)
  - [ ] 17.1 Import `TARGET_CONFIGURATION_SERVICE_BASE_URL` and
        `TargetsService` from `veracode_dast.services.targets`
  - [ ] 17.2 Implement `VeracodeClient.__init__`: call
        `get_veracode_auth()`, construct `HttpClient` with the imported
        base-URL constant and the auth provider, construct
        `TargetsService` with that `HttpClient`, assign it to
        `self.targets`
  - [ ] 17.3 Confirm `client.py` contains no Veracode API base-URL
        literal of its own — the only base URL in this task's code is the
        constant imported from `services/targets.py` (task 7.2)
  - [ ] 17.4 Add Google-style docstring and full type hints
  - _Requirements: 11.4, 12.1, 12.2_

- [ ] 18. Unit tests — models (`tests/models/test_target.py`)
  - [ ] 18.1 `Target.from_api` round-trips a fixture matching the OpenAPI
        `Target` example
  - [ ] 18.2 `TargetCreate.to_api` produces the expected request body,
        omitting unset optional fields
  - [ ] 18.3 `TargetUpdate.to_api`: unset fields absent; explicitly-set
        fields (including explicit `None` for `teams`) present
  - [ ] 18.4 `TargetPage.from_api` round-trips a fixture matching the
        OpenAPI `PagedTargets` example; confirm no attribute exposes
        `_links`
  - _Requirements: 6.8, 1.5_

- [ ] 19. Unit tests — service (`tests/services/test_targets.py`)
  - [ ] 19.1 Stub/fake `HttpClient` returning prepared `HttpResponse`
        values or raising prepared `VeracodeApiError` subclasses
  - [ ] 19.2 `list()`: default query parameters match §0.3; every
        supplied argument is forwarded
  - [ ] 19.3 `get()`: 200 → `Target`; 404 → `VeracodeNotFoundError`
        propagates
  - [ ] 19.4 `create()`: valid input → correct body + `Target`; each of
        the three conditional-validation failures raises
        `TargetValidationError` with no call to the stub; a 400/501
        response propagates as `VeracodeApiError`
  - [ ] 19.5 `update()`: only explicitly-set fields appear in the request
        body; `teams=None` sends `null`; >1 team raises
        `TargetValidationError` before any call
  - [ ] 19.6 `delete()`: 204 → `None`; 404 → `VeracodeNotFoundError`
        propagates
  - [ ] 19.7 `get_by_name()`: match on first page; match requiring a
        second page; no match anywhere → `None`, no exception raised
  - [ ] 19.8 `exists()`: delegates to `get_by_name`
  - [ ] 19.9 `ensure()`: existing target found → returned as-is, `post`
        never called; not found → `create` called, result returned;
        confirm `update` is never called by `ensure`
  - [ ] 19.10 `update_by_name()`: match found → `update` called with the
        matched `target_id`, result returned; no match →
        `TargetNotFoundError` raised, stub's `put` never called
  - [ ] 19.11 `caplog` assertion: no captured log record from this
        feature contains `url`, `description`, or `teams` values used in
        the test
  - _Requirements: 1.1–1.6, 2.1–2.3, 3.1–3.9, 4.1–4.6, 5.1–5.3, 7.1–7.3,
    8.1–8.5, 9.1–9.4, 10.1–10.11, 13.1–13.3_

- [ ] 20. Example
  - [ ] 20.1 Add `examples/target_management_example.py` using stdlib
        `argparse` to accept target business data (`--name`, `--url`,
        `--protocol`, `--target-type`, `--scan-type`, `--teams`, etc.) as
        command-line arguments — never hardcoded, never read from the
        environment by the example itself (design.md §10)
  - [ ] 20.2 Script body: construct `VeracodeClient()`, call
        `ensure(TargetCreate(...))` built from the parsed arguments,
        `update_by_name(...)` to change one field, then `delete(...)`
        using the resulting `target_id` — a practical sequence
        mirroring an Azure DevOps pipeline's provision/update/teardown
        steps, printing each typed result
  - [ ] 20.3 Confirm the script contains no Azure DevOps-specific code —
        it is a plain Python script; only the future pipeline template
        (out of scope for this feature) decides how its arguments are
        populated
  - _AGENTS.md Definition of Done_

- [ ] 21. Quality gates
  - [ ] 21.1 `ruff check` passes with no new warnings
  - [ ] 21.2 `mypy` passes in strict mode for `models/target.py`,
        `services/targets.py`, the extended `client.py`, and the extended
        `exceptions.py`
  - [ ] 21.3 `pytest` passes for `test_target.py` and `test_targets.py`
  - _AGENTS.md Definition of Done_

---

## Dependency order

1–6 (models + exceptions) have no dependency on each other beyond shared
enums and can be implemented in any order, but must precede 7–17 (service
+ client), which import them. 7 must precede 8–16 (they share the
validation helpers and constructor). 16 (`update_by_name`) calls
`get_by_name` (13) and `update` (11) directly, so it must come after
both. 17 depends on 7–16 being complete (it wires the finished
`TargetsService`). 18–19 depend on their respective implementation
tasks; 20 depends on 17; 21 depends on everything above.

## Explicitly not part of these tasks

Per [requirements.md §11](requirements.md#11-boundaries-non-goals-for-this-feature):
no Target Configuration, Analysis Profiles, Scanner Configuration,
Scanner Variables, Authentication Configuration, Analysis/scan execution,
Reports, Discovered Targets, ISM Gateways, or Schedules; no
`getTargetApiSpec`/`uploadTargetApiSpec`/`downloadTargetApiSpecContents`/
`linkTarget`/`unlinkTarget`; no direct `requests` import or HMAC logic
inside this feature; no pagination-aggregation, caching, or retry logic
beyond the HTTP Client's own (the bounded scan in task 13.3 is the one
exception, and it is not a general-purpose pagination helper).

The following were identified as valuable but are explicitly deferred
rather than part of this feature's tasks (see [design.md
§13](design.md#13-additional-architectural-recommendations-not-implemented-here)):
a page cap for `get_by_name`'s multi-page scan, and any "create-or-update
to match" method (a hypothetical `sync`) beyond `ensure`'s pure
get-or-create behavior.
