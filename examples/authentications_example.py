"""Retrieves and updates the Authentication configuration for an existing
Analysis Profile.

Never prints a sensitive field's value (password, client_secret,
base64_pkcs12, value, script_body) — these are excluded from every model's
`repr()`.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/authentications_example.py \\
        --analysis-profile-id <existing-analysis-profile-id> \\
        --config-file specs/authentications/authentication.json
"""

import argparse

from veracode_dast.client import VeracodeClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-profile-id", required=True)
    parser.add_argument("--config-file", required=True, help="SDK Configuration JSON file")
    args = parser.parse_args()

    client = VeracodeClient()

    config = client.authentications.get(args.analysis_profile_id)
    print(f"Current authentication configuration: {config}")

    updated = client.authentications.update(args.analysis_profile_id, args.config_file)
    print(f"Updated mechanism: {updated}")


if __name__ == "__main__":
    main()
