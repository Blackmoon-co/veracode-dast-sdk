"""Retrieves and updates an Analysis Profile's crawl/scan configuration.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/analysis_profiles_example.py \\
        --analysis-profile-id <existing-analysis-profile-id> \\
        --rate-limit 300 --max-duration 120
"""

import argparse

from veracode_dast.client import VeracodeClient
from veracode_dast.models.analysis_profile import AnalysisProfileUpdate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-profile-id", required=True)
    parser.add_argument("--rate-limit", type=int, default=None)
    parser.add_argument("--max-duration", type=int, default=None)
    args = parser.parse_args()

    client = VeracodeClient()

    profile = client.analysis_profiles.get(args.analysis_profile_id)
    print(f"Current profile: {profile}")
    print(
        f"rate_limit={profile.rate_limit.effective_value} "
        f"(inherited={profile.rate_limit.is_inherited})"
    )

    update_kwargs = {}
    if args.rate_limit is not None:
        update_kwargs["rate_limit"] = args.rate_limit
    if args.max_duration is not None:
        update_kwargs["max_duration"] = args.max_duration

    if update_kwargs:
        updated = client.analysis_profiles.update(
            args.analysis_profile_id, AnalysisProfileUpdate(**update_kwargs)
        )
        print(f"Updated profile: {updated}")


if __name__ == "__main__":
    main()
