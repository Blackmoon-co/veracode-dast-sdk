import pytest

from veracode_dast.client import VeracodeClient
from veracode_dast.services.analysis_profiles import AnalysisProfilesService
from veracode_dast.services.authentications import AuthenticationsService
from veracode_dast.services.ism_gateways import IsmGatewaysService
from veracode_dast.services.scanner_variables import ScannerVariablesService
from veracode_dast.services.scanners import ScannersService


@pytest.fixture(autouse=True)
def _credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERACODE_API_KEY_ID", "id-123")
    monkeypatch.setenv("VERACODE_API_KEY_SECRET", "secret-456")


def test_phase_2_services_share_targets_http_client_instance() -> None:
    client = VeracodeClient()

    assert isinstance(client.analysis_profiles, AnalysisProfilesService)
    assert isinstance(client.scanners, ScannersService)
    assert isinstance(client.authentications, AuthenticationsService)
    assert isinstance(client.scanner_variables, ScannerVariablesService)
    assert isinstance(client.ism_gateways, IsmGatewaysService)

    targets_http_client = client.targets._http_client
    assert client.analysis_profiles._http_client is targets_http_client
    assert client.scanners._http_client is targets_http_client
    assert client.authentications._http_client is targets_http_client
    assert client.scanner_variables._http_client is targets_http_client
    assert client.ism_gateways._http_client is targets_http_client
