from __future__ import annotations

import math
from typing import Any

import pandas as pd


def get_pick_cost(round_value: int, config: dict[str, Any]) -> float:
    cost_map = config["round_pick_cost"]
    if round_value not in cost_map:
        raise ValueError(f"Unsupported draft round: {round_value}")
    return float(cost_map[round_value])


def _normalization_divisor(eligible_seasons: int, method: str) -> float:
    if method == "sqrt":
        return math.sqrt(eligible_seasons)
    if method == "linear":
        return float(eligible_seasons)
    raise ValueError(f"Unsupported normalization method: {method}")


def build_player_scores(
    draft_picks: pd.DataFrame,
    roster_matches: pd.DataFrame,
    starter_flags: pd.DataFrame,
    honors: pd.DataFrame,
    awards: pd.DataFrame,
    latest_completed_season: int,
    config: dict[str, Any],
) -> pd.DataFrame:
    frame = (
        draft_picks.merge(roster_matches, on="draft_player_id", how="left")
        .merge(starter_flags, on="draft_player_id", how="left")
        .merge(honors, on="draft_player_id", how="left")
        .merge(awards, on="draft_player_id", how="left")
    )

    default_columns = {
        "latest_roster_team": None,
        "latest_roster_status": None,
        "latest_roster_status_description_abbr": None,
        "latest_roster_status_bucket": None,
        "has_roster_match": False,
        "has_current_roster_match": False,
        "roster_match_method": "unmatched",
        "has_snap_match": False,
        "snap_match_method": "unmatched",
        "total_relevant_snaps_with_drafting_team": 0.0,
        "total_relevant_snaps_any_team": 0.0,
        "snap_share_with_drafting_team": 0.0,
        "snap_share_elsewhere": 0.0,
        "peak_season_snap_share_with_drafting_team": 0.0,
        "peak_season_snap_share_any_team": 0.0,
        "record_adjusted_snap_share_with_drafting_team": 0.0,
        "record_adjusted_snap_share_elsewhere": 0.0,
        "weighted_win_pct_with_drafting_team": None,
    }
    for column, default_value in default_columns.items():
        if column not in frame.columns:
            frame[column] = default_value

    points = config["points"]
    caps = config["caps"]
    normalization = config["opportunity_normalization"]
    method = str(normalization["method"]).lower()
    max_seasons = int(normalization["max_seasons"])
    snap_share_value = config.get("snap_share_value", {})
    snap_share_points_with_drafting_team = float(
        snap_share_value.get("with_drafting_team_per_full_season", 1.0)
    )
    snap_share_points_with_any_team = float(
        snap_share_value.get("with_any_team_per_full_season", 0.35)
    )

    bool_columns = [
        "still_on_drafting_team",
        "starter_with_drafting_team",
        "starter_with_any_team",
        "special_teams_contributor",
        "has_roster_match",
        "has_current_roster_match",
        "has_snap_match",
    ]
    for column in bool_columns:
        frame[column] = frame[column].fillna(False).astype(bool)

    int_columns = [
        "starter_seasons_with_drafting_team",
        "starter_seasons_with_any_team",
        "first_team_all_pro_count",
        "second_team_all_pro_count",
        "top5_award_finish_count",
        "top5_mvp_finish_count",
    ]
    for column in int_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype(int)

    float_columns = [
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
    for column in float_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["eligible_seasons"] = (
        latest_completed_season - frame["draft_year"].astype(int) + 1
    ).clip(lower=1, upper=max_seasons)
    frame["opportunity_divisor"] = frame["eligible_seasons"].map(lambda value: _normalization_divisor(int(value), method))

    frame["retention_points_raw"] = frame["still_on_drafting_team"].astype(float) * float(points["still_on_drafting_team"])
    frame["starter_points_raw"] = 0.0
    frame.loc[frame["starter_with_drafting_team"], "starter_points_raw"] = float(points["starter_with_drafting_team"])
    frame.loc[
        ~frame["starter_with_drafting_team"] & frame["starter_with_any_team"],
        "starter_points_raw",
    ] = float(points["starter_with_any_team"])

    frame["snap_share_points_raw"] = (
        frame["record_adjusted_snap_share_with_drafting_team"].fillna(0.0) * snap_share_points_with_drafting_team
        + frame["record_adjusted_snap_share_elsewhere"].fillna(0.0) * snap_share_points_with_any_team
    )

    frame["all_pro_points_raw"] = (
        frame["first_team_all_pro_count"] * float(points["first_team_all_pro"])
        + frame["second_team_all_pro_count"] * float(points["second_team_all_pro"])
    ).clip(upper=float(caps["max_all_pro_points_per_player"]))

    frame["award_points_raw"] = (
        frame["top5_award_finish_count"] * float(points["top5_award_finish"])
        + frame["top5_mvp_finish_count"] * float(points["top5_mvp_finish"])
    ).clip(upper=float(caps["max_award_points_per_player"]))

    frame["star_points_raw"] = frame["all_pro_points_raw"] + frame["award_points_raw"]
    frame["raw_player_score"] = (
        frame["retention_points_raw"]
        + frame["starter_points_raw"]
        + frame["snap_share_points_raw"]
        + frame["star_points_raw"]
    )

    frame["retention_points"] = frame["retention_points_raw"] / frame["opportunity_divisor"]
    frame["starter_points"] = frame["starter_points_raw"] / frame["opportunity_divisor"]
    frame["snap_share_points"] = frame["snap_share_points_raw"] / frame["opportunity_divisor"]
    frame["star_points"] = frame["star_points_raw"] / frame["opportunity_divisor"]
    frame["normalized_player_score"] = frame["raw_player_score"] / frame["opportunity_divisor"]
    frame["pick_cost"] = frame["round"].map(lambda value: get_pick_cost(int(value), config))

    frame["latest_team"] = frame["latest_team"].where(frame["latest_team"].notna(), None)

    return frame[
        [
            "draft_player_id",
            "draft_year",
            "draft_team",
            "round",
            "pick",
            "overall",
            "player_name",
            "position",
            "gsis_id",
            "pfr_player_id",
            "latest_roster_team",
            "latest_team",
            "latest_roster_status",
            "latest_roster_status_description_abbr",
            "latest_roster_status_bucket",
            "still_on_drafting_team",
            "has_roster_match",
            "has_current_roster_match",
            "roster_match_method",
            "starter_with_drafting_team",
            "starter_with_any_team",
            "starter_seasons_with_drafting_team",
            "starter_seasons_with_any_team",
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
            "first_team_all_pro_count",
            "second_team_all_pro_count",
            "top5_award_finish_count",
            "top5_mvp_finish_count",
            "eligible_seasons",
            "retention_points_raw",
            "starter_points_raw",
            "snap_share_points_raw",
            "all_pro_points_raw",
            "award_points_raw",
            "retention_points",
            "starter_points",
            "snap_share_points",
            "star_points_raw",
            "star_points",
            "raw_player_score",
            "normalized_player_score",
            "pick_cost",
        ]
    ]
