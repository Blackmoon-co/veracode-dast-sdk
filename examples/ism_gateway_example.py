"""Lists ISM Gateways and assigns a gateway to an existing Target.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/ism_gateway_example.py \\
        --target-id <existing-target-id> \\
        --gateway-name "Corporate Gateway"
"""

import argparse

from veracode_dast.client import VeracodeClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--gateway-name", required=True)
    parser.add_argument(
        "--remove",
        action="store_true",
        help=(
            "Also call remove() after assigning, to exercise it. Unverified against "
            "a live account as of this writing (every attempted request body has "
            "failed with HTTP 400) — off by default so a pipeline that only needs "
            "to assign a gateway isn't broken by it. See README's "
            "'ism_gateways.remove()' note before using this."
        ),
    )
    args = parser.parse_args()

    client = VeracodeClient()

    gateways = client.ism_gateways.list()
    print("Available gateways:")
    for gateway in gateways:
        print(f"  {gateway.name}")

    assigned = client.ism_gateways.update(args.target_id, gateway_name=args.gateway_name)
    print(f"Assigned gateway: {assigned.name}")

    current = client.ism_gateways.get(args.target_id)
    print(f"Currently assigned: {current}")

    if args.remove:
        client.ism_gateways.remove(args.target_id)
        print(f"Removed gateway assignment from target {args.target_id}")


if __name__ == "__main__":
    main()
