"""The Phase 1 MVP end-to-end workflow: resolve a Team, create a Target,
upload its API Specification, and retrieve the specification's metadata.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/end_to_end_workflow_example.py \\
        --team-name "Development" --target-name "My API" --target-url api.example.com \\
        --spec-file examples/sample-openapi.yaml
"""

import argparse
import dataclasses
import json
import sys

from veracode_dast.client import VeracodeClient
from veracode_dast.exceptions import VeracodeApiError
from veracode_dast.models.target import (
    Protocol,
    ScanType,
    TargetCreate,
    TargetType,
    TargetUpdate,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team-name", required=True)
    parser.add_argument("--target-name", required=True)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--target-type", type=TargetType, choices=list(TargetType), default=TargetType.API)
    parser.add_argument("--scan-type", type=ScanType, choices=list(ScanType), default=ScanType.ENTERPRISE)
    args = parser.parse_args()

    client = VeracodeClient()

    team = client.teams.get_by_name(args.team_name)
    print(json.dumps(dataclasses.asdict(team), indent=2))

    spec_url = f"https://{args.target_url}/openapi.yaml"
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

    client.api_specifications.upload(target.target_id, args.spec_file)
    spec = client.api_specifications.get(target.target_id)
    print(json.dumps(dataclasses.asdict(spec), indent=2))


if __name__ == "__main__":
    try:
        main()
    except VeracodeApiError as e:
        print(json.dumps({"status_code": e.status_code, "response_body": e.response_body}, indent=2))
        sys.exit(1)
