"""Typed models for the DAST Target Configuration Service's Analysis Runs
resource."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from veracode_dast.models.target import Protocol, TargetStatus


class AnalysisRunScanType(StrEnum):
    """Scan type for an Analysis Run.

    Intentionally follows the `AnalysisRun.scan_type` OpenAPI schema
    exactly (`QUICK`, `ENTERPRISE`) and is independent of Target
    Management's `ScanType` (`QUICK`, `FULL`, `ENTERPRISE`) — the two
    enums model two different OpenAPI schemas for two different resources,
    and `Target.scan_type` allowing `FULL` has no bearing on what
    `AnalysisRun.scan_type` accepts. Kept as a separate class rather than
    reusing `ScanType` so an invalid `FULL` value can never be constructed
    for this field.
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
    """A Veracode DAST Analysis Run.

    Every field marked `deprecated: true` on the OpenAPI `AnalysisRun`
    schema (`id`, `project_uuid`, `protocol`, `environment`, `started_by`,
    `estimated_duration`) is intentionally omitted.

    Attributes:
        analysis_run_id: The analysis run's unique identifier.
        target_id: The ID of the Target this run belongs to.
        scan_number: The specific analysis run number for the Target.
        started_at: When the run started (UTC datetime string).
        url: The target URL scanned by this run.
        target_protocol: The protocol scanned by this run.
        scan_type: The scan depth used for this run.
        started_by_name: The name of the user who started the run.
        max_duration: The maximum duration in effect for this run.
        max_crawl_duration: The maximum crawl duration in effect for this run.
        finished_at: When the run finished, if it has.
        status: The run's current status, if known.
        max_cvss: The highest CVSS score found, if any.
        result_import_status: The status of importing this run's results
            into a linked Application, if applicable.
    """

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
        """Builds an `AnalysisRun` from a Target Configuration Service response.

        Args:
            data: The raw analysis run object from the API response.

        Returns:
            The corresponding `AnalysisRun`.
        """
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
    """One page of `GET /targets/{target_id}/analysis_runs` results.

    Attributes:
        items: The analysis runs on this page.
        page_number: The zero-based page number.
        page_size: The number of items requested per page.
        total_pages: The total number of pages available.
        total_elements: The total number of analysis runs across all pages.
    """

    items: list[AnalysisRun]
    page_number: int
    page_size: int
    total_pages: int
    total_elements: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AnalysisRunPage:
        """Builds an `AnalysisRunPage` from a paged API response.

        Args:
            data: The raw HAL-shaped response body.

        Returns:
            The corresponding `AnalysisRunPage`.
        """
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
