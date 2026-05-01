"""
FastAPI backend — Brand Intelligence & Outreach System
========================================================
POST /analyse       → Run full 12-pipeline analysis
GET  /status/{id}   → Check run status
GET  /report/{id}   → Fetch saved report
GET  /track/open/{id}    → Email open tracking pixel
GET  /track/click/{id}/{touch} → Email link click tracking
GET  /health        → API health check
GET  /config/check  → Check which APIs are configured
"""
import os, json, structlog
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from api.models import AnalyseRequest, TrackEventRequest
from config.settings import validate_config, API_HOST, API_PORT, OUTPUT_DIR

log = structlog.get_logger()

app = FastAPI(
    title="Brand Intelligence & Outreach System",
    description="Automated brand research and personalised outreach — built for StepOneXP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracker (replace with Redis/DB in production)
_jobs: dict = {}

# ─── TRACKING STORE (replace with DB in production) ───────────────────────────
_tracking: dict = {}

SCORING = {
    "open":            1,
    "open_repeated":   3,
    "click":           5,
    "linkedin_accept": 4,
    "reply":           10,
    "meeting":         20,
}

# 1x1 transparent GIF for tracking pixel
TRACKING_PIXEL = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)


# ─── HEALTH ───────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/config/check")
async def config_check():
    cfg = validate_config()
    return {
        "apis_configured": cfg,
        "ready": all(cfg.values()),
        "warnings": [f"{k} API not configured" for k, v in cfg.items() if not v],
    }


# ─── MAIN ANALYSIS ENDPOINT ───────────────────────────────────────────────────
@app.post("/analyse")
async def analyse(req: AnalyseRequest, background_tasks: BackgroundTasks):
    """
    Start a full brand intelligence analysis.
    Returns immediately with a job_id — poll /status/{job_id} for progress.
    """
    from utils.helpers import make_run_id
    job_id = make_run_id(req.company_name)
    _jobs[job_id] = {"status": "running", "progress": 0, "result": None}

    background_tasks.add_task(
        _run_analysis_job,
        job_id, req.company_name, req.company_url, req.category,
    )
    return {"job_id": job_id, "status": "started", "message": "Analysis running — poll /status/{job_id}"}


async def _run_analysis_job(job_id: str, name: str, url: str, category: str):
    try:
        from orchestrator import run_full_analysis, get_summary
        _jobs[job_id]["status"]   = "running"
        result  = run_full_analysis(name, url, category)
        summary = get_summary(result)
        _jobs[job_id]["status"]   = "complete"
        _jobs[job_id]["result"]   = summary
        _jobs[job_id]["run_id"]   = result["run_id"]
    except Exception as e:
        log.error("job_failed", job_id=job_id, error=str(e))
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"]  = str(e)


@app.get("/status/{job_id}")
async def status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return job


@app.get("/report/{run_id}")
async def get_report(run_id: str):
    """Fetch a saved report from disk."""
    out_dir  = Path(OUTPUT_DIR)
    out_path = out_dir / f"{run_id}.json"
    if not out_path.exists():
        raise HTTPException(404, f"Report {run_id} not found")
    with open(out_path) as f:
        return json.load(f)


@app.get("/reports")
async def list_reports():
    """List all saved reports."""
    out_dir = Path(OUTPUT_DIR)
    if not out_dir.exists():
        return {"reports": []}
    reports = []
    for f in sorted(out_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(f) as fp:
                data = json.load(fp)
                reports.append({
                    "run_id":       data.get("run_id"),
                    "company":      data.get("company_name"),
                    "completed_at": data.get("completed_at"),
                    "status":       data.get("overall_status"),
                })
        except Exception:
            pass
    return {"reports": reports}


# ─── TRACKING ENDPOINTS ───────────────────────────────────────────────────────
@app.get("/track/open/{tracking_id}")
async def track_open(tracking_id: str):
    """Email open tracking pixel — returns 1x1 GIF, logs the open event."""
    rec = _tracking.setdefault(tracking_id, {"opens": 0, "clicks": 0, "score": 0, "events": []})
    rec["opens"] += 1
    score_delta = SCORING["open_repeated"] if rec["opens"] > 1 else SCORING["open"]
    rec["score"] += score_delta
    rec["events"].append({"type": "open", "count": rec["opens"]})
    log.info("email_opened", tracking_id=tracking_id, total_opens=rec["opens"])
    return Response(content=TRACKING_PIXEL, media_type="image/gif")


@app.get("/track/click/{tracking_id}/{touch}")
async def track_click(tracking_id: str, touch: int, redirect: str = "https://steponexp.com"):
    """Email link click tracking — logs click and redirects."""
    from fastapi.responses import RedirectResponse
    rec = _tracking.setdefault(tracking_id, {"opens": 0, "clicks": 0, "score": 0, "events": []})
    rec["clicks"] += 1
    rec["score"]  += SCORING["click"]
    rec["events"].append({"type": "click", "touch": touch})
    log.info("link_clicked", tracking_id=tracking_id, touch=touch)
    return RedirectResponse(url=redirect)


@app.post("/track/event")
async def track_event(req: TrackEventRequest):
    """Manual event tracking (replies, LinkedIn accepts, meeting booked)."""
    rec = _tracking.setdefault(req.tracking_id, {"opens": 0, "clicks": 0, "score": 0, "events": []})
    score_delta = SCORING.get(req.event_type, 0)
    rec["score"]  += score_delta
    rec["events"].append({"type": req.event_type, "touch": req.touch, "metadata": req.metadata})
    return {"tracking_id": req.tracking_id, "score": rec["score"], "event_logged": req.event_type}


@app.get("/track/dashboard/{tracking_id}")
async def tracking_dashboard(tracking_id: str):
    """Get engagement score and status for a contact."""
    rec = _tracking.get(tracking_id, {"opens": 0, "clicks": 0, "score": 0, "events": []})
    score = rec.get("score", 0)
    if score >= 20:   status = "HOT"
    elif score >= 10: status = "WARM"
    elif score >= 3:  status = "ENGAGED"
    elif score >= 1:  status = "OPENED"
    else:             status = "COLD"
    return {"tracking_id": tracking_id, "score": score, "status": status, "events": rec.get("events", [])}


# ─── SERVE FRONTEND ───────────────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_path / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=True)
