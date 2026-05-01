from __future__ import annotations

import json
import re
from collections import OrderedDict
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd


TEAM_INFO = OrderedDict(
    [
        ("ARI", {"name": "Arizona Cardinals", "color": "#97233F"}),
        ("ATL", {"name": "Atlanta Falcons", "color": "#A71930"}),
        ("BAL", {"name": "Baltimore Ravens", "color": "#9E7C0C"}),
        ("BUF", {"name": "Buffalo Bills", "color": "#4A84C4"}),
        ("CAR", {"name": "Carolina Panthers", "color": "#0085CA"}),
        ("CHI", {"name": "Chicago Bears", "color": "#C83803"}),
        ("CIN", {"name": "Cincinnati Bengals", "color": "#FB4F14"}),
        ("CLE", {"name": "Cleveland Browns", "color": "#FF6B22"}),
        ("DAL", {"name": "Dallas Cowboys", "color": "#9BB7D4"}),
        ("DEN", {"name": "Denver Broncos", "color": "#FB4F14"}),
        ("DET", {"name": "Detroit Lions", "color": "#0076B6"}),
        ("GB", {"name": "Green Bay Packers", "color": "#FFB612"}),
        ("HOU", {"name": "Houston Texans", "color": "#A71930"}),
        ("IND", {"name": "Indianapolis Colts", "color": "#4B8FD4"}),
        ("JAX", {"name": "Jacksonville Jaguars", "color": "#D7A22A"}),
        ("KC", {"name": "Kansas City Chiefs", "color": "#E31837"}),
        ("LAC", {"name": "Los Angeles Chargers", "color": "#0099E0"}),
        ("LA", {"name": "Los Angeles Rams", "color": "#FFA300"}),
        ("LV", {"name": "Las Vegas Raiders", "color": "#A5ACAF"}),
        ("MIA", {"name": "Miami Dolphins", "color": "#00B5C0"}),
        ("MIN", {"name": "Minnesota Vikings", "color": "#FFC62F"}),
        ("NE", {"name": "New England Patriots", "color": "#C60C30"}),
        ("NO", {"name": "New Orleans Saints", "color": "#C2A35D"}),
        ("NYG", {"name": "New York Giants", "color": "#A71930"}),
        ("NYJ", {"name": "New York Jets", "color": "#3DA35C"}),
        ("PHI", {"name": "Philadelphia Eagles", "color": "#A5ACAF"}),
        ("PIT", {"name": "Pittsburgh Steelers", "color": "#FFB612"}),
        ("SEA", {"name": "Seattle Seahawks", "color": "#69BE28"}),
        ("SF", {"name": "San Francisco 49ers", "color": "#CF2B2B"}),
        ("TB", {"name": "Tampa Bay Buccaneers", "color": "#D50A0A"}),
        ("TEN", {"name": "Tennessee Titans", "color": "#4B92DB"}),
        ("WAS", {"name": "Washington Commanders", "color": "#FFB612"}),
    ]
)


def _replace_one(pattern: str, replacement: str, text: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"Expected exactly one replacement for pattern: {pattern}")
    return updated


def _fmt_points(value: Any) -> str:
    number = float(value)
    text = f"{number:g}"
    return f"{text} pt" if number == 1 else f"{text} pts"


def _fmt_value(value: Any) -> str:
    return f"{float(value):g}"


def _table_rows(rows: list[tuple[str, str]]) -> str:
    return "\n".join(
        f"                    <tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>"
        for label, value in rows
    )


def _build_scoring_details(config: dict[str, Any]) -> str:
    round_pick_cost = config.get("round_pick_cost", {})
    points = config.get("points", {})
    snap_share = config.get("snap_share_value", {})
    team_record = config.get("team_record_adjustment", {})
    opportunity = config.get("opportunity_normalization", {})
    composite = config.get("composite_weights", {})

    round_rows = [
        (f"Round {round_number}", _fmt_points(round_pick_cost.get(str(round_number), 0)))
        for round_number in range(1, 8)
    ]
    point_rows = [
        ("Still with drafting team", _fmt_points(points.get("still_on_drafting_team", 0))),
        ("Starter with drafting team", _fmt_points(points.get("starter_with_drafting_team", 0))),
        ("Starter with any team", _fmt_points(points.get("starter_with_any_team", 0))),
        ("Second-team All-Pro", _fmt_points(points.get("second_team_all_pro", 0))),
        ("First-team All-Pro", _fmt_points(points.get("first_team_all_pro", 0))),
        ("Top-5 award finish", _fmt_points(points.get("top5_award_finish", 0))),
        ("Top-5 MVP finish", _fmt_points(points.get("top5_mvp_finish", 0))),
    ]
    snap_rows = [
        (
            "Full season with drafting team",
            _fmt_points(snap_share.get("with_drafting_team_per_full_season", 0)),
        ),
        (
            "Full season with another team",
            _fmt_points(snap_share.get("with_any_team_per_full_season", 0)),
        ),
        (
            "Team record multiplier range",
            f"{_fmt_value(team_record.get('min_multiplier', 0))}x-{_fmt_value(team_record.get('max_multiplier', 0))}x",
        ),
        ("Record multiplier weight", _fmt_value(team_record.get("win_pct_multiplier_weight", 0))),
    ]
    normalization_rows = [
        ("Opportunity method", str(opportunity.get("method", ""))),
        ("Maximum seasons", _fmt_value(opportunity.get("max_seasons", 0))),
        ("Composite retention weight", _fmt_value(composite.get("retention", 0))),
        ("Composite starter weight", _fmt_value(composite.get("starter", 0))),
        ("Composite star weight", _fmt_value(composite.get("star", 0))),
    ]

    return f"""<div class="scoring-detail-grid">
              <div class="scoring-detail-card">
                <h3>Draft Pick Cost</h3>
                <p>Team value is divided by draft capital, so expensive early picks carry higher expectations.</p>
                <table>
                  <tbody>
{_table_rows(round_rows)}
                  </tbody>
                </table>
              </div>
              <div class="scoring-detail-card">
                <h3>Player Points</h3>
                <p>These are raw point values before opportunity-window normalization and team aggregation.</p>
                <table>
                  <tbody>
{_table_rows(point_rows)}
                  </tbody>
                </table>
              </div>
              <div class="scoring-detail-card">
                <h3>Snap Share</h3>
                <p>Snap share gives partial credit for real playing time, even when a player does not cross a starter threshold.</p>
                <table>
                  <tbody>
{_table_rows(snap_rows)}
                  </tbody>
                </table>
              </div>
              <div class="scoring-detail-card">
                <h3>Normalization</h3>
                <p>Raw player scores are adjusted so newer draft classes are not punished for having fewer NFL seasons.</p>
                <table>
                  <tbody>
{_table_rows(normalization_rows)}
                  </tbody>
                </table>
              </div>
            </div>"""


def _build_team_scores(team_scores: pd.DataFrame) -> list[dict[str, object]]:
    ordered = team_scores.sort_values(["rank", "team"]).reset_index(drop=True)
    rows: list[dict[str, object]] = []
    for row in ordered.itertuples(index=False):
        rows.append(
            {
                "rank": int(row.rank),
                "team": str(row.team),
                "dei": round(float(row.draft_efficiency_index), 2),
                "score": round(float(row.team_score), 6),
                "ret": round(float(row.retention_score), 6),
                "str": round(float(row.starter_score) + float(getattr(row, "snap_share_score", 0.0)), 6),
                "star": round(float(row.star_score), 6),
                "picks": int(row.total_picks),
                "starters": int(row.starter_with_drafting_team_count),
            }
        )
    return rows


def _build_top_players(player_scores: pd.DataFrame) -> list[dict[str, object]]:
    ordered = player_scores.sort_values(
        ["normalized_player_score", "raw_player_score", "player_name"],
        ascending=[False, False, True],
    ).head(20)
    rows: list[dict[str, object]] = []
    for row in ordered.itertuples(index=False):
        rows.append(
            {
                "team": str(row.draft_team),
                "name": str(row.player_name),
                "year": int(row.draft_year),
                "pos": str(row.position),
                "nsc": round(float(row.normalized_player_score), 2),
                "rsc": int(round(float(row.raw_player_score))),
                "ap": int(row.first_team_all_pro_count),
                "on": bool(row.still_on_drafting_team),
                "st": bool(row.starter_with_drafting_team),
                "sa": bool(row.starter_with_any_team),
            }
        )
    return rows


def _build_all_players(player_scores: pd.DataFrame) -> list[dict[str, object]]:
    ordered = player_scores.sort_values(["draft_year", "round", "pick", "player_name"]).reset_index(drop=True)
    rows: list[dict[str, object]] = []
    for row in ordered.itertuples(index=False):
        rows.append(
            {
                "y": int(row.draft_year),
                "t": str(row.draft_team),
                "r": int(row.round),
                "p": int(row.pick),
                "n": str(row.player_name),
                "pos": str(row.position),
                "on": bool(row.still_on_drafting_team),
                "st": bool(row.starter_with_drafting_team),
                "sa": bool(row.starter_with_any_team),
                "ap": int(row.first_team_all_pro_count),
                "sc": round(float(row.raw_player_score), 4),
                "ssd": round(float(getattr(row, "snap_share_with_drafting_team", 0.0)), 4),
                "sse": round(float(getattr(row, "snap_share_elsewhere", 0.0)), 4),
                "psd": round(float(getattr(row, "peak_season_snap_share_with_drafting_team", 0.0)), 4),
                "psa": round(float(getattr(row, "peak_season_snap_share_any_team", 0.0)), 4),
            }
        )
    return rows


def render_interactive_report(
    output_path: Path,
    team_scores: pd.DataFrame,
    player_scores: pd.DataFrame,
    metadata: dict[str, Any],
) -> None:
    template_path = Path(__file__).with_name("report_template.html")
    template = template_path.read_text(encoding="utf-8")

    team_scores_js = json.dumps(_build_team_scores(team_scores), separators=(",", ":"))
    top_players_js = json.dumps(_build_top_players(player_scores), separators=(",", ":"))
    all_players_js = json.dumps(_build_all_players(player_scores), separators=(",", ":"))
    team_info_js = json.dumps(TEAM_INFO, separators=(",", ":"))

    html = template
    html = html.replace(">Starter</th>", ">Usage</th>")
    html = html.replace('<div class="score-lbl">Starter</div>', '<div class="score-lbl">Usage</div>')
    html = html.replace("Active Starters</th>", "Historical Starters</th>")
    html = html.replace(
        "Active Starters = players who are starters with the drafting team as of roster snapshot 2025-W18.",
        "Historical Starters = players who have recorded starter-level snap seasons with the drafting team since being drafted.",
    )
    html = _replace_one(
        r"<!-- SCORING_DETAILS_START -->.*?<!-- SCORING_DETAILS_END -->",
        (
            "<!-- SCORING_DETAILS_START -->\n            "
            + _build_scoring_details(metadata.get("scoring_config", {}))
            + "\n            <!-- SCORING_DETAILS_END -->"
        ),
        html,
    )
    html = _replace_one(
        r'<ul class="notes-list">.*?</ul>',
        """<ul class="notes-list">
          <li>Draft window fixed to 2021&ndash;2025 in v1.</li>
          <li>Rank is based solely on Draft Efficiency Index (DEI), not the component-score blend.</li>
          <li>v1 uses draft_picks.allpro as first-team All-Pro count. Second-team and award-vote scraping deferred.</li>
          <li>Retention uses canonical team codes plus roster status; released or retired players are not counted as retained.</li>
          <li>Usage value combines binary historical starter flags with continuous regular-season snap share.</li>
          <li>Regular-season snap share is measured against full team-season snap totals, not only games played.</li>
          <li>A small team-record context multiplier adjusts snap-share value so equivalent usage on stronger teams is worth slightly more.</li>
          <li>Historical Starters are still threshold-based snap-count outcomes since the draft, not current projected depth-chart starters.</li>
        </ul>""",
        html,
    )
    html = _replace_one(
        r'<p class="footer-line">Generated .*?</p>',
        (
            f'<p class="footer-line">Generated {metadata["generated_at"]} '
            f"&nbsp;&middot;&nbsp; Roster snapshot {metadata['latest_roster_snapshot']} "
            f"&nbsp;&middot;&nbsp; Snap counts through {metadata['latest_snap_count_season']}</p>"
        ),
        html,
    )
    html = _replace_one(r"const TEAM_INFO = \{.*?\};", f"const TEAM_INFO = {team_info_js};", html)
    html = _replace_one(r"const TEAM_SCORES = \[.*?\];", f"const TEAM_SCORES = {team_scores_js};", html)
    html = _replace_one(r"const TOP_PLAYERS = \[.*?\];", f"const TOP_PLAYERS = {top_players_js};", html)
    html = _replace_one(r"const ALL_PLAYERS = \[.*?\];", f"const ALL_PLAYERS = {all_players_js};", html)

    output_path.write_text(html, encoding="utf-8")
