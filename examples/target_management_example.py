"""Provisions, updates, and tears down a DAST Target — mirroring the
ensure / update_by_name / delete pipeline pattern.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/target_management_example.py \\
        --name "My Target" --url example.com --protocol HTTPS \\
        --target-type WEB_APP --scan-type QUICK --teams 1
"""

import argparse

from veracode_dast.client import VeracodeClient
from veracode_dast.models.target import Protocol, ScanType, TargetCreate, TargetType, TargetUpdate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--protocol", choices=[p.value for p in Protocol], default="HTTPS")
    parser.add_argument("--target-type", choices=[t.value for t in TargetType], default="WEB_APP")
    parser.add_argument("--scan-type", choices=[s.value for s in ScanType], default="QUICK")
    parser.add_argument("--teams", nargs="*", default=None, help="At most one team ID")
    parser.add_argument("--api-spec-url", default=None)
    args = parser.parse_args()

    client = VeracodeClient()

    target = client.targets.ensure(
        TargetCreate(
            name=args.name,
            url=args.url,
            protocol=Protocol(args.protocol),
            target_type=TargetType(args.target_type),
            scan_type=ScanType(args.scan_type),
            authorized_to_scan=True,
            is_sec_lead_only=not args.teams,
            teams=args.teams,
            api_specification_file_url=args.api_spec_url,
        )
    )
    print(f"Ensured target: {target}")

    updated = client.targets.update_by_name(
        args.name, TargetUpdate(description="Updated by pipeline")
    )
    print(f"Updated target: {updated}")

    client.targets.delete(updated.target_id)
    print(f"Deleted target_id={updated.target_id}")


if __name__ == "__main__":
    main()
