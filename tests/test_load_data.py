from __future__ import annotations

import unittest

import pandas as pd

from nfl_draft_efficiency.config import load_runtime_config
from nfl_draft_efficiency.load_data import (
    build_team_records,
    match_latest_roster_snapshot,
    standardize_draft_picks,
    standardize_games,
    standardize_roster_snapshot,
)


class LoadDataTests(unittest.TestCase):
    def test_standardizers_normalize_team_codes(self) -> None:
        config = load_runtime_config()
        draft_frame = pd.DataFrame(
            [
                {
                    "season": 2025,
                    "team": "SFO",
                    "round": 1,
                    "pick": 1,
                    "overall": 1,
                    "position": "QB",
                    "gsis_id": "GSIS1",
                    "pfr_player_id": "PFR1",
                    "player_name": "Player One",
                    "allpro": 0,
                }
            ]
        )
        roster_frame = pd.DataFrame(
            [
                {
                    "full_name": "Player One",
                    "team": "SF",
                    "position": "QB",
                    "gsis_id": "GSIS1",
                    "status": "ACT",
                    "status_description_abbr": "A01",
                }
            ]
        )

        standardized_draft = standardize_draft_picks(draft_frame, [2025], config)
        standardized_roster = standardize_roster_snapshot(roster_frame, config)

        self.assertEqual(standardized_draft.loc[0, "draft_team"], "SF")
        self.assertEqual(standardized_roster.loc[0, "team"], "SF")

    def test_roster_match_uses_status_aware_current_team_logic(self) -> None:
        draft_picks = pd.DataFrame(
            [
                {
                    "draft_player_id": 1,
                    "draft_team": "SFO",
                    "gsis_id": "GSIS1",
                    "normalized_name": "brock purdy",
                    "position_group": "QB",
                },
                {
                    "draft_player_id": 2,
                    "draft_team": "NOR",
                    "gsis_id": "GSIS2",
                    "normalized_name": "retired player",
                    "position_group": "QB",
                },
            ]
        )
        roster_snapshot = pd.DataFrame(
            [
                {
                    "gsis_id": "GSIS1",
                    "player_name": "Brock Purdy",
                    "team": "SF",
                    "roster_status": "ACT",
                    "roster_status_description_abbr": "A01",
                    "roster_status_bucket": "active_roster",
                    "roster_status_priority": 40,
                    "counts_as_current_team": True,
                    "position": "QB",
                    "normalized_name": "brock purdy",
                    "position_group": "QB",
                },
                {
                    "gsis_id": "GSIS2",
                    "player_name": "Retired Player",
                    "team": "NO",
                    "roster_status": "RET",
                    "roster_status_description_abbr": "",
                    "roster_status_bucket": "not_with_team",
                    "roster_status_priority": 0,
                    "counts_as_current_team": False,
                    "position": "QB",
                    "normalized_name": "retired player",
                    "position_group": "QB",
                },
            ]
        )

        matches = match_latest_roster_snapshot(draft_picks, roster_snapshot).set_index("draft_player_id")

        self.assertEqual(matches.loc[1, "latest_roster_team"], "SF")
        self.assertEqual(matches.loc[1, "latest_team"], "SF")
        self.assertTrue(bool(matches.loc[1, "still_on_drafting_team"]))
        self.assertTrue(bool(matches.loc[1, "has_current_roster_match"]))

        self.assertEqual(matches.loc[2, "latest_roster_team"], "NO")
        self.assertTrue(pd.isna(matches.loc[2, "latest_team"]))
        self.assertEqual(matches.loc[2, "latest_roster_status"], "RET")
        self.assertFalse(bool(matches.loc[2, "still_on_drafting_team"]))
        self.assertTrue(bool(matches.loc[2, "has_roster_match"]))
        self.assertFalse(bool(matches.loc[2, "has_current_roster_match"]))

    def test_build_team_records_from_regular_season_games(self) -> None:
        games = pd.DataFrame(
            [
                {
                    "season": 2025,
                    "game_type": "REG",
                    "week": 1,
                    "home_team": "SFO",
                    "away_team": "SEA",
                    "home_score": 24,
                    "away_score": 17,
                },
                {
                    "season": 2025,
                    "game_type": "REG",
                    "week": 2,
                    "home_team": "SEA",
                    "away_team": "SFO",
                    "home_score": 10,
                    "away_score": 10,
                },
                {
                    "season": 2025,
                    "game_type": "POST",
                    "week": 20,
                    "home_team": "SFO",
                    "away_team": "SEA",
                    "home_score": 30,
                    "away_score": 0,
                },
            ]
        )

        records = build_team_records(standardize_games(games)).set_index(["season", "team"])

        self.assertEqual(int(records.loc[(2025, "SF"), "wins"]), 1)
        self.assertEqual(int(records.loc[(2025, "SF"), "ties"]), 1)
        self.assertAlmostEqual(float(records.loc[(2025, "SF"), "win_pct"]), 0.75)
        self.assertEqual(int(records.loc[(2025, "SEA"), "losses"]), 1)


if __name__ == "__main__":
    unittest.main()
