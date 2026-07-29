# Tasks — Authentications

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Depends on `TARGET_CONFIGURATION_SERVICE_BASE_URL` from
`services/targets.py`, the shared `HttpClient`, and — per requirements.md
§9 — `utils/sdk_config.py` (`load_json_config`, `suggest_closest`) and
`models/common.InheritedValue[T]`. If Scanner Profiles and/or Analysis
Profiles have already been implemented when this feature starts, tasks 4
and 1's `InheritedValue[T]` sub-step are already done — verify the files
exist with the shapes in
[scanners-profiles design §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared)
and
[analysis-profile requirements §4.5](../analysis-profile/requirements.md#4-typed-models-and-enumerations)
and import them unchanged instead of redoing this work.

---

- [ ] 1. Create shared `InheritedValue[T]` model
  - **Description:** If `src/veracode_dast/models/common.py` does not yet
    exist, create it with a generic frozen dataclass `InheritedValue[T]`
    (`effective_value: T`, `is_inherited: bool`), per design.md §3.1. If it
    already exists (Analysis Profiles implemented first), skip this task
    and import it unchanged.
  - **Acceptance Criteria:**
    - `InheritedValue(effective_value="x", is_inherited=False)` constructs
      and is usable as `InheritedValue[SomeType]`.
    - Full type hints and Google-style docstrings.
  - _Requirements: §4.8, §9.2_

- [ ] 2. Create Authentication enums and response models
  - **Description:** Add `src/veracode_dast/models/authentication.py` with
    `AuthenticationType`, `ScriptType`, `OAuth2GrantType`,
    `ParameterAuthenticationType` (all `StrEnum`, values per requirements.md
    §4.1–§4.4), and the response-side models — `Script`,
    `SystemAuthentication`, `ApplicationAuthentication`,
    `CertificateAuthentication`, `ScriptAuthentication`, `SRMAuthentication`,
    `OAuth2Authentication`, `ParameterAuthentication` — each a frozen
    dataclass with a `from_api` classmethod, field names matching
    requirements.md §0.2 verbatim, and `field(repr=False)` on every
    sensitive field (`password`, `client_secret`, `base64_pkcs12`, `value`,
    `script_body` — requirements.md §3.6.1–§3.6.2).
  - **Acceptance Criteria:**
    - `SystemAuthentication.from_api({"username": "john.doe", "password": "x"})`
      returns `SystemAuthentication(username="john.doe", password="x")`,
      and `repr(...)` does not contain `"x"`.
    - `ApplicationAuthentication` includes `enable_ai_login` (response-only,
      requirements.md §3.4.3) alongside `username`/`password`/`login_url`.
    - `ScriptAuthentication.from_api` builds `login_script`/`logout_script`
      via `Script.from_api`, handling either being absent/null.
    - `OAuth2Authentication.from_api` maps all eleven fields from
      requirements.md §0.2, with `client_secret`/`password` excluded from
      `repr()`.
    - `ParameterAuthentication.from_api` maps `id`/`title`/`type`/`key`/
      `value`, with `value` excluded from `repr()`.
    - Full type hints and Google-style docstrings.
  - _Requirements: §4.1–§4.6, §0.2, §3.6_

- [ ] 3. Create the `AuthenticationConfiguration` aggregate and `Authentication` alias
  - **Description:** In the same file as task 2, add
    `AuthenticationConfiguration` (seven fields, each
    `InheritedValue[X] | None`, matching requirements.md §0.4's
    `EffectiveAuthentications` field-for-field) with a `from_api`
    classmethod, and the module-level type alias `Authentication` (union of
    the seven response types — requirements.md §4.9).
  - **Acceptance Criteria:**
    - `AuthenticationConfiguration.from_api(data)` returns `None` for any
      of the seven fields whose API value is `null`, and an
      `InheritedValue[...]` (with `effective_value` built via that
      mechanism's `from_api`) otherwise.
    - `AuthenticationConfiguration()` constructs with all seven fields
      defaulting to `None`.
    - Full type hints and Google-style docstrings.
  - _Requirements: §4.9, §0.4, §3.1_

- [ ] 4. Create SDK Configuration Loader (reuse or create)
  - **Description:** If `src/veracode_dast/utils/sdk_config.py` does not
    yet exist (Scanner Profiles not yet implemented), create it exactly
    per
    [scanners-profiles design §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared)
    (`load_json_config`, `suggest_closest`, plus
    `ConfigFileNotFoundError`/`ConfigFileInvalidError` in `exceptions.py`).
    If it already exists, this task is a no-op — import it unchanged.
  - **Acceptance Criteria:**
    - `load_json_config()` accepts a `dict` (passthrough), a valid JSON
      file path (parsed), a missing path (`ConfigFileNotFoundError`), or a
      malformed-JSON file (`ConfigFileInvalidError`).
    - No Authentication-specific logic added to this module — it stays
      resource-agnostic (design.md §3.4).
  - _Requirements: §9.1_

- [ ] 5. Create Authentication exceptions
  - **Description:** Add `AuthenticationValidationError(VeracodeSDKError)`
    (message + `rule` kwarg) and
    `UnknownAuthenticationTypeError(VeracodeSDKError)` (`type_name` +
    `suggestion` kwargs, formatted message with an optional "Did you
    mean" line) to `src/veracode_dast/exceptions.py`, per design.md §3.3.
  - **Acceptance Criteria:**
    - Both subclass `VeracodeSDKError` directly (not `VeracodeApiError`).
    - `UnknownAuthenticationTypeError("aouth2", suggestion="oauth2")`'s
      message contains `Unknown authentication type 'aouth2'.` and
      `Did you mean 'oauth2'?`.
    - Full type hints and Google-style docstrings.
  - _Requirements: §6.1–§6.2_

- [ ] 6. Implement GET Authentication Configuration
  - **Description:** Add `AuthenticationsService` in
    `src/veracode_dast/services/authentications.py`, importing
    `TARGET_CONFIGURATION_SERVICE_BASE_URL` from `services/targets.py` (not
    redefining it). Implement `__init__(self, http_client: HttpClient)` and
    `get(self, analysis_profile_id: str) -> AuthenticationConfiguration`.
  - **Acceptance Criteria:**
    - Blank/whitespace-only `analysis_profile_id` raises
      `AuthenticationValidationError(rule="analysis_profile_id_required")`
      before any HTTP call.
    - Calls `GET /analysis_profiles/{analysis_profile_id}/authentications`
      and returns `AuthenticationConfiguration.from_api(response.data)` on
      200.
    - A 404 response propagates as `VeracodeNotFoundError`, unchanged.
    - An INFO log line names only `analysis_profile_id` — no field values.
    - Full type hints and Google-style docstrings.
  - _Requirements: §3.2_

- [ ] 7. Create per-mechanism SDK Configuration models
  - **Description:** In `models/authentication.py`, add the seven
    SDK-Configuration-side dataclasses — `BasicAuthenticationConfig`,
    `ApplicationAuthenticationConfig`, `CertificateAuthenticationConfig`,
    `ScriptAuthenticationConfig` (+ `ScriptConfig`),
    `SRMAuthenticationConfig`, `OAuth2AuthenticationConfig`,
    `ParameterAuthenticationConfig` (+ `ParameterAuthenticationEntry`) —
    each with a `to_api()` producing exactly its `*UpdateRequest` (or bare
    array) shape, field names matching requirements.md §0.3 verbatim
    (design.md §3.2).
  - **Acceptance Criteria:**
    - `BasicAuthenticationConfig(username="admin", password="secret123").to_api()`
      returns `{"username": "admin", "password": "secret123"}` — the exact
      README `"basic"` example.
    - `OAuth2AuthenticationConfig(grant_type=OAuth2GrantType.CLIENT_CREDENTIALS,
      access_token_url=..., client_id=..., client_secret=...).to_api()`
      omits every unset field (no explicit `null`s).
    - `ParameterAuthenticationConfig(parameters=[...]).to_api()` returns a
      **list**, not a dict.
    - Full type hints and Google-style docstrings.
  - _Requirements: §4.7, §0.3, design.md §7_

- [ ] 8. Implement Configuration Validator (per-mechanism dispatch)
  - **Description:** In `AuthenticationsService`, add
    `_validate_and_transform(config: dict[str, Any]) -> tuple[AuthenticationType,
    dict[str, Any] | list[Any]]`: validates `config["authentication"]` is a
    dict with a string `type`; resolves `type` against the seven
    `AuthenticationType` members (else `UnknownAuthenticationTypeError` via
    `suggest_closest`); dispatches via `match auth_type:` to one
    `_<mechanism>_config` static helper per mechanism, each performing
    exactly the presence/type/enum-membership checks in requirements.md
    §5.6–§5.12 and returning that mechanism's `*Config` object; calls
    `.to_api()` on the result (design.md §6).
  - **Acceptance Criteria:**
    - Missing/non-dict `"authentication"` →
      `AuthenticationValidationError(rule="authentication_key_required")`.
    - Missing/non-string `"type"` →
      `AuthenticationValidationError(rule="type_required")`.
    - `"type": "aouth2"` → `UnknownAuthenticationTypeError` with
      `suggestion == "oauth2"`.
    - Each mechanism's missing-required-field case raises exactly the
      `rule=` value listed in requirements.md §5.6–§5.12 (e.g.
      `basic_username_required`, `application_login_url_required`,
      `certificate_base64_pkcs12_required`,
      `script_requires_login_or_logout`, `srm_script_body_required`,
      `oauth2_grant_type_required`/`oauth2_grant_type_invalid`,
      `parameter_parameters_required`/`parameter_entry_invalid`).
    - No length/format/pattern/cross-field business-rule validation is
      added beyond what requirements.md §5.6–§5.12 specify (§5.13).
    - An empty `{"parameters": []}` for `type: "parameter"` returns
      `(AuthenticationType.PARAMETER, [])` without error.
    - Full type hints and Google-style docstrings.
  - _Requirements: §5.1–§5.13_

- [ ] 9. Implement Configuration Transformer (per-mechanism request shaping)
  - **Description:** Confirmed by task 7's `to_api()` implementations and
    task 8's dispatch — no separate `Transformer` class or method (design.md
    §7); this task is the acceptance gate that the two compose correctly
    for all seven mechanisms end-to-end (config dict in, exact API request
    body out) before wiring the HTTP call in task 10.
  - **Acceptance Criteria:**
    - For each of the seven mechanisms, feeding a representative SDK
      Configuration through `_validate_and_transform()` produces the exact
      request body shown in design.md §7 (or an equivalent per-mechanism
      example for certificate/script/srm/application, since only basic and
      oauth2 have a README-literal worked example).
  - _Requirements: design.md §7_

- [ ] 10. Implement PUT Authentication (dispatch + HTTP call)
  - **Description:** Complete `AuthenticationsService.update(self,
    analysis_profile_id: str, config_file: str | Path | dict[str, Any]) ->
    Authentication`: blank-ID guard → `load_json_config` →
    `_validate_and_transform` → look up the endpoint path in
    `_MECHANISM_PATHS` and whether to send `?method=PATCH` from
    `_SUPPORTS_PATCH` (every mechanism except `PARAMETER` — requirements.md
    §0.1, §3.4.1, §3.5.1) → `PUT` → build the typed response via a second
    `match auth_type:` dispatch (`_build_response`) → INFO log
    (`analysis_profile_id` + `type` only, never field values).
  - **Acceptance Criteria:**
    - Reproduces the flow in
      [README "Update Authentication"](README.md#update-authentication).
    - `type: "parameter"` sends **no** `method` query parameter; every
      other type always sends `method=PATCH`.
    - Returns the server's post-update typed model — `SystemAuthentication`
      for `"basic"`, `OAuth2Authentication` for `"oauth2"`,
      `list[ParameterAuthentication]` for `"parameter"`, etc. — never a
      locally reconstructed value.
    - A 404 response propagates as `VeracodeNotFoundError`, unchanged.
    - `VeracodeClient` wiring: construct `AuthenticationsService` with the
      **same** `HttpClient` instance already assigned to `self.targets`
      (`client.py`), and assign to `self.authentications`.
    - Full type hints and Google-style docstrings.
  - _Requirements: §3.3–§3.5_

- [ ] 11. Unit Tests
  - **Description:** Add `tests/models/test_authentication.py` and
    `tests/services/test_authentications.py` using the stub-`HttpClient`
    approach already used by every prior feature — no mocking library, no
    real sockets.
  - **Acceptance Criteria:** Full case list in design.md §10 is covered,
    including: `from_api` for all seven response models plus
    `AuthenticationConfiguration.from_api` (mixed None/populated fields);
    `get()`/`update()` blank-ID guards; every `_validate_and_transform`
    failure mode across all seven mechanisms; the exact README `"basic"`/
    `"oauth2"` (corrected) request-body reproductions; the `"parameter"`
    no-`method`-param and empty-list cases; 404 propagation; a `caplog`
    assertion that no log record contains any sensitive field's value; a
    `repr()`/`str()` assertion that no sensitive field's value appears on
    any populated response model.
  - _Requirements: design.md §10_

- [ ] 12. Integration Tests
  - **Description:** Add an integration-style test (or extend an existing
    end-to-end example under `examples/`) exercising
    `client.authentications.update()` → `client.authentications.get()`
    against a real or recorded Veracode API response, for at least the
    `"basic"` and one other mechanism, confirming the round trip: a
    mechanism configured via `update()` is reflected as non-`None` in the
    next `get()`'s corresponding `AuthenticationConfiguration` field.
  - **Acceptance Criteria:**
    - Confirms the real API's `EffectiveAuthentications`/per-mechanism
      response shapes match what `from_api` expects (guards against drift
      from requirements.md §0.2/§0.4 if Veracode's schema changes).
    - Confirms a 404 for an unknown `analysis_profile_id` is a real,
      observed API behavior on both `get()` and `update()`.
  - _Requirements: §0.5, §11 (Acceptance Criteria)_

- [ ] 13. Documentation
  - **Description:** Add `examples/authentications_example.py` (argparse:
    `--analysis-profile-id`, `--config-file`) demonstrating `get()` then
    `update()`, printing only non-sensitive fields. Add sample
    `specs/authentications/authentication.json` fixture(s) mirroring
    README's `"basic"`/`"oauth2"` examples (with `"oauth2"` corrected per
    requirements.md §3.1). Cross-check [README.md](README.md) still matches
    the shipped public API exactly (method names, argument names, exception
    list) — do not modify README.md itself; if a mismatch is found, the
    code changes, not the README.
  - **Acceptance Criteria:**
    - The example script runs end-to-end against a real or stubbed client
      and never prints a sensitive field's value.
    - `ruff check`, `mypy --strict`, and `pytest` all pass.
  - _AGENTS.md Definition of Done_

---

## Dependency order

1 (shared `InheritedValue[T]`, or verify reuse) has no dependency within
this feature. 2–3 (models) depend on 1 (for `AuthenticationConfiguration`)
and must precede 6, 8, 10. 4 (`utils/sdk_config.py`, or verify reuse) can
be built in parallel with 1–3. 5 (exceptions) can be built in parallel with
1–4. 6 (GET) depends on 2–3. 7 (config models) depends on 2 (shares enums)
and can be built in parallel with 6. 8 (validator dispatch) depends on 4,
5, 7. 9 is an acceptance gate over 7–8, not new code. 10 (PUT) depends on
6's service scaffold plus 8–9, and on `client.py` wiring. 11 depends on
1–10. 12 depends on 10 and a reachable Veracode API/recording. 13 depends
on 10 (example) and the whole feature being otherwise complete (README
cross-check).

## Explicitly not part of these tasks

Per [requirements.md §12](requirements.md#12-out-of-scope): no `delete`/
`remove` operation or any way to trigger the API's full-replace `204`
"removed" outcome; no Scanner Variables or ISM Gateway integration; no
combined `dast-config.json`; no replication of Veracode server-side
business rules (OAuth2 grant-type-specific requirements, SRM's
JavaScript-only note, any length/format/pattern constraint already in the
OpenAPI); no retry/caching/pagination beyond the HTTP Client; no
modification of `services/targets.py`, `services/api_specifications.py`,
`services/teams.py`, or `services/scanners.py`.
