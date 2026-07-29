# Authentications

The Authentications service manages the authentication methods associated with a Veracode DAST Analysis Profile.

Authentication allows Veracode DAST to access protected areas of an application during security analysis. Multiple authentication mechanisms are supported, including HTTP Basic Authentication, Parameter Authentication, OAuth 2.0, Client Certificates, Login Scripts, and Scriptable Request Modification.

Unlike the Veracode REST API, which exposes low-level request models, this SDK provides a simplified, configuration-driven interface. The SDK validates configuration, transforms it into the appropriate Veracode API requests, and manages the authentication lifecycle automatically.

> **Phase:** 2 - Target Configuration

---

# Features

- Retrieve Authentication configuration
- Update Authentication configuration using an SDK configuration file
- Support multiple authentication mechanisms
- Validate configuration before sending requests
- Automatically transform SDK configuration into Veracode API requests
- Strongly typed models
- Full type hints
- HMAC authentication
- Unit tested

---

# Installation

```python
from veracode_dast import VeracodeClient

client = VeracodeClient()
```

`VeracodeClient` takes no arguments — it reads `VERACODE_API_KEY_ID` and
`VERACODE_API_KEY_SECRET` from the environment automatically.

---

# SDK Configuration

Authentication is configured using a simple JSON document.

Example (`authentication.json`):

```json
{
  "authentication": {
    "type": "basic",
    "username": "admin",
    "password": "secret123"
  }
}
```

Example using OAuth 2.0:

```json
{
  "authentication": {
    "type": "oauth2",
    "grant_type": "client_credentials",
    "token_url": "https://example.com/oauth/token",
    "client_id": "client-id",
    "client_secret": "client-secret"
  }
}
```

The SDK configuration is intentionally independent of the Veracode REST API models.

---

# Get Authentication

Retrieve the authentication configuration associated with an Analysis Profile.

```python
authentication = client.authentications.get(
    analysis_profile_id="analysis_profile_id"
)

print(authentication.type)
```

---

# Update Authentication

Apply authentication settings using an SDK configuration file.

```python
client.authentications.update(
    analysis_profile_id="analysis_profile_id",
    config_file="authentication.json"
)
```

During execution the SDK will:

1. Read the configuration file.
2. Validate the configuration.
3. Transform the configuration into the Veracode API request.
4. Submit the request.
5. Return the updated Authentication configuration.

---

# Supported Authentication Types

The SDK supports the authentication mechanisms provided by the Veracode Target Configuration Service.

Examples include:

- HTTP Basic Authentication
- Parameter Authentication
- OAuth 2.0
- Client Certificate Authentication
- Login Script Authentication
- Scriptable Request Modification

Support for additional authentication mechanisms will follow future Veracode API enhancements.

---

# Configuration Transformation

### SDK Configuration

```json
{
  "authentication": {
    "type": "basic",
    "username": "admin",
    "password": "secret123"
  }
}
```

### Generated API Request

The SDK automatically transforms the SDK configuration into the request model required by the Veracode Target Configuration Service.

Users never construct Veracode API payloads manually.

---

# Validation

Configuration files are validated before any API request is made.

Examples include:

- Missing authentication type
- Missing required credentials
- Invalid authentication type
- Invalid OAuth configuration
- Missing certificate information
- Invalid configuration structure

Validation occurs before contacting the Veracode API.

---

# Returned Model

```python
Authentication
```

Example:

```python
Authentication(
    type="basic",
    username="admin"
)
```

Sensitive information such as passwords, client secrets, certificates, or tokens should never be exposed by the SDK models or logs.

---

# Exceptions

The service may raise:

- AuthenticationError
- AuthorizationError
- ValidationError
- NotFoundError
- ApiError

---

# API Endpoints

The Authentication service communicates with the Veracode Target Configuration Service Authentication endpoints.

The SDK abstracts these endpoints and their request models from the user.

---

# Relationship with Scanner Variables

Authentication and Scanner Variables complement each other.

Authentication defines **how** Veracode authenticates to the application.

Scanner Variables provide runtime values that may be consumed by authentication mechanisms such as Login Scripts or Multi-Factor Authentication (TOTP).

Both services are independent within the SDK while working together during authenticated scans.

---

# Design Philosophy

Users configure authentication using SDK configuration files rather than Veracode REST request models.

The SDK is responsible for:

- Reading configuration files
- Validating configuration
- Transforming configuration into Veracode API requests
- Communicating with the Veracode API
- Returning strongly typed Python models

Users should never construct Veracode REST request models manually.

---

# Future Vision

Authentication is one component of the complete DAST Target Configuration workflow.

Future SDK releases will integrate Authentication with:

- Analysis Profiles
- Scanner Profiles
- Scanner Variables
- ISM Gateways

while preserving each module as an independent SDK service.

---

# Related Services

Typical workflow:

```python
client.analysis_profiles.update(
    profile_id,
    config_file="analysis-profile.json"
)

client.authentications.update(
    profile_id,
    config_file="authentication.json"
)

client.scanner_variables.update(
    profile_id,
    config_file="scanner-variables.json"
)
```

Authentication integrates closely with:

- Analysis Profiles
- Scanner Variables
- Authenticated Scanning
- Login Scripts
- OAuth 2.0
- Multi-Factor Authentication (MFA)