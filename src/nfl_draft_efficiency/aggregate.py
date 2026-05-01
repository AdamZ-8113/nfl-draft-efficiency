from __future__ import annotations

import pandas as pd


def aggregate_team_scores(player_scores: pd.DataFrame, draft_years: list[int]) -> pd.DataFrame:
    grouped = player_scores.groupby("draft_team", dropna=False)

    team_scores = grouped.agg(
        total_picks=("draft_player_id", "count"),
        draft_capital=("pick_cost", "sum"),
        players_still_on_team=("still_on_drafting_team", "sum"),
        starter_with_drafting_team_count=("starter_with_drafting_team", "sum"),
        starter_with_any_team_count=("starter_with_any_team", "sum"),
        first_team_all_pro_count=("first_team_all_pro_count", "sum"),
        second_team_all_pro_count=("second_team_all_pro_count", "sum"),
        top5_award_finish_count=("top5_award_finish_count", "sum"),
        retention_points=("retention_points", "sum"),
        starter_points=("starter_points", "sum"),
        snap_share_points=("snap_share_points", "sum"),
        star_points=("star_points", "sum"),
        raw_score=("normalized_player_score", "sum"),
    ).reset_index()

    team_scores = team_scores.rename(columns={"draft_team": "team"})
    team_scores["draft_year_start"] = min(draft_years)
    team_scores["draft_year_end"] = max(draft_years)
    team_scores["retention_score"] = team_scores["retention_points"] / team_scores["draft_capital"]
    team_scores["starter_score"] = team_scores["starter_points"] / team_scores["draft_capital"]
    team_scores["snap_share_score"] = team_scores["snap_share_points"] / team_scores["draft_capital"]
    team_scores["star_score"] = team_scores["star_points"] / team_scores["draft_capital"]
    team_scores["team_score"] = team_scores["raw_score"] / team_scores["draft_capital"]

    league_average = team_scores["team_score"].mean()
    team_scores["draft_efficiency_index"] = 100.0 * team_scores["team_score"] / league_average

    team_scores = team_scores.sort_values(
        by=["draft_efficiency_index", "team_score", "team"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    team_scores["rank"] = range(1, len(team_scores) + 1)

    return team_scores[
        [
            "team",
            "draft_year_start",
            "draft_year_end",
            "total_picks",
            "draft_capital",
            "players_still_on_team",
            "starter_with_drafting_team_count",
            "starter_with_any_team_count",
            "first_team_all_pro_count",
            "second_team_all_pro_count",
            "top5_award_finish_count",
            "retention_score",
            "starter_score",
            "snap_share_score",
            "star_score",
            "raw_score",
            "team_score",
            "draft_efficiency_index",
            "rank",
        ]
    ]
