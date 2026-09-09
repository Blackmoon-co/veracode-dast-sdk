# Design — Target ↔ Application Linking

Implements [requirements.md](requirements.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Extends
[Target Management](../target-management/design.md) (adds two methods to
`TargetsService`, reuses its base-URL constant and `TargetValidationError`)
and copies the structure of [Team Management](../team-management/design.md)
for the new read-only `ApplicationsService`.

---

## 1. Overview

Two small additions, no new layer, no `HttpClient` change:

```
VeracodeClient
      ↓
  HTTP Client                          (reused, unmodified)
      ↓
ApplicationsService   ← NEW      TargetsService.link / .unlink   ← NEW methods
      ↓                                 ↓
Application, ApplicationPage  ← NEW    (no new model)
      ↓
  REST API  (DAST Target Configuration Service — same base URL as Targets)
```

`ApplicationsService` is a near-verbatim copy of `TeamService`: a
paginated `list`, a `get_by_name` that scans pages for an exact match and
raises when absent, and an `exists` that wraps `get_by_name`.
`TargetsService.link` / `.unlink` are one HTTP call each with a
blank-argument guard in front.

The "resolve app before team, link after create" ordering from the
motivating requirement lives entirely in the example script (§7), never
in the SDK — same as Team resolution today.

## 2. Architecture

This feature touches four files and adds two:

| File | Change |
|---|---|
| `src/veracode_dast/models/application.py` | **new** — `Application`, `ApplicationPage` |
| `src/veracode_dast/services/applications.py` | **new** — `ApplicationsService` |
| `src/veracode_dast/services/targets.py` | `+ link()`, `+ unlink()` |
| `src/veracode_dast/exceptions.py` | `+ ApplicationNotFoundError` |
| `src/veracode_dast/client.py` | `+ import`, `+ self.applications = ApplicationsService(tcs_http_client)` |
| `examples/…` | see §7 |

`tcs_http_client` (already constructed in `VeracodeClient.__init__` for
`self.targets` and its siblings) is passed to `ApplicationsService`
unchanged — `/applications` is on the same base URL as `/targets`.

## 3. Components and Interfaces

### 3.1 `src/veracode_dast/models/application.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Application:
    """A Veracode Application, as returned by `GET /applications`.

    Attributes:
        guid: The application's UUID. This is the value passed to
            `TargetsService.link()`.
        id: The application's identifier. A string in this OpenAPI schema
            (distinct from `Target.application_id`, which is int64 on a
            different schema — requirements.md §0.4).
        name: The application's display name.
        linked_scan_target_url: URL of the scan already linked to this
            application, if any.
    """

    guid: str
    id: str
    name: str
    linked_scan_target_url: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Application:
        """Builds an `Application` from a `GET /applications` list item."""
        return cls(
            guid=data["guid"],
            id=data["id"],
            name=data["name"],
            linked_scan_target_url=data.get("linked_scan_target_url"),
        )


@dataclass(frozen=True)
class ApplicationPage:
    """One page of `GET /applications` results (OpenAPI `PagedApplications`,
    minus `_links` — same decision as `TargetPage`)."""

    items: list[Application]
    page_number: int
    page_size: int
    total_pages: int
    total_elements: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ApplicationPage:
        """Reads `_embedded.Applications` (capital `A`) and `page.*`;
        a missing `_embedded`/`Applications` yields an empty `items`."""
        items = [
            Application.from_api(item)
            for item in data.get("_embedded", {}).get("Applications", [])
        ]
        page = data["page"]
        return cls(
            items=items,
            page_number=page["number"],
            page_size=page["size"],
            total_pages=page["total_pages"],
            total_elements=page["total_elements"],
        )
```

### 3.2 `src/veracode_dast/exceptions.py` (extended)

```python
class ApplicationNotFoundError(VeracodeSDKError):
    """Raised when no Application matches a `get_by_name` lookup.

    Attributes:
        name: The application name that was searched for.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"No application found with name: {name}")
```

Byte-for-byte the shape of `TeamNotFoundError` / `TargetNotFoundError`.
No `ApplicationValidationError` is added — `link`/`unlink`/`get_by_name`
blank-argument checks raise the existing `TargetValidationError`
(requirements.md §5.1).

### 3.3 `src/veracode_dast/services/applications.py`

```python
"""Application resolution: read-only access to the DAST Target
Configuration Service's Applications resource.

Never imports or depends on `services/targets.py` — Application resolution
is independent of Target Management, exactly like Team Management
(services/teams.py).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from veracode_dast.exceptions import ApplicationNotFoundError, TargetValidationError
from veracode_dast.models.application import Application, ApplicationPage

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

_BASE_PATH: Final = "/applications"
_DEFAULT_PAGE_SIZE: Final = 10

logger = logging.getLogger(__name__)


class ApplicationsService:
    """Read-only access to Veracode Applications (DAST TCS domain)."""

    def __init__(self, http_client: HttpClient) -> None:
        """Args:
            http_client: An `HttpClient` configured with
                `TARGET_CONFIGURATION_SERVICE_BASE_URL` (the same instance
                `TargetsService` uses).
        """
        self._http_client = http_client

    def list(
        self,
        *,
        name: str | None = None,
        page: int = 0,
        limit: int = _DEFAULT_PAGE_SIZE,
    ) -> ApplicationPage:
        """Lists Applications, one page at a time.

        Note:
            `name`'s matching semantics are undocumented in the OpenAPI;
            `get_by_name` does its own exact comparison rather than
            trusting this filter.
        """
        params: dict[str, object] = {"page": page, "limit": limit}
        if name is not None:
            params["name"] = name
        response = self._http_client.get(_BASE_PATH, params=params)
        return ApplicationPage.from_api(response.data)  # type: ignore[arg-type]

    def get_by_name(self, name: str) -> Application:
        """Resolves an Application by exact, case-sensitive name.

        Scans every page of `list(name=name)`, since the `name` filter is
        not documented as an exact match.

        Raises:
            TargetValidationError: If `name` is blank.
            ApplicationNotFoundError: If no application has that exact name.
        """
        self._require_non_blank(name, rule="name_required")
        page_number = 0
        while True:
            page = self.list(name=name, page=page_number)
            for application in page.items:
                if application.name == name:
                    logger.info("Resolved application %r to guid=%s", name, application.guid)
                    return application
            if page_number + 1 >= page.total_pages:
                break
            page_number += 1
        logger.info("No application found matching name %r", name)
        raise ApplicationNotFoundError(name)

    def exists(self, name: str) -> bool:
        """True if an Application with that exact name exists, else False.

        Any error other than `ApplicationNotFoundError` propagates.
        """
        try:
            self.get_by_name(name)
        except ApplicationNotFoundError:
            return False
        return True

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise TargetValidationError("Value must not be blank", rule=rule)
```

This is `TeamService` with `/teams`→`/applications`, `team_name`→`name`,
`Team`→`Application`, `TeamNotFoundError`→`ApplicationNotFoundError`,
`TeamValidationError`→`TargetValidationError`. The duplication is
deliberate: `TeamService` and `ApplicationsService` are independent
resources on independent (here, coincidentally shared) base URLs, and
[target-management/requirements.md §11.5](../target-management/requirements.md#11-boundaries-non-goals-for-this-feature)
already established that name-resolution helpers are not abstracted into a
shared base class.

### 3.4 `src/veracode_dast/services/targets.py` (extended)

Two methods added to `TargetsService`; nothing existing is modified.

```python
_LINK_PATH: Final = "/targets/{target_id}/link"


    def link(self, target_id: str, application_uuid: str) -> None:
        """Links a Target to a Veracode Application.

        Calls `PUT /targets/{target_id}/link`. The Target must be an
        ENTERPRISE-scan Target; the SDK does not pre-check this (a `422`
        propagates as `VeracodeValidationError`). Linking an
        already-linked Target yields `409` → `VeracodeConflictError`.

        Args:
            target_id: The target's unique identifier.
            application_uuid: The application's UUID (`Application.guid`).

        Raises:
            TargetValidationError: If `target_id` or `application_uuid` is
                blank.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        self._require_non_blank(application_uuid, rule="application_uuid_required")
        self._http_client.put(
            _LINK_PATH.format(target_id=target_id),
            json={"application_uuid": application_uuid},
        )
        logger.info("Linked target %s to an application", target_id)

    def unlink(self, target_id: str) -> None:
        """Unlinks a Target from its Application.

        Calls `DELETE /targets/{target_id}/link`.

        Args:
            target_id: The target's unique identifier.

        Raises:
            TargetValidationError: If `target_id` is blank.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        self._http_client.delete(_LINK_PATH.format(target_id=target_id))
        logger.info("Unlinked target %s from its application", target_id)

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise TargetValidationError("Value must not be blank", rule=rule)
```

`TargetsService` today has no `_require_non_blank` helper (its existing
`_validate` is create/update-specific). This adds the same static helper
`TeamService` and `ApplicationsService` use — three copies of a two-line
guard, consistent with the SDK's existing "no shared base class for
services" stance.

The `link`/`unlink` log lines name only `target_id` — never
`application_uuid` (requirements.md §6.5). `ApplicationsService.get_by_name`
logs the resolved name and `guid`, exactly as `TeamService.get_by_name`
logs the name and `team_id`; `linked_scan_target_url` (a business URL) is
never logged.

### 3.5 `src/veracode_dast/client.py` (extended)

```python
from veracode_dast.services.applications import ApplicationsService
# ...
        self.analysis_runs = AnalysisRunsService(tcs_http_client)
        self.applications = ApplicationsService(tcs_http_client)   # + this line
```

Reuses the existing `tcs_http_client` variable — **no new `HttpClient`
instance, no new base-URL constant** anywhere in this feature. This is the
only change to `client.py`.

## 4. Service Responsibilities

| Responsibility | Owner |
|---|---|
| HTTP transport, HMAC auth, retries, status→exception mapping | `HttpClient` (unchanged) |
| Blank-argument validation | `ApplicationsService._require_non_blank` / `TargetsService._require_non_blank` |
| Exact-name page scan + not-found raise | `ApplicationsService.get_by_name` |
| Building typed models from responses | `Application.from_api` / `ApplicationPage.from_api` |
| Link / unlink HTTP calls | `TargetsService.link` / `.unlink` |
| "app before team, link after create" ordering | the **example script**, not the SDK |
| Business-event logging | `ApplicationsService`, `TargetsService` |

## 5. Error Handling

| Failure | Exception | Raised by |
|---|---|---|
| Blank `name` / `target_id` / `application_uuid` | `TargetValidationError` (with `rule`) | the service, before any HTTP call |
| No exact-name match in any page | `ApplicationNotFoundError` | `ApplicationsService.get_by_name` |
| HTTP 401 | `VeracodeAuthenticationError` | `HttpClient` (unchanged) |
| HTTP 403 | `VeracodeAuthorizationError` | `HttpClient` (unchanged) |
| HTTP 404 (unknown target or application) | `VeracodeNotFoundError` | `HttpClient` (unchanged) |
| HTTP 409 (already linked / import in progress) | `VeracodeConflictError` | `HttpClient` (unchanged) |
| HTTP 422 (target not enterprise type) | `VeracodeValidationError` | `HttpClient` (unchanged) |
| HTTP 400 / 500 / 501 / other | `VeracodeApiError` | `HttpClient` (unchanged) |

No `try`/`except` around any `HttpClient` call in either service. `exists()`
is the one place an SDK exception is caught — `ApplicationNotFoundError`
only, converted to `False`; every other exception (including a `500`)
propagates (requirements.md §3.1.3, §7).

## 6. Testing Strategy

Locations: `tests/models/test_application.py`,
`tests/services/test_applications.py`, additions to
`tests/services/test_targets.py` and `tests/test_client_wiring.py`. Same
stub-`HttpClient` approach as every other service — no mocking library, no
real sockets.

Cases:

- `Application.from_api`: full mapping; `linked_scan_target_url` absent →
  `None`.
- `ApplicationPage.from_api`: `_embedded.Applications` (capital `A`) +
  `page.*` round-trip; `_embedded` entirely absent → `items == []`.
- `ApplicationsService.list`: `name` forwarded only when given;
  `page`/`limit` defaults are `0`/`10`; one call = one `GET`.
- `ApplicationsService.get_by_name`:
  - exact match on page 1 → returns it, no page 2 fetched.
  - no match on page 1, exact match on page 2 (`total_pages == 2`) →
    returns it after two `GET`s.
  - substring-only / case-different row across all pages → raises
    `ApplicationNotFoundError`.
  - blank `name` → `TargetValidationError(rule="name_required")`, no
    `GET`.
- `ApplicationsService.exists`: `True` on match; `False` when
  `get_by_name` raises `ApplicationNotFoundError`; a stubbed `500`
  propagates as `VeracodeApiError` (not `False`).
- `TargetsService.link`: body is exactly `{"application_uuid": "<uuid>"}`,
  path is `/targets/<id>/link`, `204` → `None`; blank `target_id` and
  blank `application_uuid` each raise `TargetValidationError` with the
  right `rule` and make no HTTP call; stubbed `404`/`409`/`422` propagate
  as `VeracodeNotFoundError`/`VeracodeConflictError`/`VeracodeValidationError`.
- `TargetsService.unlink`: `DELETE /targets/<id>/link`, `204` → `None`;
  blank `target_id` raises before any HTTP call.
- `caplog`: no record from `link`/`unlink` contains the
  `application_uuid`; no record from any of the three contains
  `linked_scan_target_url`.
- Wiring: `client.applications` is an `ApplicationsService` and its
  `_http_client` is the *same object* as `client.targets._http_client`.

## 7. Example Wiring

Per [AGENTS.md §11 Definition of Done](../../AGENTS.md#11-definition-of-done)
every feature ships a runnable example.

### 7.1 New: `examples/application_linking_example.py`

`argparse` CLI (`--app-name` required, `--target-id` required,
`--unlink` flag). Exercises all three new SDK operations:

1. `client.applications.exists(args.app_name)` — print the boolean.
2. `client.applications.get_by_name(args.app_name)` — print `guid` / `name`
   (or exit non-zero on `ApplicationNotFoundError` with a clear message).
3. `client.targets.link(args.target_id, app.guid)` — print confirmation.
4. `client.targets.unlink(args.target_id)` — only when `--unlink` is
   passed (destructive / mutually exclusive with a persistent link).

Business data comes only from CLI args; nothing hardcoded, nothing read
from the environment by the example itself.

### 7.2 Updated: `examples/end_to_end_workflow_example.py`

Add an **optional** `--app-name`. When present, the script:

1. Calls `client.applications.get_by_name(args.app_name)` **before**
   `client.teams.get_by_name(...)`. `ApplicationNotFoundError` is caught
   and turned into a non-zero exit with "application '<name>' does not
   exist; not creating a target" — no Team lookup, no `ensure`, nothing
   else runs.
2. After the existing `ensure` / `update_by_name` block, calls
   `client.targets.link(target.target_id, app.guid)`.

When `--app-name` is omitted, the script's behaviour is byte-for-byte
what it is today — the two new blocks are both `if args.app_name:`.

`examples/target_management_example.py` is **not** modified — it has no
Team-resolution step to sit the app check in front of, and the dedicated
`application_linking_example.py` already covers `link`/`unlink`.

## 8. Traceability

| Component | Requirements covered |
|---|---|
| `Application`, `ApplicationPage` | 3.3, §0.4 |
| `ApplicationsService.list` | 3.1.1, 7 (Acceptance) |
| `ApplicationsService.get_by_name` | 3.1.2, 4, 5.1, 7 |
| `ApplicationsService.exists` | 3.1.3, 7 |
| `ApplicationNotFoundError` | 4 |
| `TargetsService.link` | 3.2.1, 3.2.3, 5.1, 5.3, 5.4, 7 |
| `TargetsService.unlink` | 3.2.2, 3.2.3, 5.1, 7 |
| Reuse of `TargetValidationError`, no `ApplicationValidationError` | 5.1 |
| No `scan_type` pre-check, no forced idempotency | 5.3, 5.4 |
| `client.py` wiring, shared `HttpClient` | §2, 6.1, 7 (Acceptance) |
| Independence of `ApplicationsService` and `TargetsService` | 6.6 |
| Logging without Application identifiers | 6.5 |
| Example scripts | 7 (this doc), AGENTS.md Definition of Done |
| No AppSec domain, no `TargetCreate` change, no `link_by_app_name` | §8 (Out of Scope) |
