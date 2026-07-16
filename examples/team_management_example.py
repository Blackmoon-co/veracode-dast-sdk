"""Resolves a Team by name via the Admin API.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/team_management_example.py --name "Development"
"""

import argparse

from veracode_dast.client import VeracodeClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Exact team name to resolve")
    args = parser.parse_args()

    client = VeracodeClient()
    team = client.teams.get_by_name(args.name)
    print(f"Resolved team {args.name!r} -> team_id={team.team_id}")


if __name__ == "__main__":
    main()
