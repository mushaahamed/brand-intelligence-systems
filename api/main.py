"""
FastAPI backend — Brand Intelligence & Outreach System
========================================================
POST /analyse            → Run full 12-pipeline analysis
GET  /status/{id}        → Check run status (pipeline log + summaries)
GET  /report/{id}        → Fetch saved report
GET  /reports            → List all saved reports
GET  /debug/{id}         → Full debug info
GET  /track/open/{id}    → Email open tracking pixel
GET  /track/click/{id}/{touch} → Link click tracking
GET  /health             → Health check
GET  /config/check       → API configuration check
"""
import os, json, time, structlog
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from api.models import AnalyseRequest, TrackEventRequest
from config.settings import validate_config, API_HOST, API_PORT, OUTPUT_DIR

# ── Clean terminal output for demos ──────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="%H:%M:%S", utc=False),
        structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        ),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()

app = FastAPI(
    title="Brand Intelligence & Outreach System",
    description="Automated brand research and personalised outreach — built for StepOneXP",
    version="2.0.0",
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

_jobs: dict    = {}
_tracking: dict = {}

SCORING = {
    "open": 1, "open_repeated": 3, "click": 5,
    "linkedin_accept": 4, "reply": 10, "meeting": 20,
}

TRACKING_PIXEL = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)

PIPELINE_LABELS = {
    "p01_company_overview":       "Company Overview",
    "p02_brand_identity":         "Brand Identity",
    "p03_market_position":        "Market Position",
    "p04_competitor_mapping":     "Competitor Mapping",
    "p05_brand_activity":         "Brand Activity",
    "p06_experiential_footprint": "Experiential Footprint",
    "p07_reputation_research":    "Reputation Research",
    "p08_strategic_watchouts":    "Strategic Watchouts",
    "p09_decision_makers":        "Decision Makers",
    "p10_contact_intelligence":   "Contact Intelligence",
    "p11_outreach":               "Outreach Sequences",
    "p12_tracking":               "Tracking Setup",
}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/config/check")
async def config_check():
    cfg = validate_config()
    return {
        "apis_configured": cfg,
        "ready": all(cfg.values()),
        "warnings": [f"{k} API not configured" for k, v in cfg.items() if not v],
    }


@app.post("/analyse")
async def analyse(req: AnalyseRequest, background_tasks: BackgroundTasks):
    from utils.helpers import make_run_id
    job_id = make_run_id(req.company_name)
    _jobs[job_id] = {
        "status":             "running",
        "progress":           0,
        "pipeline":           "starting",
        "pipeline_label":     "Initialising...",
        "pipelines_done":     [],
        "running_pipelines":  [],
        "pipeline_summaries": {},
        "pipeline_log":       [],
        "result":             None,
        "error":              None,
        "started_at":         time.time(),
    }
    background_tasks.add_task(
        _run_analysis_job,
        job_id, req.company_name, req.company_url, req.category,
    )
    return {"job_id": job_id, "status": "started",
            "message": f"Analysis running — poll /status/{job_id}"}


def _run_analysis_job(job_id: str, name: str, url: str, category: str):
    t_start = _jobs[job_id]["started_at"]

    def _fmt_ts():
        s = time.time() - t_start
        return f"{int(s//60):02d}:{s%60:05.2f}"

    def _log_cb(pipeline_key: str, event_type: str, message: str, elapsed: float):
        entry = {
            "ts":       _fmt_ts(),
            "elapsed":  elapsed,
            "pipeline": pipeline_key,
            "type":     event_type,
            "message":  message,
        }
        _jobs[job_id]["pipeline_log"].append(entry)
        if event_type in ("done", "error") and pipeline_key != "system":
            _jobs[job_id]["pipeline_summaries"][pipeline_key] = {
                "finding": message,
                "status":  "done" if event_type == "done" else "error",
            }

    def _running(pipeline_key: str):
        running = _jobs[job_id].get("running_pipelines", [])
        if pipeline_key not in running:
            running.append(pipeline_key)
        _jobs[job_id]["running_pipelines"] = running

    def _progress(pipeline_key: str, done: int, total: int):
        done_list = _jobs[job_id].get("pipelines_done", [])
        running   = _jobs[job_id].get("running_pipelines", [])
        if pipeline_key not in done_list:
            done_list.append(pipeline_key)
        if pipeline_key in running:
            running.remove(pipeline_key)
        _jobs[job_id]["pipelines_done"]    = done_list
        _jobs[job_id]["running_pipelines"] = running
        _jobs[job_id]["pipeline"]          = pipeline_key
        _jobs[job_id]["pipeline_label"]    = PIPELINE_LABELS.get(pipeline_key, pipeline_key)
        _jobs[job_id]["progress"]          = round((len(done_list) / total) * 100)

    try:
        from orchestrator import run_full_analysis, get_summary
        log.info(f"\n{'─'*60}")
        log.info(f"  Brand Intelligence Analysis  ·  {name}  ·  {category}")
        log.info(f"{'─'*60}")
        result  = run_full_analysis(name, url, category,
                                    progress_cb=_progress,
                                    running_cb=_running,
                                    log_cb=_log_cb)
        summary = get_summary(result)

        _jobs[job_id]["status"]         = "complete"
        _jobs[job_id]["progress"]       = 100
        _jobs[job_id]["pipeline_label"] = "Done"
        _jobs[job_id]["result"]         = summary
        _jobs[job_id]["run_id"]         = result["run_id"]
        _jobs[job_id]["elapsed"]        = result.get("total_elapsed")
        elapsed_total = result.get("total_elapsed", 0)
        log.info(f"{'─'*60}")
        log.info(f"  ✅  Analysis complete  ·  {name}  ·  {elapsed_total}s  ·  12 pipelines")
        log.info(f"{'─'*60}\n")

    except Exception as e:
        import traceback
        log.error(f"  ✗  Analysis failed — {str(e)[:120]}")
        _jobs[job_id]["status"]    = "failed"
        _jobs[job_id]["error"]     = str(e)
        _jobs[job_id]["traceback"] = traceback.format_exc()
        _log_cb("system", "error", f"Job failed — {str(e)}", round(time.time()-t_start, 1))


@app.get("/status/{job_id}")
async def status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return {
        "status":             job["status"],
        "progress":           job.get("progress", 0),
        "pipeline":           job.get("pipeline"),
        "pipeline_label":     job.get("pipeline_label", ""),
        "pipelines_done":     job.get("pipelines_done", []),
        "running_pipelines":  job.get("running_pipelines", []),
        "pipeline_summaries": job.get("pipeline_summaries", {}),
        "pipeline_log":       job.get("pipeline_log", []),
        "result":             job.get("result"),
        "error":              job.get("error"),
        "run_id":             job.get("run_id"),
        "elapsed":            job.get("elapsed"),
    }


@app.get("/report/{run_id}")
async def get_report(run_id: str):
    out_path = Path(OUTPUT_DIR) / f"{run_id}.json"
    if not out_path.exists():
        raise HTTPException(404, f"Report {run_id} not found")
    with open(out_path) as f:
        return json.load(f)


@app.get("/reports")
async def list_reports():
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
                    "elapsed":      data.get("total_elapsed"),
                })
        except Exception:
            pass
    return {"reports": reports}


@app.get("/debug/{job_id}")
async def debug_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return job


@app.get("/track/open/{tracking_id}")
async def track_open(tracking_id: str):
    rec = _tracking.setdefault(tracking_id, {"opens": 0, "clicks": 0, "score": 0, "events": []})
    rec["opens"] += 1
    delta = SCORING["open_repeated"] if rec["opens"] > 1 else SCORING["open"]
    rec["score"] += delta
    rec["events"].append({"type": "open", "count": rec["opens"]})
    return Response(content=TRACKING_PIXEL, media_type="image/gif")


@app.get("/track/click/{tracking_id}/{touch}")
async def track_click(tracking_id: str, touch: int, redirect: str = "https://steponexp.com"):
    from fastapi.responses import RedirectResponse
    rec = _tracking.setdefault(tracking_id, {"opens": 0, "clicks": 0, "score": 0, "events": []})
    rec["clicks"] += 1
    rec["score"]  += SCORING["click"]
    rec["events"].append({"type": "click", "touch": touch})
    return RedirectResponse(url=redirect)


@app.post("/track/event")
async def track_event(req: TrackEventRequest):
    rec = _tracking.setdefault(req.tracking_id, {"opens": 0, "clicks": 0, "score": 0, "events": []})
    rec["score"] += SCORING.get(req.event_type, 0)
    rec["events"].append({"type": req.event_type, "touch": req.touch, "metadata": req.metadata})
    return {"tracking_id": req.tracking_id, "score": rec["score"], "event_logged": req.event_type}


@app.get("/track/dashboard/{tracking_id}")
async def tracking_dashboard(tracking_id: str):
    rec   = _tracking.get(tracking_id, {"opens": 0, "clicks": 0, "score": 0, "events": []})
    score = rec.get("score", 0)
    label = "HOT" if score >= 20 else "WARM" if score >= 10 else "ENGAGED" if score >= 3 else "OPENED" if score >= 1 else "COLD"
    return {"tracking_id": tracking_id, "score": score, "status": label, "events": rec.get("events", [])}


frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_path / "index.html"))

    @app.get("/style.css")
    async def serve_css():
        return FileResponse(str(frontend_path / "style.css"), media_type="text/css")

    @app.get("/app.js")
    async def serve_js():
        return FileResponse(str(frontend_path / "app.js"), media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=True)
