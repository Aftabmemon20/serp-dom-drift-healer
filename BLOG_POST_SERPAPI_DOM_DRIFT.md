# Catching Silent HTTP 200 Parser Regressions in Search APIs (Without Burning LLM Tokens on Every Scrape)

When you maintain parsers across 50+ live search engines—as [SerpApi](https://serpapi.com/) does across Google, Yahoo, YouTube, and Shopping—your hardest failures are rarely HTTP `500`s. Standard uptime monitors catch `500`s in seconds. The bugs that quietly break customer pipelines are **silent `200 OK` parser regressions**.

Looking through [`serpapi/public-roadmap`](https://github.com/serpapi/public-roadmap/issues/4550) in November 2026, four real failure patterns stand out immediately:
1. **Relative `/goto` links** leaking into `references[].link` on Google AI Overview ([`#4550`](https://github.com/serpapi/public-roadmap/issues/4550)) and Google AI Mode ([`#4606`](https://github.com/serpapi/public-roadmap/issues/4606)).
2. **Opaque `CAES...` redirect tokens** replacing destination URLs in `video_results[].link` on Google Videos Light ([`#4556`](https://github.com/serpapi/public-roadmap/issues/4556)).
3. **`displayed_link` duplicated into `snippet`** on Yahoo Search when the description container class shifts ([`#4596`](https://github.com/serpapi/public-roadmap/issues/4596)).
4. **False-success `"Fully empty"` walls** when Google serves a `"Verifying your request"` interstitial with HTTP `200 OK` ([`#4554`](https://github.com/serpapi/public-roadmap/issues/4554)).

## Why Naive "AI Scraping" Is the Wrong Architecture
A tempting reaction in 2026 is: *"Just pass the raw HTML to an LLM to extract JSON."* That fails in production for three reasons: latency (seconds instead of milliseconds), token cost across millions of searches, and non-deterministic hallucinations.

Instead, **`serpapi-dom-healer`** separates **fast deterministic detection** from **bounded agentic repair**:

1. **Zero-LLM Fast Path (`src/parser.py`):** Every SERP snapshot is parsed with standard CSS selectors (`BeautifulSoup`) and validated against strict deterministic contracts (`link.startswith("http")`, no `/goto` prefix, no `CAES...` redirect regex, `snippet != displayed_link`, and interstitial wall detection). Healthy pages cost **0 LLM tokens**.
2. **Fail-Fast Escalation on Non-DOM Failures:** If the validator detects a `"Verifying your request"` interstitial (`VERIFY_WALL_FALSE_200`), the pipeline **immediately escalates** to human/proxy triage instead of wasting LLM calls trying to CSS-heal a CAPTCHA wall.
3. **Bounded Keep-or-Revert Selector Repair (`src/healer.py`):** Only when a genuine DOM drift occurs does the bounded agent trigger (max 2 attempts via a thin provider interface: Groq `openai/gpt-oss-120b` -> Gemini `2.5 Flash` -> structural DOM fallback). Every candidate CSS selector is re-tested against the deterministic validator; a patch is marked **`KEEP`** only if all contracts pass with `items_parsed >= initial_items_parsed`.
4. **GitHub Duplicate Triage + Human Approval Gate (`src/github_triage.py`):** Before anyone opens another ticket across 960+ roadmap issues, the agent checks `serpapi/public-roadmap` for matching open issues and drafts a reproducible Markdown bug/PR report waiting for an engineer's approval.

## Results & Honest Limitations
- Across 7 Dev snapshots (Yahoo, Google Videos Light, AI Overview, Short Videos) and 4 unseen Held-Out engines (Bing, DuckDuckGo, YouTube Channel, Google News), the deterministic validator + bounded healer passes **7/7 Dev** and **4/4 Held-Out** with **0/3 false alarms** on healthy pages.
- **Limitations:** These fixtures are compact synthetic reproductions of real `public-roadmap` DOM drift, not full multi-megabyte Google SERP dumps; production deployment would pair this with live proxy rotation, Ruby/Nokogiri selector compilation, and a Postgres-backed human review queue.
