"""Confirms Veracode HMAC authentication can be constructed from the
environment.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set. Never
prints their values.
"""

from veracode_dast.auth import get_veracode_auth
from veracode_dast.exceptions import MissingCredentialsError


def main() -> None:
    try:
        get_veracode_auth()
    except MissingCredentialsError as exc:
        print(f"Missing credentials: {', '.join(exc.missing_variables)}")
        return
    print("Veracode HMAC authentication provider created successfully.")


if __name__ == "__main__":
    main()
