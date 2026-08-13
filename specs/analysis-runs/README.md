# Analysis Runs

## Purpose

Analysis Runs is the SDK interface for executing and monitoring DAST scans
against an existing Target: starting a scan, stopping it, listing/inspecting
past and current runs, waiting for a run to finish, and downloading its
report.

This module does not configure *what* gets scanned (Target Management,
Analysis Profiles, Scanner Configuration, Authentication Configuration) — it
only starts, stops, monitors, and reports on scans against a Target that is
already fully configured.

> **Phase:** 3 - Execute Scans

---

## Scope

This module implements the Analysis Run operations exposed by the Target
Configuration Service:

- Start an analysis run for a Target.
- Stop a running analysis run.
- List analysis runs for a Target.
- Get a single analysis run (used to check status).
- Wait for an analysis run to reach a terminal status.
- Download an analysis run's report (PDF, CSV, or JUnit).

This module does **not** manage:

- Target creation, update, or deletion.
- Analysis Profile, Scanner, Scanner Variable, Authentication, or ISM
  Gateway configuration.
- Discovered Targets.
- Schedules.
- Application/Findings/Policy data (AppSec domain).

Those capabilities belong to their respective SDK modules, or to a later
phase.

---

## Dependencies

This specification depends on the following completed modules:

- Authentication
- Shared HTTP Client
- Target Management

Analysis Runs requires an existing, already-configured Target. The SDK never
creates or configures a Target as a side effect of an Analysis Runs
operation.

---

## Relationship with Target Management

Target Management owns the Target resource. Analysis Runs operates on an
already existing Target by using its `target_id`.

Typical workflow:

```python
target = client.targets.get_by_name("My API Target")

run = client.analysis_runs.start(target.target_id)

client.analysis_runs.wait_for_completion(target.target_id, run.analysis_run_id)
```

The module never resolves Targets by name and never performs Target
creation or configuration.

---

## Public SDK API

The public SDK should read similarly to:

```python
client.analysis_runs.start(target_id)

client.analysis_runs.stop(target_id)

client.analysis_runs.list(target_id)

client.analysis_runs.get(target_id, analysis_run_id)

client.analysis_runs.wait_for_completion(target_id, analysis_run_id)

client.analysis_runs.get_report(target_id, analysis_run_id, "pdf", "report.pdf")
```

---

## Start Analysis

```python
run = client.analysis_runs.start(target_id)

print(run.analysis_run_id)
print(run.status)
```

Raises `VeracodeValidationError`/`VeracodeApiError` (via the HTTP Client) if
Veracode rejects the request — for example if an analysis is already in
progress for this Target.

---

## Stop Analysis

Stops a running analysis. `action` controls whether partial results are
kept:

```python
from veracode_dast.models.analysis_run import StopActionType

client.analysis_runs.stop(target_id, action=StopActionType.STOP_SAVE)
```

`action` defaults to `StopActionType.STOP_DELETE`, matching the Veracode
API's own default. `action` also accepts a plain string (`action=
"STOP_SAVE"`) — same convention as `get_report()`'s `format` — validated
against the two known values before any HTTP call.

---

## List Analysis Runs

```python
page = client.analysis_runs.list(target_id)

for run in page.items:
    print(run.analysis_run_id, run.status)
```

---

## Get Analysis Run

```python
run = client.analysis_runs.get(target_id, analysis_run_id)

print(run.status)
```

---

## Wait for Completion

Blocks, polling `get()` on an interval, until the analysis run reaches a
terminal status (`FINISHED`, `STOPPED`, or `FAILED`):

```python
from veracode_dast.models.target import TargetStatus

run = client.analysis_runs.wait_for_completion(
    target_id,
    analysis_run_id,
    poll_interval=15,
    timeout=3600,
)

if run.status != TargetStatus.FINISHED:
    raise RuntimeError(f"Scan did not finish successfully: {run.status}")
```

`timeout` is optional (`None` by default — waits indefinitely). If the
timeout elapses before the run reaches a terminal status,
`AnalysisRunTimeoutError` is raised.

`timeout` is a **soft bound, not an exact deadline**: elapsed time is only
checked once per poll, so the actual failure can occur up to
approximately one `poll_interval` plus one HTTP request's duration after
the nominal `timeout` value.

---

## Download Report

```python
client.analysis_runs.get_report(
    target_id,
    analysis_run_id,
    "pdf",
    "scan-report.pdf",
)
```

`format` accepts `"pdf"`, `"csv"`, or `"junit"`. The SDK writes the report
bytes to `destination_path` and returns the resolved `Path` — it never
parses or interprets the report contents.

---

## Returned Model

```python
AnalysisRun
```

Example:

```python
AnalysisRun(
    analysis_run_id="uuid5678912345678912345678912347",
    target_id="target-id",
    scan_number=1,
    started_at="2026-08-11T10:00:00Z",
    finished_at=None,
    url="https://example.com",
    target_protocol=Protocol.HTTPS,
    scan_type=AnalysisRunScanType.ENTERPRISE,
    status=TargetStatus.RUNNING,
    started_by_name="jane.doe",
    max_cvss=None,
    max_duration=14400,
    max_crawl_duration=3600,
    result_import_status=None,
)
```

---

## Exceptions

The service may raise:

- `AnalysisRunValidationError` — blank `target_id`/`analysis_run_id`, an
  unknown report `format`, an unknown stop `action`, an invalid
  `destination_path`, or an invalid `poll_interval`/`timeout`.
- `AnalysisRunTimeoutError` — `wait_for_completion()` exceeded its `timeout`
  before reaching a terminal status.
- `VeracodeAuthenticationError`, `VeracodeAuthorizationError`,
  `VeracodeNotFoundError`, `VeracodeValidationError`, `VeracodeApiError` —
  propagated unchanged from the HTTP Client.

---

## Out of Scope

This phase does not include:

- The legacy `GET /analysis_run/report/{target_id}` endpoint (target-scoped,
  no format selection, redirect-based). This is an intentional SDK scope
  decision, not a claim that the two endpoints are equivalent: this
  module's supported workflow (`start()` → `wait_for_completion()` →
  `get_report()`) always operates on a specific `AnalysisRun` and therefore
  always has its `analysis_run_id` in hand, so the SDK exposes only the
  analysis-run-scoped, format-selectable report endpoint.
- Discovered Targets (listing, ignoring, mapping).
- Schedules.
- Parsing or interpreting downloaded report contents.
- A combined `run_and_wait()`/`start_and_wait()` convenience — `start()` and
  `wait_for_completion()` are composed by the caller.

Those capabilities belong to future specifications, or are intentionally
left as caller composition.

---

## OpenAPI Review

Source: `openApi/Veracode-veracode-dast-target-configuration-service-api-1.0.0-resolved.json`.
See [requirements.md §0](requirements.md#0-openapi-review) for the full
endpoint and schema review.

---

## Expected Result

After this specification is implemented, SDK consumers should be able to
run a complete scan-execution workflow using only this module and Target
Management:

```python
client = VeracodeClient()

target = client.targets.get_by_name("My API Target")
run = client.analysis_runs.start(target.target_id)
finished = client.analysis_runs.wait_for_completion(
    target.target_id, run.analysis_run_id, timeout=3600
)
client.analysis_runs.get_report(
    target.target_id, finished.analysis_run_id, "pdf", "report.pdf"
)
```

This keeps Analysis Runs focused on scan execution and monitoring, while
Target Management, Analysis Profiles, and Scanner Configuration remain
responsible for what gets scanned and how.
