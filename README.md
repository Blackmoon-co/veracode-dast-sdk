# veracode-dast-sdk

A reusable Python SDK for the [Veracode DAST](https://docs.veracode.com/r/DAST_Essentials_and_DAST_Advanced_API) REST API.

> **Status:** Phase 1 MVP (Authentication, HTTP Client, Team Management,
> Target Management, API Specification Management), Phase 2 (Analysis
> Profiles, Scanner Profiles, Authentications, Scanner Variables, ISM
> Gateways), and Phase 3 (Analysis Runs) are implemented. See
> [AGENTS.md](AGENTS.md) for the project vision, scope, and roadmap.

## What this is

`veracode-dast-sdk` abstracts the Veracode DAST REST API behind a typed,
service-based Python client, so it can be consumed the same way from a local
script, a CI/CD pipeline (Azure DevOps today, anything else tomorrow), or any
other Python codebase — without any platform-specific dependency baked into
the SDK itself.

## Requirements

- Python 3.11+

## Installation

```bash
pip install -e ".[dev]"
```

## Authentication

The SDK reads Veracode HMAC credentials from environment variables:

```bash
export VERACODE_API_KEY_ID="..."
export VERACODE_API_KEY_SECRET="..."
```

---

## Phase 1 — Target Management

`VeracodeClient` wires up one `HttpClient` per underlying Veracode REST API,
and exposes one attribute per resource on top of it:

| `VeracodeClient` attribute  | Veracode API                      | Base URL                                          |
| --------------------------- | ---------------------------------- | -------------------------------------------------- |
| `client.teams`               | Admin API                         | `https://api.veracode.com/api/authn/v2`           |
| `client.targets`             | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.api_specifications`  | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |

- **Team Management** (`client.teams`) — read-only lookup, used to resolve a
  team name to the `team_id` a Target is assigned to.
- **Target Management** (`client.targets`) — CRUD for DAST Targets (the
  scanned application/API), plus idempotent `ensure`/`update_by_name`/`exists`
  helpers for pipelines.
- **API Specification Management** (`client.api_specifications`) — upload,
  fetch metadata for, and download the OpenAPI (JSON/YAML) or HAR file
  backing an `API`-type Target. Postman collections are not accepted —
  convert to OpenAPI first.

### Quick start

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

### Pipeline usage: idempotent provisioning

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

### API target when you only have a local OpenAPI

Creating an `API` target requires `api_specification_file_url`, and Veracode
**downloads and parses that URL synchronously while the target is created**.
A fabricated or unreachable URL fails the whole `create()` call with a
Cloudflare `502` (`origin_bad_gateway`) — not a clean validation error. So
you can't create an API target by pointing at your application's own URL
when that URL doesn't serve a spec.

`api_specifications.upload()` (`POST /targets/{id}/spec`) **fully replaces**
whatever `create()` fetched: afterwards `api_spec_url` is `null`,
`api_spec_name` is the uploaded file's name, and the scan scope is
regenerated from the uploaded document (verified against the live API,
2026-09-07).

So when your spec exists only as a local file, create the target with any
always-reachable public OpenAPI as a throwaway bootstrap, then upload the
real file over it — nothing of yours needs to be hosted:

```python
BOOTSTRAP = "https://petstore3.swagger.io/api/v3/openapi.json"  # or your own always-up spec

target = client.targets.ensure(
    TargetCreate(
        name="client-api-1",
        url="api.client.com",              # the real host to scan; need not serve a spec
        protocol=Protocol.HTTPS,
        target_type=TargetType.API,
        scan_type=ScanType.ENTERPRISE,
        authorized_to_scan=True,
        is_sec_lead_only=False,
        teams=[team.team_id],
        api_specification_file_url=BOOTSTRAP,   # only needs to be reachable during create()
    )
)
client.api_specifications.upload(target.target_id, "client-openapi.json")  # replaces the bootstrap
assert client.api_specifications.get(target.target_id).api_spec_url is None
```

A Postman collection is **not** an accepted spec format — convert it first
(`npx postman-to-openapi collection.json -o openapi.yaml`) or capture a HAR.

The runnable version is
[`scan_api_with_local_openapi_example.py`](examples/scan_api_with_local_openapi_example.py)
(`--bootstrap-spec-url` overrides the default). `end_to_end_workflow_example.py`
does the same when its `--spec-url` flag is omitted.

### Phase 1 examples

Runnable scripts in [examples/](examples/). Each requires
`VERACODE_API_KEY_ID` / `VERACODE_API_KEY_SECRET`:

| Script | What it shows |
| --- | --- |
| [`auth_example.py`](examples/auth_example.py) | Builds the HMAC auth provider from the environment. |
| [`http_client_example.py`](examples/http_client_example.py) | One raw authenticated `GET` via `HttpClient`, no typed models. |
| [`team_management_example.py`](examples/team_management_example.py) | Resolves a Team by name to its `team_id`. |
| [`target_management_example.py`](examples/target_management_example.py) | Full Target lifecycle: `ensure` → `update_by_name` → `delete`. |
| [`api_specification_management_example.py`](examples/api_specification_management_example.py) | Upload, get metadata, and download an API Specification for an existing Target. |
| [`scan_api_with_local_openapi_example.py`](examples/scan_api_with_local_openapi_example.py) | Create an API target whose real URL serves no OpenAPI, using only a local spec file (bootstrap URL + `upload()`). |
| [`end_to_end_workflow_example.py`](examples/end_to_end_workflow_example.py) | The full Phase 1 flow in one script: resolve a Team, `ensure`/update a Target, upload its spec, read the spec back — output as JSON. |

```bash
python examples/end_to_end_workflow_example.py \
  --team-name "Development" --target-name "My API" \
  --target-url api.example.com --spec-file examples/sample-openapi.yaml \
  --target-type API --scan-type ENTERPRISE

# API target when the spec exists only locally (real URL serves no OpenAPI):
python examples/scan_api_with_local_openapi_example.py \
  --team-name "Development" --target-name "client-api-1" \
  --target-url api.client.com --spec-file ./client-openapi.json
```

---

## Phase 2 — Scan Configuration

Once a Target exists, Phase 2 configures how it's actually scanned: crawl/scan
settings, which security scanners run, how Veracode authenticates to the
target application, runtime credentials, and (for privately hosted apps) the
Internal Scanning Management gateway used to reach it.

| `VeracodeClient` attribute | Veracode API                      | Base URL                                          |
| --------------------------- | ---------------------------------- | -------------------------------------------------- |
| `client.analysis_profiles`  | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.scanners`            | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.authentications`     | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.scanner_variables`   | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.ism_gateways`        | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |

- **Analysis Profiles** (`client.analysis_profiles`) — the root DAST scan
  configuration resource: `list`/`get`/`update` crawl and scan settings for
  an Analysis Profile. Every other Phase 2 resource below is addressed by
  the `analysis_profile_id` this service resolves.
- **Scanner Profiles** (`client.scanners`) — enable/disable individual DAST
  security scanners on an Analysis Profile, using a small SDK Configuration
  document instead of the raw Veracode request model.
- **Authentications** (`client.authentications`) — configure how Veracode
  authenticates to the target application (HTTP Basic, form-based,
  client certificate, login/logout scripts, Scriptable Request
  Modification, OAuth 2.0, or Parameter Authentication), one mechanism per
  `update()` call via an SDK Configuration document.
- **Scanner Variables** (`client.scanner_variables`) — runtime values
  (credentials, TOTP seeds, tokens) that authentication mechanisms
  reference by name. `update()` replaces the *entire* list — see the
  warning below.
- **ISM Gateways** (`client.ism_gateways`) — assign, change, or remove the
  Internal Scanning Management gateway a Target uses to reach a privately
  hosted application, by gateway name (never a raw gateway ID).

### Configuring Targets

Resolve the Target's Analysis Profile and configure scanning via small,
version-controllable SDK Configuration JSON files instead of the raw
Veracode API request models:

```python
profile = client.analysis_profiles.get(analysis_profile_id)

client.scanners.update(analysis_profile_id, config_file="scanner-profile.json")
client.authentications.update(analysis_profile_id, config_file="authentication.json")
client.scanner_variables.update(analysis_profile_id, config_file="scanner-variables.json")
client.ism_gateways.update(target.target_id, gateway_name="Corporate Gateway")
```

Each `update()` call: loads the configuration (path or in-memory `dict`),
validates it locally (unknown scanner/authentication-type names raise before
any HTTP call, with a "did you mean" suggestion where applicable), transforms
it into the corresponding Veracode API request, and returns the server's
updated state as a typed model.

Sample configuration files live next to each feature's spec:
[`specs/scanners-profiles/scanner-profile.json`](specs/scanners-profiles/scanner-profile.json),
[`specs/authentications/authentication.json`](specs/authentications/authentication.json),
[`specs/scanner-variables/scanner-variables.json`](specs/scanner-variables/scanner-variables.json),
[`specs/ism-gateway/ism-gateway.json`](specs/ism-gateway/ism-gateway.json).

**Scriptable Request Modification (SRM) authentication takes its script as
base64, not a file path.** `authentication.json`'s `"srm"` mechanism (and
`"script"`'s `login_script`/`logout_script`) has a `script_body` field, but
the SDK Configuration format never accepts a `.js` file path there — you
must read the script file yourself and base64-encode its contents into the
JSON before calling `update()`:

```python
import base64, json

with open("srm-script.js", "rb") as f:
    script_body = base64.b64encode(f.read()).decode("ascii")

config = {
    "authentication": {
        "type": "srm",
        "script_name": "srm-script.js",
        "script_type": "JAVASCRIPT",
        "script_body": script_body,
    }
}
client.authentications.update(analysis_profile_id, config_file=config)  # dict works, no file needed
```

See [`specs/authentications/authentication-srm.json`](specs/authentications/authentication-srm.json)
for a pre-encoded example built from
[`specs/authentications/srm-script-example.js`](specs/authentications/srm-script-example.js).

**Scanner Variables `update()` is a full replace, not a merge.** Unlike
Scanner Profiles (which only touches the scanners you list), calling
`client.scanner_variables.update(...)` sends the *complete* desired list —
any existing variable whose `reference_key` is missing from your
configuration is deleted. A pipeline that wants to add one variable without
disturbing the others must `get()` first, append to `.variables`, and pass
the full list back to `update()`.

**Scanner Variables are part of Authentication, not a standalone concept.**
They don't do anything on their own — they're the runtime values (username,
password, TOTP seed) that an Authentication mechanism's login script or MFA
step looks up by `reference_key`. There's no "active/inactive" flag on a
Scanner Variable; its only states are "present in the list" (usable by
Authentication) or "absent" (deleted). Configure `client.authentications`
first to define *how* Veracode logs in, then `client.scanner_variables` to
supply the *values* that login references.

`client.ism_gateways` and `client.api_specifications` take `target_id`, not
`analysis_profile_id` — resolve it via `client.analysis_profiles.get(analysis_profile_id).target_id`,
or use the `target_id` already returned by `client.targets.ensure(...)`.

**Not every scanner is editable.** Which scanners a Target exposes, and
whether each can be changed, depends on its `scan_type`/`target_type` —
confirmed live against two accounts:

- QUICK/WEB_APP Target: only `fingerprinting`, `http_header`, `portscan`,
  and `ssl` were editable; scanners like `sql_injection`, `xss`, and `csrf`
  came back `editable=False` and rejected the update with a 400.
- ENTERPRISE/API Target: the opposite — 32 of 34 scanners were editable;
  only `fuzzer` and `file_dir_exposure` came back `editable=False`.
  `privilege_escalation` didn't appear in the profile's scanner list at
  all — including it in an `update()` call fails, not because it's
  uneditable, but because it doesn't apply to that profile.

Sending a scanner Veracode rejects fails the *entire* `update()` call, even
if every other scanner in the same request is valid. Check the `editable`
field on each `Scanner` from `client.scanners.get(...)` before calling
`update()`, rather than assuming a fixed list.

### Phase 2 examples

Runnable scripts in [examples/](examples/). Each requires
`VERACODE_API_KEY_ID` / `VERACODE_API_KEY_SECRET`:

| Script | What it shows |
| --- | --- |
| [`analysis_profiles_example.py`](examples/analysis_profiles_example.py) | Get an Analysis Profile's crawl/scan configuration, then update selected fields. |
| [`scanner_profiles_example.py`](examples/scanner_profiles_example.py) | Get, then update, an Analysis Profile's enabled scanners from an SDK Configuration file. |
| [`authentications_example.py`](examples/authentications_example.py) | Get the effective Authentication configuration, then configure one mechanism from an SDK Configuration file. |
| [`scanner_variables_example.py`](examples/scanner_variables_example.py) | Get, then replace, an Analysis Profile's Scanner Variables from an SDK Configuration file. |
| [`ism_gateway_example.py`](examples/ism_gateway_example.py) | List available ISM Gateways, assign one to a Target by name, then remove the assignment. |

---

## Phase 3 — Execute Scans

Once a Target is configured (Phase 2), Phase 3 runs the scan itself: start
an Analysis Run, monitor or wait for it to finish, stop it early if needed,
and download the resulting report.

| `VeracodeClient` attribute | Veracode API                      | Base URL                                          |
| --------------------------- | ---------------------------------- | -------------------------------------------------- |
| `client.analysis_runs`      | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |

- **Analysis Runs** (`client.analysis_runs`) — `start`/`stop`/`list`/`get` an
  Analysis Run for an existing Target, `wait_for_completion` to block until
  it reaches a terminal status, and `get_report` to download the report
  (PDF, CSV, or JUnit) for a specific run.

### Running a scan

```python
target = client.targets.get_by_name("My API")

run = client.analysis_runs.start(target.target_id)

finished = client.analysis_runs.wait_for_completion(
    target.target_id, run.analysis_run_id, poll_interval=15, timeout=3600
)
print(finished.status)  # TargetStatus.FINISHED / STOPPED / FAILED

client.analysis_runs.get_report(
    target.target_id, finished.analysis_run_id, "pdf", "scan-report.pdf"
)
```

`wait_for_completion()`'s terminal statuses are `FINISHED`, `STOPPED`, and
`FAILED` (`RUNNING`/`STOPPING` keep it polling). `timeout` is a *soft*
bound — it's only checked once per poll, so it can be exceeded by up to
roughly one `poll_interval` plus one HTTP request — and raises
`AnalysisRunTimeoutError` once exceeded.

### Stopping a scan early

```python
from veracode_dast.models.analysis_run import StopActionType

client.analysis_runs.stop(target.target_id, action=StopActionType.STOP_SAVE)
```

`action` defaults to `StopActionType.STOP_DELETE` and also accepts a plain
string (`action="STOP_SAVE"`), validated the same way as `get_report()`'s
`format`.

### Phase 3 examples

Runnable scripts in [examples/](examples/). Each requires
`VERACODE_API_KEY_ID` / `VERACODE_API_KEY_SECRET`:

| Script | What it shows |
| --- | --- |
| [`analysis_runs_example.py`](examples/analysis_runs_example.py) | Resolve a Target by name, start (or reuse) an Analysis Run, wait for completion, optionally download a report, or stop the run instead. |

```bash
# Run a scan by Target name (resolved via TargetsService.get_by_name)
python examples/analysis_runs_example.py --target-name "sdk-demo"

# Run a scan and download a report
python examples/analysis_runs_example.py --target-name "sdk-demo" \
  --report pdf --output ./report.pdf

# Run a scan by Target ID instead of name
python examples/analysis_runs_example.py --target-id <existing-target-id>

# Inspect an existing Analysis Run instead of starting a new one
python examples/analysis_runs_example.py --target-name "sdk-demo" \
  --analysis-run-id <existing-run-id>

# Stop a running Analysis Run instead of waiting for completion
python examples/analysis_runs_example.py --target-name "sdk-demo" --stop
```

---

## Project layout

```
src/veracode_dast/       SDK source (src layout)
  services/               One module per API resource (targets, ...)
  models/                 Typed data models for API resources
  utils/                  Small, generic helpers (SDK Configuration loading)
tests/                    Test suite (pytest)
examples/                 Runnable usage examples
```

## Documentation

- [AGENTS.md](AGENTS.md) — architecture, scope, conventions, and roadmap.
  This is the source of truth for how the project is built.

## License

MIT
