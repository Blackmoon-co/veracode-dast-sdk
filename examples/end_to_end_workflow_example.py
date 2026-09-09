"""The full MVP end-to-end workflow: Phase 1 (resolve a Team, create a
Target, upload its API Specification, retrieve the specification's
metadata) always runs. Phase 2 steps (Analysis Profile rate_limit/
max_duration, Scanner Profiles, Authentications, Scanner Variables) are
each optional and only run if their corresponding flag is passed.

Pass --app-name to resolve a Veracode Application by name *before* the
Team (the script exits without creating anything if it doesn't exist) and
link the Target to it after creation.

Veracode fetches api_specification_file_url synchronously while creating an
API target, so it must be a real, reachable OpenAPI URL - a fabricated one
makes the origin return 502. If you only have a local file, leave
--spec-url unset: a known-good public spec is used just to get the target
created, then --spec-file is uploaded over it.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/end_to_end_workflow_example.py \\
        --team-name "Development" --target-name "My API" --target-url api.example.com \\
        --spec-file examples/sample-openapi.yaml \\
        --app-name "My App" \\
        --scanner-config specs/scanners-profiles/scanner-profile.json \\
        --auth-config specs/authentications/authentication.json \\
        --scanner-variables-config specs/scanner-variables/scanner-variables.json \\
        --rate-limit 300 --max-duration 120
"""

import argparse
import dataclasses
import json
import sys
import time
from typing import Any

from veracode_dast.client import VeracodeClient
from veracode_dast.exceptions import ApplicationNotFoundError, VeracodeApiError
from veracode_dast.models.analysis_profile import AnalysisProfile, AnalysisProfileUpdate
from veracode_dast.models.target import (
    Protocol,
    ScanType,
    TargetCreate,
    TargetType,
    TargetUpdate,
)

# A public OpenAPI Veracode can always GET, used to satisfy target creation
# when the caller has no hosted spec of their own. Replaced by --spec-file.
BOOTSTRAP_SPEC_URL = "https://petstore3.swagger.io/api/v3/openapi.json"


def _as_json(obj: Any) -> str:
    if isinstance(obj, list):
        return json.dumps([dataclasses.asdict(o) for o in obj], indent=2)
    return json.dumps(dataclasses.asdict(obj), indent=2)


def _resolve_analysis_profile(client: VeracodeClient, target_id: str) -> AnalysisProfile:
    """Finds the Analysis Profile Veracode creates for a Target.

    Creation is asynchronous with respect to Target creation, so this
    polls briefly rather than assuming it already exists.
    """
    for attempt in range(5):
        page = client.analysis_profiles.list(target_id=target_id)
        if page.items:
            return client.analysis_profiles.get(page.items[0].analysis_profile_id)
        if attempt < 4:
            time.sleep(2)
    raise RuntimeError(f"No Analysis Profile found for target {target_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team-name", required=True)
    parser.add_argument("--target-name", required=True)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--spec-file", required=True, help="Local OpenAPI JSON/YAML/HAR")
    parser.add_argument(
        "--spec-url",
        default=None,
        help="Hosted OpenAPI URL Veracode fetches at create time. "
        f"Defaults to a public bootstrap spec ({BOOTSTRAP_SPEC_URL}); "
        "--spec-file is uploaded over it afterwards.",
    )
    parser.add_argument(
        "--target-type", type=TargetType, choices=list(TargetType), default=TargetType.API
    )
    parser.add_argument(
        "--scan-type", type=ScanType, choices=list(ScanType), default=ScanType.ENTERPRISE
    )
    parser.add_argument("--scanner-config", default=None, help="Skipped if not provided")
    parser.add_argument("--auth-config", default=None, help="Skipped if not provided")
    parser.add_argument(
        "--scanner-variables-config", default=None, help="Skipped if not provided"
    )
    parser.add_argument("--rate-limit", type=int, default=None)
    parser.add_argument("--max-duration", type=int, default=None)
    parser.add_argument(
        "--app-name",
        default=None,
        help="Link the Target to this Veracode Application after creation. "
        "Resolved before the Team is; if no Application has this exact name, "
        "the script exits without creating a Target.",
    )
    args = parser.parse_args()

    client = VeracodeClient()

    # --- Application (resolved first, before Team/Target) ---
    app = None
    if args.app_name:
        try:
            app = client.applications.get_by_name(args.app_name)
        except ApplicationNotFoundError as exc:
            sys.exit(f"{exc}; not creating a target")
        print(json.dumps({"application_guid": app.guid, "application_name": app.name}, indent=2))

    # --- Phase 1: Team, Target, API Specification ---
    team = client.teams.get_by_name(args.team_name)
    print(json.dumps(dataclasses.asdict(team), indent=2))

    spec_url = args.spec_url or BOOTSTRAP_SPEC_URL
    print(f"Creating target with api_specification_file_url={spec_url}")
    target = client.targets.ensure(
        TargetCreate(
            name=args.target_name,
            url=args.target_url,
            protocol=Protocol.HTTPS,
            target_type=args.target_type,
            scan_type=args.scan_type,
            authorized_to_scan=True,
            is_sec_lead_only=False,
            teams=[team.team_id],
            api_specification_file_url=spec_url,
        )
    )
    target = client.targets.update_by_name(
        args.target_name,
        TargetUpdate(
            url=args.target_url,
            protocol=Protocol.HTTPS,
            api_specification_file_url=spec_url,
            teams=[team.team_id],
        ),
    )
    print(json.dumps(dataclasses.asdict(target), indent=2))

    if app is not None:
        client.targets.link(target.target_id, app.guid)
        print(f"Linked target {target.target_id} to application {app.guid}")

    client.api_specifications.upload(target.target_id, args.spec_file)
    spec = client.api_specifications.get(target.target_id)
    # If api_spec_name/type reflect the local file (not the bootstrap URL),
    # upload() replaced the spec and no hosted URL of your own is needed.
    print(json.dumps(dataclasses.asdict(spec), indent=2))

    # --- Phase 2: Analysis Profile, Scanners, Authentication, Scanner Variables ---
    profile = _resolve_analysis_profile(client, target.target_id)

    if args.rate_limit is not None or args.max_duration is not None:
        update_kwargs = {}
        if args.rate_limit is not None:
            update_kwargs["rate_limit"] = args.rate_limit
        if args.max_duration is not None:
            update_kwargs["max_duration"] = args.max_duration
        profile = client.analysis_profiles.update(
            profile.analysis_profile_id, AnalysisProfileUpdate(**update_kwargs)
        )
    print(json.dumps(dataclasses.asdict(profile), indent=2))

    if args.scanner_config is not None:
        scanners = client.scanners.update(profile.analysis_profile_id, args.scanner_config)
        print(_as_json(scanners))

    if args.auth_config is not None:
        auth = client.authentications.update(profile.analysis_profile_id, args.auth_config)
        print(_as_json(auth))

    if args.scanner_variables_config is not None:
        variables = client.scanner_variables.update(
            profile.analysis_profile_id, args.scanner_variables_config
        )
        print(_as_json(variables))


if __name__ == "__main__":
    try:
        main()
    except VeracodeApiError as e:
        print(
            json.dumps({"status_code": e.status_code, "response_body": e.response_body}, indent=2)
        )
        sys.exit(1)
