"""Resource-agnostic SDK Configuration loading and name-suggestion helpers.

Shared by every configuration-driven Phase 2 service (Scanner Profiles,
Authentications, Scanner Variables, ISM Gateways). Knows nothing about any
specific resource's schema.
"""

from __future__ import annotations

import difflib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from veracode_dast.exceptions import ConfigFileInvalidError, ConfigFileNotFoundError


def load_json_config(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Loads an SDK Configuration document.

    Args:
        source: A path to a JSON file, or an already-loaded dict.

    Returns:
        The parsed configuration as a dict.

    Raises:
        ConfigFileNotFoundError: If `source` is a path that does not exist.
        ConfigFileInvalidError: If the file's contents are not valid JSON.
    """
    if isinstance(source, dict):
        return source
    path = Path(source)
    if not path.is_file():
        raise ConfigFileNotFoundError(str(path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except json.JSONDecodeError as exc:
        raise ConfigFileInvalidError(str(path), reason=str(exc)) from exc


def suggest_closest(name: str, valid_names: Iterable[str]) -> str | None:
    """Returns the closest match to `name` among `valid_names`, or None.

    Names that `name` is a case-insensitive prefix of are preferred (the
    shortest one, if several) — this catches abbreviation-style typos
    (e.g. `"sql"` for `"sql_injection"`) that `difflib`'s similarity ratio
    alone misses when the valid name is much longer than the typo. Falls
    back to `difflib.get_close_matches` for everything else (e.g.
    transposition-style typos like `"aouth2"` for `"oauth2"`).

    Args:
        name: The unrecognized name to find a close match for.
        valid_names: The set of known-valid names to match against.

    Returns:
        The closest match, or None if no close match was found.
    """
    names = list(valid_names)
    prefix_matches = [n for n in names if n != name and n.lower().startswith(name.lower())]
    if prefix_matches:
        return min(prefix_matches, key=len)
    matches = difflib.get_close_matches(name, names, n=1)
    return matches[0] if matches else None
