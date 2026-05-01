"""
Orchestrator — Runs all 12 pipelines in sequence for a given company input.
Each pipeline result is passed forward where needed (p10 needs p09, p11 needs all, p12 needs p11).
Saves full output as JSON to ./outputs/{run_id}.json
"""
import os, json, time, structlog
from datetime import datetime
from pathlib import Path
from utils.helpers import make_run_id, timestamp

log = structlog.get_logger()


def run_full_analysis(company_name: str, company_url: str, category: str, progress_cb=None) -> dict:
    """
    Run the complete 12-pipeline brand intelligence analysis.

    Args:
        company_name: e.g. "Zepto"
        company_url:  e.g. "https://www.zeptonow.com"
        category:     e.g. "quick commerce grocery delivery"

    Returns:
        Complete analysis dict with all 12 pipeline outputs
    """
    run_id     = make_run_id(company_name)
    started_at = timestamp()
    t_total    = time.time()

    log.info("orchestrator_start", company=company_name, run_id=run_id)

    results = {
        "run_id":       run_id,
        "company_name": company_name,
        "company_url":  company_url,
        "category":     category,
        "started_at":   started_at,
        "pipelines":    {},
    }

    # ── IMPORT ALL PIPELINES ─────────────────────────────────────────────────
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

    def _run(pipeline_class, pipeline_key, **extra_kwargs):
        log.info("running_pipeline", pipeline=pipeline_key)
        if progress_cb:
            progress_cb(pipeline_key, _done[0], len(PIPELINE_KEYS))
        try:
            if extra_kwargs:
                p = pipeline_class(company_name, company_url, category, **extra_kwargs)
            else:
                p = pipeline_class(company_name, company_url, category)
            result = p.run()
            results["pipelines"][pipeline_key] = result
            _done[0] += 1
            log.info("pipeline_done", pipeline=pipeline_key, status=result.get("status"))
            return result
        except Exception as e:
            log.error("pipeline_exception", pipeline=pipeline_key, error=str(e))
            results["pipelines"][pipeline_key] = {"status": "error", "error": str(e), "output": {}}
            _done[0] += 1
            return {"status": "error", "output": {}}

    # ── RUN PIPELINES (sequential — each builds on previous) ─────────────────
    _run(CompanyOverviewPipeline,       "p01_company_overview")
    _run(BrandIdentityPipeline,         "p02_brand_identity")
    _run(MarketPositionPipeline,        "p03_market_position")
    _run(CompetitorMappingPipeline,     "p04_competitor_mapping")
    _run(BrandActivityPipeline,         "p05_brand_activity")
    _run(ExperientialFootprintPipeline, "p06_experiential_footprint")
    _run(ReputationResearchPipeline,    "p07_reputation_research")
    _run(StrategicWatchoutsPipeline,    "p08_strategic_watchouts")

    p09_result = _run(DecisionMakersPipeline, "p09_decision_makers")
    p09_output = p09_result.get("output", {})

    # p10 uses p09's decision-makers output
    p10_result = _run(
        ContactIntelligencePipeline,
        "p10_contact_intelligence",
        decision_makers_output=p09_output,
    )

    # p11 uses all previous outputs
    _run(
        OutreachPipeline,
        "p11_outreach",
        all_pipeline_outputs=results["pipelines"],
    )

    p11_output = results["pipelines"].get("p11_outreach", {}).get("output", {})

    # p12 uses p11's outreach output
    _run(
        TrackingPipeline,
        "p12_tracking",
        outreach_output=p11_output,
    )

    # ── FINALISE ─────────────────────────────────────────────────────────────
    elapsed = round(time.time() - t_total, 2)
    success_count = sum(1 for p in results["pipelines"].values() if p.get("status") == "success")
    error_count   = sum(1 for p in results["pipelines"].values() if p.get("status") == "error")

    results["completed_at"]    = timestamp()
    results["total_elapsed"]   = elapsed
    results["pipelines_run"]   = len(results["pipelines"])
    results["pipelines_ok"]    = success_count
    results["pipelines_error"] = error_count
    results["overall_status"]  = "success" if error_count == 0 else "partial" if success_count > 0 else "failed"

    # Save to disk
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
    """Extract a clean summary from full results for the API response."""
    pipes = results.get("pipelines", {})

    def _out(key): return pipes.get(key, {}).get("output", {})

    return {
        "run_id":         results["run_id"],
        "company":        results["company_name"],
        "status":         results["overall_status"],
        "elapsed_secs":   results["total_elapsed"],
        "icp_fit_score":  _out("p01_company_overview").get("icp_fit_score"),
        "readiness":      _out("p01_company_overview").get("experiential_readiness"),
        "watchout":       _out("p08_strategic_watchouts").get("overall_verdict"),
        "primary_colors": _out("p02_brand_identity").get("primary_colors"),
        "brand_tone":     _out("p02_brand_identity").get("brand_tone"),
        "pitch_angle":    _out("p06_experiential_footprint").get("pitch_angle"),
        "primary_contact": _out("p11_outreach").get("primary_contact"),
        "reputation":     _out("p07_reputation_research").get("reputation_label"),
        "full_report":    results,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python orchestrator.py 'Company Name' 'https://url.com' 'category description'")
        sys.exit(1)
    result = run_full_analysis(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(get_summary(result), indent=2, default=str))
