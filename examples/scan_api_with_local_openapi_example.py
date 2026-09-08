"""Create a DAST API Target whose real URL does NOT host an OpenAPI, using
only a local OpenAPI (JSON/YAML/HAR) file.

The problem
-----------
`POST /targets` for an API target requires `api_specification_file_url` and
Veracode **downloads and parses it synchronously while creating the
target**. A fabricated or unreachable URL fails the whole create call with
a Cloudflare 502 (`origin_bad_gateway`), not a clean 4xx. So you cannot
create an API target by "just" pointing at your target's URL when that URL
serves no spec.

The workaround (verified against the live API on 2026-09-07)
-----------------------------------------------------------
`api_specifications.upload()` (`POST /targets/{id}/spec`) **fully replaces**
whatever `create()` fetched: afterwards `api_spec_url` is `null`,
`api_spec_name` is the uploaded file's name, and the scan scope regenerates
from the uploaded document.

So: create the target with any always-reachable public OpenAPI as a
throwaway bootstrap, then upload the real local file over it. Nothing of
yours needs to be hosted.

Requires VERACODE_API_KEY_ID and VERACODE_API_KEY_SECRET to be set.

Usage:
    python examples/scan_api_with_local_openapi_example.py \\
        --team-name "Consultor" \\
        --target-name "client-api-1" \\
        --target-url "api.client.com" \\
        --spec-file ./client-openapi.json
"""

import argparse
import dataclasses
import json
import sys

from veracode_dast.client import VeracodeClient
from veracode_dast.exceptions import VeracodeApiError
from veracode_dast.models.target import Protocol, ScanType, TargetCreate, TargetType

# A public OpenAPI Veracode can always GET. Used only to get past target
# creation; overwritten by --spec-file. Point --bootstrap-spec-url at your
# own always-up spec if you don't want this external dependency in CI.
DEFAULT_BOOTSTRAP_SPEC_URL = "https://petstore3.swagger.io/api/v3/openapi.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team-name", required=True)
    parser.add_argument("--target-name", required=True)
    parser.add_argument("--target-url", required=True, help="The real API host to scan")
    parser.add_argument("--spec-file", required=True, help="Local OpenAPI JSON/YAML/HAR")
    parser.add_argument("--bootstrap-spec-url", default=DEFAULT_BOOTSTRAP_SPEC_URL)
    parser.add_argument(
        "--scan-type", type=ScanType, choices=list(ScanType), default=ScanType.ENTERPRISE
    )
    args = parser.parse_args()

    client = VeracodeClient()

    team = client.teams.get_by_name(args.team_name)

    # 1. Create the API target. api_specification_file_url must be reachable
    #    right now — the bootstrap spec satisfies that.
    target = client.targets.ensure(
        TargetCreate(
            name=args.target_name,
            url=args.target_url,
            protocol=Protocol.HTTPS,
            target_type=TargetType.API,
            scan_type=args.scan_type,
            authorized_to_scan=True,
            is_sec_lead_only=False,
            teams=[team.team_id],
            api_specification_file_url=args.bootstrap_spec_url,
        )
    )
    print(f"target {target.target_id} created with bootstrap {args.bootstrap_spec_url}")

    # 2. Upload the real local spec. This replaces the bootstrap entirely.
    client.api_specifications.upload(target.target_id, args.spec_file)

    # 3. Confirm: api_spec_name is the local file, api_spec_url is null.
    spec = client.api_specifications.get(target.target_id)
    print(json.dumps(dataclasses.asdict(spec), indent=2))
    if spec.api_spec_url is None:
        print("OK: the local spec replaced the bootstrap; nothing of yours is hosted.")
    else:
        print(f"WARNING: api_spec_url is still {spec.api_spec_url!r} — upload did not replace it.")


if __name__ == "__main__":
    try:
        main()
    except VeracodeApiError as e:
        print(json.dumps({"status_code": e.status_code, "response_body": e.response_body}, indent=2))
        sys.exit(1)
