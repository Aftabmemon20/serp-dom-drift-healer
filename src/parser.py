"""Deterministic SERP DOM parser and Silent-200 Regression Contract Validator (zero LLM cost)."""

import re
from typing import List
from bs4 import BeautifulSoup
from src.models import ParsedItem, RegressionFinding, SelectorSpec, ValidationResult

VERIFY_WALL_PATTERNS = [
    "verifying your request",
    "unusual traffic from your computer network",
    "confirm you are human",
    "captcha-form",
]

OPAQUE_TOKEN_RE = re.compile(r"(?:/url\?.*[?&]q=CAES|^CAES[A-Za-z0-9_-]{8,})")


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_serp_html(html: str, spec: SelectorSpec) -> List[ParsedItem]:
    """Parses SERP items deterministically using BeautifulSoup CSS selectors."""
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select(spec.item_selector)
    items: List[ParsedItem] = []

    for idx, node in enumerate(nodes, start=1):
        title_el = node.select_one(spec.title_selector)
        link_el = node.select_one(spec.link_selector)
        disp_el = (
            node.select_one(spec.displayed_link_selector)
            if spec.displayed_link_selector
            else None
        )
        snip_el = node.select_one(spec.snippet_selector)

        title = normalize_ws(title_el.get_text(" ")) if title_el else ""
        link = ""
        if link_el:
            link = normalize_ws(str(link_el.get("href", "")))
        displayed_link = normalize_ws(disp_el.get_text(" ")) if disp_el else ""
        snippet = normalize_ws(snip_el.get_text(" ")) if snip_el else ""

        items.append(
            ParsedItem(
                position=idx,
                title=title,
                link=link,
                displayed_link=displayed_link,
                snippet=snippet,
            )
        )
    return items


def validate_serp_snapshot(
    html: str,
    spec: SelectorSpec,
    snapshot_id: str,
    http_status: int = 200,
) -> ValidationResult:
    """
    Runs zero-LLM deterministic contract assertions on a SERP HTML snapshot to catch
    silent HTTP 200 OK parser regressions modeled on real serpapi/public-roadmap bugs.
    """
    findings: List[RegressionFinding] = []
    lower_html = html.lower()

    # Check 1: False-200 Verification / CAPTCHA interstitial wall (#4554)
    wall_hit = next((pat for pat in VERIFY_WALL_PATTERNS if pat in lower_html), None)
    items = parse_serp_html(html, spec)

    if wall_hit and len(items) == 0:
        findings.append(
            RegressionFinding(
                code="VERIFY_WALL_FALSE_200",
                severity="critical",
                field_path="search_information.results_state",
                sample_value=wall_hit,
                affected_ratio=1.0,
                message=(
                    f"Silent 200 OK interstitial detected ('{wall_hit}') with 0 parsed items. "
                    "Do not mark as healthy empty results; retry via proxy rotation."
                ),
            )
        )
        return ValidationResult(
            engine=spec.engine,
            snapshot_id=snapshot_id,
            http_status=http_status,
            items_parsed=0,
            healthy=False,
            findings=findings,
            parsed_items=[],
        )

    if not items:
        findings.append(
            RegressionFinding(
                code="EMPTY_RESULTS",
                severity="critical",
                field_path="organic_results",
                sample_value=spec.item_selector,
                affected_ratio=1.0,
                message=f"Selector '{spec.item_selector}' matched 0 items on HTTP {http_status} page.",
            )
        )
        return ValidationResult(
            engine=spec.engine,
            snapshot_id=snapshot_id,
            http_status=http_status,
            items_parsed=0,
            healthy=False,
            findings=findings,
            parsed_items=[],
        )

    total = len(items)

    # Check 2: Relative /goto links (#4550, #4606)
    goto_bad = [it for it in items if it.link.startswith("/goto")]
    if goto_bad:
        findings.append(
            RegressionFinding(
                code="RELATIVE_GOTO_LINK",
                severity="high",
                field_path="results[].link",
                sample_value=goto_bad[0].link,
                affected_ratio=round(len(goto_bad) / total, 4),
                message=(
                    f"{len(goto_bad)}/{total} items returned relative '/goto' links instead of "
                    f"absolute https:// destination URLs (selector: '{spec.link_selector}')."
                ),
            )
        )

    # Check 3: Opaque CAES... redirect tokens (#4556)
    opaque_bad = [it for it in items if OPAQUE_TOKEN_RE.search(it.link)]
    if opaque_bad:
        findings.append(
            RegressionFinding(
                code="OPAQUE_REDIRECT_TOKEN",
                severity="high",
                field_path="results[].link",
                sample_value=opaque_bad[0].link,
                affected_ratio=round(len(opaque_bad) / total, 4),
                message=(
                    f"{len(opaque_bad)}/{total} items returned opaque CAES... redirect tokens "
                    f"instead of destination URLs (selector: '{spec.link_selector}')."
                ),
            )
        )

    # Check 4: Snippet equals displayed_link (#4596)
    dup_snip_bad = [
        it
        for it in items
        if it.displayed_link
        and it.snippet
        and it.snippet.lower() == it.displayed_link.lower()
    ]
    if dup_snip_bad:
        findings.append(
            RegressionFinding(
                code="SNIPPET_EQUALS_DISPLAYED_LINK",
                severity="high",
                field_path="organic_results[].snippet",
                sample_value=dup_snip_bad[0].snippet,
                affected_ratio=round(len(dup_snip_bad) / total, 4),
                message=(
                    f"{len(dup_snip_bad)}/{total} items returned displayed_link as snippet "
                    f"instead of description text (selector: '{spec.snippet_selector}')."
                ),
            )
        )

    # Check 5: Missing critical fields (title, absolute link, or snippet)
    missing_bad = [
        it
        for it in items
        if (not it.title) or (not it.link.startswith("http")) or (len(it.snippet) < 12)
    ]
    if missing_bad and not (goto_bad or opaque_bad or dup_snip_bad):
        findings.append(
            RegressionFinding(
                code="MISSING_FIELD",
                severity="high",
                field_path="results[]",
                sample_value=f"title={missing_bad[0].title!r}, link={missing_bad[0].link!r}",
                affected_ratio=round(len(missing_bad) / total, 4),
                message=f"{len(missing_bad)}/{total} items missing valid title, https link, or snippet.",
            )
        )

    return ValidationResult(
        engine=spec.engine,
        snapshot_id=snapshot_id,
        http_status=http_status,
        items_parsed=total,
        healthy=len(findings) == 0,
        findings=findings,
        parsed_items=items,
    )
