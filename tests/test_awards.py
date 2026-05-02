from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from nfl_draft_efficiency.awards import build_awards_frame, load_ap_awards


class AwardsTests(unittest.TestCase):
    def test_build_awards_frame_matches_ap_awards_by_normalized_name(self) -> None:
        draft_picks = pd.DataFrame(
            [
                {"draft_player_id": 1, "draft_year": 2021, "player_name": "Ja'Marr Chase"},
                {"draft_player_id": 2, "draft_year": 2023, "player_name": "C.J. Stroud"},
                {"draft_player_id": 3, "draft_year": 2024, "player_name": "Unmatched Player"},
            ]
        )
        awards = pd.DataFrame(
            [
                {"season": 2021, "award": "OROY", "player_name": "Ja'Marr Chase"},
                {"season": 2024, "award": "MVP", "player_name": "C.J. Stroud"},
                {"season": 2022, "award": "DPOY", "player_name": "C.J. Stroud"},
            ]
        )

        result = build_awards_frame(draft_picks, awards=awards)

        chase = result[result["draft_player_id"] == 1].iloc[0]
        stroud = result[result["draft_player_id"] == 2].iloc[0]
        unmatched = result[result["draft_player_id"] == 3].iloc[0]

        self.assertEqual(chase["top5_award_finish_count"], 1)
        self.assertEqual(chase["top5_mvp_finish_count"], 0)
        self.assertEqual(chase["ap_award_details"], "2021 OROY")
        self.assertEqual(stroud["top5_award_finish_count"], 0)
        self.assertEqual(stroud["top5_mvp_finish_count"], 1)
        self.assertEqual(stroud["ap_award_details"], "2024 MVP")
        self.assertEqual(unmatched["top5_award_finish_count"], 0)
        self.assertEqual(unmatched["top5_mvp_finish_count"], 0)

    def test_load_awards_merges_manual_vote_finishers_without_network(self) -> None:
        with TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "ap_awards.csv"
            pd.DataFrame(
                [
                    {
                        "season": 2021,
                        "award": "OROY",
                        "player_name": "Ja'Marr Chase",
                        "team_position": "Cincinnati Bengals WR",
                        "result": "winner",
                        "source_url": "cached",
                    }
                ]
            ).to_csv(cache_path, index=False)

            awards = load_ap_awards(cache_path=cache_path)

        chase = awards[
            (awards["season"] == 2021)
            & (awards["award"] == "OROY")
            & (awards["player_name"] == "Ja'Marr Chase")
        ]
        bosa = awards[
            (awards["season"] == 2016)
            & (awards["award"] == "DROY")
            & (awards["player_name"] == "Joey Bosa")
        ]

        self.assertEqual(len(chase), 1)
        self.assertEqual(chase.iloc[0]["result"], "vote_finisher")
        self.assertEqual(len(bosa), 1)


if __name__ == "__main__":
    unittest.main()
