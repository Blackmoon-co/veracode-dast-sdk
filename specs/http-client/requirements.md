# Requirements — HTTP Client

Source context: [README.md](README.md). Architecture and conventions:
[AGENTS.md](../../AGENTS.md). Builds on
[specs/authentication](../authentication/requirements.md).

Format: user story + EARS-style acceptance criteria per requirement.

---

## 1. HTTP verb support

**User story:** As a future SDK service, I want a single client exposing one
method per HTTP verb, so that I can perform any Veracode REST operation
without touching `requests` myself.

**Acceptance criteria:**

1.1. WHEN a caller invokes `get(path, ...)` THEN THE SYSTEM SHALL send an
HTTP `GET` request to `base_url` joined with `path`.

1.2. WHEN a caller invokes `post(path, json=..., ...)` THEN THE SYSTEM SHALL
send an HTTP `POST` request with the given payload serialized as JSON.

1.3. WHEN a caller invokes `put(path, json=..., ...)` THEN THE SYSTEM SHALL
send an HTTP `PUT` request with the given payload serialized as JSON.

1.4. WHEN a caller invokes `patch(path, json=..., ...)` THEN THE SYSTEM
SHALL send an HTTP `PATCH` request with the given payload serialized as
JSON.

1.5. WHEN a caller invokes `delete(path, ...)` THEN THE SYSTEM SHALL send an
HTTP `DELETE` request to `base_url` joined with `path`.

1.6. THE SYSTEM SHALL NOT expose any HTTP method other than GET, POST, PUT,
PATCH, DELETE in Phase 1 (e.g. no `HEAD`, `OPTIONS` convenience methods),
per the README scope.

1.7. THE SYSTEM SHALL NOT expose a public generic `request(method, path,
...)` method. The implementation shared by the five verb methods SHALL be
private (e.g. `_request`) — a resource-oriented, verb-specific public API
is simpler for services to use correctly than a generic method that
requires the caller to pass the HTTP method as a string, and there is no
Phase 1 use case that needs a caller-supplied arbitrary method.

---

## 2. Base URL

**User story:** As an SDK maintainer, I want the HTTP client usable against
any Veracode API base URL, so that Target Management, a future AppSec-based
service, and future DAST services can each target their own Veracode API
without the client hardcoding knowledge of any one of them.

Veracode exposes multiple REST APIs under different base URLs that all
share the same HMAC authentication — for example the AppSec API
(`https://api.veracode.com/appsec`) and the DAST Target Configuration
Service (`https://api.veracode.com/dae/api/tcs-api/api/v1`). Future DAST
services may introduce further base URLs. Per
[AGENTS.md §3.1](../../AGENTS.md#31-authentication-is-base-url-agnostic),
each *service* owns the base URL of the Veracode API it talks to — the
HTTP client itself must stay agnostic to all of them.

**Acceptance criteria:**

2.1. WHEN the client is constructed THEN THE SYSTEM SHALL require an
explicit `base_url` argument, with no built-in default value. THE SYSTEM
SHALL NOT assume, favor, or hardcode any single Veracode API base URL (not
the AppSec API, not the DAST Target Configuration Service, not any future
one) anywhere in this feature.

2.2. THE SYSTEM SHALL allow separate `HttpClient` instances to be
constructed with different `base_url` values, so that a service targeting
the AppSec API, a service targeting the DAST Target Configuration Service,
and a service targeting any future Veracode DAST API can each get a
correctly configured client, without any change to this feature or to the
authentication module.

2.3. WHEN `base_url` and `path` are combined THEN THE SYSTEM SHALL produce
exactly one `/` between them regardless of whether `base_url` ends with `/`
or `path` starts with `/`.

2.4. THE SYSTEM SHALL NOT read the base URL from an environment variable.
Per [AGENTS.md §6.1](../../AGENTS.md#61-infrastructure-configuration), only
`VERACODE_API_KEY_ID` and `VERACODE_API_KEY_SECRET` are Phase 1 environment
variables; the base URL for a given Veracode API is supplied at
construction time by whichever service owns that API, not read implicitly.

2.5. For Phase 1, only the DAST Target Configuration Service base URL
(`https://api.veracode.com/dae/api/tcs-api/api/v1`) is actually
instantiated, by the (out-of-scope) Target Management service. THE SYSTEM
SHALL NOT hardcode that value, or any other Veracode API base URL, inside
this feature's code — it is always supplied by the caller.

---

## 3. Authentication provider injection

**User story:** As the SDK architect, I want the HTTP client to receive an
already-created authentication provider rather than build one itself, so
that authentication and HTTP communication stay completely independent —
each testable in isolation, each free to evolve without touching the
other.

**Acceptance criteria:**

3.1. WHEN the client is constructed THEN THE SYSTEM SHALL require an
explicit `auth` argument (a `requests`-compatible auth provider), with no
built-in default value.

3.2. THE SYSTEM SHALL NOT import `get_veracode_auth`, `create_hmac_auth`,
`load_credentials_from_env`, `VeracodeCredentials`, or any other symbol
from `auth.py` or `config.py`. Obtaining an auth provider is entirely the
caller's responsibility, performed *before* constructing an `HttpClient`;
this feature only ever receives the finished result.

3.3. WHEN any request is sent THEN THE SYSTEM SHALL attach the supplied
auth provider to it.

3.4. THE SYSTEM SHALL NOT implement any custom HMAC signing logic; signing
is entirely delegated to the injected auth provider.

---

## 4. Timeouts

**User story:** As an SDK consumer, I want every request to have a bounded
timeout, so a hung Veracode API call cannot hang my process forever.

**Acceptance criteria:**

4.1. WHEN the client is constructed without an explicit timeout THEN THE
SYSTEM SHALL apply a default timeout of 30 seconds to every request.

4.2. WHEN the client is constructed with an explicit `timeout` argument
THEN THE SYSTEM SHALL apply that value to every request made by that
instance instead of the default.

4.3. WHEN a request exceeds its timeout THEN THE SYSTEM SHALL raise
`VeracodeTimeoutError` instead of letting `requests.exceptions.Timeout`
propagate.

---

## 5. Retries

**User story:** As an SDK consumer, I want transient failures retried
automatically, so a single dropped connection or momentary 503 doesn't fail
my whole operation.

**Acceptance criteria:**

5.1. WHEN a response has status code 429, 500, 502, 503, or 504 THEN THE
SYSTEM SHALL retry the request, up to the configured retry limit, for
idempotent methods (GET, PUT, DELETE).

5.2. WHEN the client is constructed without an explicit retry count THEN
THE SYSTEM SHALL allow up to 3 retries per request by default.

5.3. WHEN the client is constructed with an explicit `max_retries` argument
THEN THE SYSTEM SHALL use that value instead of the default.

5.4. THE SYSTEM SHALL NOT retry `POST` or `PATCH` requests on a
status-code-based failure, since those methods are not assumed idempotent.

5.5. WHEN a connection-level failure occurs (DNS failure, refused
connection, reset connection) THEN THE SYSTEM SHALL retry it at the
transport level regardless of HTTP method, up to the configured retry
limit.

5.6. WHEN a response includes a `Retry-After` header on a retried status
code THEN THE SYSTEM SHALL honor it as the wait time before the next
attempt.

5.7. WHEN all retries for a request are exhausted without success THEN THE
SYSTEM SHALL translate the final outcome into the appropriate SDK exception
(§8) rather than raising a retry-library-specific exception.

---

## 6. Request payload serialization

**User story:** As a future SDK service, I want to pass a plain dict/list
as a request body and have it serialized correctly, so I don't need to call
`json.dumps` or set headers myself.

**Acceptance criteria:**

6.1. WHEN `json` is provided to `post`, `put`, or `patch` THEN THE SYSTEM
SHALL serialize it as the request body and set `Content-Type:
application/json`.

6.2. WHEN `params` is provided to any verb method THEN THE SYSTEM SHALL
encode it as the request's URL query string.

6.3. WHEN `headers` is provided to any verb method THEN THE SYSTEM SHALL
merge it with the client's default headers, with caller-supplied header
values taking precedence over defaults on key conflicts.

6.4. THE SYSTEM SHALL send `Accept: application/json` by default on every
request.

---

## 7. Response deserialization

**User story:** As a future SDK service, I want response bodies handed to
me as plain Python data, so I can build typed models myself without the
HTTP client knowing about any resource shape.

**Acceptance criteria:**

7.1. WHEN a response has a 2xx status code and a non-empty JSON body THEN
THE SYSTEM SHALL deserialize it into a `dict` or `list` and expose it as
`data` on the returned value.

7.2. WHEN a response has a 2xx status code and an empty body (e.g. `204 No
Content`) THEN THE SYSTEM SHALL set `data` to `None`.

7.3. THE SYSTEM SHALL NOT construct or import any typed model class; the
returned `data` is always a plain `dict`, `list`, or `None`.

7.4. IF a response has a 2xx status code but a body that is not valid JSON
THEN THE SYSTEM SHALL raise `VeracodeApiError` describing the parsing
failure, instead of letting the JSON-decoding exception propagate.

---

## 8. Response validation and error translation

**User story:** As an SDK consumer, I want every failure — a well-known
HTTP error status, a generic error status, a connection problem, or a
timeout — to surface as a specific, catchable SDK exception, so I can
handle common cases (an unauthenticated call, a missing resource, a
conflicting update) programmatically instead of inspecting raw status
codes myself, while still being able to catch one common base type for
anything else.

**Acceptance criteria:**

8.1. WHEN a response has status code 401 THEN THE SYSTEM SHALL raise
`VeracodeAuthenticationError`.

8.2. WHEN a response has status code 403 THEN THE SYSTEM SHALL raise
`VeracodeAuthorizationError`.

8.3. WHEN a response has status code 404 THEN THE SYSTEM SHALL raise
`VeracodeNotFoundError`.

8.4. WHEN a response has status code 409 THEN THE SYSTEM SHALL raise
`VeracodeConflictError`.

8.5. WHEN a response has status code 422 THEN THE SYSTEM SHALL raise
`VeracodeValidationError`.

8.6. WHEN a response has a status code in the 400–499 range not covered by
8.1–8.5 (e.g. 400, 405, 429), or a status code in the 500–599 range after
retries (§5) are exhausted, THEN THE SYSTEM SHALL raise `VeracodeApiError`
— the base exception of this feature's hierarchy — rather than inventing a
dedicated subclass for every remaining status code.

8.7. WHEN a connection-level failure occurs and retries are exhausted THEN
THE SYSTEM SHALL raise `VeracodeConnectionError`.

8.8. WHEN a request times out (§4.3) THEN THE SYSTEM SHALL raise
`VeracodeTimeoutError`.

8.9. THE SYSTEM SHALL NOT let any exception from `requests`, `urllib3`, or
`json` propagate to the caller; every failure path listed in this section
is translated before it leaves the client.

8.10. WHEN any exception listed in this section is raised THEN its
`method`, `url`, `status_code` (where applicable — `None` for connection
errors and timeouts), and `response_body` attributes SHALL be readable by
the caller for programmatic error handling.

8.11. `VeracodeAuthenticationError`, `VeracodeAuthorizationError`,
`VeracodeNotFoundError`, `VeracodeConflictError`, `VeracodeValidationError`,
`VeracodeConnectionError`, and `VeracodeTimeoutError` SHALL each be a
subclass of `VeracodeApiError`, so a caller can catch `VeracodeApiError`
alone to handle any HTTP-transport-level failure from this feature, or
catch a specific subclass to handle one case precisely.

8.12. Services SHALL NOT need to import or reference `requests` exception
types (e.g. `requests.Timeout`, `requests.ConnectionError`,
`requests.HTTPError`) to handle any failure from this feature; every
exception a service can catch is defined in `exceptions.py`.

---

## 9. Logging

**User story:** As an SDK maintainer, I want visibility into outgoing
requests, retries, and failures, so issues can be diagnosed from logs
without adding print statements.

**Acceptance criteria:**

9.1. WHEN a request is about to be sent THEN THE SYSTEM SHALL emit a
DEBUG-level log containing the HTTP method and the full URL (no headers,
no body, no auth material).

9.2. WHEN a response is received with a 2xx status code THEN THE SYSTEM
SHALL emit a DEBUG-level log containing the method, URL, and status code.

9.3. WHEN a request is retried (§5) THEN THE SYSTEM SHALL emit a
WARNING-level log containing the attempt number and the reason for the
retry.

9.4. WHEN a request ultimately fails (§8) THEN THE SYSTEM SHALL emit an
ERROR-level log containing the method, URL, status code (if any), and the
SDK exception type raised.

9.5. THE SYSTEM SHALL NOT log request or response body content, and SHALL
NOT log the `Authorization` header or any other auth/credential material,
at any log level.

9.6. Services built on top of this feature SHALL NOT need to add their own
request/response logging — this feature is the only layer responsible for
logging HTTP activity, so every service call is already covered without
duplication.

---

## 10. Boundaries (non-goals for this feature)

**User story:** As the SDK architect, I want this feature strictly scoped
to generic HTTP transport, so resource-specific logic doesn't leak into the
shared client.

**Acceptance criteria:**

10.1. THE SYSTEM SHALL NOT implement Target, Target Configuration, Analysis
Profile, Scanner, Analysis, or Report functionality as part of this
feature.

10.2. THE SYSTEM SHALL NOT contain any Veracode-resource-specific endpoint
path, request shape, or response shape; `path` and `json` are supplied
entirely by the caller.

10.3. THE SYSTEM SHALL NOT construct, import, or reference any class under
`models/`.

10.4. THE SYSTEM SHALL NOT implement `VeracodeClient` or wire up any
service; those are built in a later feature that consumes this one.

10.5. THE SYSTEM SHALL NOT implement pagination helpers. A caller that
needs multiple pages of a paginated resource calls a verb method once per
page using resource-specific query parameters it supplies itself.

10.6. THE SYSTEM SHALL be the only component in the codebase that imports
`requests`; every other module (services, models, `VeracodeClient`) SHALL
depend on this client instead.

10.7. THE SYSTEM SHALL NOT hardcode, reference, or favor any specific
Veracode API base URL (e.g. the AppSec API or the DAST Target
Configuration Service) inside `client.py`. `HttpClient` SHALL be equally
suited to any Veracode REST API base URL a caller supplies at construction
time.

---

## 11. Public interface and reuse

**User story:** As a maintainer of a future SDK service, I want a fully
typed, documented client class, so I can depend on it without reading its
implementation.

**Acceptance criteria:**

11.1. Every public class and method introduced by this feature SHALL have
complete type hints and a Google-style docstring.

11.2. THE SYSTEM SHALL expose the client as a single instantiable class
that holds its own configuration (an explicitly supplied base URL, an
explicitly supplied auth provider, timeout, retry count); constructing it
SHALL NOT require any global or module-level state and SHALL NOT call into
the authentication module, and different instances MAY simultaneously
target different Veracode API base URLs.

11.3. THE SYSTEM SHALL NOT introduce any dependency on Azure DevOps, a
CLI, or any other specific consumer.

---

## 12. Testability

**User story:** As a maintainer, I want to verify request construction,
retry behavior, and error translation without making real network calls,
so the test suite is fast and runs anywhere.

**Acceptance criteria:**

12.1. THE SYSTEM SHALL allow every verb method, retry path, and error
path to be tested by constructing `HttpClient` with a trivial stub/fake
auth object (any callable satisfying `requests.auth.AuthBase`'s contract)
and substituting the client's underlying transport (e.g. via `pytest`'s
`monkeypatch` against the `requests.Session` the client uses internally),
with no real network access, environment variables, or Veracode
credentials required.

12.2. THE SYSTEM SHALL NOT require a new third-party mocking/HTTP-fixture
dependency; constructing plain `requests.Response` objects (already a
transitive dependency via `requests`) is sufficient to exercise every path
in this feature.

12.3. THE SYSTEM SHALL NOT require any real Veracode account, API key, or
network connectivity to run its test suite.

---

## Amendment: Multipart Upload and Raw Binary Responses

Added during implementation of API Specification Management, which
discovered that the DAST Target Configuration Service's spec-upload and
spec-download endpoints do not fit the JSON-only surface this feature
originally specified — see
[api-specification-management/requirements.md §0.3–0.4](../api-specification-management/requirements.md#03-post-targetstarget_idspec).
`POST /targets/{target_id}/spec` requires `multipart/form-data`; `GET
/targets/{target_id}/spec/download` returns `application/octet-stream` raw
bytes, not JSON. Per `AGENTS.md`'s rule that services never import
`requests`, the fix has to live in this feature, not in a workaround inside
the new service. This is documented here as a non-silent, additive
amendment rather than folded invisibly into §1/§7 above.

**User story:** As API Specification Management, I want to upload a file
as `multipart/form-data` and download a raw binary response, through the
same `HttpClient` every other feature uses, so that I never need my own
`requests` import.

**Acceptance criteria:**

A.1. WHEN a caller invokes `post(path, files=..., ...)` THEN THE SYSTEM
SHALL send the request as `multipart/form-data` with the given file
field(s), and SHALL NOT set a `json` body or force `Content-Type:
application/json` on that request.

A.2. `post`'s `json` and `files` parameters are mutually exclusive by
convention (only one is ever supplied by a caller in this SDK); THE SYSTEM
SHALL NOT add runtime validation rejecting both being set, since `post` is
only ever called by this SDK's own services, not by third-party code
(internal-boundary trust, per AGENTS.md §5).

A.3. WHEN a caller invokes `get(path, raw=True, ...)` THEN, on a 2xx
response, THE SYSTEM SHALL return an `HttpResponse` whose `data` is the raw
response body as `bytes` (or `None` if the body is empty), and SHALL NOT
attempt `response.json()` on that response.

A.4. `HttpResponse.data`'s type SHALL widen to `dict[str, Any] | list[Any]
| bytes | None` to accommodate A.3; this SHALL NOT change the behavior of
any existing call site that does not pass `raw=True`.

A.5. Error translation (§8 of the original requirements) applies
identically regardless of `files`/`raw` — a non-2xx status still raises the
same status-code-mapped exception; `raw=True` only changes 2xx handling.

A.6. THE SYSTEM SHALL NOT add a sixth verb method or a public generic
`request()` method to accommodate this — `files` and `raw` are additional
optional parameters on the existing `post`/`get` methods, preserving the
five-verb, no-generic-`request()` design from §1.
