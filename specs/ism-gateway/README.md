# ISM Gateways

The ISM Gateways service manages the Internal Scanning Management (ISM) Gateway associated with a Veracode DAST Analysis Profile.

ISM Gateways enable Veracode DAST to securely scan applications that are not publicly accessible, such as internal, staging, development, or private network environments.

Unlike the Veracode REST API, which requires gateway identifiers, this SDK allows users to configure gateways using human-readable names. The SDK automatically resolves gateway names to their corresponding identifiers before communicating with the Veracode API.

> **Phase:** 2 - Target Configuration

---

# Features

- List available ISM Gateways
- Retrieve the gateway assigned to an Analysis Profile
- Assign or change an ISM Gateway using its name
- Remove an ISM Gateway assignment
- Update gateway assignments using an SDK configuration file
- Automatically resolve gateway names
- Validate configuration before sending requests
- Strongly typed models
- Full type hints
- HMAC authentication
- Unit tested

---

# Installation

```python
from veracode_dast import VeracodeDASTClient

client = VeracodeDASTClient(
    api_id="VERACODE_API_ID",
    api_key="VERACODE_API_KEY",
)
```

---

# SDK Configuration

The SDK accepts gateway names instead of Veracode gateway identifiers.

Example (`ism-gateway.json`):

```json
{
  "gateway": {
    "name": "Corporate Gateway"
  }
}
```

Users never need to know the gateway ID.

---

# List Available Gateways

Retrieve all gateways available to the current account.

```python
gateways = client.ism_gateways.list()

for gateway in gateways:
    print(gateway.name)
```

Example output:

```text
Corporate Gateway
Development Gateway
QA Gateway
Production Gateway
```

---

# Get Assigned Gateway

Retrieve the gateway assigned to a Target.

```python
gateway = client.ism_gateways.get(
    target_id="target_id"
)

print(gateway.name)
```

---

# Update Gateway Assignment

Assign a gateway by name.

```python
client.ism_gateways.update(
    target_id="target_id",
    config_file="ism-gateway.json"
)
```

or directly:

```python
client.ism_gateways.update(
    target_id="target_id",
    gateway_name="Corporate Gateway"
)
```

---

# Name Resolution

The SDK automatically resolves gateway names.

Internally the SDK performs:

1. Retrieve available gateways.
2. Find the gateway matching the configured name.
3. Extract the gateway identifier.
4. Submit the Veracode API request.
5. Return the updated gateway assignment.

Users never interact with gateway IDs.

---

# Remove Gateway Assignment

```python
client.ism_gateways.remove(
    target_id="target_id"
)
```

---

# Validation

Configuration is validated before contacting the Veracode API.

Validation includes:

- Missing gateway name
- Gateway not found
- Duplicate gateway names
- Invalid configuration structure

If the gateway cannot be found, the SDK raises:

```text
GatewayNotFoundError:
ISM Gateway 'Corporate Gateway' was not found.
```

---

# Returned Model

```python
ISMGateway
```

Example:

```python
ISMGateway(
    id="gateway-id",
    name="Corporate Gateway",
    status="ONLINE"
)
```

Although the model contains the gateway identifier, users normally interact only with the gateway name.

---

# Exceptions

The service may raise:

- AuthenticationError
- AuthorizationError
- ValidationError
- GatewayNotFoundError
- ApiError

---

# API Integration

The Veracode REST API requires gateway identifiers.

The SDK automatically performs identifier resolution before making API requests.

This behavior follows the same design philosophy used throughout the SDK, where users work with meaningful resource names rather than internal identifiers.

---

# Design Philosophy

The SDK prioritizes usability over exposing raw REST models.

Users configure resources using human-readable names.

The SDK is responsible for:

- Reading configuration
- Resolving gateway names
- Validating configuration
- Building Veracode API requests
- Calling the REST API
- Returning strongly typed Python models

Users should never need to manually retrieve or provide gateway identifiers.

---

# Related Services

Typical workflow:

```python
client.analysis_profiles.update(
    analysis_profile_id,
    config_file="analysis-profile.json"
)

client.ism_gateways.update(
    target_id,
    gateway_name="Corporate Gateway"
)
```

ISM Gateways integrate closely with:

- Analysis Profiles
- Targets
- Internal Applications
- Private Network Scanning