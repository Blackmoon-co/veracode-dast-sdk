# Design — Scanner Profiles

Implements [requirements.md](requirements.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Extends
[Target Management](../target-management/design.md) (reuses its base-URL
constant, same pattern as
[API Specification Management](../api-specification-management/design.md)).

---

## 1. Overview

The Scanner Profiles service manages which DAST security scanners are
enabled for an Analysis Profile. `get()` is a thin read — one HTTP call,
one model built from the response, the same shape as
`ApiSpecificationsService.get()`. `update()` is where this feature's real
complexity lives: turning a small SDK Configuration document into a
validated Veracode API request, entirely client-side, before any HTTP
call happens. [§2](#2-architecture) shows both shapes; the rest of this
document works through each stage of `update()`'s pipeline in turn.

## 2. Architecture

This feature adds one service and its models to the existing layered
architecture (AGENTS.md §3) — no new layer, no change to `HttpClient`:

```
VeracodeClient
      ↓
  HTTP Client        (reused, unmodified — no new capability needed)
      ↓
ScannersService       ← THIS FEATURE
      ↓
Scanner, ScannerProfile (models)
      ↓
  REST API  (DAST Target Configuration Service, same base URL as Targets)
```

Inside `ScannersService.update()`, the SDK Configuration document is
carried through four stages before the HTTP call:

```
SDK Configuration                 (scanner-profile.json, or an in-memory dict)
      ↓
Configuration Loader               load_json_config()
      ↓
Validator                          structure + known ScannerType names
      ↓
Transformer                        dict[str, bool]  →  ScannerProfileUpdateRequest shape
      ↓
HttpClient                         PUT /analysis_profiles/{id}/scanners
      ↓
Veracode API
```

Loader, Validator, and Transformer are plain functions, not classes — each
does one job, is independently unit-testable with no `HttpClient`
involved, and is composed by `ScannersService.update()`. Introducing a
class per stage would add indirection with no behavior gained; adding an
interface here would be the kind of unrequested abstraction AGENTS.md's
"Simple — the smallest client that solves the problem correctly"
principle warns against.

## 3. Components and Interfaces

### 3.1 `src/veracode_dast/models/scanner.py`

`ScannerType` uses `enum.StrEnum`, the same convention already established
by `models/target.py` (`TargetType`, `ScanType`, ...) and
`models/api_specification.py` (`ScopeType`, `ScopeRuleType`) — not
`class Foo(str, Enum)`.

```python
class ScannerType(StrEnum):
    FINGERPRINTING = "fingerprinting"
    SSL = "ssl"
    HTTP_HEADER = "http_header"
    PORTSCAN = "portscan"
    FUZZER = "fuzzer"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    FILE_INCLUSION = "file_inclusion"
    DESERIALIZATION = "deserialization"
    XXE = "xxe"
    COMMAND_INJECTION = "command_injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CSRF = "csrf"
    LDAP_INJECTION = "ldap_injection"
    COMMON_LOGIN = "common_login"
    TRACE_METHOD = "trace_method"
    CODE_INJECTION = "code_injection"
    UNSECURED_LOGIN = "unsecured_login"
    CLICKJACKING = "clickjacking"
    SSTI = "ssti"
    OBSOLETE_RESOURCE = "obsolete_resource"
    INSECURE_JWT = "insecure_jwt"
    BACKUP_FILE = "backup_file"
    ERROR_PATTERN = "error_pattern"
    OPEN_REDIRECT = "open_redirect"
    SSRF = "ssrf"
    WEBSERVER_DIR_LIST = "webserver_dir_list"
    HTTP_RESP_SPLIT = "http_resp_split"
    VIEW_STATE = "view_state"
    FILE_UPLOAD = "file_upload"
    FLASH = "flash"
    FILE_DIR_EXPOSURE = "file_dir_exposure"
    URL_SESSION = "url_session"
    STRUTS2 = "struts2"
    MALICIOUS_HOST = "malicious_host"


@dataclass(frozen=True)
class Scanner:
    id: str
    enabled: bool
    inherited: bool
    editable: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Scanner:
        """Maps the API's ScannerValue field names to the SDK's.

        `enabled` ← `effective_value`, `inherited` ← `is_inherited`,
        `editable` ← `is_editable` — the API's names are kept out of the
        public model (requirements.md §0.2), matching the README's
        `Scanner(id, enabled, inherited, editable)` shape exactly.
        """


@dataclass(frozen=True)
class ScannerProfile:
    scanners: list[Scanner] = field(default_factory=list)
    analysis_profile_id: str | None = None
    parent_analysis_profile_id: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ScannerProfile: ...
```

`analysis_profile_id`/`parent_analysis_profile_id` are real, always-present
fields of the API's `ScannerProfile` schema (requirements.md §0.2) and are
kept on the model since discarding server data the caller might want (e.g.
`parent_analysis_profile_id` to explain why a scanner is `inherited`)
would be a needless loss — but both default to `None` so the model can
still be constructed exactly as shown in
[README "Returned Model"](README.md#returned-model) (`ScannerProfile(scanners=[...])`),
keeping the spec consistent with the README's public example.

### 3.2 `src/veracode_dast/exceptions.py` (extended)

```python
class ScannerValidationError(VeracodeSDKError):
    """Raised for SDK-level Scanner Profile parameter/configuration
    validation failures (requirements.md §5.1–5.4).

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None: ...


class UnknownScannerError(VeracodeSDKError):
    """Raised when an SDK Configuration names a scanner outside the known
    ScannerType set (requirements.md §5.5).

    Attributes:
        scanner_id: The unrecognized name from the configuration.
        suggestion: The closest known ScannerType name, or None if no
            close match was found.
    """

    def __init__(self, scanner_id: str, *, suggestion: str | None) -> None:
        self.scanner_id = scanner_id
        self.suggestion = suggestion
        message = f"Unknown scanner '{scanner_id}'."
        if suggestion:
            message += f"\n\nDid you mean '{suggestion}'?"
        super().__init__(message)


class ConfigFileNotFoundError(VeracodeSDKError):
    """Raised when an SDK Configuration file path does not exist
    (requirements.md §5.6).

    Attributes:
        path: The file path that was not found.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"SDK Configuration file not found: {path}")


class ConfigFileInvalidError(VeracodeSDKError):
    """Raised when an SDK Configuration file's contents are not valid JSON
    (requirements.md §5.6).

    Attributes:
        path: The file path that failed to parse.
        reason: The underlying `json.JSONDecodeError` message.
    """

    def __init__(self, path: str, *, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"SDK Configuration file is not valid JSON: {path} ({reason})")
```

All four subclass `VeracodeSDKError` directly, never `VeracodeApiError` —
same convention as `TargetValidationError`/`ApiSpecificationValidationError`.
A dedicated `UnknownScannerError` (rather than folding this into
`ScannerValidationError(rule=...)`) is justified because it carries
structured data (`scanner_id`, `suggestion`) a caller may want to handle
programmatically (e.g. surfacing the suggestion in a CI log), not just a
formatted message. `ConfigFileNotFoundError`/`ConfigFileInvalidError` are
deliberately **not** named `Scanner...` — they belong to
`utils/sdk_config.py` (§3.3), not to this feature's resource, and are
raised the same way for every future configuration-driven module.

### 3.3 `src/veracode_dast/utils/sdk_config.py` (new, shared)

```python
def load_json_config(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Loads an SDK Configuration document.

    Args:
        source: A path to a JSON file, or an already-loaded dict.

    Returns:
        The parsed configuration as a dict.

    Raises:
        ConfigFileNotFoundError: If `source` is a path that does not exist.
        ConfigFileInvalidError: If the file's contents are not valid JSON.
    """
    if isinstance(source, dict):
        return source
    path = Path(source)
    if not path.is_file():
        raise ConfigFileNotFoundError(str(path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except json.JSONDecodeError as exc:
        raise ConfigFileInvalidError(str(path), reason=str(exc)) from exc


def suggest_closest(name: str, valid_names: Iterable[str]) -> str | None:
    """Returns the closest match to `name` among `valid_names`, or None.

    A thin wrapper over `difflib.get_close_matches` (stdlib) — no new
    dependency is justified for fuzzy string matching this simple.
    """
    matches = difflib.get_close_matches(name, list(valid_names), n=1)
    return matches[0] if matches else None
```

This module is intentionally resource-agnostic: it knows nothing about
scanners, `ScannerType`, or any Veracode schema. `ConfigFileNotFoundError`/
`ConfigFileInvalidError` are added to `exceptions.py` as generic,
non-resource-specific errors (subclassing `VeracodeSDKError` directly) —
`ScannersService.update()` catches neither; it lets the SDK Configuration
loading failure propagate as-is, since both are already
caller-actionable. See [§11](#11-future-extensibility) for why this
module exists as shared code rather than living inside
`services/scanners.py`.

### 3.4 `src/veracode_dast/services/scanners.py`

```python
from veracode_dast.services.targets import TARGET_CONFIGURATION_SERVICE_BASE_URL

_SCANNERS_PATH = "/analysis_profiles/{analysis_profile_id}/scanners"

logger = logging.getLogger(__name__)


class ScannersService:
    """Manages Scanner Profiles for existing Analysis Profiles."""

    def __init__(self, http_client: HttpClient) -> None: ...

    def get(self, analysis_profile_id: str) -> ScannerProfile: ...

    def update(
        self,
        analysis_profile_id: str,
        config_file: str | Path | dict[str, Any],
    ) -> ScannerProfile: ...
```

`TARGET_CONFIGURATION_SERVICE_BASE_URL` is **imported**, not redefined —
same rule already established by `services/api_specifications.py`.

`update()`:

```python
def update(
    self,
    analysis_profile_id: str,
    config_file: str | Path | dict[str, Any],
) -> ScannerProfile:
    self._require_non_blank(analysis_profile_id, rule="analysis_profile_id_required")

    config = load_json_config(config_file)
    scanners = self._validate(config)

    payload = {
        "scanners": [{"id": name, "value": value} for name, value in scanners.items()]
    }

    logger.info(
        "Updating scanner profile for analysis profile %s (%d scanner(s))",
        analysis_profile_id, len(scanners),
    )
    response = self._http_client.put(
        _SCANNERS_PATH.format(analysis_profile_id=analysis_profile_id),
        json=payload,
    )
    profile = ScannerProfile.from_api(response.data)  # type: ignore[arg-type]
    logger.info("Scanner profile updated for analysis profile %s", analysis_profile_id)
    return profile

@staticmethod
def _validate(config: dict[str, Any]) -> dict[str, bool]:
    if not isinstance(config, dict):
        raise ScannerValidationError(
            "SDK Configuration must be a JSON object", rule="config_must_be_object"
        )
    scanners = config.get("scanners")
    if not isinstance(scanners, dict):
        raise ScannerValidationError(
            "SDK Configuration must contain a 'scanners' object", rule="scanners_key_required"
        )
    known = {member.value for member in ScannerType}
    for name, value in scanners.items():
        if not isinstance(value, bool):
            raise ScannerValidationError(
                f"Scanner '{name}' value must be a boolean", rule="scanner_value_must_be_bool"
            )
        if name not in known:
            raise UnknownScannerError(name, suggestion=suggest_closest(name, known))
    return scanners
```

`get()` follows the established one-call, one-log-line shape (see
[api-specification-management/design.md §2.3](../api-specification-management/design.md#23-srcveracode_dastservicesapi_specificationspy)):

```python
def get(self, analysis_profile_id: str) -> ScannerProfile:
    self._require_non_blank(analysis_profile_id, rule="analysis_profile_id_required")
    response = self._http_client.get(
        _SCANNERS_PATH.format(analysis_profile_id=analysis_profile_id)
    )
    profile = ScannerProfile.from_api(response.data)  # type: ignore[arg-type]
    logger.info("Retrieved scanner profile for analysis profile %s", analysis_profile_id)
    return profile
```

## 4. Service Responsibilities

| Responsibility | Owner |
|---|---|
| HTTP transport, HMAC auth, retries, status→exception mapping | `HttpClient` (unchanged) |
| Loading SDK Configuration (file or dict) | `utils/sdk_config.load_json_config` |
| Structural validation (`scanners` key, boolean values) | `ScannersService._validate` |
| Scanner-name validation + "did you mean" suggestion | `ScannersService._validate` + `utils/sdk_config.suggest_closest` |
| SDK Configuration → API request transformation | `ScannersService.update` (inline dict comprehension — see §7) |
| Building typed models from API responses | `Scanner.from_api` / `ScannerProfile.from_api` |
| Business-event logging | `ScannersService` |

## 5. SDK Configuration Flow

1. Caller calls `client.scanners.update(analysis_profile_id, config_file)`.
2. `load_json_config()` returns a plain dict, whether `config_file` was a
   path or already a dict (requirements.md §3.2).
3. `_validate()` checks structure and scanner names, returning a plain
   `dict[str, bool]` of `{scanner_name: enabled}` on success.
4. The dict comprehension in `update()` builds the API request body.
5. `HttpClient.put()` sends the request; a non-2xx response raises the
   appropriate exception per [§9](#9-error-handling) and `update()` never
   catches it.
6. On 200, `ScannerProfile.from_api(response.data)` is returned.

This is exactly the six-step flow already documented in
[README "Update Scanner Profile"](README.md#update-scanner-profile).

## 6. Validation Flow

Two passes, both entirely local (no HTTP):

1. **Structural** — `config` is a dict; `config["scanners"]` is a dict;
   every value in it is a `bool` (requirements.md §5.2–5.4).
2. **Semantic (names only)** — every key in `config["scanners"]` is a
   member of `ScannerType` (requirements.md §5.5). On failure,
   `suggest_closest()` (stdlib `difflib.get_close_matches`, cutoff/`n`
   defaults) looks for a near match among the 35 known names and attaches
   it to `UnknownScannerError` if found.

Whether a given scanner is *appropriate* for the target's scan type is
explicitly **not** validated here (requirements.md §5.7) — that is
Veracode's own server-side rule, and duplicating it client-side would
require this SDK to track business logic that can change on Veracode's
side independently of this package's release cycle.

## 7. Transformation Layer

SDK Configuration → Veracode API request, exactly as shown in
[README "JSON Transformation"](README.md#json-transformation):

```python
# SDK Configuration (validated dict[str, bool])
{"sql_injection": True, "xss": True, "csrf": False}

# Veracode API request body (ScannerProfileUpdateRequest shape)
{
    "scanners": [
        {"id": "sql_injection", "value": True},
        {"id": "xss", "value": True},
        {"id": "csrf", "value": False},
    ]
}
```

Implemented as the single dict-comprehension in `update()` (§3.4) — a
dedicated `Transformer` class would add a layer with exactly one call
site and no independent state; a plain function/inline expression is the
smallest thing that solves this correctly (AGENTS.md §5 "Simple").
Dictionary key order is preserved (Python 3.7+ dict ordering), so the
generated request lists scanners in the same order the caller wrote them.

## 8. Models

Covered in [§3.1](#31-srcveracode_dastmodelsscannerpy). No separate
"SDK Configuration model" class is introduced — the configuration is a
plain `dict[str, Any]` end-to-end until transformation, since it has no
behavior of its own beyond validation (already owned by `_validate`).

## 9. Error Handling

| Failure | Exception | Raised by |
|---|---|---|
| Blank `analysis_profile_id` | `ScannerValidationError(rule="analysis_profile_id_required")` | `ScannersService` |
| `config_file` path does not exist | `ConfigFileNotFoundError` | `utils.sdk_config.load_json_config` |
| `config_file` is not valid JSON | `ConfigFileInvalidError` | `utils.sdk_config.load_json_config` |
| Config is not an object / missing `scanners` object / non-bool value | `ScannerValidationError` | `ScannersService._validate` |
| Unknown scanner name | `UnknownScannerError` | `ScannersService._validate` |
| HTTP 401 | `VeracodeAuthenticationError` | `HttpClient` (unchanged) |
| HTTP 404 (unknown `analysis_profile_id`) | `VeracodeNotFoundError` | `HttpClient` (unchanged) |
| HTTP 422 (Veracode scanner-eligibility rule, if ever returned) | `VeracodeValidationError` | `HttpClient` (unchanged) |
| HTTP 500 | `VeracodeApiError` | `HttpClient` (unchanged) |

Client-side checks always raise before any HTTP call (requirements.md
§5); every HTTP Client exception propagates unmodified — same shape as
[api-specification-management/design.md §4](../api-specification-management/design.md#4-error-handling).

## 10. Testing Strategy

Location: `tests/models/test_scanner.py`, `tests/utils/test_sdk_config.py`,
`tests/services/test_scanners.py`. Same stub-`HttpClient` approach as
Target/Team/API Specification Management — no mocking library, no real
sockets; real filesystem I/O only via `tmp_path` fixtures.

Cases:

- `Scanner.from_api` / `ScannerProfile.from_api`: field-name mapping
  (`effective_value`→`enabled`, `is_inherited`→`inherited`,
  `is_editable`→`editable`) round-trips against a fixture shaped like
  §0.2; `ScannerProfile(scanners=[...])` constructs without the two
  optional ID fields (README compatibility, §3.1).
- `load_json_config`: dict passthrough; valid file path → parsed dict;
  missing path → `ConfigFileNotFoundError`; malformed JSON →
  `ConfigFileInvalidError`.
- `suggest_closest`: `"sql"` against the 35 `ScannerType` values →
  `"sql_injection"`; a name with no close match → `None`.
- `ScannersService.get()`: blank `analysis_profile_id` →
  `ScannerValidationError`, no HTTP call; 200 → `ScannerProfile`; 404 →
  `VeracodeNotFoundError` propagates.
- `ScannersService.update()`:
  - blank `analysis_profile_id` → `ScannerValidationError`, no HTTP call.
  - non-dict config, missing `scanners` key, non-bool value → each their
    own `ScannerValidationError(rule=...)`, no HTTP call.
  - `{"scanners": {"sql": true}}` → `UnknownScannerError` with
    `suggestion == "sql_injection"`, no HTTP call (reproduces README
    "Validation" verbatim).
  - the exact README "SDK Configuration Format" example → `PUT` body
    equals the exact README "JSON Transformation" example; 200 →
    `ScannerProfile`.
  - accepts both a `tmp_path` JSON file and an equivalent in-memory dict,
    asserting identical resulting request bodies.
  - 404 → `VeracodeNotFoundError` propagates unchanged.
- `caplog` assertion: no captured log record contains the full scanner
  configuration payload beyond the scanner count already logged (§3.4).

## 11. Future Extensibility

`utils/sdk_config.py` (§3.3) is deliberately the *only* new shared module
this feature introduces, and it is scoped to exactly two operations every
configuration-driven module needs: loading a JSON document from a path-or-dict,
and suggesting a close match for an unrecognized key. Per
[README "Future Vision"](README.md#future-vision), Authentication, Scanner
Variables, and ISM Gateway configuration are expected to follow the same
`SDK Configuration → Loader → Validator → Transformer → HttpClient`
pipeline described in [§2](#2-architecture) — each future service:

- Reuses `load_json_config()` unchanged.
- Reuses `suggest_closest()` against its own closed name set (form field
  names, scanner variable keys, gateway option names).
- Defines its own `<Feature>ValidationError`/`Unknown<Feature>Error`
  pair, following the same two-exception convention as §3.2.
- Defines its own `_validate`/transformation dict-comprehension, since
  each resource's structural rules differ enough that a shared
  `Validator`/`Transformer` base class would need per-resource overrides
  for nearly every method — i.e., no real logic would be shared, only an
  empty interface. That is exactly the kind of interface-with-one-real-
  implementation AGENTS.md's "Simple"/"Extensible" principles (§5) argue
  against; it is not introduced here.

No other file in this feature (`models/scanner.py`,
`services/scanners.py`, the two exception classes) is written to be
generic — they are Scanner-Profile-specific, matching AGENTS.md §5
("Extensible — adding a new resource means adding a new service + model,
not touching the client or existing services").

## 12. File Layout Introduced by This Feature

```
src/veracode_dast/
├── models/scanner.py           # ScannerType, Scanner, ScannerProfile
├── services/scanners.py        # ScannersService
├── utils/sdk_config.py         # load_json_config, suggest_closest (new shared module)
├── client.py                   # (+) self.scanners, sharing client.targets' HttpClient
└── exceptions.py               # (+) ScannerValidationError, UnknownScannerError,
                                 #     ConfigFileNotFoundError, ConfigFileInvalidError

tests/
├── models/test_scanner.py
├── utils/test_sdk_config.py
└── services/test_scanners.py

examples/
└── scanner_profiles_example.py

specs/scanners-profiles/
└── scanner-profile.json        # sample SDK Configuration fixture, mirrors the README
```

## 13. Traceability

Maps each design component to the [requirements.md](requirements.md)
section(s) it satisfies.

| Component | Requirements covered |
|---|---|
| `ScannersService.get` | 3.1, 3.6 |
| `ScannersService.update` | 3.2–3.6 |
| `ScannerType`, `Scanner`, `ScannerProfile` | §0.2 |
| `utils/sdk_config.load_json_config` | 3.2, 5.6 |
| `utils/sdk_config.suggest_closest` | 5.5 |
| `ScannersService._validate` | 5.1–5.5 |
| `ScannerValidationError`, `UnknownScannerError`, `ConfigFileNotFoundError`, `ConfigFileInvalidError` | 5.1–5.6 |
| No server-side scanner-eligibility replication | 5.7, §7 (Out of Scope) |
| Public interface, `HttpClient` reuse | §2 (Goals), 4.3 |
| Reuse for future modules | §9 (Reuse for future configuration-driven modules) |
| Testing strategy | §8 (Testability) |
