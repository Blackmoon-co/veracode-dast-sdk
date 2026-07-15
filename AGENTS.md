# AGENTS.md — veracode-dast-sdk

This document is the source of truth for how `veracode-dast-sdk` is designed,
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

Implement only:

- Reusable HTTP client
- HMAC authentication (via `veracode-api-signing`)
- Targets CRUD (list, create, update, delete)
- Tests
- Logging
- Locally runnable examples

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
phase is explicitly started. See [Roadmap](#9-roadmap).

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
  HMAC authentication. Handles base URL, headers, timeouts, retries, and
  raises SDK-specific exceptions on failure.
- **Services** — one class per API resource (e.g. `TargetsService`). Contain
  resource-specific logic (endpoints, request/response shaping) and depend
  on the HTTP client, never on `requests` directly.
- **Models** — typed representations of API resources (e.g. `Target`), used
  for both request payloads and response parsing.
- **REST API** — Veracode DAST, external to this codebase.

**Hard rule:** services never import or call `requests` directly. Every
outbound call goes through the shared HTTP client so authentication,
logging, retries, and error handling live in exactly one place.

---

## 4. Project Structure

```
veracode-dast-sdk/
├── src/
│   └── veracode_dast_sdk/
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

---

## 6. Code Conventions

- Python 3.11+
- Type hints are mandatory on all public and private functions.
- Docstrings: Google style, on every public class/function.
- Linting: [Ruff](https://docs.astral.sh/ruff/).
- Static typing: [MyPy](https://mypy-lang.org/) (strict mode).
- Testing: [Pytest](https://docs.pytest.org/).
- Services-based architecture; each service owns one API resource.
- Clear separation of responsibilities between config, auth, HTTP client,
  services, and models — see [Section 7](#7-module-responsibilities).

---

## 7. Module Responsibilities

| Module           | Responsibility                                                                 |
|------------------|----------------------------------------------------------------------------------|
| `config.py`      | Read and validate SDK configuration from environment variables.                |
| `auth.py`        | Build HMAC-authenticated requests using `veracode-api-signing`.                 |
| `client.py`      | `VeracodeClient` (public entry point) and the internal shared HTTP client.      |
| `exceptions.py`  | SDK exception hierarchy (e.g. `VeracodeAPIError`, `VeracodeAuthError`).         |
| `services/`      | One class per API resource; translates domain calls into HTTP client calls.    |
| `models/`        | Typed dataclasses/models for request payloads and API responses.               |
| `utils/`         | Small, generic, cross-cutting helpers (e.g. logging configuration).            |

---

## 8. Desired Public API

The SDK should read like this once Phase 1 is complete:

```python
from veracode_dast_sdk import VeracodeClient

client = VeracodeClient()  # reads credentials from environment variables

targets = client.targets.list()
target = client.targets.create(name="my-app", url="https://example.com")
client.targets.update(target_id=target.id, name="my-app-renamed")
client.targets.delete(target_id=target.id)
```

Every future resource (analyses, reports, schedules, scanners, ...) follows
the same pattern: `client.<resource>.<action>()`.

---

## 9. Roadmap

### Phase 1 — Foundation

HTTP client, HMAC auth, Targets CRUD, tests, logging, local examples.

### Phase 2 — Core DAST resources

Analyses and Reports services, built on the same client/service pattern
established in Phase 1.

### Phase 3 — Platform consumers

Azure DevOps integration as a consumer of the SDK (custom task/extension),
without adding any Azure-specific code inside the SDK itself.

### Later / unscheduled

Schedules, Scanners, additional authentication mechanisms, CLI, PyPI
publishing — introduced only when a concrete phase calls for them.

---

## 10. Definition of Done

Every new piece of functionality must have:

- [ ] Tests
- [ ] Full type hints
- [ ] Google-style docstrings
- [ ] Logging at meaningful points (requests, errors, retries)
- [ ] A runnable example under `examples/`
- [ ] Passing Ruff
- [ ] Passing MyPy

---

## 11. Architecture Decision Records

| Decision | Rationale |
|---|---|
| Credentials via environment variables only (Phase 1) | Simplest mechanism that works everywhere (local, CI/CD) without adding a secrets-management dependency. Other mechanisms can be added later without breaking this default. |
| Single centralized HTTP client | Guarantees authentication, retries, timeouts, and error handling are implemented once and applied consistently across every service. |
| Services never call `requests` directly | Keeps the HTTP/auth layer swappable and testable in isolation; services stay focused on resource logic. |
| No Azure DevOps dependency inside the SDK | Azure DevOps is one of several possible consumers, not a core concern; keeping the SDK platform-agnostic protects reuse from other CI/CD systems. |
| No CLI in Phase 1 | A CLI is a separate consumer-facing concern; building it before the core client/service layer is stable would risk locking in the wrong API shape. |
| `src` layout | Prevents accidentally importing the package from the working directory instead of the installed package; standard for modern Python packaging. |

---

## 12. Development Flow

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
example, per the [Definition of Done](#10-definition-of-done).
