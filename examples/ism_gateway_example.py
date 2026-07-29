"""Lists ISM Gateways and assigns/removes a gateway on an existing Target.

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

    client.ism_gateways.remove(args.target_id)
    print(f"Removed gateway assignment from target {args.target_id}")


if __name__ == "__main__":
    main()
