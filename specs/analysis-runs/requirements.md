# Requirements — Analysis Runs

Traceable to [README.md](README.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Depends on the
[HTTP Client](../http-client/requirements.md) and reuses
`TARGET_CONFIGURATION_SERVICE_BASE_URL` from
[Target Management](../target-management/requirements.md) (same Veracode
API domain as every other Phase 2 module). Reuses `TargetStatus` from
[Target Management](../target-management/design.md), which draws from the
OpenAPI's shared `Status` schema (requirements.md §0.2) — the same schema
`Target.status` itself references. Also reuses `Protocol` from Target
Management, at the SDK level only: `Protocol` and `Status` are unrelated
OpenAPI schemas, but `AnalysisRun.target_protocol`'s enum values are
identical to `Protocol`'s, so this SDK reuses the existing model rather
than declaring a second, redundant one (requirements.md §0.2).

---

## 0. OpenAPI Review

Source: `openApi/Veracode-veracode-dast-target-configuration-service-api-1.0.0-resolved.json`,
server `https://api.veracode.com/dae/api/tcs-api/api/v1` (no new base URL).

### 0.1 In-scope REST endpoints

| Method | Path | operationId | Purpose |
|---|---|---|---|
| POST | `/analysis_run` | `startAnalysisRun` | Start a new analysis run for a Target |
| POST | `/analysis_run/{target_id}/stop` | `stopAnalysisRun` | Stop a running analysis run |
| GET | `/targets/{target_id}/analysis_runs` | `getAnalysisRuns` | List analysis runs for a Target (paged) |
| GET | `/targets/{target_id}/analysis_runs/{analysis_run_id}` | `getAnalysisRunById` | Get a single analysis run (status polling) |
| GET | `/targets/{target_id}/analysis_runs/{analysis_run_id}/report/{format}` | `getAnalysisRunReportByFormat` | Download the report for an analysis run (`pdf`, `csv`, `junit`) |

### 0.1.1 Explicitly excluded endpoint

`GET /analysis_run/report/{target_id}` (`getAnalysisRunReportByTargetId`) is
a target-scoped, format-less, redirect-or-download report endpoint. This
SDK does not wrap it — this is an intentional scope decision, **not** a
claim that it is behaviorally equivalent to `getAnalysisRunReportByFormat`.
The two endpoints are not proven equivalent from the OpenAPI: the legacy
endpoint needs only a `target_id` (implicitly "the" report for that
target, format unspecified — its 200 response is generic
`application/octet-stream`), while `getAnalysisRunReportByFormat` requires
an explicit `analysis_run_id` and format. This module's supported workflow
(`start()` → `wait_for_completion()` → `get_report()`) always operates on
a specific `AnalysisRun` and therefore always has its `analysis_run_id`
available, so the analysis-run-scoped, format-selectable endpoint is
sufficient for every workflow this SDK supports — without needing to claim
it subsumes the legacy endpoint's behavior in general. See README
["Out of Scope"](README.md#out-of-scope).

### 0.2 Schemas

`TargetAnalysisRunRequest` (POST `/analysis_run` request body; the only
field, `id`, is the target's ID): `{"id": "<target_id>"}`.

`inline_response_200` — the 200 response of `startAnalysisRun`: `nullable:
true`, `allOf: [AnalysisRun]`. The OpenAPI document does not describe a
condition under which this is actually null on a 200 (a scan already in
progress is a documented 400, not a null 200) — see §5.8 for how this SDK
treats that case.

`Status` (shared enum, also used by `Target.status` in
[target-management](../target-management/requirements.md)): `RUNNING`,
`STOPPING`, `STOPPED`, `FINISHED`, `FAILED`. Reused as `TargetStatus` for
`AnalysisRun.status` rather than duplicating an identical closed
vocabulary under a second name.

`AnalysisRun` (required: `analysis_run_id`, `max_crawl_duration`,
`max_duration`, `scan_number`, `scan_type`, `started_at`, `started_by_name`,
`target_id`, `target_protocol`, `url`; optional: `finished_at`, `status`,
`max_cvss`, `result_import_status`). The schema also carries six fields
marked `deprecated: true` (`id`, `project_uuid`, `protocol`, `environment`,
`started_by`, `estimated_duration`) — this SDK's `AnalysisRun` model omits
all six (§5.9); every non-deprecated field is kept.

`scan_type` on `AnalysisRun` is `enum: [QUICK, ENTERPRISE]` — a closed,
two-value set defined directly on the `AnalysisRun` schema itself. This is
**not** the same set as Target Management's `ScanType` (`QUICK`, `FULL`,
`ENTERPRISE`), and that is expected, not an inconsistency to resolve:
`AnalysisRun` and `Target` are two different OpenAPI schemas, each
defining its own `scan_type`/`ScanType` enum, and this SDK models each
resource's field according to that resource's own schema rather than
importing a sibling resource's value set. `Target.scan_type` allowing
`FULL` has no bearing on what `AnalysisRun.scan_type` is documented to
accept — the OpenAPI contract for `AnalysisRun` is authoritative here, and
it defines exactly `QUICK`/`ENTERPRISE`. A dedicated `AnalysisRunScanType`
enum is therefore introduced, intentionally scoped to the `AnalysisRun`
schema and intentionally independent of Target Management's `ScanType`
(design.md §3.1). This value set is final; it is not a placeholder pending
further validation.

`target_protocol` on `AnalysisRun` is `enum: [HTTP, HTTPS]` — identical to
Target Management's `Protocol`; reused directly.

`ResultImportStatus`: `POLLING`, `REQUESTED`, `INPROGRESS`, `COMPLETED`,
`FAILED`, `IGNORED`, `INVALID`, `ERROR`.

`StopActionType` (POST `/analysis_run/{target_id}/stop` query param
`action`, required): `STOP_DELETE` (default), `STOP_SAVE`.

`PagedAnalysisRuns` / `EmbeddedAnalysisRuns` / `PageMeta` — identical shape
to Target Management's `PagedTargets`/`EmbeddedTargets`/`PageMeta`
(`_embedded.analysis_runs`, `page.{number,size,total_pages,total_elements}`).

The `format` path parameter of `getAnalysisRunReportByFormat` is a bare
`type: string` in the OpenAPI document; its allowed values (`pdf`, `csv`,
`junit`) are documented only in the parameter description, not as a schema
enum. This SDK still models it as a closed `ReportFormat` enum client-side
(§5.5) rather than accepting an arbitrary string, since the description is
explicit and unambiguous about the closed set.

### 0.3 HTTP status codes and error responses

- `startAnalysisRun`: 200 → `inline_response_200`; 400 → no schema (target
  ID invalid, or analysis already in progress); 500 → `Problem`.
- `stopAnalysisRun`: 200 → no body; 400 → `Problem` (`Problem400Response`);
  401/403 → no body; 404 → `Problem`; 500 → `Problem`.
- `getAnalysisRuns`: 200 → `PagedAnalysisRuns`; 400 → `Problem`; 401/403 →
  no body; 404 → `Problem`; 500 → `Problem`.
- `getAnalysisRunById`: 200 → `AnalysisRun`; 400 → `Problem`; 401/403 → no
  body; 404 → `Problem`; 500 → `Problem`.
- `getAnalysisRunReportByFormat`: 200 → binary (`application/pdf`,
  `application/xml`, or `text/csv` depending on `format`); 401 → no body;
  404 → `Problem`; 500 → `Problem`.

All of the above are already mapped centrally by the HTTP Client
(`VeracodeAuthenticationError`, `VeracodeAuthorizationError`,
`VeracodeNotFoundError`, `VeracodeValidationError`/`VeracodeApiError`) — no
new status-code handling is needed in this feature.

---

## 1. Overview

Analysis Runs starts, stops, lists, and inspects scan executions against an
existing Target, and downloads the resulting report. It also provides a
`wait_for_completion()` convenience that polls `get()` until the run
reaches a terminal status — the "Wait for Completion" capability called out
by [AGENTS.md's Phase 3 roadmap](../../AGENTS.md#phase-3--execute-scans).

Unlike the Phase 2 configuration modules (Scanner Profiles, Authentication,
Scanner Variables), this feature is not configuration-driven — there is no
SDK Configuration document to load/validate/transform. Every method takes
typed arguments directly, the same shape as Target Management's CRUD
methods.

## 2. Goals

- Start and stop analysis runs for an existing Target.
- List and retrieve analysis runs as strongly typed models.
- Provide a blocking `wait_for_completion()` helper built only on the
  existing `get()` polling primitive and the standard library (`time.sleep`)
  — no new dependency.
- Download an analysis run's report to a local file, reusing the same
  raw-bytes-to-disk pattern already established by
  [API Specification Management's `download()`](../api-specification-management/design.md).
- Reuse the shared `HttpClient`, exception hierarchy, and
  `TARGET_CONFIGURATION_SERVICE_BASE_URL` — no new HTTP/auth code.

## 3. Functional Requirements

3.1. `start(target_id: str) -> AnalysisRun`. Calls `POST /analysis_run`
     with body `{"id": target_id}`; returns
     `AnalysisRun.from_api(response.data)`.

3.2. `stop(target_id: str, *, action: StopActionType | str =
     StopActionType.STOP_DELETE) -> None`. Calls `POST
     /analysis_run/{target_id}/stop?action=<action>`. `action` accepts
     either a `StopActionType` member or a plain string; a string is
     validated and normalized to `StopActionType` before any HTTP call
     (§5.10) — same acceptance pattern as `get_report()`'s `format`
     (§3.6, §5.4).

3.3. `list(target_id: str, *, page: int = 0, limit: int = 10) ->
     AnalysisRunPage`. Calls `GET /targets/{target_id}/analysis_runs`;
     returns `AnalysisRunPage.from_api(response.data)`.

3.4. `get(target_id: str, analysis_run_id: str) -> AnalysisRun`. Calls `GET
     /targets/{target_id}/analysis_runs/{analysis_run_id}`; returns
     `AnalysisRun.from_api(response.data)`.

3.5. `wait_for_completion(target_id: str, analysis_run_id: str, *,
     poll_interval: float = 15.0, timeout: float | None = None) ->
     AnalysisRun`. Repeatedly calls `get(target_id, analysis_run_id)`,
     sleeping `poll_interval` seconds between calls, until `status` is one
     of the terminal statuses (`FINISHED`, `STOPPED`, `FAILED` — §5.7),
     then returns that `AnalysisRun`. If `timeout` is not `None` and
     elapses before a terminal status is reached, raises
     `AnalysisRunTimeoutError` instead of returning. `timeout` is a **soft
     bound, not an exact deadline**: elapsed time is checked once per
     poll, immediately after `get()` returns and before sleeping, so the
     actual failure can occur up to approximately one `poll_interval` plus
     one HTTP request's duration after the nominal `timeout` value — never
     less.

3.6. `get_report(target_id: str, analysis_run_id: str, format:
     ReportFormat | str, destination_path: str | Path) -> Path`. Calls `GET
     /targets/{target_id}/analysis_runs/{analysis_run_id}/report/{format}`
     with `raw=True`; writes the response bytes to `destination_path` and
     returns the resolved `Path` — same pattern as
     [`ApiSpecificationsService.download()`](../api-specification-management/design.md).

3.7. Every method that takes `target_id` and/or `analysis_run_id` rejects a
     blank/whitespace-only value before any HTTP call (§5.1–5.2).

## 4. Non-Functional Requirements

4.1. Stateless: `AnalysisRunsService` holds only an injected `HttpClient`
     instance; no per-call or cross-call mutable state (AGENTS.md §5
     "Stateless"). `wait_for_completion()`'s loop state (elapsed time, poll
     count) lives entirely on the call stack, not on `self`.

4.2. Type hints on every public and private function; Google-style
     docstrings on every public class/function (AGENTS.md §7).

4.3. No direct `requests` import; every outbound call goes through the
     shared `HttpClient` (AGENTS.md §3, "Hard rule").

4.4. No business data (`target_id`, `analysis_run_id`, report format,
     destination path) is ever read from an environment variable (AGENTS.md
     §6.2).

4.5. Logging at meaningful points only: run started/stopped, each
     `wait_for_completion()` poll (at DEBUG — status only, not the full
     response body), terminal status reached, report download
     started/completed, validation failures. Never report file contents.

4.6. `wait_for_completion()` calls the module-level `time.sleep`
     (patchable in tests via `monkeypatch`) — no injected clock/sleep
     dependency, since the standard library already covers this and no
     other caller of this module needs to swap it.

## 5. Validation Rules

All of the following are checked **before** any HTTP call, and each raises
before any network I/O occurs:

5.1. `target_id` must be non-blank (after `.strip()`) on every method that
     takes it → `AnalysisRunValidationError(rule="target_id_required")`.

5.2. `analysis_run_id` must be non-blank on every method that takes it →
     `AnalysisRunValidationError(rule="analysis_run_id_required")`.

5.3. `get_report()`'s `destination_path` parent directory must already
     exist → `AnalysisRunValidationError(rule="destination_parent_must_exist")`
     — same rule name/shape as
     [api-specification-management/requirements.md](../api-specification-management/requirements.md).

5.4. `get_report()`'s `format`, if given as a `str`, must be one of `"pdf"`,
     `"csv"`, `"junit"` (case-sensitive, matching the OpenAPI description
     exactly) → `AnalysisRunValidationError(rule="invalid_report_format")`,
     naming the offending value and the three valid options.

5.5. `wait_for_completion()`'s `poll_interval` must be `> 0` →
     `AnalysisRunValidationError(rule="poll_interval_must_be_positive")`.

5.6. `wait_for_completion()`'s `timeout`, if not `None`, must be `> 0` →
     `AnalysisRunValidationError(rule="timeout_must_be_positive")`.

5.7. Terminal statuses for `wait_for_completion()` are exactly
     `TargetStatus.FINISHED`, `TargetStatus.STOPPED`, `TargetStatus.FAILED`.
     `RUNNING` and `STOPPING` are non-terminal and cause the loop to
     continue. A run with `status is None` (the field is optional in the
     schema) is treated as non-terminal — polling continues rather than
     guessing.

5.8. If `start()`'s 200 response body is `null` (the schema's documented
     `inline_response_200` nullability — §0.2), `AnalysisRun.from_api()` is
     called on it and its natural failure is allowed to propagate; no
     speculative handling is added for a case the OpenAPI document does not
     explain and that has never been observed. If this proves reachable in
     practice, a follow-up can add explicit handling then.

5.9. The six `deprecated: true` `AnalysisRun` fields (§0.2) are never read
     by `AnalysisRun.from_api()` and never appear on the model.

5.10. `stop()`'s `action`, if given as a `str`, must be one of
      `"STOP_DELETE"`, `"STOP_SAVE"` (case-sensitive, matching
      `StopActionType`'s values exactly) →
      `AnalysisRunValidationError(rule="invalid_stop_action")`, naming the
      offending value and the two valid options — before any HTTP call. An
      invalid string must never reach `HttpClient` and must never surface
      as a bare `AttributeError`.

## 6. Acceptance Criteria

- Given a valid `target_id`, `client.analysis_runs.start(target_id)` sends
  `POST /analysis_run` with body `{"id": target_id}` and returns an
  `AnalysisRun` built from the response.
- Given a valid `target_id`, `client.analysis_runs.stop(target_id)` sends
  `POST /analysis_run/{target_id}/stop?action=STOP_DELETE` (the default)
  and returns `None`; passing `action=StopActionType.STOP_SAVE` or
  `action="STOP_SAVE"` (a plain string) both send `action=STOP_SAVE`
  instead.
- Given `action="cancel"` (an unrecognized string), `stop()` raises
  `AnalysisRunValidationError(rule="invalid_stop_action")` before any HTTP
  call — never a bare `AttributeError`.
- `client.analysis_runs.list(target_id)` returns an `AnalysisRunPage` whose
  `items` matches the `_embedded.analysis_runs` array and whose paging
  fields match `page.*`, the same shape as
  [target-management's `TargetPage`](../target-management/design.md).
- `client.analysis_runs.get(target_id, analysis_run_id)` returns an
  `AnalysisRun` with every non-deprecated field from §0.2 populated.
- Given a stub `get()` that returns `RUNNING` twice then `FINISHED`,
  `wait_for_completion(...)` calls `get()` three times, sleeps twice
  (`poll_interval` each time), and returns the `FINISHED` `AnalysisRun`.
- Given a stub `get()` that never reaches a terminal status and a
  `timeout` shorter than the simulated elapsed time, `wait_for_completion()`
  raises `AnalysisRunTimeoutError` and makes no HTTP call beyond what
  already elapsed before the timeout fired.
- `client.analysis_runs.get_report(target_id, analysis_run_id, "pdf",
  tmp_path / "report.pdf")` writes the stubbed response bytes to that path
  and returns the resolved `Path`.
- Given `format="xml"`, `get_report()` raises `AnalysisRunValidationError`
  before any HTTP call.
- Given a blank `target_id` or `analysis_run_id`, every method raises
  `AnalysisRunValidationError` and makes no HTTP call.
- Given a 404 response, `get()`, `list()`, `stop()`, and `get_report()` let
  `VeracodeNotFoundError` propagate unchanged.

## 7. Out of Scope

Per [README.md "Out of Scope"](README.md#out-of-scope):

- The legacy `GET /analysis_run/report/{target_id}` endpoint (§0.1.1).
- Discovered Targets (`/discovered_targets*` — listing, ignoring, mapping).
- Schedules (`/analysis_profiles/{id}/schedule`) — never in scope for any
  phase to date (AGENTS.md's Phase 1 "Explicitly out of scope").
- Applications/Findings/Policies (AppSec domain).
- Parsing or interpreting downloaded report contents (PDF/CSV/JUnit) — the
  SDK returns raw bytes written to disk, nothing more.
- A combined `start()` + `wait_for_completion()` convenience method — the
  caller composes the two (README "Out of Scope").
- Any CLI or execution-platform integration (AGENTS.md §1 non-goals).

---

## 8. Testability

Stub/fake `HttpClient` returning prepared `HttpResponse` values or raising
prepared `VeracodeApiError` subclasses — same approach as
[target-management/requirements.md §13](../target-management/requirements.md#13-testability).
`wait_for_completion()` is tested by stubbing `AnalysisRunsService.get`
(or the underlying `HttpClient`) to return a scripted sequence of statuses,
and monkeypatching `time.sleep` so tests run instantly without a real
`poll_interval` delay.
