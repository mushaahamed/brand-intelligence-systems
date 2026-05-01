"""
Central settings loaded from environment variables.
All pipeline modules import from here — never read env vars directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── APIFY TOKENS (rotated by pipeline group) ─────────────────────────────────
APIFY_TOKENS = {
    "group_1": os.getenv("APIFY_TOKEN_1", ""),   # p01, p02
    "group_2": os.getenv("APIFY_TOKEN_2", ""),   # p03, p04
    "group_3": os.getenv("APIFY_TOKEN_3", ""),   # p05, p06
    "group_4": os.getenv("APIFY_TOKEN_4", ""),   # p07, p08
    "group_5": os.getenv("APIFY_TOKEN_5", ""),   # p09, p10
}

# Fallback: if only one token provided, use it for all groups
_single_token = os.getenv("APIFY_TOKEN_1", "")
for key in APIFY_TOKENS:
    if not APIFY_TOKENS[key]:
        APIFY_TOKENS[key] = _single_token

# ─── LLM ──────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = "claude-haiku-4-5-20251001"   # fast + cheap for all synthesis
CLAUDE_MODEL_FULL = "claude-sonnet-4-6"            # used only for outreach writing

# ─── HUNTER ───────────────────────────────────────────────────────────────────
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

# ─── APP ──────────────────────────────────────────────────────────────────────
APP_ENV        = os.getenv("APP_ENV", "development")
LOG_LEVEL      = os.getenv("LOG_LEVEL", "INFO")
OUTPUT_DIR     = os.getenv("OUTPUT_DIR", "./outputs")
MAX_RETRIES    = int(os.getenv("MAX_RETRIES", "3"))
REQUEST_TIMEOUT= int(os.getenv("REQUEST_TIMEOUT", "30"))
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "2"))
API_HOST       = os.getenv("API_HOST", "0.0.0.0")
API_PORT       = int(os.getenv("API_PORT", "8000"))
TRACKING_BASE  = os.getenv("TRACKING_BASE", f"http://localhost:{os.getenv('API_PORT', '8000')}/track")
ACTOR_TIMEOUT  = int(os.getenv("ACTOR_TIMEOUT", "60"))   # seconds per Apify actor run


def validate_config() -> dict:
    """Returns dict of which APIs are configured."""
    return {
        "apify":     any(t for t in APIFY_TOKENS.values()),
        "anthropic": bool(ANTHROPIC_API_KEY),
        "hunter":    bool(HUNTER_API_KEY),
    }
