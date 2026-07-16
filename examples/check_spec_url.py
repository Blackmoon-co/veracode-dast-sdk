"""Quick check: does the target actually have api_specification_file_url set,
and does update_by_name() actually persist it?

Usage:
    python examples/check_spec_url.py --target-name "sdk-demo"
"""

import argparse

from veracode_dast.client import VeracodeClient
from veracode_dast.models.target import Protocol, TargetUpdate

parser = argparse.ArgumentParser()
parser.add_argument("--target-name", required=True)
parser.add_argument("--target-url", required=True)
args = parser.parse_args()

client = VeracodeClient()

before = client.targets.get_by_name(args.target_name)
print("BEFORE:", before)

spec_url = f"https://{args.target_url}/openapi.yaml"
after = client.targets.update_by_name(
    args.target_name,
    TargetUpdate(
        url=args.target_url,
        protocol=Protocol.HTTPS,
        api_specification_file_url=spec_url,
    ),
)
print("AFTER PUT response:", after)

refetched = client.targets.get_by_name(args.target_name)
print("AFTER re-GET:", refetched)
