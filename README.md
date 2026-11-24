# `serp-dom-drift-healer` — Silent-200 SERP Regression Sentinel & Bounded CSS Selector Healer

Built as a targeted proof-of-work project for **SerpApi's [Junior Fullstack Engineer](https://serpapi.com/careers/junior-fullstack-engineer)** role ([HN Nov 2026 Thread](https://news.ycombinator.com/item?id=50342697)), modeling real November 2026 parser issues from [`serpapi/public-roadmap`](https://github.com/serpapi/public-roadmap/issues/4550).

> *Independent, unofficial proof-of-work prototype modeled on public GitHub issues. Not affiliated with, endorsed by, or sponsored by SerpApi.*

---

## 1. Architecture (Workflow-First, Agent-Second)

1. **Deterministic DOM Parser & Silent-200 Validator (`src/parser.py` — 0 LLM tokens):**
   - Catches 4 real `serpapi/public-roadmap` silent `200 OK` regression classes:
     - `SNIPPET_EQUALS_DISPLAYED_LINK` ([`#4596`](https://github.com/serpapi/public-roadmap/issues/4596) Yahoo Search)
     - `OPAQUE_REDIRECT_TOKEN` ([`#4556`](https://github.com/serpapi/public-roadmap/issues/4556) Google Videos Light `CAES...` tokens)
     - `RELATIVE_GOTO_LINK` ([`#4550`](https://github.com/serpapi/public-roadmap/issues/4550) & [`#4606`](https://github.com/serpapi/public-roadmap/issues/4606) Google AI Overview / AI Mode `/goto` links)
     - `VERIFY_WALL_FALSE_200` ([`#4554`](https://github.com/serpapi/public-roadmap/issues/4554) Google Short Videos `"Verifying your request"` false-empty responses)
2. **Bounded Keep-or-Revert CSS Selector Healer (`src/healer.py` + `src/llm_provider.py`):**
   - Healthy pages exit immediately (`0` LLM calls).
   - Interstitial/CAPTCHA walls (`VERIFY_WALL_FALSE_200`) escalate immediately to human/proxy triage without wasting LLM tokens.
   - Genuine DOM drift runs a bounded repair loop (`max_attempts=2`) via a thin provider interface (**Groq `openai/gpt-oss-120b`** -> **Gemini `2.5 Flash`** -> **Deterministic Structural DOM Analyzer**). Every candidate selector is re-tested deterministically and stops at a **Human Approval Gate**.
3. **GitHub Public-Roadmap Duplicate Triage (`src/github_triage.py`):**
   - Checks `serpapi/public-roadmap` for existing open issues (supports live public GitHub API search) and drafts a reproducible Markdown bug/PR report.
4. **FastAPI + Vanilla JS UI (`src/api.py`, `static/index.html`):**
   - Plain HTTP/REST UI served directly on `http://127.0.0.1:8000` (zero WebSocket fragility).
5. **Technical Write-Up (`BLOG_POST_SERPAPI_DOM_DRIFT.md`):**
   - Included 600-word architecture breakdown covering silent `200 OK` parser regressions, deterministic-first validation, and bounded selector healing.

---

## 2. Verified Eval Results (`7 Dev` vs. `4 Unseen Held-Out` Snapshots)

| Split | Engines Tested | Exact Triage Passed | Healable Repaired | Verify Walls Escalated | False Alarms |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Dev (`7` cases)** | Yahoo, Google Videos Light, AI Overview, Short Videos | **7/7** | **3/3** | **1/1** | **0/3** |
| **Unseen Held-Out (`4` cases)** | Bing Organic, DuckDuckGo Shopping, YouTube Channel, Google News | **4/4** | **3/3** | **1/1** | **0/0** |

---

## 3. Limitations & Production Roadmap
- **Compact synthetic HTML fixtures:** Snapshots reproduce real `public-roadmap` failure modes cleanly for deterministic CI testing, not full multi-megabyte obfuscated Google SERP dumps.
- **No live proxy rotation / CAPTCHA solver:** Interstitial walls are detected and escalated cleanly, not bypassed.
- **Stack scope:** Built in Python (FastAPI/BeautifulSoup) + Vanilla JavaScript; in SerpApi's production stack, the deterministic selector layer would target Ruby/Nokogiri + MongoDB + async background workers.

---

## 4. Quickstart

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Run all 14 unit tests (passes out-of-the-box with zero API keys)
python -m unittest discover -s tests -v

# Run Dev + Unseen Held-Out evaluation harness
python -m src.eval

# Launch FastAPI + Interactive JS Dashboard on http://127.0.0.1:8000
uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```
