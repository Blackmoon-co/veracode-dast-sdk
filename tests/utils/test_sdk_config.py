from pathlib import Path

import pytest

from veracode_dast.exceptions import ConfigFileInvalidError, ConfigFileNotFoundError
from veracode_dast.utils.sdk_config import load_json_config, suggest_closest


def test_load_json_config_passthrough_for_dict() -> None:
    source = {"a": 1}
    assert load_json_config(source) is source


def test_load_json_config_reads_valid_file(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"a": 1}', encoding="utf-8")

    assert load_json_config(path) == {"a": 1}
    assert load_json_config(str(path)) == {"a": 1}


def test_load_json_config_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigFileNotFoundError):
        load_json_config(tmp_path / "missing.json")


def test_load_json_config_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")

    with pytest.raises(ConfigFileInvalidError):
        load_json_config(path)


def test_suggest_closest_finds_near_match() -> None:
    assert suggest_closest("sql", ["sql_injection", "xss", "csrf"]) == "sql_injection"


def test_suggest_closest_returns_none_when_no_close_match() -> None:
    assert suggest_closest("zzzzzzzzzz", ["sql_injection", "xss", "csrf"]) is None
