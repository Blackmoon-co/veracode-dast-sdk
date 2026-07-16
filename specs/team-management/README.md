# Team Management

## Overview

The Team Management module provides a typed, reusable abstraction over the
Veracode **Admin API Teams** resource.

Teams belong to the **Admin API** domain (base URL
`https://api.veracode.com/api/authn/v2`), not the DAST API domain. This is a
different Veracode base URL from DAST Target Management, sharing only the
same HMAC authentication mechanism, per AGENTS.md §3.1, §3.2, and §3.3. Team
Management is the first non-DAST service implemented in this SDK.

Its responsibility is to retrieve and manage Team resources that are used by
other Veracode services, such as DAST Target Management.

The SDK hides the HTTP communication while preserving the behavior of the
underlying REST API.

---

## Background

When creating or updating a DAST Target, the Target Configuration Service
expects a **team identifier** (`team_id`) rather than a human-readable team
name.

However, users and CI/CD pipelines typically know the team by its name
(e.g. "Development", "Security", "Platform Team") instead of its UUID.

Veracode exposes a dedicated **Admin API** for Team management.

The SDK therefore provides a Team Management service capable of discovering
Teams before they are used by other SDK modules.

---

## Purpose

Provide a reusable Team service that allows SDK consumers to:

- List available Teams.
- Retrieve a Team by identifier.
- Retrieve a Team by name.
- Verify whether a Team exists.
- Reuse Team information across multiple Veracode API domains.

The Team Management module is intentionally independent from Target
Management.

It is designed as a reusable building block: any current or future SDK
module that needs to resolve a Team — not only Target Management — depends
on this service rather than re-implementing Team lookup.

---

## REST API Source of Truth

The REST contract is defined by the Veracode **Admin API**.

The specification must never invent endpoints or request models.

Only operations supported by the Admin API may be exposed.

---

## SDK Source of Truth

The SDK follows the architectural principles defined in **AGENTS.md**.

Specifically:

- One service per REST resource.
- Business data is provided by the consumer.
- Services never perform direct HTTP requests.
- The shared HTTP Client owns HTTP communication.
- Authentication is provided through the shared HMAC authentication module.

---

## Scope

Phase 1 includes only Team discovery operations.

Supported operations:

- List Teams
- Get Team by ID
- Get Team by Name
- Check whether a Team exists

If additional Team operations are supported by the Admin API, they may be
documented but remain outside the implementation scope unless explicitly
approved.

---

## Relationship with Target Management

Target Management requires a `team_id` when creating or updating a Target.

The recommended SDK workflow is:

```
Consumer
      │
      ▼
TeamService.get_by_name()
      │
      ▼
Team
      │
      ▼
TargetCreate(team_id=team.id)
      │
      ▼
TargetsService.create()
```

Target Management must never own Team lookup logic.

The Team Management module owns Team discovery.

Future SDK convenience methods may internally compose these operations,
without changing service ownership.

---

## Team Resolution Strategy (Name → ID)

The Admin API identifies a Team by its `team_id`. Consumers and CI/CD
pipelines identify a Team by its human-readable name instead.

`get_by_name()` resolves a name to a Team by composing existing REST
operations — it lists (or searches, if the Admin API supports a
server-side name filter) Teams exposed by the Admin API and matches on
name. It never adds a new Veracode endpoint; it is a client-side
resolution step built on top of `list()`.

If no Team matches the given name, `get_by_name()` raises
`TeamNotFoundError` rather than returning `None`, so callers do not need
to null-check before using the resolved Team.

### Why `get_by_name()` exists

Target creation requires a `team_id` (see
[Background](#background)), but nothing upstream of the SDK naturally
knows that ID — it only knows the Team name. `get_by_name()` exists purely
as an SDK convenience: it removes the need for every consumer to
re-implement "list Teams, then find the one with this name" themselves.
It does not change the Admin API's contract, only how ergonomically the
SDK exposes it.

---

## Public SDK API

The SDK should expose a Team service similar to:

```python
client.teams.list()

client.teams.get(team_id)

client.teams.get_by_name("Development")

client.teams.exists("Development")
```

The SDK may introduce additional convenience methods in the future without
changing the underlying REST semantics.

---

## Team Model

The Team model should represent the Team resource returned by the Admin API.

Typical attributes include:

- Team identifier
- Team name
- Description
- Parent Team (if applicable)

Only attributes defined by the Admin API may be modeled.

---

## Validation

The SDK should validate:

- Required identifiers.
- Required names.
- Invalid lookup parameters.

Validation rules must remain consistent with the Admin API.

---

## Error Handling

The SDK exposes SDK-specific exceptions only. Raw `requests` exceptions
must never reach the consumer.

Two categories of exception exist, and Team Management must keep them
separate:

- **HTTP exceptions** — already translated by the shared HTTP Client (e.g.
  a raw 4xx/5xx response). Team Management does not re-translate these; it
  lets them propagate as-is.
- **Business exceptions** — raised by Team Management itself for scenarios
  that are not simply a translated HTTP error:
  - `TeamNotFoundError` — raised by `get_by_name()` (and other name-based
    lookups) when no Team matches the given name, i.e. a client-side
    resolution failure rather than an HTTP error.
  - `TeamValidationError` — raised when a lookup parameter fails
    validation (e.g. an empty name) before any request is sent.

Team Management must never wrap or replace HTTP exceptions raised by the
shared HTTP Client — only the business scenarios above justify a
Team-specific exception.

---

## Logging

HTTP request logging is handled by the shared HTTP Client. Team Management
logs only meaningful business events, at a level useful for diagnosing
lookups in a CI/CD pipeline:

- Team list operations — the number of Teams returned.
- Team retrieval by ID — the requested `team_id`.
- Team lookup by name (`get_by_name`, `exists`) — the requested name, and
  whether resolution succeeded or fell through to `TeamNotFoundError`.
- Business-level failures raised by this module (`TeamNotFoundError`,
  `TeamValidationError`).

Team Management must never log full Team payloads or any field not
required to diagnose the operation, and must never log HTTP-level details
already owned by the shared HTTP Client (headers, auth signatures,
request/response bodies). Sensitive information must never be logged.

---

## Out of Scope

This phase does not include:

- Team creation.
- Team update.
- Team deletion.
- User management.
- Roles.
- Business Units.
- Organization management.

Those resources belong to future specifications.

---

## OpenAPI / Admin API Review

Before generating requirements, review the Admin API and identify:

- Available Team endpoints.
- Request models.
- Response models.
- Pagination.
- Search capabilities.
- Validation rules.
- Error responses.
- HTTP status codes.

The generated specification must remain fully traceable to the Admin API.

---

## Expected Result

After this specification is implemented, SDK consumers should be able to
retrieve Team information independently from any other service and reuse it
when interacting with other Veracode APIs.

Example:

```python
team = client.teams.get_by_name("Development")

target = TargetCreate(
    name="Orders API",
    target_url="https://api.company.com",
    team_id=team.id
)

client.targets.create(target)
```

This keeps Team Management and Target Management loosely coupled while
allowing seamless integration across Veracode API domains.
