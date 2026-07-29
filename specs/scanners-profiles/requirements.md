# Requirements — Scanner Profiles

Traceable to [README.md](README.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Depends on the
[HTTP Client](../http-client/requirements.md) and reuses
`TARGET_CONFIGURATION_SERVICE_BASE_URL` from Target Management (same
Veracode API domain as
[API Specification Management](../api-specification-management/requirements.md)).
Conceptually sits below [Analysis Profiles](../analysis-profile/README.md):
`analysis_profile_id` is always supplied by the caller, the same pattern
API Specification Management already uses for `target_id` — this module
never resolves, creates, or validates an Analysis Profile itself.

---

## 0. OpenAPI Review

Source: `openApi/Veracode-veracode-dast-target-configuration-service-api-1.0.0-resolved.json`,
server `https://api.veracode.com/dae/api/tcs-api/api/v1` (no new base URL).

### 0.1 In-scope REST endpoints

| Method | Path | operationId | Purpose |
|---|---|---|---|
| GET | `/analysis_profiles/{analysis_profile_id}/scanners` | `getScannerProfile` | Retrieve the effective Scanner Profile |
| PUT | `/analysis_profiles/{analysis_profile_id}/scanners` | `updateScannerProfile` | Update the Scanner Profile |

Path parameter `analysis_profile_id` is a `UUIDWithoutHyphens` (32 hex
chars, no dashes) on both endpoints — this feature does not reformat or
validate its shape beyond the generic blank-string check in §5; malformed
IDs are rejected by the API (404) and propagate unchanged.

### 0.2 Schemas

`ScannerType` (string enum) — the complete, closed set of valid scanner
identifiers:

```
fingerprinting, ssl, http_header, portscan, fuzzer, sql_injection, xss,
file_inclusion, deserialization, xxe, command_injection,
privilege_escalation, csrf, ldap_injection, common_login, trace_method,
code_injection, unsecured_login, clickjacking, ssti, obsolete_resource,
insecure_jwt, backup_file, error_pattern, open_redirect, ssrf,
webserver_dir_list, http_resp_split, view_state, file_upload, flash,
file_dir_exposure, url_session, struts2, malicious_host
```

`ScannerValue` (item of `ScannerProfile.scanners`, response only; all
fields required): `id` (`ScannerType`), `effective_value` (bool),
`is_inherited` (bool), `is_editable` (bool).

`ScannerProfile` (200 response of both GET and PUT; required:
`analysis_profile_id`, `parent_analysis_profile_id`, `scanners`):
`analysis_profile_id` (string), `parent_analysis_profile_id` (string),
`scanners` (array of `ScannerValue`).

`ScannerUpdateValue` (item of the PUT request body; required `id`,
`value`): `id` (`ScannerType`), `value` (bool).

`ScannerProfileUpdateRequest` (PUT request body): `{"scanners":
[ScannerUpdateValue, ...]}`.

### 0.3 HTTP status codes and error responses

- 200 → `ScannerProfile` (both GET and PUT).
- 401 → no body (`VeracodeAuthenticationError`, already mapped centrally
  by the HTTP Client).
- 404 → `Problem` (RFC 7807), `AnalysisProfile404Response` — unknown
  `analysis_profile_id` (`VeracodeNotFoundError`).
- 500 → `Problem`, `Problem500Response` (`VeracodeApiError`).

No 400/422 is documented for this endpoint. The OpenAPI document's global
error-code enum does list scanner-specific codes (e.g.
`SQL_INJECTION_SCANNER_INVALID`, `CSRF_SCANNER_INVALID`,
`CLICKJACKING_SCANNER_INVALID`, ...) — these represent **Veracode's own
business rule** that a given scanner may be ineligible for a specific
Analysis Profile (e.g. its target type or scan mode). This feature never
tries to replicate that eligibility logic client-side (see §7, "Out of
Scope"); if
Veracode ever returns it as a 422, it propagates unchanged as
`VeracodeValidationError` via the HTTP Client's existing status mapping.

---

## 1. Overview

The Scanner Profiles service manages which DAST security scanners are
enabled or disabled for an Analysis Profile. Per [README.md](README.md),
users never build the Veracode API's `ScannerProfileUpdateRequest`
payload by hand — they author a small, flat SDK Configuration document
(`{"scanners": {"<name>": <bool>, ...}}`) and the SDK is responsible for
loading it, validating it, transforming it into the API request shape,
calling the API, and returning strongly typed models.

This is the first Phase 2 feature to introduce an explicit
**configuration-driven** pipeline (Loader → Validator → Transformer) ahead
of the HTTP call, rather than a service method taking typed
keyword arguments directly (contrast with Target Management's
`TargetCreate`/`TargetUpdate`). §9 documents how this pipeline is built
so it is reusable, not duplicated, by later Phase 2 modules.

## 2. Goals

- Retrieve the current effective Scanner Profile for an Analysis Profile
  as strongly typed models (`ScannerProfile`, `Scanner`).
- Let users express desired scanner state using the SDK Configuration
  format instead of the Veracode OpenAPI request shape.
- Validate SDK Configuration structurally and semantically (known scanner
  names) before any HTTP call is made.
- Transform validated SDK Configuration into the Veracode API request
  automatically and invisibly to the caller.
- Reuse the shared `HttpClient`, exception hierarchy, and
  `TARGET_CONFIGURATION_SERVICE_BASE_URL` already established by Target
  Management / API Specification Management — no new HTTP/auth code.
- Structure the configuration-loading/validation logic so Authentication,
  Scanner Variables, and ISM Gateways (README "Future Vision") can reuse
  it without copy-pasting.

## 3. Functional Requirements

3.1. `get(analysis_profile_id: str) -> ScannerProfile`. Calls `GET
     /analysis_profiles/{analysis_profile_id}/scanners`; returns
     `ScannerProfile.from_api(response.data)`.

3.2. `update(analysis_profile_id: str, config_file: str | Path |
     dict[str, Any]) -> ScannerProfile`. Accepts either a path to an SDK
     Configuration JSON file or an already-loaded/in-memory dict (the
     README's file-based example is the primary path; accepting a dict
     too costs nothing extra and lets callers build configuration
     programmatically or pass fixtures in tests without touching disk).

3.3. `update()` performs, in order, before any HTTP call:
     load configuration (3.2) → validate structure (§5.1–5.3) → validate
     scanner names (§5.4–5.5) → transform to the API request shape
     ([design.md §7](design.md#7-transformation-layer)) — matching the
     six numbered steps already documented in
     [README.md "Update Scanner Profile"](README.md#update-scanner-profile).

3.4. On success (200), `update()` returns `ScannerProfile.from_api(response.data)`
     — the **server's** post-update state, never a locally reconstructed
     one, so `inherited`/`editable`/any scanner Veracode did not change
     are always accurate.

3.5. Configuration keys not present in the SDK Configuration's `scanners`
     object are left untouched — `update()` only ever sends scanners the
     caller explicitly listed; it never turns off scanners by omission.

3.6. Both `get()` and `update()` reject a blank/whitespace-only
     `analysis_profile_id` before any HTTP call.

## 4. Non-Functional Requirements

4.1. Stateless: `ScannersService` holds only an injected `HttpClient`
     instance; no per-call or cross-call mutable state (AGENTS.md §5
     "Stateless").

4.2. Type hints on every public and private function; Google-style
     docstrings on every public class/function (AGENTS.md §7).

4.3. No direct `requests` import; every outbound call goes through the
     shared `HttpClient` (AGENTS.md §3, "Hard rule").

4.4. No business data (scanner names/values, `analysis_profile_id`) is
     ever read from an environment variable (AGENTS.md §6.2).

4.5. Logging at meaningful points only (config loaded, validation
     failure, request start/success) — never scanner-by-scanner request
     bodies beyond what the HTTP Client already logs at DEBUG.

4.6. The configuration Loader/Validator building blocks must be usable
     standalone (importable, independently testable) so they can be
     reused by later configuration-driven modules (§2, last bullet).

## 5. Validation Rules

All of the following are checked **before** any HTTP call, and each
raises before any network I/O occurs:

5.1. `analysis_profile_id` must be non-blank (after `.strip()`) →
     `ScannerValidationError(rule="analysis_profile_id_required")`.

5.2. `config_file`, once loaded, must deserialize to a JSON **object**
     (Python `dict`) →
     `ScannerValidationError(rule="config_must_be_object")`.

5.3. The loaded configuration must contain a `"scanners"` key whose value
     is itself a JSON object (dict) →
     `ScannerValidationError(rule="scanners_key_required")`. An empty
     `"scanners": {}` is valid (a no-op update — README never states
     otherwise, and rejecting it would be an invented restriction).

5.4. Every value inside `"scanners"` must be a JSON boolean (Python
     `bool`) → `ScannerValidationError(rule="scanner_value_must_be_bool")`,
     naming the offending key.

5.5. Every key inside `"scanners"` must be a known `ScannerType` value
     (§0.2's closed 35-name set) → `UnknownScannerError`, carrying the
     offending name and, when a close match exists, a suggestion —
     reproducing exactly the
     [README "Validation"](README.md#validation) example: configuring
     `"sql"` fails with `Unknown scanner 'sql'.` and a `Did you mean
     'sql_injection'?` hint.

5.6. When `config_file` is a filesystem path, the file must exist and
     contain valid JSON → `ScannerValidationError(rule="config_file_not_found")`
     / `ScannerValidationError(rule="config_file_invalid_json")`.

5.7. This feature never validates whether a given scanner is *eligible*
     for the target's scan type — that is Veracode's own server-side
     business rule (§0.3) and is intentionally left to the API response.

## 6. Acceptance Criteria

- Given a valid `analysis_profile_id`, `client.scanners.get(...)` returns
  a `ScannerProfile` whose `scanners` list has one `Scanner` per entry in
  the API response, with `id`/`enabled`/`inherited`/`editable` populated
  exactly as shown in
  [README "Returned Model"](README.md#returned-model).
- Given the exact SDK Configuration from
  [README "SDK Configuration Format"](README.md#sdk-configuration-format),
  `client.scanners.update(analysis_profile_id=..., config_file="scanner-profile.json")`
  sends a PUT request whose JSON body matches
  [README "JSON Transformation"](README.md#json-transformation) — `{"id":
  "sql_injection", "value": true}` etc. — and returns the updated
  `ScannerProfile`.
- Given a configuration containing `{"scanners": {"sql": true}}`,
  `update()` raises before sending any HTTP request, with a message
  containing `Unknown scanner 'sql'.` and `Did you mean 'sql_injection'?`
  (README "Validation").
- Given a 404 response (unknown `analysis_profile_id`), both `get()` and
  `update()` let `VeracodeNotFoundError` propagate unchanged (README
  "Exceptions").
- Given a blank `analysis_profile_id`, both methods raise
  `ScannerValidationError` and make no HTTP call.

## 7. Out of Scope

Per [README.md "Future Vision"](README.md#future-vision) — the following
belong to later Phase 2 features, not this one:

- Authentication configuration.
- Scanner Variables.
- ISM Gateway configuration.
- Crawl configuration (`/analysis_profiles/{id}/crawl_configuration`
  exists in the OpenAPI document but is unrelated to this endpoint).
- Creating, listing, or deleting Analysis Profiles.
- Replicating Veracode's server-side scanner-eligibility validation
  (§0.3/§5.7) — errors from that rule propagate unchanged.
- A combined, multi-resource `dast-config.json` (README "Future Vision")
  — this feature only ever reads a single Scanner Profile configuration
  document.
- A CLI or any execution-platform integration (AGENTS.md §1 non-goals).

---

## 8. Testability

Stub/fake `HttpClient` returning prepared `HttpResponse` values or raising
prepared `VeracodeApiError` subclasses — same approach as
[target-management/requirements.md §13](../target-management/requirements.md#13-testability).
The Loader, Validator, and Transformer are all plain, pure functions that
take and return plain Python data, so they are unit-tested directly with
no `HttpClient` involved at all.

## 9. Reuse for future configuration-driven modules

The Loader (§5.6) and the "unknown key → suggestion" Validator (§5.5) are
built as small, generic, resource-agnostic helpers — not scanner-specific
logic — so that Authentication, Scanner Variables, and ISM Gateway
configuration (README "Future Vision") can depend on the same two
functions instead of re-implementing JSON loading and closest-match
suggestion each. See
[design.md §11](design.md#11-future-extensibility) for where these live.
