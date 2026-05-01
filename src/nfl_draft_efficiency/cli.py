from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .aggregate import aggregate_team_scores
from .awards import build_awards_frame
from .config import get_project_root, load_runtime_config, resolve_draft_years, resolve_output_dir
from .export import build_metadata, write_outputs
from .honors import build_honors_frame
from .load_data import (
    NFLDataClient,
    build_team_records,
    build_unmatched_players,
    match_latest_roster_snapshot,
    standardize_games,
    standardize_draft_picks,
    standardize_roster_snapshot,
    standardize_snap_counts,
)
from .scoring import build_player_scores
from .starter_model import compute_starter_flags
from .validation import build_external_validation, write_external_validation_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NFL draft efficiency pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the draft efficiency pipeline")
    run_parser.add_argument(
        "--draft-window-years",
        type=int,
        default=None,
        help="Number of draft years to include, ending at --max-draft-year or the config default max year.",
    )
    run_parser.add_argument("--min-draft-year", type=int, default=None, help="First draft year to include.")
    run_parser.add_argument("--max-draft-year", type=int, default=None, help="Last draft year to include.")
    run_parser.add_argument("--config", type=str, default=None)
    run_parser.add_argument("--output-dir", type=str, default="outputs")
    run_parser.add_argument("--skip-scraping", action="store_true", default=False)
    run_parser.add_argument("--force-refresh-cache", action="store_true", default=False)
    run_parser.add_argument("--validate-external-references", action="store_true", default=False)
    run_parser.add_argument(
        "--penalize-missing-premium-picks",
        action="store_true",
        default=False,
        help="Apply configured round 1-3 penalties when a team has no pick in those rounds for a draft year.",
    )
    return parser


def run_pipeline(args: argparse.Namespace) -> dict[str, Path]:
    config = load_runtime_config(args.config)
    draft_years = resolve_draft_years(
        config=config,
        draft_window_years=args.draft_window_years,
        min_draft_year=args.min_draft_year,
        max_draft_year=args.max_draft_year,
    )
    output_dir = resolve_output_dir(args.output_dir)

    project_root = get_project_root()
    cache_dir = project_root / "data" / "cache"
    data_client = NFLDataClient(cache_dir=cache_dir, force_refresh=args.force_refresh_cache)

    draft_picks_raw = data_client.load_draft_picks(draft_years)
    draft_picks = standardize_draft_picks(draft_picks_raw, draft_years, config)

    roster_snapshot = data_client.load_latest_roster_snapshot(anchor_year=max(draft_years))
    roster_frame = standardize_roster_snapshot(roster_snapshot.frame, config)
    roster_matches = match_latest_roster_snapshot(draft_picks, roster_frame)

    snap_counts_raw = data_client.load_snap_counts(draft_years)
    snap_counts = standardize_snap_counts(snap_counts_raw, config)
    latest_completed_season = int(snap_counts["season"].max())
    team_records = pd.DataFrame()
    try:
        games_raw = data_client.load_games(draft_years)
        games = standardize_games(games_raw)
        team_records = build_team_records(games)
    except Exception:
        team_records = pd.DataFrame()

    starter_flags = compute_starter_flags(snap_counts, draft_picks, config, team_records=team_records)
    honors = build_honors_frame(draft_picks, config)
    awards = build_awards_frame(draft_picks)

    player_scores = build_player_scores(
        draft_picks=draft_picks,
        roster_matches=roster_matches,
        starter_flags=starter_flags,
        honors=honors,
        awards=awards,
        latest_completed_season=latest_completed_season,
        config=config,
    )
    team_scores = aggregate_team_scores(
        player_scores,
        draft_years,
        config=config,
        penalize_missing_premium_picks=args.penalize_missing_premium_picks,
    )
    unmatched_players = build_unmatched_players(draft_picks, roster_matches, starter_flags)

    metadata = build_metadata(
        draft_years=draft_years,
        latest_roster_snapshot=roster_snapshot.snapshot_label,
        latest_snap_count_season=latest_completed_season,
        config=config,
        data_sources=[
            "nflverse draft_picks release CSV",
            roster_snapshot.source_name,
            "nflverse snap_counts release CSV",
            "nflverse games.csv regular-season records",
            "draft_picks.allpro",
        ],
        penalize_missing_premium_picks=args.penalize_missing_premium_picks,
    )

    outputs = write_outputs(
        output_dir=output_dir,
        team_scores=team_scores,
        player_scores=player_scores,
        unmatched_players=unmatched_players,
        metadata=metadata,
    )
    if args.validate_external_references:
        validation_frame, validation_errors = build_external_validation(player_scores)
        outputs.update(
            write_external_validation_outputs(
                output_dir=output_dir,
                validation_frame=validation_frame,
                errors=validation_errors,
            )
        )
    return outputs


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run":
        outputs = run_pipeline(args)
        print("Wrote outputs:")
        for name, path in outputs.items():
            print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
