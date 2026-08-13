"""Starts, monitors, and reports on a DAST Analysis Run for an existing
Target — exercising every public AnalysisRunsService operation.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.
"""

import argparse

from veracode_dast.client import VeracodeClient
from veracode_dast.models.analysis_run import StopActionType

_DESCRIPTION = "Start, monitor, stop, and download reports for Veracode DAST Analysis Runs."

_EPILOG = """\
Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Examples:
  # Run a scan by Target name (resolved via TargetsService.get_by_name)
  python examples/analysis_runs_example.py --target-name "sdk-demo"

  # Run a scan and request a report
  python examples/analysis_runs_example.py --target-name "sdk-demo" \\
      --report pdf --output .\\report.pdf

  # Run a scan by Target ID instead of name
  python examples/analysis_runs_example.py --target-id <existing-target-id>

  # Inspect an existing Analysis Run instead of starting a new one
  python examples/analysis_runs_example.py --target-name "sdk-demo" \\
      --analysis-run-id <existing-run-id>

  # Stop a running Analysis Run instead of waiting for completion
  python examples/analysis_runs_example.py --target-name "sdk-demo" --stop
"""

_SEPARATOR = "-" * 50


def _section(title: str) -> None:
    print(f"\n{_SEPARATOR}\n{title}\n{_SEPARATOR}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=_DESCRIPTION,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--target-name", default=None, help="Target's display name, resolved via TargetsService"
    )
    target_group.add_argument("--target-id", default=None, help="Existing target's ID")
    parser.add_argument(
        "--analysis-run-id",
        default=None,
        help="Use an existing analysis run instead of starting a new one",
    )
    parser.add_argument(
        "--poll-interval", type=float, default=15.0, help="Seconds between completion polls"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Max seconds to wait for completion (default: wait indefinitely)",
    )
    parser.add_argument(
        "--report",
        default=None,
        choices=["pdf", "csv", "junit"],
        help="Report format to download after completion (default: skip the report)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Where to write the report (default: analysis-run-report.<format>)",
    )
    parser.add_argument(
        "--stop-action",
        default="STOP_DELETE",
        choices=["STOP_DELETE", "STOP_SAVE"],
        help="Action used when --stop is given",
    )
    parser.add_argument(
        "--stop", action="store_true", help="Stop the run instead of waiting for completion"
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    client = VeracodeClient()

    _section("Target")
    if args.target_name:
        target = client.targets.get_by_name(args.target_name)
        if target is None:
            parser.error(f"No target found with name: {args.target_name}")
        target_id = target.target_id
        print(f"Name: {args.target_name}")
        print(f"ID:   {target_id}")
    else:
        target_id = args.target_id
        print(f"ID:   {target_id}")

    existing_runs = client.analysis_runs.list(target_id)
    print(f"\nExisting Analysis Runs: {existing_runs.total_elements}")

    if args.analysis_run_id:
        _section("Using Existing Analysis Run")
        analysis_run_id = args.analysis_run_id
    else:
        _section("Starting Analysis Run")
        run = client.analysis_runs.start(target_id)
        analysis_run_id = run.analysis_run_id

    print(f"Analysis Run ID:\n{analysis_run_id}")

    current = client.analysis_runs.get(target_id, analysis_run_id)
    print(f"\nStatus:\n{current.status}")

    if args.stop:
        _section("Stopping Analysis Run")
        client.analysis_runs.stop(target_id, action=StopActionType(args.stop_action))
        print(f"Action: {args.stop_action}")
        return

    _section("Waiting for Completion")
    print("Polling until the analysis run reaches a terminal status...")
    finished = client.analysis_runs.wait_for_completion(
        target_id,
        analysis_run_id,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
    )
    print(f"\nFinal Status:\n{finished.status}")

    if args.report:
        _section("Report")
        print(f"Downloading {args.report.upper()} report...")
        output = args.output or f"analysis-run-report.{args.report}"
        destination = client.analysis_runs.get_report(
            target_id, analysis_run_id, args.report, output
        )
        print(f"Saved to:\n{destination}")


if __name__ == "__main__":
    main()
