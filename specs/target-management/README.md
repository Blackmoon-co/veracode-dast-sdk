# Target Management

## Overview

This feature implements Target Management for the Veracode DAST SDK.

A Target represents the application or API that will be scanned by Veracode DAST.

This feature provides the SDK abstraction over the Veracode DAST Target Configuration Service (TCS) Target endpoints.

The SDK must expose a clean, typed, Pythonic API while faithfully implementing the Veracode REST API.

---

## Background

The SDK foundation has already been established through the following features:

- Authentication
- HTTP Client

This feature is the first business service built on top of that infrastructure.

The implementation must consume the shared HTTP Client and must never communicate directly with the REST API.

---

## Purpose

Provide a simple and reusable interface for managing Veracode DAST Targets.

The SDK should abstract the REST API while preserving the concepts defined by Veracode.

The SDK is responsible for improving the developer experience without changing the behavior of the underlying REST API.

---

## REST API Source of Truth

The OpenAPI specification located in the `openapi/` directory is the source of truth for this feature.

The SDK must faithfully represent:

- REST endpoints
- Request payloads
- Response payloads
- Enumerations
- Validation rules
- HTTP status codes

The SDK must never invent REST operations that do not exist.

---

## SDK Source of Truth

The SDK architecture is defined by `AGENTS.md`.

All implementation decisions must follow the architecture described there.

Specifically:

- Authentication is provided by the Authentication module.
- HTTP communication is provided by the shared HTTP Client.
- Target Management contains only Target-specific business logic.
- Services never communicate directly with the requests library.

---

## Scope

Phase 1 includes the following Target operations:

- List Targets
- Get Target by ID
- Create Target
- Update Target
- Delete Target

The SDK may also provide convenience methods implemented on top of the REST API, such as:

- Get Target by Name
- Target Exists
- Ensure Target
- Update Target by Name

These helper methods must internally compose existing REST operations.

They must never require additional Veracode endpoints.

---

## Target Creation

Target creation must faithfully represent the OpenAPI TargetRequest schema.

All required fields defined by the OpenAPI must be exposed by the SDK.

Examples include (subject to the OpenAPI specification):

- name
- target_url
- target_type
- scan_type
- protocol
- authorized_to_scan
- is_sec_lead_only
- teams

The SDK must not hide or invent default values for required properties unless explicitly defined by the Veracode API.

---

## Enumerations

OpenAPI enumerations should be represented as typed Python enums instead of plain strings whenever appropriate.

Examples include:

- TargetType
- ScanType
- Protocol

This improves type safety and developer experience.

---

## Validation

The SDK should perform lightweight client-side validation when possible.

Examples include:

- Required fields.
- Invalid enum values.
- Conditional requirements defined by the OpenAPI.

Validation performed by the SDK should improve usability but must never replace server-side validation.

---

## Models

The SDK should expose typed models instead of raw dictionaries whenever practical.

Models should closely represent the Veracode REST resources.

Models must remain simple data representations.

Models must never:

- Perform HTTP requests.
- Contain business logic.
- Depend on the HTTP Client.

---

## Error Handling

The SDK must expose SDK-specific exceptions only.

HTTP and requests exceptions must already have been translated by the shared HTTP Client.

Target Management should only handle Target-specific business scenarios.

This feature introduces two Target-specific exceptions for scenarios that are not simply a translated HTTP error:

- `TargetValidationError` — raised when a target request fails a conditional rule (for example, a missing API specification URL for an API-type target) before any request is sent.
- `TargetNotFoundError` — raised by name-based convenience methods (for example, Update Target by Name) when no target matches the given name.

---

## Logging

HTTP request logging is handled by the shared HTTP Client.

Target Management should log only meaningful business events when appropriate.

Sensitive information must never be logged.

---

## Out of Scope

This feature does not implement:

- Authentication configuration
- Target Configuration
- Analysis Profiles
- Scanner Configuration
- Scanner Variables
- Scan execution
- Reports
- Scheduling

Those capabilities belong to future SDK features.

---

## Expected Public API

The desired SDK should resemble:

```python
client.targets.list()

client.targets.get(target_id)

client.targets.create(...)

client.targets.update(...)

client.targets.delete(target_id)

client.targets.get_by_name(name)

client.targets.exists(name)

client.targets.ensure(...)

client.targets.update_by_name(name, ...)
```

The public API should remain resource-oriented, strongly typed, and easy to use.

---

## OpenAPI Review

Before implementation, review the OpenAPI specification and document:

- All REST operations.
- Required fields.
- Optional fields.
- Enumerations.
- Conditional validation rules.
- Response models.
- Error responses.

The generated requirements and design documents should be based on this review.

---

## Expected Result

At the end of this feature the SDK should provide a complete Target Management service built on top of the shared HTTP Client.

All Target operations should faithfully map the Veracode REST API while providing a clean Python SDK experience.

No implementation should require direct HTTP communication outside the shared HTTP Client.