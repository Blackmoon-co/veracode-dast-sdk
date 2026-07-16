# Requirements — Authentication Infrastructure

Source context: [README.md](README.md). Architecture and conventions:
[AGENTS.md](../../AGENTS.md).

Format: user story + EARS-style acceptance criteria per requirement.

---

## 1. Environment-based credential loading

**User story:** As an SDK consumer, I want the SDK to read Veracode
credentials from environment variables, so that I can authenticate without
passing secrets through code or config files.

**Acceptance criteria:**

1.1. WHEN credentials are loaded THEN THE SYSTEM SHALL read the value of
`VERACODE_API_KEY_ID` from the process environment.

1.2. WHEN credentials are loaded THEN THE SYSTEM SHALL read the value of
`VERACODE_API_KEY_SECRET` from the process environment.

1.3. THE SYSTEM SHALL NOT read credentials from any source other than
environment variables (no config files, no constructor arguments, no secret
vaults, no `.env` file parsing).

---

## 2. Credential validation

**User story:** As an SDK consumer, I want a clear, early error if my
credentials are missing, so I can fix my environment before any API call is
attempted.

**Acceptance criteria:**

2.1. IF `VERACODE_API_KEY_ID` is unset or an empty string THEN THE SYSTEM
SHALL raise `MissingCredentialsError` before an authentication provider is
created.

2.2. IF `VERACODE_API_KEY_SECRET` is unset or an empty string THEN THE
SYSTEM SHALL raise `MissingCredentialsError` before an authentication
provider is created.

2.3. IF both `VERACODE_API_KEY_ID` and `VERACODE_API_KEY_SECRET` are unset
or empty THEN THE SYSTEM SHALL raise a single `MissingCredentialsError`
whose message names both missing variables.

2.4. WHEN both variables are present and non-empty THEN THE SYSTEM SHALL
treat the credentials as valid and proceed. Phase 1 SHALL NOT perform any
format, length, or checksum validation of the credential values themselves.

---

## 3. Authentication provider creation

**User story:** As a future SDK component (HTTP client, services), I want a
ready-to-use `requests`-compatible auth object, so that I can attach it to
outgoing requests without knowing how HMAC signing works.

**Acceptance criteria:**

3.1. WHEN valid credentials are available THEN THE SYSTEM SHALL create an
instance of `RequestsAuthPluginVeracodeHMAC` (from
`veracode_api_signing.plugin_requests`), passing the API key ID and API key
secret.

3.2. THE SYSTEM SHALL NOT implement any custom HMAC signing algorithm.

3.3. THE SYSTEM SHALL return the created authentication provider as a plain
value from a function call (no module-level singleton, no hidden global
state), so it can be passed directly as the `auth=` argument of a `requests`
call.

3.4. THE SYSTEM SHALL NOT import the `requests` library. The object this
feature returns happens to be usable as the `auth=` argument of a
`requests` call because `veracode-api-signing` designed it that way — this
feature depends only on `veracode_api_signing.plugin_requests`, never on
`requests` itself.

---

## 4. Exception hierarchy

**User story:** As an SDK consumer or maintainer, I want authentication
failures to raise specific, catchable exception types, so that error
handling can distinguish auth problems from other SDK errors.

**Acceptance criteria:**

4.1. THE SYSTEM SHALL define a root exception `VeracodeSDKError(Exception)`.

4.2. THE SYSTEM SHALL define `VeracodeAuthError(VeracodeSDKError)` for
authentication-related failures.

4.3. THE SYSTEM SHALL define `MissingCredentialsError(VeracodeAuthError)`
for missing or empty required credential environment variables.

4.4. WHEN `MissingCredentialsError` is raised THEN its message SHALL name
the missing environment variable(s) by name (e.g.
`"VERACODE_API_KEY_ID"`), and SHALL NOT include any credential value.

---

## 5. Secret handling

**User story:** As a security-conscious SDK consumer, I want a guarantee
that my credentials are never written to logs, disk, or error output, so
that adopting the SDK doesn't introduce a new way to leak secrets.

**Acceptance criteria:**

5.1. THE SYSTEM SHALL NOT log the value of `VERACODE_API_KEY_ID` or
`VERACODE_API_KEY_SECRET` at any log level.

5.2. THE SYSTEM SHALL NOT persist credentials to disk, cache, or any
temporary storage.

5.3. THE SYSTEM SHALL NOT include credential values in any exception
message or stack trace raised by this feature.

5.4. WHEN credential loading or authentication provider creation completes
a step THEN THE SYSTEM SHALL emit a DEBUG-level log message describing the
event only (e.g. `"Veracode credentials loaded from environment"`,
`"Veracode HMAC authentication provider created"`), with no credential
values interpolated into the message.

---

## 6. Boundaries (non-goals for this feature)

**User story:** As the SDK architect, I want this feature strictly scoped
to authentication setup, so that unrelated functionality doesn't creep into
the first implemented module.

**Acceptance criteria:**

6.1. THE SYSTEM SHALL NOT perform any HTTP request or network call as part
of this feature.

6.2. THE SYSTEM SHALL NOT implement Target, Analysis Profile, Scanner,
Analysis, or Report functionality as part of this feature.

6.3. THE SYSTEM SHALL NOT implement alternative authentication mechanisms
(Bearer Token, OAuth, API Keys, SRM.js) as part of this feature.

6.4. THE SYSTEM SHALL NOT require credentials to be passed through the
`VeracodeClient` constructor or any other public constructor.

6.5. THE SYSTEM SHALL NOT implement the HTTP client, `VeracodeClient`,
or any SDK service in this feature. Those consume this feature's output in
a later feature.

6.6. THE SYSTEM SHALL NOT accept, store, or reference any base URL,
endpoint path, or Veracode-service-specific configuration. Veracode
exposes multiple REST APIs under different base URLs (e.g. the AppSec API
and the DAST Target Configuration Service) that all share this same HMAC
mechanism; the auth provider this feature produces must be reusable,
unmodified, by an `HttpClient` instance targeting any of them. Base URL
ownership belongs to the HTTP client / service layer, never to this
feature.

6.7. THE SYSTEM SHALL NOT import or use the `requests` library, and SHALL
NOT execute any HTTP request, directly or indirectly, in this feature's own
code. This feature is a thin wrapper around the official
`veracode-api-signing` library: its only non-stdlib import is
`RequestsAuthPluginVeracodeHMAC` from `veracode_api_signing.plugin_requests`;
its only stdlib imports are `os` (reading environment variables),
`dataclasses` (`VeracodeCredentials`), and `logging`.

---

## 7. Public interface and reuse

**User story:** As a maintainer of a future SDK module (HTTP client,
Targets service, etc.), I want a simple, dependency-free way to obtain an
auth provider, so I can reuse it without coupling to Azure DevOps or any
specific consumer.

**Acceptance criteria:**

7.1. THE SYSTEM SHALL expose credential loading and auth provider creation
as plain, stateless functions (not classes requiring instantiation or
lifecycle management).

7.2. Every public function and class introduced by this feature SHALL have
complete type hints and a Google-style docstring.

7.3. THE SYSTEM SHALL NOT introduce any dependency on Azure DevOps, a CLI,
or any other specific consumer.

7.4. THE SYSTEM SHALL produce a single auth provider instance per call that
is valid for requests to any Veracode API base URL; a caller SHALL be able
to attach the same provider to `HttpClient` instances configured with
different base URLs (e.g. AppSec API, DAST Target Configuration Service)
without calling this feature's functions again or modifying them.

---

## 8. Testability

**User story:** As a maintainer, I want to verify credential loading and
auth provider creation without real Veracode credentials or network access,
so that the test suite is fast and runs anywhere.

**Acceptance criteria:**

8.1. THE SYSTEM SHALL allow credential loading to be fully tested by
setting/unsetting environment variables within a test process (e.g. via
`pytest`'s `monkeypatch`), with no network access required.

8.2. THE SYSTEM SHALL allow authentication provider creation to be tested
by inspecting the attributes of the resulting `RequestsAuthPluginVeracodeHMAC`
instance, without mocking or reimplementing the official
`veracode-api-signing` library.

8.3. THE SYSTEM SHALL NOT require any real Veracode account, API key, or
network connectivity to run its test suite.
