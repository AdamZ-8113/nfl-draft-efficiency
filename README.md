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

By default the model includes the ten most recent configured draft classes, currently `2016-2025`.
To change the window for a run:

```bash
python -m nfl_draft_efficiency.cli run --draft-window-years 5
python -m nfl_draft_efficiency.cli run --min-draft-year 2021 --max-draft-year 2025
```

Missing round 1-3 pick penalties are included by default in the bust-adjusted score.
To turn them off for a run:

```bash
python -m nfl_draft_efficiency.cli run --no-penalize-missing-premium-picks
```

Build every supported report window from 3 through 10 years, with the report defaulting to 5 years:

```bash
python scripts/build_report_windows.py
```

Regenerate the local report and GitHub Pages entry point from existing output CSVs:

```bash
python scripts/render_report.py
```

Report styling lives in `outputs/report.css` for local review and `docs/report.css` for GitHub Pages.
The report scripts regenerate HTML and data, but they do not overwrite an existing local stylesheet.
To intentionally copy local report styling to the Pages stylesheet:

```bash
python scripts/render_report.py --sync-css
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
- `outputs/report.css`
- `outputs/summary.md`
- `outputs/windows/{3..10}/` (when `scripts/build_report_windows.py` is used)
- `outputs/external_validation.csv` (when `--validate-external-references` is used)
- `outputs/external_validation_issues.csv` (when `--validate-external-references` is used)
- `outputs/external_validation_summary.md` (when `--validate-external-references` is used)

## Defaults

- Draft window: `2016-2025`
- Report default window: `2021-2025`, with selectable 3-10 year windows when built by `scripts/build_report_windows.py`
- Core score: `bust_adjusted_dei` displayed as `Overall`
- Honors: `draft_picks.allpro` plus AP player-award recognition from NFL.com and pre-2022 AP vote finishers from Pro Football Reference
- Starter model: position-aware snap-count thresholds
- Starter longevity: capped bonus for starter seasons after the first starter season
- Bust-adjusted score: configurable round 1-3 bust penalties
- Missing premium pick penalties: on by default, disabled with `--no-penalize-missing-premium-picks`
