"""FastAPI server for serpapi-dom-healer (serves REST API + zero-WebSocket JS UI)."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.eval import EVAL_SUMMARY_PATH, FIXTURES_PATH, evaluate_all_splits
from src.healer import heal_serp_parser
from src.models import SelectorSpec, model_to_dict

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_INDEX = ROOT_DIR / "static" / "index.html"

app = FastAPI(
    title="SerpApi DOM Healer & Silent-200 Regression Sentinel",
    description=(
        "Deterministic SERP HTML regression validator + bounded self-healing CSS selector agent "
        "modeled on real Nov 2026 serpapi/public-roadmap parser issues."
    ),
    version="1.0.0",
)


class HealRequest(BaseModel):
    snapshot_id: Optional[str] = Field(default="yahoo_drifted_4596")
    custom_html: Optional[str] = None
    custom_spec: Optional[SelectorSpec] = None
    use_live_github: bool = False


@app.get("/", response_class=HTMLResponse)
def serve_ui() -> str:
    if STATIC_INDEX.exists():
        return STATIC_INDEX.read_text(encoding="utf-8")
    return "<h1>serpapi-dom-healer API is running. Visit /docs</h1>"


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "serpapi-dom-healer",
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "github_token_configured": bool(os.getenv("GITHUB_TOKEN")),
        "groq_model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    }


@app.get("/v1/snapshots")
def list_snapshots() -> Dict[str, Any]:
    raw = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return {
        "specs": raw["specs"],
        "snapshots": [
            {
                "snapshot_id": s["snapshot_id"],
                "split": s["split"],
                "engine": s["engine"],
                "roadmap_ref": s["roadmap_ref"],
                "expected_healthy": s["expected_healthy"],
                "expected_healable": s["expected_healable"],
            }
            for s in raw["snapshots"]
        ],
    }


@app.post("/v1/heal")
def run_heal(req: HealRequest) -> Dict[str, Any]:
    raw = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    specs = {k: SelectorSpec(**v) for k, v in raw["specs"].items()}
    snaps = {s["snapshot_id"]: s for s in raw["snapshots"]}

    if req.custom_html and req.custom_spec:
        html = req.custom_html
        spec = req.custom_spec
        snap_id = "custom_html_input"
    else:
        if not req.snapshot_id or req.snapshot_id not in snaps:
            raise HTTPException(status_code=404, detail=f"Snapshot '{req.snapshot_id}' not found.")
        snap = snaps[req.snapshot_id]
        html = snap["html"]
        spec = specs[snap["engine"]]
        snap_id = snap["snapshot_id"]

    report = heal_serp_parser(
        html=html,
        spec=spec,
        snapshot_id=snap_id,
        max_attempts=2,
        use_live_github=req.use_live_github,
    )
    return {
        "original_spec": model_to_dict(spec),
        "report": model_to_dict(report),
    }


@app.post("/v1/run-eval")
def run_eval() -> Dict[str, Any]:
    return evaluate_all_splits()


@app.get("/v1/eval-summary")
def get_eval_summary() -> Dict[str, Any]:
    if EVAL_SUMMARY_PATH.exists():
        return json.loads(EVAL_SUMMARY_PATH.read_text(encoding="utf-8"))
    return evaluate_all_splits()
