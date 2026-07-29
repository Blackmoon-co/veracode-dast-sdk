# Scanner Profiles

The Scanner Profiles service manages the security scanners enabled for a Veracode DAST Analysis Profile.

Unlike the Veracode REST API, which requires OpenAPI request models, this SDK uses a simplified JSON configuration format. The SDK validates the configuration, transforms it into the appropriate API request, and applies the changes automatically.

> **Phase:** 2 - Target Configuration

---

## Features

- Retrieve the current Scanner Profile
- Configure scanners using a JSON configuration file
- Validate scanner configuration before making API requests
- Automatically transform the JSON configuration into the Veracode API request model
- Strongly typed models
- Full type hints
- HMAC authentication
- Unit tested

---

## Installation

```python
from veracode_dast import VeracodeClient

client = VeracodeClient()
```

`VeracodeClient` takes no arguments — it reads `VERACODE_API_KEY_ID` and
`VERACODE_API_KEY_SECRET` from the environment automatically.

---

## SDK Configuration Format

Scanner Profiles are configured using a simple JSON document.

Example (`scanner-profile.json`):

```json
{
  "scanners": {
    "sql_injection": true,
    "xss": true,
    "csrf": false,
    "ssrf": true,
    "clickjacking": true
  }
}
```

This format is designed to be:

- Easy to read
- Easy to maintain
- Version-control friendly
- Independent of the Veracode OpenAPI specification

---

## Get Scanner Profile

Retrieve the current scanner configuration.

```python
scanner_profile = client.scanners.get(
    analysis_profile_id="analysis_profile_id"
)

for scanner in scanner_profile.scanners:
    print(scanner.id)
    print(scanner.enabled)
```

---

## Update Scanner Profile

Apply a Scanner Profile using the SDK configuration file.

```python
client.scanners.update(
    analysis_profile_id="analysis_profile_id",
    config_file="scanner-profile.json"
)
```

During execution the SDK will:

1. Read the configuration file.
2. Validate the JSON structure.
3. Validate scanner names.
4. Transform the configuration into the Veracode API request model.
5. Submit the request.
6. Return the updated Scanner Profile.

---

## JSON Transformation

The SDK hides the complexity of the Veracode API.

### SDK Configuration

```json
{
  "scanners": {
    "sql_injection": true,
    "xss": true,
    "csrf": false
  }
}
```

### Generated API Request

```json
{
  "scanners": [
    {
      "id": "sql_injection",
      "value": true
    },
    {
      "id": "xss",
      "value": true
    },
    {
      "id": "csrf",
      "value": false
    }
  ]
}
```

The OpenAPI request model is generated automatically by the SDK.

---

## Validation

Configuration files are validated before any request is sent.

Example:

```json
{
  "scanners": {
    "sql": true
  }
}
```

Result:

```text
Unknown scanner 'sql'.

Did you mean 'sql_injection'?
```

This prevents unnecessary API calls and provides clear feedback.

---

## Returned Model

```python
ScannerProfile
```

Example:

```python
ScannerProfile(
    scanners=[
        Scanner(
            id="sql_injection",
            enabled=True,
            inherited=False,
            editable=True
        ),
        Scanner(
            id="xss",
            enabled=True,
            inherited=False,
            editable=True
        )
    ]
)
```

---

## Exceptions

The service may raise:

- AuthenticationError
- AuthorizationError
- ValidationError
- NotFoundError
- ApiError

---

## API Endpoints

| Method | Endpoint |
|---------|----------|
| GET | `/analysis_profiles/{analysis_profile_id}/scanners` |
| PUT | `/analysis_profiles/{analysis_profile_id}/scanners` |

---

## Design Philosophy

The SDK is configuration-driven.

Users interact with a simple JSON configuration instead of constructing Veracode API request models.

The SDK is responsible for:

- Loading configuration files
- Validating configuration
- Transforming configuration into the Veracode API format
- Communicating with the Veracode API
- Returning strongly typed Python models

This approach makes Scanner Profiles easier to automate, review and version alongside application source code.

---

## Future Vision

Scanner Profiles are one part of the complete DAST configuration.

Future releases will use the same configuration-driven approach for:

- Analysis Profiles
- Authentication
- Scanner Variables
- ISM Gateways

Ultimately, these resources will be combined into a single declarative configuration file:

```text
dast-config.json
```

allowing an entire DAST Target Configuration to be managed from one file.

---

## Related Services

Typical workflow:

```python
profile = client.analysis_profiles.get(
    "analysis_profile_id"
)

client.scanners.update(
    analysis_profile_id=profile.id,
    config_file="scanner-profile.json"
)
```

Scanner Profiles integrate with:

- Analysis Profiles
- Authentication
- Scanner Variables
- ISM Gateways