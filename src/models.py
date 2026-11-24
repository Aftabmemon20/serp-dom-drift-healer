"""Pydantic data contracts for serpapi-dom-healer."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """Cross-compatible serializer supporting Pydantic v1 (.dict) and v2 (.model_dump)."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class SelectorSpec(BaseModel):
    engine: str
    item_selector: str
    title_selector: str
    link_selector: str
    displayed_link_selector: Optional[str] = None
    snippet_selector: str
    version: str = "v1"


class ParsedItem(BaseModel):
    position: int
    title: str
    link: str
    displayed_link: str = ""
    snippet: str = ""


class RegressionFinding(BaseModel):
    code: Literal[
        "RELATIVE_GOTO_LINK",
        "OPAQUE_REDIRECT_TOKEN",
        "SNIPPET_EQUALS_DISPLAYED_LINK",
        "VERIFY_WALL_FALSE_200",
        "EMPTY_RESULTS",
        "MISSING_FIELD",
    ]
    severity: Literal["high", "critical"]
    field_path: str
    sample_value: str
    affected_ratio: float = Field(ge=0.0, le=1.0)
    message: str


class ValidationResult(BaseModel):
    engine: str
    snapshot_id: str
    http_status: int = 200
    items_parsed: int
    healthy: bool
    findings: List[RegressionFinding] = Field(default_factory=list)
    parsed_items: List[ParsedItem] = Field(default_factory=list)


class DuplicateIssue(BaseModel):
    number: int
    title: str
    url: str
    state: str
    similarity_reason: str


class HealAttempt(BaseModel):
    attempt: int
    provider_used: str
    proposed_selectors: SelectorSpec
    validation_passed: bool
    remaining_findings: List[str] = Field(default_factory=list)
    decision: Literal["KEEP", "REVERT", "ESCALATE_HUMAN"]
    rationale: str


class HealReport(BaseModel):
    engine: str
    snapshot_id: str
    initial_findings: List[RegressionFinding]
    status: Literal[
        "healthy_no_heal_needed",
        "healed_awaiting_human_approval",
        "quarantined_needs_engineer",
    ]
    attempts: List[HealAttempt] = Field(default_factory=list)
    winning_selectors: Optional[SelectorSpec] = None
    duplicate_issues: List[DuplicateIssue] = Field(default_factory=list)
    draft_bug_report_md: str = ""
    human_approval_required: bool = True
    estimated_tokens: int = 0
