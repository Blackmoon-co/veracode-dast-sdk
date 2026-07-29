# Tasks — Analysis Profiles

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Do not start implementation until this specification is reviewed and
approved.

---

## 1. Models

- [ ] 1.1 Create `src/veracode_dast/models/common.py` with the generic
      `InheritedValue[T]` frozen dataclass (`effective_value`,
      `is_inherited`) and `InheritedValue.from_api(data: dict) ->
      InheritedValue[T]` (design.md §4.1)
  - _Requirements: 4.5_

- [ ] 1.2 Create `src/veracode_dast/models/analysis_profile.py`:
      `AnalysisProfileType(StrEnum)` — `TARGET`, `ORG`, `SYSTEM`
  - _Requirements: 4.1_

- [ ] 1.3 In the same file: `AnalysisProfileMode(StrEnum)` — `STANDARD`,
      `ENTERPRISE`
  - _Requirements: 4.2_

- [ ] 1.4 In the same file: `CrawlerMode(StrEnum)` — `SMART`, `EXHAUSTIVE`
  - _Requirements: 4.3_

- [ ] 1.5 In the same file: `DirectoryRestrictions(StrEnum)` —
      `DIR_AND_SUBDIR`, `DIR_ONLY`, `NO_RESTRICTIONS`
  - _Requirements: 4.4_

- [ ] 1.6 Add `ScopeRule.to_api()` to the existing
      `src/veracode_dast/models/api_specification.py` (design.md §4.3) —
      confirm no existing field, constructor signature, or `from_api()`
      behavior on `ScopeRule`/`ApiSpecification` changes
  - _Requirements: 4.7_

- [ ] 1.7 Implement `AnalysisProfile` as a frozen dataclass (design.md
      §4.2): required fields matching the OpenAPI `AnalysisProfile`
      schema's `required` list exactly, thirteen fields wrapped in
      `InheritedValue[T]`, `api_spec` typed as `ApiSpecification | None`
      (reused, not redefined)
  - _Requirements: 4.6, 4.7_

- [ ] 1.8 Implement `AnalysisProfile.from_api(data: dict) ->
      AnalysisProfile`, wrapping each `InheritedValue`-typed field via
      `InheritedValue.from_api`, and building `api_spec` via
      `ApiSpecification.from_api(..., target_id=...)` when the response
      includes one, falling back to the profile's own `target_id`
  - _Requirements: 3.3.3, 4.6_

- [ ] 1.9 Implement `AnalysisProfileSummary` as a frozen dataclass
      (`analysis_profile_id`, `name`, `target_id: str | None = None`) with
      `from_api(data: dict) -> AnalysisProfileSummary`
  - _Requirements: 4.6_

- [ ] 1.10 Define the private `_UNSET` sentinel and implement
      `AnalysisProfileUpdate` as a frozen dataclass: `allowed_urls`,
      `denied_urls`, `seed_urls`, `grouped_urls`, `crawler_mode`,
      `rate_limit`, `max_duration`, `max_crawl_duration`, `max_browsers`,
      `scope_rules`, `similarity_threshold`, `directory_restrictions`,
      `enable_all_target_protocols`, all defaulting to `_UNSET`; confirm
      `name`/`description` are NOT fields on this class
  - _Requirements: 3.4.3, 3.4.4, 4.6_

- [ ] 1.11 Implement `AnalysisProfileUpdate.to_api() -> dict`, returning
      only explicitly-set fields, preserving an explicit `None` (e.g.
      `allowed_urls=None`, `directory_restrictions=None`) as JSON `null`
      rather than omitting it; serialize `crawler_mode`/
      `directory_restrictions` via `.value` and `scope_rules` via
      `[r.to_api() for r in ...]`
  - _Requirements: 3.4.1, 3.4.4_

- [ ] 1.12 Implement `AnalysisProfilePage` as a frozen dataclass: `items:
      list[AnalysisProfileSummary]`, `page_number`, `page_size`,
      `total_pages`, `total_elements`, plus `__iter__` returning
      `iter(self.items)`
  - _Requirements: 3.2.7_

- [ ] 1.13 Implement `AnalysisProfilePage.from_api(data: dict) ->
      AnalysisProfilePage`, reading `_embedded.analysis_profiles` and
      `page.{number,size,total_pages,total_elements}`; do NOT read or
      expose `_links`
  - _Requirements: 3.2.4, 3.2.5_

- [ ] 1.14 Add Google-style docstrings and full type hints to every class/
      function added or modified in this section
  - _AGENTS.md Definition of Done_

---

## 2. Service implementation

- [ ] 2.1 Add `AnalysisProfileValidationError(VeracodeSDKError)` to
      `src/veracode_dast/exceptions.py`, with a `rule` attribute,
      following the exact shape of `TeamValidationError`/
      `TargetValidationError`/`ApiSpecificationValidationError` (design.md
      §4.4) — confirm it is NOT a subclass of `VeracodeApiError`
  - _Requirements: 6.1_

- [ ] 2.2 Create `src/veracode_dast/services/analysis_profiles.py` with
      `AnalysisProfilesService.__init__(self, http_client: HttpClient)`,
      storing only the client; no base-URL constant defined in this
      module; no other state
  - _Requirements: 8.2, 8.4_

- [ ] 2.3 Implement the shared `_require_non_blank` static helper (mirrors
      `TeamService`/`ApiSpecificationsService`), raising
      `AnalysisProfileValidationError`
  - _Requirements: 5.1, 6.1_

- [ ] 2.4 Implement `AnalysisProfilesService.list(*, page=0, limit=10,
      target_id=None, types=None) -> AnalysisProfilePage`: build query
      parameters from only the supplied arguments (matching §0.3's REST
      defaults exactly), forward `types` as the repeated `type` parameter,
      build the result via `AnalysisProfilePage.from_api`, emit the INFO
      log from design.md §4.5
  - _Requirements: 3.2.1–3.2.6, 7.2_

- [ ] 2.5 Implement `AnalysisProfilesService.get(analysis_profile_id: str)
      -> AnalysisProfile`: blank-ID guard first, then `GET
      /analysis_profiles/{id}`, build via `AnalysisProfile.from_api`;
      confirm `VeracodeNotFoundError` is not caught
  - _Requirements: 3.3.1–3.3.4, 5.1_

- [ ] 2.6 Implement `AnalysisProfilesService.update(analysis_profile_id:
      str, analysis_profile: AnalysisProfileUpdate) -> AnalysisProfile`:
      blank-ID guard first, then `PUT /analysis_profiles/{id}` with
      `json=analysis_profile.to_api()` and **always**
      `params={"method": "PATCH"}` — confirm there is no code path that
      omits this query parameter; build the result via
      `AnalysisProfile.from_api`; emit the INFO log from design.md §4.5
  - _Requirements: 3.4.1–3.4.8, 5.1, 7.1_

- [ ] 2.7 Add Google-style docstrings and full type hints to every
      class/function added in this section
  - _AGENTS.md Definition of Done_

---

## 3. HTTP integration

- [ ] 3.1 In `src/veracode_dast/client.py`, import
      `AnalysisProfilesService` from
      `veracode_dast.services.analysis_profiles`
  - _Requirements: 8.2_

- [ ] 3.2 Add `self.analysis_profiles = AnalysisProfilesService(tcs_http_client)`
      to `VeracodeClient.__init__`, reusing the existing `tcs_http_client`
      variable already constructed for `self.targets`/
      `self.api_specifications` — confirm no new `HttpClient` instance and
      no new base-URL constant are introduced anywhere in this task
  - _Requirements: 8.2_

- [ ] 3.3 Confirm no existing line in `client.py`, `services/targets.py`,
      `services/teams.py`, or `services/api_specifications.py` is modified
      by this task beyond the one import and one line added above
  - _Requirements: 12.5_

- [ ] 3.4 Add Google-style docstring updates to `VeracodeClient` reflecting
      the new attribute
  - _AGENTS.md Definition of Done_

---

## 4. Unit tests (models)

Location: `tests/models/test_analysis_profile.py`.

- [ ] 4.1 `InheritedValue.from_api` round-trips a fixture for at least one
      `list[str]`-valued field (e.g. `allowed_urls`) and one `bool`-valued
      field (e.g. `crawler_enabled`)
  - _Requirements: 4.5_

- [ ] 4.2 `AnalysisProfile.from_api` round-trips a fixture matching the
      OpenAPI `AnalysisProfile` example, including a nested `api_spec`
      object; assert the result's `.api_spec` is an `ApiSpecification`
      instance, not a second parallel type
  - _Requirements: 3.3.3, 4.7_

- [ ] 4.3 `AnalysisProfileSummary.from_api` round-trips a fixture matching
      `AnalysisProfileListItem`, including the case where `target_id` is
      absent
  - _Requirements: 4.6_

- [ ] 4.4 `AnalysisProfileUpdate.to_api()`: unset fields are absent from
      the result; each explicitly-set field appears; an explicit
      `allowed_urls=None` produces `{"allowed_urls": None}`; `scope_rules`
      serializes each entry via `ScopeRule.to_api()`
  - _Requirements: 3.4.3, 3.4.4_

- [ ] 4.5 `AnalysisProfilePage.from_api` round-trips a fixture matching
      `PagedAnalysisProfiles`; confirm no attribute exposes `_links`;
      confirm `list(page)` (via `__iter__`) equals `page.items`
  - _Requirements: 3.2.4, 3.2.5, 3.2.7_

- [ ] 4.6 Confirm `models/analysis_profile.py` and `models/common.py`
      import neither `requests` nor `HttpClient`
  - _Requirements: 4.6_

---

## 5. Integration tests (service + models + client wiring)

Location: `tests/services/test_analysis_profiles.py`. "Integration" here
means Service + Models exercised together through a stub `HttpClient` (one
test additionally constructs `VeracodeClient` to confirm wiring) — still
with no real network access, environment variables, or Veracode
credentials, matching every other service's test suite in this repository.

- [ ] 5.1 Build a stub/fake `HttpClient` returning prepared `HttpResponse`
      values or raising prepared `VeracodeApiError` subclasses (same
      pattern as `tests/services/test_targets.py`)
  - _Requirements: 9.1_

- [ ] 5.2 `list()`: default query parameters match §0.3's defaults; a
      supplied `target_id` is forwarded; a supplied `types` list is
      forwarded as a repeated `type` parameter; the resulting
      `AnalysisProfilePage` is built correctly from a
      `PagedAnalysisProfiles`-shaped fixture
  - _Requirements: 3.2.1–3.2.4_

- [ ] 5.3 `get()`: blank ID raises `AnalysisProfileValidationError` with no
      call made to the stub; a valid ID + 200 response returns the
      expected `AnalysisProfile`; a stubbed 404 propagates
      `VeracodeNotFoundError` unchanged
  - _Requirements: 3.3.1–3.3.4, 5.1_

- [ ] 5.4 `update()`: blank ID raises `AnalysisProfileValidationError` with
      no call made to the stub; a single-field `AnalysisProfileUpdate`
      produces a `PUT` call whose captured `params` include
      `{"method": "PATCH"}` and whose captured `json` body contains only
      that one field; a stubbed 404 propagates `VeracodeNotFoundError`; a
      stubbed 422 propagates `VeracodeValidationError`
  - _Requirements: 3.4.1, 3.4.2, 3.4.5, 3.4.7, 3.4.8_

- [ ] 5.5 `caplog` assertion: no captured log record from this feature
      contains `allowed_urls`, `denied_urls`, `seed_urls`, or
      `grouped_urls` values used in the test
  - _Requirements: 7.3_

- [ ] 5.6 `VeracodeClient()` wiring test: `client.analysis_profiles` is an
      `AnalysisProfilesService`, and its underlying `HttpClient` is the
      same object identity as `client.targets`'s (not merely an
      equivalently-configured second instance)
  - _Requirements: 8.2_

---

## 6. Documentation

- [ ] 6.1 Add `examples/analysis_profiles_example.py` using stdlib
      `argparse` to accept an `analysis_profile_id` and the update fields
      a caller wants to demonstrate changing (e.g. `--rate-limit`,
      `--max-duration`) as command-line arguments — never hardcoded, never
      read from the environment by the example itself, matching
      `examples/target_management_example.py`'s convention
  - _AGENTS.md Definition of Done_

- [ ] 6.2 Script body: construct `VeracodeClient()`, call
      `analysis_profiles.get(analysis_profile_id)` and print the typed
      result (including at least one `InheritedValue` field's
      `effective_value`/`is_inherited`), then call `update(...)` with only
      the caller-supplied fields and print the updated result
  - _AGENTS.md Definition of Done_

- [ ] 6.3 Confirm the script contains no Azure DevOps-specific code and no
      hardcoded credentials or business data
  - _Requirements: 8.2 (Platform Agnostic, per AGENTS.md §5)_

- [ ] 6.4 Do not modify [README.md](README.md) — it is the reference this
      specification was derived from, not a task output

---

## 7. Quality gates

- [ ] 7.1 `ruff check` passes with no new warnings
- [ ] 7.2 `mypy` passes in strict mode for `models/common.py`,
      `models/analysis_profile.py`, the extended
      `models/api_specification.py`, `services/analysis_profiles.py`, the
      extended `client.py`, and the extended `exceptions.py`
- [ ] 7.3 `pytest` passes for `test_analysis_profile.py` and
      `test_analysis_profiles.py`, alongside the full existing suite
      (confirming no regression to Target Management, Team Management, or
      API Specification Management)
- _AGENTS.md Definition of Done_

---

## Dependency order

1 (models) has no dependency beyond the reused `ApiSpecification`/
`ScopeRule` (already implemented) and must precede 2 (service), which
imports it. 2 must precede 3 (HTTP integration), which wires the finished
`AnalysisProfilesService` into `VeracodeClient`. 4 depends on 1; 5 depends
on 2 and 3 (the wiring test in 5.6 needs `client.py` already updated); 6
depends on 3; 7 depends on everything above.

## Explicitly not part of these tasks

Per [requirements.md §12](requirements.md#12-out-of-scope): no profile
re-parenting (`parent`, `assignable_parent_profiles`), no Schedules, no
Authentication Configuration, no Scanner Configuration, no Scanner
Variables, no Crawl Configuration; no create/delete for Analysis Profiles;
no `get_by_name`/`exists`/`ensure`-style convenience method; no
pagination-aggregation, caching, or retry logic beyond the HTTP Client's
own; no edits to `services/targets.py`, `services/teams.py`, or
`services/api_specifications.py` beyond the additive `ScopeRule.to_api()`
method (task 1.6); no config-file-driven update workflow.
