"""
API connectivity and configuration tests.
Run before your first production use:
  python -m pytest tests/ -v
"""
import os
import sys
import json
import pytest
import requests
from pathlib import Path

# ── ensure project root is on path ──────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ── helpers ──────────────────────────────────────────────────────────────────
def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


load_env()


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG TESTS
# ─────────────────────────────────────────────────────────────────────────────
class TestConfig:
    def test_env_file_exists(self):
        assert (ROOT / ".env").exists() or (ROOT / ".env.example").exists(), \
            ".env file missing — copy .env.example and fill in your keys"

    def test_openai_key_present(self):
        key = os.getenv("OPENAI_API_KEY", "")
        assert key, "OPENAI_API_KEY is not set in .env"
        assert key.startswith("sk-"), "OPENAI_API_KEY looks malformed"

    def test_at_least_one_apify_token(self):
        tokens = [os.getenv(f"APIFY_TOKEN_{i}", "") for i in range(1, 6)]
        present = [t for t in tokens if t]
        assert present, "No APIFY_TOKEN_1..5 found in environment"

    def test_hunter_key_present(self):
        key = os.getenv("HUNTER_API_KEY", "")
        assert key, "HUNTER_API_KEY is not set — email lookup will fall back to pattern inference"

    def test_settings_import(self):
        from config.settings import OPENAI_MODEL, APIFY_TOKENS
        assert OPENAI_MODEL, "OPENAI_MODEL not defined in settings"
        assert isinstance(APIFY_TOKENS, dict), "APIFY_TOKENS should be a dict"

    def test_apify_config_import(self):
        from config.apify_config import ACTORS, TOKEN_GROUP_MAP
        assert "google_search" in ACTORS
        assert "website_crawler" in ACTORS
        assert "reddit_scraper" in ACTORS
        assert len(TOKEN_GROUP_MAP) == 5, "Expected 5 token groups"


# ─────────────────────────────────────────────────────────────────────────────
# OPENAI API TEST
# ─────────────────────────────────────────────────────────────────────────────
class TestOpenAIAPI:
    def test_simple_call(self):
        """Verify OpenAI key works with a minimal gpt-4o-mini call."""
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        msg = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=32,
            messages=[{"role": "user", "content": "Reply with the word PONG only."}],
        )
        text = msg.choices[0].message.content.strip()
        assert "PONG" in text.upper(), f"Unexpected response: {text}"

    def test_json_extraction(self):
        """Verify our extract_json helper works end-to-end."""
        from utils.claude_client import extract_json
        result = extract_json(
            system="Return JSON only.",
            user='Return exactly: {"status": "ok"}',
        )
        assert isinstance(result, dict)
        assert result.get("status") == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# APIFY API TEST
# ─────────────────────────────────────────────────────────────────────────────
class TestApifyAPI:
    def test_token_format(self):
        token = os.getenv("APIFY_TOKEN_1", "")
        assert token, "APIFY_TOKEN_1 not set"
        assert len(token) >= 20, "APIFY_TOKEN_1 looks too short"

    def test_apify_user_endpoint(self):
        """Hit the Apify /users/me endpoint to confirm token validity."""
        token = os.getenv("APIFY_TOKEN_1", "")
        if not token:
            pytest.skip("APIFY_TOKEN_1 not set")
        resp = requests.get(
            "https://api.apify.com/v2/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert resp.status_code == 200, f"Apify auth failed: {resp.status_code} — {resp.text[:200]}"
        data = resp.json()
        assert "data" in data
        print(f"\n  Apify user: {data['data'].get('username')}")

    def test_google_search_actor_exists(self):
        """Confirm the google-search-scraper actor is accessible."""
        token = os.getenv("APIFY_TOKEN_1", "")
        if not token:
            pytest.skip("APIFY_TOKEN_1 not set")
        from config.apify_config import ACTORS
        actor_id = ACTORS["google_search"]
        resp = requests.get(
            f"https://api.apify.com/v2/acts/{actor_id.replace('/', '~')}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert resp.status_code == 200, f"Actor not found: {actor_id}"


# ─────────────────────────────────────────────────────────────────────────────
# HUNTER.IO API TEST
# ─────────────────────────────────────────────────────────────────────────────
class TestHunterAPI:
    def test_hunter_account_info(self):
        key = os.getenv("HUNTER_API_KEY", "")
        if not key:
            pytest.skip("HUNTER_API_KEY not set")
        resp = requests.get(
            "https://api.hunter.io/v2/account",
            params={"api_key": key},
            timeout=10,
        )
        assert resp.status_code == 200, f"Hunter auth failed: {resp.status_code}"
        data = resp.json()
        assert "data" in data
        remaining = data["data"].get("requests", {}).get("searches", {}).get("available", "?")
        print(f"\n  Hunter.io OK — searches remaining this month: {remaining}")

    def test_hunter_domain_search(self):
        key = os.getenv("HUNTER_API_KEY", "")
        if not key:
            pytest.skip("HUNTER_API_KEY not set")
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": "stripe.com", "limit": 1, "api_key": key},
            timeout=10,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("data", {}).get("domain") == "stripe.com"


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY UNIT TESTS
# ─────────────────────────────────────────────────────────────────────────────
class TestHelpers:
    def test_make_run_id(self):
        from utils.helpers import make_run_id
        rid = make_run_id("Mamaearth")
        assert rid.startswith("mamaearth_")
        assert len(rid) > 20

    def test_extract_domain(self):
        from utils.helpers import extract_domain
        assert extract_domain("https://www.mamaearth.in/about") == "mamaearth.in"
        assert extract_domain("http://mamaearth.in") == "mamaearth.in"

    def test_calculate_icp_score_max(self):
        from utils.helpers import calculate_icp_score
        score = calculate_icp_score(
            is_b2c=True, employee_count=300, is_vc_backed=True, has_india_presence=True
        )
        assert score == 100

    def test_calculate_icp_score_min(self):
        from utils.helpers import calculate_icp_score
        score = calculate_icp_score(
            is_b2c=False, employee_count=10, is_vc_backed=False, has_india_presence=False
        )
        assert score == 0

    def test_safe_json_parse_with_fence(self):
        from utils.helpers import safe_json_parse
        raw = '```json\n{"key": "value"}\n```'
        result = safe_json_parse(raw)
        assert result == {"key": "value"}

    def test_clean_text(self):
        from utils.helpers import clean_text
        assert clean_text("  Hello   World  ") == "Hello World"

    def test_truncate(self):
        from utils.helpers import truncate
        assert truncate("Hello World", 5) == "Hello…"
        assert truncate("Hi", 10) == "Hi"


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE UNIT TESTS (dry run — no real API calls)
# ─────────────────────────────────────────────────────────────────────────────
class TestPipelineBase:
    def test_base_pipeline_import(self):
        from pipelines.base import BasePipeline
        assert hasattr(BasePipeline, "run")
        assert hasattr(BasePipeline, "fetch")
        assert hasattr(BasePipeline, "extract")
        assert hasattr(BasePipeline, "synthesise")

    def test_all_pipelines_importable(self):
        from pipelines.p01_company_overview.pipeline import CompanyOverviewPipeline
        from pipelines.p02_brand_identity.pipeline import BrandIdentityPipeline
        from pipelines.p03_market_position.pipeline import MarketPositionPipeline
        from pipelines.p04_competitor_mapping.pipeline import CompetitorMappingPipeline
        from pipelines.p05_brand_activity.pipeline import BrandActivityPipeline
        from pipelines.p06_experiential_footprint.pipeline import ExperientialFootprintPipeline
        from pipelines.p07_reputation_research.pipeline import ReputationResearchPipeline
        from pipelines.p08_strategic_watchouts.pipeline import StrategicWatchoutsPipeline
        from pipelines.p09_decision_makers.pipeline import DecisionMakersPipeline
        from pipelines.p10_contact_intelligence.pipeline import ContactIntelligencePipeline
        from pipelines.p11_outreach.pipeline import OutreachPipeline
        from pipelines.p12_tracking.pipeline import TrackingPipeline

    def test_orchestrator_importable(self):
        import orchestrator
        assert hasattr(orchestrator, "run_full_analysis")
        assert hasattr(orchestrator, "get_summary")

    def test_api_models_importable(self):
        from api.models import AnalyseRequest, TrackEventRequest
        req = AnalyseRequest(
            company_name="Test Co",
            company_url="test.com",
            category="D2C brand"
        )
        assert req.company_url == "https://test.com"

    def test_fastapi_app_importable(self):
        from api.main import app
        assert app is not None


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION SMOKE TEST (skipped unless SMOKE=1 in env)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.skipif(os.getenv("SMOKE") != "1", reason="Set SMOKE=1 to run smoke test")
class TestSmoke:
    def test_p01_smoke(self):
        """Run P01 against a real company — requires all API keys."""
        from pipelines.p01_company_overview.pipeline import CompanyOverviewPipeline
        p = CompanyOverviewPipeline(
            company_name="Mamaearth",
            company_url="https://mamaearth.in",
            category="D2C skincare brand"
        )
        result = p.run()
        assert result["status"] != "error", f"Pipeline error: {result.get('error')}"
        assert "icp_fit_score" in result["output"]
        print(f"\n  ICP Score: {result['output']['icp_fit_score']}")
