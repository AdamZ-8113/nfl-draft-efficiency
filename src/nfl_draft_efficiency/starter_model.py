from __future__ import annotations

from typing import Any

import pandas as pd

from .normalize_ids import normalize_name, normalize_position_group
from .teams import normalize_team_code


def _ensure_matching_columns(frame: pd.DataFrame, config: dict[str, Any], is_draft: bool) -> pd.DataFrame:
    standardized = frame.copy()

    if is_draft:
        if "draft_player_id" not in standardized.columns:
            standardized["draft_player_id"] = range(1, len(standardized) + 1)
        if "draft_team" in standardized.columns:
            standardized["draft_team"] = standardized["draft_team"].map(normalize_team_code)
        if "normalized_name" not in standardized.columns:
            standardized["normalized_name"] = standardized["player_name"].map(normalize_name)
        if "position_group" not in standardized.columns:
            standardized["position_group"] = standardized["position"].map(lambda value: normalize_position_group(value, config))
    else:
        if "team" in standardized.columns:
            standardized["team"] = standardized["team"].map(normalize_team_code)
        if "normalized_name" not in standardized.columns:
            standardized["normalized_name"] = standardized["player"].map(normalize_name)
        if "position_group" not in standardized.columns:
            standardized["position_group"] = standardized["position"].map(lambda value: normalize_position_group(value, config))

    return standardized


def _games_above_threshold(series: pd.Series, min_pct: float) -> int:
    values = series.fillna(0)
    if not values.empty and values.max() <= 1.5 and min_pct > 1:
        values = values * 100.0
    return int(values.ge(min_pct).sum())


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _build_team_game_snap_totals(snap_counts: pd.DataFrame) -> pd.DataFrame:
    if snap_counts.empty:
        return pd.DataFrame(
            columns=[
                "season",
                "week",
                "team",
                "team_offense_snaps",
                "team_defense_snaps",
                "team_st_snaps",
            ]
        )
    return (
        snap_counts.groupby(["season", "week", "team"], dropna=False)
        .agg(
            team_offense_snaps=("offense_snaps", "max"),
            team_defense_snaps=("defense_snaps", "max"),
            team_st_snaps=("st_snaps", "max"),
        )
        .reset_index()
    )


def _usage_side_for_position_group(position_group: str, config: dict[str, Any]) -> str:
    thresholds = config["starter_thresholds"]
    fallback = config["fallback_starter_threshold"]
    rule = thresholds.get(position_group, fallback)
    side = str(rule["side"]).lower()
    if side in {"offense", "defense", "special"}:
        return side
    return "either"


def _season_team_snap_share(group: pd.DataFrame, position_group: str, config: dict[str, Any]) -> tuple[float, float]:
    side = _usage_side_for_position_group(position_group, config)

    offense_share = _safe_ratio(float(group["offense_snaps"].sum()), float(group["team_offense_snaps"].sum()))
    defense_share = _safe_ratio(float(group["defense_snaps"].sum()), float(group["team_defense_snaps"].sum()))
    special_share = _safe_ratio(float(group["st_snaps"].sum()), float(group["team_st_snaps"].sum()))

    if side == "offense":
        return offense_share, float(group["offense_snaps"].sum())
    if side == "defense":
        return defense_share, float(group["defense_snaps"].sum())
    if side == "special":
        return special_share, float(group["st_snaps"].sum())

    candidate_shares = [
        (offense_share, float(group["offense_snaps"].sum())),
        (defense_share, float(group["defense_snaps"].sum())),
        (special_share, float(group["st_snaps"].sum())),
    ]
    return max(candidate_shares, key=lambda item: item[0])


def qualifies_by_position_threshold(frame: pd.DataFrame, position_group: str, config: dict[str, Any]) -> bool:
    thresholds = config["starter_thresholds"]
    fallback = config["fallback_starter_threshold"]
    rule = thresholds.get(position_group, fallback)
    side = str(rule["side"]).lower()
    min_pct = float(rule["min_pct"])
    min_games = int(rule["min_games"])

    if side == "offense":
        return _games_above_threshold(frame["offense_pct"], min_pct) >= min_games
    if side == "defense":
        return _games_above_threshold(frame["defense_pct"], min_pct) >= min_games
    if side == "special":
        return False

    offense_games = _games_above_threshold(frame["offense_pct"], min_pct)
    defense_games = _games_above_threshold(frame["defense_pct"], min_pct)
    return offense_games >= min_games or defense_games >= min_games


def _match_snap_rows_to_draft_players(snap_counts: pd.DataFrame, draft_picks: pd.DataFrame) -> pd.DataFrame:
    exact_matches = pd.DataFrame()
    if "pfr_player_id" in draft_picks.columns and "pfr_player_id" in snap_counts.columns:
        draft_exact = draft_picks[draft_picks["pfr_player_id"].notna()].copy()
        snap_exact = snap_counts[snap_counts["pfr_player_id"].notna()].copy()
        exact_matches = snap_exact.merge(
            draft_exact[
                [
                    "draft_player_id",
                    "pfr_player_id",
                    "draft_year",
                    "draft_team",
                    "player_name",
                    "position_group",
                ]
            ].rename(columns={"position_group": "draft_position_group", "player_name": "draft_player_name"}),
            on="pfr_player_id",
            how="inner",
        )
        exact_matches["snap_match_method"] = "pfr_player_id"

    matched_player_ids = set(exact_matches["draft_player_id"].unique().tolist()) if not exact_matches.empty else set()

    fallback_drafts = draft_picks[~draft_picks["draft_player_id"].isin(matched_player_ids)].copy()
    if fallback_drafts.empty:
        combined = exact_matches
    else:
        unique_drafts = (
            fallback_drafts.groupby(["normalized_name", "position_group"])["draft_player_id"]
            .agg(["nunique", "first"])
            .reset_index()
        )
        unique_drafts = unique_drafts[unique_drafts["nunique"] == 1].rename(columns={"first": "draft_player_id"})
        fallback = snap_counts.merge(unique_drafts[["normalized_name", "position_group", "draft_player_id"]], on=["normalized_name", "position_group"], how="inner")
        fallback = fallback.merge(
            fallback_drafts[["draft_player_id", "draft_year", "draft_team", "player_name", "position_group"]].rename(
                columns={"position_group": "draft_position_group", "player_name": "draft_player_name"}
            ),
            on="draft_player_id",
            how="inner",
        )
        fallback = fallback[fallback["season"] >= fallback["draft_year"]].copy()
        fallback["snap_match_method"] = "name_position_fallback"
        combined = pd.concat([exact_matches, fallback], ignore_index=True, sort=False)

    if combined.empty:
        return pd.DataFrame(
            columns=[
                "draft_player_id",
                "season",
                "team",
                "position_group",
                "draft_position_group",
                "offense_pct",
                "defense_pct",
                "st_pct",
                "snap_match_method",
            ]
        )

    combined = combined.drop_duplicates(
        subset=["draft_player_id", "season", "week", "team", "player", "pfr_player_id"]
    ).copy()
    return combined


def compute_starter_flags(
    snap_counts: pd.DataFrame,
    draft_picks: pd.DataFrame,
    config: dict[str, Any],
    team_records: pd.DataFrame | None = None,
) -> pd.DataFrame:
    snap_counts = _ensure_matching_columns(snap_counts, config, is_draft=False)
    draft_picks = _ensure_matching_columns(draft_picks, config, is_draft=True)

    team_game_totals = _build_team_game_snap_totals(snap_counts)
    matched_snaps = _match_snap_rows_to_draft_players(snap_counts, draft_picks)
    if matched_snaps.empty:
        empty = draft_picks[["draft_player_id"]].copy()
        empty["starter_with_drafting_team"] = False
        empty["starter_with_any_team"] = False
        empty["starter_seasons_with_drafting_team"] = 0
        empty["starter_seasons_with_any_team"] = 0
        empty["special_teams_contributor"] = False
        empty["has_snap_match"] = False
        empty["snap_match_method"] = "unmatched"
        empty["total_relevant_snaps_with_drafting_team"] = 0.0
        empty["total_relevant_snaps_any_team"] = 0.0
        empty["snap_share_with_drafting_team"] = 0.0
        empty["snap_share_elsewhere"] = 0.0
        empty["peak_season_snap_share_with_drafting_team"] = 0.0
        empty["peak_season_snap_share_any_team"] = 0.0
        empty["record_adjusted_snap_share_with_drafting_team"] = 0.0
        empty["record_adjusted_snap_share_elsewhere"] = 0.0
        empty["weighted_win_pct_with_drafting_team"] = None
        return empty

    matched_snaps["effective_position_group"] = matched_snaps["position_group"].where(
        matched_snaps["position_group"].ne("UNKNOWN"), matched_snaps["draft_position_group"]
    )
    matched_snaps = matched_snaps.merge(team_game_totals, on=["season", "week", "team"], how="left")

    season_team_rows: list[dict[str, Any]] = []
    special_rule = config["special_teams_threshold"]
    special_min_pct = float(special_rule["min_pct"])
    special_min_games = int(special_rule["min_games"])
    record_config = config.get("team_record_adjustment", {})
    record_weight = float(record_config.get("win_pct_multiplier_weight", 0.15))
    min_multiplier = float(record_config.get("min_multiplier", 0.9))
    max_multiplier = float(record_config.get("max_multiplier", 1.1))
    record_map: dict[tuple[int, str], float] = {}
    if team_records is not None and not team_records.empty:
        record_map = {
            (int(row["season"]), str(row["team"])): float(row["win_pct"])
            for _, row in team_records.iterrows()
        }

    grouped = matched_snaps.groupby(["draft_player_id", "draft_team", "season", "team", "effective_position_group"], dropna=False)
    for (draft_player_id, draft_team, season, team, position_group), group in grouped:
        qualifies = qualifies_by_position_threshold(group, str(position_group), config)
        special_games = _games_above_threshold(group["st_pct"], special_min_pct)
        season_snap_share, relevant_snaps = _season_team_snap_share(group, str(position_group), config)
        team_win_pct = record_map.get((int(season), str(team)), 0.5)
        record_multiplier = 1.0 + record_weight * (team_win_pct - 0.5)
        record_multiplier = min(max(record_multiplier, min_multiplier), max_multiplier)
        season_team_rows.append(
            {
                "draft_player_id": draft_player_id,
                "draft_team": draft_team,
                "season": season,
                "team": team,
                "qualifies_starter": qualifies,
                "special_teams_contributor": special_games >= special_min_games,
                "relevant_snaps": relevant_snaps,
                "season_team_snap_share": season_snap_share,
                "team_win_pct": team_win_pct,
                "record_adjustment_multiplier": record_multiplier,
                "record_adjusted_season_team_snap_share": season_snap_share * record_multiplier,
            }
        )

    season_team = pd.DataFrame(season_team_rows)
    starter_seasons = season_team[season_team["qualifies_starter"]].copy()

    by_player = draft_picks[["draft_player_id", "draft_team"]].copy()
    by_player["starter_with_drafting_team"] = False
    by_player["starter_with_any_team"] = False
    by_player["starter_seasons_with_drafting_team"] = 0
    by_player["starter_seasons_with_any_team"] = 0
    by_player["special_teams_contributor"] = False
    by_player["total_relevant_snaps_with_drafting_team"] = 0.0
    by_player["total_relevant_snaps_any_team"] = 0.0
    by_player["snap_share_with_drafting_team"] = 0.0
    by_player["snap_share_elsewhere"] = 0.0
    by_player["peak_season_snap_share_with_drafting_team"] = 0.0
    by_player["peak_season_snap_share_any_team"] = 0.0
    by_player["record_adjusted_snap_share_with_drafting_team"] = 0.0
    by_player["record_adjusted_snap_share_elsewhere"] = 0.0
    by_player["weighted_win_pct_with_drafting_team"] = None

    if not starter_seasons.empty:
        drafting_team_counts = (
            starter_seasons[starter_seasons["team"] == starter_seasons["draft_team"]]
            .groupby("draft_player_id")["season"]
            .nunique()
        )
        any_team_counts = starter_seasons.groupby("draft_player_id")["season"].nunique()

        by_player.loc[by_player["draft_player_id"].isin(drafting_team_counts.index), "starter_with_drafting_team"] = True
        by_player.loc[by_player["draft_player_id"].isin(any_team_counts.index), "starter_with_any_team"] = True
        by_player.loc[
            by_player["draft_player_id"].isin(drafting_team_counts.index), "starter_seasons_with_drafting_team"
        ] = by_player["draft_player_id"].map(drafting_team_counts).fillna(0).astype(int)
        by_player.loc[
            by_player["draft_player_id"].isin(any_team_counts.index), "starter_seasons_with_any_team"
        ] = by_player["draft_player_id"].map(any_team_counts).fillna(0).astype(int)

    season_team["is_drafting_team"] = season_team["team"] == season_team["draft_team"]
    season_team["win_pct_weighted_share"] = season_team["team_win_pct"] * season_team["season_team_snap_share"]

    draft_snap_totals = (
        season_team[season_team["is_drafting_team"]]
        .groupby("draft_player_id")["relevant_snaps"]
        .sum()
    )
    any_snap_totals = season_team.groupby("draft_player_id")["relevant_snaps"].sum()
    draft_snap_share = (
        season_team[season_team["is_drafting_team"]]
        .groupby("draft_player_id")["season_team_snap_share"]
        .sum()
    )
    any_snap_share = season_team.groupby("draft_player_id")["season_team_snap_share"].sum()
    draft_adjusted_snap_share = (
        season_team[season_team["is_drafting_team"]]
        .groupby("draft_player_id")["record_adjusted_season_team_snap_share"]
        .sum()
    )
    any_adjusted_snap_share = season_team.groupby("draft_player_id")["record_adjusted_season_team_snap_share"].sum()
    peak_draft_snap_share = (
        season_team[season_team["is_drafting_team"]]
        .groupby("draft_player_id")["season_team_snap_share"]
        .max()
    )
    peak_any_snap_share = season_team.groupby("draft_player_id")["season_team_snap_share"].max()
    weighted_win_num = (
        season_team[season_team["is_drafting_team"]]
        .groupby("draft_player_id")["win_pct_weighted_share"]
        .sum()
    )
    weighted_win_den = (
        season_team[season_team["is_drafting_team"]]
        .groupby("draft_player_id")["season_team_snap_share"]
        .sum()
    )
    weighted_win_pct = (weighted_win_num / weighted_win_den.where(weighted_win_den > 0)).dropna()

    by_player["total_relevant_snaps_with_drafting_team"] = by_player["draft_player_id"].map(draft_snap_totals).fillna(0.0)
    by_player["total_relevant_snaps_any_team"] = by_player["draft_player_id"].map(any_snap_totals).fillna(0.0)
    by_player["snap_share_with_drafting_team"] = by_player["draft_player_id"].map(draft_snap_share).fillna(0.0)
    by_player["snap_share_elsewhere"] = (
        by_player["draft_player_id"].map(any_snap_share).fillna(0.0)
        - by_player["draft_player_id"].map(draft_snap_share).fillna(0.0)
    ).clip(lower=0.0)
    by_player["peak_season_snap_share_with_drafting_team"] = by_player["draft_player_id"].map(peak_draft_snap_share).fillna(0.0)
    by_player["peak_season_snap_share_any_team"] = by_player["draft_player_id"].map(peak_any_snap_share).fillna(0.0)
    by_player["record_adjusted_snap_share_with_drafting_team"] = by_player["draft_player_id"].map(
        draft_adjusted_snap_share
    ).fillna(0.0)
    by_player["record_adjusted_snap_share_elsewhere"] = (
        by_player["draft_player_id"].map(any_adjusted_snap_share).fillna(0.0)
        - by_player["draft_player_id"].map(draft_adjusted_snap_share).fillna(0.0)
    ).clip(lower=0.0)
    by_player.loc[
        by_player["draft_player_id"].isin(weighted_win_pct.index),
        "weighted_win_pct_with_drafting_team",
    ] = by_player["draft_player_id"].map(weighted_win_pct)

    special_counts = season_team.groupby("draft_player_id")["special_teams_contributor"].any()
    by_player["special_teams_contributor"] = by_player["draft_player_id"].map(special_counts).fillna(False)

    match_methods = matched_snaps.groupby("draft_player_id")["snap_match_method"].agg(
        lambda values: "pfr_player_id" if "pfr_player_id" in set(values) else "name_position_fallback"
    )
    by_player["has_snap_match"] = by_player["draft_player_id"].isin(match_methods.index)
    by_player["snap_match_method"] = by_player["draft_player_id"].map(match_methods).fillna("unmatched")

    return by_player[
        [
            "draft_player_id",
            "starter_with_drafting_team",
            "starter_with_any_team",
            "starter_seasons_with_drafting_team",
            "starter_seasons_with_any_team",
            "special_teams_contributor",
            "has_snap_match",
            "snap_match_method",
            "total_relevant_snaps_with_drafting_team",
            "total_relevant_snaps_any_team",
            "snap_share_with_drafting_team",
            "snap_share_elsewhere",
            "peak_season_snap_share_with_drafting_team",
            "peak_season_snap_share_any_team",
            "record_adjusted_snap_share_with_drafting_team",
            "record_adjusted_snap_share_elsewhere",
            "weighted_win_pct_with_drafting_team",
        ]
    ]
