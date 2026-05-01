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
                    "pick_cost": 8.0,
                    "still_on_drafting_team": True,
                    "starter_with_drafting_team": True,
                    "starter_with_any_team": True,
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
                    "pick_cost": 4.0,
                    "still_on_drafting_team": False,
                    "starter_with_drafting_team": False,
                    "starter_with_any_team": True,
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
        self.assertGreater(aaa["draft_efficiency_index"], bbb["draft_efficiency_index"])
        self.assertEqual(int(aaa["rank"]), 1)
        self.assertEqual(int(bbb["rank"]), 2)


if __name__ == "__main__":
    unittest.main()
