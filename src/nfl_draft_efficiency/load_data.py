from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .normalize_ids import first_existing_column, normalize_name, normalize_position_group
from .teams import (
    normalize_roster_status,
    normalize_team_code,
    roster_status_bucket,
    roster_status_counts_as_with_team,
    roster_status_priority,
)


@dataclass
class RosterSnapshot:
    frame: pd.DataFrame
    snapshot_label: str
    source_name: str


DATASET_URLS = {
    "draft_picks": "https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.csv",
    "weekly_rosters": "https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_{season}.csv",
    "rosters": "https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{season}.csv",
    "snap_counts": "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{season}.csv",
    "games": "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
}


class NFLDataClient:
    def __init__(self, cache_dir: Path, force_refresh: bool = False) -> None:
        self.cache_dir = cache_dir
        self.force_refresh = force_refresh
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_draft_picks(self, years: list[int]) -> pd.DataFrame:
        cache_path = self.cache_dir / "draft_picks.csv"
        return self._load_or_fetch(
            cache_path=cache_path,
            fetcher=lambda seasons: self._read_csv(DATASET_URLS["draft_picks"]),
            required_seasons=years,
            season_column="season",
        )

    def load_snap_counts(self, years: list[int]) -> pd.DataFrame:
        cache_path = self.cache_dir / "snap_counts.csv"
        return self._load_or_fetch(
            cache_path=cache_path,
            fetcher=lambda seasons: self._fetch_seasoned_dataset("snap_counts", seasons),
            required_seasons=years,
            season_column="season",
        )

    def load_games(self, years: list[int]) -> pd.DataFrame:
        cache_path = self.cache_dir / "games.csv"
        return self._load_or_fetch(
            cache_path=cache_path,
            fetcher=lambda seasons: self._read_csv(DATASET_URLS["games"]),
            required_seasons=years,
            season_column="season",
        )

    def load_latest_roster_snapshot(self, anchor_year: int) -> RosterSnapshot:
        current_year = max(date.today().year, anchor_year)
        weekly_cache_path = self.cache_dir / "weekly_rosters.csv"
        yearly_cache_path = self.cache_dir / "rosters.csv"

        for year in range(current_year, anchor_year - 1, -1):
            try:
                rosters = self._load_or_fetch(
                    cache_path=weekly_cache_path,
                    fetcher=lambda seasons: self._fetch_seasoned_dataset("weekly_rosters", seasons),
                    required_seasons=[year],
                    season_column="season",
                )
            except Exception:
                rosters = pd.DataFrame()

            snapshot, label = self._extract_latest_weekly_snapshot(rosters)
            if not snapshot.empty:
                return RosterSnapshot(frame=snapshot, snapshot_label=label, source_name="nflverse weekly_rosters release CSV")

        for year in range(current_year, anchor_year - 1, -1):
            try:
                rosters = self._load_or_fetch(
                    cache_path=yearly_cache_path,
                    fetcher=lambda seasons: self._fetch_seasoned_dataset("rosters", seasons),
                    required_seasons=[year],
                    season_column="season",
                )
            except Exception:
                rosters = pd.DataFrame()

            snapshot, label = self._extract_latest_season_snapshot(rosters)
            if not snapshot.empty:
                return RosterSnapshot(frame=snapshot, snapshot_label=label, source_name="nflverse rosters release CSV")

        raise RuntimeError("Unable to load a roster snapshot from nflverse.")

    def _load_or_fetch(
        self,
        cache_path: Path,
        fetcher: Callable[[list[int]], pd.DataFrame],
        required_seasons: list[int],
        season_column: str,
    ) -> pd.DataFrame:
        if cache_path.exists() and not self.force_refresh:
            cached = self._read_csv(cache_path)
            if self._cache_covers_years(cached, required_seasons, season_column):
                return cached[cached[season_column].isin(required_seasons)].copy()

        fetched = fetcher(required_seasons)
        fetched.to_csv(cache_path, index=False)
        return fetched.copy()

    def _fetch_seasoned_dataset(self, dataset_key: str, seasons: list[int]) -> pd.DataFrame:
        url_template = DATASET_URLS[dataset_key]
        frames = [self._read_csv(url_template.format(season=season)) for season in seasons]
        return pd.concat(frames, ignore_index=True)

    @staticmethod
    def _read_csv(path_or_url: str | Path) -> pd.DataFrame:
        return pd.read_csv(path_or_url, low_memory=False)

    @staticmethod
    def _cache_covers_years(frame: pd.DataFrame, years: list[int], season_column: str) -> bool:
        if frame.empty or season_column not in frame.columns:
            return False
        cached_years = {int(year) for year in frame[season_column].dropna().astype(int).unique().tolist()}
        return set(years).issubset(cached_years)

    @staticmethod
    def _extract_latest_weekly_snapshot(frame: pd.DataFrame) -> tuple[pd.DataFrame, str]:
        if frame.empty or "season" not in frame.columns:
            return pd.DataFrame(), ""
        latest_season = int(frame["season"].dropna().astype(int).max())
        season_frame = frame[frame["season"].astype(int) == latest_season].copy()
        if "game_type" in season_frame.columns:
            regular_season = season_frame[season_frame["game_type"].astype("string").str.upper() == "REG"].copy()
            if not regular_season.empty:
                season_frame = regular_season
        week_column = first_existing_column(season_frame, ["week"])
        if not week_column or season_frame[week_column].dropna().empty:
            return season_frame, str(latest_season)
        latest_week = int(season_frame[week_column].dropna().astype(int).max())
        snapshot = season_frame[season_frame[week_column].astype(int) == latest_week].copy()
        return snapshot, f"{latest_season}-W{latest_week}"

    @staticmethod
    def _extract_latest_season_snapshot(frame: pd.DataFrame) -> tuple[pd.DataFrame, str]:
        if frame.empty or "season" not in frame.columns:
            return pd.DataFrame(), ""
        latest_season = int(frame["season"].dropna().astype(int).max())
        snapshot = frame[frame["season"].astype(int) == latest_season].copy()
        return snapshot, str(latest_season)


def _stringify_identifier(series: pd.Series) -> pd.Series:
    return (
        series.where(~series.isna(), None)
        .astype("string")
        .str.strip()
        .replace({"<NA>": None, "nan": None, "None": None, "": None})
    )


def standardize_draft_picks(frame: pd.DataFrame, years: list[int], config: dict[str, Any]) -> pd.DataFrame:
    required = ["season", "team", "round", "pick", "position", "gsis_id", "pfr_player_id", "allpro"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Draft picks data is missing required columns: {missing}")

    player_name_column = first_existing_column(frame, ["player_name", "pfr_player_name", "full_name", "name"])
    if not player_name_column:
        raise ValueError("Draft picks data is missing a player-name column.")

    standardized = frame[frame["season"].astype(int).isin(years)].copy()
    standardized = standardized.rename(columns={"season": "draft_year", "team": "draft_team"})
    standardized["draft_year"] = standardized["draft_year"].astype(int)
    standardized["draft_team"] = standardized["draft_team"].map(normalize_team_code)
    standardized["round"] = standardized["round"].astype(int)
    standardized["pick"] = standardized["pick"].astype(int)
    if "overall" in standardized.columns:
        standardized["overall"] = standardized["overall"].astype(int)
    else:
        standardized["overall"] = standardized["pick"].astype(int)
    standardized["gsis_id"] = _stringify_identifier(standardized["gsis_id"])
    standardized["pfr_player_id"] = _stringify_identifier(standardized["pfr_player_id"])
    standardized["player_name"] = standardized[player_name_column].astype("string").fillna("")
    standardized["position"] = standardized["position"].astype("string").fillna("")
    standardized["normalized_name"] = standardized["player_name"].map(normalize_name)
    standardized["position_group"] = standardized["position"].map(lambda value: normalize_position_group(value, config))
    standardized["draft_player_id"] = range(1, len(standardized) + 1)
    standardized = standardized.sort_values(["draft_year", "overall", "draft_player_id"]).reset_index(drop=True)
    return standardized


def standardize_roster_snapshot(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "gsis_id",
                "player_name",
                "team",
                "roster_status",
                "roster_status_description_abbr",
                "roster_status_bucket",
                "roster_status_priority",
                "counts_as_current_team",
                "position",
                "normalized_name",
                "position_group",
            ]
        )

    name_column = first_existing_column(frame, ["player_name", "full_name", "player", "name"])
    team_column = first_existing_column(frame, ["team", "team_abbr", "club_code", "recent_team"])
    gsis_candidates = [column for column in ["gsis_id", "esb_id", "player_id", "gsis_it_id"] if column in frame.columns]
    position_column = first_existing_column(frame, ["position"])

    if not name_column or not team_column:
        raise ValueError("Roster snapshot is missing player-name or team columns.")

    standardized = frame.copy()
    standardized["player_name"] = standardized[name_column].astype("string").fillna("")
    standardized["team"] = standardized[team_column].map(normalize_team_code)
    if gsis_candidates:
        gsis_frame = standardized[gsis_candidates].copy()
        for column in gsis_candidates:
            gsis_frame[column] = _stringify_identifier(gsis_frame[column])
        standardized["gsis_id"] = gsis_frame.bfill(axis=1).iloc[:, 0]
    else:
        standardized["gsis_id"] = None
    standardized["roster_status"] = (
        standardized["status"].map(normalize_roster_status)
        if "status" in standardized.columns
        else pd.Series("", index=standardized.index, dtype="string")
    )
    standardized["roster_status_description_abbr"] = (
        standardized["status_description_abbr"].astype("string").fillna("")
        if "status_description_abbr" in standardized.columns
        else ""
    )
    standardized["roster_status_bucket"] = standardized["roster_status"].map(roster_status_bucket)
    standardized["roster_status_priority"] = standardized["roster_status"].map(roster_status_priority)
    standardized["counts_as_current_team"] = standardized["roster_status"].map(roster_status_counts_as_with_team)
    standardized["position"] = standardized[position_column].astype("string").fillna("") if position_column else ""
    standardized["normalized_name"] = standardized["player_name"].map(normalize_name)
    standardized["position_group"] = standardized["position"].map(lambda value: normalize_position_group(value, config))
    return standardized[
        [
            "gsis_id",
            "player_name",
            "team",
            "roster_status",
            "roster_status_description_abbr",
            "roster_status_bucket",
            "roster_status_priority",
            "counts_as_current_team",
            "position",
            "normalized_name",
            "position_group",
        ]
    ].drop_duplicates()


def standardize_snap_counts(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    required = [
        "season",
        "week",
        "team",
        "player",
        "pfr_player_id",
        "position",
        "offense_pct",
        "defense_pct",
        "st_pct",
    ]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Snap-count data is missing required columns: {missing}")

    standardized = frame.copy()
    if "game_type" in standardized.columns:
        standardized = standardized[standardized["game_type"].astype("string").str.upper() == "REG"].copy()

    standardized["season"] = standardized["season"].astype(int)
    standardized["week"] = standardized["week"].astype(int)
    standardized["team"] = standardized["team"].map(normalize_team_code)
    standardized["player"] = standardized["player"].astype("string").fillna("")
    standardized["pfr_player_id"] = _stringify_identifier(standardized["pfr_player_id"])
    standardized["position"] = standardized["position"].astype("string").fillna("")
    standardized["normalized_name"] = standardized["player"].map(normalize_name)
    standardized["position_group"] = standardized["position"].map(lambda value: normalize_position_group(value, config))

    for column in ["offense_pct", "defense_pct", "st_pct"]:
        standardized[column] = pd.to_numeric(standardized[column], errors="coerce").fillna(0.0)

    for column in ["offense_snaps", "defense_snaps", "st_snaps"]:
        if column not in standardized.columns:
            standardized[column] = 0.0
        standardized[column] = pd.to_numeric(standardized[column], errors="coerce").fillna(0.0)

    return standardized


def standardize_games(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["season", "game_type", "week", "home_team", "away_team", "home_score", "away_score"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Game data is missing required columns: {missing}")

    standardized = frame.copy()
    standardized = standardized[standardized["game_type"].astype("string").str.upper() == "REG"].copy()
    standardized["season"] = standardized["season"].astype(int)
    standardized["week"] = pd.to_numeric(standardized["week"], errors="coerce").fillna(0).astype(int)
    standardized["home_team"] = standardized["home_team"].map(normalize_team_code)
    standardized["away_team"] = standardized["away_team"].map(normalize_team_code)
    standardized["home_score"] = pd.to_numeric(standardized["home_score"], errors="coerce")
    standardized["away_score"] = pd.to_numeric(standardized["away_score"], errors="coerce")
    standardized = standardized.dropna(subset=["home_score", "away_score"])
    return standardized[
        [
            "season",
            "week",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
        ]
    ].copy()


def build_team_records(games: pd.DataFrame) -> pd.DataFrame:
    if games.empty:
        return pd.DataFrame(columns=["season", "team", "wins", "losses", "ties", "games", "win_pct"])

    home = games[["season", "home_team", "home_score", "away_score"]].copy()
    home["team"] = home["home_team"]
    home["wins"] = (home["home_score"] > home["away_score"]).astype(int)
    home["losses"] = (home["home_score"] < home["away_score"]).astype(int)
    home["ties"] = (home["home_score"] == home["away_score"]).astype(int)

    away = games[["season", "away_team", "away_score", "home_score"]].copy()
    away["team"] = away["away_team"]
    away["wins"] = (away["away_score"] > away["home_score"]).astype(int)
    away["losses"] = (away["away_score"] < away["home_score"]).astype(int)
    away["ties"] = (away["away_score"] == away["home_score"]).astype(int)

    records = pd.concat(
        [
            home[["season", "team", "wins", "losses", "ties"]],
            away[["season", "team", "wins", "losses", "ties"]],
        ],
        ignore_index=True,
    )

    records = records.groupby(["season", "team"], dropna=False).agg(
        wins=("wins", "sum"),
        losses=("losses", "sum"),
        ties=("ties", "sum"),
    ).reset_index()
    records["games"] = records["wins"] + records["losses"] + records["ties"]
    records["win_pct"] = (
        records["wins"] + 0.5 * records["ties"]
    ) / records["games"].where(records["games"] > 0, 1)
    return records[["season", "team", "wins", "losses", "ties", "games", "win_pct"]]


def match_latest_roster_snapshot(draft_picks: pd.DataFrame, roster_snapshot: pd.DataFrame) -> pd.DataFrame:
    base = draft_picks[["draft_player_id", "draft_team", "gsis_id", "normalized_name", "position_group"]].copy()
    base["draft_team"] = base["draft_team"].map(normalize_team_code)
    base["latest_roster_team"] = pd.NA
    base["latest_team"] = pd.NA
    base["latest_roster_status"] = pd.NA
    base["latest_roster_status_description_abbr"] = pd.NA
    base["latest_roster_status_bucket"] = pd.NA
    base["roster_match_method"] = "unmatched"
    base["has_roster_match"] = False
    base["has_current_roster_match"] = False

    if not roster_snapshot.empty and "gsis_id" in roster_snapshot.columns:
        roster_id_matches = (
            roster_snapshot.dropna(subset=["gsis_id"])
            .sort_values(["roster_status_priority", "team", "player_name"], ascending=[False, True, True])
            .drop_duplicates(subset=["gsis_id"])
            .set_index("gsis_id")
        )
        exact_mask = base["gsis_id"].notna() & base["gsis_id"].isin(roster_id_matches.index)
        base.loc[exact_mask, "latest_roster_team"] = base.loc[exact_mask, "gsis_id"].map(roster_id_matches["team"])
        base.loc[exact_mask, "latest_roster_status"] = base.loc[exact_mask, "gsis_id"].map(roster_id_matches["roster_status"])
        base.loc[exact_mask, "latest_roster_status_description_abbr"] = base.loc[exact_mask, "gsis_id"].map(
            roster_id_matches["roster_status_description_abbr"]
        )
        base.loc[exact_mask, "latest_roster_status_bucket"] = base.loc[exact_mask, "gsis_id"].map(
            roster_id_matches["roster_status_bucket"]
        )
        base.loc[exact_mask, "roster_match_method"] = "gsis_id"
        base.loc[exact_mask, "has_roster_match"] = True

        exact_current_mask = exact_mask & base["gsis_id"].map(roster_id_matches["counts_as_current_team"]).fillna(False)
        base.loc[exact_current_mask, "latest_team"] = base.loc[exact_current_mask, "latest_roster_team"]
        base.loc[exact_current_mask, "has_current_roster_match"] = True

    unresolved = ~base["has_current_roster_match"]
    if unresolved.any() and not roster_snapshot.empty:
        current_roster = roster_snapshot[roster_snapshot["counts_as_current_team"]].copy()
        unique_roster = (
            current_roster.sort_values(["roster_status_priority", "team"], ascending=[False, True])
            .groupby(["normalized_name", "position_group"])
            .agg(
                team_nunique=("team", "nunique"),
                latest_roster_team=("team", "first"),
                latest_roster_status=("roster_status", "first"),
                latest_roster_status_description_abbr=("roster_status_description_abbr", "first"),
                latest_roster_status_bucket=("roster_status_bucket", "first"),
            )
            .reset_index()
        )
        unique_roster = unique_roster[unique_roster["team_nunique"] == 1]
        fallback_map = {
            (row["normalized_name"], row["position_group"]): {
                "latest_roster_team": row["latest_roster_team"],
                "latest_roster_status": row["latest_roster_status"],
                "latest_roster_status_description_abbr": row["latest_roster_status_description_abbr"],
                "latest_roster_status_bucket": row["latest_roster_status_bucket"],
            }
            for _, row in unique_roster.iterrows()
        }
        fallback_indexes = base.index[unresolved]
        for index in fallback_indexes:
            fallback_key = (base.at[index, "normalized_name"], base.at[index, "position_group"])
            fallback_value = fallback_map.get(fallback_key)
            if not fallback_value:
                continue
            base.at[index, "latest_roster_team"] = fallback_value["latest_roster_team"]
            base.at[index, "latest_team"] = fallback_value["latest_roster_team"]
            base.at[index, "latest_roster_status"] = fallback_value["latest_roster_status"]
            base.at[index, "latest_roster_status_description_abbr"] = fallback_value[
                "latest_roster_status_description_abbr"
            ]
            base.at[index, "latest_roster_status_bucket"] = fallback_value["latest_roster_status_bucket"]
            base.at[index, "roster_match_method"] = "name_position_fallback"
            base.at[index, "has_roster_match"] = True
            base.at[index, "has_current_roster_match"] = True

    base["still_on_drafting_team"] = base["latest_team"].fillna("") == base["draft_team"].fillna("")
    return base[
        [
            "draft_player_id",
            "latest_roster_team",
            "latest_team",
            "latest_roster_status",
            "latest_roster_status_description_abbr",
            "latest_roster_status_bucket",
            "still_on_drafting_team",
            "has_roster_match",
            "has_current_roster_match",
            "roster_match_method",
        ]
    ]


def build_unmatched_players(
    draft_picks: pd.DataFrame,
    roster_matches: pd.DataFrame,
    starter_flags: pd.DataFrame,
) -> pd.DataFrame:
    frame = draft_picks.merge(
        roster_matches[["draft_player_id", "has_roster_match"]],
        on="draft_player_id",
        how="left",
    ).merge(
        starter_flags[["draft_player_id", "has_snap_match"]],
        on="draft_player_id",
        how="left",
    )

    reasons: list[dict[str, Any]] = []
    for row in frame.itertuples(index=False):
        has_roster_match = bool(row.has_roster_match) if pd.notna(row.has_roster_match) else False
        has_snap_match = bool(row.has_snap_match) if pd.notna(row.has_snap_match) else False
        reason_parts: list[str] = []
        if pd.isna(row.gsis_id) and pd.isna(row.pfr_player_id):
            reason_parts.append("missing_gsis_id_and_pfr_player_id")
        if not has_roster_match and not has_snap_match:
            reason_parts.append("no_roster_snapshot_match_and_no_snap_count_match")
        elif not has_snap_match and pd.isna(row.pfr_player_id):
            reason_parts.append("no_snap_count_match")

        if reason_parts:
            reasons.append(
                {
                    "draft_year": row.draft_year,
                    "draft_team": row.draft_team,
                    "round": row.round,
                    "pick": row.pick,
                    "player_name": row.player_name,
                    "position": row.position,
                    "gsis_id": row.gsis_id,
                    "pfr_player_id": row.pfr_player_id,
                    "reason": "; ".join(reason_parts),
                }
            )

    return pd.DataFrame(
        reasons,
        columns=[
            "draft_year",
            "draft_team",
            "round",
            "pick",
            "player_name",
            "position",
            "gsis_id",
            "pfr_player_id",
            "reason",
        ],
    )
