# Design — API Specification Management

Implements [requirements.md](requirements.md), within the architecture and
conventions defined in [AGENTS.md](../../AGENTS.md). Extends
[Target Management](../target-management/design.md) (reuses its base-URL
constant) and depends on the
[HTTP Client's multipart/raw amendment](../http-client/design.md#amendment-multipart-upload-and-raw-binary-responses).

---

## 1. Overview

```
VeracodeClient
      ↓
  HTTP Client        (reused, unmodified interface — files=/raw= already exist)
      ↓
ApiSpecificationsService   ← THIS FEATURE
      ↓
ApiSpecification, ScopeRule (models)
      ↓
  REST API  (DAST Target Configuration Service, same base URL as Targets)
```

This feature adds one Service and its models. It owns no Target lifecycle
logic and constructs no `HttpClient` of its own — it receives the same
`HttpClient` instance already wired to `client.targets`, since both target
the same base URL.

## 2. Components and Interfaces

### 2.1 `src/veracode_dast/models/api_specification.py`

```python
class ScopeType(str, Enum):
    AUDIT = "AUDIT"
    BLOCK = "BLOCK"
    IGNORE = "IGNORE"


class ScopeRuleType(str, Enum):
    PATTERN = "PATTERN"
    INDEX = "INDEX"


@dataclass(frozen=True)
class ScopeRule:
    uuid: str
    http_method: str
    url: str
    scope_type: ScopeType
    scope_rule_type: ScopeRuleType
    scope_rule_index: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "ScopeRule": ...


@dataclass(frozen=True)
class ApiSpecification:
    target_id: str
    api_spec_s3_id: str | None = None
    api_spec_name: str | None = None
    api_spec_url: str | None = None
    api_spec_type: str | None = None
    analysis_run_id: str | None = None
    uploaded_at: str | None = None
    updated_at: str | None = None
    uploaded_by: str | None = None
    updated_by: str | None = None
    scope_rules: list[ScopeRule] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any], *, target_id: str) -> "ApiSpecification":
        """Builds from the API response, falling back to the caller-supplied
        ``target_id`` if the response omits it (requirements.md §0.6)."""
```

`from_api` takes `target_id` as an explicit keyword rather than trusting the
response body to always include it, since §0.6 of requirements.md
documents that the OpenAPI schema for this response is internally
inconsistent and unconfirmed by any example payload.

### 2.2 `src/veracode_dast/exceptions.py` (extended)

```python
class ApiSpecificationValidationError(VeracodeSDKError):
    """Raised for SDK-level parameter validation failures.

    Attributes:
        rule: A short identifier of which validation rule failed.
    """

    def __init__(self, message: str, *, rule: str) -> None: ...


class ApiSpecificationFileNotFoundError(VeracodeSDKError):
    """Raised when `upload()`'s local file path does not exist.

    Attributes:
        path: The file path that was not found.
    """

    def __init__(self, message: str, *, path: str) -> None: ...
```

Same convention as `TargetValidationError`/`TargetNotFoundError` and
`TeamValidationError`/`TeamNotFoundError`: subclass `VeracodeSDKError`
directly, never `VeracodeApiError`.

### 2.3 `src/veracode_dast/services/api_specifications.py`

```python
from veracode_dast.services.targets import TARGET_CONFIGURATION_SERVICE_BASE_URL

_SPEC_PATH = "/targets/{target_id}/spec"
_SPEC_DOWNLOAD_PATH = "/targets/{target_id}/spec/download"


class ApiSpecificationsService:
    """Manages API Specifications for existing DAST API Targets."""

    def __init__(self, http_client: HttpClient) -> None: ...

    def upload(self, target_id: str, file_path: str | Path) -> ApiSpecification: ...

    def get(self, target_id: str) -> ApiSpecification: ...

    def download(self, target_id: str, destination_path: str | Path) -> Path: ...
```

`TARGET_CONFIGURATION_SERVICE_BASE_URL` is **imported**, not redefined —
this module never hardcodes a Veracode API base URL of its own (matching
the rule already established by `services/targets.py`).

`upload()`:

```python
def upload(self, target_id: str, file_path: str | Path) -> ApiSpecification:
    self._require_non_blank(target_id, rule="target_id_required")
    path = Path(file_path)
    if not path.is_file():
        raise ApiSpecificationFileNotFoundError(
            f"API specification file not found: {path}", path=str(path)
        )
    self._logger.info("Uploading API specification for target %s: %s", target_id, path.name)
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    response = self._http_client.post(
        _SPEC_PATH.format(target_id=target_id),
        files={"specFile": (path.name, path.read_bytes(), content_type)},
    )
    spec = ApiSpecification.from_api(response.data, target_id=target_id)  # type: ignore[arg-type]
    self._logger.info("Upload completed for target %s: %s", target_id, spec.api_spec_name)
    return spec
```

`get()` and `download()` follow the same shape: a blank-`target_id` guard,
one HTTP call, one log statement on success. `download()` calls
`self._http_client.get(_SPEC_DOWNLOAD_PATH.format(target_id=target_id), raw=True)`,
then `Path(destination_path).write_bytes(response.data)` (`response.data` is
`bytes` when `raw=True`, per the HTTP Client amendment).

## 3. REST ↔ SDK Mapping

| SDK method | HTTP call | Success | Failure |
|---|---|---|---|
| `upload(target_id, file_path)` | `POST /targets/{target_id}/spec` (multipart, field `specFile`) | 200 → `ApiSpecification` | 400 → `VeracodeValidationError`; 404 → `VeracodeNotFoundError` |
| `get(target_id)` | `GET /targets/{target_id}/spec` | 200 → `ApiSpecification` | 404 → `VeracodeNotFoundError` |
| `download(target_id, destination_path)` | `GET /targets/{target_id}/spec/download` (`raw=True`) | 200 → bytes written to `destination_path`, `Path` returned | 404 → `VeracodeNotFoundError` |

## 4. Error Handling

Identical shape to
[target-management/design.md §6](../target-management/design.md#6-error-handling):
client-side checks raise before any HTTP call; every HTTP Client exception
propagates unmodified.

## 5. Logging

Business events only, per requirements.md §7 — HTTP-level request/response
logging remains the HTTP Client's sole responsibility (no duplicate logging
in this service, matching the convention documented in
[http-client/design.md §5](../http-client/design.md#5-logging)).

## 6. Security Considerations

- File contents (uploaded or downloaded) are never logged or serialized
  beyond the HTTP request/response bodies themselves.
- `destination_path` is caller-supplied; this feature writes exactly there
  via `Path.write_bytes`, performing no path traversal resolution beyond
  what `pathlib` does by default — the caller is trusted the same way
  Target Management trusts caller-supplied business data (README "never
  duplicates server-side validation").

## 7. Testing Strategy

Location: `tests/models/test_api_specification.py`,
`tests/services/test_api_specifications.py`. Same stub-`HttpClient`
approach as Target/Team Management — no mocking library, no real sockets.

Cases:

- `ScopeRule.from_api` / `ApiSpecification.from_api` round-trip fixtures;
  `ApiSpecification.from_api` falls back to the supplied `target_id` when
  absent from the response.
- `upload()`: blank `target_id` → `ApiSpecificationValidationError`, no
  HTTP call; missing local file → `ApiSpecificationFileNotFoundError`, no
  HTTP call; valid input → `files=` sent with field name `specFile`,
  correct filename/bytes; 200 → `ApiSpecification`; 400 → propagates as
  `VeracodeValidationError`.
- `get()`: blank `target_id` → `ApiSpecificationValidationError`; 200 →
  `ApiSpecification`; 404 → `VeracodeNotFoundError` propagates.
- `download()`: blank `target_id` → `ApiSpecificationValidationError`;
  missing parent directory → `ApiSpecificationValidationError`; stubbed
  `raw=True` response with `data=b"..."` → bytes written to a `tmp_path`
  file and the same bytes read back; 404 → `VeracodeNotFoundError`
  propagates.
- `caplog` assertion: no captured log record contains file contents.

## 8. File Layout Introduced by This Feature

```
src/veracode_dast/
├── models/api_specification.py   # ScopeType, ScopeRuleType, ScopeRule, ApiSpecification
├── services/api_specifications.py   # ApiSpecificationsService
├── client.py    # (+) self.api_specifications, sharing client.targets' HttpClient
└── exceptions.py  # (+) ApiSpecificationValidationError, ApiSpecificationFileNotFoundError

tests/
├── models/test_api_specification.py
└── services/test_api_specifications.py

examples/
├── api_specification_management_example.py
└── end_to_end_workflow_example.py   # get_by_name -> create -> upload -> get, the task's MVP workflow
```

## 9. Traceability

| Component | Requirements covered |
|---|---|
| `ApiSpecificationsService.upload` | 1.1–1.7 |
| `ApiSpecificationsService.get` | 2.1–2.4 |
| `ApiSpecificationsService.download` | 3.1–3.5 |
| `ScopeType`, `ScopeRuleType`, `ScopeRule`, `ApiSpecification` | 4.1–4.4 |
| Client-side validation | 5.1 |
| `ApiSpecificationValidationError`, `ApiSpecificationFileNotFoundError` | 6.1–6.3 |
| Logging | 7.1–7.5 |
| No Team Management dependency, no `requests`/HMAC | 8 |
| Public interface, `HttpClient` reuse | 9 |
| Testing strategy | 10 |
