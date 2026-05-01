# NFL Draft Efficiency Implementation Spec v1

This document is the canonical implementation spec for v1 of the NFL draft efficiency project. It resolves the ambiguous parts of the original brief and should be used as the source of truth for implementation.

If this spec conflicts with the original brief, this spec wins.

## Scope

Build a Python pipeline that evaluates how efficiently each NFL team drafted from 2021 through 2025, using public data and reproducible local caching.

Primary outputs:

- Team ranking table
- Player detail table
- Metadata file
- Unmatched player log

v1 must run without any manual data entry and without any required web scraping.

## Locked v1 Decisions

### 1. Draft Window

The v1 draft window is fixed to:

```txt
2021, 2022, 2023, 2024, 2025
```

Rules:

- Include only draft picks from 2021-2025 inclusive.
- Do not include the 2026 draft in v1.
- Default CLI behavior should be equivalent to:

```bash
python -m nfl_draft_efficiency.cli run --min-draft-year 2021 --max-draft-year 2025
```

- CLI overrides may still be supported, but the product default is 2021-2025.

### 2. Canonical Ranking Formula

v1 uses a single authoritative ranking formula:

```python
team_raw_score = sum(normalized_player_score for all players drafted by team)
team_draft_capital = sum(pick_cost for all picks used by team)
team_score = team_raw_score / team_draft_capital
league_average = mean(team_score across all 32 teams)
draft_efficiency_index = 100 * team_score / league_average
```

Rules:

- `draft_efficiency_index` is the authoritative ranking metric.
- `rank` is derived by sorting `draft_efficiency_index` descending.
- Ties are broken by `team_score` descending, then team code ascending.
- `retention_score`, `starter_score`, and `star_score` are diagnostic component metrics only.
- v1 does not use the component metrics as a second ranking formula.

### 3. All-Pro and Award Handling

v1 honors logic is intentionally minimal and deterministic.

Rules:

- Use `draft_picks.allpro` as `first_team_all_pro_count`.
- Interpret `allpro` as AP First-Team All-Pro count for v1.
- Coerce null `allpro` values to `0`.
- Reject negative values.
- Fail fast with a clear error if the `allpro` column is missing.

Current shipped scoring includes AP award finalists/winners from NFL.com AP Honors pages:

- `second_team_all_pro_count = 0`
- `top5_award_finish_count` is populated for AP OPOY, DPOY, OROY, DROY, and CPOY finalists/winners
- `top5_mvp_finish_count` is populated for AP MVP finalists/winners

Scraping modules may exist as placeholders, but they must not be required for the core pipeline or for passing tests.

### 4. Starter Model for v1

v1 uses position-aware starter thresholds from the first implementation.

This replaces the "generic first, position-aware later" split from the original brief.

Starter qualification is evaluated at the `player-season-team` level using regular-season snap counts only.

Recognized position thresholds:

```txt
QB:
  offense snap pct >= 50% in at least 6 games

RB:
  offense snap pct >= 35% in at least 8 games

WR / TE / OL:
  offense snap pct >= 50% in at least 8 games

DL / EDGE / LB / DB:
  defense snap pct >= 45% in at least 8 games

K / P / LS:
  tracked separately only
```

Rules:

- A qualifying season counts as starter-level if the player meets the threshold for the normalized position group.
- For unrecognized positions, fall back to:

```txt
offense or defense snap pct >= 50% in at least 8 games
```

- Special-teams-only contributors do not count as offensive or defensive starters.
- `special_teams_contributor = True` if `st_pct >= 50%` in at least 8 games.
- `starter_with_drafting_team` is `True` if the player has at least one qualifying starter season for the team that drafted him.
- `starter_with_any_team` is `True` if the player has at least one qualifying starter season for any NFL team.
- `starter_seasons_with_drafting_team` counts unique seasons, not team stints.
- `starter_seasons_with_any_team` counts unique seasons, not team stints.

## Data Sources

### Draft Picks

Primary source:

```python
nflreadpy.load_draft_picks()
```

Required fields:

```txt
season
team
round
pick
overall
player_name
position
gsis_id
pfr_player_id
college
allpro
```

Rules:

- The drafting team always receives credit for the player.
- Use only 2021-2025 draft rows in v1.

### Rosters

Preferred source:

```python
nflreadpy.load_rosters_weekly()
```

Fallback:

```python
nflreadpy.load_rosters()
```

Rules:

- `still_on_drafting_team = True` if the player's latest available roster record matches the drafting team.
- Use the latest available season/week in the roster source.
- If weekly offseason data is missing, use the latest completed regular-season roster snapshot.
- `latest_team` in player output comes from this same snapshot.

### Snap Counts

Primary source:

```python
nflreadpy.load_snap_counts()
```

Required fields:

```txt
season
week
team
player
pfr_player_id
position
offense_pct
defense_pct
st_pct
```

Rules:

- Use regular-season data only.
- Evaluate starter qualification per `player-season-team`.
- Roll season-level flags up to one player-level row.

## Join and ID Rules

Preferred match order:

```txt
1. gsis_id
2. pfr_player_id
3. normalized player_name + normalized position group + draft year sanity check
```

Rules:

- Use exact IDs whenever possible.
- Normalize names only as a fallback.
- Log unmatched draft picks.
- Write unmatched rows to `outputs/unmatched_players.csv`.

Name normalization rules:

```txt
- lowercase
- strip punctuation
- remove common suffixes: jr, sr, ii, iii, iv
- collapse whitespace
```

## Pick Cost Model

v1 uses the round-based cost model exactly as follows:

```yaml
round_pick_cost:
  1: 8.0
  2: 6.0
  3: 4.0
  4: 3.0
  5: 2.0
  6: 1.5
  7: 1.0
```

Rules:

- Unknown rounds raise a clear error.
- Future pick-value models may be added later behind the same scoring interface.

## Player Scoring

v1 player scoring:

```yaml
points:
  still_on_drafting_team: 1
  starter_with_drafting_team: 4
  starter_with_any_team: 3
  second_team_all_pro: 4
  first_team_all_pro: 8
  top5_award_finish: 5
  top5_mvp_finish: 8
```

Application rules:

- Add `still_on_drafting_team` once if true.
- If `starter_with_drafting_team` is true, add `+4`.
- Else if `starter_with_any_team` is true, add `+3`.
- Do not award both starter bonuses to the same player.
- `second_team_all_pro` remains zero unless a second-team All-Pro source is added; AP player-award and MVP finalist/winner counts are populated from NFL.com.
- `first_team_all_pro_count` can contribute across seasons.

v1 caps:

```yaml
caps:
  max_all_pro_points_per_player: 24
  max_award_points_per_player: 16
```

The All-Pro cap and award cap are both active when the AP award cache is populated.

## Opportunity Normalization

Use the following v1 formula:

```python
eligible_seasons = latest_completed_season - draft_year + 1
eligible_seasons = min(max(eligible_seasons, 1), 5)
normalized_player_score = raw_player_score / sqrt(eligible_seasons)
```

Rules:

- `latest_completed_season` is the latest season present in the regular-season snap-count data used by the run.
- Use `sqrt` normalization in v1.
- Keep `max_seasons = 5`.

For the fixed 2021-2025 draft window, this means newer classes are still included but scaled for lower opportunity.

## Component Metrics

v1 should still output component metrics for analysis:

```txt
retention_score
starter_score
star_score
```

Definitions:

- `retention_score` is retention-related player points divided by draft capital.
- `starter_score` is starter-related player points divided by draft capital.
- `star_score` is honors-related player points divided by draft capital.

Rules:

- These are explanatory metrics only.
- They do not affect `rank` in v1.

## Outputs

Write outputs under `outputs/`.

### outputs/team_scores.csv

Required columns:

```txt
team
draft_year_start
draft_year_end
total_picks
draft_capital
players_still_on_team
starter_with_drafting_team_count
starter_with_any_team_count
first_team_all_pro_count
second_team_all_pro_count
top5_award_finish_count
retention_score
starter_score
star_score
raw_score
team_score
draft_efficiency_index
rank
```

For v1:

- `draft_year_start = 2021`
- `draft_year_end = 2025`
- `second_team_all_pro_count = 0`
- `top5_award_finish_count` is populated from the AP award cache

### outputs/player_scores.csv

Required columns:

```txt
draft_year
draft_team
round
pick
overall
player_name
position
gsis_id
pfr_player_id
latest_team
still_on_drafting_team
starter_with_drafting_team
starter_with_any_team
starter_seasons_with_drafting_team
starter_seasons_with_any_team
first_team_all_pro_count
second_team_all_pro_count
top5_award_finish_count
top5_mvp_finish_count
eligible_seasons
raw_player_score
normalized_player_score
pick_cost
```

### outputs/metadata.json

Required fields:

```json
{
  "generated_at": "...",
  "draft_years": [2021, 2022, 2023, 2024, 2025],
  "latest_roster_snapshot": "...",
  "latest_snap_count_season": 2025,
  "scoring_config": {},
  "data_sources": []
}
```

### outputs/unmatched_players.csv

Required columns:

```txt
draft_year
draft_team
round
pick
player_name
position
gsis_id
pfr_player_id
reason
```

## Caching

Cache raw source data locally:

```txt
data/cache/draft_picks.parquet
data/cache/rosters.parquet
data/cache/weekly_rosters.parquet
data/cache/snap_counts.parquet
data/cache/pfr_all_pro.parquet
data/cache/pfr_awards.parquet
```

Rules:

- If cache exists and refresh is not requested, read from cache.
- If cache does not exist, fetch and cache it.
- PFR cache files may remain absent in v1 with no effect on the main score.
- Core scoring must not require scraping.

## CLI

Required entry point:

```bash
python -m nfl_draft_efficiency.cli run
```

Required options:

```txt
--draft-window-years
--min-draft-year
--max-draft-year
--config
--output-dir
--skip-scraping
--force-refresh-cache
```

Rules:

- Running with no year flags should behave as `2021-2025`.
- `--skip-scraping` should default to `true` in v1 behavior.
- Year override flags may exist, but v1 acceptance and tests should assume the default 2021-2025 window.

## Recommended Project Structure

```txt
nfl-draft-efficiency/
  README.md
  requirements.txt
  pyproject.toml
  config/
    scoring.yml
  data/
    raw/
    processed/
    cache/
  outputs/
  src/
    nfl_draft_efficiency/
      __init__.py
      config.py
      load_data.py
      normalize_ids.py
      starter_model.py
      honors.py
      awards.py
      scoring.py
      aggregate.py
      export.py
      cli.py
  tests/
    test_scoring.py
    test_starter_model.py
    test_aggregation.py
  scripts/
    run_pipeline.py
```

## Test Requirements

Unit tests must cover:

### Pick Cost

- Round 1 returns `8.0`
- Round 7 returns `1.0`
- Unknown round raises a helpful error

### Player Scoring

- still on team adds `+1`
- starter with drafting team adds `+4`
- starter with any other team adds `+3`
- first-team all-pro adds `+8`
- second-team all-pro adds `+4` when nonzero values are manually supplied in test fixtures
- MVP top-5 adds `+8` when nonzero values are manually supplied in test fixtures
- non-MVP award top-5 adds `+5` when nonzero values are manually supplied in test fixtures
- caps are respected

### Starter Model

- QB with 6 games over 50% qualifies
- WR with only 6 games over 50% does not qualify
- RB with 8 games over 35% qualifies
- DL with 8 games over 45% qualifies
- special teams contributor does not count as normal starter

### Aggregation

- `team_score = sum(normalized_player_score) / sum(pick_cost)`
- `draft_efficiency_index` uses league average
- rank sorts descending with deterministic tiebreakers

## Acceptance Criteria

The implementation is acceptable when:

1. One command produces `team_scores.csv`, `player_scores.csv`, `metadata.json`, and `unmatched_players.csv`.
2. The pipeline runs without manual edits.
3. All 32 NFL teams are included.
4. The default draft window is exactly 2021-2025.
5. The scoring configuration is editable without changing code.
6. Starter detection is based on position-aware snap-count thresholds.
7. Retention is based on the latest available roster snapshot.
8. The final output includes component scores and a final indexed score.
9. Missing IDs and unmatched players are logged.
10. Unit tests pass.
11. Core scoring runs without scraping.

## Phase 2, Explicitly Deferred

The following are intentionally out of scope for v1 ranking correctness:

- AP Second-Team All-Pro scraping
- Award-vote scraping
- Composite metric ranking as an alternate published leaderboard
- Rolling draft-window defaults
- Pick-number expected value models
- Dashboard publishing
