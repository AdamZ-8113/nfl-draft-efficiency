from __future__ import annotations

import json
import re
from collections import OrderedDict
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

    top_team = team_scores.sort_values(["rank", "team"]).iloc[0]
    team_count = len(team_scores.index)
    player_count = len(player_scores.index)
    top_color = TEAM_INFO.get(str(top_team["team"]), {}).get("color", "#3b82f6")

    team_scores_js = json.dumps(_build_team_scores(team_scores), separators=(",", ":"))
    top_players_js = json.dumps(_build_top_players(player_scores), separators=(",", ":"))
    all_players_js = json.dumps(_build_all_players(player_scores), separators=(",", ":"))
    team_info_js = json.dumps(TEAM_INFO, separators=(",", ":"))
    stat_grid_html = f"""<div class="stat-grid">
      <div class="stat-cell">
        <div class="stat-value" style="color:{top_color}">{top_team["team"]}</div>
        <div class="stat-label">Highest Draft Efficiency</div>
      </div>
      <div class="stat-cell">
        <div class="stat-value" style="font-size:22px">{float(top_team["draft_efficiency_index"]):.2f}</div>
        <div class="stat-label">Index Points &mdash; {top_team["team"]}</div>
      </div>
      <div class="stat-cell">
        <div class="stat-value">{team_count:,}</div>
        <div class="stat-label">Teams Evaluated</div>
      </div>
      <div class="stat-cell">
        <div class="stat-value">{player_count:,}</div>
        <div class="stat-label">Draft Picks Analyzed</div>
      </div>
    </div>"""

    html = template
    html = html.replace(">Starter</th>", ">Usage</th>")
    html = html.replace('<div class="score-lbl">Starter</div>', '<div class="score-lbl">Usage</div>')
    html = _replace_one(r'<div class="stat-grid">.*?</div>\s*</div>\s*<div class="two-col">', f"{stat_grid_html}\n\n    <div class=\"two-col\">", html)
    html = html.replace("Active Starters</th>", "Historical Starters</th>")
    html = html.replace(
        "Active Starters = players who are starters with the drafting team as of roster snapshot 2025-W18.",
        "Historical Starters = players who have recorded starter-level snap seasons with the drafting team since being drafted.",
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
