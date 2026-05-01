from __future__ import annotations

import math
import unittest

import pandas as pd

from nfl_draft_efficiency.aggregate import aggregate_team_scores


class AggregationTests(unittest.TestCase):
    def test_team_aggregation_and_rank_order(self) -> None:
        player_scores = pd.DataFrame(
            [
                {
                    "draft_player_id": 1,
                    "draft_team": "AAA",
                    "draft_year": 2025,
                    "round": 1,
                    "pick_cost": 8.0,
                    "still_on_drafting_team": True,
                    "starter_with_drafting_team": True,
                    "starter_with_any_team": True,
                    "starter_seasons_with_any_team": 5,
                    "first_team_all_pro_count": 1,
                    "second_team_all_pro_count": 0,
                    "top5_award_finish_count": 0,
                    "retention_points": 1.0,
                    "starter_points": 4.0,
                    "snap_share_points": 1.5,
                    "star_points": 8.0,
                    "normalized_player_score": 13.0,
                },
                {
                    "draft_player_id": 2,
                    "draft_team": "BBB",
                    "draft_year": 2025,
                    "round": 5,
                    "pick_cost": 4.0,
                    "still_on_drafting_team": False,
                    "starter_with_drafting_team": False,
                    "starter_with_any_team": True,
                    "starter_seasons_with_any_team": 2,
                    "first_team_all_pro_count": 0,
                    "second_team_all_pro_count": 0,
                    "top5_award_finish_count": 0,
                    "retention_points": 0.0,
                    "starter_points": 3.0,
                    "snap_share_points": 0.5,
                    "star_points": 0.0,
                    "normalized_player_score": 3.0,
                },
            ]
        )

        team_scores = aggregate_team_scores(player_scores, [2021, 2022, 2023, 2024, 2025])
        aaa = team_scores.loc[team_scores["team"] == "AAA"].iloc[0]
        bbb = team_scores.loc[team_scores["team"] == "BBB"].iloc[0]

        self.assertTrue(math.isclose(aaa["team_score"], 13.0 / 8.0))
        self.assertTrue(math.isclose(bbb["team_score"], 3.0 / 4.0))
        self.assertTrue(math.isclose(aaa["snap_share_score"], 1.5 / 8.0))
        self.assertTrue(math.isclose(bbb["snap_share_score"], 0.5 / 4.0))
        self.assertTrue(math.isclose(aaa["avg_starter_years_any_team"], 5.0))
        self.assertTrue(math.isclose(bbb["avg_starter_years_any_team"], 2.0))
        self.assertIn("late_round_dei", team_scores.columns)
        self.assertGreater(bbb["late_round_dei"], aaa["late_round_dei"])
        self.assertGreater(aaa["draft_efficiency_index"], bbb["draft_efficiency_index"])
        self.assertEqual(int(aaa["rank"]), 1)
        self.assertEqual(int(bbb["rank"]), 2)

    def test_missing_premium_pick_penalty_is_optional(self) -> None:
        player_scores = pd.DataFrame(
            [
                {
                    "draft_player_id": 1,
                    "draft_team": "AAA",
                    "draft_year": 2025,
                    "round": 2,
                    "pick_cost": 6.0,
                    "still_on_drafting_team": False,
                    "starter_with_drafting_team": False,
                    "starter_with_any_team": False,
                    "first_team_all_pro_count": 0,
                    "second_team_all_pro_count": 0,
                    "top5_award_finish_count": 0,
                    "retention_points": 0.0,
                    "starter_points": 0.0,
                    "snap_share_points": 0.0,
                    "star_points": 0.0,
                    "early_round_bust": True,
                    "bust_penalty_points": -2.5,
                    "normalized_player_score": 0.0,
                    "bust_adjusted_normalized_player_score": -2.5,
                }
            ]
        )
        config = {
            "round_pick_cost": {1: 8.0, 2: 6.0, 3: 4.0},
            "opportunity_normalization": {"method": "sqrt", "max_seasons": 8},
            "early_round_bust_adjustment": {
                "rounds": [1, 2, 3],
                "missing_pick_penalty_by_round": {1: -4.0, 2: -2.5, 3: -1.5},
            },
        }

        without_missing = aggregate_team_scores(
            player_scores,
            [2025],
            config=config,
            penalize_missing_premium_picks=False,
        ).iloc[0]
        with_missing = aggregate_team_scores(
            player_scores,
            [2025],
            config=config,
            penalize_missing_premium_picks=True,
        ).iloc[0]

        self.assertEqual(int(without_missing["missing_premium_pick_count"]), 0)
        self.assertEqual(int(with_missing["missing_premium_pick_count"]), 2)
        self.assertTrue(math.isclose(with_missing["missing_pick_penalty_points"], -5.5))
        self.assertLess(with_missing["bust_adjusted_team_score"], without_missing["bust_adjusted_team_score"])


if __name__ == "__main__":
    unittest.main()
