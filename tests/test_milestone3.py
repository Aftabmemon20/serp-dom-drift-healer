"""Milestone 3 unit tests for FastAPI endpoints."""

import unittest
from src.api import HealRequest, get_eval_summary, health_check, list_snapshots, run_heal, serve_ui


class TestMilestone3API(unittest.TestCase):
    def test_health_and_ui(self) -> None:
        h = health_check()
        self.assertEqual(h["status"], "ok")
        html = serve_ui()
        self.assertIn("SerpApi DOM Healer", html)

    def test_list_snapshots(self) -> None:
        res = list_snapshots()
        self.assertEqual(len(res["snapshots"]), 11)

    def test_heal_endpoint_repairs_yahoo_4596(self) -> None:
        res = run_heal(HealRequest(snapshot_id="yahoo_drifted_4596"))
        self.assertEqual(res["report"]["status"], "healed_awaiting_human_approval")
        self.assertEqual(res["report"]["winning_selectors"]["snippet_selector"], "span.fc-falcon-desc")

    def test_eval_summary_endpoint(self) -> None:
        res = get_eval_summary()
        self.assertEqual(res["dev"]["exact_triage_passed"], "7/7")
        self.assertEqual(res["heldout"]["exact_triage_passed"], "4/4")


if __name__ == "__main__":
    unittest.main()
