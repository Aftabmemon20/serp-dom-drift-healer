"""Bounded Agentic CSS-Selector Healer with Keep-or-Revert test gate & Human Approval stop."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from src.github_triage import find_duplicate_roadmap_issues
from src.llm_provider import propose_selector_patch
from src.models import HealAttempt, HealReport, SelectorSpec, model_to_dict
from src.parser import validate_serp_snapshot

TRACE_PATH = Path(__file__).resolve().parent.parent / "data" / "heal_traces.jsonl"


def _log_trace(report: HealReport) -> None:
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine": report.engine,
        "snapshot_id": report.snapshot_id,
        "status": report.status,
        "attempts": len(report.attempts),
        "estimated_tokens": report.estimated_tokens,
        "duplicate_issue_numbers": [d.number for d in report.duplicate_issues],
    }
    with TRACE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _draft_bug_report(report: HealReport, broken_spec: SelectorSpec) -> str:
    findings_md = "\n".join(
        f"- **`{f.code}`** (`{f.field_path}`, affected `{f.affected_ratio*100:.0f}%`): {f.message} (sample: `{f.sample_value}`)"
        for f in report.initial_findings
    )
    dups_md = (
        "\n".join(f"- [#{d.number}]({d.url}) — {d.title} ({d.similarity_reason})" for d in report.duplicate_issues)
        if report.duplicate_issues
        else "- None found on `serpapi/public-roadmap` (candidate new regression)."
    )
    patch_md = (
        f"```json\n{json.dumps(model_to_dict(report.winning_selectors), indent=2)}\n```"
        if report.winning_selectors
        else "_No CSS patch accepted — requires proxy/anti-bot or manual parser investigation._"
    )
    return (
        f"## [{report.engine}] Silent 200 OK Parser Regression (`{report.snapshot_id}`)\n\n"
        f"### Detected Regressions\n{findings_md}\n\n"
        f"### Possible Duplicate Public-Roadmap Issues\n{dups_md}\n\n"
        f"### Verified Candidate Selector Patch (`status: {report.status}`)\n{patch_md}\n\n"
        f"> **Human Approval Required:** Review the candidate selector diff before merging or posting to GitHub."
    )


def heal_serp_parser(
    html: str,
    spec: SelectorSpec,
    snapshot_id: str,
    max_attempts: int = 2,
    use_live_github: bool = False,
) -> HealReport:
    """
    Workflow-First, Agent-Second Bounded Healer:
    1. Validate deterministically (0 tokens). If healthy, return immediately.
    2. Check GitHub serpapi/public-roadmap for duplicate open issues.
    3. If VERIFY_WALL_FALSE_200 -> immediately quarantine/escalate (CSS cannot fix CAPTCHA walls).
    4. Otherwise run bounded selector-repair loop (max 2 attempts), re-validating every candidate
       against deterministic contracts (Keep-or-Revert gate) and stopping at human approval.
    """
    initial = validate_serp_snapshot(html=html, spec=spec, snapshot_id=snapshot_id)
    if initial.healthy:
        report = HealReport(
            engine=spec.engine,
            snapshot_id=snapshot_id,
            initial_findings=[],
            status="healthy_no_heal_needed",
            winning_selectors=spec,
            human_approval_required=False,
            estimated_tokens=0,
        )
        _log_trace(report)
        return report

    duplicates = find_duplicate_roadmap_issues(
        engine=spec.engine, findings=initial.findings, use_live_github=use_live_github
    )

    # Guardrail: Never waste LLM tokens trying to CSS-heal a CAPTCHA / Verify Wall
    if any(f.code == "VERIFY_WALL_FALSE_200" for f in initial.findings):
        report = HealReport(
            engine=spec.engine,
            snapshot_id=snapshot_id,
            initial_findings=initial.findings,
            status="quarantined_needs_engineer",
            attempts=[
                HealAttempt(
                    attempt=1,
                    provider_used="deterministic_guardrail",
                    proposed_selectors=spec,
                    validation_passed=False,
                    remaining_findings=["VERIFY_WALL_FALSE_200"],
                    decision="ESCALATE_HUMAN",
                    rationale="Interstitial CAPTCHA/verify wall cannot be fixed by CSS selector repair; escalate to proxy/retry layer.",
                )
            ],
            duplicate_issues=duplicates,
            human_approval_required=True,
            estimated_tokens=0,
        )
        report.draft_bug_report_md = _draft_bug_report(report, spec)
        _log_trace(report)
        return report

    attempts: List[HealAttempt] = []
    total_tokens = 0
    prev_feedback = ""
    winning_spec: Optional[SelectorSpec] = None

    for attempt_num in range(1, max_attempts + 1):
        cand_spec, provider, rationale, tokens = propose_selector_patch(
            html=html,
            broken_spec=spec,
            findings=initial.findings,
            previous_feedback=prev_feedback,
        )
        total_tokens += tokens

        recheck = validate_serp_snapshot(html=html, spec=cand_spec, snapshot_id=snapshot_id)
        passed = recheck.healthy and (recheck.items_parsed >= initial.items_parsed)
        remaining = [f.code for f in recheck.findings]

        if passed:
            attempts.append(
                HealAttempt(
                    attempt=attempt_num,
                    provider_used=provider,
                    proposed_selectors=cand_spec,
                    validation_passed=True,
                    remaining_findings=[],
                    decision="KEEP",
                    rationale=rationale,
                )
            )
            winning_spec = cand_spec
            break
        else:
            attempts.append(
                HealAttempt(
                    attempt=attempt_num,
                    provider_used=provider,
                    proposed_selectors=cand_spec,
                    validation_passed=False,
                    remaining_findings=remaining,
                    decision="REVERT" if attempt_num < max_attempts else "ESCALATE_HUMAN",
                    rationale=rationale,
                )
            )
            prev_feedback = f"Candidate failed validation with remaining findings: {remaining}"

    status = (
        "healed_awaiting_human_approval"
        if winning_spec is not None
        else "quarantined_needs_engineer"
    )
    report = HealReport(
        engine=spec.engine,
        snapshot_id=snapshot_id,
        initial_findings=initial.findings,
        status=status,
        attempts=attempts,
        winning_selectors=winning_spec,
        duplicate_issues=duplicates,
        human_approval_required=True,
        estimated_tokens=total_tokens,
    )
    report.draft_bug_report_md = _draft_bug_report(report, spec)
    _log_trace(report)
    return report
