# Design — Scanner Variables

Implements [requirements.md](requirements.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Extends
[Target Management](../target-management/design.md) (reuses its base-URL
constant and shared `HttpClient` instance, same pattern as
[API Specification Management](../api-specification-management/design.md)
and [Analysis Profiles](../analysis-profile/design.md)) and reuses the
configuration-driven pipeline first built by
[Scanner Profiles](../scanners-profiles/design.md) (`utils/sdk_config.py`).

---

## 1. Overview

The Scanner Variables service manages the runtime values authentication
mechanisms reference by name during an authenticated scan. `get()` is a
thin read — one HTTP call, one model built from the response, the same
shape as `ApiSpecificationsService.get()`. `update()` follows Scanner
Profiles' configuration-driven pipeline (SDK Configuration → Loader →
Validator → Transformer → HTTP call), but with one behavior Scanner
Profiles does not have: the underlying REST endpoint is a **full-array
replace**, not a per-key toggle. §8 is dedicated entirely to that
difference, because it is the one place a naive port of Scanner Profiles'
design would silently do the wrong thing.

## 2. Architecture

This feature adds one service and its models to the existing layered
architecture (AGENTS.md §3) — no new layer, no change to `HttpClient`:

```
VeracodeClient
      ↓
  HTTP Client                    (reused, unmodified)
      ↓
ScannerVariablesService           ← THIS FEATURE
      ↓
ScannerVariable, ScannerVariables  (models)                ← THIS FEATURE
      ↓
  REST API   (DAST Target Configuration Service, same base URL as Targets)
```

Inside `ScannerVariablesService.update()`, the SDK Configuration document
is carried through the same four stages Scanner Profiles established:

```
SDK Configuration              (scanner-variables.json, or an in-memory dict)
      ↓
Configuration Loader            load_json_config()          ← REUSED, not reimplemented
      ↓
Validator                       structure + reference_key rules (§6)
      ↓
Transformer                     ScannerVariable.to_api() per entry (§7)
      ↓
HttpClient                      PUT /analysis_profiles/{id}/scanner_variables
      ↓
Veracode API                    (full-array replace — see §8)
```

`load_json_config()` is imported from `utils/sdk_config.py`
([specs/scanners-profiles design §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared))
unchanged — this feature adds nothing to that module, since `reference_key`
has no closed set for `suggest_closest()` to check membership against
(requirements.md §6.3, §9.6).

## 3. Components and Interfaces

### 3.1 `src/veracode_dast/models/scanner_variable.py` (new)

```python
"""Typed models for the DAST Target Configuration Service's Scanner
Variables resource.

Scanner Variables provide runtime values consumed by authentication
mechanisms (login scripts, MFA/TOTP) during an authenticated DAST scan —
never interpreted or processed by this SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScannerVariable:
    """A single runtime variable consumed by authentication mechanisms
    during an authenticated DAST scan.

    Attributes:
        reference_key: The name authentication mechanisms use to look up
            this variable's value.
        value: The variable's value (e.g. a username, password, or TOTP
            seed). Never logged (requirements.md §8.3).
        totp_seed: Whether `value` is a TOTP seed evaluated by Veracode at
            scan time, rather than used as-is. The SDK's simplified
            boolean over the API's `evaluation_mode` field (`TOTP`/`RAW`),
            per README's Design Philosophy (requirements.md §3.1.1).
        is_inherited: Whether this variable's value is inherited from a
            parent Analysis Profile. Defaults to False so this class can
            still be constructed exactly as shown in README's "Returned
            Model" example (requirements.md §3.1.2).
        id: This variable's identifier, if the API assigned one. Never
            supplied by SDK Configuration; always None on a
            caller-constructed instance passed to `update()`
            (requirements.md §3.1.3).
    """

    reference_key: str
    value: str | None = None  # None on read-back: server stores it write-only
    totp_seed: bool = False
    is_inherited: bool = False
    id: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ScannerVariable:
        """Builds a `ScannerVariable` from one `EffectiveScannerVariable`.

        Args:
            data: One raw `{"effective_value": {...}, "is_inherited": ...}`
                object from a `GET`/`PUT` response array
                (requirements.md §0.2).

        Returns:
            The corresponding `ScannerVariable`.
        """
        inner = data["effective_value"]
        return cls(
            reference_key=inner["reference_key"],
            value=inner.get("value"),  # absent on read-back (write-only)
            totp_seed=inner.get("evaluation_mode") == "TOTP",
            is_inherited=data["is_inherited"],
            id=inner.get("id"),
        )

    def to_api(self) -> dict[str, Any]:
        """Builds this variable's entry in a `PUT .../scanner_variables`
        request body.

        Returns:
            A JSON-serializable object with `reference_key`, `value`, and
            `evaluation_mode` (derived from `totp_seed`). Never includes
            `id` or `utilize_in_ai_assisted_login` — neither is ever set
            from SDK Configuration (requirements.md §3.1.3, §3.1.4).
        """
        return {
            "reference_key": self.reference_key,
            "value": self.value,
            "evaluation_mode": "TOTP" if self.totp_seed else "RAW",
        }


@dataclass(frozen=True)
class ScannerVariables:
    """The complete set of Scanner Variables effective for an Analysis
    Profile, as returned by `get()`/`update()`.

    Attributes:
        variables: One `ScannerVariable` per entry in the API response.
    """

    variables: list[ScannerVariable] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: list[Any]) -> ScannerVariables:
        """Builds a `ScannerVariables` from an `EffectiveScannerVariables`
        response body.

        Args:
            data: The raw response array (requirements.md §0.2).

        Returns:
            The corresponding `ScannerVariables`.
        """
        return cls(variables=[ScannerVariable.from_api(item) for item in data])
```

No `ScannerVariableEvaluationMode` enum is defined (requirements.md §4.3)
— `"RAW"`/`"TOTP"` appear only as string literals inside `to_api()`/
`from_api()`. Introducing a public enum for a two-value distinction that is
never itself exposed to callers (it is fully hidden behind `totp_seed`)
would be exactly the kind of unrequested public surface AGENTS.md §5
("Simple — the smallest client that solves the problem correctly") warns
against; contrast with Analysis Profile's `CrawlerMode`/`DirectoryRestrictions`,
which *are* directly settable by callers and therefore earn a real enum.

No standalone model is defined for `InheritableValue` or
`EffectiveScannerVariable` (requirements.md §4.4) — the one field
`InheritableValue` contributes (`is_inherited`) is folded directly onto
`ScannerVariable` rather than kept as a generic wrapper, unlike Analysis
Profile's thirteen wrapped fields, where the generic `InheritedValue[T]`
(`models/common.py`) earns its keep by being reused thirteen times. Here it
would be reused exactly once, adding an indirection
(`variable.value_wrapper.effective_value.value`) with no payoff.

### 3.2 `src/veracode_dast/exceptions.py` (extended)

```python
class ScannerVariableValidationError(VeracodeSDKError):
    """Raised for SDK-level Scanner Variable parameter/configuration
    validation failures (requirements.md §5.1–§5.8).

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None:
        """Initializes the error.

        Args:
            message: A human-readable description of the failure.
            rule: A short identifier of which validation rule failed.
        """
        self.rule = rule
        super().__init__(message)
```

Follows the exact naming/subclassing convention already used by
`ScannerValidationError`/`AnalysisProfileValidationError`/
`TargetValidationError`: prefixed by resource name, subclassing
`VeracodeSDKError` directly (never `VeracodeApiError`), since it is always
raised before any HTTP call is made. No second exception type (an
`UnknownScannerError` equivalent) is defined — see requirements.md §6.3.

### 3.3 `src/veracode_dast/utils/sdk_config.py` (reused, not extended)

This feature imports `load_json_config()` unchanged
([specs/scanners-profiles design §3.3](../scanners-profiles/design.md#33-srcveracode_dastutilssdk_configpy-new-shared)).
It does **not** import or need `suggest_closest()` — `reference_key` is an
arbitrary consumer-defined string, not a member of a closed, SDK-known set
the way `ScannerType` is, so there is nothing to suggest a closer match
against. If Scanner Profiles has not yet landed when this feature is
implemented, `utils/sdk_config.py` (and `ConfigFileNotFoundError`/
`ConfigFileInvalidError` in `exceptions.py`) must be created first, exactly
as that spec defines them (requirements.md §9.5) — this feature does not
fork a second copy.

### 3.4 `src/veracode_dast/services/scanner_variables.py` (new)

```python
"""Scanner Variables: runtime values consumed by authentication mechanisms
(login scripts, MFA/TOTP) during an authenticated DAST scan.

`update()` always sends the caller's entire SDK Configuration as the new,
complete list of Scanner Variables for the Analysis Profile — it never
merges with, or first reads, the profile's existing Scanner Variables.
See design.md §8 ("Full-Replace Semantics").
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from veracode_dast.exceptions import ScannerVariableValidationError
from veracode_dast.models.scanner_variable import ScannerVariable, ScannerVariables
from veracode_dast.utils.sdk_config import load_json_config

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

_SCANNER_VARIABLES_PATH = "/analysis_profiles/{analysis_profile_id}/scanner_variables"

logger = logging.getLogger(__name__)


class ScannerVariablesService:
    """Reads and replaces Scanner Variables for existing Analysis Profiles."""

    def __init__(self, http_client: HttpClient) -> None:
        """Initializes the service.

        Args:
            http_client: An `HttpClient` configured with
                `TARGET_CONFIGURATION_SERVICE_BASE_URL` — the same
                instance already constructed for `TargetsService` and
                sibling Phase 2 services. This class never constructs its
                own `HttpClient`.
        """
        self._http_client = http_client

    def get(self, analysis_profile_id: str) -> ScannerVariables:
        """Gets the effective Scanner Variables for an Analysis Profile.

        Args:
            analysis_profile_id: The profile's unique identifier.

        Returns:
            The profile's current Scanner Variables.

        Raises:
            ScannerVariableValidationError: If `analysis_profile_id` is blank.
            VeracodeNotFoundError: If no profile exists with that ID.
        """
        self._require_non_blank(analysis_profile_id, rule="analysis_profile_id_required")
        response = self._http_client.get(
            _SCANNER_VARIABLES_PATH.format(analysis_profile_id=analysis_profile_id)
        )
        result = ScannerVariables.from_api(response.data)  # type: ignore[arg-type]
        logger.info(
            "Retrieved %d scanner variable(s) for analysis profile %s",
            len(result.variables),
            analysis_profile_id,
        )
        return result

    def update(
        self, analysis_profile_id: str, config_file: str | Path | dict[str, Any]
    ) -> ScannerVariables:
        """Replaces the Scanner Variables for an Analysis Profile.

        Sends the entire SDK Configuration as the new, complete list of
        Scanner Variables — any existing variable whose `reference_key` is
        absent from `config_file` is removed by the server (design.md §8).
        Passing `{"variables": []}` deletes every Scanner Variable from
        the profile.

        Args:
            analysis_profile_id: The profile's unique identifier.
            config_file: A path to an SDK Configuration JSON file, or an
                already-loaded dict of the same shape.

        Returns:
            The profile's Scanner Variables after the update.

        Raises:
            ScannerVariableValidationError: If `analysis_profile_id` is
                blank, or `config_file` fails structural/semantic
                validation.
            ConfigFileNotFoundError: If `config_file` is a path that does
                not exist.
            ConfigFileInvalidError: If `config_file`'s contents are not
                valid JSON.
            VeracodeNotFoundError: If no profile exists with that ID.
        """
        self._require_non_blank(analysis_profile_id, rule="analysis_profile_id_required")
        config = load_json_config(config_file)
        variables = self._validate(config)

        logger.info(
            "Updating scanner variables for analysis profile %s (%d variable(s))",
            analysis_profile_id,
            len(variables),
        )
        response = self._http_client.put(
            _SCANNER_VARIABLES_PATH.format(analysis_profile_id=analysis_profile_id),
            json=[variable.to_api() for variable in variables],
        )
        result = (
            ScannerVariables(variables=[])
            if response.data is None
            else ScannerVariables.from_api(response.data)  # type: ignore[arg-type]
        )
        logger.info("Scanner variables updated for analysis profile %s", analysis_profile_id)
        return result

    @staticmethod
    def _validate(config: dict[str, Any]) -> list[ScannerVariable]:
        if not isinstance(config, dict):
            raise ScannerVariableValidationError(
                "SDK Configuration must be a JSON object", rule="config_must_be_object"
            )
        raw_variables = config.get("variables")
        if not isinstance(raw_variables, list):
            raise ScannerVariableValidationError(
                "SDK Configuration must contain a 'variables' array",
                rule="variables_key_required",
            )

        seen_keys: set[str] = set()
        variables: list[ScannerVariable] = []
        for entry in raw_variables:
            if not isinstance(entry, dict):
                raise ScannerVariableValidationError(
                    "Each entry in 'variables' must be a JSON object",
                    rule="variable_must_be_object",
                )
            reference_key = entry.get("reference_key")
            if not isinstance(reference_key, str) or not reference_key.strip():
                raise ScannerVariableValidationError(
                    "Each scanner variable requires a non-blank 'reference_key'",
                    rule="reference_key_required",
                )
            if reference_key in seen_keys:
                raise ScannerVariableValidationError(
                    f"Duplicate scanner variable reference_key: '{reference_key}'",
                    rule="duplicate_reference_key",
                )
            seen_keys.add(reference_key)

            value = entry.get("value")
            if not isinstance(value, str) or not value:
                raise ScannerVariableValidationError(
                    f"Scanner variable '{reference_key}' requires a non-blank 'value'",
                    rule="value_required",
                )

            totp_seed = entry.get("totp_seed", False)
            if not isinstance(totp_seed, bool):
                raise ScannerVariableValidationError(
                    f"Scanner variable '{reference_key}': 'totp_seed' must be a boolean",
                    rule="invalid_totp_configuration",
                )

            variables.append(
                ScannerVariable(reference_key=reference_key, value=value, totp_seed=totp_seed)
            )
        return variables

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise ScannerVariableValidationError("Value must not be blank", rule=rule)
```

`_validate()` performs both structural and semantic checks in one pass and
returns plain `ScannerVariable` instances — mirroring
[Scanner Profiles' `_validate()`](../scanners-profiles/design.md#34-srcveracode_dastservicesscannerspy)
in shape, but there is no separate "known name" lookup step, since
`reference_key` has no closed set to check (requirements.md §6.3).

### 3.5 `src/veracode_dast/client.py` (extended)

```python
from veracode_dast.services.scanner_variables import ScannerVariablesService

class VeracodeClient:
    def __init__(self) -> None:
        auth = get_veracode_auth()
        self.teams = TeamService(HttpClient(base_url=ADMIN_API_BASE_URL, auth=auth))
        tcs_http_client = HttpClient(base_url=TARGET_CONFIGURATION_SERVICE_BASE_URL, auth=auth)
        self.targets = TargetsService(tcs_http_client)
        self.api_specifications = ApiSpecificationsService(tcs_http_client)
        # ... self.analysis_profiles, self.scanners (Analysis Profiles / Scanner Profiles) ...
        self.scanner_variables = ScannerVariablesService(tcs_http_client)
```

One added import, one added line, reusing the same `tcs_http_client`
variable every sibling Phase 2 service already shares. No other line in
`client.py` changes.

---

## 4. Service Responsibilities

| Responsibility | Owner |
|---|---|
| HTTP transport, HMAC auth, retries, status→exception mapping | `HttpClient` (unchanged) |
| Loading SDK Configuration (file or dict) | `utils/sdk_config.load_json_config` (reused, unchanged) |
| Structural + semantic validation (§5, §6) | `ScannerVariablesService._validate` |
| SDK Configuration → API request transformation | `ScannerVariable.to_api()` + a list comprehension in `update()` |
| Building typed models from API responses | `ScannerVariable.from_api` / `ScannerVariables.from_api` |
| Full-array-replace request construction (§8) | `ScannerVariablesService.update` |
| Business-event logging, secrets never logged | `ScannerVariablesService` |

---

## 5. SDK Configuration Flow

1. Caller calls `client.scanner_variables.update(analysis_profile_id,
   config_file)`.
2. `load_json_config()` returns a plain dict, whether `config_file` was a
   path or already a dict (requirements.md §3.3.3).
3. `_validate()` checks structure and semantics, returning a plain
   `list[ScannerVariable]` on success (requirements.md §5).
4. `update()` builds the request body via `[v.to_api() for v in
   variables]` (§7).
5. `HttpClient.put()` sends the request; a non-2xx response raises the
   appropriate exception per §9, and `update()` never catches it.
6. On 200, `ScannerVariables.from_api(response.data)` is returned. On 204,
   `ScannerVariables(variables=[])` is returned without attempting to
   parse a body (requirements.md §3.3.7).

This is exactly the flow already documented in
[README "Update Scanner Variables"](README.md#update-scanner-variables),
extended only by the 204 branch the README's numbered list doesn't
separately call out but the OpenAPI document requires.

---

## 6. Validation Flow

One pass, entirely local (no HTTP), covering both structure and semantics
together (unlike Scanner Profiles, which separates a structural pass from
a "known scanner name" semantic pass — there is no analogous second pass
here, since `reference_key` has no closed set):

1. `config` is a dict; `config["variables"]` is a list; every entry in it
   is itself a dict (requirements.md §5.2–§5.4).
2. Every entry has a non-blank `reference_key`, unique across the array,
   and a non-blank `value` (requirements.md §5.5–§5.7).
3. `totp_seed`, if present, is a JSON boolean (requirements.md §5.8).

Whether a `totp_seed=true` value is actually well-formed for TOTP
evaluation is explicitly **not** validated here (requirements.md §5.11) —
same reasoning as Scanner Profiles' refusal to replicate scanner
eligibility rules: it is Veracode's own server-side concern, not a client
one this SDK should try to track independently.

---

## 7. Transformation Layer

SDK Configuration → Veracode API request, per requirements.md §7:

```python
# SDK Configuration (one validated entry)
ScannerVariable(reference_key="otp", value="ABCDEFGHIJKLMNOP", totp_seed=True)

# Veracode API request entry (ScannerVariable request shape)
{"reference_key": "otp", "value": "ABCDEFGHIJKLMNOP", "evaluation_mode": "TOTP"}
```

```python
# Full PUT body — a flat array, not wrapped in {"variables": [...]}
[
    {"reference_key": "username", "value": "admin", "evaluation_mode": "RAW"},
    {"reference_key": "password", "value": "secret123", "evaluation_mode": "RAW"},
    {"reference_key": "otp", "value": "ABCDEFGHIJKLMNOP", "evaluation_mode": "TOTP"},
]
```

Implemented as `ScannerVariable.to_api()` plus a single list comprehension
in `update()` — no dedicated `Transformer` class, for the same reason
Scanner Profiles doesn't have one (design.md §7 there): a class with
exactly one call site and no independent state adds indirection, not
value. Array order is preserved (Python list ordering), so the request
lists variables in the same order the caller wrote them
(requirements.md §3.4.2).

---

## 8. Full-Replace Semantics (Why `update()` Never Merges)

This is the one place this feature's design diverges materially from
Scanner Profiles, and it is safety-critical enough to warrant its own
section — the same weight
[Analysis Profile design §5.3](../analysis-profile/design.md#53-update--partial-body-forced-methodpatch)
gives to *its* one safety-critical decision (forcing `method=PATCH`).

**The facts (requirements.md §0.3, §0.5.1):**

- `PUT .../scanner_variables`'s request body,
  `ScannerVariablesUpdateRequest`, is a flat array of `ScannerVariable`
  objects — the complete set the caller wants, not a set of per-key
  patches.
- The same endpoint documents a 204 response meaning "Successfully deleted
  the scanner variables from the analysis profile" for an empty
  submission. An endpoint that merged incoming entries into the existing
  set by `reference_key` would have no reason to describe an empty
  submission as a *deletion* — a merge of nothing changes nothing. The
  204's very existence is the confirming signal that this endpoint always
  replaces the entire list.

**The consequence:** if an Analysis Profile currently has Scanner
Variables `username`, `password`, and `otp`, and a caller calls `update()`
with a configuration listing only `username`, the result — per the real
API's own documented behavior — is an Analysis Profile with **only**
`username`. `password` and `otp` are gone, not "left unchanged."

**The design decision:** `ScannerVariablesService.update()` sends exactly
what `_validate()` produces from the caller's configuration — nothing
more, nothing less. It does **not**:

- Call `get()` internally first and merge the caller's entries into the
  existing set before sending the `PUT`.
- Warn, prompt, or refuse to proceed when the supplied list looks "smaller
  than expected" (there is no way to know what a caller "expected"; adding
  a heuristic here would be guessing at intent AGENTS.md §5 doesn't ask
  for).
- Diverge in this behavior between an empty and a non-empty `variables`
  list — both go through the exact same code path (§3.4, `update()`).

**Why not add an auto-merge convenience anyway?** Because it would trade
one problem for a worse one: silently reading and re-sending variables the
caller never mentioned means a value this SDK doesn't model (e.g.
`utilize_in_ai_assisted_login`, requirements.md §3.1.4) could be preserved
by accident in some code paths and dropped in others, depending on
implementation details invisible to the caller — a correctness landmine
strictly worse than the current, honest "you must list what you want to
keep" behavior. A caller who explicitly wants "add one variable without
touching the rest" can trivially compose it themselves: `get()`, add the
new entry to `.variables`, write it back out as SDK Configuration, then
`update()`. This feature does not need to build that composition in for
them (requirements.md §12.2) — no concrete consumer need for it has been
identified, and inventing it now would be the kind of speculative
convenience AGENTS.md §5 ("Simple") argues against.

**Where this is surfaced to a caller**, so the behavior is never a
surprise discovered in production:

1. README.md itself (unchanged, but its "Update Scanner Variables" steps
   are consistent with — not contradicted by — this behavior).
2. requirements.md §3.3.2 (a SHALL NOT, not just descriptive prose).
3. `ScannerVariablesService`'s and `update()`'s own docstrings (§3.4
   above).
4. This section.

---

## 9. Models

| OpenAPI schema | SDK model | Notes |
|---|---|---|
| `ScannerVariable` (as used inside a response) + `InheritableValue`'s `is_inherited` | `ScannerVariable` | Flattened — `is_inherited` folded onto the same class rather than kept as a generic wrapper (§3.1, requirements.md §4.4). |
| `EffectiveScannerVariables` | `ScannerVariables` | A bare list wrapper, no pagination, no extra IDs — the response has none to preserve. |
| `ScannerVariablesUpdateRequest` | `[ScannerVariable.to_api(), ...]` | Not modeled as a distinct request type — `to_api()` on the existing model already produces exactly this shape. |
| `ScannerVariableEvaluationMode` | *(not modeled)* | Represented only as the string literals `"RAW"`/`"TOTP"` inside `to_api()`/`from_api()` (§3.1). |
| `utilize_in_ai_assisted_login` | *(not modeled)* | Out of scope (requirements.md §3.1.4, §13.1). |

No model is defined for `Problem`, `ProblemError`, or `Link`
(requirements.md §4.4) — same rule as every prior Phase 2 feature.

---

## 10. Error Handling

| Condition | Exception | Raised by |
|---|---|---|
| `analysis_profile_id` blank | `ScannerVariableValidationError(rule="analysis_profile_id_required")` | `ScannerVariablesService.get`, `.update` (before any HTTP call) |
| Non-dict config / missing `variables` array / non-dict entry | `ScannerVariableValidationError` | `ScannerVariablesService._validate` |
| Missing/blank `reference_key` or `value` | `ScannerVariableValidationError` | `ScannerVariablesService._validate` |
| Duplicate `reference_key` | `ScannerVariableValidationError(rule="duplicate_reference_key")` | `ScannerVariablesService._validate` |
| Non-boolean `totp_seed` | `ScannerVariableValidationError(rule="invalid_totp_configuration")` | `ScannerVariablesService._validate` |
| `config_file` path does not exist | `ConfigFileNotFoundError` | `utils.sdk_config.load_json_config` (reused) |
| `config_file` is not valid JSON | `ConfigFileInvalidError` | `utils.sdk_config.load_json_config` (reused) |
| HTTP 401 | `VeracodeAuthenticationError` | `HttpClient` (unchanged) |
| HTTP 404 (unknown `analysis_profile_id`) | `VeracodeNotFoundError` | `HttpClient` (unchanged) |
| HTTP 500 | `VeracodeApiError` | `HttpClient` (unchanged) |

Client-side checks always raise before any HTTP call (requirements.md
§5); every HTTP Client exception propagates unmodified — same shape as
[scanners-profiles/design.md §9](../scanners-profiles/design.md#9-error-handling).

---

## 11. Testing Strategy

Location: `tests/models/test_scanner_variable.py`,
`tests/services/test_scanner_variables.py`. Same stub-`HttpClient`
approach as every other service — no mocking library, no real sockets;
real filesystem I/O only via `tmp_path` fixtures (reusing
`utils/sdk_config.py`'s already-tested Loader means this feature's own
Loader-path tests only need to confirm the import wiring, not re-test
`load_json_config()` itself).

Cases:

- `ScannerVariable.from_api` / `ScannerVariables.from_api`: round-trips a
  fixture shaped like requirements.md §0.2 (`effective_value` +
  `is_inherited`), including one entry with `evaluation_mode: "TOTP"`
  (→ `totp_seed=True`) and one with `evaluation_mode` absent (→
  `totp_seed=False`, the schema default); confirms `id` is carried through
  when present and `None` when absent.
- `ScannerVariable.to_api()`: `totp_seed=True` → `evaluation_mode:
  "TOTP"`; `totp_seed=False` → `evaluation_mode: "RAW"`; never includes
  `id` regardless of whether the instance has one set.
- `ScannerVariable(reference_key="username", value="admin",
  totp_seed=False)` constructs without `is_inherited`/`id` (README
  compatibility, requirements.md §3.1.2, §3.1.3).
- `ScannerVariablesService.get()`: blank `analysis_profile_id` →
  `ScannerVariableValidationError`, no HTTP call; 200 →
  correctly-built `ScannerVariables`; 404 → `VeracodeNotFoundError`
  propagates.
- `ScannerVariablesService.update()`:
  - blank `analysis_profile_id` → `ScannerVariableValidationError`, no
    HTTP call.
  - non-dict config, missing `variables` array, non-dict entry, missing
    `reference_key`, missing `value`, non-boolean `totp_seed`, duplicate
    `reference_key` → each their own `ScannerVariableValidationError(rule=...)`,
    no HTTP call.
  - the exact README "SDK Configuration" example → `PUT` body matches
    §7's transformation exactly (list order preserved); 200 → correctly
    built `ScannerVariables`.
  - a config listing fewer variables than an Analysis Profile currently
    has → the captured request body contains *only* the supplied entries
    (proves no read-then-merge occurs — requirements.md Acceptance
    Criterion 4).
  - `config_file={"variables": []}` + a stubbed 204 response → returns
    `ScannerVariables(variables=[])` without attempting to parse a body.
  - accepts both a `tmp_path` JSON file and an equivalent in-memory dict,
    asserting identical resulting request bodies.
  - 404 → `VeracodeNotFoundError` propagates unchanged.
- `caplog` assertion: across every test in this suite that exercises a
  real `value` (e.g. `"secret123"`, `"ABCDEFGHIJKLMNOP"`), no captured log
  record contains that string (requirements.md §8.3 — the strictest
  assertion in this feature's test suite).
- `VeracodeClient()` wiring: `client.scanner_variables` is a
  `ScannerVariablesService`, and its underlying `HttpClient` is the same
  object identity as `client.targets`'s.

---

## 12. Future Extensibility

This feature introduces no new shared module — it consumes
`utils/sdk_config.py` exactly as Scanner Profiles left it
(requirements.md §9.5, §9.6). A future Authentication Configuration or ISM
Gateway feature (README "Future Vision") can follow the same
`SDK Configuration → Loader → Validator → Transformer → HttpClient`
pipeline, reusing `load_json_config()` the same way this feature does,
without this feature changing.

The one pattern this feature adds that is *not* shared with Scanner
Profiles — a "does this endpoint replace or merge?" check (§8) — is worth
carrying forward as a design *question* (not shared code) for any future
configuration-driven feature: before assuming a `PUT` endpoint merges by
key, check whether the OpenAPI document describes an empty/partial
submission as a deletion, the same signal §8 relied on here.

No file in this feature (`models/scanner_variable.py`,
`services/scanner_variables.py`, the one new exception class) is written
to be generic — they are Scanner-Variable-specific, matching AGENTS.md §5
("Extensible — adding a new resource means adding a new service + model,
not touching the client or existing services").

---

## 13. File Layout Introduced by This Feature

```
src/veracode_dast/
├── models/scanner_variable.py       # ScannerVariable, ScannerVariables
├── services/scanner_variables.py    # ScannerVariablesService
├── client.py                        # (+) self.scanner_variables, sharing client.targets' HttpClient
└── exceptions.py                    # (+) ScannerVariableValidationError

tests/
├── models/test_scanner_variable.py
└── services/test_scanner_variables.py

examples/
└── scanner_variables_example.py

specs/scanner-variables/
└── scanner-variables.json           # sample SDK Configuration fixture, mirrors the README
```

No change to `utils/sdk_config.py` or `exceptions.py`'s existing
`ConfigFileNotFoundError`/`ConfigFileInvalidError` — those are consumed,
not extended.

---

## 14. Traceability

Maps each design component to the [requirements.md](requirements.md)
section(s) it satisfies.

| Component | Requirements covered |
|---|---|
| `ScannerVariablesService.get` | 3.2 |
| `ScannerVariablesService.update` | 3.3, 3.4 |
| `ScannerVariable`, `ScannerVariables` | 3.1.1–3.1.3, 4.1, 4.2 |
| No public `ScannerVariableEvaluationMode` | 3.1.1, 4.3 |
| `utils/sdk_config.load_json_config` (reused) | 9.5 |
| No `suggest_closest()` reuse | 6.3, 9.6 |
| `ScannerVariablesService._validate` | 5.1–5.8 |
| `ScannerVariableValidationError` | 6.1 |
| Full-replace semantics, no auto-merge | 3.3.2, §8 (this document) |
| 204 → `ScannerVariables(variables=[])` | 3.3.7 |
| Secrets never logged | 8.1–8.4 |
| Public interface, `HttpClient` reuse | 9.1–9.4 |
| Testing strategy | 10 (requirements.md), 11 (this document) |
