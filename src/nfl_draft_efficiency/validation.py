from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .normalize_ids import normalize_name
from .teams import get_espn_team_page, normalize_team_code


_ESPN_STATE_PATTERN = re.compile(r"window\['__espnfitt__'\]=(\{.*\});</script>", flags=re.DOTALL)
_REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}


@dataclass
class ESPNTeamReference:
    roster_groups: dict[str, list[str]]
    starter_slots: dict[str, list[str]]


def _fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers=_REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def _extract_espn_state(html: str) -> dict[str, Any]:
    match = _ESPN_STATE_PATTERN.search(html)
    if not match:
        raise ValueError("Unable to locate ESPN page state.")
    return json.loads(match.group(1))


def _load_espn_roster_groups(team_code: str) -> dict[str, list[str]]:
    page_state = _extract_espn_state(_fetch_html(get_espn_team_page(team_code, "roster")))
    groups = page_state["page"]["content"]["roster"]["groups"]

    roster_groups: dict[str, list[str]] = {}
    for group in groups:
        group_name = str(group.get("name", "")).strip()
        for athlete in group.get("athletes", []):
            normalized = normalize_name(athlete.get("name"))
            if not normalized:
                continue
            roster_groups.setdefault(normalized, [])
            if group_name and group_name not in roster_groups[normalized]:
                roster_groups[normalized].append(group_name)
    return roster_groups


def _load_espn_depth_starters(team_code: str) -> dict[str, list[str]]:
    page_state = _extract_espn_state(_fetch_html(get_espn_team_page(team_code, "depth")))
    groups = page_state["page"]["content"]["depth"]["dethTeamGroups"]

    starter_slots: dict[str, list[str]] = {}
    for group in groups:
        group_name = str(group.get("name", "")).strip()
        for row in group.get("rows", []):
            if len(row) < 2 or not isinstance(row[1], dict):
                continue
            starter = row[1]
            normalized = normalize_name(starter.get("name"))
            if not normalized:
                continue
            slot_name = str(row[0]).strip()
            descriptor = f"{group_name}:{slot_name}" if group_name and slot_name else slot_name or group_name
            starter_slots.setdefault(normalized, [])
            if descriptor and descriptor not in starter_slots[normalized]:
                starter_slots[normalized].append(descriptor)
    return starter_slots


def _load_espn_reference(team_code: str) -> ESPNTeamReference:
    canonical_team = normalize_team_code(team_code)
    return ESPNTeamReference(
        roster_groups=_load_espn_roster_groups(canonical_team),
        starter_slots=_load_espn_depth_starters(canonical_team),
    )


def build_external_validation(player_scores: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    working = player_scores.copy()
    working["draft_team"] = working["draft_team"].map(normalize_team_code)
    working["normalized_name"] = working["player_name"].map(normalize_name)

    references: dict[str, ESPNTeamReference] = {}
    errors: list[dict[str, str]] = []
    for team_code in sorted(working["draft_team"].dropna().astype(str).unique().tolist()):
        if not team_code:
            continue
        try:
            references[team_code] = _load_espn_reference(team_code)
        except Exception as exc:
            errors.append({"team": team_code, "source": "espn", "error": str(exc)})

    rows: list[dict[str, Any]] = []
    for row in working.itertuples(index=False):
        reference = references.get(row.draft_team)
        roster_groups = reference.roster_groups.get(row.normalized_name, []) if reference else []
        starter_slots = reference.starter_slots.get(row.normalized_name, []) if reference else []

        espn_on_drafting_team = bool(roster_groups)
        espn_current_depth_starter = bool(starter_slots)
        issues: list[str] = []
        if reference is None:
            issues.append("espn_reference_unavailable")
        elif espn_on_drafting_team != bool(row.still_on_drafting_team):
            issues.append("roster_membership_mismatch")
        if reference is not None and espn_on_drafting_team and espn_current_depth_starter and not bool(row.starter_with_drafting_team):
            issues.append("current_depth_chart_starter_not_historical_starter")

        rows.append(
            {
                "draft_player_id": row.draft_player_id,
                "draft_year": row.draft_year,
                "draft_team": row.draft_team,
                "player_name": row.player_name,
                "position": row.position,
                "pipeline_latest_roster_team": row.latest_roster_team,
                "pipeline_latest_team": row.latest_team,
                "pipeline_latest_roster_status": row.latest_roster_status,
                "pipeline_latest_roster_status_bucket": row.latest_roster_status_bucket,
                "pipeline_still_on_drafting_team": bool(row.still_on_drafting_team),
                "pipeline_starter_with_drafting_team": bool(row.starter_with_drafting_team),
                "espn_on_drafting_team": espn_on_drafting_team,
                "espn_roster_groups": " | ".join(roster_groups),
                "espn_current_depth_starter": espn_current_depth_starter,
                "espn_depth_starter_slots": " | ".join(starter_slots),
                "validation_issues": "; ".join(issues),
            }
        )

    validation_frame = pd.DataFrame(
        rows,
        columns=[
            "draft_player_id",
            "draft_year",
            "draft_team",
            "player_name",
            "position",
            "pipeline_latest_roster_team",
            "pipeline_latest_team",
            "pipeline_latest_roster_status",
            "pipeline_latest_roster_status_bucket",
            "pipeline_still_on_drafting_team",
            "pipeline_starter_with_drafting_team",
            "espn_on_drafting_team",
            "espn_roster_groups",
            "espn_current_depth_starter",
            "espn_depth_starter_slots",
            "validation_issues",
        ],
    )
    return validation_frame, errors


def write_external_validation_outputs(
    output_dir: Path,
    validation_frame: pd.DataFrame,
    errors: list[dict[str, str]],
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    validation_csv = output_dir / "external_validation.csv"
    issues_csv = output_dir / "external_validation_issues.csv"
    summary_md = output_dir / "external_validation_summary.md"

    issues_frame = validation_frame[validation_frame["validation_issues"].astype("string").str.len().fillna(0) > 0].copy()
    validation_frame.to_csv(validation_csv, index=False)
    issues_frame.to_csv(issues_csv, index=False)

    roster_mismatch_count = int(
        validation_frame["validation_issues"].astype("string").str.contains("roster_membership_mismatch", regex=False).fillna(False).sum()
    )
    starter_advisory_count = int(
        validation_frame["validation_issues"]
        .astype("string")
        .str.contains("current_depth_chart_starter_not_historical_starter", regex=False)
        .fillna(False)
        .sum()
    )

    error_lines = ["- None"] if not errors else [f"- `{error['team']}`: {error['error']}" for error in errors]
    summary = f"""# External Validation Summary

- Validation source: `ESPN roster` and `ESPN depth chart`
- Players checked: `{len(validation_frame)}`
- Teams fetched successfully: `{validation_frame['draft_team'].nunique() - len(errors)}`
- Teams with fetch errors: `{len(errors)}`
- Roster membership mismatches: `{roster_mismatch_count}`
- Current depth-chart starter advisories: `{starter_advisory_count}`

## Notes

- `roster_membership_mismatch` means the pipeline and ESPN disagree on whether the player is currently with his drafting team.
- `current_depth_chart_starter_not_historical_starter` is advisory: ESPN marks the player as a current first-team depth-chart starter, but the pipeline's historical snap-count starter flag is still false.

## Fetch Errors

{chr(10).join(error_lines)}
"""
    summary_md.write_text(summary, encoding="utf-8")

    return {
        "external_validation_csv": validation_csv,
        "external_validation_issues_csv": issues_csv,
        "external_validation_summary_md": summary_md,
    }
