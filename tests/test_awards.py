from __future__ import annotations

import unittest

import pandas as pd

from nfl_draft_efficiency.awards import build_awards_frame


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


if __name__ == "__main__":
    unittest.main()
