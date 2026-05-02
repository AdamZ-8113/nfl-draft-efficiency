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
        ("MIN", {"name": "Minnesota Vikings", "color": "#4F2683"}),
        ("NE", {"name": "New England Patriots", "color": "#C60C30"}),
        ("NO", {"name": "New Orleans Saints", "color": "#C2A35D"}),
        ("NYG", {"name": "New York Giants", "color": "#A71930"}),
        ("NYJ", {"name": "New York Jets", "color": "#3DA35C"}),
        ("PHI", {"name": "Philadelphia Eagles", "color": "#007A33"}),
        ("PIT", {"name": "Pittsburgh Steelers", "color": "#FFB612"}),
        ("SEA", {"name": "Seattle Seahawks", "color": "#69BE28"}),
        ("SF", {"name": "San Francisco 49ers", "color": "#CF2B2B"}),
        ("TB", {"name": "Tampa Bay Buccaneers", "color": "#D50A0A"}),
        ("TEN", {"name": "Tennessee Titans", "color": "#4B92DB"}),
        ("WAS", {"name": "Washington Commanders", "color": "#FFB612"}),
    ]
)


def _replace_one(pattern: str, replacement: str, text: str) -> str:
    updated, count = re.subn(pattern, lambda _match: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"Expected exactly one replacement for pattern: {pattern}")
    return updated


def _fmt_points(value: Any) -> str:
    number = float(value)
    text = f"{number:g}"
    return f"{text} pt" if number == 1 else f"{text} pts"


def _fmt_value(value: Any) -> str:
    return f"{float(value):g}"


def _mapping_get(mapping: dict[Any, Any], key: int, default: Any = 0) -> Any:
    return mapping.get(key, mapping.get(str(key), default))


def _table_rows(rows: list[tuple[str, str]]) -> str:
    return "\n".join(
        f"                    <tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>"
        for label, value in rows
    )


def _build_scoring_details(config: dict[str, Any]) -> str:
    round_pick_cost = config.get("round_pick_cost", {})
    points = config.get("points", {})
    snap_share = config.get("snap_share_value", {})
    starter_longevity = config.get("starter_longevity_value", {})
    team_record = config.get("team_record_adjustment", {})
    opportunity = config.get("opportunity_normalization", {})
    composite = config.get("composite_weights", {})
    bust_adjustment = config.get("early_round_bust_adjustment", {})
    bust_penalty_by_round = bust_adjustment.get("penalty_by_round", {})
    missing_penalty_by_round = bust_adjustment.get("missing_pick_penalty_by_round", {})

    round_rows = [
        (f"Round {round_number}", _fmt_points(_mapping_get(round_pick_cost, round_number, 0)))
        for round_number in range(1, 8)
    ]
    point_rows = [
        ("Still with drafting team", _fmt_points(points.get("still_on_drafting_team", 0))),
        ("Starter with drafting team", _fmt_points(points.get("starter_with_drafting_team", 0))),
        ("Starter with any team", _fmt_points(points.get("starter_with_any_team", 0))),
        ("Second-team All-Pro", _fmt_points(points.get("second_team_all_pro", 0))),
        ("First-team All-Pro", _fmt_points(points.get("first_team_all_pro", 0))),
        ("AP player-award recognition", _fmt_points(points.get("top5_award_finish", 0))),
        ("AP MVP recognition", _fmt_points(points.get("top5_mvp_finish", 0))),
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
    starter_longevity_rows = [
        (
            "Baseline starter seasons",
            _fmt_value(starter_longevity.get("baseline_starter_seasons", 1)),
        ),
        (
            "Max extra starter seasons",
            _fmt_value(starter_longevity.get("max_extra_starter_seasons", 0)),
        ),
        (
            "Extra year with drafting team",
            _fmt_points(starter_longevity.get("with_drafting_team_per_extra_starter_season", 0)),
        ),
        (
            "Extra year elsewhere",
            _fmt_points(starter_longevity.get("elsewhere_per_extra_starter_season", 0)),
        ),
    ]
    normalization_rows = [
        ("Opportunity method", str(opportunity.get("method", ""))),
        ("Maximum seasons", _fmt_value(opportunity.get("max_seasons", 0))),
        ("Composite retention weight", _fmt_value(composite.get("retention", 0))),
        ("Composite starter weight", _fmt_value(composite.get("starter", 0))),
        ("Composite star weight", _fmt_value(composite.get("star", 0))),
    ]
    bust_rows = [
        ("Bust rounds", ", ".join(f"Round {round_value}" for round_value in bust_adjustment.get("rounds", []))),
        ("Round 1 bust penalty", _fmt_points(_mapping_get(bust_penalty_by_round, 1, 0))),
        ("Round 2 bust penalty", _fmt_points(_mapping_get(bust_penalty_by_round, 2, 0))),
        ("Round 3 bust penalty", _fmt_points(_mapping_get(bust_penalty_by_round, 3, 0))),
        ("Round 1 missing-pick penalty", _fmt_points(_mapping_get(missing_penalty_by_round, 1, 0))),
        ("Round 2 missing-pick penalty", _fmt_points(_mapping_get(missing_penalty_by_round, 2, 0))),
        ("Round 3 missing-pick penalty", _fmt_points(_mapping_get(missing_penalty_by_round, 3, 0))),
        ("Minimum seasons before bust", _fmt_value(bust_adjustment.get("min_eligible_seasons", 0))),
        ("Max peak snap share for bust", f"{float(bust_adjustment.get('max_peak_snap_share_any_team', 0)) * 100:g}%"),
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
                <h3>Starter Longevity</h3>
                <p>The first starter season is already rewarded by starter status; extra starter seasons add capped bonus value.</p>
                <table>
                  <tbody>
{_table_rows(starter_longevity_rows)}
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
              <div class="scoring-detail-card">
                <h3>Bust Adjustment</h3>
                <p>Rounds 1-3 can receive explicit negative value when a pick has enough time to develop but never becomes a meaningful contributor.</p>
                <table>
                  <tbody>
{_table_rows(bust_rows)}
                  </tbody>
                </table>
              </div>
            </div>"""


def _draft_year_label(metadata: dict[str, Any]) -> str:
    years = [int(year) for year in metadata.get("draft_years", [])]
    if not years:
        return "Draft Window"
    return f"{min(years)}-{max(years)}"


SOURCE_LINKS = OrderedDict(
    [
        (
            "nflverse draft_picks release CSV",
            "https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.csv",
        ),
        (
            "nflverse roster_snapshot release CSV",
            "https://github.com/nflverse/nflverse-data/releases",
        ),
        (
            "nflverse weekly_rosters release CSV",
            "https://github.com/nflverse/nflverse-data/releases",
        ),
        (
            "nflverse snap_counts release CSV",
            "https://github.com/nflverse/nflverse-data/releases",
        ),
        (
            "nflverse games.csv regular-season records",
            "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
        ),
        (
            "draft_picks.allpro",
            "https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.csv",
        ),
        ("NFL.com AP Honors articles", "https://www.nfl.com/news"),
        (
            "Pro Football Reference AP award voting pages",
            "https://www.pro-football-reference.com/awards/",
        ),
        (
            "Associated Press NFL award voting rules",
            "https://www.ap.org/media-center/press-releases/2022/ap-updates-voting-system-for-its-nfl-awards/",
        ),
    ]
)


def _extract_inline_style(html: str) -> str | None:
    match = re.search(r"<style>\s*(.*?)\s*</style>", html, flags=re.S)
    if not match:
        return None
    return match.group(1).strip() + "\n"


def _ensure_stylesheet(output_path: Path, template_html: str, stylesheet_name: str = "report.css") -> None:
    stylesheet_path = output_path.with_name(stylesheet_name)
    if stylesheet_path.exists():
        return

    existing_style = None
    if output_path.exists():
        existing_style = _extract_inline_style(output_path.read_text(encoding="utf-8"))

    source_stylesheet_path = Path(__file__).with_name(stylesheet_name)
    if existing_style:
        stylesheet = existing_style
    elif source_stylesheet_path.exists():
        stylesheet = source_stylesheet_path.read_text(encoding="utf-8")
    else:
        stylesheet = _extract_inline_style(template_html)

    if not stylesheet:
        raise ValueError("Could not find report CSS in the stylesheet source or HTML template.")
    stylesheet_path.write_text(stylesheet, encoding="utf-8")


def _externalize_styles(html: str, stylesheet_name: str = "report.css") -> str:
    stylesheet_link = f'<link rel="stylesheet" href="{stylesheet_name}">'
    if re.search(r"<style>.*?</style>", html, flags=re.S):
        return _replace_one(r"<style>.*?</style>", stylesheet_link, html)
    if stylesheet_link in html:
        return html
    return html.replace("</head>", f"  {stylesheet_link}\n</head>", 1)


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
                "str": round(
                    float(row.starter_score)
                    + float(getattr(row, "snap_share_score", 0.0))
                    + float(getattr(row, "starter_longevity_score", 0.0)),
                    6,
                ),
                "star": round(float(row.star_score), 6),
                "apaw": int(getattr(row, "top5_award_finish_count", 0)) + int(getattr(row, "top5_mvp_finish_count", 0)),
                "mvp": int(getattr(row, "top5_mvp_finish_count", 0)),
                "prem": round(float(getattr(row, "premium_pick_dei", 0.0)), 2),
                "late": round(float(getattr(row, "late_round_dei", 0.0)), 2),
                "bust": round(float(getattr(row, "premium_bust_rate", 0.0) or 0.0), 4),
                "badj": round(float(getattr(row, "bust_adjusted_dei", 0.0)), 2),
                "miss": int(getattr(row, "missing_premium_pick_count", 0)),
                "picks": int(row.total_picks),
                "starters": round(float(getattr(row, "avg_starter_years_any_team", 0.0)), 2),
            }
        )
    return rows


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    text = str(value)
    return "" if text.lower() == "nan" else text


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
                "aw": int(getattr(row, "top5_award_finish_count", 0)),
                "mvp": int(getattr(row, "top5_mvp_finish_count", 0)),
                "awd": _clean_text(getattr(row, "ap_award_details", "")),
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
                "aw": int(getattr(row, "top5_award_finish_count", 0)),
                "mvp": int(getattr(row, "top5_mvp_finish_count", 0)),
                "awd": _clean_text(getattr(row, "ap_award_details", "")),
                "bst": bool(getattr(row, "early_round_bust", False)),
                "sc": round(float(row.raw_player_score), 4),
                "bas": round(float(getattr(row, "bust_adjusted_raw_player_score", row.raw_player_score)), 4),
                "syd": int(getattr(row, "starter_seasons_with_drafting_team", 0)),
                "sya": int(getattr(row, "starter_seasons_with_any_team", 0)),
                "ssd": round(float(getattr(row, "snap_share_with_drafting_team", 0.0)), 4),
                "sse": round(float(getattr(row, "snap_share_elsewhere", 0.0)), 4),
                "psd": round(float(getattr(row, "peak_season_snap_share_with_drafting_team", 0.0)), 4),
                "psa": round(float(getattr(row, "peak_season_snap_share_any_team", 0.0)), 4),
            }
        )
    return rows


def _build_sources(data_sources: list[str]) -> str:
    rows: list[str] = []
    for source in data_sources:
        url = SOURCE_LINKS.get(source)
        label = escape(source)
        if url:
            rows.append(f'              <li><a href="{escape(url)}">{label}</a></li>')
        else:
            rows.append(f"              <li>{label}</li>")
    if not rows:
        return '<ul class="sources-list"><li>Source metadata was not available for this run.</li></ul>'
    return "<ul class=\"sources-list\">\n" + "\n".join(rows) + "\n            </ul>"


def _metadata_for_browser(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "generatedAt": metadata.get("generated_at"),
        "draftYears": metadata.get("draft_years", []),
        "latestRosterSnapshot": metadata.get("latest_roster_snapshot"),
        "latestSnapCountSeason": metadata.get("latest_snap_count_season"),
        "penalizeMissingPremiumPicks": bool(metadata.get("penalize_missing_premium_picks", False)),
        "label": _draft_year_label(metadata),
    }


def _build_window_payload(
    team_scores: pd.DataFrame,
    player_scores: pd.DataFrame,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "label": _draft_year_label(metadata),
        "teamScores": _build_team_scores(team_scores),
        "topPlayers": _build_top_players(player_scores),
        "allPlayers": _build_all_players(player_scores),
        "metadata": _metadata_for_browser(metadata),
    }


def render_interactive_report(
    output_path: Path,
    team_scores: pd.DataFrame,
    player_scores: pd.DataFrame,
    metadata: dict[str, Any],
    report_windows: dict[int, dict[str, Any]] | None = None,
    default_window_years: int = 5,
) -> None:
    template_path = Path(__file__).with_name("report_template.html")
    template = template_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_stylesheet(output_path, template)

    team_info_js = json.dumps(TEAM_INFO, separators=(",", ":"))
    draft_year_label = _draft_year_label(metadata)
    if report_windows is None:
        window_key = len(metadata.get("draft_years", [])) or default_window_years
        report_windows = {window_key: _build_window_payload(team_scores, player_scores, metadata)}
        default_window_years = window_key
    report_windows_js = json.dumps(report_windows, separators=(",", ":"))

    html = _externalize_styles(template)
    html = _replace_one(
        r"<title>NFL Draft Efficiency .*?</title>",
        f"<title>NFL Draft Efficiency &mdash; {draft_year_label}</title>",
        html,
    )
    html = html.replace(">Starter</th>", ">Usage</th>")
    html = html.replace('<div class="score-lbl">Starter</div>', '<div class="score-lbl">Usage</div>')
    html = html.replace("2021-2025", draft_year_label)
    html = html.replace("Active Starters</th>", "Avg Starter Years</th>")
    html = html.replace("Historical Starters</th>", "Avg Starter Years</th>")
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
        r"<!-- SOURCES_START -->.*?<!-- SOURCES_END -->",
        (
            "<!-- SOURCES_START -->\n            "
            + _build_sources(metadata.get("data_sources", []))
            + "\n            <!-- SOURCES_END -->"
        ),
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
    html = _replace_one(r"const REPORT_WINDOWS = \{.*?\};", f"const REPORT_WINDOWS = {report_windows_js};", html)
    html = _replace_one(
        r"const DEFAULT_DRAFT_WINDOW = \d+;",
        f"const DEFAULT_DRAFT_WINDOW = {int(default_window_years)};",
        html,
    )

    output_path.write_text(html, encoding="utf-8")
