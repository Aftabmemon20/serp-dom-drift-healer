"""Milestone 1 unit tests: deterministic SERP parsing & silent-200 regression detection."""

import json
import unittest
from pathlib import Path
from src.models import SelectorSpec
from src.parser import validate_serp_snapshot

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "serp_snapshots.json"


class TestMilestone1ParserAndContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
        cls.specs = {k: SelectorSpec(**v) for k, v in cls.data["specs"].items()}
        cls.snaps = {s["snapshot_id"]: s for s in cls.data["snapshots"]}

    def test_healthy_snapshots_pass_zero_findings(self) -> None:
        for sid in ("yahoo_healthy_01", "gvid_healthy_01", "aiov_healthy_01"):
            snap = self.snaps[sid]
            res = validate_serp_snapshot(snap["html"], self.specs[snap["engine"]], sid)
            self.assertTrue(res.healthy, f"Expected {sid} to be healthy, got {res.findings}")
            self.assertGreaterEqual(res.items_parsed, 2)

    def test_catches_yahoo_4596_snippet_equals_displayed_link(self) -> None:
        snap = self.snaps["yahoo_drifted_4596"]
        res = validate_serp_snapshot(snap["html"], self.specs[snap["engine"]], snap["snapshot_id"])
        self.assertFalse(res.healthy)
        codes = [f.code for f in res.findings]
        self.assertIn("SNIPPET_EQUALS_DISPLAYED_LINK", codes)

    def test_catches_google_videos_light_4556_opaque_caes_tokens(self) -> None:
        snap = self.snaps["gvid_drifted_4556"]
        res = validate_serp_snapshot(snap["html"], self.specs[snap["engine"]], snap["snapshot_id"])
        self.assertFalse(res.healthy)
        codes = [f.code for f in res.findings]
        self.assertIn("OPAQUE_REDIRECT_TOKEN", codes)

    def test_catches_ai_overview_4550_relative_goto_links(self) -> None:
        snap = self.snaps["aiov_drifted_4550"]
        res = validate_serp_snapshot(snap["html"], self.specs[snap["engine"]], snap["snapshot_id"])
        self.assertFalse(res.healthy)
        codes = [f.code for f in res.findings]
        self.assertIn("RELATIVE_GOTO_LINK", codes)

    def test_catches_short_videos_4554_verify_wall_false_200(self) -> None:
        snap = self.snaps["gshort_wall_4554"]
        res = validate_serp_snapshot(snap["html"], self.specs[snap["engine"]], snap["snapshot_id"])
        self.assertFalse(res.healthy)
        codes = [f.code for f in res.findings]
        self.assertIn("VERIFY_WALL_FALSE_200", codes)


if __name__ == "__main__":
    unittest.main()
