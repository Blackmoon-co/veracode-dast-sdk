# Tasks — Authentication Infrastructure

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Do not start implementation until this specification is reviewed and
approved.

---

- [ ] 1. Exception hierarchy
  - [ ] 1.1 Create `src/veracode_dast/exceptions.py`
  - [ ] 1.2 Implement `VeracodeSDKError(Exception)`
  - [ ] 1.3 Implement `VeracodeAuthError(VeracodeSDKError)`
  - [ ] 1.4 Implement `MissingCredentialsError(VeracodeAuthError)`, accepting
        a list of missing variable names and building a message that names
        them without ever including a value
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 2. Credential loading (`config.py`)
  - [ ] 2.1 Create `src/veracode_dast/config.py`
  - [ ] 2.2 Implement `VeracodeCredentials` as a frozen dataclass
        (`api_key_id: str`, `api_key_secret: str`)
  - [ ] 2.3 Implement `load_credentials_from_env()`: read both env vars,
        treat unset or empty-string as missing, raise
        `MissingCredentialsError` listing every missing variable
  - [ ] 2.4 Add a DEBUG log statement on success with no credential values
  - [ ] 2.5 Add Google-style docstrings and full type hints
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 5.1, 5.4, 7.2_

- [ ] 3. HMAC auth provider creation (`auth.py`)
  - [ ] 3.1 Create `src/veracode_dast/auth.py`
  - [ ] 3.2 Implement `create_hmac_auth(credentials)` using
        `RequestsAuthPluginVeracodeHMAC` from
        `veracode_api_signing.plugin_requests`
  - [ ] 3.3 Implement `get_veracode_auth()` combining
        `load_credentials_from_env()` + `create_hmac_auth()`
  - [ ] 3.4 Add a DEBUG log statement on successful provider creation with
        no credential values
  - [ ] 3.5 Add Google-style docstrings and full type hints
  - [ ] 3.6 Confirm neither `create_hmac_auth` nor `get_veracode_auth`
        accepts, stores, or references a base URL, endpoint, or any
        Veracode-service-specific configuration
  - [ ] 3.7 Confirm `auth.py` and `config.py` import only `os`,
        `dataclasses`, `logging` (stdlib) and
        `RequestsAuthPluginVeracodeHMAC` from
        `veracode_api_signing.plugin_requests` — no `import requests`
        anywhere in this feature
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 5.1, 5.4, 6.6, 6.7, 7.1, 7.2, 7.4_

- [ ] 4. Unit tests
  - [ ] 4.1 `tests/test_config.py`: valid env vars; missing id; missing
        secret; both missing; empty-string treated as missing
  - [ ] 4.2 `tests/test_auth.py`: `create_hmac_auth` returns a correctly
        populated `RequestsAuthPluginVeracodeHMAC`; `get_veracode_auth()`
        succeeds end-to-end with `monkeypatch`-set env vars and propagates
        `MissingCredentialsError` when they're absent
  - [ ] 4.3 Add a `caplog`-based assertion that no test's fake credential
        values appear in captured log output
  - _Requirements: 2.1–2.4, 3.1, 5.1, 5.3, 8.1, 8.2, 8.3_

- [ ] 5. Example
  - [ ] 5.1 Add `examples/auth_example.py`: reads env vars (documented at
        the top of the file), calls `get_veracode_auth()`, and prints a
        success confirmation — never prints the credential values
  - _Requirements: 5.1, 5.3; AGENTS.md Definition of Done_

- [ ] 6. Quality gates
  - [ ] 6.1 `ruff check` passes with no new warnings
  - [ ] 6.2 `mypy` passes in strict mode for `config.py`, `auth.py`,
        `exceptions.py`
  - [ ] 6.3 `pytest` passes for `test_config.py` and `test_auth.py`
  - _AGENTS.md Definition of Done_

---

## Explicitly not part of these tasks

Per [requirements.md §6](requirements.md#6-boundaries-non-goals-for-this-feature):
no HTTP client, no `VeracodeClient`, no services, no models, no other
authentication mechanism, no CLI, no Azure DevOps code, no base
URL/endpoint/service-specific configuration of any kind (that ownership
belongs to the HTTP Client feature and the services built on top of it),
and no `import requests` anywhere in this feature — this module is only a
thin wrapper around `veracode-api-signing`.
