from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from utils.file_utils import load_json


@lru_cache(maxsize=1)
def get_repo_root() -> Path:
    """
    Expected location:
    code/src/config/path_manager.py

    repo root = ../../../
    """
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def get_paths_config() -> dict:
    paths_file = get_repo_root() / "code" / "config" / "paths.json"
    return load_json(str(paths_file))


def _get_nested_value(data: dict, dotted_key: str) -> Any:
    current: Any = data

    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"Key '{dotted_key}' not found in paths.json")
        current = current[part]

    return current


def resolve_repo_path(raw_path: str) -> str:
    path = Path(raw_path)

    if path.is_absolute():
        return str(path)

    return str(get_repo_root() / path)


def get_path(key: str) -> str:
    """
    Returns an absolute path for a key from paths.json.

    Example:
        get_path("config.models_config")
        get_path("models.base_dir")
        get_path("prompts.rendered_dir")
    """
    value = _get_nested_value(get_paths_config(), key)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Key '{key}' in paths.json must be a non-empty string")

    return resolve_repo_path(value)


def get_value(key: str) -> Any:
    """
    Returns the raw value from paths.json without path resolution.
    Useful for non-path config values.
    """
    return _get_nested_value(get_paths_config(), key)