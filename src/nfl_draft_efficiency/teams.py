from __future__ import annotations

from typing import Final

import pandas as pd


TEAM_CODE_ALIASES: Final[dict[str, str]] = {
    "ARI": "ARI",
    "ATL": "ATL",
    "BAL": "BAL",
    "BUF": "BUF",
    "CAR": "CAR",
    "CHI": "CHI",
    "CIN": "CIN",
    "CLE": "CLE",
    "DAL": "DAL",
    "DEN": "DEN",
    "DET": "DET",
    "GB": "GB",
    "GNB": "GB",
    "HOU": "HOU",
    "IND": "IND",
    "JAX": "JAX",
    "KC": "KC",
    "KAN": "KC",
    "LA": "LA",
    "LAR": "LA",
    "RAM": "LA",
    "STL": "LA",
    "LAC": "LAC",
    "SDG": "LAC",
    "LV": "LV",
    "LVR": "LV",
    "OAK": "LV",
    "RAI": "LV",
    "MIA": "MIA",
    "MIN": "MIN",
    "NE": "NE",
    "NWE": "NE",
    "NO": "NO",
    "NOR": "NO",
    "NYG": "NYG",
    "NYJ": "NYJ",
    "PHI": "PHI",
    "PHO": "ARI",
    "PIT": "PIT",
    "SEA": "SEA",
    "SF": "SF",
    "SFO": "SF",
    "TB": "TB",
    "TAM": "TB",
    "TEN": "TEN",
    "WAS": "WAS",
}

ESPN_TEAM_PAGES: Final[dict[str, tuple[str, str]]] = {
    "ARI": ("ari", "arizona-cardinals"),
    "ATL": ("atl", "atlanta-falcons"),
    "BAL": ("bal", "baltimore-ravens"),
    "BUF": ("buf", "buffalo-bills"),
    "CAR": ("car", "carolina-panthers"),
    "CHI": ("chi", "chicago-bears"),
    "CIN": ("cin", "cincinnati-bengals"),
    "CLE": ("cle", "cleveland-browns"),
    "DAL": ("dal", "dallas-cowboys"),
    "DEN": ("den", "denver-broncos"),
    "DET": ("det", "detroit-lions"),
    "GB": ("gb", "green-bay-packers"),
    "HOU": ("hou", "houston-texans"),
    "IND": ("ind", "indianapolis-colts"),
    "JAX": ("jax", "jacksonville-jaguars"),
    "KC": ("kc", "kansas-city-chiefs"),
    "LA": ("lar", "los-angeles-rams"),
    "LAC": ("lac", "los-angeles-chargers"),
    "LV": ("lv", "las-vegas-raiders"),
    "MIA": ("mia", "miami-dolphins"),
    "MIN": ("min", "minnesota-vikings"),
    "NE": ("ne", "new-england-patriots"),
    "NO": ("no", "new-orleans-saints"),
    "NYG": ("nyg", "new-york-giants"),
    "NYJ": ("nyj", "new-york-jets"),
    "PHI": ("phi", "philadelphia-eagles"),
    "PIT": ("pit", "pittsburgh-steelers"),
    "SEA": ("sea", "seattle-seahawks"),
    "SF": ("sf", "san-francisco-49ers"),
    "TB": ("tb", "tampa-bay-buccaneers"),
    "TEN": ("ten", "tennessee-titans"),
    "WAS": ("wsh", "washington-commanders"),
}

ACTIVE_ROSTER_STATUSES: Final[frozenset[str]] = frozenset({"ACT"})
RESERVE_ROSTER_STATUSES: Final[frozenset[str]] = frozenset({"E14", "EXE", "INA", "PUP", "RES", "RSN", "SUS"})
PRACTICE_SQUAD_STATUSES: Final[frozenset[str]] = frozenset({"DEV"})
NOT_WITH_TEAM_STATUSES: Final[frozenset[str]] = frozenset({"CUT", "NWT", "RET", "RFA", "TRC", "TRD", "TRL", "TRT", "UFA"})


def normalize_team_code(value: object) -> str:
    if pd.isna(value):
        return ""
    team_code = str(value).strip().upper()
    if not team_code:
        return ""
    return TEAM_CODE_ALIASES.get(team_code, team_code)


def team_codes_equal(left: object, right: object) -> bool:
    left_code = normalize_team_code(left)
    right_code = normalize_team_code(right)
    return bool(left_code) and left_code == right_code


def normalize_roster_status(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def roster_status_bucket(status: object) -> str:
    normalized = normalize_roster_status(status)
    if normalized in ACTIVE_ROSTER_STATUSES:
        return "active_roster"
    if normalized in RESERVE_ROSTER_STATUSES:
        return "reserve_inactive"
    if normalized in PRACTICE_SQUAD_STATUSES:
        return "practice_squad"
    if normalized in NOT_WITH_TEAM_STATUSES:
        return "not_with_team"
    if normalized:
        return "unknown_status"
    return "missing_status"


def roster_status_counts_as_with_team(status: object) -> bool:
    return roster_status_bucket(status) in {"active_roster", "reserve_inactive", "practice_squad"}


def roster_status_priority(status: object) -> int:
    bucket = roster_status_bucket(status)
    if bucket == "active_roster":
        return 40
    if bucket == "reserve_inactive":
        return 30
    if bucket == "practice_squad":
        return 20
    if bucket == "unknown_status":
        return 10
    return 0


def get_espn_team_page(team_code: str, page_type: str) -> str:
    espn_team = ESPN_TEAM_PAGES[normalize_team_code(team_code)]
    short_code, slug = espn_team
    return f"https://www.espn.com/nfl/team/{page_type}/_/name/{short_code}/{slug}"
