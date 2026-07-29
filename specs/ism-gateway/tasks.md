# Tasks — ISM Gateways

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Do not start implementation until this specification is reviewed and
approved — and, per requirements.md §14.7, until §1.3 (`IsmEndpoint.token`
as the identifier sent for `endpointUuid`) and §1.4 (empty-body `PUT` as
`remove()`) have been validated against a live or sandbox Veracode
account. Both are inferred from an underspecified OpenAPI schema, not
confirmed by any documented example — see design.md §15.1.

---

- [ ] 0. Precondition — live-account validation (requirements.md §14.7)
  - [ ] 0.1 Against a real or sandbox Veracode account, call `GET
        /ism_gateways` and inspect a real `IsmEndpoint` entry: confirm
        whether `token` is in fact a stable per-endpoint identifier (or
        find whichever field actually is one)
  - [ ] 0.2 Call `PUT /ism_gateways/targets/{target_id}` with an empty
        body (`{}`) against a target that currently has a gateway
        assigned; confirm the assignment is cleared (not left unchanged,
        not rejected)
  - [ ] 0.3 If either assumption is wrong, update requirements.md §1.3/
        §1.4 and design.md §3.4/§3.7 accordingly before proceeding — the
        rest of this task list assumes both are confirmed

- [ ] 1. Models (`models/ism_gateway.py`)
  - [ ] 1.1 Implement `ISMEndpoint` as a frozen dataclass: `token: str`,
        `name: str | None = None`, `status: str | None = None`
  - [ ] 1.2 Implement `ISMEndpoint.from_api(data: dict) -> ISMEndpoint`
  - [ ] 1.3 Implement `ISMGateway` as a frozen dataclass: `id: str`,
        `name: str`, `status: str | None = None`, `hostname: str | None =
        None`, `endpoints: list[ISMEndpoint] = field(default_factory=list)`
  - [ ] 1.4 Implement `ISMGateway.from_api(data: dict) -> ISMGateway`,
        mapping `refId` → `id`
  - [ ] 1.5 Confirm class names are exactly `ISMGateway`/`ISMEndpoint`
        (not `IsmGateway`/`IsmEndpoint`) per design.md §3.1's naming
        decision
  - [ ] 1.6 Confirm `ISMGateway(id="gateway-id", name="Corporate
        Gateway", status="ONLINE")` (README's literal example)
        constructs without error
  - [ ] 1.7 Do NOT implement a model for `TargetIsmGateway`, `Problem`,
        or `ProblemError` (design.md §7)
  - [ ] 1.8 Add Google-style docstrings and full type hints
  - _Requirements: 7.1–7.6_

- [ ] 2. Configuration model (decision, not new code)
  - [ ] 2.1 Confirm SDK Configuration (`{"gateway": {"name": ...}}`)
        stays a plain `dict[str, Any]` end-to-end — no dedicated
        `IsmGatewayConfig` class is introduced, matching the precedent in
        [scanners-profiles design §8](../scanners-profiles/design.md#8-models)
        ("configuration is a plain dict... since it has no behavior of
        its own beyond validation")
  - [ ] 2.2 Document this decision inline (a one-line comment or
        docstring note on `_extract_gateway_name_from_config`, task 7) so
        a future reader doesn't wonder where the "config model" is
  - _Requirements: design.md §3.6_

- [ ] 3. `IsmGatewaysService.list`
  - [ ] 3.1 Create `src/veracode_dast/services/ism_gateways.py`
  - [ ] 3.2 Define module constants `_ISM_GATEWAYS_PATH = "/ism_gateways"`,
        `_TARGET_ISM_GATEWAY_PATH = "/ism_gateways/targets/{target_id}"`
  - [ ] 3.3 Implement `IsmGatewaysService.__init__(self, http_client:
        HttpClient)`, storing the client and a module logger; confirm
        `IsmGatewaysService` never constructs an `HttpClient` itself and
        imports `TARGET_CONFIGURATION_SERVICE_BASE_URL` rather than
        redefining it (task 12 uses the constant; this task only needs
        the import to exist for later use)
  - [ ] 3.4 Implement `list(self) -> list[ISMGateway]`: `GET
        /ism_gateways`, build via `ISMGateway.from_api` per array item
  - [ ] 3.5 Emit the `INFO` log from design.md §9 on success
  - [ ] 3.6 Add Google-style docstring and full type hints
  - _Requirements: 4.1.1–4.1.3_

- [ ] 4. `IsmGatewaysService.get`
  - [ ] 4.1 Implement the `_require_non_blank` static helper (same
        pattern as `ApiSpecificationsService`/`TargetsService`)
  - [ ] 4.2 Implement `get(self, target_id: str) -> ISMGateway | None`
  - [ ] 4.3 Call `GET /ism_gateways/targets/{target_id}`; if
        `gatewayUuid` is absent/blank, log and return `None`
  - [ ] 4.4 Otherwise call `self.list()` and find the matching `id`;
        raise `IsmGatewayValidationError(rule="gateway_not_found_by_id")`
        if none matches
  - [ ] 4.5 Emit the `INFO` logs from design.md §9 (assigned vs.
        unassigned cases)
  - [ ] 4.6 Confirm no 404 handling is added for this endpoint beyond
        letting whatever the HTTP Client raises propagate (requirements.md
        §0.3.1: none is documented)
  - [ ] 4.7 Add Google-style docstring and full type hints
  - _Requirements: 4.2.1–4.2.6_

- [ ] 5. Gateway Resolver (`_resolve_gateway_by_name`, `_select_endpoint`)
  - [ ] 5.1 Implement `_resolve_gateway_by_name(name: str, gateways:
        list[ISMGateway]) -> ISMGateway` as a module-level pure function:
        exact-match filter; zero matches → `GatewayNotFoundError` (with
        `suggest_closest` suggestion); more than one match →
        `GatewayNameNotUniqueError`
  - [ ] 5.2 Implement `_select_endpoint(gateway: ISMGateway) ->
        ISMEndpoint` as a module-level pure function: zero endpoints →
        `IsmGatewayValidationError(rule="gateway_has_no_endpoint")`; more
        than one → `IsmGatewayValidationError(rule="gateway_endpoint_ambiguous")`;
        exactly one → return it
  - [ ] 5.3 Confirm both functions take already-fetched data and make no
        `HttpClient` call themselves (design.md §3.4, requirements.md
        §5.1)
  - [ ] 5.4 Add Google-style docstrings and full type hints
  - _Requirements: 4.3.5–4.3.9, 5.1–5.3_

- [ ] 6. Configuration Loader (reuse)
  - [ ] 6.1 If `utils/sdk_config.py` does not yet exist (i.e. Scanner
        Profiles has not yet been implemented), create it exactly per
        [scanners-profiles design §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared)
        (`load_json_config`, `suggest_closest`) and add
        `ConfigFileNotFoundError`/`ConfigFileInvalidError` to
        `exceptions.py` exactly as that spec defines them
  - [ ] 6.2 Otherwise, confirm the existing `utils/sdk_config.py` is
        imported unmodified — no second Loader implementation
  - [ ] 6.3 Import `load_json_config` and `suggest_closest` into
        `services/ism_gateways.py`
  - _Requirements: 8.1–8.3_

- [ ] 7. Configuration Validator (`_extract_gateway_name_from_config`)
  - [ ] 7.1 Implement `_extract_gateway_name_from_config(config: dict)
        -> str`: config must be a dict (else
        `IsmGatewayValidationError(rule="config_must_be_object")`);
        must contain a `"gateway"` dict (else
        `rule="gateway_key_required"`); `gateway["name"]` must be a
        non-blank string (else `rule="gateway_name_required"`)
  - [ ] 7.2 Add the task-2 decision note (plain-dict configuration, no
        model class) as a one-line docstring comment on this function
  - [ ] 7.3 Add Google-style docstring and full type hints
  - _Requirements: 6.4–6.6_

- [ ] 8. Configuration Transformer (`_build_target_ism_gateway_payload`)
  - [ ] 8.1 Implement `_build_target_ism_gateway_payload(gateway:
        ISMGateway, endpoint: ISMEndpoint) -> dict[str, Any]` returning
        `{"gatewayUuid": gateway.id, "endpointUuid": endpoint.token}`
  - [ ] 8.2 Add Google-style docstring and full type hints
  - _Requirements: 4.3.10_

- [ ] 9. `IsmGatewaysService.update`
  - [ ] 9.1 Implement `update(self, target_id: str, *, gateway_name:
        str | None = None, config_file: str | Path | dict[str, Any] |
        None = None) -> ISMGateway`
  - [ ] 9.2 Validate `target_id` non-blank (task 4.1's helper)
  - [ ] 9.3 Validate exactly one of `gateway_name`/`config_file` is
        supplied → else `IsmGatewayValidationError(rule=
        "gateway_name_or_config_file_required")`
  - [ ] 9.4 If `config_file` given: `load_json_config()` (task 6) →
        `_extract_gateway_name_from_config()` (task 7) to obtain
        `gateway_name`
  - [ ] 9.5 Call `self.list()`, then `_resolve_gateway_by_name()` (task
        5.1) and `_select_endpoint()` (task 5.2)
  - [ ] 9.6 Build the request body via
        `_build_target_ism_gateway_payload()` (task 8) and call `PUT
        /ism_gateways/targets/{target_id}`
  - [ ] 9.7 On success, return the `ISMGateway` resolved in 9.5 — confirm
        no second `list()`/lookup call is made to "rebuild" the result
        (design.md §4.3.11's reasoning: `TargetIsmGateway`'s response
        carries no name/status data to rebuild one from)
  - [ ] 9.8 Emit the `INFO` logs from design.md §9 (before and after)
  - [ ] 9.9 Confirm no HTTP call is made before every validation/
        resolution step passes (mirrors the "validate before HTTP" rule
        every prior feature follows)
  - [ ] 9.10 Add Google-style docstring and full type hints
  - _Requirements: 4.3.1–4.3.12_

- [ ] 10. `IsmGatewaysService.remove`
  - [ ] 10.1 Implement `remove(self, target_id: str) -> None`
  - [ ] 10.2 Validate `target_id` non-blank
  - [ ] 10.3 Call `PUT /ism_gateways/targets/{target_id}` with `json={}`
  - [ ] 10.4 Emit the `INFO` logs from design.md §9 (before and after)
  - [ ] 10.5 Add Google-style docstring and full type hints
  - _Requirements: 4.4.1–4.4.4_

- [ ] 11. Exception additions (`exceptions.py`)
  - [ ] 11.1 Implement `IsmGatewayValidationError(VeracodeSDKError)` with
        a `rule` attribute; confirm it is NOT a subclass of
        `VeracodeApiError`
  - [ ] 11.2 Implement `GatewayNotFoundError(VeracodeSDKError)` with
        `name`/`suggestion` attributes and the exact message format from
        design.md §3.2; confirm the class name matches README's literal
        spelling (not `IsmGatewayNotFoundError`)
  - [ ] 11.3 Implement `GatewayNameNotUniqueError(VeracodeSDKError)` with
        `name`/`matches` attributes
  - [ ] 11.4 Add Google-style docstrings and full type hints
  - _Requirements: 6.1–6.3_

- [ ] 12. `VeracodeClient` (`client.py`)
  - [ ] 12.1 Import `IsmGatewaysService` from
        `veracode_dast.services.ism_gateways`
  - [ ] 12.2 Add `self.ism_gateways = IsmGatewaysService(tcs_http_client)`
        after `self.api_specifications`, reusing the existing
        `tcs_http_client` instance — confirm no new `HttpClient` or base
        URL is introduced
  - _Requirements: 10.1–10.2_

- [ ] 13. Unit tests — models (`tests/models/test_ism_gateway.py`)
  - [ ] 13.1 `ISMEndpoint.from_api` / `ISMGateway.from_api` round-trip a
        fixture matching requirements.md §0.2, confirming `refId` → `id`
  - [ ] 13.2 `ISMGateway(id=..., name=..., status=...)` (README's literal
        example) constructs without `hostname`/`endpoints`
  - _Requirements: 7.1–7.6_

- [ ] 14. Unit tests — Gateway Resolver and Configuration Validator/Transformer
  - [ ] 14.1 `_resolve_gateway_by_name`: exact match; zero matches (with
        and without a close-name suggestion) → `GatewayNotFoundError`;
        multiple matches → `GatewayNameNotUniqueError` with all matched
        `id`s
  - [ ] 14.2 `_select_endpoint`: one endpoint → selected; zero → `rule=
        "gateway_has_no_endpoint"`; two or more → `rule=
        "gateway_endpoint_ambiguous"`
  - [ ] 14.3 `_extract_gateway_name_from_config`: valid config → extracted
        name; non-dict, missing `gateway` key, blank `name` → each their
        own `rule`
  - [ ] 14.4 `_build_target_ism_gateway_payload`: produces
        `{"gatewayUuid": ..., "endpointUuid": ...}` exactly
  - _Requirements: 5.1–5.3, 6.4–6.6, 4.3.10_

- [ ] 15. Unit tests — service (`tests/services/test_ism_gateways.py`)
  - [ ] 15.1 Stub/fake `HttpClient` returning prepared `HttpResponse`
        values or raising prepared `VeracodeApiError` subclasses
  - [ ] 15.2 `list()`: 200 → `list[ISMGateway]` matching fixture
        count/order
  - [ ] 15.3 `get()`: blank `target_id` → validation error, no HTTP call;
        unassigned target → `None`; assigned target → matching
        `ISMGateway`, asserting exactly two stub `get` calls were made;
        `gatewayUuid` with no `list()` match → `IsmGatewayValidationError
        (rule="gateway_not_found_by_id")`
  - [ ] 15.4 `update()`: blank `target_id` → validation error, no HTTP
        call; neither/both `gateway_name`/`config_file` → validation
        error, no HTTP call; the README "SDK Configuration" fixture via
        `config_file` (both a `tmp_path` JSON file and an equivalent
        in-memory dict) → identical `PUT` body to the direct
        `gateway_name=` call; unresolvable name → `GatewayNotFoundError`,
        no `put` call; ambiguous name → `GatewayNameNotUniqueError`, no
        `put` call; zero/multiple endpoints → `IsmGatewayValidationError`,
        no `put` call; 404 → `VeracodeNotFoundError` propagates
  - [ ] 15.5 `remove()`: blank `target_id` → validation error, no HTTP
        call; 200 → `None`, asserting the stub's `put` was called with
        `json={}`; 404 → `VeracodeNotFoundError` propagates
  - [ ] 15.6 `caplog` assertion: no captured log record from this feature
        contains any `token` value used in a test fixture
  - _Requirements: 4.1.1–4.4.4, 6.1–6.3, 9.1–9.6, 11.1–11.3_

- [ ] 16. Integration tests
  - [ ] 16.1 Add `tests/integration/test_ism_gateways_integration.py`
        (or extend an existing integration suite if one already exists
        from a prior feature), gated behind whatever marker/skip
        convention this SDK's other integration tests use for "requires a
        real Veracode account" (follow the precedent set by the first
        Phase 1/2 feature to introduce one; if none exists yet, this is
        the first — keep the marker generic, e.g. `@pytest.mark.integration`,
        not ISM-Gateway-specific)
  - [ ] 16.2 Exercise the full `list()` → `update(gateway_name=...)` →
        `get()` → `remove()` → `get()` round trip against a real
        Veracode account's actual ISM gateway configuration, confirming
        the live-account assumptions from task 0 (`token` as identifier,
        empty-body `PUT` as remove) hold against the real API — not just
        against fixtures
  - [ ] 16.3 Confirm the round trip leaves the test account's target in
        its original gateway-assignment state afterward (re-assign
        whatever was there before, or leave unassigned if that was the
        starting state) — this test must not permanently alter shared
        account state
  - _Requirements: 14.7 (design.md §15.1)_

- [ ] 17. Example
  - [ ] 17.1 Add `examples/ism_gateway_example.py` using stdlib
        `argparse` to accept `--target-id` and `--gateway-name` as
        command-line arguments — never hardcoded, never read from the
        environment by the example itself (AGENTS.md §6.2), matching the
        precedent set by
        [target-management design §10](../target-management/design.md#10-file-layout-introduced-by-this-feature)
  - [ ] 17.2 Script body: construct `VeracodeClient()`, call `list()` and
        print available gateway names, call `update(target_id,
        gateway_name=...)`, call `get(target_id)` to confirm, call
        `remove(target_id)` — printing each typed result
  - [ ] 17.3 Confirm the script contains no Azure DevOps-specific code
  - [ ] 17.4 Add `specs/ism-gateway/ism-gateway.json` as a sample SDK
        Configuration fixture mirroring README exactly
        (`{"gateway": {"name": "Corporate Gateway"}}`), for use by both
        the example and the config-file unit tests (task 15.4)
  - _AGENTS.md Definition of Done_

- [ ] 18. Documentation
  - [ ] 18.1 Confirm `README.md` needs no edits — it is the authoritative
        source this spec was derived from and is not modified by this
        feature (per the original task brief: "Do not modify README.md")
  - [ ] 18.2 Add a short "ISM Gateways" section to the project root
        `README.md`'s pipeline-usage documentation, following the
        existing convention that pipeline usage flows (ensure/
        update_by_name/delete-style walkthroughs) live in the project
        README, not under `specs/`
  - [ ] 18.3 Confirm every public class/method introduced by this
        feature has a complete Google-style docstring (cross-check
        against tasks 1, 3–5, 7–12)
  - _AGENTS.md Definition of Done_

- [ ] 19. Quality gates
  - [ ] 19.1 `ruff check` passes with no new warnings
  - [ ] 19.2 `mypy` passes in strict mode for `models/ism_gateway.py`,
        `services/ism_gateways.py`, the extended `client.py`, and the
        extended `exceptions.py`
  - [ ] 19.3 `pytest` passes for `test_ism_gateway.py` and
        `test_ism_gateways.py`
  - _AGENTS.md Definition of Done_

---

## Dependency order

0 (live-account validation) should happen before 5 and 9–10 are finalized,
since it can change `_select_endpoint`'s and `remove()`'s implementation
— but the surrounding scaffolding (1–4) can be built in parallel while
validation is pending. 1 (models) has no dependency on anything else in
this feature. 2 is a decision, not code, and can be confirmed at any
point. 3–4 depend on 1 (they return/consume `ISMGateway`). 5 depends on 1
(operates on `ISMGateway`/`ISMEndpoint`) and on 11 (raises its
exceptions) being at least stubbed. 6 depends on Scanner Profiles' state
in the codebase (create if absent, else import). 7 depends on 6 (uses
`load_json_config`) and 11. 8 depends on 1. 9 depends on 3 (`list()`), 5,
6, 7, 8, and 11 all being complete. 10 depends only on 4's
`_require_non_blank` helper. 12 depends on 3–4 and 9–10 being complete
(it wires the finished `IsmGatewaysService`). 13–15 depend on their
respective implementation tasks; 16 depends on 9–10 and on task 0's
validation having actually happened against a real account; 17 depends
on 12; 18 depends on 17; 19 depends on everything above.

## Explicitly not part of these tasks

Per [requirements.md §14](requirements.md#14-out-of-scope): no
`endpoint_name`-style disambiguation for multi-endpoint gateways; no
internal `analysis_profile_id` → `target_id` resolution (a caller
performs that themselves via `client.analysis_profiles.get(...)`); no
Target Management/Analysis Profiles/Scanner Profiles/Scanner Variables/
Authentication Configuration work; no replication of
`ISM_GATEWAY_MAPPING_ERROR`/`TARGET_ISM_CONFIGURATION_REQUIRED` as
client-side validation; no caching/retry/pagination-aggregation beyond
the HTTP Client's own; no CLI or execution-platform integration.

The following was identified as valuable but is explicitly deferred
rather than part of this feature's tasks (see [design.md
§15](design.md#15-additional-architectural-recommendations-not-implemented-here)):
an `endpoint_name=` parameter for multi-endpoint gateways, and caching
`list()` results across a single `update()`/`get()` call (not across
calls — that would violate the Stateless principle).
