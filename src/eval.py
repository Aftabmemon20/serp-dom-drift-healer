"""Dev vs. Unseen Held-Out evaluation harness for serpapi-dom-healer."""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List
from src.healer import heal_serp_parser
from src.models import SelectorSpec

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "serp_snapshots.json"
EVAL_SUMMARY_PATH = Path(__file__).resolve().parent.parent / "data" / "eval_summary.json"


def evaluate_all_splits() -> Dict[str, Any]:
    raw = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    specs = {k: SelectorSpec(**v) for k, v in raw["specs"].items()}
    summary: Dict[str, Any] = {}

    for split in ("dev", "heldout"):
        subset = [s for s in raw["snapshots"] if s["split"] == split]
        correct = 0
        healed_ok = 0
        healable_total = 0
        escalated_ok = 0
        wall_total = 0
        false_alarms = 0
        healthy_total = 0
        providers = Counter()
        rows: List[Dict[str, Any]] = []

        for snap in subset:
            report = heal_serp_parser(
                html=snap["html"],
                spec=specs[snap["engine"]],
                snapshot_id=snap["snapshot_id"],
                use_live_github=False,
            )
            for a in report.attempts:
                providers[a.provider_used] += 1

            exp_healthy = snap["expected_healthy"]
            exp_healable = snap["expected_healable"]

            if exp_healthy:
                healthy_total += 1
                is_ok = report.status == "healthy_no_heal_needed"
                if not is_ok:
                    false_alarms += 1
            elif exp_healable:
                healable_total += 1
                is_ok = report.status == "healed_awaiting_human_approval"
                if is_ok:
                    healed_ok += 1
            else:
                wall_total += 1
                is_ok = report.status == "quarantined_needs_engineer"
                if is_ok:
                    escalated_ok += 1

            if is_ok:
                correct += 1

            rows.append(
                {
                    "snapshot_id": snap["snapshot_id"],
                    "engine": snap["engine"],
                    "roadmap_ref": snap["roadmap_ref"],
                    "status": report.status,
                    "correct": is_ok,
                    "attempts": len(report.attempts),
                    "duplicates_found": [d.number for d in report.duplicate_issues],
                    "estimated_tokens": report.estimated_tokens,
                }
            )

        summary[split] = {
            "total_cases": len(subset),
            "exact_triage_passed": f"{correct}/{len(subset)}",
            "healable_repaired": f"{healed_ok}/{healable_total}",
            "non_healable_escalated": f"{escalated_ok}/{wall_total}",
            "false_alarms": f"{false_alarms}/{healthy_total}",
            "provider_breakdown": dict(providers),
            "cases": rows,
        }

    EVAL_SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    out = evaluate_all_splits()
    for sp, metrics in out.items():
        print(
            f"[{sp.upper()}] Passed={metrics['exact_triage_passed']} | "
            f"Healed={metrics['healable_repaired']} | Escalated={metrics['non_healable_escalated']} | "
            f"FalseAlarms={metrics['false_alarms']} | Providers={metrics['provider_breakdown']}"
        )
