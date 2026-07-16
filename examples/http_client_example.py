"""Performs one authenticated GET against the DAST Target Configuration
Service using HttpClient directly, and prints the result.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.
"""

from veracode_dast.auth import get_veracode_auth
from veracode_dast.client import HttpClient

TARGET_CONFIGURATION_SERVICE_BASE_URL = "https://api.veracode.com/dae/api/tcs-api/api/v1"


def main() -> None:
    client = HttpClient(base_url=TARGET_CONFIGURATION_SERVICE_BASE_URL, auth=get_veracode_auth())
    response = client.get("/targets", params={"limit": 10})
    print(response.data)


if __name__ == "__main__":
    main()
