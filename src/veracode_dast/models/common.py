"""Small, generic model shapes shared across Veracode DAST resources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class InheritedValue(Generic[T]):
    """A configuration value that may be inherited from a parent Analysis
    Profile.

    Attributes:
        effective_value: The value in effect for this profile.
        is_inherited: True if `effective_value` is inherited from the
            parent Analysis Profile rather than set on this profile
            directly.
    """

    effective_value: T
    is_inherited: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> InheritedValue[T]:
        """Builds an `InheritedValue` from a raw wrapper object.

        Args:
            data: The raw `{"effective_value": ..., "is_inherited": ...}`
                object from the API response.

        Returns:
            The corresponding `InheritedValue`.
        """
        return cls(effective_value=data["effective_value"], is_inherited=data["is_inherited"])
