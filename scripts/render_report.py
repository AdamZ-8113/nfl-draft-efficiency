from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from nfl_draft_efficiency.interactive_report import render_interactive_report


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "outputs"
    output_path = output_dir / "report.html"
    pages_path = project_root / "docs" / "index.html"
    team_scores = pd.read_csv(output_dir / "team_scores.csv")
    player_scores = pd.read_csv(output_dir / "player_scores.csv")
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    render_interactive_report(
        output_path=output_path,
        team_scores=team_scores,
        player_scores=player_scores,
        metadata=metadata,
    )
    pages_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output_path, pages_path)
    print(output_path)
    print(pages_path)


if __name__ == "__main__":
    main()
