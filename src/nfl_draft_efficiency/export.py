from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
from .interactive_report import render_interactive_report


def write_html_report(
    output_path: Path,
    team_scores: pd.DataFrame,
    player_scores: pd.DataFrame,
    metadata: dict[str, Any],
) -> None:
    render_interactive_report(
        output_path=output_path,
        team_scores=team_scores,
        player_scores=player_scores,
        metadata=metadata,
    )


def write_summary_markdown(output_path: Path, team_scores: pd.DataFrame, metadata: dict[str, Any]) -> None:
    top_team = team_scores.iloc[0]
    bottom_team = team_scores.iloc[-1]
    top_ten = team_scores.head(10)[["rank", "team", "draft_efficiency_index", "team_score"]]
    markdown_rows = ["| Rank | Team | Draft Efficiency Index | Team Score |", "| --- | --- | ---: | ---: |"]
    for row in top_ten.itertuples(index=False):
        markdown_rows.append(
            f"| {int(row.rank)} | {row.team} | {row.draft_efficiency_index:.1f} | {row.team_score:.3f} |"
        )
    summary = f"""# NFL Draft Efficiency Summary

- Generated at: `{metadata["generated_at"]}`
- Draft years: `{", ".join(str(year) for year in metadata["draft_years"])}`
- Latest roster snapshot: `{metadata["latest_roster_snapshot"]}`
- Latest snap-count season: `{metadata["latest_snap_count_season"]}`

## Headline

`{top_team.team}` finished first with a draft efficiency index of `{top_team.draft_efficiency_index:.1f}`.

`{bottom_team.team}` finished last with a draft efficiency index of `{bottom_team.draft_efficiency_index:.1f}`.

## Top 10 Teams

{chr(10).join(markdown_rows)}
"""
    output_path.write_text(summary, encoding="utf-8")


def write_outputs(
    output_dir: Path,
    team_scores: pd.DataFrame,
    player_scores: pd.DataFrame,
    unmatched_players: pd.DataFrame,
    metadata: dict[str, Any],
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    team_csv = output_dir / "team_scores.csv"
    player_csv = output_dir / "player_scores.csv"
    unmatched_csv = output_dir / "unmatched_players.csv"
    metadata_json = output_dir / "metadata.json"
    team_parquet = output_dir / "team_scores.parquet"
    player_parquet = output_dir / "player_scores.parquet"
    report_html = output_dir / "report.html"
    summary_md = output_dir / "summary.md"

    player_export_columns = [
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
    player_export = player_scores[player_export_columns].copy()

    team_scores.to_csv(team_csv, index=False)
    player_export.to_csv(player_csv, index=False)
    unmatched_players.to_csv(unmatched_csv, index=False)
    parquet_written = True
    try:
        team_scores.to_parquet(team_parquet, index=False)
        player_export.to_parquet(player_parquet, index=False)
    except Exception:
        parquet_written = False
    metadata_json.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_html_report(report_html, team_scores, player_scores, metadata)
    write_summary_markdown(summary_md, team_scores, metadata)
    outputs = {
        "team_scores_csv": team_csv,
        "player_scores_csv": player_csv,
        "unmatched_players_csv": unmatched_csv,
        "metadata_json": metadata_json,
        "report_html": report_html,
        "summary_md": summary_md,
    }
    if parquet_written:
        outputs["team_scores_parquet"] = team_parquet
        outputs["player_scores_parquet"] = player_parquet
    return outputs


def build_metadata(
    draft_years: list[int],
    latest_roster_snapshot: str,
    latest_snap_count_season: int,
    config: dict[str, Any],
    data_sources: list[str],
    penalize_missing_premium_picks: bool = False,
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "draft_years": draft_years,
        "latest_roster_snapshot": latest_roster_snapshot,
        "latest_snap_count_season": latest_snap_count_season,
        "penalize_missing_premium_picks": penalize_missing_premium_picks,
        "scoring_config": config,
        "data_sources": data_sources,
    }
