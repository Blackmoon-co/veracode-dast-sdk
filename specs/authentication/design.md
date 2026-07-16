# Design — Authentication Infrastructure

Implements the requirements in [requirements.md](requirements.md), within
the architecture and conventions defined in [AGENTS.md](../../AGENTS.md).

---

## 1. Overview

This feature builds the bottom two layers of the SDK's layered architecture
that concern credentials and authentication:

```
VeracodeClient          ← NOT built in this feature
      ↓
  HTTP Client            ← NOT built in this feature
      ↓
   Services              ← NOT built in this feature
      ↓
    Models               ← NOT built in this feature
      ↓
  REST API

  ┌─────────────────────────────────────────┐
  │  This feature:                           │
  │  config.py  → auth.py  → exceptions.py   │
  └─────────────────────────────────────────┘
```

`config.py` and `auth.py` produce a single artifact — a `requests`-compatible
auth object — that a future HTTP Client feature will attach to every
outgoing request. This feature performs no I/O beyond reading process
environment variables.

**Import boundary.** This feature is only a thin wrapper around the
official `veracode-api-signing` library. Its imports are limited to:
`os` (reading environment variables), `dataclasses` and `logging` (stdlib),
and `RequestsAuthPluginVeracodeHMAC` from
`veracode_api_signing.plugin_requests`. Neither `config.py` nor `auth.py`
imports `requests`, executes an HTTP request, or references any REST
endpoint — the auth object it returns is merely *compatible* with
`requests`'s `auth=` parameter by virtue of the `veracode-api-signing`
contract, not because this feature depends on `requests`.

**Naming note:** the package name is `veracode_dast` (no `sdk` suffix), per
[AGENTS.md](../../AGENTS.md#4-project-structure) and `pyproject.toml`. The
`specs/authentication/README.md` usage example — `from veracode_dast import
VeracodeClient` — matches this design.

**Base-URL-agnostic note:** Veracode exposes multiple REST APIs under
different base URLs that all share this same HMAC mechanism — for example
the AppSec API (`https://api.veracode.com/appsec`) and the DAST Target
Configuration Service (`https://api.veracode.com/dae/api/tcs-api/api/v1`) —
and future DAST services may add more (see
[AGENTS.md §3.1](../../AGENTS.md#31-authentication-is-base-url-agnostic)).
Neither `config.py` nor `auth.py` accepts, stores, or references a base
URL or endpoint anywhere in this design. The auth provider returned by
`get_veracode_auth()` is a plain, reusable object; which Veracode API base
URL it gets attached to is decided entirely by the (later) HTTP Client
feature and the services that configure it.

---

## 2. Components and Interfaces

### 2.1 `src/veracode_dast/exceptions.py`

```python
class VeracodeSDKError(Exception):
    """Root exception for all errors raised by veracode-dast."""


class VeracodeAuthError(VeracodeSDKError):
    """Raised for authentication-related failures."""


class MissingCredentialsError(VeracodeAuthError):
    """Raised when one or more required credential environment variables
    are missing or empty.

    Args:
        missing_variables: Names of the environment variables that are
            missing or empty. Never contains credential values.
    """

    def __init__(self, missing_variables: list[str]) -> None: ...
```

No other exception types are introduced by this feature (e.g. no
`VeracodeApiError` — that belongs to the future HTTP Client feature).

### 2.2 `src/veracode_dast/config.py`

```python
@dataclass(frozen=True)
class VeracodeCredentials:
    """Veracode HMAC API credentials.

    Attributes:
        api_key_id: Veracode API key ID.
        api_key_secret: Veracode API key secret.
    """

    api_key_id: str
    api_key_secret: str


def load_credentials_from_env() -> VeracodeCredentials:
    """Read and validate Veracode HMAC credentials from environment
    variables.

    Reads ``VERACODE_API_KEY_ID`` and ``VERACODE_API_KEY_SECRET``.

    Returns:
        A populated ``VeracodeCredentials`` instance.

    Raises:
        MissingCredentialsError: If either variable is unset or empty.
    """
    ...
```

`VeracodeCredentials` is frozen (immutable) — it's a plain data holder, not
a place to add validation/behavior later; validation stays in
`load_credentials_from_env`. `config.py`'s only imports are `os`
(stdlib) and `dataclasses` (stdlib) — it never imports `requests` or
`veracode_api_signing`.

### 2.3 `src/veracode_dast/auth.py`

```python
def create_hmac_auth(
    credentials: VeracodeCredentials,
) -> RequestsAuthPluginVeracodeHMAC:
    """Create the official Veracode HMAC auth provider for ``requests``.

    Args:
        credentials: Validated Veracode API credentials.

    Returns:
        A ``RequestsAuthPluginVeracodeHMAC`` instance ready to be passed as
        the ``auth=`` argument of a ``requests`` call.
    """
    ...


def get_veracode_auth() -> RequestsAuthPluginVeracodeHMAC:
    """Load credentials from the environment and create the Veracode HMAC
    auth provider in one call.

    This is the single entry point future SDK components (HTTP client,
    services) should use to obtain authentication — they should not call
    ``load_credentials_from_env`` / `create_hmac_auth`` separately unless
    they need the intermediate credentials object.

    Returns:
        A ready-to-use ``RequestsAuthPluginVeracodeHMAC`` instance.

    Raises:
        MissingCredentialsError: If required environment variables are
            missing or empty.
    """
    ...
```

`get_veracode_auth()` is the function the future HTTP Client feature is
expected to call; `create_hmac_auth` / `load_credentials_from_env` stay
exported for direct use in tests and by callers that already hold a
`VeracodeCredentials` instance. `auth.py`'s only non-stdlib import is
`RequestsAuthPluginVeracodeHMAC` from
`veracode_api_signing.plugin_requests` — it never imports `requests`
directly, and never constructs or sends an HTTP request itself.

---

## 3. Data Model

| Field            | Type  | Notes                                   |
|------------------|-------|------------------------------------------|
| `api_key_id`     | `str` | From `VERACODE_API_KEY_ID`. Never empty. |
| `api_key_secret` | `str` | From `VERACODE_API_KEY_SECRET`. Never empty. |

`VeracodeCredentials` has no methods beyond what `@dataclass(frozen=True)`
generates. It is not serialized, logged, or printed (its default `repr`
would include secret values — this feature's tests must confirm nothing
in the codepath calls `repr()`/`str()` on it in a log statement).

---

## 4. Error Handling

| Condition | Exception | Message content |
|---|---|---|
| `VERACODE_API_KEY_ID` missing/empty, secret present | `MissingCredentialsError` | Names `VERACODE_API_KEY_ID` only |
| `VERACODE_API_KEY_SECRET` missing/empty, id present | `MissingCredentialsError` | Names `VERACODE_API_KEY_SECRET` only |
| Both missing/empty | `MissingCredentialsError` | Names both variables |

No other failure modes exist in this feature — there is no network call
that can time out or return an HTTP error.

---

## 5. Logging

- Each module gets its logger via `logging.getLogger(__name__)` — no
  custom logger/formatter setup (that belongs to `utils/`, out of scope
  here; standard library `logging` defaults are sufficient for Phase 1).
- Log statements in this feature, both at `DEBUG` level:
  - `config.py`: on successful load — `"Veracode credentials loaded from environment"`.
  - `auth.py`: on successful provider creation — `"Veracode HMAC authentication provider created"`.
- No `INFO`/`WARNING`/`ERROR` logging is added by this feature; the
  `MissingCredentialsError` exception itself communicates the failure to
  the caller.
- No credential value, or object whose `repr()` includes one, is ever
  passed to a logging call.

---

## 6. Security Considerations

- Credentials exist only as local variables / a `VeracodeCredentials`
  instance passed by return value — never assigned to module-level state.
- Nothing in this feature writes to disk, environment (beyond reading),
  or any cache.
- Exception messages are restricted to variable *names*, never values
  (see [Error Handling](#4-error-handling)).

---

## 7. Testing Strategy

Location: `tests/test_config.py`, `tests/test_auth.py`.

No new test dependency is needed — `pytest`'s built-in `monkeypatch`
fixture covers environment variable manipulation, and this feature makes
no network calls to mock.

`test_config.py`:
- Both variables set and non-empty → returns `VeracodeCredentials` with
  matching values.
- `VERACODE_API_KEY_ID` missing → `MissingCredentialsError` naming only
  that variable.
- `VERACODE_API_KEY_SECRET` missing → `MissingCredentialsError` naming
  only that variable.
- Both missing → `MissingCredentialsError` naming both.
- Either variable set to `""` → treated as missing (same as unset).

`test_auth.py`:
- `create_hmac_auth` with a `VeracodeCredentials` instance returns a
  `RequestsAuthPluginVeracodeHMAC` whose `api_key_id` / `api_key_secret`
  attributes match the input (inspecting the real object from
  `veracode-api-signing`, not a mock).
- `get_veracode_auth()` with valid env vars set (via `monkeypatch`) returns
  a working provider end-to-end.
- `get_veracode_auth()` with missing env vars propagates
  `MissingCredentialsError`.

Log assertions (either in these files or a shared test):
- Capturing log output (`caplog`) during a successful `get_veracode_auth()`
  call contains no substring equal to the test's fake credential values.

---

## 8. File Layout Introduced by This Feature

```
src/veracode_dast/
├── config.py       # VeracodeCredentials, load_credentials_from_env
├── auth.py         # create_hmac_auth, get_veracode_auth
└── exceptions.py   # VeracodeSDKError, VeracodeAuthError, MissingCredentialsError

tests/
├── test_config.py
└── test_auth.py

examples/
└── auth_example.py   # Prints confirmation that a provider was created;
                       # never prints the credentials themselves.
```

`services/` and `models/` are untouched by this feature.

---

## 9. Traceability

| Component | Requirements covered |
|---|---|
| `exceptions.py` | 4.1, 4.2, 4.3, 4.4, 5.3 |
| `config.py` | 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 5.4, 8.1 |
| `auth.py` | 3.1, 3.2, 3.3, 3.4, 5.4, 7.1, 7.4, 8.2 |
| Logging (§5) | 5.1, 5.4 |
| No HTTP/services/CLI/other-auth code added | 6.1–6.5 |
| No base URL / endpoint / service config anywhere in this feature | 6.6 |
| No `requests` import; import boundary limited to `os`/`dataclasses`/`logging`/`veracode_api_signing.plugin_requests` | 3.4, 6.7 |
| Type hints + docstrings on all of the above | 7.2 |
| No new dependency beyond `veracode-api-signing`, stdlib, `pytest` | 7.3, 8.3 |
