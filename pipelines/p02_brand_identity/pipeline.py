"""
Pipeline 02 — Brand Identity
==============================
Extracts INTENTIONAL brand colors — not frequency-based garbage.

Priority order for color extraction:
  1. CSS custom properties (--primary, --brand-*, --accent-* etc) — always intentional
  2. HTML <meta name="theme-color"> — the browser chrome color, 100% brand
  3. Colors in semantic brand elements (buttons, CTAs, headings, hero sections)
  4. General CSS — filtered to remove known third-party widget signatures

This avoids picking up Razorpay blue, WhatsApp green, payment widget colours
which overwhelm frequency-based extraction on e-commerce sites.
"""
import re, json, requests, structlog
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pipelines.base import BasePipeline
from utils.web_scraper import fast_crawl
from utils.claude_client import synthesise
from utils.helpers import normalise_url, safe_json_parse, truncate

log = structlog.get_logger()
PIPELINE_ID = "p02_brand_identity"

# ── Regexes ────────────────────────────────────────────────────────────────────
HEX_RE      = re.compile(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
RGB_RE      = re.compile(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')
FONT_RE     = re.compile(r'font-family\s*:\s*([^;}{]+)')
CSS_LINK_RE = re.compile(r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+)["\']', re.I)

# CSS custom properties: "--primary-color: #ff4500" or "--brand-green: rgb(60,120,0)"
CSS_VAR_RE  = re.compile(
    r'(--[\w-]*(?:primary|secondary|brand|accent|color|colour|theme|main|key|cta|button|hero|highlight)[\w-]*)'
    r'\s*:\s*(#[0-9a-fA-F]{3,6}|rgb\([^)]+\))',
    re.I
)
# Also catch any --xxx: #color (even without brand keywords — all vars are intentional)
CSS_VAR_ANY = re.compile(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\b')

# meta theme-color
THEME_COLOR_RE = re.compile(
    r'<meta[^>]+(?:name=["\']theme-color["\'][^>]+content=["\']([^"\']+)["\']'
    r'|content=["\']([^"\']+)["\'][^>]+name=["\']theme-color["\'])',
    re.I
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

STYLE_BLOCK_RE = re.compile(r'<style[^>]*>(.*?)</style>', re.DOTALL | re.I)

# ── Third-party color signatures (never brand colors) ─────────────────────────
THIRD_PARTY_COLORS = {
    # Social media
    "#1877f2", "#4267b2",         # Facebook
    "#1da1f2",                    # Twitter / X
    "#e1306c", "#833ab4", "#c13584", "#fd1d1d",  # Instagram
    "#25d366", "#128c7e",         # WhatsApp
    "#ff0000", "#cc0000",         # YouTube
    "#0077b5", "#0a66c2",         # LinkedIn
    # Payment gateways common in India
    "#072654", "#528ff0", "#2d81f7", "#3395ff",  # Razorpay
    "#00b9f5", "#002970", "#00baf2",             # Paytm / PayU
    "#f6a623",                    # generic payment yellow
    # Google
    "#4285f4", "#34a853", "#fbbc04", "#ea4335",
    # Common framework defaults
    "#007bff", "#0d6efd",         # Bootstrap primary
    "#6c757d",                    # Bootstrap secondary
    "#28a745", "#198754",         # Bootstrap success
    "#dc3545",                    # Bootstrap danger
    "#ffc107",                    # Bootstrap warning
    "#17a2b8", "#0dcaf0",         # Bootstrap info
}


def _rgb_to_hex(r, g, b) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _norm_hex(raw: str) -> str | None:
    """Normalise any color string to lowercase 6-digit hex, or None if invalid/excluded."""
    raw = raw.strip()
    m = HEX_RE.search(raw)
    if m:
        h = "#" + m.group(1).lower()
        if len(h) == 4:
            h = "#" + "".join(c * 2 for c in h[1:])
        return h
    m = RGB_RE.search(raw)
    if m:
        return _rgb_to_hex(m.group(1), m.group(2), m.group(3))
    return None


def _is_boring(hex_val: str) -> bool:
    """True for near-white, near-black, or mid-grey — never brand colors."""
    r = int(hex_val[1:3], 16); g = int(hex_val[3:5], 16); b = int(hex_val[5:7], 16)
    if r > 230 and g > 230 and b > 230: return True   # near-white
    if r < 25  and g < 25  and b < 25:  return True   # near-black
    # mid grey: all channels within 15 of each other AND medium brightness
    if abs(r-g) < 15 and abs(g-b) < 15 and 60 < r < 200: return True
    return False


def _fetch_css(url: str) -> str:
    try:
        r = requests.get(url, timeout=8, headers=HEADERS)
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            if "html" not in ct:
                return r.text[:60000]
    except Exception:
        pass
    return ""


def _extract_css_assets(html: str, base_url: str) -> list[str]:
    urls = []
    for m in CSS_LINK_RE.finditer(html):
        href = m.group(1)
        urls.append(href if href.startswith("http") else urljoin(base_url, href))
    return urls[:6]


# ── Smart color extractors ─────────────────────────────────────────────────────

def _extract_css_vars(css_text: str) -> list[str]:
    """
    Extract colors from CSS custom properties.
    These are ALWAYS intentional — designers put brand colors in CSS vars.
    Returns deduped list, brand-keyword vars first.
    """
    brand_colors = []
    other_vars   = []
    seen         = set()

    # Brand-keyword vars get highest priority
    for m in CSS_VAR_RE.finditer(css_text):
        h = _norm_hex(m.group(2))
        if h and h not in seen and not _is_boring(h) and h not in THIRD_PARTY_COLORS:
            seen.add(h)
            brand_colors.append(h)

    # All other CSS vars (still intentional, just not named with brand keywords)
    for m in CSS_VAR_ANY.finditer(css_text):
        h = _norm_hex(m.group(2))
        if h and h not in seen and not _is_boring(h) and h not in THIRD_PARTY_COLORS:
            seen.add(h)
            other_vars.append(h)

    return (brand_colors + other_vars)[:8]


def _extract_meta_theme_color(html: str) -> str | None:
    """Extract <meta name='theme-color' content='#xxx'>"""
    m = THEME_COLOR_RE.search(html)
    if m:
        raw = m.group(1) or m.group(2)
        return _norm_hex(raw)
    return None


def _extract_semantic_colors(html: str, css_text: str) -> list[str]:
    """
    Find colors used in brand-intent contexts:
    - Primary/CTA buttons
    - H1/H2 headings
    - Hero/banner sections
    - Navigation bar
    Returns them deduped and filtered.
    """
    colors = []
    seen   = set()

    # Semantic CSS selectors that carry brand colors
    semantic_patterns = [
        r'(?:\.btn-primary|\.cta|\.button-primary|\.btn-cta|\.primary-btn)[^{]*\{[^}]*',
        r'(?:button|\.btn)[^{]*\{[^}]*(?:background|color)[^}]*',
        r'(?:h1|h2|\.hero|\.banner|\.header-main|\.nav-brand|\.site-header)[^{]*\{[^}]*',
        r'(?:\.primary|\.accent|\.brand-color|\.brand-bg|\.highlight)[^{]*\{[^}]*',
    ]

    combined = css_text + "\n" + html
    for pat in semantic_patterns:
        for block_m in re.finditer(pat, combined, re.I | re.S):
            block = block_m.group(0)
            for hm in HEX_RE.finditer(block):
                h = _norm_hex("#" + hm.group(1))
                if h and h not in seen and not _is_boring(h) and h not in THIRD_PARTY_COLORS:
                    seen.add(h)
                    colors.append(h)

    # Also check inline styles on the body and hero elements
    soup_colors = []
    try:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(style=True):
            style = tag.get("style", "")
            # Only check hero/banner/header elements or body
            tag_name = tag.name or ""
            classes  = " ".join(tag.get("class", []))
            if any(k in (tag_name + classes).lower() for k in
                   ["hero", "banner", "header", "nav", "primary", "brand", "cta", "body"]):
                for hm in HEX_RE.finditer(style):
                    h = _norm_hex("#" + hm.group(1))
                    if h and h not in seen and not _is_boring(h) and h not in THIRD_PARTY_COLORS:
                        seen.add(h)
                        soup_colors.append(h)
    except Exception:
        pass

    return (colors + soup_colors)[:8]


def _extract_general_colors(css_text: str, html: str) -> list[str]:
    """
    General frequency-based extraction as final fallback.
    Still filters third-party colors and boring greys.
    """
    counts = {}
    for text in [css_text, html]:
        for m in HEX_RE.finditer(text):
            h = _norm_hex("#" + m.group(1))
            if h and not _is_boring(h) and h not in THIRD_PARTY_COLORS:
                counts[h] = counts.get(h, 0) + 1
        for m in RGB_RE.finditer(text):
            h = _rgb_to_hex(m.group(1), m.group(2), m.group(3))
            h = _norm_hex(h)
            if h and not _is_boring(h) and h not in THIRD_PARTY_COLORS:
                counts[h] = counts.get(h, 0) + 1

    return [c for c, _ in sorted(counts.items(), key=lambda x: -x[1])][:10]


def _extract_inline_style_colors(html: str) -> list[str]:
    """
    Parse colors from <style> blocks embedded in the HTML.
    Modern JS-heavy sites (Shopify, Next.js) often put their brand CSS here
    rather than in separate linked CSS files.
    """
    all_inline = "\n".join(STYLE_BLOCK_RE.findall(html))
    if not all_inline:
        return []
    return _extract_general_colors(all_inline, "")


def _find_logo_url(html: str, base_url: str) -> str | None:
    """
    Find the brand logo image URL from the page.
    Priority: apple-touch-icon > og:image > img[class*=logo] > first SVG/PNG with 'logo' in name
    """
    soup = BeautifulSoup(html, "lxml")

    # 1. apple-touch-icon — always a brand icon
    for link in soup.find_all("link", rel=True):
        rels = link.get("rel", [])
        if isinstance(rels, list):
            rels = " ".join(rels)
        if "apple-touch-icon" in rels:
            href = link.get("href", "")
            if href:
                return href if href.startswith("http") else urljoin(base_url, href)

    # 2. og:image — often the brand logo or hero image
    meta_og = soup.find("meta", property="og:image")
    if meta_og and meta_og.get("content"):
        return meta_og["content"]

    # 3. img with logo in class, id, alt, or src
    for img in soup.find_all("img"):
        src = img.get("src", "") or img.get("data-src", "")
        alt = img.get("alt", "")
        cls = " ".join(img.get("class", []))
        _id = img.get("id", "")
        if any("logo" in x.lower() for x in [src, alt, cls, _id]):
            if src:
                return src if src.startswith("http") else urljoin(base_url, src)

    return None


def _extract_logo_colors(logo_url: str) -> list[str]:
    """Download logo image and extract dominant colors via colorthief."""
    if not logo_url:
        return []
    try:
        from colorthief import ColorThief
        from io import BytesIO
        from PIL import Image

        r = requests.get(logo_url, timeout=8, headers=HEADERS, stream=True)
        if r.status_code != 200:
            return []

        content_type = r.headers.get("content-type", "")
        # Accept images and SVGs
        if "image" not in content_type and "svg" not in content_type:
            return []
        if "svg" in content_type or logo_url.lower().endswith(".svg"):
            # SVG — extract hex colors directly from markup
            svg_text = r.text
            seen = set()
            results = []
            for m in HEX_RE.finditer(svg_text):
                h = _norm_hex("#" + m.group(1))
                if h and h not in seen and not _is_boring(h) and h not in THIRD_PARTY_COLORS:
                    seen.add(h); results.append(h)
            return results[:5]

        # Raster image — use colorthief
        img_data = BytesIO(r.content)
        ct = ColorThief(img_data)
        palette = ct.get_palette(color_count=6, quality=5)
        colors = []
        for rgb in palette:
            h = _rgb_to_hex(*rgb)
            h = _norm_hex(h)
            if h and not _is_boring(h) and h not in THIRD_PARTY_COLORS:
                colors.append(h)
        return colors[:5]
    except Exception:
        return []


def _parse_fonts(css_text: str) -> list[str]:
    fonts = []
    for m in FONT_RE.finditer(css_text):
        first = m.group(1).strip().split(",")[0].strip().strip("'\"")
        if first and first.lower() not in (
            "inherit", "initial", "sans-serif", "serif", "monospace",
            "system-ui", "-apple-system", "arial", "helvetica"
        ):
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
        raw = {"pages": [], "css_texts": [], "html_raw": "", "final_url": url,
               "logo_url": None, "logo_colors": []}

        log.info(f"     Fetching website assets for {self.company_name}...")
        raw["pages"] = fast_crawl(url, max_pages=3)

        try:
            resp = requests.get(url, timeout=12, headers=HEADERS, allow_redirects=True)
            html = resp.text
            raw["html_raw"]  = html[:15000]
            raw["final_url"] = resp.url

            # Linked CSS files
            css_count = 0
            for css_url in _extract_css_assets(html, resp.url):
                css_text = _fetch_css(css_url)
                if css_text:
                    raw["css_texts"].append(css_text)
                    css_count += 1
            if css_count:
                log.info(f"     {css_count} CSS stylesheet(s) fetched — analysing design tokens")

            # Logo image colors
            logo_url = _find_logo_url(html, resp.url)
            if logo_url:
                raw["logo_url"]    = logo_url
                raw["logo_colors"] = _extract_logo_colors(logo_url)
                if raw["logo_colors"]:
                    log.info(f"     Brand logo identified — {len(raw['logo_colors'])} dominant colors extracted")

        except Exception:
            pass

        return raw

    def extract(self, raw: dict) -> dict:
        all_css = "\n".join(raw.get("css_texts", []))
        html    = raw.get("html_raw", "")

        # ── 5-layer color extraction (highest to lowest confidence) ──
        logo_colors     = raw.get("logo_colors", [])          # from brand logo image/svg
        meta_color      = _extract_meta_theme_color(html)     # <meta theme-color>
        inline_colors   = _extract_inline_style_colors(html)  # <style> blocks in HTML
        css_var_colors  = _extract_css_vars(all_css + "\n" + "\n".join(
            STYLE_BLOCK_RE.findall(html)))                     # CSS vars from both sources
        semantic_colors = _extract_semantic_colors(html, all_css)
        general_colors  = _extract_general_colors(all_css, html)

        # Merge in priority order, dedup
        seen = set()
        merged = []
        for color in (
            logo_colors +                          # logo = strongest brand signal
            ([meta_color] if meta_color else []) + # meta theme-color = browser chrome
            css_var_colors +                       # CSS vars = intentional design tokens
            inline_colors +                        # inline <style> blocks
            semantic_colors +                      # buttons, hero, headings
            general_colors                         # frequency fallback
        ):
            if color and color not in seen:
                seen.add(color)
                merged.append(color)

        fonts = _parse_fonts(all_css) or _parse_fonts(
            "\n".join(STYLE_BLOCK_RE.findall(html))) or _parse_fonts(html)
        copy  = _extract_homepage_copy(raw.get("pages", []))

        log.info(f"     Brand palette extracted — {len(merged)} colors identified across {len([x for x in [logo_colors, [meta_color] if meta_color else [], css_var_colors, inline_colors] if x])} signal sources")

        return {
            "company_name":       self.company_name,
            # Structured for LLM — grouped by confidence tier
            "colors_logo":        logo_colors,
            "colors_meta":        [meta_color] if meta_color else [],
            "colors_css_vars":    css_var_colors,
            "colors_inline":      inline_colors[:8],
            "colors_semantic":    semantic_colors,
            "colors_general":     general_colors[:8],
            # Merged best-guess list for fallback
            "extracted_colors":   merged[:12],
            "extracted_fonts":    fonts,
            "homepage_copy":      truncate(copy, 1500),
            "css_sample":         (all_css or "\n".join(STYLE_BLOCK_RE.findall(html)))[:3000],
            "logo_url":           raw.get("logo_url"),
        }

    def synthesise(self, structured: dict) -> dict:
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
        with open(prompt_path) as f:
            system_prompt = f.read()

        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}

COLOR EXTRACTION RESULTS (use these to identify the real brand palette):

  LOGO colors — extracted from the actual brand logo image (HIGHEST confidence):
    {structured.get('colors_logo') or 'Not found'}
    Logo URL: {structured.get('logo_url') or 'Not found'}

  meta theme-color (browser chrome — 100% intentional):
    {structured['colors_meta'] or 'Not found'}

  CSS custom property colors (--primary, --brand-*, --accent-* etc — very high confidence):
    {structured['colors_css_vars'] or 'None found'}

  Inline <style> block colors (brand CSS embedded in HTML — high confidence):
    {structured.get('colors_inline', [])[:6] or 'None found'}

  Semantic element colors (buttons, CTAs, headings, hero sections — high confidence):
    {structured['colors_semantic'] or 'None found'}

  General CSS colors (filtered, no third-party widgets — medium confidence):
    {structured['colors_general'][:6] or 'None found'}

FONTS: {structured['extracted_fonts']}

HOMEPAGE COPY (for tone, voice and positioning analysis):
{structured['homepage_copy']}

CSS SAMPLE (first 1500 chars — look for CSS variable definitions):
{structured['css_sample'][:1500]}

IMPORTANT: Logo colors and meta theme-color are the strongest signals — the brand CHOSE these.
CSS custom properties are design tokens set intentionally by their team.
Inline <style> block colors are real — modern sites (Shopify, Next.js) embed CSS here, not in files.
IGNORE any colors that look like payment gateways (Razorpay, Paytm), social media icons, or chat widgets.
Pick 2-4 colors that form a coherent, intentional brand palette."""

        # Use GPT-4o (not mini) — it has real brand knowledge to validate extracted colors
        from config.settings import OPENAI_MODEL_FULL
        result_str = synthesise(system_prompt, user_data, model=OPENAI_MODEL_FULL, max_tokens=1000)

        if result_str:
            output = safe_json_parse(result_str)
            if output:
                if not output.get("primary_colors"):
                    best = (structured.get("colors_logo") or
                            structured["colors_meta"] or
                            structured["colors_css_vars"] or
                            structured.get("colors_inline") or
                            structured["colors_semantic"] or
                            structured["extracted_colors"])
                    output["primary_colors"]  = best[:3]
                    output["secondary_colors"] = best[3:6]
                log.info(f"     Tone: {output.get('brand_tone')} · Primary: {output.get('primary_colors')}")
                return output

        # Hard fallback — GPT call failed entirely
        best = (structured.get("colors_logo") or
                structured["colors_meta"] or
                structured["colors_css_vars"] or
                structured.get("colors_inline") or
                structured["colors_semantic"] or
                structured["extracted_colors"])
        return {
            "primary_colors":    best[:3],
            "secondary_colors":  best[3:6],
            "extracted_fonts":   structured["extracted_fonts"],
            "brand_tone":        "Unknown",
            "brand_maturity":    "Unknown",
            "missing_brand_elements":    [],
            "experiential_design_angle": "Insufficient data",
        }
