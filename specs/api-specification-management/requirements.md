# Requirements — API Specification Management

Traceable to [README.md](README.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Builds on
[Target Management](../target-management/requirements.md) (for `target_id`)
and the [HTTP Client](../http-client/requirements.md), including its
[multipart/binary amendment](../http-client/requirements.md#amendment-multipart-upload-and-raw-binary-responses).

---

## 0. OpenAPI Review

Source: `openApi/Veracode-veracode-dast-target-configuration-service-api-1.0.0-resolved.json`,
server `https://api.veracode.com/dae/api/tcs-api/api/v1` (same domain as
Target Management — no new base URL).

### 0.1 In-scope REST endpoints

| Method | Path | operationId | Purpose |
|---|---|---|---|
| GET | `/targets/{target_id}/spec` | `getTargetApiSpec` | API Specification metadata |
| POST | `/targets/{target_id}/spec` | `uploadTargetApiSpec` | Upload an API Specification file |
| GET | `/targets/{target_id}/spec/download` | `downloadTargetApiSpecContents` | Raw API Specification file contents |

Out of scope (exist in the OpenAPI, not part of this feature): `PUT/DELETE
/targets/{target_id}/link` (Target linking — Target Management's concern if
ever added), anything under `/analysis_run`, `/analysis_profiles`,
`/discovered_targets`, `/ism_gateways`.

### 0.2 `GET /targets/{target_id}/spec`

Path param `target_id` (required). Query param `scan_id` (optional string,
"UUID of the scan or analysis run") — **not exposed** in Phase 1; this
feature only supports the current/latest spec for a target, matching the
README's scope (no version history).

- 200 → `ApiSpec` schema (§0.4).
- 401/403 → no body.
- 404 → `Problem`.
- 500 → `Problem`.

### 0.3 `POST /targets/{target_id}/spec`

Path param `target_id` (required). Request body **`multipart/form-data`**,
schema `target_id_spec_body`:

```json
{
  "required": ["specFile"],
  "properties": {
    "specFile": {
      "type": "string",
      "format": "binary",
      "description": "The API specification file must be in JSON, YAML, or HAR format."
    }
  }
}
```

The multipart field name is exactly `specFile`. No other fields are part of
the request body.

- 200 → `ApiSpec` (metadata of the newly uploaded spec).
- 400 → `Problem` ("Veracode could not validate your API specification
  file") — this is a **server-side validation failure**. 400 is not one of
  the HTTP Client's specifically-mapped status codes (only 401/403/404/
  409/422 are — see
  [http-client/design.md §4](../http-client/design.md#4-error-handling)),
  so it propagates unchanged as the base `VeracodeApiError`; this feature
  never tries to replicate Veracode's spec-content validation.
- 401/403 → no body.
- 501 → `Problem`.

### 0.4 `GET /targets/{target_id}/spec/download`

Path param `target_id` (required). Query param `scan_id` (optional) — not
exposed in Phase 1, same rationale as §0.2.

- 200, `Content-Type: application/octet-stream`, `{"type": "string",
  "format": "binary"}` — raw file bytes, **not JSON**. This is why the HTTP
  Client needed the `raw=True` amendment (see
  [http-client/requirements.md Amendment](../http-client/requirements.md#amendment-multipart-upload-and-raw-binary-responses)).
- 401/403 → no body.
- 404 → `Problem`.
- 500 → `Problem`.

### 0.5 Schemas

`ApiSpec` (metadata returned by both `GET .../spec` and `POST .../spec`):

| Field | Type | Notes |
|---|---|---|
| `api_spec_s3_id` | string | API specification identifier on S3 |
| `api_spec_name` | string | API specification name |
| `api_spec_url` | string | API specification URL provided by the client |
| `api_spec_type` | string | API specification type |
| `target_id` | string | ID of the target |
| `analysis_run_id` | string | ID of the analysis run |
| `uploaded_at` | string (UTC datetime) | |
| `updated_at` | string (UTC datetime) | |
| `uploaded_by` | string | principal who uploaded |
| `updated_by` | string | principal who last modified |
| `scope_rules` | array of `ScopeRule` | |

**Note on `required`:** the OpenAPI document lists `specId` as a required
field of `ApiSpec`, but `specId` is never defined in `ApiSpec.properties` —
this is a documented inconsistency in the upstream spec, not a field this
SDK models. Per requirement §0.6 below, every `ApiSpecification` field is
therefore treated as optional (`None`-defaulted) except `target_id`, which
this feature always has from the caller regardless of what the response
contains.

`ScopeRule` (required: `http_method`, `scope_rule_index`, `scope_rule_type`,
`scope_type`, `url`, `uuid`):

| Field | Type | Notes |
|---|---|---|
| `uuid` | string | |
| `http_method` | string | Enterprise-mode HTTP method for API scans |
| `url` | string | Enterprise-mode URL for API scans |
| `scope_type` | enum `AUDIT \| BLOCK \| IGNORE` | |
| `scope_rule_type` | enum `PATTERN \| INDEX` | |
| `scope_rule_index` | integer | |

### 0.6 Field-optionality decision

Because of the `specId` inconsistency above, and because no example
response for `POST/GET .../spec` is present in either the OpenAPI file or
the Postman collection, this feature does not assume any `ApiSpec` field
beyond `target_id` is always present. §7 (Integration Validation) of
[the implementation plan] confirms the real shape against a live account;
until then, every optional field defaults to `None` (or `[]` for
`scope_rules`) rather than raising if absent.

### 0.7 HTTP status codes and error responses

Same `Problem` (RFC 7807) shape as Target Management
([target-management/requirements.md §0.7](../target-management/requirements.md#07-http-status-codes-and-error-responses)) —
no new error schema introduced. All HTTP-level errors (401, 403, 404, 400,
501, 500) propagate unchanged from the shared HTTP Client — this feature
never wraps them (README "Error Handling").

---

## 1. Upload an API Specification

1.1. `upload(target_id: str, file_path: str | Path) -> ApiSpecification`.
1.2. `target_id` blank/whitespace-only → `ApiSpecificationValidationError`
     before any HTTP call.
1.3. `file_path` must reference an existing, readable file →
     `ApiSpecificationFileNotFoundError` before any HTTP call.
1.4. The file is read as bytes and sent as `multipart/form-data`, field
     name `specFile`, filename = `Path(file_path).name`, content-type
     guessed via `mimetypes.guess_type` (fallback
     `application/octet-stream`) — never re-encoded, re-parsed, or
     validated as JSON/YAML by the SDK (README "Validation
     Responsibilities": never duplicate server-side validation).
1.5. On success (200), returns `ApiSpecification.from_api(response.data)`.
1.6. A 400 (Veracode rejects the file content) propagates as the base
     `VeracodeApiError`, unchanged, per §0.3 — 400 has no more specific
     mapped exception class.
1.7. This feature never creates, checks for, or assumes the existence of a
     Target beyond letting a 404 from the HTTP Client propagate naturally
     (README "Responsibilities": "not responsible for... validating Target
     existence beyond API responses").

## 2. Get API Specification metadata

2.1. `get(target_id: str) -> ApiSpecification`.
2.2. `target_id` blank/whitespace-only → `ApiSpecificationValidationError`
     before any HTTP call.
2.3. On success (200), returns `ApiSpecification.from_api(response.data)`.
2.4. A 404 (no spec uploaded yet, or unknown target) propagates as
     `VeracodeNotFoundError`, unchanged.

## 3. Download API Specification contents

3.1. `download(target_id: str, destination_path: str | Path) -> Path`.
3.2. `target_id` blank/whitespace-only → `ApiSpecificationValidationError`
     before any HTTP call.
3.3. `destination_path`'s parent directory must exist →
     `ApiSpecificationValidationError` before any HTTP call (this feature
     never creates directories on the caller's behalf).
3.4. Calls `GET .../spec/download` with `raw=True`; writes the returned
     bytes to `destination_path` via `Path.write_bytes`; returns the
     resolved `Path`.
3.5. The SDK never inspects or logs the downloaded content (README
     "Logging": never log API Specification contents).

## 4. Typed models

4.1. `ScopeType(str, Enum)`: `AUDIT`, `BLOCK`, `IGNORE`.
4.2. `ScopeRuleType(str, Enum)`: `PATTERN`, `INDEX`.
4.3. `ScopeRule` — frozen dataclass mirroring §0.5, with `from_api`.
4.4. `ApiSpecification` — frozen dataclass mirroring §0.5/§0.6, with
     `from_api`. No separate `ApiSpecificationUploadRequest` model: the
     public API takes `(target_id, file_path)` as plain arguments (README
     "Public SDK API"); wrapping two primitives in a request object adds a
     type with no behavior, so it is intentionally not built.

## 5. Client-side validation

5.1. Exactly the three checks in §1.2/1.3, §2.2, §3.2/3.3 — nothing beyond
     required-parameter, blank-string, and local-filesystem checks (README
     "Validation Responsibilities").

## 6. Error handling

6.1. `ApiSpecificationValidationError(VeracodeSDKError)` — raised only for
     the client-side checks above; carries a `rule` attribute, following
     the naming/subclassing convention established in
     [target-management/design.md §2.2](../target-management/design.md#22-srcveracode_dastexceptionspy)
     (subclasses `VeracodeSDKError` directly, never `VeracodeApiError`).
6.2. `ApiSpecificationFileNotFoundError(VeracodeSDKError)` — raised only
     when `upload()`'s `file_path` does not exist; carries a `path`
     attribute.
6.3. Every HTTP-level failure (`VeracodeNotFoundError`,
     `VeracodeValidationError`, etc.) propagates unmodified — this feature
     never catches and rewraps an `HttpClient` exception (README "Error
     Handling").

## 7. Logging

7.1. `upload()`: INFO "upload started" (target_id, filename) before the
     call, INFO "upload completed" (target_id, `api_spec_name`) after.
7.2. `get()`: INFO "metadata retrieved" (target_id) after success.
7.3. `download()`: INFO "download started" (target_id, destination path)
     before, INFO "download completed" (target_id, byte count) after.
7.4. Validation failures: INFO with the failing rule/path, never the file's
     contents.
7.5. Never log: HTTP headers, authentication info, file contents, API
     Specification contents (README "Logging") — HTTP-level logging is the
     HTTP Client's responsibility, not duplicated here.

## 8. Boundaries (non-goals for this feature)

Per [README.md "Out of Scope"](README.md#out-of-scope): no editing of API
Specifications, no version history, no spec comparison, no deep spec
validation, no automatic Target creation, no Application linking, no scan
execution/configuration. No dependency on Team Management. No direct
`requests` import or HMAC logic — all HTTP goes through the shared
`HttpClient`.

## 9. Public interface and reuse

```python
client.api_specifications.upload(target_id, "openapi.yaml") -> ApiSpecification
client.api_specifications.get(target_id) -> ApiSpecification
client.api_specifications.download(target_id, "downloaded-openapi.yaml") -> Path
```

`ApiSpecificationsService` is constructed with the **same `HttpClient`
instance** already constructed for `TargetsService` (same
`TARGET_CONFIGURATION_SERVICE_BASE_URL`, imported from
`services/targets.py` rather than redefined) — one `Session`/connection
pool per Veracode API domain, not per service.

## 10. Testability

Stub/fake `HttpClient` returning prepared `HttpResponse` values (including
`data: bytes` for the `raw=True` download case) or raising prepared
`VeracodeApiError` subclasses — same approach as
[target-management/requirements.md §13](../target-management/requirements.md#13-testability).
No real file I/O beyond `tmp_path`-based pytest fixtures for `upload`'s
source file and `download`'s destination.
