from __future__ import annotations

import unittest

from nfl_draft_efficiency.validation import _extract_espn_state


class ValidationTests(unittest.TestCase):
    def test_extract_espn_state_from_html(self) -> None:
        html = """
        <html>
          <body>
            <script>window['__espnfitt__']={"page":{"content":{"roster":{"groups":[]}}}};</script>
          </body>
        </html>
        """
        state = _extract_espn_state(html)
        self.assertEqual(state["page"]["content"]["roster"]["groups"], [])


if __name__ == "__main__":
    unittest.main()
