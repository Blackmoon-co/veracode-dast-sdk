# Tasks — Scanner Variables

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Do not start implementation until this specification is reviewed and
approved.

Depends on `TARGET_CONFIGURATION_SERVICE_BASE_URL` from
`services/targets.py` and on `utils/sdk_config.py`
(`load_json_config`, `ConfigFileNotFoundError`, `ConfigFileInvalidError`)
from [specs/scanners-profiles](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared).
If Scanner Profiles has not been implemented yet, task 0 below creates
`utils/sdk_config.py` first, exactly as that spec defines it — this
feature does not fork a second copy.

---

## 0. Prerequisite (only if not already present)

- [ ] 0.1 Check whether `src/veracode_dast/utils/sdk_config.py` already
      exists with `load_json_config(source: str | Path | dict[str, Any])
      -> dict[str, Any]`. If it does not, create it exactly as
      [specs/scanners-profiles design.md §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared)
      specifies, plus `ConfigFileNotFoundError`/`ConfigFileInvalidError` in
      `exceptions.py`. Do NOT add `suggest_closest()` as part of this task
      if it doesn't already exist — this feature does not need it
      (_Requirements: 9.5, 9.6_) and adding it here would be scope creep
      belonging to whichever feature needs it first.
  - _Requirements: 9.5_

---

## 1. Models

- [ ] 1.1 Create `src/veracode_dast/models/scanner_variable.py` with the
      `ScannerVariable` frozen dataclass: `reference_key: str`, `value:
      str`, `totp_seed: bool = False`, `is_inherited: bool = False`, `id:
      str | None = None`
  - _Requirements: 4.1_

- [ ] 1.2 Implement `ScannerVariable.from_api(data: dict) ->
      ScannerVariable`, reading `data["effective_value"]["reference_key"]`,
      `["value"]`, mapping `["evaluation_mode"] == "TOTP"` to `totp_seed`,
      reading `data["is_inherited"]`, and `data["effective_value"].get("id")`
  - _Requirements: 3.2.3, 3.1.2, 3.1.3_

- [ ] 1.3 Implement `ScannerVariable.to_api() -> dict`, emitting exactly
      `reference_key`, `value`, `evaluation_mode` (`"TOTP"` if `totp_seed`
      else `"RAW"`) — confirm `id` and `utilize_in_ai_assisted_login` are
      never present in the output regardless of the instance's `id` value
  - _Requirements: 7.1, 3.1.3, 3.1.4_

- [ ] 1.4 In the same file, implement `ScannerVariables` as a frozen
      dataclass: `variables: list[ScannerVariable] = field(default_factory=list)`
  - _Requirements: 4.2_

- [ ] 1.5 Implement `ScannerVariables.from_api(data: list) ->
      ScannerVariables`, building one `ScannerVariable` per array entry via
      `ScannerVariable.from_api`
  - _Requirements: 3.2.3, 4.2_

- [ ] 1.6 Confirm no `ScannerVariableEvaluationMode` enum or any other
      public type is defined anywhere in this file beyond
      `ScannerVariable`/`ScannerVariables` — `"RAW"`/`"TOTP"` are string
      literals used only inside `to_api()`/`from_api()`
  - _Requirements: 4.3_

- [ ] 1.7 Confirm `models/scanner_variable.py` imports neither `requests`
      nor `HttpClient`
  - _Requirements: 4.5_

- [ ] 1.8 Add Google-style docstrings and full type hints to every
      class/function added in this section
  - _AGENTS.md Definition of Done_

---

## 2. Service implementation

- [ ] 2.1 Add `ScannerVariableValidationError(VeracodeSDKError)` to
      `src/veracode_dast/exceptions.py`, with a `rule` attribute, following
      the exact shape of `ScannerValidationError`/
      `AnalysisProfileValidationError` — confirm it is NOT a subclass of
      `VeracodeApiError`
  - _Requirements: 6.1_

- [ ] 2.2 Create `src/veracode_dast/services/scanner_variables.py` with
      `ScannerVariablesService.__init__(self, http_client: HttpClient)`,
      storing only the client; no base-URL constant defined in this
      module; import `TARGET_CONFIGURATION_SERVICE_BASE_URL` from
      `services/targets.py` only where needed for docstrings/tests, never
      redefine it
  - _Requirements: 9.2, 9.4_

- [ ] 2.3 Implement the shared `_require_non_blank` static helper (mirrors
      every other service), raising `ScannerVariableValidationError`
  - _Requirements: 3.2.2, 3.3.5, 6.1_

- [ ] 2.4 Implement `ScannerVariablesService.get(analysis_profile_id: str)
      -> ScannerVariables`: blank-ID guard first, then `GET
      /analysis_profiles/{id}/scanner_variables`, build via
      `ScannerVariables.from_api`, emit the INFO log naming the count and
      `analysis_profile_id`; confirm `VeracodeNotFoundError` is not caught
  - _Requirements: 3.2.1, 3.2.3, 3.2.4, 8.1_

- [ ] 2.5 Implement `ScannerVariablesService._validate(config: dict) ->
      list[ScannerVariable]`: config is a dict → `variables` is a list →
      each entry is a dict → each entry has a non-blank `reference_key`
      (and is not a duplicate of one already seen) → each entry has a
      non-blank `value` → `totp_seed`, if present, is a `bool` — raising
      the specific `ScannerVariableValidationError(rule=...)` documented
      in requirements.md §5.2–§5.8 for each failure, in that check order
  - _Requirements: 5.1–5.8_

- [ ] 2.6 Implement `ScannerVariablesService.update(analysis_profile_id:
      str, config_file: str | Path | dict[str, Any]) -> ScannerVariables`:
      blank-ID guard → `load_json_config(config_file)` (reused, not
      reimplemented) → `_validate` → `PUT
      /analysis_profiles/{id}/scanner_variables` with
      `json=[v.to_api() for v in variables]` → if `response.data is None`
      (204) return `ScannerVariables(variables=[])`, else
      `ScannerVariables.from_api(response.data)`; emit INFO logs before and
      after the call naming `analysis_profile_id` and the variable count —
      never a variable's `value`
  - _Requirements: 3.3.1, 3.3.4, 3.3.6, 3.3.7, 3.3.8, 8.2, 8.3_

- [ ] 2.7 Confirm `update()` contains no code path that reads existing
      Scanner Variables (no internal `get()` call, no merge logic) before
      sending the `PUT` — the request body is built solely from
      `_validate()`'s return value
  - _Requirements: 3.3.2 (safety-critical — design.md §8)_

- [ ] 2.8 Add Google-style docstrings and full type hints to every
      class/function added in this section
  - _AGENTS.md Definition of Done_

---

## 3. HTTP integration

- [ ] 3.1 In `src/veracode_dast/client.py`, import
      `ScannerVariablesService` from
      `veracode_dast.services.scanner_variables`
  - _Requirements: 9.2_

- [ ] 3.2 Add `self.scanner_variables = ScannerVariablesService(tcs_http_client)`
      to `VeracodeClient.__init__`, reusing the existing `tcs_http_client`
      variable already constructed for `self.targets`/
      `self.api_specifications` — confirm no new `HttpClient` instance and
      no new base-URL constant are introduced anywhere in this task
  - _Requirements: 9.2_

- [ ] 3.3 Confirm no existing line in `client.py`, `services/targets.py`,
      `services/teams.py`, `services/api_specifications.py`, or
      `utils/sdk_config.py` is modified by this task beyond the one import
      and one line added above
  - _Requirements: 13.7_

- [ ] 3.4 Add a Google-style docstring update to `VeracodeClient`
      reflecting the new attribute
  - _AGENTS.md Definition of Done_

---

## 4. Unit tests (models)

Location: `tests/models/test_scanner_variable.py`.

- [ ] 4.1 `ScannerVariable.from_api` round-trips a fixture with
      `evaluation_mode: "TOTP"` (→ `totp_seed=True`) and one with
      `evaluation_mode` absent (→ `totp_seed=False`); confirms `id` is
      carried through when present and `None` when absent; confirms
      `is_inherited` is read from the wrapper, not the inner object
  - _Requirements: 3.2.3, 3.1.2, 3.1.3_

- [ ] 4.2 `ScannerVariable.to_api()`: `totp_seed=True` →
      `{"evaluation_mode": "TOTP", ...}`; `totp_seed=False` →
      `{"evaluation_mode": "RAW", ...}`; the result never contains an `id`
      key even when the instance's `id` is set
  - _Requirements: 7.1, 3.1.3_

- [ ] 4.3 `ScannerVariable(reference_key="username", value="admin",
      totp_seed=False)` constructs without `is_inherited`/`id` (README
      "Returned Model" compatibility)
  - _Requirements: 3.1.2, 3.1.3_

- [ ] 4.4 `ScannerVariables.from_api` round-trips a fixture matching
      `EffectiveScannerVariables` (an array, not an object)
  - _Requirements: 3.2.3, 4.2_

- [ ] 4.5 Confirm `models/scanner_variable.py` imports neither `requests`
      nor `HttpClient`
  - _Requirements: 4.5_

---

## 5. Integration tests (service + models + client wiring)

Location: `tests/services/test_scanner_variables.py`. Same stub-`HttpClient`
pattern as every other service's test suite — no real network access,
environment variables, or Veracode credentials.

- [ ] 5.1 Build a stub/fake `HttpClient` returning prepared `HttpResponse`
      values or raising prepared `VeracodeApiError` subclasses (same
      pattern as `tests/services/test_targets.py`)
  - _Requirements: 10.1_

- [ ] 5.2 `get()`: blank ID raises `ScannerVariableValidationError` with no
      call made to the stub; a valid ID + 200 response returns the
      expected `ScannerVariables`; a stubbed 404 propagates
      `VeracodeNotFoundError` unchanged
  - _Requirements: 3.2.1–3.2.4_

- [ ] 5.3 `update()`: blank ID raises with no call made; each of
      `_validate()`'s failure modes (non-dict config, missing `variables`,
      non-dict entry, missing `reference_key`, missing `value`, duplicate
      `reference_key`, non-boolean `totp_seed`) raises its specific
      `ScannerVariableValidationError(rule=...)` with no call made to the
      stub
  - _Requirements: 5.1–5.8_

- [ ] 5.4 `update()`: the exact README "SDK Configuration" example
      produces a `PUT` whose captured JSON body is a flat array matching
      design.md §7's transformation (list order preserved, `otp` entry has
      `evaluation_mode: "TOTP"`); a stubbed 200 response returns the
      correctly built `ScannerVariables`
  - _Requirements: 3.3.1, 3.3.6, 7.1, 7.2_

- [ ] 5.5 `update()`: given a config listing fewer `reference_key`s than a
      simulated "existing" set, assert the captured request body contains
      *only* the supplied entries — proves no internal `get()`/merge
      occurs (design.md §8; requirements.md Acceptance Criterion 4)
  - _Requirements: 3.3.2_

- [ ] 5.6 `update()`: `config_file={"variables": []}` + a stubbed 204
      response → returns `ScannerVariables(variables=[])` without raising
      on an empty/missing response body
  - _Requirements: 3.3.7_

- [ ] 5.7 `update()`: accepts both a `tmp_path` JSON file and an equivalent
      in-memory dict for `config_file`, asserting identical resulting
      request bodies; a stubbed 404 propagates `VeracodeNotFoundError`
  - _Requirements: 3.3.3, 3.3.8_

- [ ] 5.8 `caplog` assertion: across every test in this file that uses a
      real-looking `value` (e.g. `"secret123"`, `"ABCDEFGHIJKLMNOP"`), no
      captured log record from `get()` or `update()` contains that string
  - _Requirements: 8.3 (safety-critical)_

- [ ] 5.9 `VeracodeClient()` wiring test: `client.scanner_variables` is a
      `ScannerVariablesService`, and its underlying `HttpClient` is the
      same object identity as `client.targets`'s
  - _Requirements: 9.2_

---

## 6. Documentation

- [ ] 6.1 Add `examples/scanner_variables_example.py` using stdlib
      `argparse` to accept `--analysis-profile-id` and `--config-file` as
      command-line arguments — never hardcoded, never read from the
      environment by the example itself, matching
      `examples/target_management_example.py`'s convention
  - _AGENTS.md Definition of Done_

- [ ] 6.2 Script body: construct `VeracodeClient()`, call
      `scanner_variables.get(analysis_profile_id)` and print each
      variable's `reference_key` and `totp_seed`/`is_inherited` (never
      `value`, to avoid printing secrets to a terminal/CI log by example),
      then call `update(analysis_profile_id, config_file)` and print the
      resulting count
  - _AGENTS.md Definition of Done, Requirements: 8.3_

- [ ] 6.3 Add a sample `specs/scanner-variables/scanner-variables.json`
      fixture mirroring README's "SDK Configuration" example exactly
  - _AGENTS.md Definition of Done_

- [ ] 6.4 Confirm the script contains no Azure DevOps-specific code and no
      hardcoded credentials or business data
  - _Requirements: 9.2 (Platform Agnostic, per AGENTS.md §5)_

- [ ] 6.5 Do not modify [README.md](README.md) — it is the reference this
      specification was derived from, not a task output

---

## 7. Quality gates

- [ ] 7.1 `ruff check` passes with no new warnings
- [ ] 7.2 `mypy` passes in strict mode for `models/scanner_variable.py`,
      `services/scanner_variables.py`, the extended `client.py`, and the
      extended `exceptions.py`
- [ ] 7.3 `pytest` passes for `test_scanner_variable.py` and
      `test_scanner_variables.py`, alongside the full existing suite
      (confirming no regression to Target Management, Team Management, API
      Specification Management, or Scanner Profiles' shared
      `utils/sdk_config.py`)
- _AGENTS.md Definition of Done_

---

## Dependency order

0 (prerequisite `utils/sdk_config.py`, only if Scanner Profiles hasn't
landed yet) must precede everything else. 1 (models) has no other
dependency and must precede 2 (service), which imports it and imports 0's
`load_json_config`. 2 must precede 3 (HTTP integration), which wires the
finished `ScannerVariablesService` into `VeracodeClient`. 4 depends on 1; 5
depends on 2 and 3 (the wiring test in 5.9 needs `client.py` already
updated); 6 depends on 3; 7 depends on everything above.

## Explicitly not part of these tasks

Per [requirements.md §13](requirements.md#13-out-of-scope): no
`utilize_in_ai_assisted_login` support; no read-then-merge/`upsert()`
convenience on top of `update()`; no "unknown reference_key"/"did you
mean" suggestion mechanism; no Authentication Configuration, Scanner
Profiles, Analysis Profiles CRUD, Crawl Configuration, or ISM Gateway
configuration; no server-side TOTP-seed validity validation; no combined
`dast-config.json`; no edits to `services/targets.py`,
`services/teams.py`, `services/api_specifications.py`, or
`utils/sdk_config.py` beyond task 0's creation (only if not already
present); no CLI.
