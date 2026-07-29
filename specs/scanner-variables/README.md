# Scanner Variables

The Scanner Variables service manages runtime variables used by Veracode DAST during authenticated scans.

Scanner Variables provide values that can be consumed by authentication mechanisms such as login scripts and multi-factor authentication (MFA). They allow authentication workflows to reference configurable values instead of hardcoded credentials or secrets.

Unlike the Veracode REST API, which exposes raw request models, this SDK provides a simplified configuration format. The SDK validates the configuration, transforms it into the appropriate API request, and applies the changes automatically.

> **Phase:** 2 - Target Configuration

---

# Features

- Retrieve Scanner Variables
- Update Scanner Variables using an SDK configuration file
- Validate configuration before sending requests
- Automatically transform SDK configuration into the Veracode API request
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

Scanner Variables are configured using a simple JSON document.

Example (`scanner-variables.json`):

```json
{
  "variables": [
    {
      "reference_key": "username",
      "value": "admin"
    },
    {
      "reference_key": "password",
      "value": "secret123"
    },
    {
      "reference_key": "otp",
      "value": "ABCDEFGHIJKLMNOP",
      "totp_seed": true
    }
  ]
}
```

This format is designed to be:

- Easy to read
- Easy to maintain
- Version-control friendly
- Independent of the Veracode OpenAPI specification

---

# Get Scanner Variables

Retrieve the Scanner Variables configured for an Analysis Profile.

```python
variables = client.scanner_variables.get(
    analysis_profile_id="analysis_profile_id"
)

for variable in variables.variables:
    print(variable.reference_key)
    print(variable.value)
```

---

# Update Scanner Variables

Apply Scanner Variables using an SDK configuration file.

```python
client.scanner_variables.update(
    analysis_profile_id="analysis_profile_id",
    config_file="scanner-variables.json"
)
```

During execution the SDK will:

1. Read the configuration file.
2. Validate the configuration.
3. Transform the configuration into the Veracode API request.
4. Submit the request.
5. Return the updated Scanner Variables.

---

# Runtime Variables

Scanner Variables provide runtime values that can be consumed by authentication mechanisms during an analysis.

Typical examples include:

- Login script variables
- Multi-factor authentication (TOTP) secrets
- Runtime credentials
- Authentication tokens
- Values referenced during authenticated scans

The SDK stores and manages these values but does not interpret or process them.

---

# Configuration Transformation

### SDK Configuration

```json
{
  "variables": [
    {
      "reference_key": "username",
      "value": "admin"
    },
    {
      "reference_key": "password",
      "value": "secret123"
    }
  ]
}
```

### Generated API Request

The SDK automatically converts the configuration into the request model expected by the Veracode Target Configuration Service.

Users never need to build the API request manually.

---

# Validation

Configuration files are validated before any API request is made.

Examples include:

- Missing reference keys
- Duplicate variables
- Missing values
- Invalid TOTP configuration
- Invalid configuration structure

The SDK provides descriptive validation errors before contacting the Veracode API.

---

# Returned Model

```python
ScannerVariables
```

Example:

```python
ScannerVariables(
    variables=[
        ScannerVariable(
            reference_key="username",
            value="admin",
            totp_seed=False
        ),
        ScannerVariable(
            reference_key="otp",
            value="ABCDEFGHIJKLMNOP",
            totp_seed=True
        )
    ]
)
```

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

| Method | Endpoint |
|---------|----------|
| GET | `/analysis_profiles/{analysis_profile_id}/scanner_variables` |
| PUT | `/analysis_profiles/{analysis_profile_id}/scanner_variables` |

---

# Relationship with Authentication

Scanner Variables complement the Authentication service.

Authentication defines **how** Veracode authenticates to the application.

Scanner Variables provide the runtime values consumed by authentication mechanisms such as login scripts and multi-factor authentication.

Although they are closely related, they are managed as independent services by the Veracode API and therefore by this SDK.

---

# Design Philosophy

Users configure Scanner Variables using the SDK configuration format rather than Veracode API request models.

The SDK is responsible for:

- Reading configuration files
- Validating configuration
- Transforming configuration into the Veracode API request
- Communicating with the Veracode API
- Returning strongly typed Python models

Users should never need to construct the Veracode request models manually.

---

# Future Vision

Scanner Variables are one part of the complete DAST target configuration.

Future releases will allow multiple configuration services to be managed together, including:

- Analysis Profiles
- Scanner Profiles
- Authentications
- ISM Gateways

while preserving each service as an independent SDK component.

---

# Related Services

Typical workflow:

```python
client.authentications.update(
    analysis_profile_id="analysis_profile_id",
    config_file="authentication.json"
)

client.scanner_variables.update(
    analysis_profile_id="analysis_profile_id",
    config_file="scanner-variables.json"
)
```

Scanner Variables integrate closely with:

- Analysis Profiles
- Authentications
- Login Scripts
- Multi-Factor Authentication (MFA)