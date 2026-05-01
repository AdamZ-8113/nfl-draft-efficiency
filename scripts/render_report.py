from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd


def _load_window(output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict] | None:
    team_scores_path = output_dir / "team_scores.csv"
    player_scores_path = output_dir / "player_scores.csv"
    metadata_path = output_dir / "metadata.json"
    if not team_scores_path.exists() or not player_scores_path.exists() or not metadata_path.exists():
        return None
    team_scores = pd.read_csv(team_scores_path)
    player_scores = pd.read_csv(player_scores_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return team_scores, player_scores, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the interactive HTML report from existing model outputs.")
    parser.add_argument(
        "--sync-css",
        action="store_true",
        default=False,
        help="Overwrite docs/report.css with outputs/report.css. By default existing CSS files are preserved.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "src"))

    from nfl_draft_efficiency.interactive_report import _build_window_payload, render_interactive_report

    output_dir = project_root / "outputs"
    output_path = output_dir / "report.html"
    pages_path = project_root / "docs" / "index.html"
    default_window_years = 5
    default_loaded = _load_window(output_dir)
    if default_loaded is None:
        raise FileNotFoundError("Missing outputs/team_scores.csv, outputs/player_scores.csv, or outputs/metadata.json")
    team_scores, player_scores, metadata = default_loaded

    report_windows = {}
    windows_dir = output_dir / "windows"
    for years in range(3, 9):
        loaded = _load_window(windows_dir / str(years))
        if loaded is None:
            continue
        window_team_scores, window_player_scores, window_metadata = loaded
        report_windows[years] = _build_window_payload(
            window_team_scores,
            window_player_scores,
            window_metadata,
        )

    render_interactive_report(
        output_path=output_path,
        team_scores=team_scores,
        player_scores=player_scores,
        metadata=metadata,
        report_windows=report_windows or None,
        default_window_years=default_window_years if report_windows else len(metadata.get("draft_years", [])),
    )
    pages_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output_path, pages_path)
    stylesheet_path = output_path.with_name("report.css")
    pages_stylesheet_path = pages_path.with_name("report.css")
    if stylesheet_path.exists() and (args.sync_css or not pages_stylesheet_path.exists()):
        shutil.copyfile(stylesheet_path, pages_stylesheet_path)
    print(output_path)
    print(pages_path)


if __name__ == "__main__":
    main()
