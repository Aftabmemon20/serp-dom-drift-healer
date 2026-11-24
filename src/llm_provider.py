"""Thin LLM provider interface (Groq openai/gpt-oss-120b -> Gemini 2.5 Flash -> Deterministic DOM Analyzer)."""

import json
import os
import re
from typing import List, Tuple
import httpx
from bs4 import BeautifulSoup
from src.models import RegressionFinding, SelectorSpec, model_to_dict


def _deterministic_dom_repair(
    html: str,
    broken_spec: SelectorSpec,
    findings: List[RegressionFinding],
) -> Tuple[SelectorSpec, str, str, int]:
    """
    Zero-cost structural DOM analyzer fallback when no LLM API key is configured
    or a free-tier provider hits rate limits. Inspects the first matched item subtree
    to find clean replacement selectors for broken links or duplicated snippets.
    """
    soup = BeautifulSoup(html, "html.parser")
    sample_item = soup.select_one(broken_spec.item_selector)
    new_data = model_to_dict(broken_spec)
    new_data["version"] = f"{broken_spec.version}_healed"
    reasons: List[str] = []

    if sample_item is None:
        return (
            SelectorSpec(**new_data),
            "deterministic_dom_analyzer",
            "Item container selector matched 0 nodes; cannot repair structurally.",
            120,
        )

    finding_codes = {f.code for f in findings}

    # Repair broken link selector (/goto or opaque CAES... redirect tokens)
    if "RELATIVE_GOTO_LINK" in finding_codes or "OPAQUE_REDIRECT_TOKEN" in finding_codes:
        for anchor in sample_item.select("a[href]"):
            href = str(anchor.get("href", "")).strip()
            if href.startswith("https://") and "/url?" not in href and "CAES" not in href:
                classes = anchor.get("class") or []
                if classes:
                    new_sel = f"a.{classes[0]}"
                    new_data["link_selector"] = new_sel
                    reasons.append(
                        f"Switched link_selector from '{broken_spec.link_selector}' to '{new_sel}' "
                        f"(holds clean https:// destination URL)."
                    )
                    break

    # Repair snippet selector when snippet == displayed_link (#4596)
    if "SNIPPET_EQUALS_DISPLAYED_LINK" in finding_codes:
        disp_el = (
            sample_item.select_one(broken_spec.displayed_link_selector)
            if broken_spec.displayed_link_selector
            else None
        )
        disp_text = disp_el.get_text(" ", strip=True).lower() if disp_el else ""
        for cand in sample_item.select("p, span, div"):
            if cand.find(["p", "span", "div", "a", "h2", "h3", "h4"]):
                continue
            txt = cand.get_text(" ", strip=True)
            if len(txt) >= 25 and txt.lower() != disp_text and "http" not in txt.lower():
                classes = cand.get("class") or []
                if classes:
                    new_sel = f"{cand.name}.{classes[0]}"
                    new_data["snippet_selector"] = new_sel
                    reasons.append(
                        f"Switched snippet_selector from '{broken_spec.snippet_selector}' to '{new_sel}' "
                        f"(contains full description text instead of displayed_link)."
                    )
                    break

    rationale = " ".join(reasons) if reasons else "No cleaner sibling selector found in DOM."
    est_tokens = max(1, len(html[:1500]) // 4)
    return SelectorSpec(**new_data), "deterministic_dom_analyzer", rationale, est_tokens


def propose_selector_patch(
    html: str,
    broken_spec: SelectorSpec,
    findings: List[RegressionFinding],
    previous_feedback: str = "",
) -> Tuple[SelectorSpec, str, str, int]:
    """
    Thin Provider Interface:
    1. Tries Groq (`openai/gpt-oss-120b` via GROQ_API_KEY)
    2. Falls back to Gemini (`gemini-2.5-flash` via GEMINI_API_KEY)
    3. Falls back to deterministic structural DOM analyzer (`deterministic_dom_analyzer`)
    """
    soup = BeautifulSoup(html, "html.parser")
    first_item = soup.select_one(broken_spec.item_selector)
    excerpt = str(first_item)[:1800] if first_item else html[:1800]

    findings_summary = "\n".join(
        f"- [{f.code}] {f.message} (sample: {f.sample_value})" for f in findings
    )
    system_prompt = (
        "You are a SERP HTML Parser Engineer. Given a broken SelectorSpec, regression findings, "
        "and a sample HTML item subtree, return strict JSON with updated CSS selectors that fix "
        "the broken field while keeping all other fields intact.\n"
        'Return JSON ONLY: {"title_selector": "...", "link_selector": "...", '
        '"displayed_link_selector": null or "...", "snippet_selector": "...", "rationale": "..."}'
    )
    user_prompt = (
        f"CURRENT SPEC:\n{json.dumps(model_to_dict(broken_spec), indent=2)}\n\n"
        f"REGRESSION FINDINGS:\n{findings_summary}\n\n"
        f"PREVIOUS RETRY FEEDBACK:\n{previous_feedback or 'None'}\n\n"
        f"SAMPLE ITEM HTML:\n{excerpt}"
    )

    # Provider 1: Groq (Free Tier)
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        try:
            groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": groq_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.0,
                    },
                )
                if resp.status_code == 200:
                    payload = resp.json()
                    parsed = json.loads(payload["choices"][0]["message"]["content"])
                    merged = model_to_dict(broken_spec)
                    for key in ("title_selector", "link_selector", "displayed_link_selector", "snippet_selector"):
                        if key in parsed and parsed[key] is not None:
                            merged[key] = str(parsed[key])
                    merged["version"] = f"{broken_spec.version}_groq_healed"
                    tokens = int(payload.get("usage", {}).get("total_tokens", 350))
                    return (
                        SelectorSpec(**merged),
                        f"groq:{groq_model}",
                        str(parsed.get("rationale", "Proposed by Groq LLM.")),
                        tokens,
                    )
        except Exception as exc:
            print(f"[Groq Provider Fallback] {exc}")

    # Provider 2: Gemini (Free Tier)
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                    json={
                        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
                        "generationConfig": {"responseMimeType": "application/json"},
                    },
                )
                if resp.status_code == 200:
                    payload = resp.json()
                    raw = payload["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw)
                    merged = model_to_dict(broken_spec)
                    for key in ("title_selector", "link_selector", "displayed_link_selector", "snippet_selector"):
                        if key in parsed and parsed[key] is not None:
                            merged[key] = str(parsed[key])
                    merged["version"] = f"{broken_spec.version}_gemini_healed"
                    tokens = int(payload.get("usageMetadata", {}).get("totalTokenCount", 350))
                    return (
                        SelectorSpec(**merged),
                        "gemini:gemini-2.5-flash",
                        str(parsed.get("rationale", "Proposed by Gemini 2.5 Flash.")),
                        tokens,
                    )
        except Exception as exc:
            print(f"[Gemini Provider Fallback] {exc}")

    # Provider 3: Deterministic Structural DOM Analyzer (Zero Cost Offline Fallback)
    return _deterministic_dom_repair(html, broken_spec, findings)
