# Tasks — HTTP Client

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Do not start implementation until this specification is reviewed and
approved.

---

- [ ] 1. Exception hierarchy additions (`exceptions.py`)
  - [ ] 1.1 Implement `VeracodeApiError(VeracodeSDKError)` with `method`,
        `url`, `status_code`, `response_body` attributes
  - [ ] 1.2 Implement `VeracodeConnectionError(VeracodeApiError)`
  - [ ] 1.3 Implement `VeracodeTimeoutError(VeracodeApiError)`
  - [ ] 1.4 Implement `VeracodeAuthenticationError(VeracodeApiError)` (401)
  - [ ] 1.5 Implement `VeracodeAuthorizationError(VeracodeApiError)` (403)
  - [ ] 1.6 Implement `VeracodeNotFoundError(VeracodeApiError)` (404)
  - [ ] 1.7 Implement `VeracodeConflictError(VeracodeApiError)` (409)
  - [ ] 1.8 Implement `VeracodeValidationError(VeracodeApiError)` (422)
  - [ ] 1.9 Do NOT implement `VeracodeClientError`/`VeracodeServerError` —
        any status code without a dedicated class above raises
        `VeracodeApiError` directly (see design.md §2.1)
  - [ ] 1.10 Add Google-style docstrings and full type hints
  - _Requirements: 8.1–8.6, 8.11, 11.1_

- [ ] 2. `HttpResponse` (`client.py`)
  - [ ] 2.1 Create `src/veracode_dast/client.py`
  - [ ] 2.2 Implement `HttpResponse` as a frozen dataclass (`status_code:
        int`, `data: dict | list | None`, `headers: Mapping[str, str]`)
  - _Requirements: 7.1, 7.2, 7.3, 11.1, 11.2_

- [ ] 3. `HttpClient` construction
  - [ ] 3.1 Define module constants: `DEFAULT_TIMEOUT`,
        `DEFAULT_MAX_RETRIES`, `_RETRY_STATUS_FORCELIST`,
        `_RETRIABLE_METHODS`, `_STATUS_EXCEPTIONS` (status code → exception
        class lookup, see design.md §4). Do NOT define a base-URL constant
        — no Veracode API base URL is hardcoded anywhere in this feature
  - [ ] 3.2 Implement `__init__(base_url, auth, timeout=DEFAULT_TIMEOUT,
        max_retries=DEFAULT_MAX_RETRIES)` with `base_url` **and** `auth`
        as required arguments (no default value for either)
  - [ ] 3.3 Confirm `client.py` does NOT import `get_veracode_auth`,
        `create_hmac_auth`, `load_credentials_from_env`,
        `VeracodeCredentials`, or any other symbol from `auth.py`/
        `config.py` — `auth` is only ever received, never created
  - [ ] 3.4 Build one `requests.Session`, mount an `HTTPAdapter` configured
        with a `urllib3` `Retry` (`total=max_retries`, `backoff_factor=0.5`,
        `status_forcelist=_RETRY_STATUS_FORCELIST`,
        `allowed_methods=_RETRIABLE_METHODS`,
        `respect_retry_after_header=True`) for both `http://` and `https://`
  - [ ] 3.5 Add Google-style docstrings and full type hints
  - _Requirements: 2.1, 2.2, 2.5, 3.1, 3.2, 3.4, 4.1, 4.2, 5.1, 5.2, 5.3,
    5.4, 5.5, 5.6, 10.7, 11.1, 11.2, 11.3_

- [ ] 4. Shared request implementation and verb methods
  - [ ] 4.1 Implement private `_request(method, path, *, json=None,
        params=None, headers=None) -> HttpResponse`
  - [ ] 4.2 Join `base_url` and `path` producing exactly one `/` between
        them regardless of surrounding slashes
  - [ ] 4.3 Merge caller `headers` over `{"Accept": "application/json"}`,
        caller values taking precedence on conflicts
  - [ ] 4.4 Send via `self._session.request(...)` with `auth`, `timeout`,
        `params`, `json`
  - [ ] 4.5 Implement `get`, `post`, `put`, `patch`, `delete` as thin
        wrappers around `_request`
  - [ ] 4.6 Confirm no public `request(method, path, ...)` method exists —
        `_request` stays private
  - [ ] 4.7 Add Google-style docstrings and full type hints
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.4, 3.3, 6.1, 6.2,
    6.3, 6.4, 11.1_

- [ ] 5. Response parsing and error translation
  - [ ] 5.1 Catch `requests.exceptions.Timeout` → raise
        `VeracodeTimeoutError`
  - [ ] 5.2 Catch `requests.exceptions.ConnectionError` → raise
        `VeracodeConnectionError`
  - [ ] 5.3 On status >= 400, look up `_STATUS_EXCEPTIONS.get(status_code,
        VeracodeApiError)` and raise it with `status_code`/`method`/`url`/
        `response_body` (JSON-parsed body, or raw text if not JSON)
  - [ ] 5.4 Confirm 401/403/404/409/422 map to `VeracodeAuthenticationError`
        /`VeracodeAuthorizationError`/`VeracodeNotFoundError`/
        `VeracodeConflictError`/`VeracodeValidationError` respectively, and
        every other 4xx/5xx maps to `VeracodeApiError`
  - [ ] 5.5 On 2xx with empty body → return `HttpResponse` with `data=None`
  - [ ] 5.6 On 2xx with JSON body → return `HttpResponse` with parsed
        `data`
  - [ ] 5.7 On 2xx with non-JSON body → raise `VeracodeApiError`
  - [ ] 5.8 Confirm no `requests`/`urllib3`/`json` exception can escape
        `_request` uncaught
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.1–8.10, 8.12_

- [ ] 6. Logging
  - [ ] 6.1 `DEBUG` log before sending: method + URL only
  - [ ] 6.2 `DEBUG` log after a 2xx response: method + URL + status code
  - [ ] 6.3 `ERROR` log immediately before each raise in task 5: method +
        URL + status code (if any) + exception class name
  - [ ] 6.4 Confirm no log statement includes `json`, `params`, the
        `Authorization` header, any other header value, or response body
        content
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 7. Unit tests (`tests/test_client.py`)
  - [ ] 7.1 Local helper to build `requests.Response` fixtures
        (`status_code`, optional JSON body, optional headers) without a
        real socket; local trivial stub `auth` object used by every test
  - [ ] 7.2 Each verb method sends the expected method/URL/params/json via
        a `monkeypatch`-replaced `HttpClient._session.request`
  - [ ] 7.3 Constructing `HttpClient` without `base_url` or without `auth`
        raises `TypeError`
  - [ ] 7.4 `base_url`/`path` joining with/without leading/trailing slashes
  - [ ] 7.5 Two `HttpClient` instances constructed with different
        `base_url` values send requests to their respective hosts
        independently (no shared state)
  - [ ] 7.6 Default vs. explicit `timeout`/`max_retries`; the supplied
        `auth` object is attached to every outgoing request unchanged
  - [ ] 7.7 2xx JSON body, 2xx empty body, 2xx invalid-JSON body
  - [ ] 7.8 401/403/404/409/422 → `VeracodeAuthenticationError`/
        `VeracodeAuthorizationError`/`VeracodeNotFoundError`/
        `VeracodeConflictError`/`VeracodeValidationError`, each with
        correct attributes
  - [ ] 7.9 An unmapped 4xx and a 5xx (after mocking retries exhausted) →
        `VeracodeApiError` with correct attributes
  - [ ] 7.10 Each specific exception class from 7.8, plus the
        `VeracodeApiError` fallback, is an instance of `VeracodeApiError`
  - [ ] 7.11 Simulated `ConnectionError` → `VeracodeConnectionError`
  - [ ] 7.12 Simulated `Timeout` → `VeracodeTimeoutError`
  - [ ] 7.13 `POST`/`PATCH` excluded from the mounted adapter's
        `allowed_methods`
  - [ ] 7.14 `caplog` assertion: no captured log record contains any body,
        header, `Authorization` value, or param value used in the test
  - _Requirements: 1.1–1.7, 2.1–2.5, 3.1–3.4, 4.1–4.3, 5.1–5.7, 6.1–6.4,
    7.1–7.4, 8.1–8.12, 9.1–9.6, 10.7, 12.1, 12.2, 12.3_

- [ ] 8. Example
  - [ ] 8.1 Add `examples/http_client_example.py`: calls
        `get_veracode_auth()` (reads credentials from the environment),
        constructs
        `HttpClient(base_url="https://api.veracode.com/dae/api/tcs-api/api/v1", auth=...)`,
        performs one `GET`, prints `HttpResponse.data`
  - _AGENTS.md Definition of Done_

- [ ] 9. Quality gates
  - [ ] 9.1 `ruff check` passes with no new warnings
  - [ ] 9.2 `mypy` passes in strict mode for `client.py` and the extended
        `exceptions.py`
  - [ ] 9.3 `pytest` passes for `test_client.py`
  - _AGENTS.md Definition of Done_

- [ ] 10. Amendment: multipart upload and raw binary responses (see
      [design.md Amendment](design.md#amendment-multipart-upload-and-raw-binary-responses))
  - [ ] 10.1 Widen `HttpResponse.data` to `dict[str, Any] | list[Any] |
        bytes | None`
  - [ ] 10.2 Add `files: Mapping[str, tuple[str, bytes, str]] | None =
        None` to `post()`, threaded through `_request`
  - [ ] 10.3 Add `raw: bool = False` to `get()`, threaded through
        `_request`
  - [ ] 10.4 On 2xx with `raw=True`: return `response.content or None` as
        `data`, skipping `response.json()`
  - [ ] 10.5 Confirm non-2xx error translation (task 5) is unaffected by
        `files`/`raw`
  - [ ] 10.6 Add the test cases in design.md's "Testing additions"
  - _Requirements: Amendment A.1–A.6_

---

## Explicitly not part of these tasks

Per [requirements.md §10](requirements.md#10-boundaries-non-goals-for-this-feature):
no Target/Target Configuration/Analysis Profile/Scanner/Analysis/Report
logic, no model classes, no `VeracodeClient`, no service wiring, no
pagination helpers, and no code that creates or resolves an auth provider
(`get_veracode_auth()` is only ever *called* by the example script and,
later, by service/`VeracodeClient` wiring — never by `client.py` itself).

The following were identified as valuable but are explicitly deferred to a
follow-up change rather than this feature's tasks (see [design.md
§10](design.md#10-additional-architectural-recommendations-not-implemented-here)):
a Ruff banned-api rule enforcing "only `client.py` imports `requests`",
and any documentation/tuning around thread-safety or connection-pool
sizing beyond what §2.3–2.4 already describe.
