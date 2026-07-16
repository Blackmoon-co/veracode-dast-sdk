"""API Specification Management: upload, retrieve, and download API
Specifications for existing DAST API Targets.

Never manages Target lifecycle — every method takes an existing `target_id`.
Never depends on Team Management.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING

from veracode_dast.exceptions import (
    ApiSpecificationFileNotFoundError,
    ApiSpecificationValidationError,
)
from veracode_dast.models.api_specification import ApiSpecification

if TYPE_CHECKING:
    from veracode_dast.client import HttpClient

_SPEC_PATH = "/targets/{target_id}/spec"
_SPEC_DOWNLOAD_PATH = "/targets/{target_id}/spec/download"

logger = logging.getLogger(__name__)


class ApiSpecificationsService:
    """Manages API Specifications for existing DAST API Targets."""

    def __init__(self, http_client: HttpClient) -> None:
        """Initializes the service.

        Args:
            http_client: An `HttpClient` configured with
                `TARGET_CONFIGURATION_SERVICE_BASE_URL` — typically the
                same instance already constructed for `TargetsService`.
        """
        self._http_client = http_client

    def upload(self, target_id: str, file_path: str | Path) -> ApiSpecification:
        """Uploads an API Specification file for a Target.

        Args:
            target_id: The target's unique identifier.
            file_path: Path to a local JSON, YAML, or HAR API specification
                file.

        Returns:
            The uploaded specification's metadata.

        Raises:
            ApiSpecificationValidationError: If `target_id` is blank.
            ApiSpecificationFileNotFoundError: If `file_path` does not
                reference an existing file.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        path = Path(file_path)
        if not path.is_file():
            raise ApiSpecificationFileNotFoundError(
                f"API specification file not found: {path}", path=str(path)
            )

        logger.info("Uploading API specification for target %s: %s", target_id, path.name)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        response = self._http_client.post(
            _SPEC_PATH.format(target_id=target_id),
            files={"specFile": (path.name, path.read_bytes(), content_type)},
        )
        spec = ApiSpecification.from_api(response.data, target_id=target_id)  # type: ignore[arg-type]
        logger.info("Upload completed for target %s: %s", target_id, spec.api_spec_name)
        return spec

    def get(self, target_id: str) -> ApiSpecification:
        """Gets API Specification metadata for a Target.

        Args:
            target_id: The target's unique identifier.

        Returns:
            The specification's metadata.

        Raises:
            ApiSpecificationValidationError: If `target_id` is blank.
            VeracodeNotFoundError: If the target has no uploaded specification.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        response = self._http_client.get(_SPEC_PATH.format(target_id=target_id))
        spec = ApiSpecification.from_api(response.data, target_id=target_id)  # type: ignore[arg-type]
        logger.info("Retrieved API specification metadata for target %s", target_id)
        return spec

    def download(self, target_id: str, destination_path: str | Path) -> Path:
        """Downloads the raw API Specification contents for a Target.

        Args:
            target_id: The target's unique identifier.
            destination_path: Local path to write the downloaded file to.

        Returns:
            The resolved destination path.

        Raises:
            ApiSpecificationValidationError: If `target_id` is blank, or
                `destination_path`'s parent directory does not exist.
            VeracodeNotFoundError: If the target has no uploaded specification.
        """
        self._require_non_blank(target_id, rule="target_id_required")
        destination = Path(destination_path)
        if not destination.parent.is_dir():
            raise ApiSpecificationValidationError(
                f"Destination directory does not exist: {destination.parent}",
                rule="destination_parent_must_exist",
            )

        logger.info("Downloading API specification for target %s to %s", target_id, destination)
        response = self._http_client.get(
            _SPEC_DOWNLOAD_PATH.format(target_id=target_id), raw=True
        )
        content = response.data or b""
        destination.write_bytes(content)  # type: ignore[arg-type]
        logger.info("Download completed for target %s: %d byte(s)", target_id, len(content))
        return destination

    @staticmethod
    def _require_non_blank(value: str, *, rule: str) -> None:
        if not value or not value.strip():
            raise ApiSpecificationValidationError("Value must not be blank", rule=rule)
