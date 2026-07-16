# veracode-dast-sdk

A reusable Python SDK for the [Veracode DAST](https://docs.veracode.com/r/DAST_Essentials_and_DAST_Advanced_API) REST API.

> **Status:** Phase 1 MVP — Authentication, HTTP Client, Team Management,
> Target Management, and API Specification Management are implemented.
> See [AGENTS.md](AGENTS.md) for the project vision, scope, and roadmap.

## What this is

`veracode-dast-sdk` abstracts the Veracode DAST REST API behind a typed,
service-based Python client, so it can be consumed the same way from a local
script, a CI/CD pipeline (Azure DevOps today, anything else tomorrow), or any
other Python codebase — without any platform-specific dependency baked into
the SDK itself.

## What it talks to

`VeracodeClient` wires up one `HttpClient` per underlying Veracode REST API,
and exposes one attribute per resource on top of it:

| `VeracodeClient` attribute | Veracode API                            | Base URL                                        |
| -------------------------- | ---------------------------------------- | ------------------------------------------------ |
| `client.teams`              | Admin API                                | `https://api.veracode.com/api/authn/v2`          |
| `client.targets`             | DAST Target Configuration Service        | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.api_specifications`  | DAST Target Configuration Service        | `https://api.veracode.com/dae/api/tcs-api/api/v1` |

- **Team Management** (`client.teams`) — read-only lookup, used to resolve a
  team name to the `team_id` a Target is assigned to.
- **Target Management** (`client.targets`) — CRUD for DAST Targets (the
  scanned application/API), plus idempotent `ensure`/`update_by_name`/`exists`
  helpers for pipelines.
- **API Specification Management** (`client.api_specifications`) — upload,
  fetch metadata for, and download the OpenAPI/Postman/HAR file backing an
  `API`-type Target.

## Requirements

- Python 3.11+

## Installation

```bash
pip install -e ".[dev]"
```

## Quick start

```python
from veracode_dast.client import VeracodeClient
from veracode_dast.models.target import TargetCreate, TargetType, ScanType, Protocol

client = VeracodeClient()  # reads VERACODE_API_KEY_ID / VERACODE_API_KEY_SECRET

team = client.teams.get_by_name("Development")

target = client.targets.create(
    TargetCreate(
        name="My API",
        url="api.example.com",
        protocol=Protocol.HTTPS,
        target_type=TargetType.API,
        scan_type=ScanType.QUICK,
        authorized_to_scan=True,
        is_sec_lead_only=False,
        teams=[team.team_id],
        api_specification_file_url="https://example.com/openapi.yaml",
    )
)

client.api_specifications.upload(target.target_id, "openapi.yaml")
spec = client.api_specifications.get(target.target_id)
```

## Pipeline usage: idempotent provisioning

For CI/CD pipelines that re-run on every deploy, prefer the idempotent
`ensure`/`update_by_name`/`delete` methods over `create`/`get` — they key off
the target's unique `name` instead of a `target_id` the pipeline would have
to persist between runs:

```python
target = client.targets.ensure(TargetCreate(name="My API", ...))  # get-or-create, never updates
client.targets.update_by_name("My API", TargetUpdate(description="Deployed by CI"))
client.targets.delete(target.target_id)  # teardown, e.g. on environment destroy
```

`ensure()` never updates an existing target's fields — it only creates when
absent. Use `update_by_name()` explicitly when a pipeline needs to change a
previously-provisioned target's configuration.

## Examples

Runnable scripts in [examples/](examples/), from lowest-level to a full
workflow. Each requires `VERACODE_API_KEY_ID` / `VERACODE_API_KEY_SECRET`:

| Script | What it shows |
| --- | --- |
| [`auth_example.py`](examples/auth_example.py) | Builds the HMAC auth provider from the environment. |
| [`http_client_example.py`](examples/http_client_example.py) | One raw authenticated `GET` via `HttpClient`, no typed models. |
| [`team_management_example.py`](examples/team_management_example.py) | Resolves a Team by name to its `team_id`. |
| [`target_management_example.py`](examples/target_management_example.py) | Full Target lifecycle: `ensure` → `update_by_name` → `delete`. |
| [`api_specification_management_example.py`](examples/api_specification_management_example.py) | Upload, get metadata, and download an API Specification for an existing Target. |
| [`end_to_end_workflow_example.py`](examples/end_to_end_workflow_example.py) | The full Phase 1 flow in one script: resolve a Team, `ensure`/update a Target, upload its spec, read the spec back — output as JSON. |

```bash
python examples/end_to_end_workflow_example.py \
  --team-name "Development" --target-name "My API" \
  --target-url api.example.com --spec-file examples/sample-openapi.yaml \
  --target-type API --scan-type ENTERPRISE
```

## Authentication (Phase 1)

The SDK reads Veracode HMAC credentials from environment variables:

```bash
export VERACODE_API_KEY_ID="..."
export VERACODE_API_KEY_SECRET="..."
```

## Project layout

```
src/veracode_dast/       SDK source (src layout)
  services/               One module per API resource (targets, ...)
  models/                 Typed data models for API resources
tests/                    Test suite (pytest)
examples/                 Runnable usage examples
```

## Documentation

- [AGENTS.md](AGENTS.md) — architecture, scope, conventions, and roadmap.
  This is the source of truth for how the project is built.

## License

MIT
