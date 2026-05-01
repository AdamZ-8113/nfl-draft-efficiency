from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


_SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b", flags=re.IGNORECASE)
_PUNCT_RE = re.compile(r"[^\w\s/+\-]")
_POSITION_SPLIT_RE = re.compile(r"[/,\s+\-]+")


def normalize_name(name: object) -> str:
    if pd.isna(name):
        return ""
    text = str(name).lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _SUFFIX_RE.sub(" ", text)
    return " ".join(text.split())


def build_position_alias_map(config: dict) -> dict[str, str]:
    alias_map: dict[str, str] = {}
    for group, aliases in config.get("position_groups", {}).items():
        alias_map[group.upper()] = group.upper()
        for alias in aliases:
            alias_map[str(alias).upper()] = group.upper()
    return alias_map


def normalize_position_group(position: object, config: dict) -> str:
    if pd.isna(position):
        return "UNKNOWN"

    alias_map = build_position_alias_map(config)
    raw = str(position).upper().replace(".", " ").strip()
    tokens = [token for token in _POSITION_SPLIT_RE.split(raw) if token]
    if not tokens:
        return alias_map.get(raw, "UNKNOWN")

    for token in tokens:
        group = alias_map.get(token)
        if group:
            return group
    return alias_map.get(raw, "UNKNOWN")


def first_existing_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None

