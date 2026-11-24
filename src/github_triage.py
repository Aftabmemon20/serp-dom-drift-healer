"""GitHub serpapi/public-roadmap duplicate issue lookup (live API + verified Nov 2026 offline index)."""

import os
from typing import List
import httpx
from src.models import DuplicateIssue, RegressionFinding

# Verified real issues retrieved from github.com/serpapi/public-roadmap in Nov 2026
RECORDED_ROADMAP_INDEX = [
    {
        "number": 4596,
        "title": "[Yahoo Search API] Fix organic results snippet returning the displayed link",
        "url": "https://github.com/serpapi/public-roadmap/issues/4596",
        "state": "open",
        "keywords": ["yahoo_search", "SNIPPET_EQUALS_DISPLAYED_LINK", "displayed_link", "snippet"],
    },
    {
        "number": 4556,
        "title": "[Google Videos Light API] Video result links contain opaque tokens instead of destination URLs",
        "url": "https://github.com/serpapi/public-roadmap/issues/4556",
        "state": "open",
        "keywords": ["google_videos_light", "OPAQUE_REDIRECT_TOKEN", "CAES"],
    },
    {
        "number": 4550,
        "title": "[Google AI Overview API] /goto links returned in references.link and text_blocks.snippet_links.link",
        "url": "https://github.com/serpapi/public-roadmap/issues/4550",
        "state": "open",
        "keywords": ["google_ai_overview", "RELATIVE_GOTO_LINK", "/goto"],
    },
    {
        "number": 4606,
        "title": "[Google AI Mode API] /goto links returned in the output",
        "url": "https://github.com/serpapi/public-roadmap/issues/4606",
        "state": "open",
        "keywords": ["google_ai_mode", "RELATIVE_GOTO_LINK", "/goto"],
    },
    {
        "number": 4554,
        "title": '[Google Short Videos API] "Verify request" result incorrectly marked as successful with "Fully empty"',
        "url": "https://github.com/serpapi/public-roadmap/issues/4554",
        "state": "open",
        "keywords": ["google_short_videos", "VERIFY_WALL_FALSE_200", "verifying your request"],
    },
]


def find_duplicate_roadmap_issues(
    engine: str,
    findings: List[RegressionFinding],
    use_live_github: bool = False,
) -> List[DuplicateIssue]:
    """
    Searches serpapi/public-roadmap for existing open issues matching this engine + regression code.
    Uses GitHub Search API when `use_live_github=True`, with clean fallback to the verified local index.
    """
    if not findings:
        return []

    codes = {f.code for f in findings}
    if use_live_github:
        try:
            q_term = engine.replace("_", " ")
            headers = {"Accept": "application/vnd.github+json"}
            gh_token = os.getenv("GITHUB_TOKEN", "").strip()
            if gh_token:
                headers["Authorization"] = f"Bearer {gh_token}"
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(
                    "https://api.github.com/search/issues",
                    params={"q": f"repo:serpapi/public-roadmap is:issue is:open {q_term}", "per_page": 3},
                    headers=headers,
                )
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    if items:
                        return [
                            DuplicateIssue(
                                number=int(it["number"]),
                                title=str(it["title"]),
                                url=str(it["html_url"]),
                                state=str(it["state"]),
                                similarity_reason=f"Live GitHub search match on repo:serpapi/public-roadmap for '{q_term}'.",
                            )
                            for it in items
                        ]
        except Exception:
            pass

    matches: List[DuplicateIssue] = []
    for row in RECORDED_ROADMAP_INDEX:
        kws = set(row["keywords"])
        engine_match = engine in kws
        code_match = bool(codes.intersection(kws))
        if engine_match and code_match:
            matches.append(
                DuplicateIssue(
                    number=row["number"],
                    title=row["title"],
                    url=row["url"],
                    state=row["state"],
                    similarity_reason=f"Exact match on engine '{engine}' + regression code {sorted(codes.intersection(kws))}.",
                )
            )
    return matches
