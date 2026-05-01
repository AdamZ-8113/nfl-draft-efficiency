from __future__ import annotations

import pandas as pd


def build_awards_frame(draft_picks: pd.DataFrame) -> pd.DataFrame:
    awards = draft_picks[["draft_player_id"]].copy()
    awards["top5_award_finish_count"] = 0
    awards["top5_mvp_finish_count"] = 0
    return awards

