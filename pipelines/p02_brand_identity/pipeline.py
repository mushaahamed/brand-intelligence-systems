"""
Pipeline 02 — Brand Identity
==============================
Layer 1: Crawl website homepage + CSS extraction
Layer 2: Extract colors, fonts, tone from CSS/HTML/copy
Layer 3: Claude synthesises brand identity profile + missing elements

Unique feature: CSS color extraction without browser rendering.
We parse raw CSS files linked from the HTML for hex color values and font-family declarations.
"""
import re
import json
import requests
import structlog
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pipelines.base import BasePipeline
from utils.apify_client import crawl_website
from utils.claude_client import synthesise
from utils.helpers import normalise_url, extract_domain, safe_json_parse, truncate

log = structlog.get_logger()
PIPELINE_ID = "p02_brand_identity"

# Common CSS color patterns
HEX_RE     = re.compile(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
RGB_RE     = re.compile(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')
FONT_RE    = re.compile(r'font-family\s*:\s*([^;}{]+)')
CSS_LINK_RE= re.compile(r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+)["\']', re.I)


def _rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _extract_css_assets(html: str, base_url: str) -> list[str]:
    """Find all CSS stylesheet URLs in HTML."""
    urls = []
    for match in CSS_LINK_RE.finditer(html):
        href = match.group(1)
        if href.startswith("http"):
            urls.append(href)
        else:
            urls.append(urljoin(base_url, href))
    return urls[:5]  # Limit to first 5 CSS files


def _fetch_css(url: str, timeout: int = 10) -> str:
    """Fetch a CSS file content."""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and "text/css" in r.headers.get("content-type", ""):
            return r.text[:50000]
    except Exception:
        pass
    return ""


def _parse_colors(css_text: str) -> list[str]:
    """Extract unique hex colors from CSS, sorted by frequency."""
    colors = {}
    for m in HEX_RE.finditer(css_text):
        hex_val = "#" + m.group(1).lower()
        if len(hex_val) == 4:   # Expand shorthand
            hex_val = "#" + "".join(c*2 for c in hex_val[1:])
        # Filter out near-white, near-black, and pure grays
        r = int(hex_val[1:3], 16)
        g = int(hex_val[3:5], 16)
        b = int(hex_val[5:7], 16)
        if (r > 240 and g > 240 and b > 240): continue  # near-white
        if (r < 15 and g < 15 and b < 15): continue      # near-black
        colors[hex_val] = colors.get(hex_val, 0) + 1

    for m in RGB_RE.finditer(css_text):
        hex_val = _rgb_to_hex(m.group(1), m.group(2), m.group(3))
        colors[hex_val] = colors.get(hex_val, 0) + 1

    # Return top colors by frequency
    return [c for c, _ in sorted(colors.items(), key=lambda x: -x[1])][:10]


def _parse_fonts(css_text: str) -> list[str]:
    """Extract font-family values from CSS."""
    fonts = []
    for m in FONT_RE.finditer(css_text):
        raw = m.group(1).strip()
        # Take first font in stack, strip quotes
        first = raw.split(",")[0].strip().strip("'\"")
        if first and first.lower() not in ("inherit", "initial", "sans-serif", "serif", "monospace"):
            if first not in fonts:
                fonts.append(first)
    return fonts[:4]


def _extract_homepage_copy(pages: list[dict]) -> str:
    """Get homepage copy for tone analysis."""
    for page in pages:
        url = page.get("url", "")
        if url.rstrip("/").count("/") <= 2:  # Homepage or near-root
            text = page.get("markdown") or page.get("text") or ""
            return text[:2000]
    return pages[0].get("markdown", "") if pages else ""


class BrandIdentityPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Brand Identity"

    # ── LAYER 1: FETCH ────────────────────────────────────────────────────────

    def fetch(self) -> dict:
        url = normalise_url(self.company_url)
        raw = {"pages": [], "css_texts": [], "html_raw": ""}

        # Crawl website
        log.info("p02_fetch_website", url=url)
        pages = crawl_website(url, PIPELINE_ID, max_pages=4)
        raw["pages"] = pages

        # Fetch homepage HTML directly for CSS links
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            html = resp.text
            raw["html_raw"] = html[:10000]

            # Fetch CSS files
            css_urls = _extract_css_assets(html, url)
            log.info("p02_css_files_found", count=len(css_urls))
            for css_url in css_urls:
                css_text = _fetch_css(css_url)
                if css_text:
                    raw["css_texts"].append(css_text)
        except Exception as e:
            log.warning("p02_html_fetch_failed", error=str(e))

        return raw

    # ── LAYER 2: EXTRACT ─────────────────────────────────────────────────────

    def extract(self, raw: dict) -> dict:
        all_css = "\n".join(raw.get("css_texts", []))
        html    = raw.get("html_raw", "")

        colors  = _parse_colors(all_css + html)
        fonts   = _parse_fonts(all_css)
        copy    = _extract_homepage_copy(raw.get("pages", []))

        # Extract inline styles from HTML as fallback
        if not colors:
            colors = _parse_colors(html)
        if not fonts:
            fonts = _parse_fonts(html)

        return {
            "company_name":   self.company_name,
            "extracted_colors": colors,
            "extracted_fonts":  fonts,
            "homepage_copy":    truncate(copy, 1500),
            "css_sample":       all_css[:2000] if all_css else "",
            "html_sample":      html[:1000],
        }

    # ── LAYER 3: SYNTHESISE ───────────────────────────────────────────────────

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
                # Ensure extracted colors are included even if Claude missed some
                if structured["extracted_colors"] and not output.get("primary_colors"):
                    output["primary_colors"]   = structured["extracted_colors"][:3]
                    output["secondary_colors"]  = structured["extracted_colors"][3:6]
                return output

        # Fallback
        return {
            "primary_colors":    structured["extracted_colors"][:3],
            "secondary_colors":  structured["extracted_colors"][3:6],
            "extracted_fonts":   structured["extracted_fonts"],
            "brand_tone":        "Unknown",
            "brand_maturity":    "Unknown",
            "missing_brand_elements": [],
            "experiential_design_angle": "Insufficient data — manual review recommended",
        }
