from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_default_config_path() -> Path:
    return get_project_root() / "config" / "scoring.yml"


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_yaml_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at {path}, found {type(data).__name__}.")
    return data


def load_runtime_config(config_path: str | None = None) -> dict[str, Any]:
    config = load_yaml_file(get_default_config_path())
    if config_path:
        override_path = Path(config_path)
        if not override_path.is_absolute():
            override_path = get_project_root() / override_path
        config = deep_merge(config, load_yaml_file(override_path))
    if "round_pick_cost" in config:
        config["round_pick_cost"] = {int(key): value for key, value in config["round_pick_cost"].items()}
    return config


def resolve_output_dir(output_dir: str | None) -> Path:
    if not output_dir:
        return get_project_root() / "outputs"
    output_path = Path(output_dir)
    if output_path.is_absolute():
        return output_path
    return get_project_root() / output_path


def resolve_draft_years(
    config: dict[str, Any],
    draft_window_years: int | None = None,
    min_draft_year: int | None = None,
    max_draft_year: int | None = None,
) -> list[int]:
    default_min = int(config["default_min_draft_year"])
    default_max = int(config["default_max_draft_year"])
    default_window = int(config["default_draft_window_years"])

    if min_draft_year is not None and max_draft_year is not None:
        if min_draft_year > max_draft_year:
            raise ValueError("min_draft_year cannot be greater than max_draft_year.")
        return list(range(min_draft_year, max_draft_year + 1))

    if min_draft_year is not None and max_draft_year is None:
        window = draft_window_years or default_window
        return list(range(min_draft_year, min_draft_year + window))

    if max_draft_year is not None and min_draft_year is None:
        window = draft_window_years or default_window
        return list(range(max_draft_year - window + 1, max_draft_year + 1))

    if draft_window_years is not None:
        return list(range(default_max - draft_window_years + 1, default_max + 1))

    return list(range(default_min, default_max + 1))
