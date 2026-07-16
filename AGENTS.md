# AGENTS.md — veracode-dast-sdk

This document is the source of truth for how `veracode-dast` is designed,
built, and extended. Any contributor (human or AI agent) working on this
repository should read this before writing code.

---

## 1. Project Vision

### Problem

Teams that use Veracode DAST need to script against its REST API — to
manage scan targets, trigger analyses, and pull reports — from many
different places: a developer's laptop, a CI/CD pipeline, a scheduled job.
Today that means every consumer re-implements HTTP handling, HMAC signing,
pagination, and error handling from scratch.

### Goal

Provide a single, well-tested Python SDK that:

- Wraps the Veracode DAST REST API behind a typed, discoverable client.
- Can be imported and used identically regardless of where it runs.
- Is the *only* place HMAC authentication and HTTP concerns live, so every
  consumer benefits from fixes and improvements made once.

### Non-goals

- This SDK does **not** implement a CLI, a GUI, or any orchestration logic.
- It does **not** implement Azure DevOps tasks, extensions, or pipelines —
  Azure DevOps is a *consumer* of this SDK, never the other way around.
- It does **not** try to replace or reimplement Veracode's platform
  behavior; it is a thin, faithful abstraction over the REST API, not a new
  product.
- It does not manage credentials storage, secrets vaults, or CI/CD secrets
  injection — it only reads credentials once they're available in the
  environment.

---

## 2. Scope

### Phase 1 (current)

Phase 1 is an MVP: usable end-to-end from a local script or an Azure
DevOps pipeline, not just a set of isolated building blocks. Implement
only:

- Reusable HTTP client
- HMAC authentication (via `veracode-api-signing`)
- Team Management (Admin Domain)
- Target Management (DAST Domain)
- API Specification Management (DAST Domain)
- Tests
- Logging
- Locally runnable examples

Target Management covers the Targets resource end-to-end. The SDK should
support future operations such as `list`, `get`, `find_by_name`, `ensure`,
`create`, `update`, and `delete` on this resource without changing the
architecture — new operations are added as new service methods, not new
layers.

Team Management is included in Phase 1 because Target Management depends
on it to resolve a `team_id` from a team name — it is an Admin Domain
resource included here for this dependency, not a sign that the Admin
Domain generally is in scope (see [Roadmap](#10-roadmap)). API
Specification Management covers uploading an OpenAPI or Postman
Collection for a Target.

### Explicitly out of scope for Phase 1

- Analysis
- Reports
- API-key/other authentication mechanisms beyond HMAC
- SRM.js
- Schedules
- Scanners
- CLI
- Azure DevOps integration
- Publishing to PyPI

Anything not listed under "Phase 1" above is out of scope until a later
phase is explicitly started. See [Roadmap](#10-roadmap).

---

## 3. Architecture

Clean, layered architecture. Each layer only talks to the layer directly
below it:

```
VeracodeClient
      ↓
  HTTP Client
      ↓
   Services
      ↓
    Models
      ↓
  REST API
```

- **`VeracodeClient`** — the single public entry point. Owns configuration
  and exposes services as attributes (e.g. `client.targets`).
- **HTTP Client** — the *only* component that calls `requests` and applies
  HMAC authentication. Each instance is configured with the base URL of one
  Veracode API; handles headers, timeouts, retries, and raises
  SDK-specific exceptions on failure.
- **Services** — one class per API resource (e.g. `TargetsService`). Contain
  resource-specific logic (endpoints, request/response shaping) and depend
  on the HTTP client, never on `requests` directly. Each service owns the
  base URL of the Veracode API it talks to (see §3.1).
- **Models** — typed representations of API resources (e.g. `Target`), used
  for both request payloads and response parsing.
- **REST API** — Veracode DAST, external to this codebase.

**Hard rule:** services never import or call `requests` directly. Every
outbound call goes through the shared HTTP client so authentication,
logging, retries, and error handling live in exactly one place.

**Hard rule:** models never perform HTTP requests, contain business logic,
or know about the HTTP client. A model is a simple typed representation of
a Veracode resource — business logic belongs to services, HTTP
communication belongs to the HTTP client.

### 3.1 Authentication is base-URL-agnostic

Veracode exposes multiple REST APIs under different base URLs that all
share the same HMAC authentication mechanism — for example the AppSec API
(`https://api.veracode.com/appsec`) and the DAST Target Configuration
Service (`https://api.veracode.com/dae/api/tcs-api/api/v1`). Future DAST
services may introduce further base URLs.

**Hard rule:** `auth.py` never knows about base URLs, endpoints, or any
service-specific configuration. Its only responsibility is producing a
`requests`-compatible HMAC auth provider that is valid for *any* Veracode
API. Base URL ownership belongs to the service/HTTP-client layer: each
service constructs (or is given) an `HttpClient` instance configured with
the base URL of the Veracode API it targets, and attaches the shared,
base-URL-independent auth provider to it. Adding a new Veracode API base
URL is a change to a service, never to `auth.py` or `client.py`.

### 3.2 Designed to extend beyond DAST (future)

Veracode exposes several REST API domains beyond DAST — e.g. the AppSec API
and the Admin API (Teams, Users, Roles, Business Units) — that share the
same HMAC scheme but live at different base URLs. Because auth is
base-URL-agnostic (§3.1) and each service already owns the base URL of the
API it talks to, adding a non-DAST domain requires only new services and
models; `auth.py` and `client.py` do not change.

This SDK's current goal remains the DAST SDK described in this document.
Evolving into a generic, multi-domain Veracode SDK — including any rename
of the package, repository, or import paths — is a decision to be revisited
when the first non-DAST service (e.g. Admin API Team Management) is
actually implemented, not before. Until then, the repository name, package
name, `pyproject.toml`, import paths, and current folder structure stay
unchanged.

### 3.3 Supported Veracode API Domains

The SDK is designed to communicate with multiple Veracode REST API domains.

Current domains include:

| Domain | Base URL | Primary Resources |
|---------|----------|-------------------|
| DAST Target Configuration Service | https://api.veracode.com/dae/api/tcs-api/api/v1 | Targets, API Specifications, Authentication, Analysis Profiles |
| Admin API | https://api.veracode.com/api/authn/v2 | Teams, Users, Roles, Business Units |
| AppSec API | https://api.veracode.com/appsec | Applications, Findings, Policies |

Each service belongs to exactly one API domain.

The HTTP Client is configured with the appropriate base URL for the service
it supports.

---

## 4. Project Structure

```
veracode-dast-sdk/
├── src/
│   └── veracode_dast/
│       ├── config.py       # Reads/validates env-based configuration
│       ├── auth.py         # HMAC authentication (veracode-api-signing)
│       ├── client.py       # HTTP client + VeracodeClient entry point
│       ├── exceptions.py   # SDK-specific exception hierarchy
│       ├── services/       # One module per API resource
│       ├── models/         # Typed models per API resource
│       └── utils/          # Small, generic helpers (logging setup, etc.)
├── tests/                  # Mirrors the src/ layout
├── examples/                # Runnable scripts demonstrating SDK usage
├── pyproject.toml
├── README.md
└── AGENTS.md
```

Folders are created as they're needed by an actual phase — this repository
does not carry empty placeholder modules for functionality that doesn't
exist yet.

---

## 5. Design Principles

The SDK must be:

- **Simple** — the smallest client that solves the problem correctly.
- **Extensible** — adding a new resource means adding a new service +
  model, not touching the client or existing services.
- **Reusable** — no assumption about the caller (local script, pipeline,
  scheduler, etc).
- **Typed** — every public function has complete type hints.
- **Maintainable** — clear separation of responsibilities, no hidden state.

The SDK abstracts *how* you talk to the Veracode DAST API (HTTP, auth,
pagination, error handling). It does not hide *what* Veracode does — its
resources, semantics, and API behavior should remain recognizable to anyone
who knows the Veracode DAST API.

### Stateless

Services must never maintain runtime state. Every operation must be
independent.

### Platform Agnostic

The SDK must never assume Azure DevOps, GitHub Actions, Jenkins, or any
execution platform. Execution platforms are SDK consumers, not part of the
SDK architecture.

---
## 6. Runtime Configuration vs Business Data

The SDK clearly distinguishes between infrastructure configuration and business data.

### 6.1 Infrastructure Configuration

Infrastructure configuration is required for the SDK to operate and may be obtained from environment variables.

During Phase 1, the following environment variables are supported:

- `VERACODE_API_KEY_ID`
- `VERACODE_API_KEY_SECRET`

These values are part of the SDK infrastructure and are automatically loaded by the SDK.

### 6.2 Business Data

Business data represents Veracode resources and must always be provided by the SDK consumer at runtime.

Examples include:

- Target name
- Target URL
- Target description
- Business criticality
- API specifications
- Scanner configuration
- Analysis configuration
- Report identifiers

The SDK must never read business data from environment variables.

This design keeps the SDK independent of any execution platform, allowing it to be reused by Azure DevOps, GitHub Actions, Jenkins, local scripts, or any other application.

---

## 7. Code Conventions

- Python 3.11+
- Type hints are mandatory on all public and private functions.
- Docstrings: Google style, on every public class/function.
- Linting: [Ruff](https://docs.astral.sh/ruff/).
- Static typing: [MyPy](https://mypy-lang.org/) (strict mode).
- Testing: [Pytest](https://docs.pytest.org/).
- Services-based architecture; each service owns one API resource.
- Clear separation of responsibilities between config, auth, HTTP client,
  services, and models — see [Section 8](#8-module-responsibilities).

**Exception strategy:** the SDK never lets raw exceptions from `requests`,
`veracode-api-signing`, or any other dependency reach the consumer. Every
HTTP, authentication, and API error is translated into an SDK-specific
exception (see `exceptions.py` in [Section 8](#8-module-responsibilities)),
so consumers only ever need to catch exceptions defined by this project.

---

## 8. Module Responsibilities

| Module           | Responsibility                                                                 |
|------------------|----------------------------------------------------------------------------------|
| `config.py`      | Read and validate SDK configuration from environment variables.                |
| `auth.py`        | Build HMAC-authenticated requests using `veracode-api-signing`. Never owns a base URL, endpoint, or any service-specific configuration (see [§3.1](#31-authentication-is-base-url-agnostic)). |
| `client.py`      | `VeracodeClient` (public entry point) and the internal shared HTTP client. The HTTP client accepts the target base URL per instance; it never hardcodes a specific Veracode API base URL. |
| `exceptions.py`  | SDK exception hierarchy (e.g. `VeracodeAPIError`, `VeracodeAuthError`).         |
| `services/`      | One class per API resource; translates domain calls into HTTP client calls.    |
| `models/`        | Typed dataclasses/models for request payloads and API responses.               |
| `utils/`         | Small, generic, cross-cutting helpers (e.g. logging configuration).            |

---

## 9. Desired Public API

The SDK should read like this once Phase 1 is complete:

```python
client = VeracodeClient()  # reads credentials from environment variables

client.targets.list()

client.targets.get(target_id)

client.targets.create(...)

client.targets.update(...)

client.targets.delete(...)
```

The API stays resource-oriented: every future resource (target
configuration, analysis profiles, scanners, analyses, reports, ...) follows
the same pattern, `client.<resource>.<action>()`, with business data always
passed in by the caller rather than assumed by the SDK.

---

## 10. Roadmap

The roadmap is organized around deliverable milestones — each phase is a
concrete, usable outcome, not just a feature list. Within a phase, work is
still grouped by API domain (per
[§3.3](#33-supported-veracode-api-domains)) so domain ownership stays
visible; domain membership is architectural and does not change based on
when something is implemented.

### Phase 1 — MVP

The goal of Phase 1 is to provide a fully usable SDK capable of preparing
an API Target for DAST scanning.

This phase intentionally spans multiple Veracode API domains where
required to deliver a complete workflow.

**Core**
- Authentication
- HTTP Client

**Admin**
- Team Management

**DAST**
- Target Management
- API Specification Management

**Quality**
- Tests
- Examples

Expected outcome — a consumer can, using only this phase:

- Resolve a Team by name.
- Create a DAST Target.
- Upload an OpenAPI or Postman Collection.
- Do all of the above equally well from a local script or an Azure DevOps
  pipeline.

### Phase 2 — Configure Targets

All DAST Domain.

- Authentication Configuration
- Analysis Profiles
- Scanner Configuration

### Phase 3 — Execute Scans

All DAST Domain.

- Analysis
- Reports
- Wait for Completion

### Later / unscheduled

- **Admin** — User Management, Role Management, Business Unit Management
- **AppSec** — Applications, Findings, Policies
- **Cross-cutting** — CLI, Azure DevOps integration, additional
  authentication mechanisms, PyPI publishing

Introduced only when a concrete phase calls for them.

---

## 11. Definition of Done

Every new piece of functionality must have:

- [ ] Tests
- [ ] Full type hints
- [ ] Google-style docstrings
- [ ] Logging at meaningful points (requests, errors, retries)
- [ ] A runnable example under `examples/`
- [ ] Passing Ruff
- [ ] Passing MyPy

---

## 12. Architecture Decision Records

| Decision | Rationale |
|---|---|
| Credentials via environment variables only (Phase 1) | Simplest mechanism that works everywhere (local, CI/CD) without adding a secrets-management dependency. Other mechanisms can be added later without breaking this default. |
| Single centralized HTTP client | Guarantees authentication, retries, timeouts, and error handling are implemented once and applied consistently across every service. |
| Services never call `requests` directly | Keeps the HTTP/auth layer swappable and testable in isolation; services stay focused on resource logic. |
| No Azure DevOps dependency inside the SDK | Azure DevOps is one of several possible consumers, not a core concern; keeping the SDK platform-agnostic protects reuse from other CI/CD systems. |
| No CLI in Phase 1 | A CLI is a separate consumer-facing concern; building it before the core client/service layer is stable would risk locking in the wrong API shape. |
| `src` layout | Prevents accidentally importing the package from the working directory instead of the installed package; standard for modern Python packaging. |
| Business data is never read from environment variables | Environment variables are reserved for SDK infrastructure configuration only. Business resources such as Targets, Target Configuration, Analysis Profiles, Scanners, Analyses, Reports, API Specifications and Authentication Configuration must always be supplied by the SDK consumer at runtime. |
| Authentication (`auth.py`) never owns a base URL | Veracode exposes multiple REST APIs under different base URLs (e.g. AppSec API, DAST Target Configuration Service) that all share the same HMAC scheme. Keeping `auth.py` base-URL-agnostic lets the same auth provider be reused across every current and future Veracode API without modification. |
| `HttpClient` requires an explicit `base_url` per instance, with no hardcoded default | Each service owns the base URL of the Veracode API it talks to (Target Management → DAST Target Configuration Service; future services → their own base URL). A required constructor argument, rather than a baked-in default, lets new Veracode API base URLs be introduced by adding a service, without touching the HTTP client or the authentication module. |
| Multi-domain support (AppSec, Admin, ...) is architecturally designed for, but only the Admin Domain's Team Management ships in Phase 1 — as a dependency of Target Management, not a general Admin Domain commitment (see [§3.2](#32-designed-to-extend-beyond-dast-future)) | The auth and HTTP-client layers already generalize to any Veracode base URL, so no architectural change is needed to add a domain later. Renaming the package/repo now would be premature — the project's current goal is the DAST SDK, and no other non-DAST service beyond Team Management exists yet to validate the shape of that change. |

---

## 13. Development Flow

```
Requirements
     ↓
Architecture
     ↓
Implementation
     ↓
Tests
     ↓
Examples
     ↓
Review
```

No implementation starts without an agreed architecture for that piece of
scope. No feature is considered complete without tests and a runnable
example, per the [Definition of Done](#11-definition-of-done).
