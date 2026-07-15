# veracode-dast-sdk

A reusable Python SDK for the [Veracode DAST](https://docs.veracode.com/r/DAST_Essentials_and_DAST_Advanced_API) REST API.

> **Status:** early architecture phase. No functionality is implemented yet.
> See [AGENTS.md](AGENTS.md) for the project vision, scope, and roadmap.

## What this is

`veracode-dast-sdk` abstracts the Veracode DAST REST API behind a typed,
service-based Python client, so it can be consumed the same way from a local
script, a CI/CD pipeline (Azure DevOps today, anything else tomorrow), or any
other Python codebase — without any platform-specific dependency baked into
the SDK itself.

## Status

This repository currently contains only the project scaffolding and
architecture documentation. Implementation starts with Phase 1 as defined in
[AGENTS.md](AGENTS.md#2-scope).

## Requirements

- Python 3.11+

## Installation (once Phase 1 lands)

```bash
pip install -e ".[dev]"
```

## Authentication (Phase 1)

The SDK reads Veracode HMAC credentials from environment variables:

```bash
export VERACODE_API_KEY_ID="..."
export VERACODE_API_KEY_SECRET="..."
```

## Project layout

```
src/veracode_dast_sdk/   SDK source (src layout)
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
