# NFL Draft Efficiency

Python pipeline for ranking NFL teams by draft efficiency across the fixed 2021-2025 draft window.

Live report:

- https://adamz-8113.github.io/nfl-draft-efficiency/

Plain-English scoring explainer:

- [docs/scoring-explained.md](docs/scoring-explained.md)

## What it does

- Loads draft pick, roster, and snap-count data from nflverse via `nflreadpy`
- Loads draft pick, roster, and snap-count data from official nflverse release URLs
- Computes player-level retention, starter, and star outcomes
- Normalizes scores for player development window
- Aggregates player scores into team draft efficiency scores
- Exports CSV, parquet, JSON, Markdown, and HTML outputs

## Quick start

```bash
python -m pip install -e .
python -m nfl_draft_efficiency.cli run
python -m unittest discover -s tests
```

Regenerate the local report and GitHub Pages entry point from existing output CSVs:

```bash
python scripts/render_report.py
```

Refresh cached nflverse data and add an external validation pass:

```bash
python -m nfl_draft_efficiency.cli run --force-refresh-cache --validate-external-references
```

## Main outputs

- `outputs/team_scores.csv`
- `outputs/player_scores.csv`
- `outputs/metadata.json`
- `outputs/unmatched_players.csv`
- `outputs/report.html`
- `outputs/summary.md`
- `outputs/external_validation.csv` (when `--validate-external-references` is used)
- `outputs/external_validation_issues.csv` (when `--validate-external-references` is used)
- `outputs/external_validation_summary.md` (when `--validate-external-references` is used)

## Defaults

- Draft window: `2021-2025`
- Core score: `draft_efficiency_index`
- Honors in v1: `draft_picks.allpro` only
- Starter model: position-aware snap-count thresholds
