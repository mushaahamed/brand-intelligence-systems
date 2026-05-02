# P02 — Brand Identity

Extracts the actual brand colors and typography directly from the company's CSS files — no browser rendering required. Produces the palette, font stack, brand tone, and an experiential design angle for StepOneXP's pitch deck.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1 RAW FETCH** | Fetch homepage HTML + linked CSS files via direct HTTP | `requests` / `httpx` |
| **L2 EXTRACT** | Parse CSS with regex: HEX colors (`#xxx`/`#xxxxxx`), RGB/RGBA values, `font-family` declarations; filter near-whites/near-blacks/pure-grays; sort by frequency | Python regex (HEX_RE, RGB_RE, FONT_RE) |
| **L3 SYNTHESISE** | Map color palette + fonts → brand tone, voice keywords, missing elements, experiential design angle | Claude Haiku |

## CSS parsing detail

```python
HEX_RE  = re.compile(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
RGB_RE  = re.compile(r'rgba?\((\d+),\s*(\d+),\s*(\d+)')
FONT_RE = re.compile(r"font-family\s*:\s*([^;}{]+)")
```

Colors are filtered by:
- Removing near-white (R,G,B all > 240)
- Removing near-black (R,G,B all < 15)
- Removing pure grays (R=G=B ± 5)

Top 10 colors by frequency are returned.

## Output fields

| Field | Type | Description |
|-------|------|-------------|
| `primary_colors` | string[] | Top brand colors as hex codes |
| `primary_fonts` | string[] | Font families found in CSS |
| `brand_tone` | string | Overall tonal assessment |
| `brand_voice_keywords` | string[] | Words that describe their voice |
| `missing_brand_elements` | string[] | Gaps in brand identity |
| `experiential_design_angle` | string | How to design activations that match their brand |

## Cost estimate
~$0.02/run (homepage fetch + 2–5 CSS fetches + 1 Haiku synthesis)
