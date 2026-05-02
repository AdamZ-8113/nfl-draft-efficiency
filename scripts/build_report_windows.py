from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path


def _copy_default_window(project_root: Path, default_window: int) -> None:
    output_dir = project_root / "outputs"
    default_dir = output_dir / "windows" / str(default_window)
    for filename in [
        "team_scores.csv",
        "player_scores.csv",
        "unmatched_players.csv",
        "metadata.json",
        "summary.md",
    ]:
        source = default_dir / filename
        if source.exists():
            shutil.copyfile(source, output_dir / filename)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 3-10 year model outputs and render the interactive report.")
    parser.add_argument("--min-window", type=int, default=3)
    parser.add_argument("--max-window", type=int, default=10)
    parser.add_argument("--default-window", type=int, default=5)
    parser.add_argument("--skip-scraping", action="store_true", default=False)
    parser.add_argument("--force-refresh-cache", action="store_true", default=False)
    parser.add_argument("--no-penalize-missing-premium-picks", action="store_true", default=False)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "src"))

    from nfl_draft_efficiency.cli import run_pipeline

    for window in range(args.min_window, args.max_window + 1):
        pipeline_args = Namespace(
            draft_window_years=window,
            min_draft_year=None,
            max_draft_year=None,
            config=None,
            output_dir=str(project_root / "outputs" / "windows" / str(window)),
            skip_scraping=args.skip_scraping,
            force_refresh_cache=args.force_refresh_cache,
            validate_external_references=False,
            penalize_missing_premium_picks=not args.no_penalize_missing_premium_picks,
        )
        print(f"Building {window}-year draft window...")
        run_pipeline(pipeline_args)

    _copy_default_window(project_root, args.default_window)
    subprocess.run([sys.executable, str(project_root / "scripts" / "render_report.py")], check=True)


if __name__ == "__main__":
    main()
