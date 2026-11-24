"""Milestone 2 unit tests: self-healing selector loop, duplicate triage, and Held-Out eval."""

import json
import unittest
from pathlib import Path
from src.eval import EVAL_SUMMARY_PATH, evaluate_all_splits
from src.healer import heal_serp_parser
from src.models import SelectorSpec

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "serp_snapshots.json"


class TestMilestone2HealerAndEval(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
        cls.specs = {k: SelectorSpec(**v) for k, v in cls.data["specs"].items()}
        cls.snaps = {s["snapshot_id"]: s for s in cls.data["snapshots"]}

    def test_healthy_snapshot_uses_zero_llm_attempts(self) -> None:
        snap = self.snaps["yahoo_healthy_01"]
        report = heal_serp_parser(snap["html"], self.specs[snap["engine"]], snap["snapshot_id"])
        self.assertEqual(report.status, "healthy_no_heal_needed")
        self.assertEqual(len(report.attempts), 0)
        self.assertEqual(report.estimated_tokens, 0)

    def test_heals_yahoo_4596_and_finds_duplicate_issue(self) -> None:
        snap = self.snaps["yahoo_drifted_4596"]
        report = heal_serp_parser(snap["html"], self.specs[snap["engine"]], snap["snapshot_id"])
        self.assertEqual(report.status, "healed_awaiting_human_approval")
        self.assertIsNotNone(report.winning_selectors)
        self.assertEqual(report.winning_selectors.snippet_selector, "span.fc-falcon-desc")
        self.assertIn(4596, [d.number for d in report.duplicate_issues])
        self.assertTrue(report.human_approval_required)

    def test_heals_google_videos_4556_and_ai_overview_4550(self) -> None:
        for sid, expected_sel, expected_issue in (
            ("gvid_drifted_4556", "a.vid-canonical", 4556),
            ("aiov_drifted_4550", "a.ai-source-url", 4550),
        ):
            snap = self.snaps[sid]
            report = heal_serp_parser(snap["html"], self.specs[snap["engine"]], sid)
            self.assertEqual(report.status, "healed_awaiting_human_approval")
            self.assertEqual(report.winning_selectors.link_selector, expected_sel)
            self.assertIn(expected_issue, [d.number for d in report.duplicate_issues])

    def test_escalates_verify_wall_4554_without_selector_patch(self) -> None:
        snap = self.snaps["gshort_wall_4554"]
        report = heal_serp_parser(snap["html"], self.specs[snap["engine"]], snap["snapshot_id"])
        self.assertEqual(report.status, "quarantined_needs_engineer")
        self.assertIsNone(report.winning_selectors)
        self.assertIn(4554, [d.number for d in report.duplicate_issues])
        self.assertEqual(report.attempts[0].decision, "ESCALATE_HUMAN")

    def test_eval_passes_both_dev_and_unseen_heldout_splits(self) -> None:
        summary = evaluate_all_splits()
        self.assertEqual(summary["dev"]["exact_triage_passed"], "7/7")
        self.assertEqual(summary["heldout"]["exact_triage_passed"], "4/4")
        self.assertEqual(summary["dev"]["false_alarms"], "0/3")
        self.assertTrue(EVAL_SUMMARY_PATH.exists())


if __name__ == "__main__":
    unittest.main()
