from veracode_dast.models.analysis_run import (
    AnalysisRun,
    AnalysisRunPage,
    AnalysisRunScanType,
    ResultImportStatus,
)
from veracode_dast.models.target import Protocol, TargetStatus


def _analysis_run_api_fixture(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "analysis_run_id": "run-1",
        "target_id": "t-1",
        "scan_number": 1,
        "started_at": "2026-08-11T10:00:00Z",
        "url": "https://example.com",
        "target_protocol": "HTTPS",
        "scan_type": "ENTERPRISE",
        "started_by_name": "jane.doe",
        "max_duration": 14400,
        "max_crawl_duration": 3600,
    }
    data.update(overrides)
    return data


def test_analysis_run_from_api_round_trips_required_fields() -> None:
    run = AnalysisRun.from_api(_analysis_run_api_fixture())

    assert run.analysis_run_id == "run-1"
    assert run.target_id == "t-1"
    assert run.scan_number == 1
    assert run.started_at == "2026-08-11T10:00:00Z"
    assert run.url == "https://example.com"
    assert run.target_protocol == Protocol.HTTPS
    assert run.scan_type == AnalysisRunScanType.ENTERPRISE
    assert run.started_by_name == "jane.doe"
    assert run.max_duration == 14400
    assert run.max_crawl_duration == 3600
    assert run.finished_at is None
    assert run.status is None
    assert run.max_cvss is None
    assert run.result_import_status is None


def test_analysis_run_from_api_ignores_deprecated_fields() -> None:
    run = AnalysisRun.from_api(
        _analysis_run_api_fixture(
            id=12345,
            project_uuid="legacy-uuid",
            protocol=1,
            environment=1,
            started_by=99,
            estimated_duration=120,
        )
    )

    assert not hasattr(run, "id")
    assert not hasattr(run, "project_uuid")
    assert not hasattr(run, "protocol")
    assert not hasattr(run, "environment")
    assert not hasattr(run, "started_by")
    assert not hasattr(run, "estimated_duration")


def test_analysis_run_from_api_reads_optional_fields() -> None:
    run = AnalysisRun.from_api(
        _analysis_run_api_fixture(
            finished_at="2026-08-11T11:00:00Z",
            status="RUNNING",
            max_cvss=7.5,
            result_import_status="COMPLETED",
        )
    )

    assert run.finished_at == "2026-08-11T11:00:00Z"
    assert run.status == TargetStatus.RUNNING
    assert run.max_cvss == 7.5
    assert run.result_import_status == ResultImportStatus.COMPLETED


def test_analysis_run_page_from_api_round_trips_and_hides_links() -> None:
    data = {
        "_embedded": {"analysis_runs": [_analysis_run_api_fixture()]},
        "_links": {"self": {"href": "https://example.com"}},
        "page": {"size": 10, "total_elements": 1, "total_pages": 1, "number": 0},
    }

    page = AnalysisRunPage.from_api(data)

    assert len(page.items) == 1
    assert page.items[0].analysis_run_id == "run-1"
    assert page.total_elements == 1
    assert not hasattr(page, "_links")
