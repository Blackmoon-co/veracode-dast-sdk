# Tasks — API Specification Management

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Depends on the HTTP Client's multipart/raw amendment (see
[http-client/design.md Amendment](../http-client/design.md#amendment-multipart-upload-and-raw-binary-responses))
and on `TARGET_CONFIGURATION_SERVICE_BASE_URL` from
`services/targets.py` (Target Management).

---

- [ ] 1. Models (`models/api_specification.py`)
  - [ ] 1.1 Implement `ScopeType(str, Enum)`: `AUDIT`, `BLOCK`, `IGNORE`
  - [ ] 1.2 Implement `ScopeRuleType(str, Enum)`: `PATTERN`, `INDEX`
  - [ ] 1.3 Implement `ScopeRule` frozen dataclass + `from_api`
  - [ ] 1.4 Implement `ApiSpecification` frozen dataclass (only `target_id`
        required; every other field optional) + `from_api(data, *,
        target_id)` falling back to the supplied `target_id`
  - [ ] 1.5 Add Google-style docstrings and full type hints
  - _Requirements: 4.1–4.4_

- [ ] 2. Exception additions (`exceptions.py`)
  - [ ] 2.1 Implement `ApiSpecificationValidationError(VeracodeSDKError)`
        with a `rule` attribute
  - [ ] 2.2 Implement `ApiSpecificationFileNotFoundError(VeracodeSDKError)`
        with a `path` attribute
  - [ ] 2.3 Confirm neither subclasses `VeracodeApiError`
  - _Requirements: 6.1–6.3_

- [ ] 3. `ApiSpecificationsService` construction
  - [ ] 3.1 Create `services/api_specifications.py`, importing
        `TARGET_CONFIGURATION_SERVICE_BASE_URL` from `services/targets.py`
        (not redefining it)
  - [ ] 3.2 Implement `__init__(self, http_client: HttpClient)`, storing
        the client and a module logger
  - [ ] 3.3 Implement a private blank-string validation helper
  - [ ] 3.4 Add Google-style docstrings and full type hints
  - _Requirements: 5.1, 9_

- [ ] 4. `upload`
  - [ ] 4.1 Implement `upload(target_id, file_path) ->
        ApiSpecification`
  - [ ] 4.2 Blank `target_id` → `ApiSpecificationValidationError`; missing
        file → `ApiSpecificationFileNotFoundError`; both before any HTTP
        call
  - [ ] 4.3 `POST /targets/{target_id}/spec` with `files={"specFile":
        (name, bytes, content_type)}`
  - [ ] 4.4 Build `ApiSpecification` from the 200 response
  - [ ] 4.5 Emit INFO logs (start/complete) per design.md §5
  - _Requirements: 1.1–1.7_

- [ ] 5. `get`
  - [ ] 5.1 Implement `get(target_id) -> ApiSpecification`
  - [ ] 5.2 Blank `target_id` → `ApiSpecificationValidationError`
  - [ ] 5.3 `GET /targets/{target_id}/spec`; build `ApiSpecification`;
        confirm 404 propagates as `VeracodeNotFoundError`
  - _Requirements: 2.1–2.4_

- [ ] 6. `download`
  - [ ] 6.1 Implement `download(target_id, destination_path) -> Path`
  - [ ] 6.2 Blank `target_id` or missing destination parent directory →
        `ApiSpecificationValidationError`
  - [ ] 6.3 `GET /targets/{target_id}/spec/download` with `raw=True`;
        write bytes via `Path.write_bytes`; return the resolved `Path`
  - _Requirements: 3.1–3.5_

- [ ] 7. `VeracodeClient` wiring (`client.py`)
  - [ ] 7.1 Construct `ApiSpecificationsService` with the **same**
        `HttpClient` instance already assigned to `self.targets`
  - [ ] 7.2 Assign to `self.api_specifications`
  - _Requirements: 9_

- [ ] 8. Unit tests
  - [ ] 8.1 `tests/models/test_api_specification.py`: `from_api`
        round-trips, `target_id` fallback
  - [ ] 8.2 `tests/services/test_api_specifications.py`: full case list in
        design.md §7
  - _Requirements: 10_

- [ ] 9. Examples
  - [ ] 9.1 `examples/api_specification_management_example.py` (argparse:
        `--target-id`, `--spec-file`, `--download-to`)
  - [ ] 9.2 `examples/end_to_end_workflow_example.py`: the task's exact
        MVP workflow — `client.teams.get_by_name(...)` →
        `client.targets.create(...)` →
        `client.api_specifications.upload(...)` →
        `client.api_specifications.get(...)`
  - [ ] 9.3 A minimal sample OpenAPI YAML fixture for the upload examples
  - _AGENTS.md Definition of Done_

- [ ] 10. Quality gates
  - [ ] 10.1 `ruff check` passes with no new warnings
  - [ ] 10.2 `mypy` passes in strict mode
  - [ ] 10.3 `pytest` passes
  - _AGENTS.md Definition of Done_

---

## Dependency order

1–2 (models + exceptions) can be implemented in any order but must precede
3–7 (service + client), which import them. 3 must precede 4–6. 7 depends on
4–6 and on Target Management's `client.targets` already being wired. 8
depends on 1–7; 9 depends on 7; 10 depends on everything above.

## Explicitly not part of these tasks

Per [requirements.md §8](requirements.md#8-boundaries-non-goals-for-this-feature):
no editing of API Specifications, no version history, no spec comparison,
no deep spec validation, no automatic Target creation, no Application
linking, no scan execution/configuration, no Team Management dependency.
