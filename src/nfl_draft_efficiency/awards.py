from __future__ import annotations

import csv
import re
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

from .config import get_project_root
from .normalize_ids import normalize_name


AP_AWARD_URLS: dict[int, str] = {
    2022: "https://www.nfl.com/news/nfl-honors-finalists-announced-for-select-awards-from-2022-season",
    2023: "https://www.nfl.com/news/nfl-honors-finalists-announced-for-mvp-other-awards-from-2023-season",
    2024: "https://www.nfl.com/news/nfl-honors-finalists-announced-for-mvp-other-awards-from-2024-season",
    2025: "https://www.nfl.com/news/nfl-honors-finalists-announced-for-mvp-other-awards-from-2025-season",
}

AP_AWARD_HEADERS: list[tuple[str, str]] = [
    ("AP Most Valuable Player", "MVP"),
    ("AP Defensive Player of the Year", "DPOY"),
    ("AP Offensive Player of the Year", "OPOY"),
    ("AP Offensive Rookie of the Year", "OROY"),
    ("AP Defensive Rookie of the Year", "DROY"),
    ("AP Comeback Player of the Year", "CPOY"),
    ("AP Coach of the Year", "COY"),
    ("AP Assistant Coach of the Year", "ACOY"),
]

AP_2021_WINNERS: list[dict[str, object]] = [
    {"season": 2021, "award": "MVP", "player_name": "Aaron Rodgers", "team_position": "Green Bay Packers QB"},
    {"season": 2021, "award": "OPOY", "player_name": "Cooper Kupp", "team_position": "Los Angeles Rams WR"},
    {"season": 2021, "award": "DPOY", "player_name": "T.J. Watt", "team_position": "Pittsburgh Steelers LB"},
    {"season": 2021, "award": "OROY", "player_name": "Ja'Marr Chase", "team_position": "Cincinnati Bengals WR"},
    {"season": 2021, "award": "DROY", "player_name": "Micah Parsons", "team_position": "Dallas Cowboys LB"},
    {"season": 2021, "award": "CPOY", "player_name": "Joe Burrow", "team_position": "Cincinnati Bengals QB"},
]

AP_2021_SOURCE_URL = "https://www.nfl.com/news/list-of-nfl-honors-award-winners-from-2021-nfl-season"


def _default_awards_cache_path() -> Path:
    return get_project_root() / "data" / "cache" / "ap_award_finalists.csv"


def _fetch_url_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="ignore")
    text = unescape(re.sub("<[^>]+>", "\n", html)).replace("\\n", "\n")
    return text.replace("\r", "")


def _parse_nfl_awards_page(season: int, url: str) -> list[dict[str, object]]:
    text = _fetch_url_text(url)
    positions: list[tuple[int, str, str]] = []
    for header, award_code in AP_AWARD_HEADERS:
        match = re.search(re.escape(header), text)
        if match:
            positions.append((match.start(), header, award_code))
    positions.sort()

    rows: list[dict[str, object]] = []
    for index, (start, header, award_code) in enumerate(positions):
        if award_code in {"COY", "ACOY"}:
            continue
        end = positions[index + 1][0] if index + 1 < len(positions) else len(text)
        segment = text[start:end]
        segment = re.sub(re.escape(header) + r"(?: presented by [^\n]+)?", "", segment, count=1)
        lines = [line.strip() for line in segment.split("\n") if line.strip()]
        for line in lines:
            if "," not in line:
                continue
            if line.startswith(('"', "{", "Follow ", "Finalists ", "The finalists")):
                continue
            player_name, team_position = line.split(",", 1)
            player_name = player_name.strip()
            if not player_name or len(player_name) > 45 or player_name.startswith(("AP ", "NFL ")):
                continue
            rows.append(
                {
                    "season": season,
                    "award": award_code,
                    "player_name": player_name,
                    "team_position": team_position.strip().rstrip(","),
                    "result": "finalist",
                    "source_url": url,
                }
            )
    return rows


def refresh_ap_awards_cache(cache_path: Path | None = None) -> pd.DataFrame:
    cache_path = cache_path or _default_awards_cache_path()
    rows: list[dict[str, object]] = []
    for row in AP_2021_WINNERS:
        rows.append({**row, "result": "winner", "source_url": AP_2021_SOURCE_URL})
    for season, url in AP_AWARD_URLS.items():
        rows.extend(_parse_nfl_awards_page(season, url))

    frame = pd.DataFrame(rows)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False, quoting=csv.QUOTE_MINIMAL)
    return frame


def load_ap_awards(cache_path: Path | None = None) -> pd.DataFrame:
    cache_path = cache_path or _default_awards_cache_path()
    if cache_path.exists():
        return pd.read_csv(cache_path)
    return refresh_ap_awards_cache(cache_path)


def build_awards_frame(draft_picks: pd.DataFrame, awards: pd.DataFrame | None = None) -> pd.DataFrame:
    awards = awards.copy() if awards is not None else load_ap_awards()
    base = draft_picks[["draft_player_id", "draft_year", "player_name"]].copy()
    base["normalized_name"] = base["player_name"].map(normalize_name)

    if awards.empty:
        matched = pd.DataFrame(columns=["draft_player_id", "award", "season"])
    else:
        awards["season"] = pd.to_numeric(awards["season"], errors="coerce").fillna(0).astype(int)
        awards["award"] = awards["award"].astype("string").fillna("")
        awards["normalized_name"] = awards["player_name"].map(normalize_name)
        matched = awards.merge(base, on="normalized_name", how="inner", suffixes=("_award", ""))
        matched = matched[matched["season"] >= matched["draft_year"].astype(int)].copy()

    rows: list[dict[str, object]] = []
    for draft_player_id in base["draft_player_id"]:
        player_awards = matched[matched["draft_player_id"] == draft_player_id].sort_values(["season", "award"])
        mvp_count = int((player_awards["award"] == "MVP").sum())
        other_count = int((player_awards["award"] != "MVP").sum())
        details = "; ".join(f"{int(row.season)} {row.award}" for row in player_awards.itertuples(index=False))
        rows.append(
            {
                "draft_player_id": int(draft_player_id),
                "top5_award_finish_count": other_count,
                "top5_mvp_finish_count": mvp_count,
                "ap_award_details": details,
            }
        )
    return pd.DataFrame(rows)
