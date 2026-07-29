# Tasks — Scanner Profiles

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Depends on `TARGET_CONFIGURATION_SERVICE_BASE_URL` from
`services/targets.py` (Target Management) and the shared `HttpClient` — no
new HTTP Client capability is required.

---

- [ ] 1. Create Scanner models
  - **Description:** Add `ScannerType(StrEnum)` (the 35-value closed set
    from requirements.md §0.2) and the `Scanner` frozen dataclass
    (`id`, `enabled`, `inherited`, `editable`) with `from_api`, mapping the
    API's `ScannerValue` field names (`effective_value`→`enabled`,
    `is_inherited`→`inherited`, `is_editable`→`editable`) to the README's
    public shape. File: `src/veracode_dast/models/scanner.py`.
  - **Acceptance Criteria:**
    - `ScannerType` has exactly the 35 members listed in
      requirements.md §0.2, each value matching the API's raw string.
    - `Scanner.from_api({"id": "sql_injection", "effective_value": True,
      "is_inherited": False, "is_editable": True})` returns
      `Scanner(id="sql_injection", enabled=True, inherited=False,
      editable=True)`.
    - Full type hints and Google-style docstrings.
  - _Requirements: §0.2_

- [ ] 2. Create Scanner Profile models
  - **Description:** Add the `ScannerProfile` frozen dataclass
    (`scanners: list[Scanner]`, `analysis_profile_id: str | None = None`,
    `parent_analysis_profile_id: str | None = None`) with `from_api`, in
    the same file as task 1.
  - **Acceptance Criteria:**
    - `ScannerProfile(scanners=[...])` constructs without the two optional
      ID fields, matching
      [README "Returned Model"](README.md#returned-model) verbatim.
    - `ScannerProfile.from_api(data)` builds every `Scanner` in
      `data["scanners"]` via `Scanner.from_api` and carries through
      `analysis_profile_id`/`parent_analysis_profile_id` when present.
    - Full type hints and Google-style docstrings.
  - _Requirements: §0.2, design.md §3.1_

- [ ] 3. Implement GET Scanner Profile
  - **Description:** Add `ScannersService` in
    `src/veracode_dast/services/scanners.py`, importing
    `TARGET_CONFIGURATION_SERVICE_BASE_URL` from `services/targets.py`
    (not redefining it). Implement `__init__(self, http_client:
    HttpClient)` and `get(self, analysis_profile_id: str) ->
    ScannerProfile`.
  - **Acceptance Criteria:**
    - Blank/whitespace-only `analysis_profile_id` raises
      `ScannerValidationError(rule="analysis_profile_id_required")`
      before any HTTP call.
    - Calls `GET /analysis_profiles/{analysis_profile_id}/scanners` and
      returns `ScannerProfile.from_api(response.data)` on 200.
    - A 404 response propagates as `VeracodeNotFoundError`, unchanged.
    - Full type hints and Google-style docstrings.
  - _Requirements: 3.1, 3.6_

- [ ] 4. Implement SDK Configuration Loader
  - **Description:** Add `src/veracode_dast/utils/sdk_config.py` with
    `load_json_config(source: str | Path | dict[str, Any]) ->
    dict[str, Any]`: returns `source` unchanged if it is already a dict;
    otherwise reads and JSON-parses the file at that path.
  - **Acceptance Criteria:**
    - Passing a `dict` returns it unchanged (identity, no copy needed).
    - Passing a path to a valid JSON file returns the parsed dict.
    - A missing path raises `ConfigFileNotFoundError` (new exception,
      `exceptions.py`, subclasses `VeracodeSDKError` directly).
    - A path whose contents are not valid JSON raises
      `ConfigFileInvalidError` (new exception, same convention).
    - No scanner-specific logic in this module — resource-agnostic, so it
      is reusable by later configuration-driven modules (design.md §11).
    - Full type hints and Google-style docstrings.
  - _Requirements: 3.2, 5.6_

- [ ] 5. Implement Configuration Validator
  - **Description:** In `utils/sdk_config.py`, add `suggest_closest(name:
    str, valid_names: Iterable[str]) -> str | None` (thin wrapper over
    stdlib `difflib.get_close_matches`). In `services/scanners.py`, add
    `ScannersService._validate(config: dict[str, Any]) -> dict[str,
    bool]`, checking, in order: `config` is a dict; `config["scanners"]`
    is a dict; every value in it is a `bool`; every key in it is a member
    of `ScannerType` (else raise `UnknownScannerError` using
    `suggest_closest` against the known name set).
  - **Acceptance Criteria:**
    - `suggest_closest("sql", <35 ScannerType values>)` returns
      `"sql_injection"`.
    - Non-dict config → `ScannerValidationError(rule="config_must_be_object")`.
    - Missing/non-dict `"scanners"` key →
      `ScannerValidationError(rule="scanners_key_required")`.
    - Non-bool scanner value →
      `ScannerValidationError(rule="scanner_value_must_be_bool")`.
    - `{"scanners": {"sql": true}}` → `UnknownScannerError` whose message
      contains `Unknown scanner 'sql'.` and `Did you mean 'sql_injection'?`
      (README "Validation", verbatim).
    - An empty `{"scanners": {}}` is valid (returns `{}`, no error).
    - Full type hints and Google-style docstrings.
  - _Requirements: 5.1–5.5_

- [ ] 6. Implement Configuration Transformer
  - **Description:** In `ScannersService.update()`, build the Veracode API
    request body from the validated `dict[str, bool]` returned by task 5's
    validator: `{"scanners": [{"id": name, "value": value} for name, value
    in scanners.items()]}`. No separate `Transformer` class (design.md
    §6) — a single dict comprehension is the complete implementation.
  - **Acceptance Criteria:**
    - Given `{"sql_injection": True, "xss": True, "csrf": False}`,
      produces exactly
      [README "JSON Transformation"](README.md#json-transformation)'s
      generated API request, key order preserved.
  - _Requirements: §6 (design.md)_

- [ ] 7. Implement PUT Scanner Profile
  - **Description:** Complete `ScannersService.update(self,
    analysis_profile_id: str, config_file: str | Path | dict[str, Any]) ->
    ScannerProfile`, composing tasks 3–6: blank-ID guard → `load_json_config`
    → `_validate` → build request body → `PUT
    /analysis_profiles/{analysis_profile_id}/scanners` → build
    `ScannerProfile.from_api(response.data)` from the response.
  - **Acceptance Criteria:**
    - Reproduces the six-step flow in
      [README "Update Scanner Profile"](README.md#update-scanner-profile).
    - Accepts both a file path and an in-memory dict for `config_file`.
    - Returns the server's post-update `ScannerProfile` (never a
      locally-reconstructed one).
    - A 404 response propagates as `VeracodeNotFoundError`, unchanged.
    - INFO logs before/after the call (analysis_profile_id, scanner
      count) — never the full configuration payload.
    - `VeracodeClient` wiring: construct `ScannersService` with the
      **same** `HttpClient` instance already assigned to `self.targets`
      (`client.py`), and assign to `self.scanners`.
    - Full type hints and Google-style docstrings.
  - _Requirements: 3.2–3.6_

- [ ] 8. Unit Tests
  - **Description:** Add `tests/models/test_scanner.py`,
    `tests/utils/test_sdk_config.py`, `tests/services/test_scanners.py`
    using the stub-`HttpClient` approach already used by Target/API
    Specification Management — no mocking library, no real sockets.
  - **Acceptance Criteria:** Full case list in design.md §10 is covered,
    including: `from_api` field-name mapping and README-shape
    construction; loader dict/path/missing-file/malformed-JSON cases;
    `suggest_closest` match and no-match cases; `get`/`update` blank-ID
    guards; every `_validate` failure mode; the exact README config →
    request-body transformation; 404 propagation; a `caplog` assertion
    that no log record contains the full scanner payload.
  - _Requirements: §10 (design.md)_

- [ ] 9. Integration Tests
  - **Description:** Add an integration-style test (or extend an existing
    end-to-end example under `examples/`) that exercises `client.scanners.get()`
    → `client.scanners.update()` → `client.scanners.get()` against a real
    or recorded Veracode API response, confirming the round trip: scanners
    enabled via `update()` are reflected in the next `get()`.
  - **Acceptance Criteria:**
    - Confirms the real API's `ScannerProfile`/`ScannerValue` response
      shape matches what `Scanner.from_api`/`ScannerProfile.from_api`
      expect (guards against drift from requirements.md §0.2 if Veracode's
      schema changes).
    - Confirms a 404 for an unknown `analysis_profile_id` is a real,
      observed API behavior, not just an assumption from the OpenAPI
      document.
  - _Requirements: §0.3, 6 (Acceptance Criteria)_

- [ ] 10. Documentation
  - **Description:** Add `examples/scanner_profiles_example.py` (argparse:
    `--analysis-profile-id`, `--config-file`) demonstrating `get()` then
    `update()`. Add a sample `specs/scanners-profiles/scanner-profile.json`
    fixture mirroring the README's example. Cross-check
    [README.md](README.md) still matches the shipped public API exactly
    (method names, argument names, exception list) — do not modify
    README.md itself; if a mismatch is found, the code changes, not the
    README.
  - **Acceptance Criteria:**
    - The example script runs end-to-end against a real or stubbed
      client and prints the same shape shown in the README.
    - `ruff check`, `mypy --strict`, and `pytest` all pass.
  - _AGENTS.md Definition of Done_

---

## Dependency order

1–2 (models) can be implemented together (same file) and must precede 3–7,
which import them. 4–5 (`utils/sdk_config.py` + `_validate`) can be built
in parallel with 3, but must both land before 6–7. 6 is inline within 7,
not a separate landing point. 7 depends on 3–6 and on `client.py` wiring.
8 depends on 1–7. 9 depends on 7 and a reachable Veracode API/recording.
10 depends on 7 (example) and on the whole feature being otherwise
complete (README cross-check).

## Explicitly not part of these tasks

Per [requirements.md §7](requirements.md#7-out-of-scope): no Authentication,
Scanner Variables, or ISM Gateway configuration; no crawl configuration; no
creating/listing/deleting Analysis Profiles; no client-side replication of
Veracode's server-side scanner-eligibility validation; no combined
`dast-config.json`; no CLI.
