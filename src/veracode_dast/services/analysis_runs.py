"""Analysis Runs: start, stop, monitor, and report on DAST scans for
existing Targets.

Never manages Target lifecycle or scan configuration — every method takes
an existing `target_id`. Never depends on Target Management, Analysis
Profiles, or Scanner Configuration beyond that.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Final

from veracode_dast.exceptions import AnalysisRunTimeoutError, AnalysisRunValidationError
from veracode_dast.models.analysis_run import (
    AnalysisRun,
    AnalysisRunPage,
    ReportFormat,
    StopActionType,
)
from veracode_dast.models.target import TargetStatus

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

_ANALYSIS_RUN_PATH: Final = "/analysis_run"
_STOP_PATH: Final = "/analysis_run/{target_id}/stop"
_RUNS_PATH: Final = "/targets/{target_id}/analysis_runs"
_RUN_PATH: Final = "/targets/{target_id}/analysis_runs/{analysis_run_id}"
_REPORT_PATH: Final = "/targets/{target_id}/analysis_runs/{analysis_run_id}/report/{format}"

_TERMINAL_STATUSES: Final = frozenset(
    {TargetStatus.FINISHED, TargetStatus.STOPPED, TargetStatus.FAILED}
)

logger = logging.getLogger(__name__)


class AnalysisRunsService:
    """Starts, stops, monitors, and reports on Analysis Runs for existing
    Targets."""

    def __init__(self, http_client: HttpClient) -> None:
        """Initializes the service.

        Args:
            http_client: An `HttpClient` configured with
                `TARGET_CONFIGURATION_SERVICE_BASE_URL` — typically the
                same instance already constructed for `TargetsService`.
        """
        self._http_client = http_client

    def start(self, target_id: str) -> AnalysisRun:
        """Starts a new Analysis Run for a Target.

        Args:
            target_id: The target's unique identifier.

        Returns:
            The started `AnalysisRun`.

        Raises:
            AnalysisRunValidationError: If `target_id` is blank.
            VeracodeApiError: If Veracode rejects the request, e.g. an
                analysis is already in progress for this Target.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        response = self._http_client.post(_ANALYSIS_RUN_PATH, json={"id": target_id})
        run = AnalysisRun.from_api(response.data)  # type: ignore[arg-type]
        logger.info("Started analysis run %s for target %s", run.analysis_run_id, target_id)
        return run

    def stop(
        self, target_id: str, *, action: StopActionType | str = StopActionType.STOP_DELETE
    ) -> None:
        """Stops a running Analysis Run for a Target.

        Args:
            target_id: The target's unique identifier.
            action: Whether to delete or save partial results. Accepts a
                `StopActionType` member or an equivalent plain string.
                Defaults to `StopActionType.STOP_DELETE`.

        Raises:
            AnalysisRunValidationError: If `target_id` is blank, or
                `action` is not a recognized `StopActionType` value.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        stop_action = self._validate_action(action)
        self._http_client.post(
            _STOP_PATH.format(target_id=target_id), params={"action": stop_action.value}
        )
        logger.info("Stopped analysis run for target %s (action=%s)", target_id, stop_action.value)

    def list(self, target_id: str, *, page: int = 0, limit: int = 10) -> AnalysisRunPage:
        """Lists Analysis Runs for a Target, one page at a time.

        Args:
            target_id: The target's unique identifier.
            page: The zero-based page number to fetch.
            limit: The number of items per page (10-200).

        Returns:
            The requested page of Analysis Runs.

        Raises:
            AnalysisRunValidationError: If `target_id` is blank.
            VeracodeNotFoundError: If no target exists with that ID.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        response = self._http_client.get(
            _RUNS_PATH.format(target_id=target_id), params={"page": page, "limit": limit}
        )
        return AnalysisRunPage.from_api(response.data)  # type: ignore[arg-type]

    def get(self, target_id: str, analysis_run_id: str) -> AnalysisRun:
        """Gets one Analysis Run by ID.

        Args:
            target_id: The target's unique identifier.
            analysis_run_id: The analysis run's unique identifier.

        Returns:
            The matching `AnalysisRun`.

        Raises:
            AnalysisRunValidationError: If `target_id` or `analysis_run_id`
                is blank.
            VeracodeNotFoundError: If no matching target/analysis run exists.
        """
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
        """Polls `get()` until the Analysis Run reaches a terminal status.

        Terminal statuses are `FINISHED`, `STOPPED`, and `FAILED`; `RUNNING`
        and `STOPPING` are non-terminal and cause polling to continue. A
        run with no `status` yet is also treated as non-terminal.

        `timeout` is a soft bound, not an exact deadline: elapsed time is
        checked once per poll, immediately after `get()` returns and before
        sleeping, so the actual failure can occur up to approximately one
        `poll_interval` plus one HTTP request's duration after the nominal
        `timeout` value — never less.

        Args:
            target_id: The target's unique identifier.
            analysis_run_id: The analysis run's unique identifier.
            poll_interval: Seconds to sleep between polls. Must be positive.
            timeout: Maximum seconds to wait before raising
                `AnalysisRunTimeoutError`. `None` waits indefinitely. If
                given, must be positive.

        Returns:
            The `AnalysisRun` once it reaches a terminal status.

        Raises:
            AnalysisRunValidationError: If `target_id`/`analysis_run_id` is
                blank, or `poll_interval`/`timeout` is not positive.
            AnalysisRunTimeoutError: If `timeout` elapses before the run
                reaches a terminal status.
        """
        if poll_interval <= 0:
            raise AnalysisRunValidationError(
                "poll_interval must be positive", rule="poll_interval_must_be_positive"
            )
        if timeout is not None and timeout <= 0:
            raise AnalysisRunValidationError(
                "timeout must be positive", rule="timeout_must_be_positive"
            )

        start_time = time.monotonic()
        while True:
            run = self.get(target_id, analysis_run_id)
            logger.debug("Polled analysis run %s: status=%s", analysis_run_id, run.status)
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
            # up to ~poll_interval + one request late.
            time.sleep(poll_interval)

    def get_report(
        self,
        target_id: str,
        analysis_run_id: str,
        format: ReportFormat | str,
        destination_path: str | Path,
    ) -> Path:
        """Downloads an Analysis Run's report to a local file.

        Args:
            target_id: The target's unique identifier.
            analysis_run_id: The analysis run's unique identifier.
            format: The report format. Accepts a `ReportFormat` member or
                an equivalent plain string (`"pdf"`, `"csv"`, `"junit"`).
            destination_path: Local path to write the downloaded report to.

        Returns:
            The resolved destination path.

        Raises:
            AnalysisRunValidationError: If `target_id`/`analysis_run_id` is
                blank, `format` is not a recognized value, or
                `destination_path`'s parent directory does not exist.
            VeracodeNotFoundError: If no matching target/analysis run exists.
        """
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
            report_format.value,
            analysis_run_id,
            destination,
        )
        response = self._http_client.get(
            _REPORT_PATH.format(
                target_id=target_id, analysis_run_id=analysis_run_id, format=report_format.value
            ),
            raw=True,
        )
        content = response.data or b""
        destination.write_bytes(content)  # type: ignore[arg-type]
        logger.info(
            "Download completed for analysis run %s: %d byte(s)", analysis_run_id, len(content)
        )
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
