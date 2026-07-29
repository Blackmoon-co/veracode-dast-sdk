"""Retrieves and replaces the Scanner Variables for an existing Analysis
Profile.

`update()` replaces the *entire* list of Scanner Variables — any existing
variable not listed in `--config-file` is deleted by Veracode.

Never prints a variable's `value` (a credential/secret/TOTP seed).

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/scanner_variables_example.py \\
        --analysis-profile-id <existing-analysis-profile-id> \\
        --config-file specs/scanner-variables/scanner-variables.json
"""

import argparse

from veracode_dast.client import VeracodeClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-profile-id", required=True)
    parser.add_argument("--config-file", required=True, help="SDK Configuration JSON file")
    args = parser.parse_args()

    client = VeracodeClient()

    current = client.scanner_variables.get(args.analysis_profile_id)
    for variable in current.variables:
        print(
            f"{variable.reference_key}: totp={variable.totp_seed}",
            f"inherited={variable.is_inherited}",
        )

    updated = client.scanner_variables.update(args.analysis_profile_id, args.config_file)
    print(f"Updated {len(updated.variables)} scanner variable(s)")


if __name__ == "__main__":
    main()
