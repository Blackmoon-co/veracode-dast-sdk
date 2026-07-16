"""The Phase 1 MVP end-to-end workflow: resolve a Team, create a Target,
upload its API Specification, and retrieve the specification's metadata.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/end_to_end_workflow_example.py \\
        --team-name "Development" --target-name "My API" --target-url api.example.com \\
        --spec-file examples/sample-openapi.yaml
"""

import argparse

from veracode_dast.client import VeracodeClient
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
    args = parser.parse_args()

    client = VeracodeClient()

    team = client.teams.get_by_name(args.team_name)
    print(f"Resolved team: {team}")

    spec_url = f"https://{args.target_url}/openapi.yaml"
    target = client.targets.ensure(
        TargetCreate(
            name=args.target_name,
            url=args.target_url,
            protocol=Protocol.HTTPS,
            target_type=TargetType.API,
            scan_type=ScanType.FULL,
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
    print(f"Target ready: {target}")

    client.api_specifications.upload(target.target_id, args.spec_file)
    spec = client.api_specifications.get(target.target_id)
    print(f"API specification metadata: {spec}")


if __name__ == "__main__":
    main()
