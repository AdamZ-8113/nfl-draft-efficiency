from __future__ import annotations

import unittest

import pandas as pd

from nfl_draft_efficiency.config import load_runtime_config
from nfl_draft_efficiency.starter_model import compute_starter_flags


def _make_snap_rows(player: str, pfr_id: str, team: str, position: str, column: str, pct: float, games: int) -> list[dict]:
    rows = []
    for week in range(1, games + 1):
        offense_snaps = 60 if column == "offense" else 0
        defense_snaps = 60 if column == "defense" else 0
        st_snaps = 20 if column == "special" else 0
        rows.append(
            {
                "season": 2025,
                "week": week,
                "team": team,
                "player": player,
                "pfr_player_id": pfr_id,
                "position": position,
                "offense_snaps": offense_snaps,
                "offense_pct": pct if column == "offense" else 0,
                "defense_snaps": defense_snaps,
                "defense_pct": pct if column == "defense" else 0,
                "st_snaps": st_snaps,
                "st_pct": pct if column == "special" else 0,
            }
        )
    return rows


class StarterModelTests(unittest.TestCase):
    def test_position_aware_starter_thresholds(self) -> None:
        config = load_runtime_config()
        draft_picks = pd.DataFrame(
            [
                {"draft_player_id": 1, "draft_year": 2025, "draft_team": "CHI", "player_name": "QB One", "position": "QB", "pfr_player_id": "QB1"},
                {"draft_player_id": 2, "draft_year": 2025, "draft_team": "CHI", "player_name": "WR One", "position": "WR", "pfr_player_id": "WR1"},
                {"draft_player_id": 3, "draft_year": 2025, "draft_team": "SEA", "player_name": "RB One", "position": "RB", "pfr_player_id": "RB1"},
                {"draft_player_id": 4, "draft_year": 2025, "draft_team": "DAL", "player_name": "DL One", "position": "DE", "pfr_player_id": "DL1"},
                {"draft_player_id": 5, "draft_year": 2025, "draft_team": "NE", "player_name": "ST One", "position": "WR", "pfr_player_id": "ST1"},
                {"draft_player_id": 6, "draft_year": 2025, "draft_team": "SFO", "player_name": "Niners Starter", "position": "QB", "pfr_player_id": "QB6"},
            ]
        )
        snap_counts = pd.DataFrame(
            _make_snap_rows("QB One", "QB1", "CHI", "QB", "offense", 55, 6)
            + _make_snap_rows("WR One", "WR1", "CHI", "WR", "offense", 55, 6)
            + _make_snap_rows("RB One", "RB1", "SEA", "RB", "offense", 40, 8)
            + _make_snap_rows("DL One", "DL1", "DAL", "DE", "defense", 50, 8)
            + _make_snap_rows("ST One", "ST1", "NE", "WR", "special", 60, 8)
            + _make_snap_rows("Niners Starter", "QB6", "SF", "QB", "offense", 60, 6)
        )
        team_records = pd.DataFrame(
            [
                {"season": 2025, "team": "CHI", "win_pct": 0.5},
                {"season": 2025, "team": "SEA", "win_pct": 0.5},
                {"season": 2025, "team": "DAL", "win_pct": 0.5},
                {"season": 2025, "team": "NE", "win_pct": 0.5},
                {"season": 2025, "team": "SF", "win_pct": 1.0},
            ]
        )

        flags = compute_starter_flags(snap_counts, draft_picks, config, team_records=team_records).set_index("draft_player_id")

        self.assertTrue(bool(flags.loc[1, "starter_with_any_team"]))
        self.assertFalse(bool(flags.loc[2, "starter_with_any_team"]))
        self.assertTrue(bool(flags.loc[3, "starter_with_any_team"]))
        self.assertTrue(bool(flags.loc[4, "starter_with_any_team"]))
        self.assertFalse(bool(flags.loc[5, "starter_with_any_team"]))
        self.assertTrue(bool(flags.loc[5, "special_teams_contributor"]))
        self.assertTrue(bool(flags.loc[6, "starter_with_drafting_team"]))
        self.assertAlmostEqual(float(flags.loc[6, "snap_share_with_drafting_team"]), 1.0, places=6)
        multiplier = 1.0 + float(config["team_record_adjustment"]["win_pct_multiplier_weight"]) * 0.5
        multiplier = min(max(multiplier, float(config["team_record_adjustment"]["min_multiplier"])), float(config["team_record_adjustment"]["max_multiplier"]))
        self.assertAlmostEqual(float(flags.loc[6, "record_adjusted_snap_share_with_drafting_team"]), multiplier, places=6)


if __name__ == "__main__":
    unittest.main()
