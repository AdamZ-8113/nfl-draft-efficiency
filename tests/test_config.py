from __future__ import annotations

import unittest

from nfl_draft_efficiency.config import load_runtime_config, resolve_draft_years


class ConfigTests(unittest.TestCase):
    def test_default_draft_window_is_ten_years(self) -> None:
        config = load_runtime_config()

        self.assertEqual(
            resolve_draft_years(config),
            [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        )

    def test_draft_window_years_uses_configured_max_year(self) -> None:
        config = load_runtime_config()

        self.assertEqual(resolve_draft_years(config, draft_window_years=5), [2021, 2022, 2023, 2024, 2025])

    def test_draft_window_years_can_anchor_to_max_year(self) -> None:
        config = load_runtime_config()

        self.assertEqual(
            resolve_draft_years(config, draft_window_years=3, max_draft_year=2023),
            [2021, 2022, 2023],
        )


if __name__ == "__main__":
    unittest.main()
