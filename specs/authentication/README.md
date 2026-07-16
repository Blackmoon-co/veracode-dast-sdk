# Authentication Infrastructure

## Overview

This feature implements the authentication infrastructure for the Veracode DAST SDK.

Authentication is the first feature of the SDK because every Veracode REST API requires HMAC authentication before any request can be executed.

This feature provides the foundation that will be reused by every future SDK module.

Its responsibility is limited to obtaining the Veracode credentials, validating them, and creating the official Veracode HMAC authentication provider.

No HTTP communication is performed in this feature.

---

# Background

The Veracode DAST SDK is being developed using a Specification-Driven Development approach.

Each feature begins with a high-level context document (README.md), followed by:

- requirements.md
- design.md
- tasks.md

The architecture and coding standards for the entire SDK are defined in the project's `AGENTS.md`.

This README provides only the functional context for this feature.

---

# Purpose

The purpose of this feature is to provide a reusable authentication component that will later be consumed by:

- HTTP Client
- Target Service
- Analysis Profile Service
- Scanner Service
- Analysis Service
- Report Service
- Every future SDK module

The authentication module is responsible only for creating and exposing the authentication provider.

It must not communicate with the Veracode REST API.

---

# Scope

This feature includes:

- Reading Veracode credentials from environment variables.
- Validating required credentials.
- Creating the official `RequestsAuthPluginVeracodeHMAC` authentication provider.
- Exposing the authentication provider for later use by the SDK HTTP client.

---

# Out of Scope

This feature does **not** implement:

- HTTP Client
- REST API communication
- Target CRUD
- Analysis Profiles
- Scanners
- Reports
- Analysis execution
- Authentication mechanisms for scanned APIs
  - SRM.js
  - Bearer Token
  - OAuth
  - API Keys
- Azure DevOps integration
- CLI
- Package publishing

---

# Authentication

The SDK authenticates using the official Veracode authentication library:

- `veracode-api-signing`

Authentication must be created using the official implementation:

```python
RequestsAuthPluginVeracodeHMAC(
    api_key_id,
    api_key_secret
)
```

The SDK must **never** implement its own HMAC authentication algorithm.

---

# Credential Source

During **Phase 1**, credentials are obtained **exclusively** from environment variables.

Supported variables:

- `VERACODE_API_KEY_ID`
- `VERACODE_API_KEY_SECRET`

These variables are mandatory.

The SDK must validate that both variables exist before creating the authentication provider.

No other credential source is supported during Phase 1.

---

# Phase 1 Constraints

For this phase, the SDK must:

- Use only environment variables.
- Use only the official `veracode-api-signing` library.
- Never implement a custom HMAC algorithm.
- Never perform HTTP requests.
- Never store credentials.
- Never log credentials.
- Never expose secrets.
- Never read credentials from configuration files.
- Never require credentials through the SDK constructor.
- Follow the architecture defined in `AGENTS.md`.

---

# Design Principles

The authentication module must follow the following principles:

- Single Responsibility Principle.
- Reusable by every SDK service.
- Independent from Azure DevOps.
- Independent from the HTTP client implementation.
- Easy to test.
- Fully typed.
- Easy to maintain.

---

# Expected Result

At the end of this feature the SDK must be capable of creating a reusable Veracode HMAC authentication provider.

The authentication provider will later be consumed by the SDK HTTP client.

No REST API communication should exist after completing this feature.

---

# Expected Usage

The consumer only needs to define the required environment variables.

Example:

```bash
export VERACODE_API_KEY_ID=xxxxxxxxxxxxxxxx
export VERACODE_API_KEY_SECRET=xxxxxxxxxxxxxxxx
```

Then the SDK can be initialized as:

```python
from veracode_dast import VeracodeClient

client = VeracodeClient()
```

The SDK automatically reads the environment variables and creates the official Veracode HMAC authentication provider.

---

# Future Evolution

Future phases of the SDK will build on top of this feature.

Examples include:

- HTTP Client
- Target Service
- Analysis Profile Service
- Scanner Service
- Analysis execution
- Report retrieval

No changes to the authentication architecture should be required for those future modules.
