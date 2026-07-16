"""Uploads, retrieves, and downloads an API Specification for an existing
DAST API Target.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/api_specification_management_example.py \\
        --target-id <existing-api-target-id> \\
        --spec-file examples/sample-openapi.yaml \\
        --download-to /tmp/downloaded-openapi.yaml
"""

import argparse

from veracode_dast.client import VeracodeClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", required=True, help="Existing API target's ID")
    parser.add_argument("--spec-file", required=True, help="Local OpenAPI/Postman/HAR file")
    parser.add_argument("--download-to", required=True, help="Where to write the downloaded spec")
    args = parser.parse_args()

    client = VeracodeClient()

    uploaded = client.api_specifications.upload(args.target_id, args.spec_file)
    print(f"Uploaded: {uploaded}")

    spec = client.api_specifications.get(args.target_id)
    print(f"Metadata: {spec}")

    destination = client.api_specifications.download(args.target_id, args.download_to)
    print(f"Downloaded to: {destination}")


if __name__ == "__main__":
    main()
