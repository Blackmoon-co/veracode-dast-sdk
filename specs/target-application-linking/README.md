# Target ↔ Application Linking

## Purpose

This feature lets an SDK consumer link a DAST Target to a Veracode
**Application** — the application profile created in Veracode's static
(SAST) side — so DAST results are imported into that Application, the same
way DAST Essentials links a scan to an application.

It adds two capabilities:

1. **Resolve an Application by name** (`client.applications`) — a
   read-only lookup, mirroring `client.teams.get_by_name`.
2. **Link / unlink a Target** (`client.targets.link` / `.unlink`) — the
   `PUT` / `DELETE /targets/{target_id}/link` operations the Target
   Management spec explicitly deferred
   ([target-management/requirements.md §0.2](../target-management/requirements.md#02-additional-target-operations-found-in-the-openapi-out-of-scope)).

> **Phase:** extends Phase 1 — Target Management. Same relationship
> Team Management has to Target creation: a name-resolution dependency,
> pulled in because Target provisioning needs it, not a general
> commitment to the AppSec domain.

---

## Motivating requirement

A pipeline provisioning a DAST Target wants to attach it to an existing
Application by name:

- A new `--app-name` argument is added to the provisioning example.
- **If `--app-name` is given:** the Application is resolved by name
  **before the Team is resolved and before the Target is created**. If no
  Application has that exact name, the run fails immediately with "that
  application does not exist" and no Target is created or updated.
- **If `--app-name` is given and the Application exists:** its UUID is
  taken and passed to `PUT /targets/{target_id}/link` after the Target is
  created, exactly as the DAST OpenAPI documents.
- **If `--app-name` is omitted:** nothing about linking runs; the Target
  is provisioned exactly as it is today.

The ordering ("check the app first") is a property of the **example
script**, not the SDK. The SDK ships the primitives; the example composes
them — the same division already used for Team resolution
([AGENTS.md §1](../../AGENTS.md#1-project-vision) non-goals: "does not
implement ... orchestration logic").

---

## REST API source of truth

`openApi/Veracode-veracode-dast-target-configuration-service-api-1.0.0-resolved.json`
("Veracode DAST Target Configuration Service API", v1.0.0, server
`https://api.veracode.com/dae/api/tcs-api/api/v1`).

Both endpoints this feature wraps are defined in that document, on the
**same base URL** Target Management already uses
(`TARGET_CONFIGURATION_SERVICE_BASE_URL`):

| Method | Path | operationId |
|---|---|---|
| GET | `/applications` | `getApplications` |
| PUT | `/targets/{target_id}/link` | `linkTarget` |
| DELETE | `/targets/{target_id}/link` | `unlinkTarget` |

No new base URL, no new `HttpClient`, no AppSec-domain service is
introduced. The Veracode "Example" Postman collection reaches the
application list through the AppSec API
(`GET https://api.veracode.com/appsec/v1/applications`); this SDK uses the
DAST TCS document's own `/applications` instead because it is the source
of truth for every Target-related spec, it returns exactly the fields
linking needs (`guid`, `name`), and it keeps the whole feature on one
already-wired base URL. See
[requirements.md §0.5](requirements.md#05-why-the-tcs-applications-endpoint-not-the-appsec-one).

---

## Public SDK API

```python
# Resolve an Application by name (raises ApplicationNotFoundError if absent)
app = client.applications.get_by_name("My App")
print(app.guid, app.name)

client.applications.exists("My App")          # -> bool, never raises

# Link / unlink a Target
client.targets.link(target.target_id, app.guid)   # PUT  /targets/{id}/link
client.targets.unlink(target.target_id)           # DELETE /targets/{id}/link
```

`applications` also exposes the raw paged list, for parity with the other
read services:

```python
page = client.applications.list(name="My App")
for a in page.items:
    print(a.guid, a.name)
```

---

## Returned models

```python
Application(
    guid="60e630b1-4ab7-4415-b920-5dd30b2e3a45",
    id="123456",
    name="My App",
    linked_scan_target_url="https://api.example.com",   # optional
)

ApplicationPage(items=[Application, ...], page_number=0, page_size=10,
                total_pages=1, total_elements=1)
```

`Application.id` is a **string** in this OpenAPI schema (the `Target`
response model's `application_id` is a separate `int64` field on a
different schema — not reused here; see
[requirements.md §0.4](requirements.md#04-schemas)).

---

## Behaviour notes

- **`link()` requires an ENTERPRISE-scan Target.** The OpenAPI documents a
  `422` "Target must be of enterprise type" for both `linkTarget` and
  `unlinkTarget`. The SDK does **not** pre-check the Target's `scan_type`
  (it would cost an extra `GET` and could reject a request the server
  would accept if that rule changes); the `422` propagates as
  `VeracodeValidationError`. See
  [requirements.md §5.3](requirements.md#5-validation-rules).
- **`link()` is not idempotent.** Linking an already-linked Target returns
  `409` → `VeracodeConflictError`. A pipeline that re-runs can catch
  `VeracodeConflictError` and treat it as "already linked", or call
  `unlink()` first.
- **`get_by_name()` raises**, matching `client.teams.get_by_name`
  (`TeamNotFoundError`) rather than `client.targets.get_by_name` (returns
  `None`). The motivating requirement is "fail saying the app does not
  exist", which a raised `ApplicationNotFoundError` expresses directly.
  `exists()` is the non-raising form.

---

## Exceptions

- `ApplicationNotFoundError` — no Application matches the exact name given
  to `get_by_name()`. Subclasses `VeracodeSDKError`, not
  `VeracodeApiError` (the underlying `GET /applications` succeeded — it
  just returned no exact match), same as `TeamNotFoundError` /
  `TargetNotFoundError`.
- `TargetValidationError` — blank `target_id` or `application_uuid` passed
  to `link()` / `unlink()` (reused from Target Management, not a new
  type).
- `VeracodeAuthenticationError`, `VeracodeAuthorizationError`,
  `VeracodeNotFoundError`, `VeracodeConflictError`,
  `VeracodeValidationError`, `VeracodeApiError` — propagated unchanged
  from the HTTP Client.

---

## Out of scope

- The AppSec Applications API (`/appsec/v1/applications`) and any other
  AppSec-domain resource (Findings, Policies). Still "Later / unscheduled"
  in [AGENTS.md §10](../../AGENTS.md#10-roadmap).
- Reading link state as a first-class thing: the `Target` model already
  surfaces `application_name` / `application_uuid` / `application_id` when
  the API populates them (Target Management spec §0.4) — no new read path
  is added.
- Creating, updating, or deleting Applications. This feature is read +
  link only.
- Result-import status polling after a link (that is an Analysis Runs
  concern — `AnalysisRun.result_import_status`).
- Any change to how a Target is created — `TargetCreate` / `TargetUpdate`
  are untouched. The OpenAPI's `TargetRequest` / `TargetUpdateRequest`
  schemas carry no application field; linking is a separate call.

---

## Expected result

After this feature, a provisioning script can do:

```python
client = VeracodeClient()

app = client.applications.get_by_name(args.app_name)   # first — aborts if missing
team = client.teams.get_by_name(args.team_name)
target = client.targets.ensure(TargetCreate(name=args.target_name, ...))
client.targets.link(target.target_id, app.guid)
```

and omitting `args.app_name` skips the first and last lines entirely.
