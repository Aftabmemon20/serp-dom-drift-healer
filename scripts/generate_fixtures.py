"""Generates realistic SERP HTML snapshots reproducing Nov 2026 serpapi/public-roadmap regressions + unseen Held-Out engines."""

import json
from pathlib import Path

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "serp_snapshots.json"


def build_fixtures() -> dict:
    # 1. Yahoo Search (#4596): healthy vs drifted (snippet moved to .fc-falcon while .compText .d-ib holds displayed_link)
    yahoo_healthy_html = """<!doctype html><html><head><title>coffee mug - Yahoo Search</title></head><body>
    <header><nav class="top-nav"><a href="https://yahoo.com">Mail</a><a href="https://news.yahoo.com">News</a></nav></header>
    <main id="web"><ol class="searchCenterMiddle">
      <li class="algo-sr"><div class="dd algo"><div class="compTitle"><h3 class="title"><a class="ac-algo" href="https://www.amazon.com/ceramic-coffee-mug">Insulated Ceramic Coffee Mug 350ml</a></h3><span class="cite-url">www.amazon.com/ceramic-coffee-mug</span></div>
      <div class="compText"><p class="lh-16">Double-walled insulated ceramic coffee mug with spill-proof lid, dishwasher safe for daily office use.</p></div></div></li>
      <li class="algo-sr"><div class="dd algo"><div class="compTitle"><h3 class="title"><a class="ac-algo" href="https://www.target.com/stoneware-mug">Threshold Stoneware Coffee Mug</a></h3><span class="cite-url">www.target.com/stoneware-mug</span></div>
      <div class="compText"><p class="lh-16">Hand-glazed 14oz stoneware mug crafted for hot coffee and tea, microwave and dishwasher friendly.</p></div></div></li>
      <li class="algo-sr"><div class="dd algo"><div class="compTitle"><h3 class="title"><a class="ac-algo" href="https://www.yeti.com/rambler-14oz">YETI Rambler 14 oz Stackable Mug</a></h3><span class="cite-url">www.yeti.com/rambler-14oz</span></div>
      <div class="compText"><p class="lh-16">Kitchen-grade stainless steel vacuum-insulated camp mug built to keep espresso hot on the trail.</p></div></div></li>
    </ol></main><footer>Yahoo Privacy & Terms</footer></body></html>"""

    yahoo_drifted_html = """<!doctype html><html><head><title>coffee mug - Yahoo Search</title></head><body>
    <header><nav class="top-nav"><a href="https://yahoo.com">Mail</a></nav></header>
    <main id="web"><ol class="searchCenterMiddle">
      <li class="algo-sr"><div class="dd algo"><div class="compTitle"><h3 class="title"><a class="ac-algo" href="https://www.amazon.com/ceramic-coffee-mug">Insulated Ceramic Coffee Mug 350ml</a></h3><span class="cite-url">www.amazon.com/ceramic-coffee-mug</span></div>
      <div class="compText"><p class="lh-16">www.amazon.com/ceramic-coffee-mug</p><span class="fc-falcon-desc">Double-walled insulated ceramic coffee mug with spill-proof lid, dishwasher safe for daily office use.</span></div></div></li>
      <li class="algo-sr"><div class="dd algo"><div class="compTitle"><h3 class="title"><a class="ac-algo" href="https://www.target.com/stoneware-mug">Threshold Stoneware Coffee Mug</a></h3><span class="cite-url">www.target.com/stoneware-mug</span></div>
      <div class="compText"><p class="lh-16">www.target.com/stoneware-mug</p><span class="fc-falcon-desc">Hand-glazed 14oz stoneware mug crafted for hot coffee and tea, microwave and dishwasher friendly.</span></div></div></li>
      <li class="algo-sr"><div class="dd algo"><div class="compTitle"><h3 class="title"><a class="ac-algo" href="https://www.yeti.com/rambler-14oz">YETI Rambler 14 oz Stackable Mug</a></h3><span class="cite-url">www.yeti.com/rambler-14oz</span></div>
      <div class="compText"><p class="lh-16">www.yeti.com/rambler-14oz</p><span class="fc-falcon-desc">Kitchen-grade stainless steel vacuum-insulated camp mug built to keep espresso hot on the trail.</span></div></div></li>
    </ol></main></body></html>"""

    # 2. Google Videos Light (#4556): healthy vs drifted (a.vid-link now contains /url?opi=89978449&q=CAES... while canonical URL moved to a.vid-canonical)
    gvid_healthy_html = """<!doctype html><html><body><div id="rso">
      <div class="vid-card"><h3 class="vid-title">Easy 15-Minute Pasta Recipe</h3><a class="vid-link" href="https://www.tiktok.com/@chef/video/741001">Watch on TikTok</a><p class="vid-desc">Quick garlic butter pasta made in one pan in 15 minutes.</p></div>
      <div class="vid-card"><h3 class="vid-title">Crispy Garlic Noodles</h3><a class="vid-link" href="https://www.tiktok.com/@noodles/video/741002">Watch on TikTok</a><p class="vid-desc">Weeknight crispy chili garlic noodles with scallions.</p></div>
      <div class="vid-card"><h3 class="vid-title">Homemade Ramen Broth</h3><a class="vid-link" href="https://www.tiktok.com/@ramen/video/741003">Watch on TikTok</a><p class="vid-desc">Rich miso ramen broth ready in under 20 minutes.</p></div>
    </div></body></html>"""

    gvid_drifted_html = """<!doctype html><html><body><div id="rso">
      <div class="vid-card"><h3 class="vid-title">Easy 15-Minute Pasta Recipe</h3><a class="vid-link" href="/url?opi=89978449&q=CAESQ29uZmlnVG9rZW4xMjM0NQ">Redirect</a><a class="vid-canonical" href="https://www.tiktok.com/@chef/video/741001">Source</a><p class="vid-desc">Quick garlic butter pasta made in one pan in 15 minutes.</p></div>
      <div class="vid-card"><h3 class="vid-title">Crispy Garlic Noodles</h3><a class="vid-link" href="/url?opi=89978449&q=CAESQ29uZmlnVG9rZW42Nzg5MA">Redirect</a><a class="vid-canonical" href="https://www.tiktok.com/@noodles/video/741002">Source</a><p class="vid-desc">Weeknight crispy chili garlic noodles with scallions.</p></div>
      <div class="vid-card"><h3 class="vid-title">Homemade Ramen Broth</h3><a class="vid-link" href="/url?opi=89978449&q=CAESQ29uZmlnVG9rZW45OTk5OQ">Redirect</a><a class="vid-canonical" href="https://www.tiktok.com/@ramen/video/741003">Source</a><p class="vid-desc">Rich miso ramen broth ready in under 20 minutes.</p></div>
    </div></body></html>"""

    # 3. Google AI Overview (#4550 & #4606): healthy vs drifted (/goto relative links in a.ai-ref-link vs canonical in a.ai-source-url)
    aiov_healthy_html = """<!doctype html><html><body><section class="ai-overview">
      <div class="ref-card"><h4 class="ref-title">PostgreSQL MVCC Documentation</h4><a class="ai-ref-link" href="https://www.postgresql.org/docs/current/mvcc.html">postgresql.org</a><p class="ref-snippet">PostgreSQL maintains data consistency using Multi-Version Concurrency Control.</p></div>
      <div class="ref-card"><h4 class="ref-title">Transaction Isolation Levels</h4><a class="ai-ref-link" href="https://www.postgresql.org/docs/current/transaction-iso.html">postgresql.org</a><p class="ref-snippet">Read Committed is the default isolation level in PostgreSQL.</p></div>
    </section></body></html>"""

    aiov_drifted_html = """<!doctype html><html><body><section class="ai-overview">
      <div class="ref-card"><h4 class="ref-title">PostgreSQL MVCC Documentation</h4><a class="ai-ref-link" href="/goto?id=abc123&sig=xyz">Redirect</a><a class="ai-source-url" href="https://www.postgresql.org/docs/current/mvcc.html">postgresql.org</a><p class="ref-snippet">PostgreSQL maintains data consistency using Multi-Version Concurrency Control.</p></div>
      <div class="ref-card"><h4 class="ref-title">Transaction Isolation Levels</h4><a class="ai-ref-link" href="/goto?id=def456&sig=uvw">Redirect</a><a class="ai-source-url" href="https://www.postgresql.org/docs/current/transaction-iso.html">postgresql.org</a><p class="ref-snippet">Read Committed is the default isolation level in PostgreSQL.</p></div>
    </section></body></html>"""

    # 4. Google Short Videos (#4554): "Verifying your request" wall returning HTTP 200 OK + 0 items (cannot be healed by CSS selector -> MUST ESCALATE/QUARANTINE!)
    gshort_verify_wall_html = """<!doctype html><html><head><title>Verifying your request</title></head><body>
      <div class="challenge-box"><h1>Verifying your request</h1><p>Our systems have detected unusual traffic from your computer network. Please complete the challenge.</p></div>
    </body></html>"""

    # 5. UNSEEN HELD-OUT SPLIT (4 completely different engines/DOM structures not used during dev design)
    bing_drifted_html = """<!doctype html><html><body><ol id="b_results">
      <li class="b_algo"><h2 class="b_title"><a class="b_old_link" href="/goto?u=a1b2c3">FastAPI Async Guide</a><a class="b_direct_href" href="https://fastapi.tiangolo.com/async/">Docs</a></h2><div class="b_caption"><p class="b_snippet">Learn how async def and concurrency work in FastAPI applications.</p></div></li>
      <li class="b_algo"><h2 class="b_title"><a class="b_old_link" href="/goto?u=d4e5f6">Pydantic V2 Validation</a><a class="b_direct_href" href="https://docs.pydantic.dev/latest/">Docs</a></h2><div class="b_caption"><p class="b_snippet">High-speed data validation and settings management using Python type annotations.</p></div></li>
    </ol></body></html>"""

    ddg_drifted_html = """<!doctype html><html><body><div class="results">
      <article class="result-card"><h2 class="res-head"><a class="res-url" href="https://www.rei.com/trail-pack">REI Co-op Trail 25 Pack</a></h2><span class="res-domain">www.rei.com/trail-pack</span><div class="res-body"><span class="old-desc">www.rei.com/trail-pack</span><p class="new-summary">Durable 25-liter daypack designed for steep day hikes and daily commutes.</p></div></article>
      <article class="result-card"><h2 class="res-head"><a class="res-url" href="https://www.osprey.com/daylite">Osprey Daylite Plus Pack</a></h2><span class="res-domain">www.osprey.com/daylite</span><div class="res-body"><span class="old-desc">www.osprey.com/daylite</span><p class="new-summary">Lightweight commuter backpack with padded laptop sleeve and breathable harness.</p></div></article>
    </div></body></html>"""

    yt_drifted_html = """<!doctype html><html><body><div class="yt-grid">
      <div class="yt-item"><span class="yt-name">3Blue1Brown</span><a class="yt-watch" href="/url?opi=111&q=CAESYTRedirectToken01">Go</a><a class="yt-channel-href" href="https://www.youtube.com/@3blue1brown">Channel</a><p class="yt-bio">Animated math explanations covering linear algebra, calculus, and neural networks.</p></div>
      <div class="yt-item"><span class="yt-name">Fireship</span><a class="yt-watch" href="/url?opi=111&q=CAESYTRedirectToken02">Go</a><a class="yt-channel-href" href="https://www.youtube.com/@Fireship">Channel</a><p class="yt-bio">High-intensity code tutorials and tech news to help you ship apps faster.</p></div>
    </div></body></html>"""

    gnews_wall_html = """<!doctype html><html><body><div class="interstitial">
      <h2>Verifying your request</h2><p>Automated queries are temporarily paused. Confirm you are human to continue.</p>
    </div></body></html>"""

    data = {
        "specs": {
            "yahoo_search": {
                "engine": "yahoo_search",
                "item_selector": "li.algo-sr",
                "title_selector": "h3.title a.ac-algo",
                "link_selector": "h3.title a.ac-algo",
                "displayed_link_selector": "span.cite-url",
                "snippet_selector": "div.compText p.lh-16",
                "version": "v1",
            },
            "google_videos_light": {
                "engine": "google_videos_light",
                "item_selector": "div.vid-card",
                "title_selector": "h3.vid-title",
                "link_selector": "a.vid-link",
                "displayed_link_selector": None,
                "snippet_selector": "p.vid-desc",
                "version": "v1",
            },
            "google_ai_overview": {
                "engine": "google_ai_overview",
                "item_selector": "div.ref-card",
                "title_selector": "h4.ref-title",
                "link_selector": "a.ai-ref-link",
                "displayed_link_selector": None,
                "snippet_selector": "p.ref-snippet",
                "version": "v1",
            },
            "google_short_videos": {
                "engine": "google_short_videos",
                "item_selector": "div.short-card",
                "title_selector": "h3.short-title",
                "link_selector": "a.short-link",
                "displayed_link_selector": None,
                "snippet_selector": "p.short-desc",
                "version": "v1",
            },
            "bing_organic": {
                "engine": "bing_organic",
                "item_selector": "li.b_algo",
                "title_selector": "h2.b_title a.b_old_link",
                "link_selector": "h2.b_title a.b_old_link",
                "displayed_link_selector": None,
                "snippet_selector": "div.b_caption p.b_snippet",
                "version": "v1",
            },
            "duckduckgo_shopping": {
                "engine": "duckduckgo_shopping",
                "item_selector": "article.result-card",
                "title_selector": "h2.res-head a.res-url",
                "link_selector": "h2.res-head a.res-url",
                "displayed_link_selector": "span.res-domain",
                "snippet_selector": "div.res-body span.old-desc",
                "version": "v1",
            },
            "youtube_channel": {
                "engine": "youtube_channel",
                "item_selector": "div.yt-item",
                "title_selector": "span.yt-name",
                "link_selector": "a.yt-watch",
                "displayed_link_selector": None,
                "snippet_selector": "p.yt-bio",
                "version": "v1",
            },
            "google_news": {
                "engine": "google_news",
                "item_selector": "article.news-card",
                "title_selector": "h3.news-head",
                "link_selector": "a.news-link",
                "displayed_link_selector": None,
                "snippet_selector": "p.news-snippet",
                "version": "v1",
            },
        },
        "snapshots": [
            {"snapshot_id": "yahoo_healthy_01", "split": "dev", "engine": "yahoo_search", "expected_healthy": True, "expected_healable": False, "roadmap_ref": "#4596", "html": yahoo_healthy_html},
            {"snapshot_id": "yahoo_drifted_4596", "split": "dev", "engine": "yahoo_search", "expected_healthy": False, "expected_healable": True, "roadmap_ref": "#4596", "html": yahoo_drifted_html},
            {"snapshot_id": "gvid_healthy_01", "split": "dev", "engine": "google_videos_light", "expected_healthy": True, "expected_healable": False, "roadmap_ref": "#4556", "html": gvid_healthy_html},
            {"snapshot_id": "gvid_drifted_4556", "split": "dev", "engine": "google_videos_light", "expected_healthy": False, "expected_healable": True, "roadmap_ref": "#4556", "html": gvid_drifted_html},
            {"snapshot_id": "aiov_healthy_01", "split": "dev", "engine": "google_ai_overview", "expected_healthy": True, "expected_healable": False, "roadmap_ref": "#4550", "html": aiov_healthy_html},
            {"snapshot_id": "aiov_drifted_4550", "split": "dev", "engine": "google_ai_overview", "expected_healthy": False, "expected_healable": True, "roadmap_ref": "#4550", "html": aiov_drifted_html},
            {"snapshot_id": "gshort_wall_4554", "split": "dev", "engine": "google_short_videos", "expected_healthy": False, "expected_healable": False, "roadmap_ref": "#4554", "html": gshort_verify_wall_html},
            {"snapshot_id": "bing_drifted_heldout", "split": "heldout", "engine": "bing_organic", "expected_healthy": False, "expected_healable": True, "roadmap_ref": "unseen", "html": bing_drifted_html},
            {"snapshot_id": "ddg_drifted_heldout", "split": "heldout", "engine": "duckduckgo_shopping", "expected_healthy": False, "expected_healable": True, "roadmap_ref": "unseen", "html": ddg_drifted_html},
            {"snapshot_id": "yt_drifted_heldout", "split": "heldout", "engine": "youtube_channel", "expected_healthy": False, "expected_healable": True, "roadmap_ref": "unseen", "html": yt_drifted_html},
            {"snapshot_id": "gnews_wall_heldout", "split": "heldout", "engine": "google_news", "expected_healthy": False, "expected_healable": False, "roadmap_ref": "unseen", "html": gnews_wall_html},
        ],
    }

    FIXTURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


if __name__ == "__main__":
    res = build_fixtures()
    print(f"Generated {len(res['snapshots'])} SERP HTML snapshots at {FIXTURES_PATH}")
