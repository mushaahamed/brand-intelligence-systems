"""
Base pipeline class. Every pipeline module inherits from this.
Enforces the 3-layer architecture: fetch → extract → synthesise.
"""
import json
import time
import structlog
from abc import ABC, abstractmethod
from typing import Any, Optional
from utils.helpers import timestamp, make_run_id

log = structlog.get_logger()


class BasePipeline(ABC):
    """
    Every pipeline has exactly 3 layers:
      Layer 1 — fetch():    Pull raw data from Apify actors / APIs
      Layer 2 — extract():  Structure raw data into defined metrics
      Layer 3 — synthesise(): LLM reasons over structured data → final output

    Subclasses must implement all three methods.
    """

    pipeline_id: str = "base"
    pipeline_name: str = "Base Pipeline"

    def __init__(self, company_name: str, company_url: str, category: str):
        self.company_name = company_name
        self.company_url  = company_url
        self.category     = category
        self.run_id       = make_run_id(company_name)
        self.started_at   = timestamp()
        self._raw_data: dict    = {}
        self._structured: dict  = {}
        self._output: dict      = {}

    # ── ABSTRACT METHODS (must implement in subclass) ─────────────────────────

    @abstractmethod
    def fetch(self) -> dict:
        """Layer 1: Pull raw data from external sources. No LLM here."""
        pass

    @abstractmethod
    def extract(self, raw: dict) -> dict:
        """Layer 2: Extract and structure defined metrics from raw data."""
        pass

    @abstractmethod
    def synthesise(self, structured: dict) -> dict:
        """Layer 3: LLM synthesises structured data → final output dict."""
        pass

    # ── RUN (orchestrates all 3 layers) ──────────────────────────────────────

    def run(self) -> dict:
        """Execute the full pipeline. Returns final output or error dict."""
        log.info("pipeline_start", pipeline=self.pipeline_id, company=self.company_name)
        t0 = time.time()

        try:
            # Layer 1
            log.info("layer_1_fetch", pipeline=self.pipeline_id)
            self._raw_data = self.fetch()

            # Layer 2
            log.info("layer_2_extract", pipeline=self.pipeline_id)
            self._structured = self.extract(self._raw_data)

            # Layer 3
            log.info("layer_3_synthesise", pipeline=self.pipeline_id)
            self._output = self.synthesise(self._structured)

            elapsed = round(time.time() - t0, 2)
            log.info("pipeline_complete", pipeline=self.pipeline_id, elapsed=elapsed)

            return {
                "pipeline_id":   self.pipeline_id,
                "pipeline_name": self.pipeline_name,
                "company":       self.company_name,
                "run_id":        self.run_id,
                "started_at":    self.started_at,
                "completed_at":  timestamp(),
                "elapsed_secs":  elapsed,
                "status":        "success",
                "output":        self._output,
            }

        except Exception as e:
            log.error("pipeline_error", pipeline=self.pipeline_id, error=str(e))
            return {
                "pipeline_id":  self.pipeline_id,
                "company":      self.company_name,
                "run_id":       self.run_id,
                "status":       "error",
                "error":        str(e),
                "output":       {},
            }

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _safe_get(self, data: dict, *keys, default=None) -> Any:
        """Safely traverse nested dicts."""
        for key in keys:
            if not isinstance(data, dict):
                return default
            data = data.get(key, default)
        return data

    def _collect_text(self, items: list, field: str = "text", max_chars: int = 3000) -> str:
        """Collect and truncate text from a list of scraped items."""
        parts = []
        total = 0
        for item in items:
            text = item.get(field, item.get("markdown", item.get("content", "")))
            if text and isinstance(text, str):
                parts.append(text.strip())
                total += len(text)
                if total >= max_chars:
                    break
        return "\n\n".join(parts)[:max_chars]
