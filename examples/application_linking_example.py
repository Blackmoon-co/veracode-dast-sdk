"""Resolves a Veracode Application by name and links an existing DAST
Target to it — exercising every public ApplicationsService operation plus
TargetsService.link / .unlink.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/application_linking_example.py \\
        --app-name "My App" --target-id <existing-enterprise-target-id>

    # Also unlink again afterwards (destructive):
    python examples/application_linking_example.py \\
        --app-name "My App" --target-id <id> --unlink
"""

import argparse
import sys

from veracode_dast.client import VeracodeClient
from veracode_dast.exceptions import ApplicationNotFoundError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-name", required=True, help="Exact Application name to resolve")
    parser.add_argument("--target-id", required=True, help="Existing Target's ID (ENTERPRISE scan)")
    parser.add_argument(
        "--unlink", action="store_true", help="Unlink the Target again after linking"
    )
    args = parser.parse_args()

    client = VeracodeClient()

    print(f"exists({args.app_name!r}) -> {client.applications.exists(args.app_name)}")

    try:
        app = client.applications.get_by_name(args.app_name)
    except ApplicationNotFoundError as exc:
        sys.exit(f"{exc}; not linking target {args.target_id}")

    print(f"Resolved application: guid={app.guid} name={app.name!r}")

    client.targets.link(args.target_id, app.guid)
    print(f"Linked target {args.target_id} -> application {app.guid}")

    if args.unlink:
        client.targets.unlink(args.target_id)
        print(f"Unlinked target {args.target_id}")


if __name__ == "__main__":
    main()
