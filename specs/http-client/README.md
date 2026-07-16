# HTTP Client

## Overview

This feature implements the reusable HTTP client for the Veracode DAST SDK.

The HTTP client is the only component responsible for communicating with the Veracode REST APIs.

Every SDK service must use this client.

No service is allowed to communicate directly with the REST API.

The HTTP client is responsible for applying authentication, sending requests, processing responses, logging requests, and translating HTTP failures into SDK-specific exceptions.

---

## Background

Authentication has already been implemented as a separate feature.

Authentication is completely independent from HTTP communication: it is
responsible only for creating the official `RequestsAuthPluginVeracodeHMAC`
authentication provider, and knows nothing about base URLs, endpoints, or
HTTP. This feature never creates authentication itself — it receives a
ready-made authentication provider through its constructor and becomes the
foundation for every future SDK service.

The HTTP client is intentionally generic and does not contain any resource-specific logic.

Veracode exposes multiple REST APIs under different base URLs that all
share this same HMAC authentication — for example the AppSec API
(`https://api.veracode.com/appsec`) and the DAST Target Configuration
Service (`https://api.veracode.com/dae/api/tcs-api/api/v1`). Future
Veracode APIs may expose additional base URLs. The HTTP client owns the
base URL (one Veracode API per client instance); each SDK service is
responsible for using the base URL of the Veracode API it targets. For
Phase 1 only the DAST Target Configuration Service base URL is actually
used, but the design supports any future Veracode API base URL without
architectural changes.

---

## Purpose

Provide a reusable HTTP abstraction for the SDK.

The client should centralize:

- HTTP communication
- Attaching an injected authentication provider
- Default headers
- Base URL (per client instance)
- Timeouts
- Retries
- Error handling
- Logging

Every future SDK service must depend on this component.

---

## Scope

This feature includes:

- HTTP GET
- HTTP POST
- HTTP PUT
- HTTP PATCH
- HTTP DELETE

The client must:

- Accept a pre-created authentication provider via its constructor and
  attach it to every request. It must never create authentication itself
  or call into the Authentication module to obtain one.
- Accept the target Veracode API base URL via its constructor, so it can
  serve the AppSec API, the DAST Target Configuration Service, or any
  future Veracode API without code changes — only Phase 1's Target
  Management service actually uses the DAST Target Configuration Service
  base URL.
- Serialize request payloads.
- Deserialize JSON responses into plain data structures (dicts/lists) —
  never into typed models. Building models from that data is a Service's
  responsibility, per AGENTS.md's Models hard rule.
- Validate HTTP responses.
- Translate errors into SDK exceptions, distinguishing common cases (401,
  403, 404, 409, 422, connection failure, timeout) so callers can react
  programmatically instead of inspecting status codes themselves.
- Expose only resource-oriented verb methods (`get`, `post`, `put`,
  `patch`, `delete`) as its public API — no generic `request(method, ...)`
  method.

---

## Out of Scope

This feature does not implement:

- Targets
- Target Configuration
- Analysis Profiles
- Scanners
- Analysis execution
- Reports

The client must not know anything about Veracode resources.

---

## Constraints

The HTTP client must be the only component allowed to use the requests library.

Services must never import requests directly.

Authentication must be delegated to the Authentication module — but that
delegation happens *before* this feature is involved. The HTTP client
never imports `auth.py`/`config.py` and never calls `get_veracode_auth()`;
it only accepts a ready-made authentication provider as a constructor
argument.

Business logic must never exist inside the HTTP client.

Models must never be constructed or imported by the HTTP client — that
would violate AGENTS.md's rule that models never know about the HTTP
client.

Raw exceptions from `requests` (or any other dependency) must never
propagate to the caller — every failure is translated into an SDK-specific
exception, so consumers only ever catch exceptions defined by this
project.

---

## Design Principles

The HTTP client should be:

- Stateless
- Reusable
- Fully typed
- Resource agnostic
- Easy to test
- Independent of any execution platform

---

## Expected Result

At the end of this feature the SDK should provide a reusable HTTP client that every future service can consume.

No service should need to know how HTTP communication is performed.