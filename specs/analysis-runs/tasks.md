# Tasks — Analysis Runs

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Do not start implementation until this specification is reviewed and
approved.

---

## 1. Models

- [ ] 1.1 Create `src/veracode_dast/models/analysis_run.py`:
      `AnalysisRunScanType(StrEnum)` — `QUICK`, `ENTERPRISE`. Follows the
      `AnalysisRun.scan_type` OpenAPI schema exactly and is intentionally
      independent of Target Management's `ScanType` (design.md §3.1) — do
      not add `FULL`.
  - _Requirements: §0.2_

- [ ] 1.2 In the same file: `ResultImportStatus(StrEnum)` — `POLLING`,
      `REQUESTED`, `INPROGRESS`, `COMPLETED`, `FAILED`, `IGNORED`,
      `INVALID`, `ERROR`
  - _Requirements: §0.2_

- [ ] 1.3 In the same file: `StopActionType(StrEnum)` — `STOP_DELETE`,
      `STOP_SAVE`
  - _Requirements: §0.2, 3.2_

- [ ] 1.4 In the same file: `ReportFormat(StrEnum)` — `PDF = "pdf"`, `CSV =
      "csv"`, `JUNIT = "junit"`
  - _Requirements: §0.2, 3.6, 5.4_

- [ ] 1.5 Implement `AnalysisRun` as a frozen dataclass with the fields
      listed in design.md §3.1, importing `Protocol`/`TargetStatus` from
      `models/target.py` rather than redefining them; confirm none of the
      six `deprecated: true` OpenAPI fields (`id`, `project_uuid`,
      `protocol`, `environment`, `started_by`, `estimated_duration`) appear
      as fields
  - _Requirements: §0.2, 5.9_

- [ ] 1.6 Implement `AnalysisRun.from_api(data: dict) -> AnalysisRun` per
      design.md §3.1, wrapping optional `status`/`result_import_status`
      only when present/truthy in the response
  - _Requirements: 3.1, 3.4, 5.9_

- [ ] 1.7 Implement `AnalysisRunPage` as a frozen dataclass: `items:
      list[AnalysisRun]`, `page_number`, `page_size`, `total_pages`,
      `total_elements` — same shape as `TargetPage`
  - _Requirements: 3.3_

- [ ] 1.8 Implement `AnalysisRunPage.from_api(data: dict) ->
      AnalysisRunPage`, reading `_embedded.analysis_runs` and
      `page.{number,size,total_pages,total_elements}`
  - _Requirements: 3.3_

- [ ] 1.9 Add Google-style docstrings and full type hints to every
      class/function added in this section
  - _AGENTS.md Definition of Done_

---

## 2. Exceptions

- [ ] 2.1 Add `AnalysisRunValidationError(VeracodeSDKError)` to
      `src/veracode_dast/exceptions.py`, with a `rule` attribute, following
      the exact shape of `TargetValidationError`/
      `ApiSpecificationValidationError` — confirm it is NOT a subclass of
      `VeracodeApiError`
  - _Requirements: §5_

- [ ] 2.2 Add `AnalysisRunTimeoutError(VeracodeSDKError)` per design.md
      §3.2, carrying `target_id`, `analysis_run_id`, `elapsed`, and
      `last_status`
  - _Requirements: 3.5_

---

## 3. Service implementation

- [ ] 3.1 Create `src/veracode_dast/services/analysis_runs.py` with
      `AnalysisRunsService.__init__(self, http_client: HttpClient)`,
      storing only the client; no base-URL constant defined in this module
      (import `TARGET_CONFIGURATION_SERVICE_BASE_URL` from
      `services/targets.py` where needed, i.e. nowhere in this file itself
      — it's only consumed in `client.py`)
  - _Requirements: 4.1, 4.3_

- [ ] 3.2 Implement the shared `_require_non_blank` static helper, raising
      `AnalysisRunValidationError`
  - _Requirements: 5.1, 5.2_

- [ ] 3.3 Implement `AnalysisRunsService.start(target_id: str) ->
      AnalysisRun`: blank-ID guard, `POST /analysis_run` with body
      `{"id": target_id}`, build via `AnalysisRun.from_api`, INFO log
  - _Requirements: 3.1, 5.1, 5.8_

- [ ] 3.4 Implement `AnalysisRunsService.stop(target_id: str, *, action:
      StopActionType | str = StopActionType.STOP_DELETE) -> None`:
      blank-ID guard, then `_validate_action(action)` (task 3.10) before
      any HTTP call, `POST /analysis_run/{target_id}/stop?action=<action>`
      using the normalized `StopActionType`'s `.value`, no return value,
      INFO log
  - _Requirements: 3.2, 5.1, 5.10_

- [ ] 3.5 Implement `AnalysisRunsService.list(target_id: str, *, page=0,
      limit=10) -> AnalysisRunPage`: blank-ID guard, `GET
      /targets/{target_id}/analysis_runs`, build via
      `AnalysisRunPage.from_api`
  - _Requirements: 3.3, 5.1_

- [ ] 3.6 Implement `AnalysisRunsService.get(target_id: str,
      analysis_run_id: str) -> AnalysisRun`: both blank-ID guards, `GET
      /targets/{target_id}/analysis_runs/{analysis_run_id}`, build via
      `AnalysisRun.from_api`
  - _Requirements: 3.4, 5.1, 5.2_

- [ ] 3.7 Implement `AnalysisRunsService.wait_for_completion(target_id:
      str, analysis_run_id: str, *, poll_interval: float = 15.0, timeout:
      float | None = None) -> AnalysisRun` per design.md §3.3: validate
      `poll_interval`/`timeout`, then loop calling `self.get(...)`,
      checking `status` against the module-level `_TERMINAL_STATUSES`
      frozenset, sleeping via the module-level `time.sleep` between polls,
      tracking elapsed time via `time.monotonic()`, raising
      `AnalysisRunTimeoutError` if `timeout` elapses first
  - _Requirements: 3.5, 5.5, 5.6, 5.7_

- [ ] 3.8 Implement `AnalysisRunsService.get_report(target_id: str,
      analysis_run_id: str, format: ReportFormat | str, destination_path:
      str | Path) -> Path` per design.md §3.3: both blank-ID guards,
      `_validate_format`, destination-parent-exists guard, `GET
      .../report/{format}` with `raw=True`, write bytes via
      `Path.write_bytes`, return the resolved `Path`
  - _Requirements: 3.6, 5.1-5.4_

- [ ] 3.9 Implement the private `_validate_format` static helper per
      design.md §3.3, raising `AnalysisRunValidationError(rule=
      "invalid_report_format")` and listing the three valid values in the
      message
  - _Requirements: 5.4_

- [ ] 3.10 Implement the private `_validate_action` static helper per
      design.md §3.3 (mirrors `_validate_format`): pass a `StopActionType`
      through unchanged, convert/validate a `str`, raising
      `AnalysisRunValidationError(rule="invalid_stop_action")` and listing
      the two valid values in the message — never let a plain `str`
      without a `.value` attribute reach the HTTP call
  - _Requirements: 5.10_

- [ ] 3.11 Add Google-style docstrings and full type hints to every
      class/function added in this section
  - _AGENTS.md Definition of Done_

---

## 4. HTTP integration

- [ ] 4.1 In `src/veracode_dast/client.py`, import `AnalysisRunsService`
      from `veracode_dast.services.analysis_runs`
  - _Requirements: §2_

- [ ] 4.2 Add `self.analysis_runs = AnalysisRunsService(tcs_http_client)` to
      `VeracodeClient.__init__`, reusing the existing `tcs_http_client`
      variable already constructed for `self.targets` and its siblings —
      confirm no new `HttpClient` instance and no new base-URL constant are
      introduced anywhere in this task
  - _Requirements: §2_

- [ ] 4.3 Confirm no existing line in `client.py` or any other
      `services/*.py` module is modified by this task beyond the one import
      and one line added above
  - _Requirements: §7 (Out of Scope)_

---

## 5. Unit tests (models)

Location: `tests/models/test_analysis_run.py`.

- [ ] 5.1 `AnalysisRun.from_api` round-trips a fixture matching the OpenAPI
      `AnalysisRun` schema example, including the six deprecated fields in
      the raw payload; assert the constructed model has no attribute for
      any of them
  - _Requirements: 5.9_

- [ ] 5.2 `AnalysisRun.from_api` with `status`/`result_import_status`
      absent from the payload → both fields `None` on the model; with both
      present → both correctly typed (`TargetStatus`, `ResultImportStatus`)
  - _Requirements: 3.4_

- [ ] 5.3 `AnalysisRunPage.from_api` round-trips a fixture matching
      `PagedAnalysisRuns`
  - _Requirements: 3.3_

- [ ] 5.4 Confirm `models/analysis_run.py` imports neither `requests` nor
      `HttpClient`
  - _AGENTS.md §3, Hard rule_

---

## 6. Integration tests (service + models + client wiring)

Location: `tests/services/test_analysis_runs.py`. Stub/fake `HttpClient`
returning prepared `HttpResponse` values or raising prepared
`VeracodeApiError` subclasses — same pattern as
`tests/services/test_targets.py`. No real network access, environment
variables, real `time.sleep` delays, or Veracode credentials.

- [ ] 6.1 `start()`: request body is exactly `{"id": target_id}`; 200 →
      `AnalysisRun`; blank `target_id` → `AnalysisRunValidationError`, no
      HTTP call
  - _Requirements: 3.1, 6 (Acceptance Criteria)_

- [ ] 6.2 `stop()`: default call sends `action=STOP_DELETE`; explicit
      `action=StopActionType.STOP_SAVE` and the equivalent plain string
      `action="STOP_SAVE"` both send `action=STOP_SAVE`; return value is
      `None`; `action="cancel"` raises
      `AnalysisRunValidationError(rule="invalid_stop_action")` before any
      HTTP call
  - _Requirements: 3.2, 5.10, 6 (Acceptance Criteria)_

- [ ] 6.3 `list()`/`get()`: mirror `TargetsService`'s existing test
      coverage shape; blank IDs raise with no HTTP call; a stubbed 404
      propagates `VeracodeNotFoundError` unchanged
  - _Requirements: 3.3, 3.4, 6 (Acceptance Criteria)_

- [ ] 6.4 `wait_for_completion()`, with `AnalysisRunsService.get` stubbed
      (via a monkeypatched method or a scripted `HttpClient`) and
      `time.sleep` monkeypatched to a no-op:
      - `RUNNING`, `RUNNING`, `FINISHED` sequence → three `get()` calls,
        two `sleep()` calls, returns the `FINISHED` run
      - `status=None` → treated as non-terminal, loop continues
      - a sequence that never reaches a terminal status, with
        `time.monotonic` monkeypatched to advance past `timeout` → raises
        `AnalysisRunTimeoutError` carrying the last observed status
      - `poll_interval=0` and `timeout=0` → each its own
        `AnalysisRunValidationError`, no `get()` call
  - _Requirements: 3.5, 5.5-5.7, 6 (Acceptance Criteria)_

- [ ] 6.5 `get_report()`: writes stubbed raw bytes to a `tmp_path`-based
      destination; returns the resolved `Path`; `format="xml"` raises
      `AnalysisRunValidationError` before any HTTP call; a destination
      whose parent directory does not exist raises before any HTTP call; a
      stubbed 404 propagates `VeracodeNotFoundError` unchanged
  - _Requirements: 3.6, 5.3, 5.4, 6 (Acceptance Criteria)_

- [ ] 6.6 `caplog` assertion: no captured log record from this feature
      contains report file bytes/contents
  - _Requirements: 4.5_

- [ ] 6.7 `VeracodeClient()` wiring test: `client.analysis_runs` is an
      `AnalysisRunsService`, and its underlying `HttpClient` is the same
      object identity as `client.targets`'s
  - _Requirements: §4 (HTTP integration)_

---

## 7. Documentation

- [ ] 7.1 Add `examples/analysis_runs_example.py` using stdlib `argparse`
      to accept a `target_id` and optional `--analysis-run-id`,
      `--poll-interval`, `--timeout`, `--report-format`, `--report-path`,
      and `--stop-action` as command-line arguments — never hardcoded,
      never read from the environment by the example itself, matching
      `examples/target_management_example.py`'s convention
  - _AGENTS.md Definition of Done_

- [ ] 7.2 Script body must exercise all six public `AnalysisRunsService`
      operations, so every method has runnable-example coverage (not just
      the ones README.md shows as inline snippets):
      1. `list(target_id)` — print existing runs for the target first.
      2. `start(target_id)` (skipped in favor of the caller-supplied
         `--analysis-run-id` if given, so the script is also usable
         against an already-running scan).
      3. `get(target_id, analysis_run_id)` — print the freshly
         started/given run.
      4. `wait_for_completion(...)` — print the final status.
      5. `get_report(...)` — print the resolved path.
      6. `stop(target_id, action=...)` — behind an explicit `--stop` flag
         (default off, since stopping is destructive/mutually exclusive
         with waiting for a real completion) so the method is still
         demonstrated without making the default run path pointlessly
         stop its own scan
  - _AGENTS.md Definition of Done_

- [ ] 7.3 Confirm the script contains no Azure DevOps-specific code and no
      hardcoded credentials or business data
  - _AGENTS.md §5, Platform Agnostic_

- [ ] 7.4 Do not modify [README.md](README.md) — it is the reference this
      specification was derived from, not a task output

---

## 8. Quality gates

- [ ] 8.1 `ruff check` passes with no new warnings
- [ ] 8.2 `mypy --strict` passes for `models/analysis_run.py`,
      `services/analysis_runs.py`, the extended `client.py`, and the
      extended `exceptions.py`
- [ ] 8.3 `pytest` passes for `test_analysis_run.py` and
      `test_analysis_runs.py`, alongside the full existing suite
      (confirming no regression to any Phase 1/Phase 2 module)
- _AGENTS.md Definition of Done_

---

## Dependency order

1 (models) has no dependency beyond the reused `Protocol`/`TargetStatus`
(already implemented in `models/target.py`) and must precede 2
(exceptions, no internal dependency of its own) and 3 (service), which
imports both 1 and 2. 3 must precede 4 (HTTP integration), which wires the
finished `AnalysisRunsService` into `VeracodeClient`. 5 depends on 1; 6
depends on 3 and 4 (the wiring test in 6.7 needs `client.py` already
updated); 7 depends on 4; 8 depends on everything above.

## Explicitly not part of these tasks

Per [requirements.md §7](requirements.md#7-out-of-scope): no legacy
`GET /analysis_run/report/{target_id}` wrapper; no Discovered Targets
(listing, ignoring, mapping); no Schedules; no Applications/Findings/
Policies; no parsing or interpreting downloaded report contents; no
combined `start()` + `wait_for_completion()` convenience method; no CLI or
execution-platform integration; no edits to `services/targets.py` or any
other existing service beyond the additive `client.py` wiring in Section 4.
