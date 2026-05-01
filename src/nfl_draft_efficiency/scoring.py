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


def _build_bust_mask(frame: pd.DataFrame, config: dict[str, Any]) -> pd.Series:
    bust_config = config.get("early_round_bust_adjustment", {})
    if not bust_config.get("enabled", False):
        return pd.Series(False, index=frame.index)

    rounds = {int(round_value) for round_value in bust_config.get("rounds", [])}
    min_eligible_seasons = int(bust_config.get("min_eligible_seasons", 2))
    max_peak_snap_share = float(bust_config.get("max_peak_snap_share_any_team", 0.35))
    count_starter_elsewhere_as_non_bust = bool(bust_config.get("count_starter_elsewhere_as_non_bust", True))
    count_honors_as_non_bust = bool(bust_config.get("count_honors_as_non_bust", True))

    starter_column = "starter_with_any_team" if count_starter_elsewhere_as_non_bust else "starter_with_drafting_team"
    peak_snap_share = frame[["peak_season_snap_share_with_drafting_team", "peak_season_snap_share_any_team"]].max(axis=1)
    has_honors = (
        frame["first_team_all_pro_count"]
        + frame["second_team_all_pro_count"]
        + frame["top5_award_finish_count"]
        + frame["top5_mvp_finish_count"]
    ) > 0

    mask = (
        frame["round"].astype(int).isin(rounds)
        & (frame["eligible_seasons"] >= min_eligible_seasons)
        & ~frame[starter_column]
        & (peak_snap_share.fillna(0.0) <= max_peak_snap_share)
    )
    if count_honors_as_non_bust:
        mask &= ~has_honors
    return mask


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
        "ap_award_details": "",
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
    frame["ap_award_details"] = frame["ap_award_details"].fillna("").astype("string")

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
    bust_config = config.get("early_round_bust_adjustment", {})
    penalty_by_round = bust_config.get("penalty_by_round", {})
    frame["early_round_bust"] = _build_bust_mask(frame, config)
    frame["bust_penalty_points_raw"] = 0.0
    if penalty_by_round:
        frame.loc[frame["early_round_bust"], "bust_penalty_points_raw"] = frame.loc[
            frame["early_round_bust"], "round"
        ].map(lambda value: float(penalty_by_round.get(int(value), 0.0)))
    frame["bust_adjusted_raw_player_score"] = frame["raw_player_score"] + frame["bust_penalty_points_raw"]

    frame["retention_points"] = frame["retention_points_raw"] / frame["opportunity_divisor"]
    frame["starter_points"] = frame["starter_points_raw"] / frame["opportunity_divisor"]
    frame["snap_share_points"] = frame["snap_share_points_raw"] / frame["opportunity_divisor"]
    frame["star_points"] = frame["star_points_raw"] / frame["opportunity_divisor"]
    frame["bust_penalty_points"] = frame["bust_penalty_points_raw"] / frame["opportunity_divisor"]
    frame["normalized_player_score"] = frame["raw_player_score"] / frame["opportunity_divisor"]
    frame["bust_adjusted_normalized_player_score"] = (
        frame["bust_adjusted_raw_player_score"] / frame["opportunity_divisor"]
    )
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
            "ap_award_details",
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
            "early_round_bust",
            "bust_penalty_points_raw",
            "bust_penalty_points",
            "raw_player_score",
            "normalized_player_score",
            "bust_adjusted_raw_player_score",
            "bust_adjusted_normalized_player_score",
            "pick_cost",
        ]
    ]
