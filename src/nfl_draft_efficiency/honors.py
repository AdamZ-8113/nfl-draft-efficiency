from __future__ import annotations

from typing import Any

import pandas as pd


def build_honors_frame(draft_picks: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if "allpro" not in draft_picks.columns:
        raise ValueError("Draft picks data must include an 'allpro' column for v1 honors scoring.")

    honors = draft_picks[["draft_player_id", "allpro"]].copy()
    honors["first_team_all_pro_count"] = pd.to_numeric(honors["allpro"], errors="coerce").fillna(0).astype(int)
    if (honors["first_team_all_pro_count"] < 0).any():
        raise ValueError("All-Pro counts cannot be negative.")

    honors["second_team_all_pro_count"] = 0
    return honors[["draft_player_id", "first_team_all_pro_count", "second_team_all_pro_count"]]

