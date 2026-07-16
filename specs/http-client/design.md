# Design — HTTP Client

Implements the requirements in [requirements.md](requirements.md), within
the architecture and conventions defined in [AGENTS.md](../../AGENTS.md).
Extends the exception hierarchy from
[specs/authentication](../authentication/design.md#21-srcveracode_dastexceptionspy);
otherwise independent of it — this feature does not import `auth.py` or
`config.py` (see [AGENTS.md §3.1](../../AGENTS.md#31-authentication-is-base-url-agnostic)).

---

## 1. Overview

This feature builds the second layer of the SDK's layered architecture:

```
VeracodeClient          ← NOT built in this feature
      ↓
  HTTP Client            ← THIS FEATURE (client.py: HttpClient, HttpResponse)
      ↓
   Services              ← NOT built in this feature
      ↓
    Models               ← NOT built in this feature
      ↓
  REST API
```

`HttpClient` is a single, instantiable, stateless-with-respect-to-business-data
class that wraps a `requests.Session`. It is the only place in the codebase
that imports `requests`. It reuses `VeracodeSDKError` as the root of its
own exception additions, but it does **not** import anything else from the
authentication feature. It knows nothing about Targets, Analyses, or any
other Veracode resource — every request's path, query parameters, and body
come entirely from the caller (a future Service).

**Authentication is injected, never created.** Per the architecture
decision that authentication and HTTP communication are completely
independent, `HttpClient` receives a ready-made `requests`-compatible auth
provider as a required constructor argument. It never calls
`get_veracode_auth()`, never imports `auth.py` or `config.py`, and has no
fallback for a missing auth argument. Whoever constructs an `HttpClient`
(a future Service, or the `VeracodeClient` wiring) is responsible for
calling `get_veracode_auth()` first and passing the result in. This keeps
the two features testable in complete isolation — this feature's tests
never need real or fake credentials, only a trivial stub auth object.

**Multiple Veracode API base URLs.** Per
[AGENTS.md §3.1](../../AGENTS.md#31-authentication-is-base-url-agnostic),
Veracode exposes several REST APIs under different base URLs sharing the
same HMAC scheme — e.g. the AppSec API (`https://api.veracode.com/appsec`)
and the DAST Target Configuration Service
(`https://api.veracode.com/dae/api/tcs-api/api/v1`). `HttpClient` takes
`base_url` as a **required** constructor argument with no built-in default,
so it stays equally suited to any of them. Each future service is
responsible for constructing its own `HttpClient` instance with the base
URL of the Veracode API it targets — for Phase 1, the (out-of-scope)
Target Management service will construct
`HttpClient(base_url="https://api.veracode.com/dae/api/tcs-api/api/v1")`.
Nothing in this feature references that (or any other) URL string; the
value above is illustrative of how a future caller uses this class, not
something implemented here.

`VeracodeClient` (the public entry point that exposes `client.targets`,
etc.) is **not** built here — it is assembled in the feature that adds the
first Service, once there is a service to wire up.

---

## 2. Components and Interfaces

### 2.1 `src/veracode_dast/exceptions.py` (extended)

This feature adds eight exception classes to the hierarchy already defined
by the authentication feature ([design.md
§2.1](../authentication/design.md#21-srcveracode_dastexceptionspy)):

```python
class VeracodeApiError(VeracodeSDKError):
    """Base class for all HTTP-transport-level failures, and the exception
    raised directly for any status code that has no more specific subclass
    below.

    Attributes:
        method: The HTTP method of the request that failed (e.g. "GET").
        url: The full request URL.
        status_code: The HTTP status code, or None if the failure occurred
            before a response was received (connection error, timeout, or
            local JSON-decode failure).
        response_body: The parsed JSON body (dict/list), the raw response
            text if it wasn't valid JSON, or None if no response was
            received.
    """

    def __init__(
        self,
        message: str,
        *,
        method: str,
        url: str,
        status_code: int | None = None,
        response_body: dict[str, Any] | list[Any] | str | None = None,
    ) -> None: ...


class VeracodeConnectionError(VeracodeApiError):
    """Raised when a request fails at the connection level (DNS failure,
    refused connection, reset connection) after retries are exhausted."""


class VeracodeTimeoutError(VeracodeApiError):
    """Raised when a request exceeds its configured timeout."""


class VeracodeAuthenticationError(VeracodeApiError):
    """Raised for HTTP responses with status code 401."""


class VeracodeAuthorizationError(VeracodeApiError):
    """Raised for HTTP responses with status code 403."""


class VeracodeNotFoundError(VeracodeApiError):
    """Raised for HTTP responses with status code 404."""


class VeracodeConflictError(VeracodeApiError):
    """Raised for HTTP responses with status code 409."""


class VeracodeValidationError(VeracodeApiError):
    """Raised for HTTP responses with status code 422."""
```

**Naming note:** the base class is `VeracodeApiError` (lowercase `pi`),
distinct from `VeracodeAPIError` used in an earlier draft of this design —
this is the name settled on for this feature and is used consistently
throughout.

**Why a flat set of specific subclasses plus one catch-all, instead of a
`VeracodeClientError`/`VeracodeServerError` split:** the five subclasses
above map to the status codes a Service is actually expected to react to
differently (unauthenticated, unauthorized, missing resource, conflicting
state, invalid payload). Every other 4xx (400, 405, 429, ...) and every
5xx carries no behavior this SDK needs to distinguish in Phase 1, so it is
raised as `VeracodeApiError` directly rather than inventing a subclass per
remaining status code — adding `VeracodeClientError`/`VeracodeServerError`
back in as an *intermediate* layer between `VeracodeApiError` and "no more
specific subclass" would only reproduce the same catch-all one level down,
with no behavioral difference. A caller can always catch `VeracodeApiError`
to handle "any HTTP failure," or a specific subclass to handle one case
precisely; `error.status_code` remains available either way.

`VeracodeAuthError` (from the authentication feature) is **not** the
parent of `VeracodeAuthenticationError`/`VeracodeAuthorizationError`. They
are unrelated exception trees on purpose: `VeracodeAuthError` covers
failures in *obtaining* an auth provider (before any HTTP call is even
possible), while `VeracodeAuthenticationError`/`VeracodeAuthorizationError`
cover a Veracode API *rejecting* a request that already carried one. Per
the architecture decision that authentication and HTTP communication are
independent modules, this feature does not import `VeracodeAuthError` or
express any relationship to it.

### 2.2 `src/veracode_dast/client.py`

```python
DEFAULT_TIMEOUT: Final = 30.0
DEFAULT_MAX_RETRIES: Final = 3
_RETRY_STATUS_FORCELIST: Final = (429, 500, 502, 503, 504)
_RETRIABLE_METHODS: Final = frozenset({"GET", "PUT", "DELETE", "HEAD", "OPTIONS"})


@dataclass(frozen=True)
class HttpResponse:
    """A plain, requests-independent view of an HTTP response.

    Attributes:
        status_code: The HTTP status code of a successful (2xx) response.
        data: The deserialized JSON body as a dict/list, or None if the
            response body was empty. Never a typed model.
        headers: The response headers.
    """

    status_code: int
    data: dict[str, Any] | list[Any] | None
    headers: Mapping[str, str]


class HttpClient:
    """Generic, resource-agnostic HTTP client for the Veracode DAST REST API.

    This is the only component in the SDK allowed to import ``requests``.
    Every SDK service must depend on an instance of this class instead of
    calling ``requests`` directly.
    """

    def __init__(
        self,
        base_url: str,
        auth: AuthBase,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """Create a configured HTTP client for one Veracode API.

        Args:
            base_url: Scheme + host (+ path prefix) every request made by
                this instance is resolved against, e.g.
                ``"https://api.veracode.com/dae/api/tcs-api/api/v1"``.
                Required — this class has no default, since a given
                instance is always scoped to one specific Veracode API
                (see AGENTS.md §3.1). Callers targeting a different
                Veracode API construct a separate ``HttpClient`` instance
                with that API's base URL.
            auth: A ready-made ``requests``-compatible auth provider (e.g.
                the result of calling ``get_veracode_auth()``). Required —
                this class has no default and never creates authentication
                itself; authentication and HTTP communication are
                independent modules, so the caller obtains an auth
                provider first and passes it in here.
            timeout: Seconds to wait for a response before raising
                ``VeracodeTimeoutError``.
            max_retries: Maximum retry attempts for idempotent methods on
                connection errors or the statuses in
                ``_RETRY_STATUS_FORCELIST``.
        """
        ...

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse: ...

    def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse: ...

    def put(
        self,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse: ...

    def patch(
        self,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse: ...

    def delete(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse: ...
```

All five verb methods share one private implementation,
`_request(method, path, *, json=None, params=None, headers=None) ->
HttpResponse`, that:

1. Builds the full URL: `base_url.rstrip("/") + "/" + path.lstrip("/")`.
2. Merges `headers` over the default headers (`{"Accept": "application/json"}`,
   plus `Content-Type: application/json` implicitly set by `requests` when
   `json` is passed).
3. Sends the request via `self._session.request(...)` with `auth=self._auth`
   and `timeout=self._timeout`.
4. Logs and translates outcomes per §4 and §5 below.
5. Returns an `HttpResponse` on any 2xx status.

`_request` is the only place that touches `requests` types; every public
method is a thin, five-line wrapper around it.

**No public `request()` method.** `_request` is private and stays that
way — `HttpClient`'s public surface is exactly `get`/`post`/`put`/`patch`/
`delete`. A generic public `request(method, path, ...)` was considered and
rejected: it would let a caller pass an arbitrary method string (including
typos, or methods this SDK doesn't support), pushes a stringly-typed
parameter onto every call site, and there is no Phase 1 caller that needs
it — the five resource-oriented methods cover every case in README's
Scope. If a genuine need for a sixth verb appears later, it is added as a
sixth named method, not by opening up the generic entry point.

### 2.3 Session Management: `requests.Session()` vs. `requests.request()`

**Decision: use one `requests.Session` per `HttpClient` instance.**

| | `requests.Session()` (chosen) | `requests.request()` per call |
|---|---|---|
| Connection reuse | Yes — pools and reuses the underlying TCP/TLS connection across calls to the same host via `urllib3`'s connection pool. | No — each call opens a fresh connection (and, over HTTPS, repeats the TLS handshake). |
| Retry/backoff configuration | Supported via a `Retry`-configured `HTTPAdapter` mounted once (§2.4) — required for requirement §5. | Not supported directly; would need to pass an equivalent adapter-configured `Session` per call anyway, which defeats the simplicity of using the module-level function. |
| Default headers | Set once on `session.headers`, applied to every call automatically. | Must be passed explicitly on every call. |
| Thread-safety | A single `Session` instance is not guaranteed safe for concurrent use from multiple threads (per `requests`' own documentation) — each thread should use its own `HttpClient`/`Session`. | Each call is independent, so this concern doesn't apply. |
| Cost for Phase 1's call volume (single Target CRUD calls) | Negligible extra cost (one `Session` object for the lifetime of an `HttpClient`). | Negligible extra cost either way at this volume. |
| Cost for future phases (Phase 3 "Wait for Completion" polling, pagination) | Meaningfully faster — repeated calls to the same host reuse the connection instead of paying handshake cost every poll. | Meaningfully slower under repeated polling against the same host. |

`requests.Session()` is the clear choice: it is required to configure
retries at all (§2.4 depends on mounting an adapter, which only a
`Session` supports), and it is the only option that gives future phases —
especially status polling — a meaningful performance benefit. The one
trade-off, thread-safety, is accepted as a documented limitation rather
than solved with internal locking: per [AGENTS.md
§5](../../AGENTS.md#5-design-principles) this SDK makes no assumption
about the caller's execution context, so a caller running `HttpClient`
across multiple threads is expected to construct one instance per thread
(the same guidance `requests` itself gives for `Session`), rather than
sharing one instance. Building thread-safety machinery nobody asked for
would be scope creep for a Phase 1 SDK with no concurrent-caller
requirement.

### 2.4 Session and retry configuration

`HttpClient.__init__` builds one `requests.Session` and mounts a
`urllib3.util.retry.Retry` via `requests.adapters.HTTPAdapter` for both
`http://` and `https://`:

```python
retry = Retry(
    total=max_retries,
    backoff_factor=0.5,
    status_forcelist=_RETRY_STATUS_FORCELIST,
    allowed_methods=_RETRIABLE_METHODS,
    respect_retry_after_header=True,
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)
```

This uses `urllib3` (already vendored as a transitive dependency of
`requests` — no new dependency) to handle retry counting, backoff, and
`Retry-After` parsing, instead of hand-rolled retry-loop code. `POST` and
`PATCH` are excluded from `allowed_methods`, so they are never retried on a
5xx/429 status (requirement 5.4); connection-level failures below the
adapter (DNS, refused/reset connection) are retried by `urllib3` regardless
of method, matching requirement 5.5.

The `Session` is created once per `HttpClient` instance and reused across
calls purely for connection pooling — it holds no per-request or business
state, so this does not violate the "Stateless" design principle in
[AGENTS.md §5](../../AGENTS.md#5-design-principles) (that principle is
about business/domain state, which this class never holds).

---

## 3. Data Model

| Type | Field | Notes |
|---|---|---|
| `HttpResponse` | `status_code` | `int`, always 2xx (non-2xx raises instead of returning). |
| `HttpResponse` | `data` | `dict \| list \| None`. `None` only for an empty body. |
| `HttpResponse` | `headers` | Read-only mapping of response headers. |

No other data types are introduced. `HttpClient` itself holds only
configuration (`base_url`, `auth`, `timeout`, `_session`) as private
instance attributes — it has no public data attributes.

---

## 4. Error Handling

| Condition | Exception | `status_code` |
|---|---|---|
| Connection error (DNS, refused/reset), retries exhausted | `VeracodeConnectionError` | `None` |
| Request exceeds `timeout` | `VeracodeTimeoutError` | `None` |
| 2xx response, body is not valid JSON | `VeracodeApiError` | actual 2xx code |
| Response status 401 | `VeracodeAuthenticationError` | 401 |
| Response status 403 | `VeracodeAuthorizationError` | 403 |
| Response status 404 | `VeracodeNotFoundError` | 404 |
| Response status 409 | `VeracodeConflictError` | 409 |
| Response status 422 | `VeracodeValidationError` | 422 |
| Any other 400–499 response | `VeracodeApiError` | actual code |
| 500–599 response, retries exhausted | `VeracodeApiError` | actual code |

Translation happens in `_request`:

```python
_STATUS_EXCEPTIONS: Final[dict[int, type[VeracodeApiError]]] = {
    401: VeracodeAuthenticationError,
    403: VeracodeAuthorizationError,
    404: VeracodeNotFoundError,
    409: VeracodeConflictError,
    422: VeracodeValidationError,
}

try:
    response = self._session.request(method, url, ..., timeout=self._timeout)
except requests.exceptions.Timeout as exc:
    raise VeracodeTimeoutError(..., method=method, url=url) from exc
except requests.exceptions.ConnectionError as exc:
    raise VeracodeConnectionError(..., method=method, url=url) from exc

if response.status_code >= 400:
    exception_cls = _STATUS_EXCEPTIONS.get(response.status_code, VeracodeApiError)
    raise exception_cls(..., status_code=response.status_code, ...)

# 2xx: parse body
if not response.content:
    return HttpResponse(response.status_code, None, response.headers)
try:
    return HttpResponse(response.status_code, response.json(), response.headers)
except ValueError as exc:
    raise VeracodeApiError(..., status_code=response.status_code,
                            response_body=response.text) from exc
```

`_STATUS_EXCEPTIONS` is a small lookup table, not a chain of `if`
statements — adding a sixth specific status code in a later feature is a
one-line addition to this dict, not a new branch. By the time `_request`
reaches this check, `requests`'s own `Session` (via the mounted `Retry`
adapter) has already exhausted retries for a retriable method/status — no
separate retry-counting code is needed here. `raise_for_status()` is
intentionally not used, since it raises `requests.exceptions.HTTPError`,
which requirement 8.9 forbids letting propagate; the explicit status-code
lookup above replaces it.

`response_body` on every exception in `_STATUS_EXCEPTIONS.values()` (and on
the `VeracodeApiError` fallback) is the parsed JSON body when the error
response is JSON, otherwise the raw text (some APIs return plain-text or
HTML error bodies) — populated with a `try: response.json() except
ValueError: response.text` fallback, mirroring the 2xx parsing path.

---

## 5. Logging

- `client.py` gets its logger via `logging.getLogger(__name__)` — no
  custom logger/formatter (same rule as the authentication feature; that
  belongs to `utils/`, still out of scope).
- `DEBUG` before every request: `"HTTP %s %s"`, method and URL only.
- `DEBUG` after every 2xx response: `"HTTP %s %s -> %s"`, method, URL,
  status code.
- `WARNING` on each retry `urllib3` performs: this feature relies on
  `urllib3`'s own retry logging surfaced through the standard
  `urllib3`/`requests` loggers rather than re-implementing retry-attempt
  logging — no additional code is needed to satisfy requirement 9.3 beyond
  ensuring `urllib3`'s logger propagates (Python logging default).
- `ERROR` immediately before each of the raises in §4: `"HTTP %s %s
  failed: %s"`, method, URL, exception class name.
- No log statement in this file ever includes `json`, `params` values, a
  response body, or a header value — only method, URL, and status code, per
  requirement 9.5. This explicitly includes the `Authorization` header:
  `client.py` never passes `self._session.headers` or a per-request
  `headers` value to a logging call, only the fixed strings above.
- Per requirement 9.6, this feature is documented (README, AGENTS.md) as
  the *only* layer responsible for logging HTTP activity — future Service
  authors are expected not to add their own request/response logging
  around calls to `HttpClient`, since every call is already logged here.
  There is no code in this feature that enforces that on a Service (that
  would require inspecting Service code, out of scope); it is a
  documented convention future service reviews should check.

---

## 6. Security Considerations

- `auth` is passed straight to `requests.Session.request(auth=...)`; the
  client never inspects, logs, or serializes it. Because `auth` is
  injected rather than created here (§1), this feature also never touches
  `VERACODE_API_KEY_ID`/`VERACODE_API_KEY_SECRET` or any credential-loading
  code at all — its security surface is strictly smaller than a design
  where the client reads credentials itself.
- Query parameters and JSON bodies are caller-supplied business data
  (§10.2 of requirements) — this feature does not assume any of it is
  secret, but per §9.5 it is never logged regardless, since the HTTP
  client cannot know in general which fields a future service might
  consider sensitive.
- Response bodies from error paths (`response_body` on exceptions) are
  returned to the caller, not logged, keeping error detail available for
  programmatic handling without writing it to shared log output.

---

## 7. Testing Strategy

Location: `tests/test_client.py`.

No new test dependency is needed — `requests.Response` objects are
constructed directly (already a transitive dependency), and
`HttpClient._session.request` is replaced with a `pytest` `monkeypatch`
fixture returning a prepared `Response`, or raising a prepared
`requests.exceptions.ConnectionError`/`Timeout` to exercise the failure
paths. A tiny local helper (e.g. `_make_response(status_code, json_body=None,
headers=None)`) builds these fixtures; it does not open a real socket.
Every test constructs `HttpClient` with a trivial stub `auth` object (e.g.
a no-op callable satisfying `requests.auth.AuthBase`) — since `auth` is
always injected (§1), no test needs real or fake credentials, environment
variables, or the authentication module at all.

Cases to cover:

- Each verb method (`get`/`post`/`put`/`patch`/`delete`) sends the expected
  method, URL, `params`, and `json` body to the underlying session.
- Constructing `HttpClient` without `base_url` or without `auth` raises
  `TypeError` (stdlib behavior of a required parameter — no custom
  validation code to test beyond confirming the parameter is required).
- `base_url` + `path` joining is correct regardless of leading/trailing
  slashes (2.3).
- Two `HttpClient` instances constructed with different `base_url` values
  send requests to their respective hosts independently, with no shared
  state between them (2.1, 2.2).
- Default vs. explicit `timeout`/`max_retries` are applied when
  constructing the client (4.1–4.2, 5.2–5.3); the supplied `auth` object is
  attached to every request unchanged (3.3).
- 2xx with JSON body → `HttpResponse.data` matches; 2xx with empty body →
  `data is None`; 2xx with invalid JSON body → `VeracodeApiError`.
- 401 → `VeracodeAuthenticationError`; 403 → `VeracodeAuthorizationError`;
  404 → `VeracodeNotFoundError`; 409 → `VeracodeConflictError`; 422 →
  `VeracodeValidationError` — each with correct `status_code`, `method`,
  `url`, `response_body`.
- An unmapped 4xx (e.g. 400) and a 5xx (after mocking the adapter/session
  to exhaust retries) → `VeracodeApiError` (the base class) with the same
  attributes.
- Each of the five specific exceptions above, and the `VeracodeApiError`
  fallback, are subclasses of `VeracodeApiError` (one `issubclass` check
  per class, covering 8.11).
- Simulated `requests.exceptions.ConnectionError` → `VeracodeConnectionError`.
- Simulated `requests.exceptions.Timeout` → `VeracodeTimeoutError`.
- `POST`/`PATCH` are not included in the mounted adapter's
  `allowed_methods` (inspect the adapter's `Retry` config directly, or
  assert on `HttpClient`'s constants) — covers 5.4 without needing to
  simulate a real multi-attempt retry sequence.
- `caplog` assertion: no captured log record's message contains a JSON
  body, header value, or `Authorization`/auth-header value used in the
  test, across a request/response/error cycle.

---

## 8. File Layout Introduced by This Feature

```
src/veracode_dast/
├── client.py       # HttpResponse, HttpClient (extends exceptions.py; does NOT import auth.py/config.py)
└── exceptions.py   # + VeracodeApiError, VeracodeConnectionError,
                     #   VeracodeTimeoutError, VeracodeAuthenticationError,
                     #   VeracodeAuthorizationError, VeracodeNotFoundError,
                     #   VeracodeConflictError, VeracodeValidationError

tests/
└── test_client.py

examples/
└── http_client_example.py   # GET against the DAST Target Configuration
                              # Service using
                              # HttpClient(base_url="https://api.veracode.com/dae/api/tcs-api/api/v1",
                              #            auth=get_veracode_auth())
                              # directly; prints the resulting HttpResponse.data.
                              # (This is the one place in this feature's
                              # deliverables that calls get_veracode_auth() —
                              # the example script is the "caller," not client.py.)
```

`services/` and `models/` remain untouched by this feature. `VeracodeClient`
is not added to `client.py` in this feature — it arrives with the first
Service.

---

## 9. Traceability

| Component | Requirements covered |
|---|---|
| `HttpClient.get/post/put/patch/delete` (no public `request()`) | 1.1–1.7 |
| `base_url` required constructor argument, no default | 2.1, 2.2, 2.3, 2.4, 2.5 |
| `auth` required constructor argument; no import of `auth.py`/`config.py` | 3.1, 3.2, 3.3, 3.4 |
| `timeout` handling | 4.1, 4.2, 4.3 |
| `Retry`-mounted adapter (§2.4) | 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7 |
| Request building (`json`, `params`, `headers`) | 6.1, 6.2, 6.3, 6.4 |
| Response parsing | 7.1, 7.2, 7.3, 7.4 |
| Error translation (§4), `_STATUS_EXCEPTIONS` lookup | 8.1–8.12 |
| Logging (§5) | 9.1, 9.2, 9.3, 9.4, 9.5, 9.6 |
| No resource/model/service/pagination code added | 10.1–10.5 |
| Sole `requests` importer | 10.6 |
| No hardcoded Veracode API base URL anywhere in this feature | 10.7 |
| Type hints + docstrings on all of the above | 11.1, 11.2, 11.3 |
| Test strategy (§7) | 12.1, 12.2, 12.3 |

---

## 10. Additional Architectural Recommendations (not implemented here)

These are improvements identified during this review that are worth
adopting, but are documentation/tooling changes for a maintainer to apply
separately — not part of this feature's implementation tasks.

1. **Mechanically enforce "only `client.py` imports `requests`" (requirement
   10.6).** Today this is a code-review convention. Ruff supports banning
   specific imports per path via `flake8-tidy-imports`'s banned-api rule.
   Adding to `pyproject.toml`:
   ```toml
   [tool.ruff.lint.flake8-tidy-imports.banned-api]
   "requests".msg = "Only src/veracode_dast/client.py may import requests."
   ```
   plus a per-file ignore for `client.py`, turns this architectural rule
   into a CI-enforced lint failure instead of something only a reviewer
   catches. Recommended as a follow-up change to `pyproject.toml`, not part
   of this feature.

2. **One `HttpClient`/`Session` per thread, documented, not enforced.**
   §2.3 accepts that a `Session` is not safe for concurrent use from
   multiple threads and defers this to caller discipline. If a future
   phase adds a concurrent use case (e.g. parallel polling across multiple
   targets), revisit whether `HttpClient` needs a documented "one instance
   per thread" note in its class docstring, or whether callers naturally
   already create one `VeracodeClient` per unit of work. No action needed
   for Phase 1.

3. **Connection pool sizing.** `HTTPAdapter`'s default `pool_maxsize` (10)
   is left untouched — Phase 1's call volume (single Target CRUD calls)
   never approaches it. If a future phase does highly concurrent or
   high-throughput polling against one `HttpClient`, revisit `pool_maxsize`
   then; tuning it now would be speculative.

4. **`VeracodeApiError` fallback observability.** Because many distinct
   4xx/5xx status codes collapse into the same `VeracodeApiError` (§2.1),
   a caller inspecting only the exception *type* can't distinguish, say, a
   500 from a 501. This is intentional (§2.1's rationale), but it means
   `status_code` — already a required, documented attribute (8.10) — is
   the only way to distinguish them. No design change needed; noted here
   so a future maintainer doesn't mistake the flat hierarchy for a gap.

---

## Amendment: Multipart Upload and Raw Binary Responses

Implements
[requirements.md Amendment](requirements.md#amendment-multipart-upload-and-raw-binary-responses),
discovered while designing API Specification Management. Two optional
parameters are added to the existing `HttpResponse`/`HttpClient` surface
(§2/§3 above) — no new class, no new verb, no change to any other
method's behavior.

```python
@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    data: dict[str, Any] | list[Any] | bytes | None   # was: dict | list | None
    headers: Mapping[str, str]


class HttpClient:
    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        raw: bool = False,
    ) -> HttpResponse: ...

    def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        files: Mapping[str, tuple[str, bytes, str]] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse: ...
```

`_request` gains matching `files`/`raw` parameters, threaded straight to
`self._session.request(..., files=files)`, and its 2xx-handling branch
becomes:

```python
if response.status_code >= 400:
    ...  # unchanged — §4 error translation applies identically

if raw:
    return HttpResponse(response.status_code, response.content or None, response.headers)

if not response.content:
    return HttpResponse(response.status_code, None, response.headers)
try:
    return HttpResponse(response.status_code, response.json(), response.headers)
except ValueError as exc:
    raise VeracodeApiError(..., status_code=response.status_code, response_body=response.text) from exc
```

When `files` is supplied, `json` is expected to be `None` (§ A.2 —
convention, not runtime-enforced); `requests` sets the
`multipart/form-data` `Content-Type` (with boundary) itself when `files` is
passed, so the client's default-header merge (§2.2 step 2) must not force
`Content-Type: application/json` in that case — it already doesn't, since
that header is only added by `requests` when `json=` is non-`None`.

**Why extend existing methods instead of adding `upload()`/`download()`
methods to `HttpClient`:** the five-verb surface (§2.2) maps to HTTP
semantics (GET/POST/PUT/PATCH/DELETE), not to resource-specific operations
— "upload" and "download" are resource-level concepts that belong to
`ApiSpecificationsService`, which already expresses them as
`upload()`/`download()` at the *service* layer. `HttpClient` only needed to
stop assuming every request/response body is JSON; `files`/`raw` say
exactly that, without teaching `HttpClient` anything about API
Specifications.

Logging (§5) is unaffected: the same DEBUG/ERROR statements fire regardless
of `files`/`raw`, and still never log body content — this was already true
for `json`, and now also covers `files`/binary `data`.

### Testing additions

`tests/test_client.py` gains: `post(..., files=...)` sends a
`multipart/form-data` request with the given field (assert via the stub
session's captured `files` kwarg, not by parsing wire bytes); `get(...,
raw=True)` on a 2xx response returns `HttpResponse.data` as the exact bytes
of a fixture `requests.Response.content`, with no `response.json()` call
attempted; `get(..., raw=True)` on an empty 2xx body returns `data=None`;
non-2xx behavior is identical with and without `raw=True`/`files=...`
(reuses the existing status-code test matrix, parametrized).
