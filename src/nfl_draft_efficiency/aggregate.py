from __future__ import annotations

import math
from typing import Any

import pandas as pd


def _normalization_divisor(eligible_seasons: int, method: str) -> float:
    if method == "sqrt":
        return math.sqrt(eligible_seasons)
    if method == "linear":
        return float(eligible_seasons)
    raise ValueError(f"Unsupported normalization method: {method}")


def _missing_premium_pick_penalties(
    player_scores: pd.DataFrame,
    draft_years: list[int],
    config: dict[str, Any],
    penalize_missing_premium_picks: bool,
) -> pd.DataFrame:
    teams = sorted(player_scores["draft_team"].dropna().unique())
    base = pd.DataFrame({"team": teams})
    base["missing_premium_pick_count"] = 0
    base["missing_premium_pick_cost"] = 0.0
    base["missing_pick_penalty_points"] = 0.0
    if not penalize_missing_premium_picks:
        return base

    bust_config = config.get("early_round_bust_adjustment", {})
    rounds = [int(round_value) for round_value in bust_config.get("rounds", [])]
    penalty_by_round = bust_config.get("missing_pick_penalty_by_round", {})
    round_pick_cost = config.get("round_pick_cost", {})
    normalization = config.get("opportunity_normalization", {})
    method = str(normalization.get("method", "sqrt")).lower()
    max_seasons = int(normalization.get("max_seasons", len(draft_years)))
    latest_year = max(draft_years)

    existing = set(
        player_scores.loc[player_scores["round"].astype(int).isin(rounds), ["draft_team", "draft_year", "round"]]
        .assign(round=lambda frame: frame["round"].astype(int), draft_year=lambda frame: frame["draft_year"].astype(int))
        .itertuples(index=False, name=None)
    )
    rows: list[dict[str, Any]] = []
    for team in teams:
        missing_count = 0
        missing_cost = 0.0
        missing_penalty = 0.0
        for year in draft_years:
            eligible_seasons = max(1, min(max_seasons, latest_year - int(year) + 1))
            divisor = _normalization_divisor(eligible_seasons, method)
            for round_value in rounds:
                if (team, int(year), int(round_value)) in existing:
                    continue
                missing_count += 1
                missing_cost += float(round_pick_cost.get(round_value, 0.0))
                missing_penalty += float(penalty_by_round.get(round_value, 0.0)) / divisor
        rows.append(
            {
                "team": team,
                "missing_premium_pick_count": missing_count,
                "missing_premium_pick_cost": missing_cost,
                "missing_pick_penalty_points": missing_penalty,
            }
        )
    return pd.DataFrame(rows)


def _index_from_league_average(series: pd.Series) -> pd.Series:
    league_average = series.mean()
    if league_average == 0:
        return pd.Series(0.0, index=series.index)
    return 100.0 * series / league_average


def aggregate_team_scores(
    player_scores: pd.DataFrame,
    draft_years: list[int],
    config: dict[str, Any] | None = None,
    penalize_missing_premium_picks: bool = False,
) -> pd.DataFrame:
    config = config or {}
    player_scores = player_scores.copy()
    if "early_round_bust" not in player_scores:
        player_scores["early_round_bust"] = False
    if "bust_penalty_points" not in player_scores:
        player_scores["bust_penalty_points"] = 0.0
    if "bust_adjusted_normalized_player_score" not in player_scores:
        player_scores["bust_adjusted_normalized_player_score"] = player_scores["normalized_player_score"]
    if "round" not in player_scores:
        player_scores["round"] = 99
    if "top5_mvp_finish_count" not in player_scores:
        player_scores["top5_mvp_finish_count"] = 0
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
        top5_mvp_finish_count=("top5_mvp_finish_count", "sum"),
        retention_points=("retention_points", "sum"),
        starter_points=("starter_points", "sum"),
        snap_share_points=("snap_share_points", "sum"),
        star_points=("star_points", "sum"),
        bust_penalty_points=("bust_penalty_points", "sum"),
        premium_bust_count=("early_round_bust", "sum"),
        raw_score=("normalized_player_score", "sum"),
        bust_adjusted_raw_score=("bust_adjusted_normalized_player_score", "sum"),
    ).reset_index()

    team_scores = team_scores.rename(columns={"draft_team": "team"})
    premium_counts = (
        player_scores.loc[player_scores["round"].astype(int) <= 3]
        .groupby("draft_team", dropna=False)
        .agg(
            premium_picks=("draft_player_id", "count"),
            premium_draft_capital=("pick_cost", "sum"),
            premium_raw_score=("normalized_player_score", "sum"),
        )
        .rename_axis("team")
        .reset_index()
    )
    team_scores = team_scores.merge(
        premium_counts,
        on="team",
        how="left",
    )
    team_scores[["premium_picks", "premium_draft_capital", "premium_raw_score"]] = team_scores[
        ["premium_picks", "premium_draft_capital", "premium_raw_score"]
    ].fillna(0.0)

    missing_penalties = _missing_premium_pick_penalties(
        player_scores=player_scores,
        draft_years=draft_years,
        config=config,
        penalize_missing_premium_picks=penalize_missing_premium_picks,
    )
    team_scores = team_scores.merge(missing_penalties, on="team", how="left")
    team_scores[["missing_premium_pick_count", "missing_premium_pick_cost", "missing_pick_penalty_points"]] = (
        team_scores[["missing_premium_pick_count", "missing_premium_pick_cost", "missing_pick_penalty_points"]].fillna(0.0)
    )
    team_scores["draft_year_start"] = min(draft_years)
    team_scores["draft_year_end"] = max(draft_years)
    team_scores["retention_score"] = team_scores["retention_points"] / team_scores["draft_capital"]
    team_scores["starter_score"] = team_scores["starter_points"] / team_scores["draft_capital"]
    team_scores["snap_share_score"] = team_scores["snap_share_points"] / team_scores["draft_capital"]
    team_scores["star_score"] = team_scores["star_points"] / team_scores["draft_capital"]
    team_scores["team_score"] = team_scores["raw_score"] / team_scores["draft_capital"]
    team_scores["premium_bust_rate"] = team_scores["premium_bust_count"] / team_scores["premium_picks"].where(
        team_scores["premium_picks"] > 0
    )
    team_scores["premium_pick_score"] = team_scores["premium_raw_score"] / team_scores["premium_draft_capital"].where(
        team_scores["premium_draft_capital"] > 0
    )
    team_scores["premium_pick_score"] = team_scores["premium_pick_score"].fillna(0.0)
    team_scores["bust_adjusted_raw_score"] = (
        team_scores["bust_adjusted_raw_score"] + team_scores["missing_pick_penalty_points"]
    )
    team_scores["bust_adjusted_draft_capital"] = team_scores["draft_capital"] + team_scores["missing_premium_pick_cost"]
    team_scores["bust_adjusted_team_score"] = (
        team_scores["bust_adjusted_raw_score"] / team_scores["bust_adjusted_draft_capital"].where(
            team_scores["bust_adjusted_draft_capital"] > 0
        )
    ).fillna(0.0)

    team_scores["draft_efficiency_index"] = _index_from_league_average(team_scores["team_score"])
    team_scores["premium_pick_dei"] = _index_from_league_average(team_scores["premium_pick_score"])
    team_scores["bust_adjusted_dei"] = _index_from_league_average(team_scores["bust_adjusted_team_score"])

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
            "top5_mvp_finish_count",
            "retention_score",
            "starter_score",
            "snap_share_score",
            "star_score",
            "premium_picks",
            "premium_bust_count",
            "premium_bust_rate",
            "premium_draft_capital",
            "premium_raw_score",
            "premium_pick_score",
            "premium_pick_dei",
            "bust_penalty_points",
            "missing_premium_pick_count",
            "missing_premium_pick_cost",
            "missing_pick_penalty_points",
            "raw_score",
            "team_score",
            "draft_efficiency_index",
            "bust_adjusted_raw_score",
            "bust_adjusted_draft_capital",
            "bust_adjusted_team_score",
            "bust_adjusted_dei",
            "rank",
        ]
    ]
