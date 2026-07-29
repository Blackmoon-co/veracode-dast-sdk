from veracode_dast.models.authentication import (
    ApplicationAuthentication,
    AuthenticationConfiguration,
    CertificateAuthentication,
    OAuth2Authentication,
    OAuth2GrantType,
    ParameterAuthentication,
    ParameterAuthenticationType,
    Script,
    ScriptAuthentication,
    ScriptType,
    SRMAuthentication,
    SystemAuthentication,
)


def test_system_authentication_from_api_and_repr_hides_password() -> None:
    auth = SystemAuthentication.from_api({"username": "john.doe", "password": "super-secret"})
    assert auth == SystemAuthentication(username="john.doe", password="super-secret")
    assert "super-secret" not in repr(auth)


def test_application_authentication_from_api_includes_enable_ai_login() -> None:
    auth = ApplicationAuthentication.from_api(
        {
            "username": "john.doe",
            "password": "super-secret",
            "login_url": "https://example.com/login",
            "enable_ai_login": True,
        }
    )
    assert auth.enable_ai_login is True
    assert "super-secret" not in repr(auth)


def test_certificate_authentication_hides_secrets_in_repr() -> None:
    auth = CertificateAuthentication.from_api(
        {"cert_name": "cert-1", "base64_pkcs12": "base64data", "password": "cert-pass"}
    )
    assert "base64data" not in repr(auth)
    assert "cert-pass" not in repr(auth)


def test_script_authentication_from_api_handles_absent_scripts() -> None:
    auth = ScriptAuthentication.from_api({})
    assert auth == ScriptAuthentication(login_script=None, logout_script=None)


def test_script_authentication_from_api_builds_scripts() -> None:
    auth = ScriptAuthentication.from_api(
        {
            "login_script": {"script_name": "login", "script_type": "SELENIUM", "script_body": "x"},
            "logout_script": None,
        }
    )
    assert auth.login_script == Script(
        script_name="login", script_type=ScriptType.SELENIUM, script_body="x"
    )
    assert auth.logout_script is None
    assert "x" not in repr(auth.login_script)


def test_srm_authentication_hides_script_body() -> None:
    auth = SRMAuthentication.from_api({"script_body": "srm-body"})
    assert "srm-body" not in repr(auth)


def test_oauth2_authentication_from_api_maps_all_fields() -> None:
    auth = OAuth2Authentication.from_api(
        {
            "grant_type": "CLIENT_CREDENTIALS",
            "access_token_url": "https://example.com/oauth/token",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "authorization_url": "https://example.com/authorize",
            "username": "user",
            "password": "pass",
            "redirect_url": "https://example.com/redirect",
            "scope": "read",
            "use_openid_connect": True,
            "openid_url": "https://example.com/openid",
        }
    )
    assert auth.grant_type == OAuth2GrantType.CLIENT_CREDENTIALS
    assert "client-secret" not in repr(auth)
    assert "password=" not in repr(auth)


def test_parameter_authentication_from_api_hides_value() -> None:
    auth = ParameterAuthentication.from_api(
        {
            "id": "id-1",
            "title": "API Key",
            "type": "HTTP_HEADER",
            "key": "X-API-Key",
            "value": "secret-token",
        }
    )
    assert auth.type == ParameterAuthenticationType.HTTP_HEADER
    assert "secret-token" not in repr(auth)


def test_authentication_configuration_from_api_mixed_none_and_populated() -> None:
    data = {
        "system_authentication": {
            "is_inherited": False,
            "effective_value": {"username": "admin", "password": "secret123"},
        },
        "application_authentication": None,
        "certificate_authentication": None,
        "script_authentication": None,
        "srm_authentication": None,
        "oauth2_authentication": None,
        "parameter_authentications": {
            "is_inherited": True,
            "effective_value": [
                {
                    "title": "API Key",
                    "type": "HTTP_HEADER",
                    "key": "X-API-Key",
                    "value": "secret-token",
                }
            ],
        },
    }
    config = AuthenticationConfiguration.from_api(data)

    assert config.application_authentication is None
    assert config.system_authentication is not None
    assert config.system_authentication.effective_value.username == "admin"
    assert config.system_authentication.is_inherited is False
    assert config.parameter_authentications is not None
    assert config.parameter_authentications.is_inherited is True
    assert len(config.parameter_authentications.effective_value) == 1


def test_authentication_configuration_defaults_to_all_none() -> None:
    config = AuthenticationConfiguration()
    assert config.system_authentication is None
    assert config.parameter_authentications is None
