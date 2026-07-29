# Analysis Profiles

The Analysis Profiles service provides access to Veracode DAST Analysis Profiles.

Analysis Profiles define how a DAST target is configured and serve as the parent resource for scanner configuration, authentication, scanner variables, and other scan settings.

> **Phase:** 2 - Target Configuration

---

## Features

- List analysis profiles
- Get an analysis profile by ID
- Update an analysis profile
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

## List Analysis Profiles

```python
profiles = client.analysis_profiles.list()

for profile in profiles:
    print(profile.id)
    print(profile.name)
```

---

## Get Analysis Profile

```python
profile = client.analysis_profiles.get(
    "analysis_profile_id"
)

print(profile.id)
print(profile.name)
print(profile.description)
```

---

## Update Analysis Profile

```python
updated = client.analysis_profiles.update(
    analysis_profile_id="analysis_profile_id",
    name="Production Profile",
    description="Production DAST profile"
)

print(updated.name)
```

---

## Returned Model

```python
AnalysisProfile
```

Example

```python
AnalysisProfile(
    id="1234567890abcdef",
    name="Production",
    description="Production profile",
    profile_type="CUSTOM",
    parent_profile_id=None
)
```

---

## Exceptions

The service may raise:

- AuthenticationError
- AuthorizationError
- NotFoundError
- ValidationError
- ApiError

---

## API Endpoints

| Method | Endpoint |
|----------|----------|
| GET | `/analysis_profiles` |
| GET | `/analysis_profiles/{analysis_profile_id}` |
| PUT | `/analysis_profiles/{analysis_profile_id}` |

---

## Related Services

Analysis Profiles are the root object for:

- Authentication
- Scanner Profiles
- Scanner Variables
- ISM Gateway Configuration

Typical workflow:

```python
profile = client.analysis_profiles.get(profile_id)

client.scanners.update(...)

client.authentications.update_form(...)

client.scanner_variables.update(...)
```

---

## Next Steps

After retrieving an Analysis Profile you can configure:

- Scanner Profile
- Scanner Variables
- Authentication
- ISM Gateway