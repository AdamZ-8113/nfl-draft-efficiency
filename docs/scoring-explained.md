# NFL Draft Efficiency Scoring Explained

This document explains the scoring model in plain English.

## What question is this trying to answer?

The model is trying to answer:

**"How much value did a team get from its draft picks compared with how much draft capital it spent?"**

It is not trying to predict the future. It is a scorecard for recent draft results.

## The simple version

Each drafted player earns value for the team that picked him.

A team scores well when it:

- keeps drafted players on the roster
- turns picks into real contributors
- gets strong players without spending too much draft capital
- finds players who earn honors like All-Pro or AP player-award recognition

Then the model adjusts for two things:

- newer draft classes have had less time to prove themselves
- early draft picks are more expensive than late picks
- premium-pick busts and missing premium picks are penalized in the default ranking

## How a player earns points

Here is the current scoring logic in simple terms:

### 1. Staying with the drafting team

- A player gets credit if he is still with the team that drafted him.

Why this matters:

- Teams usually want drafted players to stick.
- It is a weak signal by itself, so it is only one small part of the score.

### 2. Becoming a starter

- A player gets more credit if he became a starter for the team that drafted him.
- He gets some credit if he became a starter somewhere else instead.

Current starter settings:

- Starter with drafting team: `4` raw points
- Starter with any team: `2` raw points

Why this matters:

- Turning picks into starters is one of the clearest signs of drafting success.

### 3. Playing a meaningful share of snaps

- A player gets extra credit for actually being on the field a lot.
- This goes beyond a simple starter / non-starter label.
- Higher regular-season snap share means more value.
- Snap share with the drafting team is worth more than the same snap share somewhere else.

Why this matters:

- Some players contribute a lot even if they do not cleanly fit a starter label.
- This makes the model more fair than a pure yes/no starter system.

### 4. Staying a starter

- The first starter season is already rewarded by the starter score.
- Additional starter seasons add a capped longevity bonus.
- Extra starter seasons with the drafting team are worth more than starter seasons elsewhere.

Current starter-longevity settings:

- Baseline starter seasons before bonus: `1`
- Maximum extra starter seasons counted: `4`
- Extra starter season with drafting team: `1.0` raw points
- Extra starter season elsewhere: `0.25` raw points

Why this matters:

- A rookie starter should get credit, but a three-to-five-year starter has proven more.
- This helps longer lookback windows distinguish sustained hits from short-term need fillers.

### 5. Earning high-end honors

- First-team All-Pro adds more value.
- Second-team All-Pro adds some value.
- AP player-award finalists and winners add value.
- AP MVP recognition is tracked separately from other AP player awards.

Why this matters:

- Elite players should move the score more than average starters.

The AP player-award data includes MVP, Offensive Player of the Year, Defensive Player of the Year, Offensive Rookie of the Year, Defensive Rookie of the Year, and Comeback Player of the Year. Coach awards are excluded because they are not player draft outcomes.

## What does "starter" mean here?

This model does **not** use a depth chart from a website.

Instead, it uses regular-season snap data and position-based thresholds.

In plain English:

- if a player was on the field often enough, in enough games, at his position, he counts as a historical starter

That means this is a record of real playing time, not a projected lineup.

## How team record is used

Team win-loss record is only used in a small way.

- It slightly adjusts the snap-share value
- Heavy usage on a stronger team gets a small boost
- Heavy usage on a weaker team gets a small reduction

This adjustment is intentionally modest. The goal is to add context without letting team success completely override individual value.

## How younger players are treated fairly

A player drafted in 2025 has had much less time to build a resume than a player drafted in 2018.

So the model softens that difference by normalizing scores for opportunity window.

In plain English:

- newer players are not judged on the same raw scale as older players

## How draft capital is used

After player value is added up, the team total is divided by draft capital.

This matters because:

- a team with many early picks should be expected to get more value
- a team that finds strong players with cheaper picks should get credit for that

So the score is really about **value per unit of draft capital**, not just total value.

## How early-round busts are handled

The report also includes a stricter bust-adjusted score.

This adds explicit penalties for rounds 1-3 when a player has had enough time to develop but still has not become a meaningful contributor.

By default:

- Round 1 bust: `-4` raw points
- Round 2 bust: `-2.5` raw points
- Round 3 bust: `-1` raw point

A player avoids the bust label if he becomes a starter, earns meaningful playing time above the configured snap-share threshold, or earns high-end honors.

The model also penalizes teams for missing premium picks entirely. If a team has no pick in a configured premium round for a draft year, it receives that round's missing-pick penalty. This is on by default because the scorecard is measuring draft results, and trading away premium picks still leaves the team without a drafted player from that slot.

You can disable this behavior for a run with:

```bash
python -m nfl_draft_efficiency.cli run --no-penalize-missing-premium-picks
```

Current missing-pick penalties are:

- Missing Round 1 pick: `-3` raw points
- Missing Round 2 pick: `-1` raw point
- Missing Round 3 pick: `-0.5` raw points

## What the main report columns mean

The default ranking column is **Overall**.

Overall means:

- player value from all rounds
- divided by draft capital
- adjusted for round 1-3 bust penalties
- adjusted for missing round 1-3 picks
- scaled so league average is about `100`

The report also shows supporting views:

- **Round 1-3 Only** isolates premium picks and includes the same bust and missing-pick penalties.
- **Rounds 4-7 Only** isolates late-round draft value.
- **DEI (no BP)** is the overall Draft Efficiency Index before explicit bust penalties or missing-pick penalties.
- **Avg Starter Years** is the average number of starter-level seasons per drafted player, counting starter seasons with the drafting team or another NFL team.

Think of it like this:

- `100` is around league average
- above `100` means better than average
- below `100` means worse than average

Example for any index-style column:

- `115` means the team scored about 15% better than league average
- `90` means the team scored about 10% worse than league average

## What this model does well

- It rewards real playing time, not just reputation.
- It gives extra credit for stars, All-Pros, and AP player-award recognition.
- It accounts for cheaper vs. more expensive picks.
- It is easier to understand than a black-box model.

## What this model does not fully capture

No single score can perfectly answer "who drafts best?"

This model does **not** fully account for:

- injuries and unusual career interruptions
- coaching fit or scheme fit
- salary value vs. performance
- playoff performance
- exact pick-slot value inside each round
- whether a team made the right choice compared with who was still available

So this should be treated as a useful scorecard, not absolute truth.

## Where to change the settings

If you want to tune the model, the main settings live in:

- `config/scoring.yml`

That file controls things like:

- points for starters, All-Pro selections, and AP player-award recognition
- pick-cost values by round
- how much snap share matters
- how much team record matters

## Data sources

The model uses public NFL data sources:

- nflverse draft pick release data
- nflverse roster snapshot release data
- nflverse snap count release data
- nflverse regular-season game data for team records
- `draft_picks.allpro` for All-Pro counts
- NFL.com AP Honors articles for AP player-award finalists and winners

## Bottom line

This model is trying to reward teams that:

- draft players who stay
- draft players who play
- draft players who keep starting for multiple seasons
- draft players who become important contributors
- draft stars
- do all of that without overspending draft capital

That makes it a reasonable way to compare draft results, as long as you remember it is a simplified model and not a perfect measure of front-office quality.
