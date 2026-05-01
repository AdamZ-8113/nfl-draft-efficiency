# NFL Draft Efficiency

Python pipeline for ranking NFL teams by draft efficiency across a configurable draft window.

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

By default the model includes the eight most recent configured draft classes, currently `2018-2025`.
To change the window for a run:

```bash
python -m nfl_draft_efficiency.cli run --draft-window-years 5
python -m nfl_draft_efficiency.cli run --min-draft-year 2021 --max-draft-year 2025
```

To include penalties for missing round 1-3 picks in the bust-adjusted score:

```bash
python -m nfl_draft_efficiency.cli run --penalize-missing-premium-picks
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

- Draft window: `2018-2025`
- Core score: `draft_efficiency_index`
- Honors: `draft_picks.allpro` plus AP player-award finalists/winners from NFL.com
- Starter model: position-aware snap-count thresholds
- Bust-adjusted score: configurable round 1-3 bust penalties
- Missing premium pick penalties: off by default, enabled with `--penalize-missing-premium-picks`
