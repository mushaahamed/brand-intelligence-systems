"""
Pipeline 02 — Brand Identity
==============================
Fast version: direct HTTP crawl for pages and CSS (no Apify).
"""
import re
import json
import requests
import structlog
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pipelines.base import BasePipeline
from utils.web_scraper import fast_crawl
from utils.claude_client import synthesise
from utils.helpers import normalise_url, extract_domain, safe_json_parse, truncate

log = structlog.get_logger()
PIPELINE_ID = "p02_brand_identity"

HEX_RE     = re.compile(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
RGB_RE     = re.compile(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')
FONT_RE    = re.compile(r'font-family\s*:\s*([^;}{]+)')
CSS_LINK_RE= re.compile(r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+)["\']', re.I)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}


def _rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _extract_css_assets(html: str, base_url: str) -> list[str]:
    urls = []
    for match in CSS_LINK_RE.finditer(html):
        href = match.group(1)
        urls.append(href if href.startswith("http") else urljoin(base_url, href))
    return urls[:5]


def _fetch_css(url: str) -> str:
    try:
        r = requests.get(url, timeout=8, headers=HEADERS)
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            # Accept CSS regardless of content-type — many CDNs serve as text/plain or application/octet-stream
            if "html" not in ct:  # exclude HTML pages accidentally matched
                return r.text[:50000]
    except Exception:
        pass
    return ""


def _parse_colors(css_text: str) -> list[str]:
    colors = {}
    for m in HEX_RE.finditer(css_text):
        hex_val = "#" + m.group(1).lower()
        if len(hex_val) == 4:
            hex_val = "#" + "".join(c*2 for c in hex_val[1:])
        r = int(hex_val[1:3], 16); g = int(hex_val[3:5], 16); b = int(hex_val[5:7], 16)
        # skip near-white (boring backgrounds) and near-black (text defaults)
        if r > 235 and g > 235 and b > 235: continue
        if r < 20 and g < 20 and b < 20: continue
        # Boost weight for colors defined in CSS custom properties (brand colours live here)
        weight = 1
        # Find if this hex appears near a CSS variable definition like "--primary-color: #ff4500"
        pos = m.start()
        context = css_text[max(0, pos-40):pos]
        if "--" in context or "brand" in context.lower() or "primary" in context.lower() or "accent" in context.lower():
            weight = 5
        colors[hex_val] = colors.get(hex_val, 0) + weight
    for m in RGB_RE.finditer(css_text):
        hex_val = _rgb_to_hex(m.group(1), m.group(2), m.group(3))
        r = int(m.group(1)); g = int(m.group(2)); b = int(m.group(3))
        if r > 235 and g > 235 and b > 235: continue
        if r < 20 and g < 20 and b < 20: continue
        colors[hex_val] = colors.get(hex_val, 0) + 1
    return [c for c, _ in sorted(colors.items(), key=lambda x: -x[1])][:12]


def _parse_fonts(css_text: str) -> list[str]:
    fonts = []
    for m in FONT_RE.finditer(css_text):
        first = m.group(1).strip().split(",")[0].strip().strip("'\"")
        if first and first.lower() not in ("inherit", "initial", "sans-serif", "serif", "monospace"):
            if first not in fonts:
                fonts.append(first)
    return fonts[:4]


def _extract_homepage_copy(pages: list[dict]) -> str:
    for page in pages:
        if page.get("url", "").rstrip("/").count("/") <= 2:
            return (page.get("markdown") or page.get("text") or "")[:2000]
    return pages[0].get("markdown", "") if pages else ""


class BrandIdentityPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Brand Identity"

    def fetch(self) -> dict:
        url = normalise_url(self.company_url)
        raw = {"pages": [], "css_texts": [], "html_raw": ""}

        log.info("p02_fetch_website", url=url)
        raw["pages"] = fast_crawl(url, max_pages=3)

        try:
            resp = requests.get(url, timeout=12, headers=HEADERS, allow_redirects=True)
            html = resp.text
            raw["html_raw"] = html[:10000]
            final_url = resp.url
            for css_url in _extract_css_assets(html, final_url):
                css_text = _fetch_css(css_url)
                if css_text:
                    raw["css_texts"].append(css_text)
        except Exception as e:
            log.warning("p02_html_fetch_failed", error=str(e))

        return raw

    def extract(self, raw: dict) -> dict:
        all_css = "\n".join(raw.get("css_texts", []))
        html    = raw.get("html_raw", "")
        colors  = _parse_colors(all_css + html) or _parse_colors(html)
        fonts   = _parse_fonts(all_css) or _parse_fonts(html)
        copy    = _extract_homepage_copy(raw.get("pages", []))
        return {
            "company_name":     self.company_name,
            "extracted_colors": colors,
            "extracted_fonts":  fonts,
            "homepage_copy":    truncate(copy, 1500),
            "css_sample":       all_css[:2000] if all_css else "",
            "html_sample":      html[:1000],
        }

    def synthesise(self, structured: dict) -> dict:
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
        with open(prompt_path) as f:
            system_prompt = f.read()

        user_data = f"""
COMPANY: {structured['company_name']}
CATEGORY: {self.category}
EXTRACTED COLORS FROM CSS: {structured['extracted_colors']}
EXTRACTED FONTS FROM CSS: {structured['extracted_fonts']}
HOMEPAGE COPY (for tone analysis):
{structured['homepage_copy']}
CSS SAMPLE:
{structured['css_sample'][:1000]}
"""
        result_str = synthesise(system_prompt, user_data, max_tokens=1000)

        if result_str:
            output = safe_json_parse(result_str)
            if output:
                if structured["extracted_colors"] and not output.get("primary_colors"):
                    output["primary_colors"]  = structured["extracted_colors"][:3]
                    output["secondary_colors"] = structured["extracted_colors"][3:6]
                return output

        return {
            "primary_colors":   structured["extracted_colors"][:3],
            "secondary_colors": structured["extracted_colors"][3:6],
            "extracted_fonts":  structured["extracted_fonts"],
            "brand_tone":       "Unknown",
            "brand_maturity":   "Unknown",
            "missing_brand_elements": [],
            "experiential_design_angle": "Insufficient data",
        }
