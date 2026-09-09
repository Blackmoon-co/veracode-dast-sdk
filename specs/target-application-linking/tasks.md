# Tasks — Target ↔ Application Linking

Implementation checklist derived from [design.md](design.md), traceable to
[requirements.md](requirements.md). Follow the module responsibilities and
Definition of Done in [AGENTS.md](../../AGENTS.md#11-definition-of-done).

Do not start implementation until this specification is reviewed and
approved.

---

## 1. Models

- [ ] 1.1 Create `src/veracode_dast/models/application.py`. `Application`
      frozen dataclass: `guid: str`, `id: str`, `name: str`,
      `linked_scan_target_url: str | None = None`. Imports neither
      `requests` nor `HttpClient`.
  - _Requirements: 3.3.1, 3.3.3, §0.4_

- [ ] 1.2 `Application.from_api(data: dict) -> Application` — `guid`/`id`/
      `name` required keys, `linked_scan_target_url` via `.get(...)`.
  - _Requirements: 3.3.1_

- [ ] 1.3 `ApplicationPage` frozen dataclass: `items: list[Application]`,
      `page_number`, `page_size`, `total_pages`, `total_elements` — same
      shape as `TargetPage`.
  - _Requirements: 3.3.2_

- [ ] 1.4 `ApplicationPage.from_api(data: dict) -> ApplicationPage` —
      reads `_embedded.Applications` (**capital `A`**) and
      `page.{number,size,total_pages,total_elements}`; a missing
      `_embedded` or missing `Applications` yields `items == []` (use
      `data.get("_embedded", {}).get("Applications", [])`).
  - _Requirements: 3.3.2, 7 (Acceptance: absent `_embedded`)_

- [ ] 1.5 Google-style docstrings + full type hints on everything added.
  - _AGENTS.md Definition of Done_

---

## 2. Exception

- [ ] 2.1 Add `ApplicationNotFoundError(VeracodeSDKError)` to
      `src/veracode_dast/exceptions.py`, carrying `name`, message
      `f"No application found with name: {name}"` — byte-for-byte the
      shape of `TeamNotFoundError`. Confirm it is **not** a subclass of
      `VeracodeApiError`.
  - _Requirements: 4_

- [ ] 2.2 Do **not** add an `ApplicationValidationError` — blank-argument
      checks in this feature raise the existing `TargetValidationError`.
  - _Requirements: 5.1_

---

## 3. `ApplicationsService`

- [ ] 3.1 Create `src/veracode_dast/services/applications.py` with a
      module docstring stating it never imports or depends on
      `services/targets.py` (mirror the `services/teams.py` docstring).
      `_BASE_PATH = "/applications"`, `_DEFAULT_PAGE_SIZE = 10`,
      module-level `logger`.
  - _Requirements: 1, 6.3, 6.6_

- [ ] 3.2 `ApplicationsService.__init__(self, http_client: HttpClient)` —
      stores only the client. No base-URL constant defined in this module
      (it is only ever consumed in `client.py`, which imports
      `TARGET_CONFIGURATION_SERVICE_BASE_URL` from `services/targets.py`).
  - _Requirements: 6.1, 6.3_

- [ ] 3.3 `_require_non_blank(value, *, rule)` static helper raising
      `TargetValidationError` — same two lines as in `services/teams.py`.
  - _Requirements: 5.1_

- [ ] 3.4 `list(*, name: str | None = None, page: int = 0, limit: int =
      _DEFAULT_PAGE_SIZE) -> ApplicationPage` — `GET /applications`,
      forward `name` only when not `None`, always send `page`/`limit`;
      build via `ApplicationPage.from_api`. One call = one request.
  - _Requirements: 3.1.1, 7 (Acceptance)_

- [ ] 3.5 `get_by_name(name: str) -> Application` — blank guard
      (`rule="name_required"`), then scan `list(name=name)` page by page
      for an exact, case-sensitive `application.name == name`; return the
      first match; `INFO` log on resolve; after the last page
      (`page_number + 1 >= page.total_pages`) raise
      `ApplicationNotFoundError(name)` with an `INFO` "not found" log.
      Same control flow as `TeamService.get_by_name`.
  - _Requirements: 3.1.2, 4, 5.1_

- [ ] 3.6 `exists(name: str) -> bool` — `try: get_by_name(name)` / `except
      ApplicationNotFoundError: return False` / `return True`. No other
      exception is caught.
  - _Requirements: 3.1.3, 7 (Acceptance: 500 propagates, not False)_

- [ ] 3.7 Google-style docstrings + full type hints on everything added.
  - _AGENTS.md Definition of Done_

---

## 4. `TargetsService.link` / `.unlink`

- [ ] 4.1 In `src/veracode_dast/services/targets.py` add
      `_LINK_PATH: Final = "/targets/{target_id}/link"` alongside the
      existing `_BASE_PATH`.
  - _Requirements: 3.2_

- [ ] 4.2 Add `_require_non_blank(value, *, rule)` static helper to
      `TargetsService` (it currently has only `_validate`), raising
      `TargetValidationError` — same two lines used in `teams.py` /
      `applications.py`.
  - _Requirements: 5.1_

- [ ] 4.3 `link(self, target_id: str, application_uuid: str) -> None` —
      blank guards for `target_id` (`rule="target_id_required"`) and
      `application_uuid` (`rule="application_uuid_required"`) **before**
      any HTTP call; `self._http_client.put(_LINK_PATH.format(
      target_id=target_id), json={"application_uuid": application_uuid})`;
      `INFO` log naming **only** `target_id`; return `None`.
  - _Requirements: 3.2.1, 3.2.3, 5.1, 5.3, 5.4, 6.5_

- [ ] 4.4 `unlink(self, target_id: str) -> None` — blank guard for
      `target_id`; `self._http_client.delete(_LINK_PATH.format(
      target_id=target_id))`; `INFO` log naming only `target_id`;
      return `None`.
  - _Requirements: 3.2.2, 3.2.3, 5.1, 6.5_

- [ ] 4.5 Confirm no existing method, constant, or import in
      `services/targets.py` is modified — this task is purely additive.
      In particular `link`/`unlink` do **not** call `get()`,
      `ApplicationsService`, or read `scan_type`.
  - _Requirements: 3.2.3, 5.3, 6.6, §8_

- [ ] 4.6 Google-style docstrings + full type hints on both methods.
  - _AGENTS.md Definition of Done_

---

## 5. Client wiring

- [ ] 5.1 In `src/veracode_dast/client.py` import `ApplicationsService`
      from `veracode_dast.services.applications`.
  - _Requirements: §2_

- [ ] 5.2 Add `self.applications = ApplicationsService(tcs_http_client)` to
      `VeracodeClient.__init__`, reusing the existing `tcs_http_client`
      variable. Confirm **no** new `HttpClient` instance and **no** new
      base-URL constant are introduced.
  - _Requirements: §2, 6.1, 7 (Acceptance: shared HttpClient)_

- [ ] 5.3 Confirm this is the only change to `client.py` (one import, one
      assignment line).
  - _Requirements: §8_

---

## 6. Unit tests — models

Location: `tests/models/test_application.py`.

- [ ] 6.1 `Application.from_api` round-trips a fixture with all four
      fields; a second fixture without `linked_scan_target_url` →
      attribute is `None`.
  - _Requirements: 3.3.1_

- [ ] 6.2 `ApplicationPage.from_api` round-trips a `PagedApplications`
      fixture (`_embedded.Applications`, capital `A`); a fixture with no
      `_embedded` key → `items == []`, no `KeyError`.
  - _Requirements: 3.3.2, 7 (Acceptance)_

- [ ] 6.3 Confirm `models/application.py` imports neither `requests` nor
      `HttpClient`.
  - _AGENTS.md §3 Hard rule_

---

## 7. Integration tests — `ApplicationsService`

Location: `tests/services/test_applications.py`. Stub/fake `HttpClient`
returning prepared `HttpResponse` values or raising prepared
`VeracodeApiError` subclasses — same pattern as
`tests/services/test_teams.py`. No network, env vars, or credentials.

- [ ] 7.1 `list()`: `name` present → `name` in the forwarded params;
      `name` omitted → not in params; `page`/`limit` default to `0`/`10`;
      exactly one `HttpClient.get` call.
  - _Requirements: 3.1.1_

- [ ] 7.2 `get_by_name()`: exact match on page 1 → returns it, only one
      `get` call.
  - _Requirements: 3.1.2_

- [ ] 7.3 `get_by_name()`: no match page 1, exact match page 2
      (`total_pages == 2`) → returns it after two `get` calls.
  - _Requirements: 3.1.2, 7 (Acceptance: multi-page scan)_

- [ ] 7.4 `get_by_name()`: only a case-different / substring row across
      all pages → raises `ApplicationNotFoundError` carrying `name`.
  - _Requirements: 3.1.2, 4_

- [ ] 7.5 `get_by_name()` / `exists()`: blank/whitespace `name` →
      `TargetValidationError(rule="name_required")`, no `get` call.
  - _Requirements: 5.1_

- [ ] 7.6 `exists()`: `True` on match; `False` when `get_by_name` raises
      `ApplicationNotFoundError`; a stubbed `500` on the underlying `get`
      propagates as `VeracodeApiError` (assert it is **not** swallowed
      into `False`).
  - _Requirements: 3.1.3, 7 (Acceptance)_

---

## 8. Integration tests — `link` / `unlink`

Location: additions to `tests/services/test_targets.py`.

- [ ] 8.1 `link("t-1", "app-uuid")`: asserts `HttpClient.put` called with
      path `/targets/t-1/link` and `json == {"application_uuid":
      "app-uuid"}`; `204` response → returns `None`.
  - _Requirements: 3.2.1, 7 (Acceptance)_

- [ ] 8.2 `link()`: blank `target_id` →
      `TargetValidationError(rule="target_id_required")`; blank
      `application_uuid` →
      `TargetValidationError(rule="application_uuid_required")`; neither
      makes an HTTP call.
  - _Requirements: 5.1_

- [ ] 8.3 `link()`: stubbed `404` / `409` / `422` propagate as
      `VeracodeNotFoundError` / `VeracodeConflictError` /
      `VeracodeValidationError`, unchanged (service has no `try`/`except`).
  - _Requirements: 3.2.3, 5.3, 5.4, 7 (Acceptance)_

- [ ] 8.4 `unlink("t-1")`: asserts `HttpClient.delete` called with
      `/targets/t-1/link`; `204` → `None`; blank `target_id` raises
      before any HTTP call.
  - _Requirements: 3.2.2, 5.1_

- [ ] 8.5 `caplog` (INFO): no record emitted by `link`/`unlink` contains
      the `application_uuid` value.
  - _Requirements: 6.5_

---

## 9. Wiring test

Location: additions to `tests/test_client_wiring.py`.

- [ ] 9.1 `client.applications` is an `ApplicationsService`; its
      `_http_client` is the **same object** (`is`) as
      `client.targets._http_client`.
  - _Requirements: §2, 7 (Acceptance)_

---

## 10. Examples

- [ ] 10.1 Create `examples/application_linking_example.py` — stdlib
      `argparse`: `--app-name` (required), `--target-id` (required),
      `--unlink` (flag). Body: `exists()` → `get_by_name()` (exit
      non-zero with a clear message on `ApplicationNotFoundError`) →
      `link(target_id, app.guid)` → `unlink(target_id)` only if
      `--unlink`. No hardcoded / env-sourced business data.
  - _Requirements: 7.1 (design.md); AGENTS.md Definition of Done_

- [ ] 10.2 Update `examples/end_to_end_workflow_example.py`: add optional
      `--app-name`. When set, `client.applications.get_by_name(...)` runs
      **before** `client.teams.get_by_name(...)`, catching
      `ApplicationNotFoundError` → non-zero exit ("application '<name>'
      does not exist; not creating a target"), before any Team/Target
      call. After the existing `ensure`/`update_by_name` block,
      `client.targets.link(target.target_id, app.guid)`. Both new blocks
      guarded by `if args.app_name:`; omitting the flag leaves current
      behaviour unchanged.
  - _Requirements: 7.2 (design.md); README "Motivating requirement"_

- [ ] 10.3 Do **not** modify `examples/target_management_example.py`
      (no Team step to precede; covered by 10.1).
  - _Requirements: 7.2 (design.md)_

- [ ] 10.4 Confirm no example contains Azure DevOps-specific code or
      hardcoded credentials/business data.
  - _AGENTS.md §5 Platform Agnostic_

- [ ] 10.5 Do not modify this spec's [README.md](README.md) /
      [requirements.md](requirements.md) / [design.md](design.md) — they
      are the reference this spec was derived from, not task outputs.
      Updating the project-level `README.md` / `README.es.md` for the new
      `client.applications` surface and the `link`/`unlink` methods is a
      separate documentation task, not covered here.

---

## 11. Quality gates

- [ ] 11.1 `ruff check` passes with no new warnings.
- [ ] 11.2 `mypy --strict` passes for `models/application.py`,
      `services/applications.py`, the extended `services/targets.py`,
      `client.py`, and `exceptions.py`.
- [ ] 11.3 `pytest` passes for the new `test_application.py` /
      `test_applications.py` and the extended `test_targets.py` /
      `test_client_wiring.py`, alongside the full existing suite (no
      regression to any Phase 1/2/3 module).
- _AGENTS.md Definition of Done_

---

## Dependency order

1 (models) precedes 2 (exception, independent) and 3/4 (services, which
import 1 and 2). 3 and 4 are independent of each other. 5 (wiring) needs 3.
6 needs 1; 7 needs 3; 8 needs 4; 9 needs 5. 10 needs 3+4+5. 11 needs
everything.

## Explicitly not part of these tasks

Per [requirements.md §8](requirements.md#8-out-of-scope): no AppSec
Applications API; no Application create/update/delete; no change to
`TargetCreate`/`TargetUpdate`/`Target` or the target create/update flow;
no `TargetsService.link_by_app_name(...)` convenience; no result-import
status handling; no `_links` parsing; no shared base class for the
name-resolution services; no CLI or execution-platform integration; no
edits to `services/targets.py` beyond the additive `_LINK_PATH`,
`_require_non_blank`, `link`, and `unlink`.
