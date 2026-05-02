from __future__ import annotations

import math
import unittest

import pandas as pd

from nfl_draft_efficiency.scoring import build_player_scores, get_pick_cost


def _test_config() -> dict:
    return {
        "round_pick_cost": {1: 8.0, 2: 6.0, 3: 4.0, 4: 3.0, 5: 2.0, 6: 1.5, 7: 1.0},
        "points": {
            "still_on_drafting_team": 0.5,
            "starter_with_drafting_team": 4.0,
            "starter_with_any_team": 3.0,
            "second_team_all_pro": 1.0,
            "first_team_all_pro": 2.0,
            "top5_award_finish": 0.0,
            "top5_mvp_finish": 0.0,
        },
        "caps": {
            "max_all_pro_points_per_player": 24.0,
            "max_award_points_per_player": 16.0,
        },
        "opportunity_normalization": {"method": "sqrt", "max_seasons": 5},
        "snap_share_value": {
            "with_drafting_team_per_full_season": 1.0,
            "with_any_team_per_full_season": 0.5,
        },
        "starter_longevity_value": {
            "baseline_starter_seasons": 1,
            "max_extra_starter_seasons": 4,
            "with_drafting_team_per_extra_starter_season": 1.0,
            "elsewhere_per_extra_starter_season": 0.25,
        },
        "early_round_bust_adjustment": {
            "enabled": True,
            "rounds": [1, 2, 3],
            "penalty_by_round": {1: -4.0, 2: -2.5, 3: -1.5},
            "min_eligible_seasons": 2,
            "max_peak_snap_share_any_team": 0.35,
            "count_starter_elsewhere_as_non_bust": True,
            "count_honors_as_non_bust": True,
        },
    }


class ScoringTests(unittest.TestCase):
    def test_pick_cost_rounds_and_unknown_round(self) -> None:
        config = _test_config()
        self.assertEqual(get_pick_cost(1, config), 8.0)
        self.assertEqual(get_pick_cost(7, config), 1.0)
        with self.assertRaisesRegex(ValueError, "Unsupported draft round"):
            get_pick_cost(8, config)

    def test_player_scoring_handles_fractional_weights_and_snap_share_value(self) -> None:
        config = _test_config()
        draft_picks = pd.DataFrame(
            [
                {
                    "draft_player_id": 1,
                    "draft_year": 2021,
                    "draft_team": "DET",
                    "round": 1,
                    "pick": 1,
                    "overall": 1,
                    "player_name": "Alpha Player",
                    "position": "QB",
                    "gsis_id": "GSIS1",
                    "pfr_player_id": "PFR1",
                },
                {
                    "draft_player_id": 2,
                    "draft_year": 2022,
                    "draft_team": "GB",
                    "round": 7,
                    "pick": 1,
                    "overall": 250,
                    "player_name": "Beta Player",
                    "position": "WR",
                    "gsis_id": None,
                    "pfr_player_id": "PFR2",
                },
            ]
        )
        roster_matches = pd.DataFrame(
            [
                {
                    "draft_player_id": 1,
                    "latest_team": "DET",
                    "still_on_drafting_team": True,
                },
                {
                    "draft_player_id": 2,
                    "latest_team": "NYJ",
                    "still_on_drafting_team": False,
                },
            ]
        )
        starter_flags = pd.DataFrame(
            [
                {
                    "draft_player_id": 1,
                    "starter_with_drafting_team": True,
                    "starter_with_any_team": True,
                    "starter_seasons_with_drafting_team": 2,
                    "starter_seasons_with_any_team": 2,
                    "special_teams_contributor": False,
                    "has_snap_match": True,
                    "snap_match_method": "pfr_player_id",
                    "total_relevant_snaps_with_drafting_team": 1200.0,
                    "total_relevant_snaps_any_team": 1200.0,
                    "snap_share_with_drafting_team": 2.0,
                    "snap_share_elsewhere": 0.0,
                    "peak_season_snap_share_with_drafting_team": 1.0,
                    "peak_season_snap_share_any_team": 1.0,
                    "record_adjusted_snap_share_with_drafting_team": 2.0,
                    "record_adjusted_snap_share_elsewhere": 0.0,
                    "weighted_win_pct_with_drafting_team": 0.65,
                },
                {
                    "draft_player_id": 2,
                    "starter_with_drafting_team": False,
                    "starter_with_any_team": True,
                    "starter_seasons_with_drafting_team": 0,
                    "starter_seasons_with_any_team": 1,
                    "special_teams_contributor": False,
                    "has_snap_match": True,
                    "snap_match_method": "pfr_player_id",
                    "total_relevant_snaps_with_drafting_team": 0.0,
                    "total_relevant_snaps_any_team": 900.0,
                    "snap_share_with_drafting_team": 0.0,
                    "snap_share_elsewhere": 1.5,
                    "peak_season_snap_share_with_drafting_team": 0.0,
                    "peak_season_snap_share_any_team": 0.9,
                    "record_adjusted_snap_share_with_drafting_team": 0.0,
                    "record_adjusted_snap_share_elsewhere": 1.5,
                    "weighted_win_pct_with_drafting_team": None,
                },
            ]
        )
        honors = pd.DataFrame(
            [
                {"draft_player_id": 1, "first_team_all_pro_count": 4, "second_team_all_pro_count": 1},
                {"draft_player_id": 2, "first_team_all_pro_count": 0, "second_team_all_pro_count": 0},
            ]
        )
        awards = pd.DataFrame(
            [
                {"draft_player_id": 1, "top5_award_finish_count": 0, "top5_mvp_finish_count": 0},
                {"draft_player_id": 2, "top5_award_finish_count": 0, "top5_mvp_finish_count": 0},
            ]
        )

        scores = build_player_scores(
            draft_picks=draft_picks,
            roster_matches=roster_matches,
            starter_flags=starter_flags,
            honors=honors,
            awards=awards,
            latest_completed_season=2025,
            config=config,
        )

        alpha = scores.loc[scores["draft_player_id"] == 1].iloc[0]
        beta = scores.loc[scores["draft_player_id"] == 2].iloc[0]

        self.assertEqual(alpha["retention_points_raw"], 0.5)
        self.assertEqual(alpha["starter_points_raw"], 4.0)
        self.assertEqual(alpha["snap_share_points_raw"], 2.0)
        self.assertEqual(alpha["starter_longevity_points_raw"], 1.0)
        self.assertEqual(alpha["all_pro_points_raw"], 9.0)
        self.assertEqual(alpha["award_points_raw"], 0.0)
        self.assertEqual(alpha["raw_player_score"], 16.5)

        self.assertEqual(beta["retention_points_raw"], 0.0)
        self.assertEqual(beta["starter_points_raw"], 3.0)
        self.assertEqual(beta["snap_share_points_raw"], 0.75)
        self.assertEqual(beta["starter_longevity_points_raw"], 0.25)
        self.assertEqual(beta["raw_player_score"], 4.0)

        self.assertTrue(math.isclose(alpha["normalized_player_score"], 16.5 / math.sqrt(5)))
        self.assertTrue(math.isclose(beta["normalized_player_score"], 4.0 / math.sqrt(4)))

    def test_early_round_bust_penalty_applies_to_low_usage_miss(self) -> None:
        config = _test_config()
        draft_picks = pd.DataFrame(
            [
                {
                    "draft_player_id": 1,
                    "draft_year": 2022,
                    "draft_team": "DET",
                    "round": 1,
                    "pick": 1,
                    "overall": 1,
                    "player_name": "First Round Miss",
                    "position": "QB",
                    "gsis_id": "GSIS1",
                    "pfr_player_id": "PFR1",
                }
            ]
        )
        roster_matches = pd.DataFrame(
            [{"draft_player_id": 1, "latest_team": "DET", "still_on_drafting_team": False}]
        )
        starter_flags = pd.DataFrame(
            [
                {
                    "draft_player_id": 1,
                    "starter_with_drafting_team": False,
                    "starter_with_any_team": False,
                    "starter_seasons_with_drafting_team": 0,
                    "starter_seasons_with_any_team": 0,
                    "special_teams_contributor": False,
                    "has_snap_match": True,
                    "snap_match_method": "pfr_player_id",
                    "total_relevant_snaps_with_drafting_team": 100.0,
                    "total_relevant_snaps_any_team": 100.0,
                    "snap_share_with_drafting_team": 0.1,
                    "snap_share_elsewhere": 0.0,
                    "peak_season_snap_share_with_drafting_team": 0.2,
                    "peak_season_snap_share_any_team": 0.2,
                    "record_adjusted_snap_share_with_drafting_team": 0.1,
                    "record_adjusted_snap_share_elsewhere": 0.0,
                    "weighted_win_pct_with_drafting_team": 0.5,
                }
            ]
        )
        honors = pd.DataFrame(
            [{"draft_player_id": 1, "first_team_all_pro_count": 0, "second_team_all_pro_count": 0}]
        )
        awards = pd.DataFrame(
            [{"draft_player_id": 1, "top5_award_finish_count": 0, "top5_mvp_finish_count": 0}]
        )

        scores = build_player_scores(
            draft_picks=draft_picks,
            roster_matches=roster_matches,
            starter_flags=starter_flags,
            honors=honors,
            awards=awards,
            latest_completed_season=2025,
            config=config,
        )
        player = scores.iloc[0]

        self.assertTrue(bool(player["early_round_bust"]))
        self.assertEqual(player["bust_penalty_points_raw"], -4.0)
        self.assertTrue(
            math.isclose(
                player["bust_adjusted_normalized_player_score"],
                (0.1 - 4.0) / math.sqrt(4),
            )
        )


if __name__ == "__main__":
    unittest.main()
