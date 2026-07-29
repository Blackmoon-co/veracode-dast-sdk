"""Retrieves and updates the Scanner Profile for an existing Analysis
Profile.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/scanner_profiles_example.py \\
        --analysis-profile-id <existing-analysis-profile-id> \\
        --config-file specs/scanners-profiles/scanner-profile.json
"""

import argparse

from veracode_dast.client import VeracodeClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-profile-id", required=True)
    parser.add_argument("--config-file", required=True, help="SDK Configuration JSON file")
    args = parser.parse_args()

    client = VeracodeClient()

    profile = client.scanners.get(args.analysis_profile_id)
    print(f"Current scanner profile: {profile}")

    updated = client.scanners.update(args.analysis_profile_id, args.config_file)
    print(f"Updated scanner profile: {updated}")


if __name__ == "__main__":
    main()
