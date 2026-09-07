"""Typed models for the DAST Target Configuration Service's Scanner
Variables resource.

Scanner Variables provide runtime values consumed by authentication
mechanisms (login scripts, MFA/TOTP) during an authenticated DAST scan —
never interpreted or processed by this SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScannerVariable:
    """A single runtime variable consumed by authentication mechanisms
    during an authenticated DAST scan.

    Attributes:
        reference_key: The name authentication mechanisms use to look up
            this variable's value.
        value: The variable's value (e.g. a username, password, or TOTP
            seed). Never logged. `None` on a model parsed from a
            `get()`/`update()` response — the API stores values write-only
            and never echoes them back.
        totp_seed: Whether `value` is a TOTP seed evaluated by Veracode at
            scan time, rather than used as-is. The SDK's simplified
            boolean over the API's `evaluation_mode` field (`TOTP`/`RAW`).
        is_inherited: Whether this variable's value is inherited from a
            parent Analysis Profile.
        id: This variable's identifier, if the API assigned one. Never
            supplied by SDK Configuration; always None on a
            caller-constructed instance passed to `update()`.
    """

    reference_key: str
    value: str | None = None
    totp_seed: bool = False
    is_inherited: bool = False
    id: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ScannerVariable:
        """Builds a `ScannerVariable` from one `EffectiveScannerVariable`.

        Args:
            data: One raw `{"effective_value": {...}, "is_inherited": ...}`
                object from a `GET`/`PUT` response array.

        Returns:
            The corresponding `ScannerVariable`.
        """
        inner = data["effective_value"]
        return cls(
            reference_key=inner["reference_key"],
            value=inner.get("value"),  # write-only server-side; absent on read-back
            totp_seed=inner.get("evaluation_mode") == "TOTP",
            is_inherited=data["is_inherited"],
            id=inner.get("id"),
        )

    def to_api(self) -> dict[str, Any]:
        """Builds this variable's entry in a `PUT .../scanner_variables`
        request body.

        Returns:
            A JSON-serializable object with `reference_key`, `value`, and
            `evaluation_mode` (derived from `totp_seed`). Never includes
            `id` or `utilize_in_ai_assisted_login`.
        """
        return {
            "reference_key": self.reference_key,
            "value": self.value,
            "evaluation_mode": "TOTP" if self.totp_seed else "RAW",
        }


@dataclass(frozen=True)
class ScannerVariables:
    """The complete set of Scanner Variables effective for an Analysis
    Profile, as returned by `get()`/`update()`.

    Attributes:
        variables: One `ScannerVariable` per entry in the API response.
    """

    variables: list[ScannerVariable] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: list[Any]) -> ScannerVariables:
        """Builds a `ScannerVariables` from an `EffectiveScannerVariables`
        response body.

        Args:
            data: The raw response array.

        Returns:
            The corresponding `ScannerVariables`.
        """
        return cls(variables=[ScannerVariable.from_api(item) for item in data])
