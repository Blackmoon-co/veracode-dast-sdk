# Design — Analysis Runs

Implements [requirements.md](requirements.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Extends
[Target Management](../target-management/design.md) (reuses its base-URL
constant and `Protocol`/`TargetStatus` models, same pattern as
[API Specification Management](../api-specification-management/design.md)
and [Scanner Profiles](../scanners-profiles/design.md)).

---

## 1. Overview

Analysis Runs is a plain CRUD-and-action service, the same shape as Target
Management, not a configuration-driven pipeline like Scanner Profiles or
Authentication. Five of its six methods (`start`, `stop`, `list`, `get`,
`get_report`) are single HTTP calls with request/response mapping.
`wait_for_completion()` is the one method with real logic: a bounded poll
loop built entirely on `get()` and the standard library.

## 2. Architecture

This feature adds one service and its models to the existing layered
architecture (AGENTS.md §3) — no new layer, no change to `HttpClient`:

```
VeracodeClient
      ↓
  HTTP Client              (reused, unmodified)
      ↓
AnalysisRunsService          ← THIS FEATURE
      ↓
AnalysisRun, AnalysisRunPage (models)
      ↓
  REST API  (DAST Target Configuration Service, same base URL as Targets)
```

`wait_for_completion()`'s poll loop:

```
get(target_id, analysis_run_id)
      ↓
status terminal? ──No──▶ time.sleep(poll_interval) ──▶ (loop)
      │                         ▲
     Yes                        │
      ↓                  timeout exceeded? ──Yes──▶ raise AnalysisRunTimeoutError
   return AnalysisRun
```

No new thread, process, or async runtime is introduced — this is a
synchronous blocking call, consistent with the rest of the SDK (`requests`
is synchronous throughout).

## 3. Components and Interfaces

### 3.1 `src/veracode_dast/models/analysis_run.py`

```python
class AnalysisRunScanType(StrEnum):
    """Scan type for an Analysis Run.

    Intentionally follows the `AnalysisRun.scan_type` OpenAPI schema
    exactly (`QUICK`, `ENTERPRISE`) and is independent of Target
    Management's `ScanType` (`QUICK`, `FULL`, `ENTERPRISE`) — the two
    enums model two different OpenAPI schemas for two different resources,
    and `Target.scan_type` allowing `FULL` has no bearing on what
    `AnalysisRun.scan_type` accepts. Kept as a separate class rather than
    reusing `ScanType` so an invalid `FULL` value can never be constructed
    for this field (requirements.md §0.2).
    """

    QUICK = "QUICK"
    ENTERPRISE = "ENTERPRISE"


class ResultImportStatus(StrEnum):
    """Status of importing an Analysis Run's results into a linked
    Application."""

    POLLING = "POLLING"
    REQUESTED = "REQUESTED"
    INPROGRESS = "INPROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    IGNORED = "IGNORED"
    INVALID = "INVALID"
    ERROR = "ERROR"


class StopActionType(StrEnum):
    """Action to take when stopping an Analysis Run."""

    STOP_DELETE = "STOP_DELETE"
    STOP_SAVE = "STOP_SAVE"


class ReportFormat(StrEnum):
    """Format for a downloaded Analysis Run report."""

    PDF = "pdf"
    CSV = "csv"
    JUNIT = "junit"


@dataclass(frozen=True)
class AnalysisRun:
    analysis_run_id: str
    target_id: str
    scan_number: int
    started_at: str
    url: str
    target_protocol: Protocol
    scan_type: AnalysisRunScanType
    started_by_name: str
    max_duration: int
    max_crawl_duration: int
    finished_at: str | None = None
    status: TargetStatus | None = None
    max_cvss: float | None = None
    result_import_status: ResultImportStatus | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AnalysisRun:
        """Maps an `AnalysisRun` API object, skipping every field marked
        `deprecated: true` in the OpenAPI schema (requirements.md §0.2,
        §5.9): `id`, `project_uuid`, `protocol`, `environment`,
        `started_by`, `estimated_duration`."""
        status = data.get("status")
        result_import_status = data.get("result_import_status")
        return cls(
            analysis_run_id=data["analysis_run_id"],
            target_id=data["target_id"],
            scan_number=data["scan_number"],
            started_at=data["started_at"],
            url=data["url"],
            target_protocol=Protocol(data["target_protocol"]),
            scan_type=AnalysisRunScanType(data["scan_type"]),
            started_by_name=data["started_by_name"],
            max_duration=data["max_duration"],
            max_crawl_duration=data["max_crawl_duration"],
            finished_at=data.get("finished_at"),
            status=TargetStatus(status) if status else None,
            max_cvss=data.get("max_cvss"),
            result_import_status=(
                ResultImportStatus(result_import_status) if result_import_status else None
            ),
        )


@dataclass(frozen=True)
class AnalysisRunPage:
    items: list[AnalysisRun]
    page_number: int
    page_size: int
    total_pages: int
    total_elements: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AnalysisRunPage:
        """Same `_embedded`/`page` HAL shape as `TargetPage.from_api`
        (target-management/design.md)."""
        items = [
            AnalysisRun.from_api(item)
            for item in data.get("_embedded", {}).get("analysis_runs", [])
        ]
        page = data["page"]
        return cls(
            items=items,
            page_number=page["number"],
            page_size=page["size"],
            total_pages=page["total_pages"],
            total_elements=page["total_elements"],
        )
```

`Protocol` and `TargetStatus` are **imported** from `models/target.py`, not
redefined — same rule already established for
`TARGET_CONFIGURATION_SERVICE_BASE_URL` reuse across services.

### 3.2 `src/veracode_dast/exceptions.py` (extended)

```python
class AnalysisRunValidationError(VeracodeSDKError):
    """Raised for SDK-level Analysis Run parameter validation failures
    (requirements.md §5.1-5.6, 5.10).

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        self.rule = rule
        super().__init__(message)


class AnalysisRunTimeoutError(VeracodeSDKError):
    """Raised when `wait_for_completion()` exceeds its `timeout` before the
    Analysis Run reaches a terminal status (requirements.md §3.5).

    Attributes:
        target_id: The target's unique identifier.
        analysis_run_id: The analysis run's unique identifier.
        elapsed: Seconds elapsed before the timeout fired.
        last_status: The last observed status, or None if no successful
            `get()` call completed before the timeout.
    """

    def __init__(
        self,
        target_id: str,
        analysis_run_id: str,
        *,
        elapsed: float,
        last_status: TargetStatus | None,
    ) -> None:
        self.target_id = target_id
        self.analysis_run_id = analysis_run_id
        self.elapsed = elapsed
        self.last_status = last_status
        super().__init__(
            f"Analysis run {analysis_run_id} did not reach a terminal status "
            f"within {elapsed:.0f}s (last status: {last_status})"
        )
```

Both subclass `VeracodeSDKError` directly, following the same convention as
every other feature's validation/domain error pair.

### 3.3 `src/veracode_dast/services/analysis_runs.py`

```python
from veracode_dast.services.targets import TARGET_CONFIGURATION_SERVICE_BASE_URL

_ANALYSIS_RUN_PATH = "/analysis_run"
_STOP_PATH = "/analysis_run/{target_id}/stop"
_RUNS_PATH = "/targets/{target_id}/analysis_runs"
_RUN_PATH = "/targets/{target_id}/analysis_runs/{analysis_run_id}"
_REPORT_PATH = "/targets/{target_id}/analysis_runs/{analysis_run_id}/report/{format}"

_TERMINAL_STATUSES: Final = frozenset(
    {TargetStatus.FINISHED, TargetStatus.STOPPED, TargetStatus.FAILED}
)

logger = logging.getLogger(__name__)


class AnalysisRunsService:
    """Starts, stops, monitors, and reports on Analysis Runs for existing
    Targets."""

    def __init__(self, http_client: HttpClient) -> None:
        self._http_client = http_client

    def start(self, target_id: str) -> AnalysisRun:
        self._require_non_blank(target_id, rule="target_id_required")
        response = self._http_client.post(_ANALYSIS_RUN_PATH, json={"id": target_id})
        run = AnalysisRun.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Started analysis run %s for target %s", run.analysis_run_id, target_id)
        return run

    def stop(
        self, target_id: str, *, action: StopActionType | str = StopActionType.STOP_DELETE
    ) -> None:
        self._require_non_blank(target_id, rule="target_id_required")
        stop_action = self._validate_action(action)
        self._http_client.post(
            _STOP_PATH.format(target_id=target_id), params={"action": stop_action.value}
        )
        logger.info("Stopped analysis run for target %s (action=%s)", target_id, stop_action.value)

    def list(self, target_id: str, *, page: int = 0, limit: int = 10) -> AnalysisRunPage:
        self._require_non_blank(target_id, rule="target_id_required")
        response = self._http_client.get(
            _RUNS_PATH.format(target_id=target_id), params={"page": page, "limit": limit}
        )
        return AnalysisRunPage.from_api(response.data)  # type: ignore[arg-type]

    def get(self, target_id: str, analysis_run_id: str) -> AnalysisRun:
        self._require_non_blank(target_id, rule="target_id_required")
        self._require_non_blank(analysis_run_id, rule="analysis_run_id_required")
        response = self._http_client.get(
            _RUN_PATH.format(target_id=target_id, analysis_run_id=analysis_run_id)
        )
        return AnalysisRun.from_api(response.data)  # type: ignore[arg-type]

    def wait_for_completion(
        self,
        target_id: str,
        analysis_run_id: str,
        *,
        poll_interval: float = 15.0,
        timeout: float | None = None,
    ) -> AnalysisRun:
        if poll_interval <= 0:
            raise AnalysisRunValidationError(
                "poll_interval must be positive", rule="poll_interval_must_be_positive"
            )
        if timeout is not None and timeout <= 0:
            raise AnalysisRunValidationError(
                "timeout must be positive", rule="timeout_must_be_positive"
            )

        start_time = time.monotonic()
        run: AnalysisRun | None = None
        while True:
            run = self.get(target_id, analysis_run_id)
            logger.debug(
                "Polled analysis run %s: status=%s", analysis_run_id, run.status
            )
            if run.status in _TERMINAL_STATUSES:
                logger.info(
                    "Analysis run %s reached terminal status %s", analysis_run_id, run.status
                )
                return run
            elapsed = time.monotonic() - start_time
            if timeout is not None and elapsed >= timeout:
                raise AnalysisRunTimeoutError(
                    target_id, analysis_run_id, elapsed=elapsed, last_status=run.status
                )
            # `timeout` is a soft bound: checked once per iteration, before
            # sleeping — so a run that turns terminal or a timeout that
            # elapses mid-sleep is only observed on the *next* iteration,
            # up to ~poll_interval + one request late (requirements.md §3.5).
            time.sleep(poll_interval)

    def get_report(
        self,
        target_id: str,
        analysis_run_id: str,
        format: ReportFormat | str,
        destination_path: str | Path,
    ) -> Path:
        self._require_non_blank(target_id, rule="target_id_required")
        self._require_non_blank(analysis_run_id, rule="analysis_run_id_required")
        report_format = self._validate_format(format)
        destination = Path(destination_path)
        if not destination.parent.is_dir():
            raise AnalysisRunValidationError(
                f"Destination directory does not exist: {destination.parent}",
                rule="destination_parent_must_exist",
            )

        logger.info(
            "Downloading %s report for analysis run %s to %s",
            report_format.value, analysis_run_id, destination,
        )
        response = self._http_client.get(
            _REPORT_PATH.format(
                target_id=target_id, analysis_run_id=analysis_run_id, format=report_format.value
            ),
            raw=True,
        )
        content = response.data or b""
        destination.write_bytes(content)  # type: ignore[arg-type]
        logger.info("Download completed for analysis run %s: %d byte(s)", analysis_run_id, len(content))
        return destination

    @staticmethod
    def _validate_action(action: StopActionType | str) -> StopActionType:
        if isinstance(action, StopActionType):
            return action
        try:
            return StopActionType(action)
        except ValueError as exc:
            valid = ", ".join(member.value for member in StopActionType)
            raise AnalysisRunValidationError(
                f"Invalid stop action '{action}'; must be one of: {valid}",
                rule="invalid_stop_action",
            ) from exc

    @staticmethod
    def _validate_format(format: ReportFormat | str) -> ReportFormat:
        if isinstance(format, ReportFormat):
            return format
        try:
            return ReportFormat(format)
        except ValueError as exc:
            valid = ", ".join(member.value for member in ReportFormat)
            raise AnalysisRunValidationError(
                f"Invalid report format '{format}'; must be one of: {valid}",
                rule="invalid_report_format",
            ) from exc

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise AnalysisRunValidationError("Value must not be blank", rule=rule)
```

`TARGET_CONFIGURATION_SERVICE_BASE_URL` is **imported**, not redefined —
same rule already established by every prior Phase 2 service.

`wait_for_completion()` uses `time.monotonic()` for elapsed-time tracking
(immune to wall-clock adjustments) and calls the module-level `time.sleep`
directly — no injected clock — matching requirements.md §4.6.

## 4. Service Responsibilities

| Responsibility | Owner |
|---|---|
| HTTP transport, HMAC auth, retries, status→exception mapping | `HttpClient` (unchanged) |
| Parameter validation (blank IDs, report format, stop action, poll/timeout values) | `AnalysisRunsService._require_non_blank` / `_validate_format` / `_validate_action` / inline checks |
| Poll-until-terminal loop | `AnalysisRunsService.wait_for_completion` |
| Building typed models from API responses | `AnalysisRun.from_api` / `AnalysisRunPage.from_api` |
| Writing report bytes to disk | `AnalysisRunsService.get_report` |
| Business-event logging | `AnalysisRunsService` |

## 5. Error Handling

| Failure | Exception | Raised by |
|---|---|---|
| Blank `target_id`/`analysis_run_id` | `AnalysisRunValidationError` | `AnalysisRunsService` |
| Invalid report `format` string | `AnalysisRunValidationError(rule="invalid_report_format")` | `AnalysisRunsService._validate_format` |
| Invalid stop `action` string | `AnalysisRunValidationError(rule="invalid_stop_action")` | `AnalysisRunsService._validate_action` |
| `get_report()` destination parent missing | `AnalysisRunValidationError(rule="destination_parent_must_exist")` | `AnalysisRunsService.get_report` |
| Non-positive `poll_interval`/`timeout` | `AnalysisRunValidationError` | `AnalysisRunsService.wait_for_completion` |
| `wait_for_completion()` exceeds `timeout` | `AnalysisRunTimeoutError` | `AnalysisRunsService.wait_for_completion` |
| HTTP 401 | `VeracodeAuthenticationError` | `HttpClient` (unchanged) |
| HTTP 403 | `VeracodeAuthorizationError` | `HttpClient` (unchanged) |
| HTTP 404 (unknown target/analysis run) | `VeracodeNotFoundError` | `HttpClient` (unchanged) |
| HTTP 400 (invalid target, or analysis already in progress) | `VeracodeApiError` | `HttpClient` (unchanged) |
| HTTP 422 | `VeracodeValidationError` | `HttpClient` (unchanged) |
| HTTP 500 | `VeracodeApiError` | `HttpClient` (unchanged) |

`HttpClient`'s `_STATUS_EXCEPTIONS` map (`client.py`) has no entry for
400 — it always falls through to the generic `VeracodeApiError` default.
`VeracodeValidationError` is raised only for 422. No endpoint in this
feature is documented to return 422 (requirements.md §0.3), so the 422 row
above is included only for completeness with the shared `HttpClient`
contract, not because this feature's endpoints are known to trigger it.

Client-side checks always raise before any HTTP call (requirements.md §5);
every HTTP Client exception propagates unmodified, including from within
`wait_for_completion()`'s loop — a transport failure on any poll aborts the
wait immediately rather than being retried or swallowed.

## 6. Testing Strategy

Location: `tests/models/test_analysis_run.py`,
`tests/services/test_analysis_runs.py`. Same stub-`HttpClient` approach as
Target Management — no mocking library, no real sockets; real filesystem
I/O only via `tmp_path` fixtures for `get_report()`.

Cases:

- `AnalysisRun.from_api`: full field mapping against a fixture shaped like
  §0.2, including the six deprecated fields present in the raw payload but
  absent from the constructed model (asserts they're silently dropped, not
  erroring).
- `AnalysisRunPage.from_api`: `_embedded.analysis_runs` + `page.*`
  round-trip, same shape as `test_target.py`'s `TargetPage` case.
- `AnalysisRunsService.start()`: request body is exactly `{"id":
  target_id}`; 200 → `AnalysisRun`; blank `target_id` → validation error,
  no HTTP call.
- `AnalysisRunsService.stop()`: default `action` sends
  `action=STOP_DELETE`; explicit `StopActionType.STOP_SAVE` and the
  equivalent plain string `"STOP_SAVE"` both send `action=STOP_SAVE`;
  returns `None`; an unrecognized string (e.g. `"cancel"`) raises
  `AnalysisRunValidationError(rule="invalid_stop_action")` before any HTTP
  call.
- `AnalysisRunsService.list()`/`get()`: same pattern as
  `TargetsService.list()`/`get()`; blank IDs raise before any HTTP call;
  404 propagates `VeracodeNotFoundError` unchanged.
- `AnalysisRunsService.wait_for_completion()`, with `time.sleep`
  monkeypatched to a no-op and `AnalysisRunsService.get` stubbed to return a
  scripted sequence of `AnalysisRun` objects:
  - `RUNNING`, `RUNNING`, `FINISHED` → three `get()` calls, two `sleep()`
    calls, returns the `FINISHED` run.
  - `status=None` → treated as non-terminal, loop continues.
  - a sequence that never reaches a terminal status, with a monkeypatched
    `time.monotonic` advancing past `timeout` → raises
    `AnalysisRunTimeoutError` with the last observed status.
  - `poll_interval=0` / `timeout=0` → `AnalysisRunValidationError`, no
    `get()` call.
- `AnalysisRunsService.get_report()`: writes stubbed raw bytes to
  `tmp_path`; returns the resolved `Path`; `format="xml"` raises before any
  HTTP call; missing destination parent directory raises before any HTTP
  call; 404 propagates unchanged.
- `caplog` assertion: no captured log record at INFO/DEBUG contains report
  file contents.

## 7. File Layout Introduced by This Feature

```
src/veracode_dast/
├── models/analysis_run.py      # AnalysisRunScanType, ResultImportStatus, StopActionType,
│                                #   ReportFormat, AnalysisRun, AnalysisRunPage
├── services/analysis_runs.py   # AnalysisRunsService
├── client.py                   # (+) self.analysis_runs, sharing client.targets' HttpClient
└── exceptions.py               # (+) AnalysisRunValidationError, AnalysisRunTimeoutError

tests/
├── models/test_analysis_run.py
└── services/test_analysis_runs.py

examples/
└── analysis_runs_example.py
```

## 8. Traceability

| Component | Requirements covered |
|---|---|
| `AnalysisRunsService.start` | 3.1, 3.7 |
| `AnalysisRunsService.stop`, `_validate_action` | 3.2, 3.7, 5.10 |
| `AnalysisRunsService.list` | 3.3, 3.7 |
| `AnalysisRunsService.get` | 3.4, 3.7 |
| `AnalysisRunsService.wait_for_completion` | 3.5, 5.5-5.7 |
| `AnalysisRunsService.get_report` | 3.6, 5.3-5.4 |
| `AnalysisRun`, `AnalysisRunPage`, `AnalysisRunScanType`, `ResultImportStatus`, `StopActionType`, `ReportFormat` | §0.2, 5.9 |
| `AnalysisRunValidationError`, `AnalysisRunTimeoutError` | §5 |
| No legacy target-scoped report endpoint | §0.1.1, §7 (Out of Scope) |
| Public interface, `HttpClient` reuse | §2 (Goals), 4.3 |
| Testing strategy | §8 (Testability) |
