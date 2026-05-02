"""
Orchestrator — Runs all 12 pipelines.
P01-P09 run in parallel (ThreadPoolExecutor), then P10→P11→P12 sequentially.
Emits log_cb events so the frontend can show a live terminal feed.
"""
import os, json, time, threading, structlog
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.helpers import make_run_id, timestamp

log = structlog.get_logger()

# ── Human-readable start messages ────────────────────────────────────────────
START_MESSAGES = {
    "p01_company_overview":       "Crawling website + 2 Google searches (funding · team · news)",
    "p02_brand_identity":         "Extracting CSS colours, fonts & brand voice from homepage",
    "p03_market_position":        "Searching sentiment signals & share-of-voice data",
    "p04_competitor_mapping":     "Identifying competitors + crawling their websites",
    "p05_brand_activity":         "Scanning PR, campaigns & partnerships (last 24 months)",
    "p06_experiential_footprint": "Searching for events, sponsorships & activations",
    "p07_reputation_research":    "Scraping Reddit + review platforms for authentic sentiment",
    "p08_strategic_watchouts":    "Scanning for risk signals, leadership changes & controversies",
    "p09_decision_makers":        "Finding marketing decision-makers via Google / LinkedIn",
    "p10_contact_intelligence":   "Looking up email addresses via Hunter.io",
    "p11_outreach":               "Generating personalised 4-touch outreach sequence with GPT-4o",
    "p12_tracking":               "Configuring engagement tracking pixel & scoring model",
}

# ── Key finding extractor (one-liner per pipeline) ───────────────────────────
def _key_finding(pipeline_key: str, result: dict) -> str:
    if result.get("status") == "error":
        return f"Error — {result.get('error','?')[:60]}"
    o = result.get("output", {})
    try:
        if pipeline_key == "p01_company_overview":
            return f"ICP {o.get('icp_fit_score','?')}/100 · {o.get('business_model','?')} · {o.get('experiential_readiness','?')} readiness"
        if pipeline_key == "p02_brand_identity":
            cols  = len(o.get("primary_colors") or o.get("extracted_colors") or [])
            fonts = (o.get("primary_fonts") or o.get("extracted_fonts") or ["?"])
            return f"{cols} colours · Font: {fonts[0]} · Tone: {o.get('brand_tone','?')}"
        if pipeline_key == "p03_market_position":
            return f"Sentiment: {o.get('brand_sentiment','?')} · SoV: {o.get('share_of_voice_level','?')} · Gap: {o.get('perception_gap_score','?')}/5"
        if pipeline_key == "p04_competitor_mapping":
            return f"{len(o.get('competitors',[]))} competitors · Urgency: {o.get('competitive_urgency','?')}"
        if pipeline_key == "p05_brand_activity":
            return f"{len(o.get('recent_campaigns',[]))} campaigns · Budget: {o.get('budget_signal','?')} · {str(o.get('last_major_campaign','?'))[:40]}"
        if pipeline_key == "p06_experiential_footprint":
            return f"{len(o.get('events_timeline',[]))} events · Score: {o.get('experiential_maturity_score','?')}/5 · {o.get('events_frequency','?')}"
        if pipeline_key == "p07_reputation_research":
            return f"{o.get('reputation_label','?')} · Score: {o.get('overall_reputation_score','?')}/100 · Reddit: {o.get('reddit_sentiment','?')}"
        if pipeline_key == "p08_strategic_watchouts":
            return f"Verdict: {o.get('overall_verdict','?')} · {o.get('timing_recommendation','?')}"
        if pipeline_key == "p09_decision_makers":
            return f"{o.get('total_contacts_found',0)} contacts · Primary: {o.get('primary_contact','?')} · {o.get('confidence_level','?')}"
        if pipeline_key == "p10_contact_intelligence":
            return f"{o.get('total_contacts',0)} contacts · {o.get('verified_emails',0)} emails verified · Pattern: {o.get('email_pattern','?')}"
        if pipeline_key == "p11_outreach":
            pc = o.get("primary_contact") or {}
            return f"4-touch sequence → {pc.get('name','?')} ({pc.get('title','?')})"
        if pipeline_key == "p12_tracking":
            return f"{len(o.get('tracking_records',[]))} records · pixel + click tracking configured"
    except Exception:
        pass
    return "Completed"


def run_full_analysis(
    company_name: str,
    company_url:  str,
    category:     str,
    progress_cb=None,
    running_cb=None,
    log_cb=None,        # NEW: fn(pipeline_key, event_type, message, elapsed)
) -> dict:
    run_id     = make_run_id(company_name)
    started_at = timestamp()
    t_total    = time.time()

    log.info("orchestrator_start", company=company_name, run_id=run_id)
    if log_cb:
        log_cb("system", "start", f"Starting full analysis for \"{company_name}\"", 0)
        log_cb("system", "info",  f"Phase 1 — running P01–P09 in parallel (4 workers)", 0)

    results = {
        "run_id":       run_id,
        "company_name": company_name,
        "company_url":  company_url,
        "category":     category,
        "started_at":   started_at,
        "pipelines":    {},
    }

    from pipelines.p01_company_overview.pipeline  import CompanyOverviewPipeline
    from pipelines.p02_brand_identity.pipeline    import BrandIdentityPipeline
    from pipelines.p03_market_position.pipeline   import MarketPositionPipeline
    from pipelines.p04_competitor_mapping.pipeline import CompetitorMappingPipeline
    from pipelines.p05_brand_activity.pipeline    import BrandActivityPipeline
    from pipelines.p06_experiential_footprint.pipeline import ExperientialFootprintPipeline
    from pipelines.p07_reputation_research.pipeline import ReputationResearchPipeline
    from pipelines.p08_strategic_watchouts.pipeline import StrategicWatchoutsPipeline
    from pipelines.p09_decision_makers.pipeline   import DecisionMakersPipeline
    from pipelines.p10_contact_intelligence.pipeline import ContactIntelligencePipeline
    from pipelines.p11_outreach.pipeline          import OutreachPipeline
    from pipelines.p12_tracking.pipeline          import TrackingPipeline

    PIPELINE_KEYS = [
        "p01_company_overview", "p02_brand_identity", "p03_market_position",
        "p04_competitor_mapping", "p05_brand_activity", "p06_experiential_footprint",
        "p07_reputation_research", "p08_strategic_watchouts", "p09_decision_makers",
        "p10_contact_intelligence", "p11_outreach", "p12_tracking",
    ]
    _done = [0]
    _lock = threading.Lock()

    def _run(pipeline_class, pipeline_key, **extra_kwargs):
        t_pipe = time.time()
        elapsed_start = round(time.time() - t_total, 1)
        log.info("running_pipeline", pipeline=pipeline_key)

        if running_cb:
            running_cb(pipeline_key)
        if log_cb:
            msg = START_MESSAGES.get(pipeline_key, pipeline_key)
            log_cb(pipeline_key, "start", msg, elapsed_start)

        try:
            p = pipeline_class(company_name, company_url, category, **extra_kwargs) \
                if extra_kwargs else pipeline_class(company_name, company_url, category)
            result = p.run()

            elapsed_done = round(time.time() - t_total, 1)
            pipe_elapsed = round(time.time() - t_pipe, 1)

            with _lock:
                results["pipelines"][pipeline_key] = result
                _done[0] += 1

            finding = _key_finding(pipeline_key, result)
            log.info("pipeline_done", pipeline=pipeline_key, status=result.get("status"), elapsed=pipe_elapsed)

            if log_cb:
                log_cb(pipeline_key, "done", f"{finding}  [{pipe_elapsed}s]", elapsed_done)
            if progress_cb:
                progress_cb(pipeline_key, _done[0], len(PIPELINE_KEYS))
            return result

        except Exception as e:
            elapsed_done = round(time.time() - t_total, 1)
            log.error("pipeline_exception", pipeline=pipeline_key, error=str(e))
            error_result = {"status": "error", "error": str(e), "output": {}}
            with _lock:
                results["pipelines"][pipeline_key] = error_result
                _done[0] += 1
            if log_cb:
                log_cb(pipeline_key, "error", f"Error — {str(e)[:80]}", elapsed_done)
            if progress_cb:
                progress_cb(pipeline_key, _done[0], len(PIPELINE_KEYS))
            return error_result

    # ── PHASE 1: P01–P09 in parallel ─────────────────────────────────────────
    phase1 = [
        (CompanyOverviewPipeline,        "p01_company_overview"),
        (BrandIdentityPipeline,          "p02_brand_identity"),
        (MarketPositionPipeline,         "p03_market_position"),
        (CompetitorMappingPipeline,      "p04_competitor_mapping"),
        (BrandActivityPipeline,          "p05_brand_activity"),
        (ExperientialFootprintPipeline,  "p06_experiential_footprint"),
        (ReputationResearchPipeline,     "p07_reputation_research"),
        (StrategicWatchoutsPipeline,     "p08_strategic_watchouts"),
        (DecisionMakersPipeline,         "p09_decision_makers"),
    ]

    p09_result = {"output": {}}

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_key = {executor.submit(_run, cls, key): key for cls, key in phase1}
        for future in as_completed(future_to_key):
            key    = future_to_key[future]
            result = future.result()
            if key == "p09_decision_makers":
                p09_result = result

    # ── PHASE 2: P10 → P11 → P12 sequential ─────────────────────────────────
    if log_cb:
        log_cb("system", "info", "Phase 2 — P10 Contact Intel → P11 Outreach → P12 Tracking", round(time.time()-t_total,1))

    p10_result = _run(
        ContactIntelligencePipeline,
        "p10_contact_intelligence",
        decision_makers_output=p09_result.get("output", {}),
    )

    _run(OutreachPipeline, "p11_outreach", all_pipeline_outputs=results["pipelines"])

    p11_output = results["pipelines"].get("p11_outreach", {}).get("output", {})
    _run(TrackingPipeline, "p12_tracking", outreach_output=p11_output)

    # ── FINALISE ─────────────────────────────────────────────────────────────
    elapsed       = round(time.time() - t_total, 2)
    success_count = sum(1 for p in results["pipelines"].values() if p.get("status") == "success")
    error_count   = sum(1 for p in results["pipelines"].values() if p.get("status") == "error")

    results["completed_at"]    = timestamp()
    results["total_elapsed"]   = elapsed
    results["pipelines_run"]   = len(results["pipelines"])
    results["pipelines_ok"]    = success_count
    results["pipelines_error"] = error_count
    results["overall_status"]  = "success" if error_count == 0 else "partial" if success_count > 0 else "failed"

    if log_cb:
        log_cb("system", "complete",
               f"Analysis complete in {elapsed}s — {success_count}/12 pipelines OK"
               + (f" · {error_count} errors" if error_count else ""),
               elapsed)

    _save_output(results, run_id)
    log.info("orchestrator_complete", run_id=run_id, elapsed=elapsed, ok=success_count, errors=error_count)
    return results


def _save_output(results: dict, run_id: str):
    output_dir = Path(os.getenv("OUTPUT_DIR", "./outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{run_id}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    log.info("output_saved", path=str(out_path))


def get_summary(results: dict) -> dict:
    pipes = results.get("pipelines", {})
    def _out(key): return pipes.get(key, {}).get("output", {})
    return {
        "run_id":          results["run_id"],
        "company":         results["company_name"],
        "status":          results["overall_status"],
        "elapsed_secs":    results["total_elapsed"],
        "icp_fit_score":   _out("p01_company_overview").get("icp_fit_score"),
        "readiness":       _out("p01_company_overview").get("experiential_readiness"),
        "watchout":        _out("p08_strategic_watchouts").get("overall_verdict"),
        "primary_colors":  _out("p02_brand_identity").get("primary_colors"),
        "brand_tone":      _out("p02_brand_identity").get("brand_tone"),
        "pitch_angle":     _out("p06_experiential_footprint").get("pitch_angle"),
        "primary_contact": _out("p11_outreach").get("primary_contact"),
        "reputation":      _out("p07_reputation_research").get("reputation_label"),
        "full_report":     results,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python orchestrator.py 'Company Name' 'https://url.com' 'category'")
        sys.exit(1)
    result = run_full_analysis(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(get_summary(result), indent=2, default=str))
